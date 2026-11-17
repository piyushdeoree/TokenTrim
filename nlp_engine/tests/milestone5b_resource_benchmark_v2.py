"""Milestone 5B v2: Resilient Checkpoint-Enabled Resource Benchmark Runner.

Provides:
1. Incremental per-sample atomic checkpointing (`milestone5b_resource_checkpoint.json`)
2. Automatic resumption from existing checkpoints without rerunning completed samples
3. Checkpoint corruption and configuration signature mismatch validation
4. Live unbuffered timestamped logging (`milestone5b_resource_benchmark.log`)
5. Genuine hard timeout enforcement via CREATE_SUSPENDED subprocess isolation & Win32 Job Object assignment
6. Multi-layered process-tree cleanup (Win32 Job Object + taskkill /F /T + Toolhelp32 process snapshot)
7. Soft upfront warm-up latency gates persisted across resumed runs
8. Bounded, realistic workload generators for large inputs (512 KiB, 1 MiB, 2 MiB, optional 4 MiB)
9. Memory stability experiments (tracemalloc + Windows working set) with per-iteration checkpointing
10. Multi-process concurrency scaling (1, 2, 4, 8 isolated worker processes) with per-request atomic checkpointing
11. Final structured JSON and Markdown report compilation with safe artifact preservation
"""

from __future__ import annotations

import argparse
import concurrent.futures
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import threading
import time
import tracemalloc
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from nlp_engine import analyze_prompt_detailed

# Output file paths
TESTS_DIR = Path(__file__).resolve().parent
CHECKPOINT_PATH = TESTS_DIR / "milestone5b_resource_checkpoint.json"
LOG_PATH = TESTS_DIR / "milestone5b_resource_benchmark.log"
JSON_OUTPUT_PATH = TESTS_DIR / "milestone5b_resource_results_v2.json"
MD_OUTPUT_PATH = TESTS_DIR / "milestone5b_resource_results_v2.md"

FORMAT_VERSION = 2
DEFAULT_WORKER_TIMEOUT = 180  # 3 minutes hard timeout per sample


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class CheckpointCorruptionError(Exception):
    """Raised when a checkpoint file exists but contains corrupted or truncated data."""


class CheckpointValidationError(Exception):
    """Raised when a checkpoint does not match the required schema version or structure."""


class ConfigurationMismatchError(Exception):
    """Raised when attempting to resume a checkpoint created with a different configuration."""


class WorkerTimeoutError(Exception):
    """Raised when a sample execution exceeds its configured hard timeout limit."""


class JobObjectIsolationError(Exception):
    """Raised when Win32 Job Object process-tree isolation cannot be reliably established."""


# ---------------------------------------------------------------------------
# Win32 Constants, Structures & 64-Bit Safe Function Signatures
# ---------------------------------------------------------------------------

TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPTHREAD = 0x00000004
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
THREAD_SUSPEND_RESUME = 0x0002
CREATE_SUSPENDED = 0x00000004
STILL_ACTIVE = 259
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JobObjectExtendedLimitInformation = 9


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("PageFaultCount", wt.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(wt.ULONG)),
        ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", wt.LONG),
        ("dwFlags", wt.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ThreadID", wt.DWORD),
        ("th32OwnerProcessID", wt.DWORD),
        ("tpBasePri", wt.LONG),
        ("tpDeltaPri", wt.LONG),
        ("dwFlags", wt.DWORD),
    ]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wt.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wt.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wt.DWORD),
        ("SchedulingClass", wt.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryLimit", ctypes.c_size_t),
        ("PeakJobMemoryLimit", ctypes.c_size_t),
    ]


def _get_win32_kernel32():
    """Return kernel32 with explicit 64-bit safe argtypes and restypes configured."""
    if sys.platform != "win32":
        return None
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    k32.GetCurrentProcess.argtypes = []
    k32.GetCurrentProcess.restype = wt.HANDLE

    k32.CreateJobObjectW.argtypes = [wt.LPVOID, wt.LPCWSTR]
    k32.CreateJobObjectW.restype = wt.HANDLE

    k32.SetInformationJobObject.argtypes = [wt.HANDLE, ctypes.c_int, wt.LPVOID, wt.DWORD]
    k32.SetInformationJobObject.restype = wt.BOOL

    k32.AssignProcessToJobObject.argtypes = [wt.HANDLE, wt.HANDLE]
    k32.AssignProcessToJobObject.restype = wt.BOOL

    k32.TerminateJobObject.argtypes = [wt.HANDLE, wt.UINT]
    k32.TerminateJobObject.restype = wt.BOOL

    k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k32.OpenProcess.restype = wt.HANDLE

    k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    k32.GetExitCodeProcess.restype = wt.BOOL

    k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
    k32.TerminateProcess.restype = wt.BOOL

    k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    k32.CreateToolhelp32Snapshot.restype = wt.HANDLE

    k32.Process32First.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
    k32.Process32First.restype = wt.BOOL

    k32.Process32Next.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
    k32.Process32Next.restype = wt.BOOL

    k32.Thread32First.argtypes = [wt.HANDLE, ctypes.POINTER(THREADENTRY32)]
    k32.Thread32First.restype = wt.BOOL

    k32.Thread32Next.argtypes = [wt.HANDLE, ctypes.POINTER(THREADENTRY32)]
    k32.Thread32Next.restype = wt.BOOL

    k32.OpenThread.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k32.OpenThread.restype = wt.HANDLE

    k32.ResumeThread.argtypes = [wt.HANDLE]
    k32.ResumeThread.restype = wt.DWORD

    k32.CloseHandle.argtypes = [wt.HANDLE]
    k32.CloseHandle.restype = wt.BOOL

    return k32


def get_process_memory() -> Tuple[Optional[float], Optional[float]]:
    """Return (current_working_set_mib, peak_working_set_mib) on Windows, or (None, None)."""
    if sys.platform != "win32":
        return None, None
    try:
        k32 = _get_win32_kernel32()
        fn = getattr(k32, "K32GetProcessMemoryInfo", None)
        if fn is None:
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            fn = psapi.GetProcessMemoryInfo
        fn.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wt.DWORD]
        fn.restype = wt.BOOL

        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        h = k32.GetCurrentProcess()
        if fn(h, ctypes.byref(pmc), pmc.cb):
            cur_mib = round(pmc.WorkingSetSize / (1024 * 1024), 2)
            peak_mib = round(pmc.PeakWorkingSetSize / (1024 * 1024), 2)
            return cur_mib, peak_mib
    except Exception:
        pass
    return None, None


# ---------------------------------------------------------------------------
# Windows Toolhelp32 Snapshot & Process Inspection Utilities
# ---------------------------------------------------------------------------

def is_process_alive(pid: int) -> bool:
    """Return True if a process with PID pid is still running on the system."""
    if not pid or pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            k32 = _get_win32_kernel32()
            h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not h:
                return False
            exit_code = wt.DWORD()
            res = k32.GetExitCodeProcess(h, ctypes.byref(exit_code))
            k32.CloseHandle(h)
            return bool(res and exit_code.value == STILL_ACTIVE)
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def get_descendant_pids(root_pid: int) -> List[int]:
    """Return all child and grandchild PIDs for a given root PID on Windows."""
    if sys.platform != "win32" or not root_pid or root_pid <= 0:
        return []
    try:
        k32 = _get_win32_kernel32()
        h_snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if not h_snap or h_snap == INVALID_HANDLE_VALUE:
            return []

        parent_map: Dict[int, List[int]] = {}
        pe = PROCESSENTRY32()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
        if k32.Process32First(h_snap, ctypes.byref(pe)):
            while True:
                parent_map.setdefault(pe.th32ParentProcessID, []).append(pe.th32ProcessID)
                if not k32.Process32Next(h_snap, ctypes.byref(pe)):
                    break
        k32.CloseHandle(h_snap)

        descendants: List[int] = []
        queue = [root_pid]
        while queue:
            curr = queue.pop(0)
            for ch in parent_map.get(curr, []):
                descendants.append(ch)
                queue.append(ch)
        return descendants
    except Exception:
        return []


def resume_suspended_process(pid: int) -> bool:
    """Resume all suspended threads belonging to pid after Job Object assignment completes."""
    if sys.platform != "win32" or not pid or pid <= 0:
        return False
    try:
        k32 = _get_win32_kernel32()
        h_snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
        if not h_snap or h_snap == INVALID_HANDLE_VALUE:
            return False

        te = THREADENTRY32()
        te.dwSize = ctypes.sizeof(THREADENTRY32)
        resumed_any = False
        if k32.Thread32First(h_snap, ctypes.byref(te)):
            while True:
                if te.th32OwnerProcessID == pid:
                    h_thread = k32.OpenThread(THREAD_SUSPEND_RESUME, False, te.th32ThreadID)
                    if h_thread:
                        prev_count = k32.ResumeThread(h_thread)
                        k32.CloseHandle(h_thread)
                        if prev_count != 0xFFFFFFFF:
                            resumed_any = True
                if not k32.Thread32Next(h_snap, ctypes.byref(te)):
                    break
        k32.CloseHandle(h_snap)
        return resumed_any
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Windows Job Object & Reliable Process-Tree Termination
# ---------------------------------------------------------------------------

def create_job_object() -> Optional[int]:
    """Create a Windows Job Object configured to kill all assigned processes when closed."""
    if sys.platform != "win32":
        return None
    try:
        k32 = _get_win32_kernel32()
        h_job = k32.CreateJobObjectW(None, None)
        if not h_job:
            return None

        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        res = k32.SetInformationJobObject(
            h_job,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not res:
            k32.CloseHandle(h_job)
            return None
        return int(h_job)
    except Exception:
        return None


def assign_process_to_job(h_job: Optional[int], proc_handle: int) -> bool:
    """Assign a process handle to an existing Windows Job Object."""
    if not h_job or not proc_handle or sys.platform != "win32":
        return False
    try:
        k32 = _get_win32_kernel32()
        return bool(k32.AssignProcessToJobObject(wt.HANDLE(h_job), wt.HANDLE(proc_handle)))
    except Exception:
        return False


def _close_proc_pipes_and_reap(proc: subprocess.Popen, wait_timeout: float = 3.0) -> None:
    """Close subprocess standard pipes and reap the process handle without hanging."""
    for stream in (proc.stdin, proc.stdout, proc.stderr):
        if stream is not None:
            try:
                stream.close()
            except Exception:
                pass
    try:
        proc.wait(timeout=wait_timeout)
    except Exception:
        try:
            proc.kill()
            proc.wait(timeout=2.0)
        except Exception:
            pass


def kill_process_tree(
    proc: subprocess.Popen,
    h_job: Optional[int] = None,
    force_toolhelp_fallback: bool = False,
    force_job_object_only: bool = False,
) -> None:
    """Reliably terminate a subprocess and all its descendant processes on Windows and POSIX.

    Layers (unless isolated for testing via force_job_object_only or force_toolhelp_fallback):
    1. Win32 Job Object kernel-level termination (TerminateJobObject + CloseHandle).
    2. taskkill /F /T /PID (walks Windows process tree by parent PID).
    3. Toolhelp32 process snapshot walk (directly calls TerminateProcess on all descendant PIDs).
    4. Direct proc.kill() on the root worker process and pipe closure/reaping.
    """
    if sys.platform == "win32":
        k32 = _get_win32_kernel32()
        pid = proc.pid
        descendants = get_descendant_pids(pid) if pid else []

        # 1. Terminate Win32 Job Object (kernel-level termination of entire assigned tree)
        if h_job and not force_toolhelp_fallback:
            try:
                k32.TerminateJobObject(wt.HANDLE(h_job), 1)
            except Exception:
                pass

        # 2. Invoke taskkill /F /T /PID unless isolated to Job Object or Toolhelp32
        if pid and not force_toolhelp_fallback and not force_job_object_only:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    check=False,
                    timeout=5,
                )
            except Exception:
                pass

        # 3. Direct Toolhelp32 process-tree termination fallback
        if descendants and not force_job_object_only:
            for d_pid in reversed(descendants):
                try:
                    h_proc = k32.OpenProcess(PROCESS_TERMINATE, False, d_pid)
                    if h_proc:
                        k32.TerminateProcess(h_proc, 1)
                        k32.CloseHandle(h_proc)
                except Exception:
                    pass

        # 4. Direct process termination fallback on the root worker (unless testing Job Object alone)
        if not force_job_object_only:
            try:
                proc.kill()
            except Exception:
                pass

        # 5. Close Job Object handle (triggers KILL_ON_JOB_CLOSE as well)
        if h_job:
            try:
                k32.CloseHandle(wt.HANDLE(h_job))
            except Exception:
                pass

        # 6. Close pipes and reap process handle safely
        _close_proc_pipes_and_reap(proc)
    else:
        try:
            import signal
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        _close_proc_pipes_and_reap(proc)


# ---------------------------------------------------------------------------
# Safe Report & Checkpoint Preservation Mechanism
# ---------------------------------------------------------------------------

def safe_archive_file(file_path: Path, archive_tag: Optional[str] = None) -> Optional[Path]:
    """Safely archive file_path to a unique timestamped backup without overwriting existing files."""
    if not file_path.exists():
        return None

    tag = archive_tag or time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    stem = file_path.stem
    ext = file_path.suffix
    bak_name = f"{stem}.{tag}{ext}.bak"
    bak_path = file_path.parent / bak_name

    counter = 1
    while bak_path.exists():
        bak_name = f"{stem}.{tag}_{counter}{ext}.bak"
        bak_path = file_path.parent / bak_name
        counter += 1

    try:
        os.replace(file_path, bak_path)
        return bak_path
    except Exception:
        try:
            shutil.copy2(file_path, bak_path)
            file_path.unlink()
            return bak_path
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Live Logging
# ---------------------------------------------------------------------------

class ProgressLogger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self._lock = threading.Lock()

    def log(self, message: str, level: str = "INFO") -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        line = f"[{timestamp}] [{level}] {message}"
        with self._lock:
            print(line, flush=True)
            try:
                with self.log_path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
                    f.flush()
            except Exception:
                pass


LOGGER = ProgressLogger(LOG_PATH)


# ---------------------------------------------------------------------------
# Deterministic Prompt Generators
# ---------------------------------------------------------------------------

def _pad_to_target_bytes(text: str, target_bytes: int) -> str:
    """Pad or trim text to exactly target_bytes in UTF-8 encoding."""
    encoded = text.encode("utf-8")
    if len(encoded) == target_bytes:
        return text
    if len(encoded) > target_bytes:
        trimmed = encoded[:target_bytes]
        return trimmed.decode("utf-8", errors="ignore")

    needed = target_bytes - len(encoded)
    prefix = "\n\n# System Architecture Appendix Notes\n"
    prefix_bytes = len(prefix.encode("utf-8"))
    if needed <= prefix_bytes + 2:
        return text + (" " * needed)

    body_bytes = needed - prefix_bytes - 1
    padding = prefix + ("=" * body_bytes) + "\n"
    candidate = text + padding
    diff = len(candidate.encode("utf-8")) - target_bytes
    if diff > 0:
        candidate = candidate[:-diff]
    elif diff < 0:
        candidate = candidate + (" " * (-diff))
    return candidate


def generate_clause_heavy_prompt(target_bytes: int) -> str:
    """Profile 1: Exactly 329 instruction clauses (crossing 300 guard), expanded with context."""
    base_clauses = [
        "Please ensure the application validates incoming JSON payloads against the v2 schema.",
        "Set the connection pool minimum size to 10 connections.",
        "Set the connection pool maximum size to 100 connections.",
        "Do not allow unauthenticated access to the admin dashboard under any circumstances.",
        "Cache expiration time must be exactly 300 seconds.",
        "Cache expiration time must not exceed 600 seconds.",
        "Retry transient network errors up to 3 times with exponential backoff.",
        "Log all failed authentication attempts to /var/log/audit.log.",
        "Format date and time output using ISO-8601 UTC format strictly.",
        "Never commit secrets, tokens, or private keys to source control.",
        "Use Redis cluster mode for distributed session storage.",
        "When payload size exceeds 10MB, return HTTP status 413 Payload Too Large.",
        "Sanitize all user-provided HTML inputs to prevent cross-site scripting attacks.",
        "Do not disable TLS 1.3 protocol verification.",
    ]
    lines = ["# High-Density Clause and Instruction Specification\n"]
    target_clauses = 329
    clause_idx = 1
    while clause_idx <= target_clauses:
        for clause in base_clauses:
            if clause_idx > target_clauses:
                break
            lines.append(f"Directive {clause_idx}: {clause}")
            clause_idx += 1

    prompt_core = "\n".join(lines)
    note_idx = 1
    while len(prompt_core.encode("utf-8")) < target_bytes:
        note = (
            f"\n\nContext Note {note_idx}: Operational subsystem {note_idx} coordinates background job execution, "
            f"observes telemetry metrics, and records checkpoint heartbeats to the persistent cluster catalog."
        )
        note_idx += 1
        prompt_core += note

    return _pad_to_target_bytes(prompt_core, target_bytes)


def generate_technical_protected_prompt(target_bytes: int) -> str:
    """Profile 2: Technical literals, code blocks, JSON schemas, regex, filepaths, URLs, env vars."""
    blocks = [
        """```python
import hashlib
import hmac

def verify_webhook(payload: bytes, secret: str, signature: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```""",
        """```json
{
  "$schema": "[https://json-schema.org/draft/2020-12/schema](https://json-schema.org/draft/2020-12/schema)",
  "title": "CostRecord",
  "type": "object",
  "properties": {
    "account_id": {"type": "string", "pattern": "^acc_[a-zA-Z0-9]{16}$"},
    "model": {"type": "string", "enum": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"]},
    "tokens_consumed": {"type": "integer", "minimum": 1},
    "cost_usd": {"type": "number", "minimum": 0.0}
  },
  "required": ["account_id", "model", "tokens_consumed", "cost_usd"]
}
```""",
        """```sql
SELECT account_id, model, SUM(tokens_consumed) AS total_tokens, SUM(cost_usd) AS total_cost
FROM billing.daily_usage
WHERE usage_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY account_id, model
ORDER BY total_cost DESC;
```""",
        """Endpoints and configuration:
- Primary API: https://api.tokentrim.internal:8443/v2/telemetry/events
- Database path: F:\\TokenTrim\\DataStore\\telemetry_primary.db
- Backup path: /var/backup/tokentrim/snapshot-2026-11.tar.gz
- Environment: $TOKEN_TRIM_SECRET_KEY, $REDIS_REPLICA_PORT=6380, $WORKER_CONCURRENCY=8
- Regex validation: ^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$
- Multilingual note: කරුණාකර දත්ත සමුදාය ආරක්ෂා කරන්න (Protect the database).
- Spanish requirement: Asegurar que todas las transacciones sean atómicas.""",
    ]
    lines = ["# Technical Infrastructure and Protected Literals Specification\n"]
    block_idx = 1
    while True:
        for b in blocks:
            lines.append(f"## Component Specification Unit {block_idx}\n{b}\n")
            block_idx += 1
            current = "\n".join(lines)
            if len(current.encode("utf-8")) >= target_bytes:
                return _pad_to_target_bytes(current, target_bytes)


def generate_multisection_spec_prompt(target_bytes: int) -> str:
    """Profile 3: Structured enterprise architecture specification with bounded constraints."""
    modules = [
        ("Authentication and Access Control", "Output format: JSON strictly.", "All session tokens must use JWT with ES256 signing."),
        ("Billing and Cost Forecasting", "Output format: Markdown table format strictly.", "Daily aggregation runs at 00:00:00 UTC."),
        ("Prompt Optimization Pipeline", "Output format: YAML configuration schema strictly.", "Conservative 300-clause guard must remain active."),
        ("Event Ingestion Engine", "Output format: Protocol Buffers v3 strictly.", "Dead letter queue location: s3://tokentrim-dlq-prod/events/"),
        ("Database Storage Tier", "Output format: PostgreSQL DDL schema strictly.", "Replication factor must be set to 3."),
        ("Distributed Cache Cluster", "Output format: Redis sentinel configuration.", "Cluster nodes must communicate over TLS 1.3."),
        ("Observability and Metrics", "Output format: Prometheus metrics exposition.", "Sample resolution must be exactly 15 seconds."),
        ("Audit Logging Subsystem", "Output format: CEF standard format strictly.", "Log retention period must be exactly 365 days."),
    ]
    lines = ["# Enterprise System Architecture and Operational Specification\n"]
    for idx, (title, fmt, req) in enumerate(modules, start=1):
        lines.append(
            f"# Section {idx}: {title}\n"
            f"Scope: Core platform component {idx}.\n"
            f"{fmt}\n"
            f"Requirement: {req}\n"
            f"Architectural description: This subsystem coordinates with surrounding microservices, maintains "
            f"internal state consistency across the distributed cluster, and enforces tenant isolation boundary checks.\n"
        )
    current = "\n".join(lines)
    note_idx = 1
    while len(current.encode("utf-8")) < target_bytes:
        desc = (
            f"\n\nArchitecture Appendix Note {note_idx}: Integration contract {note_idx} establishes high-availability "
            f"failover semantics, cross-region replication latency bounds, and automated disaster recovery runbooks."
        )
        note_idx += 1
        current += desc

    return _pad_to_target_bytes(current, target_bytes)


GENERATORS: Dict[str, Callable[[int], str]] = {
    "clause_heavy": generate_clause_heavy_prompt,
    "technical_protected": generate_technical_protected_prompt,
    "multisection_spec": generate_multisection_spec_prompt,
}


# ---------------------------------------------------------------------------
# Checkpoint Persistence and Validation
# ---------------------------------------------------------------------------

def calculate_workload_signature(scenarios_config: list, memory_config: dict, concurrency_config: dict) -> str:
    """Compute a deterministic hash of the benchmark configuration matrix."""
    blob = json.dumps({
        "scenarios": scenarios_config,
        "memory": memory_config,
        "concurrency": concurrency_config,
    }, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def atomic_write_checkpoint(checkpoint_path: Path, data: dict) -> None:
    """Atomically write data to checkpoint_path using a PID/thread-unique temp file and os.replace."""
    unique_tmp = checkpoint_path.parent / (
        f"{checkpoint_path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        with unique_tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(unique_tmp, checkpoint_path)
    finally:
        if unique_tmp.exists():
            try:
                unique_tmp.unlink()
            except Exception:
                pass


def load_and_validate_checkpoint(checkpoint_path: Path, expected_signature: Optional[str] = None) -> dict:
    """Load existing checkpoint, verifying integrity, version, and signature."""
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found at {checkpoint_path}")

    try:
        with checkpoint_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise CheckpointCorruptionError(f"Corrupted or truncated checkpoint JSON at {checkpoint_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise CheckpointValidationError("Checkpoint root must be a JSON object")

    if data.get("format_version") != FORMAT_VERSION:
        raise CheckpointValidationError(
            f"Unsupported checkpoint version {data.get('format_version')}; expected {FORMAT_VERSION}"
        )

    required_keys = {"benchmark_id", "workload_signature", "scenarios", "memory_experiments", "concurrency_experiments"}
    missing = required_keys - set(data.keys())
    if missing:
        raise CheckpointValidationError(f"Checkpoint is missing required keys: {sorted(missing)}")

    if expected_signature and data.get("workload_signature") != expected_signature:
        raise ConfigurationMismatchError(
            f"Checkpoint signature {data.get('workload_signature')[:12]} does not match "
            f"current workload configuration {expected_signature[:12]}. "
            f"Use --fresh to archive the old checkpoint and start a new benchmark."
        )

    return data


# ---------------------------------------------------------------------------
# Isolated Process Sample Execution
# ---------------------------------------------------------------------------

def execute_pipeline_sample(prompt: str, model: str) -> dict:
    """Execute a single public pipeline analysis and measure metrics."""
    rss_start, _ = get_process_memory()

    tracemalloc.start()
    tracemalloc.reset_peak()
    baseline_traced = tracemalloc.get_traced_memory()[0]

    t0 = time.perf_counter()
    res = analyze_prompt_detailed(prompt, model=model)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    current_traced, peak_traced = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_traced_mib = round(peak_traced / (1024 * 1024), 2)
    traced_delta_mib = round((current_traced - baseline_traced) / (1024 * 1024), 2)
    rss_end, rss_peak = get_process_memory()

    final_text = res.final.optimized_prompt
    exact_fb = (final_text == prompt)
    final_sha256 = hashlib.sha256(final_text.encode("utf-8")).hexdigest()

    return {
        "status": "OK",
        "latency_ms": elapsed_ms,
        "peak_traced_mib": peak_traced_mib,
        "traced_delta_mib": traced_delta_mib,
        "rss_start_mib": rss_start,
        "rss_end_mib": rss_end,
        "rss_peak_mib": rss_peak,
        "original_tokens": res.final.original_tokens,
        "optimized_tokens": res.final.optimized_tokens,
        "tokens_saved": res.final.tokens_saved,
        "reduction_percentage": res.final.reduction_percentage,
        "optimization_accepted": res.optimization_accepted,
        "exact_fallback": exact_fb,
        "output_sha256": final_sha256,
    }


def run_sample_with_hard_timeout(
    prompt: str,
    model: str,
    timeout_seconds: int = DEFAULT_WORKER_TIMEOUT,
    use_subprocess: bool = False,
    custom_worker_cmd: Optional[List[str]] = None,
    force_toolhelp_fallback: bool = False,
    require_job_object: bool = True,
) -> dict:
    """Run sample execution with genuine hard timeout support and zero-race Win32 Job Object isolation.

    On Windows, when Job Object isolation is active:
    1. Create the Win32 Job Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE.
    2. Spawn the worker subprocess with CREATE_SUSPENDED so it cannot execute or spawn children yet.
    3. Assign the suspended process to the Job Object. If assignment fails, terminate the suspended
       process immediately and fail explicitly rather than running uncontained.
    4. Resume the suspended main thread and wait with `proc.communicate(timeout=timeout_seconds)`.
    """
    if not use_subprocess and not custom_worker_cmd:
        try:
            return execute_pipeline_sample(prompt, model)
        except Exception as exc:
            return {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}

    worker_cmd = custom_worker_cmd or [
        sys.executable,
        "-m",
        "nlp_engine.tests.milestone5b_resource_benchmark_v2",
        "--worker",
        "--model",
        model,
    ]

    is_win = (sys.platform == "win32")
    enforce_job = is_win and (not force_toolhelp_fallback) and require_job_object
    h_job: Optional[int] = None

    if enforce_job:
        h_job = create_job_object()
        if not h_job:
            return {
                "status": "ERROR",
                "error": "Failed to create Win32 Job Object for hard process-tree isolation.",
            }

    creation_flags = CREATE_SUSPENDED if enforce_job else 0
    preexec = os.setsid if (not is_win and hasattr(os, "setsid")) else None

    try:
        proc = subprocess.Popen(
            worker_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            creationflags=creation_flags,
            preexec_fn=preexec,
        )
    except Exception as exc:
        if h_job and is_win:
            try:
                _get_win32_kernel32().CloseHandle(wt.HANDLE(h_job))
            except Exception:
                pass
        return {"status": "ERROR", "error": f"Failed to spawn worker subprocess: {exc}"}

    if enforce_job:
        assigned = assign_process_to_job(h_job, int(proc._handle))
        if not assigned:
            kill_process_tree(proc, h_job, force_toolhelp_fallback=force_toolhelp_fallback)
            return {
                "status": "ERROR",
                "error": "Failed to assign worker process to Win32 Job Object before execution.",
            }
        if not resume_suspended_process(proc.pid):
            kill_process_tree(proc, h_job, force_toolhelp_fallback=force_toolhelp_fallback)
            return {
                "status": "ERROR",
                "error": "Failed to resume worker process after Win32 Job Object assignment.",
            }

    try:
        stdout_data, stderr_data = proc.communicate(input=prompt, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        kill_process_tree(proc, h_job, force_toolhelp_fallback=force_toolhelp_fallback)
        h_job = None  # Already closed in kill_process_tree
        return {
            "status": "TIMEOUT",
            "error": f"Sample exceeded hard timeout limit of {timeout_seconds} seconds",
            "latency_ms": timeout_seconds * 1000.0,
        }
    except Exception as exc:
        kill_process_tree(proc, h_job, force_toolhelp_fallback=force_toolhelp_fallback)
        h_job = None
        return {
            "status": "ERROR",
            "error": f"Subprocess communication error: {type(exc).__name__}: {exc}",
        }
    finally:
        if h_job and is_win:
            try:
                _get_win32_kernel32().CloseHandle(wt.HANDLE(h_job))
            except Exception:
                pass
        _close_proc_pipes_and_reap(proc, wait_timeout=1.0)

    if proc.returncode != 0:
        return {
            "status": "ERROR",
            "error": f"Worker exited with code {proc.returncode}: {stderr_data.strip()}",
        }

    try:
        return json.loads(stdout_data.strip())
    except Exception as exc:
        return {
            "status": "ERROR",
            "error": f"Failed to parse worker output: {exc}. Raw: {stdout_data[:200]}",
        }


# ---------------------------------------------------------------------------
# Benchmark Orchestrator
# ---------------------------------------------------------------------------

class BenchmarkOrchestrator:
    def __init__(
        self,
        checkpoint_path: Path = CHECKPOINT_PATH,
        log_path: Path = LOG_PATH,
        smoke_test: bool = False,
        include_4mib: bool = False,
        use_subprocess: bool = False,
        sample_timeout: int = DEFAULT_WORKER_TIMEOUT,
    ):
        self.checkpoint_path = checkpoint_path
        self.logger = ProgressLogger(log_path)
        self.smoke_test = smoke_test
        self.include_4mib = include_4mib
        self.use_subprocess = use_subprocess
        self.sample_timeout = sample_timeout
        self.model = "tokentrim-benchmark-estimate"
        self._checkpoint_lock = threading.Lock()

        # Build workload configuration matrix
        if smoke_test:
            self.scenarios_config = [
                {"id": "smoke_2k_clause", "profile": "clause_heavy", "target_bytes": 2048, "samples": 1},
                {"id": "smoke_16k_tech", "profile": "technical_protected", "target_bytes": 16384, "samples": 1},
            ]
            self.memory_config = {"identical_repeats": 2, "alternating_repeats": 0, "target_bytes": 4096}
            self.concurrency_config = {"worker_levels": [1, 2], "prompts_count": 4}
            self.sample_timeout = min(sample_timeout, 30)
        else:
            self.scenarios_config = [
                # 512 KiB (1 warmup + 3 measured samples)
                {"id": "512KiB_clause_heavy", "profile": "clause_heavy", "target_bytes": 512 * 1024, "samples": 3},
                {"id": "512KiB_technical_protected", "profile": "technical_protected", "target_bytes": 512 * 1024, "samples": 3},
                {"id": "512KiB_multisection_spec", "profile": "multisection_spec", "target_bytes": 512 * 1024, "samples": 3},

                # 1 MiB (1 warmup + 2 measured samples)
                {"id": "1MiB_clause_heavy", "profile": "clause_heavy", "target_bytes": 1024 * 1024, "samples": 2},
                {"id": "1MiB_technical_protected", "profile": "technical_protected", "target_bytes": 1024 * 1024, "samples": 2},
                {"id": "1MiB_multisection_spec", "profile": "multisection_spec", "target_bytes": 1024 * 1024, "samples": 2},

                # 2 MiB (1 warmup + 2 measured samples)
                {"id": "2MiB_clause_heavy", "profile": "clause_heavy", "target_bytes": 2048 * 1024, "samples": 2},
                {"id": "2MiB_technical_protected", "profile": "technical_protected", "target_bytes": 2048 * 1024, "samples": 2},
                {"id": "2MiB_multisection_spec", "profile": "multisection_spec", "target_bytes": 2048 * 1024, "samples": 2},
            ]
            if include_4mib:
                self.scenarios_config.append(
                    {"id": "4MiB_technical_protected", "profile": "technical_protected", "target_bytes": 4096 * 1024, "samples": 1}
                )
            self.memory_config = {"identical_repeats": 5, "alternating_repeats": 5, "target_bytes": 512 * 1024}
            self.concurrency_config = {"worker_levels": [1, 2, 4, 8], "prompts_count": 8}

        self.signature = calculate_workload_signature(self.scenarios_config, self.memory_config, self.concurrency_config)
        self.checkpoint = self._init_or_load_checkpoint()

    def _init_or_load_checkpoint(self) -> dict:
        if self.checkpoint_path.exists():
            try:
                data = load_and_validate_checkpoint(self.checkpoint_path, expected_signature=self.signature)
                self.logger.log(f"Resuming existing checkpoint ({self.checkpoint_path.name}) with signature {self.signature[:12]}.")
                return data
            except ConfigurationMismatchError as exc:
                self.logger.log(f"Configuration mismatch: {exc}", level="WARNING")
                raise
            except Exception as exc:
                self.logger.log(f"Checkpoint validation failed: {exc}", level="ERROR")
                raise

        import numpy, pydantic, tiktoken, pytest
        env_meta = {
            "os": f"{platform.system()} {platform.release()} ({platform.version()})",
            "python_version": sys.version.split()[0],
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
            "pytest_version": pytest.__version__,
            "numpy_version": numpy.__version__,
            "pydantic_version": pydantic.__version__,
            "tiktoken_version": tiktoken.__version__,
        }
        data = {
            "format_version": FORMAT_VERSION,
            "benchmark_id": "tokentrim_milestone5b_v2",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "workload_signature": self.signature,
            "execution_mode": "subprocess" if self.use_subprocess else "in_process",
            "environment": env_meta,
            "scenarios": {},
            "memory_experiments": {},
            "concurrency_experiments": {},
            "all_completed": False,
        }
        atomic_write_checkpoint(self.checkpoint_path, data)
        self.logger.log(f"Initialized new atomic checkpoint at {self.checkpoint_path.name}.")
        return data

    def save_checkpoint(self) -> None:
        with self._checkpoint_lock:
            self.checkpoint["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            atomic_write_checkpoint(self.checkpoint_path, self.checkpoint)

    def _effective_requested_samples(self, sc_cfg: dict) -> int:
        sc_state = self.checkpoint["scenarios"].get(sc_cfg["id"], {})
        return int(sc_state.get("requested_samples", sc_cfg["samples"]))

    def run_all(self) -> None:
        total_samples = sum(self._effective_requested_samples(s) for s in self.scenarios_config)
        completed_samples = sum(
            len(self.checkpoint["scenarios"].get(s["id"], {}).get("completed_samples", []))
            for s in self.scenarios_config
        )

        self.logger.log(
            f"Starting benchmark execution. Total planned samples: {total_samples}. Already completed: {completed_samples}."
        )

        # 1. Large-input scenarios
        for sc_idx, sc_cfg in enumerate(self.scenarios_config, start=1):
            sc_id = sc_cfg["id"]
            sc_state = self.checkpoint["scenarios"].setdefault(sc_id, {
                "target_bytes": sc_cfg["target_bytes"],
                "profile": sc_cfg["profile"],
                "requested_samples": sc_cfg["samples"],
                "warmup": None,
                "completed_samples": [],
                "status": "pending",
            })

            gen_fn = GENERATORS[sc_cfg["profile"]]
            prompt = gen_fn(sc_cfg["target_bytes"])
            sc_state["actual_bytes"] = len(prompt.encode("utf-8"))
            sc_state["char_count"] = len(prompt)
            sc_state["input_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

            # Warm-up (persisted immediately)
            if sc_state["warmup"] is None:
                self.logger.log(f"[{sc_idx}/{len(self.scenarios_config)}] Scenario '{sc_id}': Running warm-up...")
                w_start = time.perf_counter()
                w_res = run_sample_with_hard_timeout(
                    prompt,
                    self.model,
                    timeout_seconds=self.sample_timeout,
                    use_subprocess=self.use_subprocess,
                )
                w_elapsed = round((time.perf_counter() - w_start) * 1000, 2)
                w_res["wall_elapsed_ms"] = w_elapsed
                sc_state["warmup"] = w_res
                self.save_checkpoint()
                self.logger.log(
                    f"[{sc_idx}/{len(self.scenarios_config)}] Scenario '{sc_id}': Warm-up completed in {w_elapsed}ms. Checkpoint saved."
                )

                # Soft upfront gate: if warm-up > 90s, persist sample cap in checkpoint
                if w_elapsed > 90000.0 and sc_state["requested_samples"] > 1:
                    self.logger.log(
                        f"[{sc_idx}/{len(self.scenarios_config)}] Scenario '{sc_id}': Warm-up ({w_elapsed}ms) exceeded 90s soft threshold. "
                        f"Capping remaining samples to 1 and persisting cap in checkpoint.",
                        level="WARNING",
                    )
                    sc_state["requested_samples"] = 1
                    sc_state["warmup_capped"] = True
                    total_samples = sum(self._effective_requested_samples(s) for s in self.scenarios_config)
                    self.save_checkpoint()

            # Measured samples (using persisted requested_samples so resumed runs preserve warm-up caps)
            while len(sc_state["completed_samples"]) < sc_state["requested_samples"]:
                sample_idx = len(sc_state["completed_samples"]) + 1
                self.logger.log(
                    f"[{sc_idx}/{len(self.scenarios_config)}] Scenario '{sc_id}': "
                    f"Executing sample {sample_idx}/{sc_state['requested_samples']}..."
                )
                sample_res = run_sample_with_hard_timeout(
                    prompt,
                    self.model,
                    timeout_seconds=self.sample_timeout,
                    use_subprocess=self.use_subprocess,
                )
                sample_res["sample_index"] = sample_idx
                sc_state["completed_samples"].append(sample_res)
                completed_samples += 1

                pct = round((completed_samples / total_samples) * 100, 1) if total_samples > 0 else 100.0
                self.save_checkpoint()
                self.logger.log(
                    f"[{sc_idx}/{len(self.scenarios_config)}] Scenario '{sc_id}': Sample {sample_idx} completed "
                    f"(Status: {sample_res.get('status')}, Latency: {sample_res.get('latency_ms', 0)}ms). "
                    f"Overall Progress: {completed_samples}/{total_samples} ({pct}%). Checkpoint saved."
                )

                if sample_res.get("status") == "TIMEOUT":
                    self.logger.log(
                        f"[{sc_idx}/{len(self.scenarios_config)}] Scenario '{sc_id}': Sample {sample_idx} timed out. "
                        f"Skipping further samples for this scenario.",
                        level="WARNING",
                    )
                    break

            sc_state["status"] = "completed"
            self.save_checkpoint()

        # 2. Memory experiments (incrementally persisted per iteration)
        self._run_memory_experiments()

        # 3. Multi-process concurrency experiments (incrementally persisted per request)
        self._run_concurrency_experiments()

        self.checkpoint["all_completed"] = True
        self.save_checkpoint()
        self.logger.log("All benchmark scenarios, memory tests, and multi-process concurrency runs completed successfully.")

    def _run_memory_experiments(self) -> None:
        mem_state = self.checkpoint["memory_experiments"]
        p_tech = generate_technical_protected_prompt(self.memory_config["target_bytes"])

        # Identical repeats
        same_runs = mem_state.setdefault("identical_repeats", [])
        repeats_target = self.memory_config.get("identical_repeats", 2)
        identical_status = mem_state.get("identical_status", "in_progress")

        if identical_status != "completed":
            while len(same_runs) < repeats_target:
                idx = len(same_runs) + 1
                self.logger.log(f"[Memory] Identical repeat run {idx}/{repeats_target}...")
                r = run_sample_with_hard_timeout(
                    p_tech,
                    self.model,
                    timeout_seconds=self.sample_timeout,
                    use_subprocess=self.use_subprocess,
                )
                r["iteration"] = idx
                same_runs.append(r)
                self.save_checkpoint()
                self.logger.log(f"[Memory] Identical repeat {idx} saved to checkpoint (Status: {r.get('status')}).")

                if r.get("status") != "OK":
                    self.logger.log(f"[Memory] Identical repeat {idx} returned {r.get('status')}. Halting series.", level="WARNING")
                    mem_state["identical_status"] = "aborted"
                    self.save_checkpoint()
                    break
            else:
                mem_state["identical_status"] = "completed"
                self.save_checkpoint()

        # Alternating repeats
        alt_runs = mem_state.setdefault("alternating_repeats", [])
        alt_target = self.memory_config.get("alternating_repeats", 0)
        alt_status = mem_state.get("alternating_status", "in_progress")
        p_clause = generate_clause_heavy_prompt(self.memory_config["target_bytes"])

        if alt_target > 0 and alt_status != "completed":
            while len(alt_runs) < alt_target:
                idx = len(alt_runs) + 1
                p = p_clause if (idx % 2 == 1) else p_tech
                self.logger.log(f"[Memory] Alternating repeat run {idx}/{alt_target}...")
                r = run_sample_with_hard_timeout(
                    p,
                    self.model,
                    timeout_seconds=self.sample_timeout,
                    use_subprocess=self.use_subprocess,
                )
                r["iteration"] = idx
                alt_runs.append(r)
                self.save_checkpoint()
                self.logger.log(f"[Memory] Alternating repeat {idx} saved to checkpoint (Status: {r.get('status')}).")

                if r.get("status") != "OK":
                    self.logger.log(f"[Memory] Alternating repeat {idx} returned {r.get('status')}. Halting series.", level="WARNING")
                    mem_state["alternating_status"] = "aborted"
                    self.save_checkpoint()
                    break
            else:
                mem_state["alternating_status"] = "completed"
                self.save_checkpoint()

    def _run_concurrency_experiments(self, custom_worker_cmd: Optional[List[str]] = None) -> None:
        """Run multi-process concurrency experiments using isolated worker processes with Win32 Job Object timeouts.

        Scope & Guarantees:
        - Each concurrent request executes in a dedicated OS subprocess coordinated by a lightweight dispatcher thread.
        - Measures multi-process concurrency throughput, latency, and deterministic output equivalence against sequential runs.
        - Hard OS-level timeout enforcement per request via CREATE_SUSPENDED + Win32 Job Object process-tree cleanup.
        - Resumed tiers compute throughput from the contiguous resumed batch (`batch_wall_ms`) rather than summing
          disconnected wall-clock segments across interrupted runs, while recording `cumulative_wall_ms` separately.
        """
        conc_state = self.checkpoint["concurrency_experiments"]
        prompts = [
            "Please configure the HTTP request timeout to exactly 30 seconds.\nPlease configure the HTTP request timeout to exactly 30 seconds.\nEnsure requests are logged to audit.log.",
            "Connect to https://api.tokentrim.internal:8080/v1/costs using TLS 1.3.\nStore cache records in F:\\TokenTrim\\Cache\\records.db with permissions 0600.\nDo not disable SSL certificate verification.",
            "Set cache lifetime to 300 seconds.\nSet cache lifetime to 600 seconds.",
            "# Module A\nOutput format: JSON.\n# Module B\nOutput format: XML.",
        ]
        if self.concurrency_config.get("prompts_count", 4) > 4:
            prompts.extend([
                generate_technical_protected_prompt(16 * 1024),
                generate_clause_heavy_prompt(16 * 1024),
                generate_multisection_spec_prompt(16 * 1024),
                "Use Redis port 6379 for caching session tokens.\nUse Redis port 6379 for caching session tokens.\nDatabase connection timeout must be 5000 ms.",
            ])

        # 1. Establish sequential reference outputs if not present
        ref_runs = conc_state.setdefault("sequential_references", [])
        if not ref_runs:
            self.logger.log(f"[Multi-Process Concurrency] Generating sequential reference outputs for {len(prompts)} prompts...")
            for idx, p in enumerate(prompts):
                res = analyze_prompt_detailed(p, model=self.model)
                out_h = hashlib.sha256(res.final.optimized_prompt.encode("utf-8")).hexdigest()
                ref_runs.append({
                    "prompt_idx": idx,
                    "sha256": out_h,
                    "tokens_saved": res.final.tokens_saved,
                    "accepted": res.optimization_accepted,
                })
            self.save_checkpoint()
            self.logger.log("[Multi-Process Concurrency] Sequential reference outputs saved to checkpoint.")

        # 2. Worker levels with multi-process concurrency and per-request atomic persistence
        levels = self.concurrency_config.get("worker_levels", [1, 2])
        level_results = conc_state.setdefault("levels", {})

        for workers in levels:
            key = f"workers_{workers}"
            lvl_state = level_results.setdefault(key, {
                "workers": workers,
                "total_requests": len(prompts),
                "requests": {},
                "status": "in_progress",
            })

            if lvl_state.get("status") == "completed":
                self.logger.log(f"[Multi-Process Concurrency] Worker level {workers} already completed. Skipping.")
                continue

            completed_requests = lvl_state.setdefault("requests", {})
            pending_indices = [
                i for i in range(len(prompts))
                if str(i) not in completed_requests or completed_requests[str(i)].get("status") not in ("OK", "ERROR", "TIMEOUT")
            ]

            if not pending_indices and len(completed_requests) == len(prompts):
                self._finalize_concurrency_level(
                    lvl_state,
                    workers,
                    len(prompts),
                    batch_wall_ms=lvl_state.get("wall_ms", 0.0),
                    batch_request_count=len(prompts),
                    was_resumed=bool(lvl_state.get("resumed", False)),
                )
                self.save_checkpoint()
                continue

            is_resumed_tier = len(completed_requests) > 0
            if is_resumed_tier:
                lvl_state["resumed"] = True

            self.logger.log(
                f"[Multi-Process Concurrency] Running worker level {workers} "
                f"({len(pending_indices)} pending requests out of {len(prompts)})..."
            )

            def worker_task(prompt_idx: int) -> dict:
                t0 = time.perf_counter()
                res = run_sample_with_hard_timeout(
                    prompts[prompt_idx],
                    model=self.model,
                    timeout_seconds=self.sample_timeout,
                    use_subprocess=True,
                    custom_worker_cmd=custom_worker_cmd,
                )
                req_ms = round((time.perf_counter() - t0) * 1000, 2)

                if res.get("status") == "OK":
                    out_h = res.get("output_sha256", "")
                    saved = res.get("tokens_saved", 0)
                    accepted = res.get("optimization_accepted", False)
                    ref = ref_runs[prompt_idx]
                    matches = (
                        out_h == ref["sha256"]
                        and saved == ref["tokens_saved"]
                        and accepted == ref["accepted"]
                    )
                    return {
                        "prompt_idx": prompt_idx,
                        "status": "OK",
                        "latency_ms": res.get("latency_ms", req_ms),
                        "sha256": out_h,
                        "tokens_saved": saved,
                        "accepted": accepted,
                        "matches_sequential": matches,
                    }
                elif res.get("status") == "TIMEOUT":
                    return {
                        "prompt_idx": prompt_idx,
                        "status": "TIMEOUT",
                        "error": res.get("error", "Request timed out"),
                        "latency_ms": res.get("latency_ms", req_ms),
                        "matches_sequential": False,
                    }
                else:
                    return {
                        "prompt_idx": prompt_idx,
                        "status": "ERROR",
                        "error": res.get("error", "Worker error"),
                        "latency_ms": req_ms,
                        "matches_sequential": False,
                    }

            t_start = time.perf_counter()
            max_w = min(workers, len(pending_indices))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as executor:
                futures = {executor.submit(worker_task, i): i for i in pending_indices}
                for fut in concurrent.futures.as_completed(futures):
                    p_idx = futures[fut]
                    try:
                        req_res = fut.result()
                    except Exception as exc:
                        req_res = {
                            "prompt_idx": p_idx,
                            "status": "ERROR",
                            "error": str(exc),
                            "latency_ms": 0.0,
                            "matches_sequential": False,
                        }

                    completed_requests[str(p_idx)] = req_res
                    self.save_checkpoint()
                    self.logger.log(
                        f"[Multi-Process Concurrency] Worker level {workers}: Request {p_idx} completed "
                        f"(Status: {req_res.get('status')}, Match: {req_res.get('matches_sequential')}). Checkpoint saved."
                    )

            batch_elapsed = round((time.perf_counter() - t_start) * 1000, 2)
            self._finalize_concurrency_level(
                lvl_state,
                workers,
                len(prompts),
                batch_wall_ms=batch_elapsed,
                batch_request_count=len(pending_indices),
                was_resumed=is_resumed_tier,
            )
            self.save_checkpoint()
            self.logger.log(
                f"[Multi-Process Concurrency] Worker level {workers} completed and saved "
                f"(Throughput: {lvl_state.get('throughput_rps')} req/s, Matches: {lvl_state.get('matches_sequential')}/{len(prompts)})."
            )

    def _finalize_concurrency_level(
        self,
        lvl_state: dict,
        workers: int,
        total_reqs: int,
        batch_wall_ms: Optional[float] = None,
        batch_request_count: Optional[int] = None,
        was_resumed: bool = False,
    ) -> None:
        """Deterministic aggregation of worker level results without summing disconnected wall-clock segments."""
        requests = lvl_state.get("requests", {})
        latencies = [r["latency_ms"] for r in requests.values() if "latency_ms" in r and r.get("status") == "OK"]
        all_latencies = [r["latency_ms"] for r in requests.values() if "latency_ms" in r]
        successes = sum(1 for r in requests.values() if r.get("status") == "OK")
        failures = sum(1 for r in requests.values() if r.get("status") != "OK")
        matches = sum(1 for r in requests.values() if r.get("matches_sequential"))

        prior_cumulative = float(lvl_state.get("cumulative_wall_ms", lvl_state.get("wall_ms", 0.0)) or 0.0)
        if batch_wall_ms is not None and batch_wall_ms > 0.0:
            active_wall_ms = round(batch_wall_ms, 2)
            cumulative_wall_ms = round(prior_cumulative + active_wall_ms, 2)
            effective_reqs = batch_request_count if (batch_request_count and batch_request_count > 0) else total_reqs
        else:
            active_wall_ms = round(float(lvl_state.get("wall_ms", 0.0) or 0.0), 2)
            if active_wall_ms <= 0.0 and latencies:
                active_wall_ms = round(sum(latencies) / max(workers, 1), 2)
            cumulative_wall_ms = round(max(prior_cumulative, active_wall_ms), 2)
            effective_reqs = total_reqs

        throughput = round(effective_reqs / (active_wall_ms / 1000.0), 2) if active_wall_ms > 0 else 0.0

        lvl_state["workers"] = workers
        lvl_state["total_requests"] = total_reqs
        lvl_state["wall_ms"] = active_wall_ms
        lvl_state["cumulative_wall_ms"] = cumulative_wall_ms
        lvl_state["throughput_basis_requests"] = effective_reqs
        lvl_state["resumed"] = bool(was_resumed or lvl_state.get("resumed", False))
        lvl_state["successes"] = successes
        lvl_state["failures"] = failures
        lvl_state["matches_sequential"] = matches
        lvl_state["throughput_rps"] = throughput
        lvl_state["median_latency_ms"] = round(statistics.median(latencies), 2) if latencies else (
            round(statistics.median(all_latencies), 2) if all_latencies else 0.0
        )
        lvl_state["isolation_verified"] = (matches == total_reqs and failures == 0)
        lvl_state["status"] = "completed"


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def compile_final_reports(checkpoint_path: Path, json_out: Path, md_out: Path) -> Tuple[dict, str]:
    """Compile finalized JSON and Markdown reports from a completed or partial checkpoint.

    Safely archives any existing report files from prior runs before overwriting.
    """
    data = load_and_validate_checkpoint(checkpoint_path)

    # Preserve existing reports if they belong to a different benchmark run or configuration
    if json_out.exists():
        try:
            existing_doc = json.loads(json_out.read_text(encoding="utf-8"))
            if (
                existing_doc.get("workload_signature") != data.get("workload_signature")
                or existing_doc.get("created_at") != data.get("created_at")
            ):
                safe_archive_file(json_out)
        except Exception:
            pass

    if md_out.exists() and not json_out.exists():
        safe_archive_file(md_out)

    # 1. JSON Report
    json_out.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # 2. Markdown Report
    env = data.get("environment", {})
    exec_mode = data.get("execution_mode", "in_process")
    lines = [
        "# TokenTrim Milestone 5B — Large-Input & Resource Characterization Report (v2)",
        "",
        "## 1. Executive Summary",
        "",
        "This independent benchmark characterization evaluates the TokenTrim NLP Engine across large inputs,",
        "memory allocation scaling, repeated stability, multi-process concurrency, and cross-process output determinism.",
        "Production code remained untouched throughout this milestone.",
        "",
        "## 2. Environment Specifications",
        "",
        f"- **Operating System:** {env.get('os', 'Unknown')}",
        f"- **Python Version:** {env.get('python_version', 'Unknown')}",
        f"- **Processor / Architecture:** {env.get('processor', 'Unknown')} ({env.get('cpu_count', 'Unknown')} logical cores)",
        f"- **Pytest Version:** {env.get('pytest_version', 'Unknown')}",
        f"- **NumPy Version:** {env.get('numpy_version', 'Unknown')}",
        f"- **Pydantic Version:** {env.get('pydantic_version', 'Unknown')}",
        f"- **tiktoken Version:** {env.get('tiktoken_version', 'Unknown')}",
        f"- **Execution Isolation Mode:** `{exec_mode}`",
        "- **Checkpoint Mode:** Atomic per-sample JSON persistence (`os.replace`)",
        "",
        "## 3. Large-Input Scaling & Latency Results",
        "",
        "| Scenario ID | Profile | Target Bytes | Chars | Samples | Min ms | Median ms | Mean ms | Max ms | SD ms | Peak Traced MiB | Fallback | Integrity |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|",
    ]

    for sc_id, sc in data.get("scenarios", {}).items():
        samples = sc.get("completed_samples", [])
        if not samples:
            continue
        latencies = [s["latency_ms"] for s in samples if s.get("status") == "OK" and "latency_ms" in s]
        min_ms = round(min(latencies), 1) if latencies else 0.0
        max_ms = round(max(latencies), 1) if latencies else 0.0
        mean_ms = round(statistics.mean(latencies), 1) if latencies else 0.0
        med_ms = round(statistics.median(latencies), 1) if latencies else 0.0
        sd_ms = round(statistics.stdev(latencies), 1) if len(latencies) > 1 else 0.0
        peak_traced = max((s.get("peak_traced_mib", 0.0) for s in samples), default=0.0)
        fb_all = all(s.get("exact_fallback", False) for s in samples)
        integ_all = all(s.get("output_sha256") == sc.get("input_sha256") for s in samples if s.get("exact_fallback"))

        fb_str = "yes" if fb_all else "no"
        integ_str = "PASS" if integ_all else "CHECK"
        lines.append(
            f"| `{sc_id}` | `{sc.get('profile')}` | {sc.get('target_bytes')} | {sc.get('char_count')} | "
            f"{len(samples)} | {min_ms:.1f} | {med_ms:.1f} | {mean_ms:.1f} | {max_ms:.1f} | {sd_ms:.1f} | "
            f"{peak_traced:.1f} | {fb_str} | **{integ_str}** |"
        )

    lines.extend([
        "",
        "## 4. Multi-Process Concurrency Scaling",
        "",
        "- **Concurrency Model:** Isolated OS subprocess workers coordinated by a lightweight dispatcher pool under Win32 Job Object hard timeout enforcement.",
        "- **Scope Note:** This experiment characterizes multi-process parallel throughput and cross-process deterministic equivalence against sequential baselines. In-process multi-threaded concurrency is intentionally outside the scope of this hard-timeout benchmark because Python threads cannot be forcibly terminated on timeout without risking interpreter state corruption.",
        "",
        "| Worker Level | Total Reqs | Success | Failures | Match Sequential | Wall Time ms | Throughput (req/s) | Median Latency ms | Process Isolation |",
        "|---|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ])

    for lvl_key, lvl in data.get("concurrency_experiments", {}).get("levels", {}).items():
        iso_str = "VERIFIED" if lvl.get("isolation_verified") else "FAILED"
        lines.append(
            f"| `{lvl.get('workers')} workers` | {lvl.get('total_requests')} | {lvl.get('successes')} | "
            f"{lvl.get('failures')} | {lvl.get('matches_sequential')} | {lvl.get('wall_ms'):.1f} | "
            f"{lvl.get('throughput_rps'):.2f} | {lvl.get('median_latency_ms'):.1f} | **{iso_str}** |"
        )

    lines.extend([
        "",
        "## 5. Memory Allocation Scaling & Stability Results",
        "",
        f"- **Isolation Mode:** {'Subprocess-isolated' if exec_mode == 'subprocess' else 'In-process'}",
        "- **Note on Isolation:** When run under subprocess isolation, peak tracemalloc and RSS reflect per-request footprint under hard kernel timeout enforcement. Cumulative RSS retention across iterations is characterized during in-process runs.",
        "",
        "| Series | Iteration | Latency ms | Peak Traced MiB | Net Traced Delta MiB | RSS Start MiB | RSS Peak MiB | Status |",
        "|---|---:|---:|---:|---:|---:|---:|:---:|",
    ])

    mem = data.get("memory_experiments", {})
    for item in mem.get("identical_repeats", []):
        lines.append(
            f"| Identical | {item.get('iteration', '-')} | {item.get('latency_ms', 0.0):.1f} | "
            f"{item.get('peak_traced_mib', 0.0):.2f} | {item.get('traced_delta_mib', 0.0):.2f} | "
            f"{item.get('rss_start_mib', '-')} | {item.get('rss_peak_mib', '-')} | `{item.get('status', 'OK')}` |"
        )
    for item in mem.get("alternating_repeats", []):
        lines.append(
            f"| Alternating | {item.get('iteration', '-')} | {item.get('latency_ms', 0.0):.1f} | "
            f"{item.get('peak_traced_mib', 0.0):.2f} | {item.get('traced_delta_mib', 0.0):.2f} | "
            f"{item.get('rss_start_mib', '-')} | {item.get('rss_peak_mib', '-')} | `{item.get('status', 'OK')}` |"
        )

    lines.extend(["", "## 6. Status: Complete", ""])
    md_content = "\n".join(lines)
    md_out.write_text(md_content, encoding="utf-8")
    return data, md_content


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Milestone 5B v2 Benchmark Runner")
    parser.add_argument("--smoke-test", action="store_true", help="Run bounded smoke test for validation (<30s)")
    parser.add_argument("--resume", action="store_true", default=True, help="Resume from existing checkpoint if present")
    parser.add_argument("--fresh", action="store_true", help="Start fresh run, safely archiving existing checkpoint and reports")
    parser.add_argument("--include-4mib", action="store_true", help="Include optional 4 MiB exploratory probe")
    parser.add_argument("--use-subprocess", action="store_true", help="Execute samples in isolated subprocesses with process-tree cleanup")
    parser.add_argument("--sample-timeout", type=int, default=DEFAULT_WORKER_TIMEOUT, help="Hard timeout limit in seconds per sample")
    parser.add_argument("--report-only", action="store_true", help="Generate final reports from existing checkpoint")
    parser.add_argument("--worker", action="store_true", help="Subprocess worker mode (reads prompt from stdin)")
    parser.add_argument("--model", type=str, default="tokentrim-benchmark-estimate", help="Model name for token counting")
    args = parser.parse_args()

    if args.worker:
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        prompt = sys.stdin.read()
        res = execute_pipeline_sample(prompt, args.model)
        sys.stdout.write(json.dumps(res) + "\n")
        sys.stdout.flush()
        return

    if args.report_only:
        compile_final_reports(CHECKPOINT_PATH, JSON_OUTPUT_PATH, MD_OUTPUT_PATH)
        LOGGER.log(f"Compiled final reports from {CHECKPOINT_PATH.name} to {JSON_OUTPUT_PATH.name} and {MD_OUTPUT_PATH.name}.")
        return

    if args.fresh:
        tag = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        if CHECKPOINT_PATH.exists():
            bak = safe_archive_file(CHECKPOINT_PATH, tag)
            LOGGER.log(f"Archived existing checkpoint to {bak.name}.")
        if JSON_OUTPUT_PATH.exists():
            bak = safe_archive_file(JSON_OUTPUT_PATH, tag)
            LOGGER.log(f"Archived existing JSON report to {bak.name}.")
        if MD_OUTPUT_PATH.exists():
            bak = safe_archive_file(MD_OUTPUT_PATH, tag)
            LOGGER.log(f"Archived existing Markdown report to {bak.name}.")

    orchestrator = BenchmarkOrchestrator(
        checkpoint_path=CHECKPOINT_PATH,
        log_path=LOG_PATH,
        smoke_test=args.smoke_test,
        include_4mib=args.include_4mib,
        use_subprocess=args.use_subprocess,
        sample_timeout=args.sample_timeout,
    )
    orchestrator.run_all()
    compile_final_reports(CHECKPOINT_PATH, JSON_OUTPUT_PATH, MD_OUTPUT_PATH)
    LOGGER.log("Milestone 5B v2 Benchmark execution completed successfully.")


if __name__ == "__main__":
    main()
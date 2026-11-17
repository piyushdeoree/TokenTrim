"""Controlled A/B verification for the Milestone 4 validator changes.

Run from the repository root with the project environment:

    python -m nlp_engine.tests.milestone4a_ab_benchmark

The runner creates isolated package copies under this tests directory, checks
that they differ only in validator.py, interleaves warm measurements, runs the
realistic evaluation and tests in the copies, then removes only its own unique
temporary workspace. Result artifacts use Milestone 4A-specific filenames.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parents[1]
ENGINE_DIR = REPO_ROOT / "nlp_engine"
BASELINE_PATH = TEST_DIR / "baselines" / "milestone4_pre_optimization_validator.py"
CONFIG_PATH = TEST_DIR / "performance_prompts.json"
RUNNER_PATH = TEST_DIR / "run_performance_benchmark.py"
RESULT_PATH = TEST_DIR / "milestone4a_ab_benchmark_results.json"
RAW_PATH = TEST_DIR / "milestone4a_ab_raw_samples.json"
REPORT_PATH = TEST_DIR / "milestone4a_ab_benchmark_results.md"
PROFILE_PATH = TEST_DIR / "milestone4a_ab_profile_results.md"
MODEL = "tokentrim-performance-estimate"
WARMUPS = 2
SAMPLE_COUNTS = {
    "small_2k": 20,
    "medium_16k": 20,
    "large_64k": 10,
    "very_large_256k": 5,
    "very_large_512k": 5,
}
STAGES = ("analysis", "optimization", "validation", "full_pipeline")
ABBA_ORDERS = (("A", "B"), ("B", "A"), ("B", "A"), ("A", "B"))
PACKAGE_VERSIONS = (
    "numpy", "scikit-learn", "nltk", "pydantic", "tiktoken", "pytest",
    "sentence-transformers", "torch", "transformers", "huggingface-hub",
    "tokenizers", "safetensors", "psutil",
)


WORKER_CODE = r'''
import cProfile, hashlib, json, os, pstats, re, socket, statistics, sys, time, tracemalloc

os.environ["TOKENTRIM_ENABLE_SEMANTIC_MODEL"] = "false"
os.environ["TOKENTRIM_SEMANTIC_DEVICE"] = "cpu"
original_connect = socket.socket.connect
def blocked_connect(_sock, _address):
    raise OSError("Network access disabled in Milestone 4A benchmark worker")
socket.socket.connect = blocked_connect

from nlp_engine import analyze_prompt_detailed, tokenizer_info
from nlp_engine.analyzer import build_analysis
from nlp_engine.optimizer import optimize_prompt
from nlp_engine.tests.run_performance_benchmark import build_prompt, load_config
from nlp_engine.tests.run_realistic_evaluation import evaluate_case, load_dataset
from nlp_engine.validator import validate_optimization

config = load_config()
analysis_cache = {}
candidate_cache = {}

def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def prepare(prompt):
    key = digest(prompt)
    if key not in analysis_cache:
        analysis = build_analysis(prompt, config["evaluation_model"])
        candidate = optimize_prompt(prompt, analysis)
        analysis_cache[key] = analysis
        candidate_cache[key] = candidate
    return key, analysis_cache[key], candidate_cache[key]

def quality_snapshot(result):
    return {
        "optimization_accepted": bool(result.optimization_accepted),
        "validation": result.validation.model_dump(mode="json"),
        "candidate": {
            "method": result.candidate.method,
            "tokens_saved": result.candidate.tokens_saved,
            "optimized_prompt_sha256": digest(result.candidate.optimized_prompt),
        },
        "final": {
            "method": result.final.method,
            "original_tokens": result.final.original_tokens,
            "optimized_tokens": result.final.optimized_tokens,
            "tokens_saved": result.final.tokens_saved,
            "reduction_percentage": result.final.reduction_percentage,
            "changes": list(result.final.changes),
        },
        "final_prompt_sha256": digest(result.final.optimized_prompt),
    }

def call_stage(stage, prompt, key, analysis, candidate):
    if stage == "analysis":
        output = build_analysis(prompt, config["evaluation_model"])
        return {"instruction_count": output.features.instruction_count,
                "constraint_count": output.features.constraint_count,
                "prepared_segment_count": len(output.prepared.segments)}
    if stage == "optimization":
        output = optimize_prompt(prompt, analysis)
        return {"method": output.method, "tokens_saved": output.tokens_saved,
                "optimized_prompt_sha256": digest(output.optimized_prompt)}
    if stage == "validation":
        output = validate_optimization(prompt, candidate.optimized_prompt)
        return output.model_dump(mode="json")
    if stage == "full_pipeline":
        return quality_snapshot(analyze_prompt_detailed(
            prompt, model=config["evaluation_model"]))
    raise ValueError("Unknown benchmark stage: " + stage)

print(json.dumps({"ready": True,
                  "tokenizer": tokenizer_info(config["evaluation_model"]).__dict__},
                 ensure_ascii=True), flush=True)

for line in sys.stdin:
    try:
        request = json.loads(line)
        action = request["action"]
        if action == "quit":
            print(json.dumps({"ok": True}), flush=True)
            break
        if action == "evaluate":
            rows = [evaluate_case(case) for case in load_dataset()]
            response = {"rows": rows}
        else:
            prompt = request["prompt"]
            key, analysis, candidate = prepare(prompt)
            if action == "prepare":
                response = {
                    "prompt_sha256": key,
                    "candidate_sha256": digest(candidate.optimized_prompt),
                    "candidate_method": candidate.method,
                    "candidate_tokens_saved": candidate.tokens_saved,
                    "candidate_prompt": candidate.optimized_prompt,
                    "tokenizer": tokenizer_info(config["evaluation_model"]).__dict__,
                }
            elif action == "call":
                started = time.perf_counter()
                output = call_stage(request["stage"], prompt, key, analysis, candidate)
                response = {"duration_ms": (time.perf_counter() - started) * 1000,
                            "output": output}
            elif action == "memory":
                stage = request["stage"]
                tracemalloc.start()
                before_current, _ = tracemalloc.get_traced_memory()
                output = call_stage(stage, prompt, key, analysis, candidate)
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                response = {
                    "stage": stage,
                    "current_before_bytes": before_current,
                    "current_after_bytes": current,
                    "current_delta_bytes": current - before_current,
                    "peak_traced_bytes": peak,
                    "incremental_peak_bytes": max(0, peak - before_current),
                    "output": output,
                }
            elif action == "profile":
                profiler = cProfile.Profile()
                profiler.enable()
                output = validate_optimization(prompt, candidate.optimized_prompt)
                profiler.disable()
                stats = pstats.Stats(profiler)
                functions = []
                for (filename, lineno, name), values in sorted(
                    stats.stats.items(), key=lambda item: item[1][3], reverse=True
                ):
                    if "nlp_engine" not in filename.replace("\\", "/"):
                        continue
                    primitive_calls, calls, self_seconds, cumulative_seconds, _ = values
                    functions.append({
                        "function": name,
                        "filename": os.path.basename(filename),
                        "line": lineno,
                        "calls": calls,
                        "primitive_calls": primitive_calls,
                        "self_seconds": self_seconds,
                        "cumulative_seconds": cumulative_seconds,
                    })
                    if len(functions) == 25:
                        break
                response = {
                    "total_calls": stats.total_calls,
                    "primitive_calls": stats.prim_calls,
                    "total_profile_seconds": stats.total_tt,
                    "validation": output.model_dump(mode="json"),
                    "top_nlp_engine_functions": functions,
                }
            else:
                raise ValueError("Unknown worker action: " + str(action))
        print(json.dumps(response, ensure_ascii=True, separators=(",", ":")), flush=True)
    except Exception as exc:
        print(json.dumps({"worker_error": type(exc).__name__ + ": " + str(exc)},
                         ensure_ascii=True), flush=True)
'''


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def controlled_environment(package_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(package_root),
        "PYTHONHASHSEED": "0",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "TOKENTRIM_ENABLE_SEMANTIC_MODEL": "false",
        "TOKENTRIM_SEMANTIC_DEVICE": "cpu",
        "CUDA_VISIBLE_DEVICES": "",
        "NVIDIA_VISIBLE_DEVICES": "",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
    })
    env.pop("TOKENTRIM_SEMANTIC_MODEL", None)
    return env


def package_files(package_root: Path) -> dict[str, str]:
    return {
        path.relative_to(package_root).as_posix(): sha256_file(path)
        for path in sorted(package_root.rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
    }


def make_isolated_copies(work_root: Path) -> tuple[dict[str, Path], dict[str, Any]]:
    versions: dict[str, Path] = {}
    for version in ("A", "B"):
        version_root = work_root / version
        package_dest = version_root / "nlp_engine"

        def ignore(directory: str, names: list[str]) -> set[str]:
            ignored = {name for name in names if name in {"__pycache__", ".pytest_cache"}}
            if Path(directory).resolve() == (ENGINE_DIR / "tests").resolve():
                ignored.update(name for name in names if name.startswith(".milestone4a_ab_"))
            return ignored

        shutil.copytree(ENGINE_DIR, package_dest, ignore=ignore)
        if version == "A":
            shutil.copyfile(BASELINE_PATH, package_dest / "validator.py")
        versions[version] = version_root

    files_a = package_files(versions["A"] / "nlp_engine")
    files_b = package_files(versions["B"] / "nlp_engine")
    all_paths = sorted(set(files_a) | set(files_b))
    differences = [
        {"path": path, "A": files_a.get(path), "B": files_b.get(path)}
        for path in all_paths
        if files_a.get(path) != files_b.get(path)
    ]
    differing_paths = [item["path"] for item in differences]
    if differing_paths != ["validator.py"]:
        raise RuntimeError(
            "Isolated versions differ outside validator.py: "
            + json.dumps(differing_paths)
        )

    return versions, {
        "differing_files": differences,
        "A_file_count": len(files_a),
        "B_file_count": len(files_b),
        "A_validator_sha256": sha256_file(versions["A"] / "nlp_engine" / "validator.py"),
        "B_validator_sha256": sha256_file(versions["B"] / "nlp_engine" / "validator.py"),
        "identical_except_validator": True,
    }


class Worker:
    def __init__(self, version: str, root: Path, env: dict[str, str]):
        self.version = version
        self.root = root
        self.process = subprocess.Popen(
            [sys.executable, "-u", "-c", WORKER_CODE],
            cwd=root,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        ready_line = self.process.stdout.readline() if self.process.stdout else ""
        if not ready_line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"Version {version} worker failed to start: {stderr}")
        self.ready = json.loads(ready_line)
        if not self.ready.get("ready"):
            raise RuntimeError(f"Version {version} worker did not become ready: {ready_line}")

    def request(self, request: dict[str, Any]) -> dict[str, Any]:
        if not self.process.stdin or not self.process.stdout:
            raise RuntimeError("Worker pipes are unavailable")
        self.process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"Version {self.version} worker exited: {stderr}")
        result = json.loads(line)
        if "worker_error" in result:
            raise RuntimeError(f"Version {self.version}: {result['worker_error']}")
        return result

    def close(self) -> None:
        if self.process.poll() is None:
            try:
                self.request({"action": "quit"})
            except Exception:
                self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=10)
        if self.process.stderr:
            self.process.stderr.close()
        if self.process.stdout:
            self.process.stdout.close()
        if self.process.stdin:
            self.process.stdin.close()


def describe_environment() -> dict[str, Any]:
    packages: dict[str, str] = {}
    for name in PACKAGE_VERSIONS:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "not installed"

    try:
        import psutil
        rss_available = True
        cpu_model = platform.processor()
        physical_cpus = psutil.cpu_count(logical=False)
    except Exception:
        rss_available = False
        cpu_model = platform.processor()
        physical_cpus = None

    return {
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "platform": platform.platform(),
        "os": platform.system(),
        "cpu_model": cpu_model,
        "logical_cpus": os.cpu_count(),
        "physical_cpus": physical_cpus,
        "packages": packages,
        "psutil_available": rss_available,
        "semantic_model_enabled": False,
        "semantic_model_dependencies_available": {
            name: packages[name]
            for name in ("sentence-transformers", "torch", "transformers")
        },
        "environment": {
            "PYTHONHASHSEED": "0",
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "TOKENTRIM_ENABLE_SEMANTIC_MODEL": "false",
            "TOKENTRIM_SEMANTIC_DEVICE": "cpu",
            "TOKENTRIM_SEMANTIC_MODEL": "unset",
            "CUDA_VISIBLE_DEVICES": "",
            "NVIDIA_VISIBLE_DEVICES": "",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
        },
    }


def summarize(samples: list[float]) -> dict[str, Any]:
    ordered = sorted(samples)
    return {
        "samples": len(samples),
        "min_ms": min(samples) if samples else None,
        "median_ms": statistics.median(samples) if samples else None,
        "mean_ms": statistics.mean(samples) if samples else None,
        "max_ms": max(samples) if samples else None,
        "p95_ms": ordered[math.ceil(0.95 * len(ordered)) - 1] if len(samples) >= 20 else None,
        "sample_stddev_ms": statistics.stdev(samples) if len(samples) > 1 else None,
        "samples_ms": samples,
    }


def compare_summaries(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    a_value = a["median_ms"]
    b_value = b["median_ms"]
    delta = b_value - a_value
    return {
        "A_median_ms": a_value,
        "B_median_ms": b_value,
        "latency_change_ms_B_minus_A": delta,
        "latency_change_percent": (delta / a_value * 100) if a_value else None,
        "speedup_A_over_B": (a_value / b_value) if b_value else None,
    }


def eval_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": len(rows),
        "expected_behavior_counts": {
            key: sum(row["expected_behavior"] == key for row in rows)
            for key in sorted({row["expected_behavior"] for row in rows})
        },
        "matched_expectations": sum(bool(row["behavior_correct"]) for row in rows),
        "optimizations_accepted": sum(bool(row["optimization_accepted"]) for row in rows),
        "unchanged_prompts": sum(row["actual_behavior"] == "left_unchanged" for row in rows),
        "unsafe_candidates_rejected": sum(
            row["actual_behavior"] == "unsafe_candidate_rejected" for row in rows
        ),
        "false_removals": sum(bool(row["false_removal"]) for row in rows),
        "unexpected_optimizations": sum(bool(row["unexpected_optimization"]) for row in rows),
        "missed_opportunities": sum(bool(row["missed_opportunity"]) for row in rows),
        "exceptions": sum(row.get("exception") is not None for row in rows),
        "estimated_tokens_saved": sum(row.get("tokens_saved") or 0 for row in rows),
    }


def run_tests(version: str, root: Path, env: dict[str, str]) -> dict[str, Any]:
    command = [sys.executable, "-m", "pytest", "nlp_engine/tests", "-v"]
    if version == "A":
        # This module directly imports the Milestone 4 private helper, which
        # does not exist in the historical source. The remaining suite is run
        # unchanged against A; B runs the complete current suite.
        command.append("--ignore=nlp_engine/tests/test_validator_performance_reuse.py")
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )
    output = completed.stdout + completed.stderr
    summary_match = re.search(r"=+\s*(\d+ passed[^\n=]*|[^\n]*\d+ failed[^\n=]*)\s*=+", output)
    return {
        "command": command,
        "return_code": completed.returncode,
        "duration_seconds": time.perf_counter() - started,
        "summary": summary_match.group(1).strip() if summary_match else None,
        "output_tail": output[-6000:],
        "baseline_specific_tests_excluded": version == "A",
    }


def run_realistic_runner(version: str, root: Path, env: dict[str, str]) -> dict[str, Any]:
    command = [sys.executable, "-m", "nlp_engine.tests.run_realistic_evaluation"]
    completed = subprocess.run(
        command,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )
    return {
        "command": command,
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def markdown_report(data: dict[str, Any], raw_filename: str, profile_filename: str) -> str:
    lines = [
        "# Milestone 4A Controlled A/B Benchmark",
        "",
        "## Executive summary",
        "",
        "The benchmark compares the recovered pre-Milestone-4 validator (A) with the current optimized validator (B). Both isolated engine copies were verified identical except for `nlp_engine/validator.py`. No performance conclusion is inferred until the reported samples and functional checks are considered together.",
        "",
        "## Sources and isolation",
        "",
        f"- A source: `{data['source']['baseline_path']}`",
        f"- B source: `{data['source']['current_path']}`",
        f"- A validator SHA-256: `{data['source']['A_validator_sha256']}`",
        f"- B validator SHA-256: `{data['source']['B_validator_sha256']}`",
        f"- Other copied files: identical (`{data['source']['identical_except_validator']}`); file count per copy: {data['source']['A_file_count']}",
        f"- Measurement harness SHA-256: `{data['source']['measurement_harness_sha256']}`",
        f"- Prompt configuration SHA-256: `{data['source']['prompt_config_sha256']}`",
        "- Temporary A/B copies were created under `nlp_engine/tests/` and removed after the run.",
        "",
        "## Environment",
        "",
        f"- Python: `{data['environment']['python'].splitlines()[0]}`",
        f"- Executable: `{data['environment']['python_executable']}`",
        f"- Platform: `{data['environment']['platform']}`",
        f"- CPU: `{data['environment']['cpu_model']}`; logical processors: {data['environment']['logical_cpus']}; physical: {data['environment']['physical_cpus']}",
        f"- Packages: `{json.dumps(data['environment']['packages'], sort_keys=True)}`",
        "- Semantic model disabled; no model or provider calls; socket connections blocked in benchmark workers.",
        f"- Tokenizer: `{json.dumps(data['tokenizer'], sort_keys=True)}` (unknown model, heuristic estimate).",
        f"- Environment controls: `{json.dumps(data['environment']['environment'], sort_keys=True)}`",
        "",
        "## Methodology",
        "",
        "- Inputs are generated by the existing `performance_prompts.json` and `build_prompt()`; SHA-256 is recorded for every prompt.",
        "- Two resident workers use the same interpreter and installed packages, with independent processes and isolated package roots.",
        "- Each worker receives two warm-up calls per stage and prompt. Measured runs are interleaved in repeating ABBA order.",
        "- Each repetition measures analysis, optimization, validation, and full pipeline separately. Memory uses a separate traced call to avoid contaminating latency.",
        "- Samples per version were 20 at 2K and 16K, 10 at 64K, and 5 at 256K and 512K. The large-prompt cases required several minutes even at five repetitions; p95 is omitted below 20 samples.",
        "- Cold import was omitted; it is unrelated to warm validation and process-start measurements would add machine/file-cache noise.",
        "- p95 is shown only for 20 or more samples. For smaller sample counts, p95 is omitted. No statistical significance claim is made.",
        "",
        "## Timing results",
        "",
        "Latency change is `(B - A) / A * 100`; negative means B is faster. Speedup is `A / B`.",
        "",
        "| Prompt | Stage | Version | n | Min ms | Median ms | Mean ms | Max ms | Std dev ms | p95 ms |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for prompt_id, prompt_result in data["timings"].items():
        for stage, stage_result in prompt_result["stages"].items():
            show = lambda value: "—" if value is None else f"{value:.3f}"
            for version in ("A", "B"):
                stats = stage_result[version]
                lines.append(
                    f"| {prompt_result['prompt_characters']:,} chars | {stage} | {version} | "
                    f"{stats['samples']} | {show(stats['min_ms'])} | {show(stats['median_ms'])} | "
                    f"{show(stats['mean_ms'])} | {show(stats['max_ms'])} | "
                    f"{show(stats['sample_stddev_ms'])} | {show(stats['p95_ms'])} |"
                )
    lines.extend([
        "",
        "### A/B median comparison",
        "",
        "| Prompt | Stage | A median ms | B median ms | Change ms | Change % | A/B speedup |",
        "|---|---|---:|---:|---:|---:|---:|",
    ])
    for prompt_id, prompt_result in data["timings"].items():
        for stage, stage_result in prompt_result["stages"].items():
            comparison = stage_result["comparison"]
            show = lambda value: "—" if value is None else f"{value:.3f}"
            lines.append(
                f"| {prompt_result['prompt_characters']:,} chars | {stage} | "
                f"{show(comparison['A_median_ms'])} | {show(comparison['B_median_ms'])} | "
                f"{show(comparison['latency_change_ms_B_minus_A'])} | "
                f"{show(comparison['latency_change_percent'])}% | "
                f"{show(comparison['speedup_A_over_B'])} |"
            )
    lines.extend(["", "Raw individual samples are preserved in the raw JSON artifact.", "", "## Memory"])
    lines.extend([
        "",
        "Traced memory was measured separately for validation and full pipeline. `incremental_peak_bytes` is the traced peak above the current allocation at the start of that call. RSS is unavailable when psutil is not installed.",
        "",
        "| Prompt | Stage | A peak bytes | B peak bytes | Difference bytes | Difference % | RSS |",
        "|---|---|---:|---:|---:|---:|---|",
    ])
    for prompt_id, record in data["memory"].items():
        for stage in ("validation", "full_pipeline"):
            a = record["A"][stage]["incremental_peak_bytes"]
            b = record["B"][stage]["incremental_peak_bytes"]
            difference = b - a
            pct = difference / a * 100 if a else None
            lines.append(f"| {record['prompt_characters']:,} chars | {stage} | {a} | {b} | {difference} | {pct:.2f}% | unavailable |" if pct is not None else f"| {record['prompt_characters']:,} chars | {stage} | {a} | {b} | {difference} | — | unavailable |")
    lines.extend([
        "",
        "## Functional equivalence",
        "",
        f"- Performance prompt validation results equivalent: `{data['functional']['performance_prompts_equivalent']}`.",
        f"- Candidate text hashes equivalent: `{data['functional']['candidate_hashes_equivalent']}`.",
        f"- Detailed realistic evaluation rows equivalent: `{data['functional']['realistic_rows_equivalent']}`; differing rows: {len(data['functional']['realistic_differences'])}.",
        f"- Measured performance-stage outputs equivalent: `{json.dumps(data['functional'].get('performance_stage_equivalence', {}), sort_keys=True)}`.",
        f"- Version A evaluation: `{json.dumps(data['evaluations']['A']['summary'], sort_keys=True)}`.",
        f"- Version B evaluation: `{json.dumps(data['evaluations']['B']['summary'], sort_keys=True)}`.",
        "- Complete per-case and validation results are preserved in raw JSON.",
        "",
        "## Test results",
        "",
        f"- A standard full-suite collection: `{data['tests']['A_standard']['summary'] or 'failed to collect'}` (return code {data['tests']['A_standard']['return_code']}). The current Milestone 4 reuse test imports a private helper absent from the historical baseline.",
        f"- A baseline-compatible suite excluding that B-specific module: `{data['tests']['A_compatible']['summary'] or 'see output'}` (return code {data['tests']['A_compatible']['return_code']}).",
        f"- B full suite: `{data['tests']['B']['summary'] or 'see output'}` (return code {data['tests']['B']['return_code']}).",
        "- Both isolated copies ran the existing realistic evaluation module; results and report outputs are in the raw data.",
        "",
        "## Profiling",
        "",
        f"See [{profile_filename}]({profile_filename}) for separate cProfile results at 64K and 512K. Profile time is not compared to ordinary latency.",
        "",
        "## Limitations and verdict",
        "",
        f"- Verdict: **{data['verdict']}**.",
        "- Profile and latency measurements are specific to this local machine and Python environment.",
        "- p95 is descriptive only for the 20-sample cases; smaller groups do not report p95.",
        "- The benchmark ran without intentionally concurrent CPU-heavy work, but unrelated operating-system background load was not instrumented.",
        "- RSS and cold-import comparisons were not performed. Traced Python memory does not include native allocations.",
        "- No validation threshold or production behavior was changed.",
        "",
        f"Raw samples and environment/source metadata: [{raw_filename}]({raw_filename}).",
        "",
    ])
    return "\n".join(lines)


def profile_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# Milestone 4A Validation Profiling",
        "",
        "Profiles are separate from warm latency measurements. cProfile instrumentation increases execution time; use these results to locate work, not to claim user-facing latency changes.",
        "",
        f"A validator SHA-256: `{data['source']['A_validator_sha256']}`  ",
        f"B validator SHA-256: `{data['source']['B_validator_sha256']}`",
        "",
    ]
    for size, pair in data["profiles"].items():
        lines.extend([f"## {size}", ""])
        for version in ("A", "B"):
            profile = pair[version]
            lines.extend([
                f"### Version {version}",
                "",
                f"- Total calls: {profile['total_calls']:,}; primitive calls: {profile['primitive_calls']:,}.",
                f"- Total profiled validation time: {profile['total_profile_seconds']:.3f}s.",
                "",
                "| Function | Calls | Self seconds | Cumulative seconds | Source |",
                "|---|---:|---:|---:|---|",
            ])
            for item in profile["top_nlp_engine_functions"][:15]:
                source = f"{Path(item['filename']).name}:{item['line']}"
                lines.append(f"| `{item['function']}` | {item['calls']} | {item['self_seconds']:.4f} | {item['cumulative_seconds']:.4f} | `{source}` |")
            lines.append("")
    lines.extend([
        "## Interpretation",
        "",
        "Compare call counts and cumulative time only within matching prompt size and the same environment. The earlier implementation should segment the optimized prompt again in entity extraction and recompute candidate features per original constraint; the optimized implementation should avoid those repeated operations. A reduction in those calls is not by itself evidence of lower wall latency.",
        "",
    ])
    return "\n".join(lines)


def complete_existing_results() -> None:
    """Collect the separate A/B profiles and finish saved run artifacts."""
    if not RESULT_PATH.is_file() or not RAW_PATH.is_file():
        raise FileNotFoundError("Completed A/B timing and raw-sample JSON files are required")
    if REPORT_PATH.exists() or PROFILE_PATH.exists():
        raise FileExistsError("Refusing to overwrite an existing Milestone 4A report")

    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    raw_samples = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    expected_a = sha256_file(BASELINE_PATH)
    expected_b = sha256_file(ENGINE_DIR / "validator.py")
    if result["source"]["A_validator_sha256"] != expected_a:
        raise RuntimeError("Saved A results do not use the preserved baseline currently on disk")
    if result["source"]["B_validator_sha256"] != expected_b:
        raise RuntimeError("Saved B results do not use the current validator currently on disk")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    from nlp_engine.tests.run_performance_benchmark import build_prompt

    selected = {item["id"]: item for item in config["size_scenarios"]}
    prompts = {
        prompt_id: build_prompt(config, selected[prompt_id])
        for prompt_id in ("large_64k", "very_large_512k")
    }
    profiles: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(prefix=".milestone4a_ab_profiles_", dir=TEST_DIR) as temporary:
        versions, isolation = make_isolated_copies(Path(temporary))
        if isolation["A_validator_sha256"] != expected_a or isolation["B_validator_sha256"] != expected_b:
            raise RuntimeError("Profile copies do not match the measured A/B sources")
        workers = {
            version: Worker(version, versions[version], controlled_environment(versions[version]))
            for version in ("A", "B")
        }
        try:
            for prompt_id, prompt in prompts.items():
                profiles[prompt_id] = {}
                order = ABBA_ORDERS[0 if prompt_id == "large_64k" else 1]
                for version in order:
                    workers[version].request({"action": "prepare", "prompt": prompt})
                    workers[version].request({
                        "action": "call", "prompt": prompt, "stage": "validation"
                    })
                    profiles[prompt_id][version] = workers[version].request({
                        "action": "profile", "prompt": prompt
                    })
        finally:
            for worker in workers.values():
                worker.close()

    result["source"].update(result.get("isolation", {}))
    result["profiles"] = profiles
    result["verdict"] = "genuine improvement" if (
        result["functional"]["performance_prompts_equivalent"]
        and result["functional"]["candidate_hashes_equivalent"]
        and result["functional"]["realistic_rows_equivalent"]
        and all(
            result["timings"][prompt_id]["stages"][stage]["comparison"]["latency_change_percent"] < 0
            for prompt_id in result["timings"]
            for stage in ("validation", "full_pipeline")
        )
    ) else "mixed results"
    raw_samples["isolation"] = result.get("isolation")
    raw_samples["profiles"] = profiles
    stage_equivalence = {}
    for stage in STAGES:
        compared = [
            (prompt_id, left, right)
            for prompt_id, versions_data in raw_samples["samples"].items()
            for left, right in zip(
                versions_data["A"][stage],
                versions_data["B"][stage],
            )
        ]
        different = [
            {"prompt_id": prompt_id, "iteration": left["iteration"]}
            for prompt_id, left, right in compared
            if left["output"] != right["output"]
        ]
        stage_equivalence[stage] = {
            "compared_samples": len(compared),
            "identical_outputs": not different,
            "different_outputs": different,
        }
    result["functional"]["performance_stage_equivalence"] = stage_equivalence

    report_data = dict(result)
    report_data["tests"] = {
        key: test
        for version_tests in result["tests"].values()
        for key, test in version_tests.items()
    }

    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    RAW_PATH.write_text(json.dumps(raw_samples, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(
        markdown_report(report_data, RAW_PATH.name, PROFILE_PATH.name), encoding="utf-8"
    )
    PROFILE_PATH.write_text(profile_markdown(result), encoding="utf-8")
    print(f"Results: {RESULT_PATH}")
    print(f"Raw samples: {RAW_PATH}")
    print(f"Profile report: {PROFILE_PATH}")
    print(f"Summary report: {REPORT_PATH}")
    print(f"Verdict: {result['verdict']}")


def main() -> None:
    for path in (RESULT_PATH, RAW_PATH, REPORT_PATH, PROFILE_PATH):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing Milestone 4A artifact: {path}")
    if not BASELINE_PATH.is_file():
        raise FileNotFoundError(f"Verified historical source is missing: {BASELINE_PATH}")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    from nlp_engine.tests.run_performance_benchmark import build_prompt

    scenarios = {item["id"]: item for item in config["size_scenarios"]}
    prompts = {
        scenario_id: build_prompt(config, scenarios[scenario_id])
        for scenario_id in SAMPLE_COUNTS
    }
    prompt_hashes = {key: sha256_bytes(value.encode("utf-8")) for key, value in prompts.items()}
    environment = describe_environment()
    environment["tokenizer"] = None

    raw: dict[str, Any] = {
        "format_version": 1,
        "status": "in_progress",
        "created_at_local": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "environment": environment,
        "source": {
            "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True).stdout.strip(),
            "A_validator_sha256": sha256_file(BASELINE_PATH),
            "B_validator_sha256": sha256_file(ENGINE_DIR / "validator.py"),
            "baseline_path": str(BASELINE_PATH),
            "current_path": str(ENGINE_DIR / "validator.py"),
            "harness_sha256": sha256_file(Path(__file__)),
            "prompt_config_sha256": sha256_file(CONFIG_PATH),
            "tokenizer_source_sha256": sha256_file(ENGINE_DIR / "tokenizer.py"),
        },
        "configuration": {
            "sample_counts_per_version": SAMPLE_COUNTS,
            "warmup_calls_per_stage": WARMUPS,
            "measurement_order": [list(order) for order in ABBA_ORDERS],
            "stages": list(STAGES),
            "semantic_model_enabled": False,
            "cold_import_measured": False,
            "psutil_rss_measured": False,
        },
        "prompts": {
            key: {"characters": len(text), "sha256": prompt_hashes[key]}
            for key, text in prompts.items()
        },
        "isolation": None,
        "tokenizer": None,
        "timings": {},
        "memory": {},
        "profiles": {},
        "evaluations": {},
        "tests": {},
        "functional": {},
        "verdict": "pending",
    }

    # Create each copy in a unique temporary directory beneath the approved
    # tests artifact tree. TemporaryDirectory cleans up only this new folder.
    with tempfile.TemporaryDirectory(prefix=".milestone4a_ab_", dir=TEST_DIR) as temporary:
        work_root = Path(temporary)
        versions, isolation = make_isolated_copies(work_root)
        raw["isolation"] = isolation
        workers: dict[str, Worker] = {}
        envs = {version: controlled_environment(root) for version, root in versions.items()}

        try:
            for version in ("A", "B"):
                workers[version] = Worker(version, versions[version], envs[version])
            raw["worker_ready"] = {version: workers[version].ready for version in workers}
            raw["tokenizer"] = workers["A"].ready["tokenizer"]
            if workers["A"].ready["tokenizer"] != workers["B"].ready["tokenizer"]:
                raise RuntimeError("A/B tokenizer metadata differs")

            prepared: dict[str, dict[str, dict[str, Any]]] = {"A": {}, "B": {}}
            for prompt_id, prompt in prompts.items():
                for version in ("A", "B"):
                    prepared[version][prompt_id] = workers[version].request({"action": "prepare", "prompt": prompt})
                if prepared["A"][prompt_id]["candidate_sha256"] != prepared["B"][prompt_id]["candidate_sha256"]:
                    raise RuntimeError(f"Optimization candidates differ for {prompt_id}")

            for prompt_id, prompt in prompts.items():
                print(f"[{prompt_id}] warming and measuring {SAMPLE_COUNTS[prompt_id]} samples per version", flush=True)
                raw["timings"][prompt_id] = {"prompt_characters": len(prompt)}
                samples: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {
                    version: {stage: [] for stage in STAGES}
                    for version in ("A", "B")
                }

                for version in ("A", "B"):
                    for stage in STAGES:
                        for _ in range(WARMUPS):
                            workers[version].request({"action": "call", "prompt": prompt, "stage": stage})

                for iteration in range(SAMPLE_COUNTS[prompt_id]):
                    order = ABBA_ORDERS[iteration % len(ABBA_ORDERS)]
                    for stage_index, stage in enumerate(STAGES):
                        stage_order = order if stage_index % 2 == 0 else tuple(reversed(order))
                        for version in stage_order:
                            result = workers[version].request({"action": "call", "prompt": prompt, "stage": stage})
                            samples[version][stage].append({
                                "iteration": iteration + 1,
                                "version_order": list(stage_order),
                                "duration_ms": result["duration_ms"],
                                "output": result["output"],
                            })

                raw["timings"][prompt_id]["stages"] = {}
                for stage in STAGES:
                    summaries = {
                        version: summarize([item["duration_ms"] for item in samples[version][stage]])
                        for version in ("A", "B")
                    }
                    raw["timings"][prompt_id]["stages"][stage] = {
                        "A": summaries["A"],
                        "B": summaries["B"],
                        "comparison": compare_summaries(summaries["A"], summaries["B"]),
                    }
                raw.setdefault("raw_samples", {})[prompt_id] = samples

                raw["memory"][prompt_id] = {"prompt_characters": len(prompt)}
                memory_pair: dict[str, dict[str, Any]] = {"A": {}, "B": {}}
                for stage_index, stage in enumerate(("validation", "full_pipeline")):
                    order = ABBA_ORDERS[stage_index]
                    for version in order:
                        memory_pair[version][stage] = workers[version].request({
                            "action": "memory", "prompt": prompt, "stage": stage
                        })
                for stage in ("validation", "full_pipeline"):
                    a_bytes = memory_pair["A"][stage]["incremental_peak_bytes"]
                    b_bytes = memory_pair["B"][stage]["incremental_peak_bytes"]
                    memory_pair["A"][stage]["difference"] = None
                    memory_pair["B"][stage]["difference"] = {
                        "bytes_B_minus_A": b_bytes - a_bytes,
                        "percent_B_minus_A": ((b_bytes - a_bytes) / a_bytes * 100) if a_bytes else None,
                    }
                raw["memory"][prompt_id].update(memory_pair)

                if prompt_id in ("large_64k", "very_large_512k"):
                    order = ABBA_ORDERS[0 if prompt_id == "large_64k" else 1]
                    raw["profiles"][prompt_id] = {}
                    for version in order:
                        raw["profiles"][prompt_id][version] = workers[version].request({
                            "action": "profile", "prompt": prompt
                        })
                print(f"[{prompt_id}] measurements and memory complete", flush=True)

            # Public realistic evaluation through the established runner in
            # each isolated copy, followed by structured per-case output.
            for version in ("A", "B"):
                print(f"[evaluation {version}] running public realistic evaluation", flush=True)
                raw["evaluations"][version] = {
                    "runner": run_realistic_runner(version, versions[version], envs[version]),
                    "rows": workers[version].request({"action": "evaluate"})["rows"],
                }
                raw["evaluations"][version]["summary"] = eval_summary(
                    raw["evaluations"][version]["rows"]
                )

            # A's full test collection is expected to encounter the B-specific
            # private helper test. Capture that result, then run all applicable
            # baseline tests. B runs the complete suite, including that module.
            standard_a_command = [sys.executable, "-m", "pytest", "nlp_engine/tests", "-v"]
            print("[tests A] checking standard collection and baseline-compatible suite", flush=True)
            standard_a = subprocess.run(
                standard_a_command,
                cwd=versions["A"], env=envs["A"], capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=900,
            )
            standard_output = standard_a.stdout + standard_a.stderr
            match = re.search(r"=+\s*(\d+ passed[^\n=]*|[^\n]*\d+ failed[^\n=]*)\s*=+", standard_output)
            raw["tests"]["A_standard"] = {
                "command": standard_a_command,
                "return_code": standard_a.returncode,
                "summary": match.group(1).strip() if match else None,
                "output_tail": standard_output[-6000:],
            }
            raw["tests"]["A_compatible"] = run_tests("A", versions["A"], envs["A"])
            print("[tests B] running complete NLP suite", flush=True)
            raw["tests"]["B"] = run_tests("B", versions["B"], envs["B"])

            rows_a = raw["evaluations"]["A"]["rows"]
            rows_b = raw["evaluations"]["B"]["rows"]
            differences = []
            if len(rows_a) != len(rows_b):
                differences.append({"length_A": len(rows_a), "length_B": len(rows_b)})
            for a, b in zip(rows_a, rows_b):
                if a != b:
                    differences.append({
                        "id": a.get("id"),
                        "different_fields": sorted(key for key in set(a) | set(b) if a.get(key) != b.get(key)),
                        "A_pipeline_validation": a.get("pipeline_validation"),
                        "B_pipeline_validation": b.get("pipeline_validation"),
                        "A_final_prompt": a.get("final_prompt"),
                        "B_final_prompt": b.get("final_prompt"),
                    })
            raw["functional"] = {
                "performance_prompts_equivalent": all(
                    samples["A"]["validation"][i]["output"] == samples["B"]["validation"][i]["output"]
                    for prompt_id in prompts
                    for samples in [raw["raw_samples"][prompt_id]]
                    for i in range(SAMPLE_COUNTS[prompt_id])
                ),
                "candidate_hashes_equivalent": all(
                    prepared["A"][prompt_id]["candidate_sha256"] == prepared["B"][prompt_id]["candidate_sha256"]
                    for prompt_id in prompts
                ),
                "realistic_rows_equivalent": not differences,
                "realistic_differences": differences,
                "A_evaluation_summary": raw["evaluations"]["A"]["summary"],
                "B_evaluation_summary": raw["evaluations"]["B"]["summary"],
            }

            # Include evaluated summaries and per-run output but keep the raw
            # latency sample arrays in their own dedicated artifact.
            raw["status"] = "complete"
            raw["verdict"] = "inconclusive"
            raw["limitations"] = [
                "No cold-import comparison was run.",
                "RSS is unavailable unless psutil is installed.",
                "p95 is reported only for at least 20 samples.",
                "Version A's current Milestone 4-specific test module is excluded from its compatible suite because it imports an unavailable private helper; its standard collection result is recorded separately.",
            ]
            raw_samples_data = {
                "format_version": 1,
                "source": raw["source"],
                "configuration": raw["configuration"],
                "prompts": raw["prompts"],
                "samples": raw.get("raw_samples", {}),
            }
            # Always close workers before leaving the isolated workspace.
        finally:
            for worker in workers.values():
                worker.close()

    # Final summaries from raw per-version samples, with outputs retained in
    # the raw artifact. Remove per-sample outputs from the compact report JSON.
    compact_timings: dict[str, Any] = {}
    for prompt_id, record in raw["timings"].items():
        compact_timings[prompt_id] = {
            "prompt_characters": record["prompt_characters"],
            "stages": record["stages"],
        }
    result_data = {
        key: value for key, value in raw.items()
        if key not in ("raw_samples", "profiles", "evaluations", "tests")
    }
    result_data["source"].update(raw["isolation"])
    result_data["timings"] = compact_timings
    result_data["evaluations"] = {
        version: {"runner": raw["evaluations"][version]["runner"],
                  "summary": raw["evaluations"][version]["summary"],
                  "cases": [
                      {key: row.get(key) for key in (
                          "id", "expected_behavior", "actual_behavior", "behavior_correct",
                          "pipeline_validation", "llm_candidate_validation",
                          "optimization_accepted", "fallback_used", "fallback_reason",
                          "final_prompt", "original_tokens", "final_tokens", "tokens_saved",
                          "false_removal", "unexpected_optimization", "missed_opportunity",
                          "exception",
                      )}
                      for row in raw["evaluations"][version]["rows"]
                  ]}
        for version in ("A", "B")
    }
    result_data["tests"] = {
        version: {key: value for key, value in raw["tests"].items() if key.startswith(version)}
        for version in ("A", "B")
    }
    report_data = dict(result_data)
    report_data["profiles"] = raw["profiles"]
    report_data["tests"] = raw["tests"]
    report_data["evaluations"] = result_data["evaluations"]
    RESULT_PATH.write_text(json.dumps(result_data, ensure_ascii=False, indent=2), encoding="utf-8")
    RAW_PATH.write_text(json.dumps(raw_samples_data, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(
        markdown_report(report_data, RAW_PATH.name, PROFILE_PATH.name), encoding="utf-8"
    )
    PROFILE_PATH.write_text(profile_markdown(raw), encoding="utf-8")
    print(f"Results: {RESULT_PATH}")
    print(f"Raw samples: {RAW_PATH}")
    print(f"Profile report: {PROFILE_PATH}")
    print(f"Summary report: {REPORT_PATH}")
    print(f"Verdict: {raw['verdict']}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--complete-existing"]:
        complete_existing_results()
    else:
        main()

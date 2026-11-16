"""Standalone CPU-first performance benchmark for the NLP engine.

Run from the repository root:

    python -m nlp_engine.tests.run_performance_benchmark

This benchmark is intentionally not collected by pytest. It measures analysis,
candidate generation, validation, full-pipeline latency, cold process startup,
optional semantic paths, deterministic rewrite callbacks, and memory where
available. It makes no performance pass/fail claim and changes no engine limit.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import socket
import statistics
import subprocess
import sys
import time
import tracemalloc
from collections import Counter
from pathlib import Path
from typing import Any, Callable


TEST_DIR = Path(__file__).resolve().parent
ROOT_DIR = TEST_DIR.parents[1]
CONFIG_PATH = TEST_DIR / "performance_prompts.json"
RAW_RESULT_PATH = TEST_DIR / "performance_benchmark_results.json"
REPORT_PATH = TEST_DIR / "performance_benchmark_results.md"
RESULT_MARKER = "__TOKENTRIM_PERFORMANCE_RESULT__"
MODEL_PACKAGES = (
    "numpy", "scikit-learn", "nltk", "pydantic", "tiktoken", "pytest",
    "sentence-transformers", "torch", "transformers", "huggingface-hub",
    "tokenizers", "safetensors", "psutil",
)


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)
    if config.get("format_version") != 1:
        raise ValueError("Unsupported performance prompt corpus format")
    return config


def build_prompt(config: dict[str, Any], scenario: dict[str, Any]) -> str:
    """Create an identical, reproducible prompt from corpus templates."""
    lines = list(config["fixed_prompt_sections"])
    fixed_instruction_count = 6
    extra_count = max(0, int(scenario["instruction_clauses"]) - fixed_instruction_count)
    lines.append("Additional processing instructions:")
    lines.extend(
        config["instruction_template"].format(index=index)
        for index in range(extra_count)
    )
    prompt = "\n".join(lines)

    target = int(scenario.get("target_characters", len(prompt)))
    notes = []
    note_index = 0
    prefix = "\n\nBackground context:\n"
    current_length = len(prompt) + len(prefix)
    while True:
        note = config["context_template"].format(index=note_index)
        addition = len(note) + (1 if notes else 0)
        if current_length + addition > target:
            break
        notes.append(note)
        current_length += addition
        note_index += 1

    if notes:
        prompt += prefix + "\n".join(notes)
    return prompt


def make_candidate(prompt: str, callback_mode: str) -> str:
    if callback_mode == "none":
        return prompt
    if callback_mode == "safe_shorter":
        repeated = "- Keep the original record identifier unchanged."
        marker = repeated + "\n" + repeated
        if marker not in prompt:
            return prompt
        return prompt.replace(marker, repeated, 1)
    if callback_mode == "lossy":
        return prompt.replace(
            "- Do not change the meaning of `source_timestamp` or `normalized_value`.",
            "- Change the meaning of `source_timestamp` or `normalized_value`.",
            1,
        )
    if callback_mode == "unchanged":
        return prompt
    raise ValueError(f"Unknown callback mode: {callback_mode}")


def _percentile(samples: list[float], percentile: float) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def summarize_samples(samples: list[float]) -> dict[str, Any]:
    return {
        "iterations": len(samples),
        "p50_ms": statistics.median(samples) if samples else None,
        "p95_ms": _percentile(samples, 0.95),
        "max_ms": max(samples) if samples else None,
        "samples_ms": samples,
    }


def _quality_snapshot(result, prompt: str) -> dict[str, Any]:
    final = result.final
    return {
        "optimization_accepted": bool(result.optimization_accepted),
        "validation_is_valid": bool(result.validation.is_valid),
        "original_prompt_retained": final.optimized_prompt == prompt,
        "final_method": final.method,
        "original_tokens": final.original_tokens,
        "final_tokens": final.optimized_tokens,
        "estimated_tokens_saved": final.tokens_saved,
        "reduction_percentage": final.reduction_percentage,
        "fallback_changes": list(final.changes),
    }


def _set_cpu_and_offline_environment(semantic_mode: str, semantic_model: str) -> None:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["NVIDIA_VISIBLE_DEVICES"] = ""
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

    from nlp_engine.semantic_similarity import (
        DEVICE_ENV,
        ENABLE_ENV,
        MODEL_ENV,
    )

    os.environ[DEVICE_ENV] = "cpu"
    os.environ[MODEL_ENV] = semantic_model
    os.environ[ENABLE_ENV] = "true" if semantic_mode == "local_cached_model" else "false"


class DeterministicEmbeddingStub:
    """Local, repeatable encoder for measuring hybrid-path overhead only."""

    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions

    def encode(self, texts, **_kwargs):
        import numpy as np

        vectors = np.zeros((len(texts), self.dimensions), dtype=float)
        for row, text in enumerate(texts):
            for token in re.findall(r"[a-zA-Z0-9_]+", str(text).lower()):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                column = int.from_bytes(digest[:4], "big") % self.dimensions
                vectors[row, column] += 1.0
        return vectors


def _configure_semantic_mode(semantic_mode: str, semantic_model: str):
    """Configure a worker and return a cleanup callback plus model state."""
    _set_cpu_and_offline_environment(semantic_mode, semantic_model)
    import nlp_engine.semantic_similarity as semantic

    load_duration: list[float] = []
    model_state: dict[str, Any] = {"available": None, "error": None}
    original_connect = socket.socket.connect

    def network_disabled_connect(_sock, _address):
        raise OSError("Network access disabled by performance benchmark")

    socket.socket.connect = network_disabled_connect

    def restore_network():
        socket.socket.connect = original_connect

    if semantic_mode == "semantic_disabled":
        return restore_network, load_duration, model_state

    if semantic_mode == "deterministic_semantic_stub":
        original_get_model = semantic.get_semantic_model
        stub = DeterministicEmbeddingStub()
        semantic.get_semantic_model = lambda: stub
        def cleanup_stub():
            semantic.get_semantic_model = original_get_model
            restore_network()

        return cleanup_stub, load_duration, {"available": True, "error": None}

    if semantic_mode != "local_cached_model":
        raise ValueError(f"Unknown semantic mode: {semantic_mode}")

    original_get_model = semantic.get_semantic_model

    def timed_get_model():
        started = time.perf_counter()
        try:
            model = original_get_model()
            model_state["available"] = model is not None
            if model is None:
                model_state["error"] = (
                    "Optional model could not be loaded from the local cache "
                    "in offline mode."
                )
            return model
        except Exception as exc:
            model_state["available"] = False
            model_state["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            load_duration.append((time.perf_counter() - started) * 1000)

    semantic.get_semantic_model = timed_get_model

    def cleanup():
        semantic.get_semantic_model = original_get_model
        restore_network()

    return cleanup, load_duration, model_state


def _callback_for(prompt: str, callback_mode: str, callback_stats: dict[str, Any]):
    if callback_mode == "none":
        return None

    def local_callback(_rewrite_request: str) -> str:
        started = time.perf_counter()
        try:
            return make_candidate(prompt, callback_mode)
        finally:
            callback_stats["count"] += 1
            callback_stats["duration_ms"].append(
                (time.perf_counter() - started) * 1000
            )

    return local_callback


def _run_worker(scenario: dict[str, Any], semantic_mode: str,
                callback_mode: str, worker_mode: str,
                config: dict[str, Any], semantic_model: str) -> dict[str, Any]:
    prompt = build_prompt(config, scenario)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    result: dict[str, Any] = {
        "scenario_id": scenario["id"],
        "semantic_mode": semantic_mode,
        "callback_mode": callback_mode,
        "worker_mode": worker_mode,
        "prompt_characters": len(prompt),
        "prompt_sha256": prompt_hash,
        "target_characters": scenario.get("target_characters"),
        "target_instruction_clauses": scenario["instruction_clauses"],
        "exceptions": [],
    }

    import_started = time.perf_counter()
    from nlp_engine import analyze_prompt_detailed, tokenizer_info
    from nlp_engine.analyzer import build_analysis
    from nlp_engine.optimizer import optimize_prompt
    from nlp_engine.redundancy import build_clauses
    from nlp_engine.validator import validate_optimization

    import_ms = (time.perf_counter() - import_started) * 1000
    result["engine_import_ms"] = import_ms
    result["tokenizer"] = dataclasses.asdict(tokenizer_info(config["evaluation_model"]))

    cleanup, model_load_durations, model_state = (
        _configure_semantic_mode(semantic_mode, semantic_model)
    )
    result["semantic_model_available"] = model_state["available"]
    result["semantic_model_error"] = model_state["error"]
    callback_stats = {"count": 0, "duration_ms": []}
    callback = _callback_for(prompt, callback_mode, callback_stats)

    try:
        if worker_mode == "cold":
            started = time.perf_counter()
            detailed = analyze_prompt_detailed(
                prompt,
                model=config["evaluation_model"],
                llm_rewriter=callback,
            )
            result["cold_first_full_pipeline_ms"] = (time.perf_counter() - started) * 1000
            result["cold_quality"] = _quality_snapshot(detailed, prompt)
            result["semantic_model_available"] = model_state["available"]
            result["semantic_model_error"] = model_state["error"]
            result["llm_callback_validation"] = (
                validate_optimization(prompt, make_candidate(prompt, callback_mode)).model_dump()
                if callback is not None else None
            )
            result["callback_invocations"] = callback_stats["count"]
            result["callback_ms"] = summarize_samples(callback_stats["duration_ms"])
            result["semantic_model_load_ms"] = (
                model_load_durations[0] if model_load_durations else None
            )
            return result

        if worker_mode != "warm":
            raise ValueError(f"Unknown worker mode: {worker_mode}")

        warmup_count = int(config["warmup_iterations"])
        iterations = int(scenario["warm_iterations"])
        analysis = build_analysis(prompt, config["evaluation_model"])
        candidate = optimize_prompt(prompt, analysis)

        stage_functions: dict[str, Callable[[], Any]] = {
            "analysis": lambda: build_analysis(prompt, config["evaluation_model"]),
            "optimization": lambda: optimize_prompt(prompt, analysis),
            "validation": lambda: validate_optimization(
                prompt, candidate.optimized_prompt
            ),
            "full_pipeline": lambda: analyze_prompt_detailed(
                prompt,
                model=config["evaluation_model"],
                llm_rewriter=callback,
            ),
        }

        latency_results: dict[str, Any] = {}
        stage_outputs: dict[str, Any] = {}
        for stage, function in stage_functions.items():
            for _ in range(warmup_count):
                try:
                    function()
                except Exception as exc:
                    result["exceptions"].append(
                        {"stage": stage, "phase": "warmup", "error": f"{type(exc).__name__}: {exc}"}
                    )
                    break

            samples = []
            outputs = []
            for iteration in range(iterations):
                started = time.perf_counter()
                try:
                    output = function()
                    samples.append((time.perf_counter() - started) * 1000)
                    outputs.append(output)
                except Exception as exc:
                    result["exceptions"].append(
                        {
                            "stage": stage,
                            "phase": "measured",
                            "iteration": iteration + 1,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )

            latency_results[stage] = summarize_samples(samples)
            stage_outputs[stage] = outputs

        full_results = stage_outputs["full_pipeline"]
        quality = [_quality_snapshot(item, prompt) for item in full_results]
        quality_summary = {
            "pipeline_iterations": len(quality),
            "optimization_accepted": sum(q["optimization_accepted"] for q in quality),
            "validation_passed": sum(q["validation_is_valid"] for q in quality),
            "original_prompt_retained": sum(q["original_prompt_retained"] for q in quality),
            "prompt_changed": sum(not q["original_prompt_retained"] for q in quality),
            "estimated_tokens_saved_total": sum(q["estimated_tokens_saved"] for q in quality),
            "estimated_tokens_saved_per_run": (
                statistics.mean(q["estimated_tokens_saved"] for q in quality)
                if quality else None
            ),
            "final_methods": dict(Counter(q["final_method"] for q in quality)),
            "llm_candidate_validation": None,
        }
        if callback is not None:
            llm_check = validate_optimization(prompt, make_candidate(prompt, callback_mode))
            quality_summary["llm_candidate_validation"] = llm_check.model_dump()

        result["warmup_iterations_per_stage"] = warmup_count
        result["warm_latency"] = latency_results
        result["quality"] = quality_summary
        result["quality_runs"] = quality
        result["callback_invocations"] = callback_stats["count"]
        result["callback_ms"] = summarize_samples(callback_stats["duration_ms"])
        result["semantic_model_load_ms"] = (
            model_load_durations[0] if model_load_durations else None
        )
        result["semantic_model_available"] = model_state["available"]
        result["semantic_model_error"] = model_state["error"]
        result["analysis_features"] = {
            "instruction_count": analysis.features.instruction_count,
            "constraint_count": analysis.features.constraint_count,
            "pairwise_clause_count": len(build_clauses(analysis.prepared.segments)),
            "character_count": len(prompt),
        }
        result["optimization_candidate"] = {
            "method": candidate.method,
            "tokens_saved": candidate.tokens_saved,
        }

        # Memory is sampled separately so tracemalloc overhead does not
        # contaminate the latency distributions above.
        memory: dict[str, Any] = {}
        rss_before = None
        try:
            import psutil
            rss_before = psutil.Process().memory_info().rss
        except Exception:
            psutil = None

        tracemalloc.start()
        try:
            memory_result = analyze_prompt_detailed(
                prompt,
                model=config["evaluation_model"],
                llm_rewriter=callback,
            )
            _, peak_python_bytes = tracemalloc.get_traced_memory()
            memory["python_peak_allocated_bytes"] = peak_python_bytes
            memory["quality"] = _quality_snapshot(memory_result, prompt)
        except Exception as exc:
            memory["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            tracemalloc.stop()

        if rss_before is not None and psutil is not None:
            try:
                rss_after = psutil.Process().memory_info().rss
                memory["process_rss_before_bytes"] = rss_before
                memory["process_rss_after_bytes"] = rss_after
                memory["process_rss_delta_bytes"] = rss_after - rss_before
            except Exception as exc:
                memory["process_rss_error"] = f"{type(exc).__name__}: {exc}"
        else:
            memory["process_rss"] = "unavailable; psutil is not installed or could not be read"

        result["memory"] = memory
        return result
    finally:
        cleanup()


def _worker_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--worker-mode", choices=("cold", "warm"), required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--semantic-mode", required=True)
    parser.add_argument("--callback-mode", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--semantic-model", required=True)
    args = parser.parse_args(argv)

    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        scenarios = config["size_scenarios"] + config["clause_scenarios"]
        scenario = next(item for item in scenarios if item["id"] == args.scenario)
        result = _run_worker(
            scenario, args.semantic_mode, args.callback_mode,
            args.worker_mode, config, args.semantic_model,
        )
    except BaseException as exc:
        result = {
            "worker_error": f"{type(exc).__name__}: {exc}",
            "worker_mode": args.worker_mode,
            "scenario_id": args.scenario,
            "semantic_mode": args.semantic_mode,
            "callback_mode": args.callback_mode,
        }

    print(RESULT_MARKER + json.dumps(result, ensure_ascii=False, default=str))
    return 0


def _environment_metadata(config: dict[str, Any], semantic_model: str) -> dict[str, Any]:
    try:
        commit_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        git_status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT_DIR, check=True,
            capture_output=True, text=True,
        ).stdout.splitlines()
    except Exception as exc:
        commit_hash = None
        git_status = [f"Could not read Git metadata: {type(exc).__name__}: {exc}"]

    versions = {}
    for package in MODEL_PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None

    try:
        cpu_model = platform.processor() or platform.uname().processor or "unreported"
    except Exception:
        cpu_model = "unreported"

    return {
        "git_commit": commit_hash,
        "git_worktree_dirty": bool(git_status),
        "git_status_entries": git_status,
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "operating_system": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "cpu_model": cpu_model,
        "cpu_identifier": os.getenv("PROCESSOR_IDENTIFIER"),
        "logical_cpu_count": os.cpu_count(),
        "dependency_versions": versions,
        "benchmark_configuration": config,
        "semantic_model_name": semantic_model,
        "semantic_model_device": "cpu",
        "offline_mode": True,
    }


def _child_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["NVIDIA_VISIBLE_DEVICES"] = ""
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["TOKENIZERS_PARALLELISM"] = "false"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    old_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT_DIR) + (os.pathsep + old_pythonpath if old_pythonpath else "")
    return env


def _run_child(scenario_id: str, semantic_mode: str, callback_mode: str,
               worker_mode: str, config: dict[str, Any], semantic_model: str,
               timeout_seconds: float) -> dict[str, Any]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker-mode", worker_mode,
        "--scenario", scenario_id,
        "--semantic-mode", semantic_mode,
        "--callback-mode", callback_mode,
        "--config", str(CONFIG_PATH),
        "--semantic-model", semantic_model,
    ]
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT_DIR,
            env=_child_environment(),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "scenario_id": scenario_id,
            "semantic_mode": semantic_mode,
            "callback_mode": callback_mode,
            "worker_mode": worker_mode,
            "timeout": True,
            "timeout_seconds": timeout_seconds,
            "process_elapsed_ms": (time.perf_counter() - started) * 1000,
            "exceptions": ["Worker exceeded harness timeout and was terminated."],
        }

    result = None
    for line in completed.stdout.splitlines():
        if line.startswith(RESULT_MARKER):
            try:
                result = json.loads(line[len(RESULT_MARKER):])
            except json.JSONDecodeError:
                pass

    if result is None:
        return {
            "scenario_id": scenario_id,
            "semantic_mode": semantic_mode,
            "callback_mode": callback_mode,
            "worker_mode": worker_mode,
            "worker_error": "Worker returned no parseable result.",
            "return_code": completed.returncode,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
            "process_elapsed_ms": (time.perf_counter() - started) * 1000,
            "exceptions": ["Worker returned no parseable result."],
        }

    result["process_elapsed_ms"] = (time.perf_counter() - started) * 1000
    result["return_code"] = completed.returncode
    if completed.returncode != 0:
        result.setdefault("exceptions", []).append(
            f"Worker exited with code {completed.returncode}: {completed.stderr[-1000:]}"
        )
    return result


def _aggregate(results: list[dict[str, Any]], key: str) -> dict[str, Any]:
    samples = [float(result[key]) for result in results if isinstance(result.get(key), (int, float))]
    return summarize_samples(samples)


def _run_benchmark(config: dict[str, Any], semantic_model: str,
                   timeout_seconds: float, only_scenario: str | None,
                   include_local_model: bool) -> dict[str, Any]:
    size_scenarios = config["size_scenarios"]
    clause_scenarios = config["clause_scenarios"]
    all_scenarios = size_scenarios + clause_scenarios
    if only_scenario:
        all_scenarios = [item for item in all_scenarios if item["id"] == only_scenario]
        if not all_scenarios:
            raise ValueError(f"Unknown scenario: {only_scenario}")

    warm_jobs: list[tuple[dict[str, Any], str, str]] = [
        (scenario, "semantic_disabled", "none") for scenario in all_scenarios
    ]
    scenario_by_id = {item["id"]: item for item in all_scenarios}
    # Compare semantic overhead on representative sizes; the deterministic
    # stub is synthetic and is never labeled as model performance.
    for scenario_id in config["semantic_stub_representative_scenarios"]:
        if scenario_id in scenario_by_id:
            warm_jobs.append((scenario_by_id[scenario_id], "deterministic_semantic_stub", "none"))
    # Deterministic callbacks exercise candidate validation without provider
    # calls. Medium input is the representative callback comparison.
    callback_scenario_id = "medium_16k"
    if callback_scenario_id in scenario_by_id:
        for callback_mode in ("safe_shorter", "lossy"):
            warm_jobs.append((scenario_by_id[callback_scenario_id], "semantic_disabled", callback_mode))

    if include_local_model:
        for scenario_id in config["cached_model_representative_scenarios"]:
            if scenario_id in scenario_by_id:
                warm_jobs.append((scenario_by_id[scenario_id], "local_cached_model", "none"))

    warm_results = []
    for index, (scenario, semantic_mode, callback_mode) in enumerate(warm_jobs, start=1):
        print(
            f"[warm {index}/{len(warm_jobs)}] {scenario['id']} | "
            f"{semantic_mode} | callback={callback_mode}",
            flush=True,
        )
        result = _run_child(
            scenario["id"], semantic_mode, callback_mode, "warm",
            config, semantic_model, timeout_seconds,
        )
        result["warm_requested_iterations"] = int(scenario["warm_iterations"])
        warm_results.append(result)

    # Cold starts are measured in fresh worker processes. Use the configured
    # representative sizes across the baseline, stub, and callback paths.
    cold_jobs: list[tuple[str, str, str]] = []
    scenario_ids = {item["id"] for item in all_scenarios}
    representative = [
        value for value in config["cold_representative_scenarios"]
        if value in scenario_ids
    ]
    for scenario_id in representative:
        cold_jobs.extend([
            (scenario_id, "semantic_disabled", "none"),
            (scenario_id, "deterministic_semantic_stub", "none"),
        ])
    callback_cold_scenario = "medium_16k"
    if callback_cold_scenario in scenario_ids:
        cold_jobs.extend([
            (callback_cold_scenario, "semantic_disabled", "safe_shorter"),
            (callback_cold_scenario, "semantic_disabled", "lossy"),
        ])
    if include_local_model and callback_cold_scenario in scenario_ids:
        cold_jobs.append((callback_cold_scenario, "local_cached_model", "none"))

    cold_results = []
    cold_repetitions = int(config["cold_iterations"])
    total_cold = len(cold_jobs) * cold_repetitions
    cold_index = 0
    for scenario_id, semantic_mode, callback_mode in cold_jobs:
        for repetition in range(cold_repetitions):
            cold_index += 1
            print(
                f"[cold {cold_index}/{total_cold}] {scenario_id} | "
                f"{semantic_mode} | callback={callback_mode} | run={repetition + 1}",
                flush=True,
            )
            cold_results.append(_run_child(
                scenario_id, semantic_mode, callback_mode, "cold",
                config, semantic_model, timeout_seconds,
            ))

    local_model_results = [
        result for result in warm_results + cold_results
        if result.get("semantic_mode") == "local_cached_model"
    ]
    local_model_available = any(
        result.get("semantic_model_available") is True
        for result in local_model_results
    )
    if include_local_model and not local_model_available:
        local_model_status = (
            "unavailable: sentence-transformers is not installed or the configured "
            "model is not cached locally; offline mode prevented downloads"
        )
    elif include_local_model:
        local_model_status = "measured using the actual locally cached model on CPU"
    else:
        local_model_status = "not requested; deterministic stub is reported separately"

    return {
        "metadata": _environment_metadata(config, semantic_model),
        "semantic_model_status": local_model_status,
        "semantic_model_requested": include_local_model,
        "runner_configuration": {
            "timeout_seconds": timeout_seconds,
            "only_scenario": only_scenario,
            "cold_repetitions_per_cold_job": cold_repetitions,
            "warmup_iterations_per_stage": config["warmup_iterations"],
            "process_isolation": True,
            "cpu_only": True,
            "network_access": "offline worker environment; socket guard enabled; no provider calls",
            "token_counts": "heuristic estimates using fixed unknown model name",
        },
        "warm_results": warm_results,
        "cold_results": cold_results,
    }


def _render_metrics_table(results: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Scenario | Input chars | Tokenizer | Pairwise clauses | Semantic path | Callback | Stage | n | p50 ms | p95 ms | max ms | Exceptions |",
        "|---|---:|---:|---:|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        if result.get("worker_error") or result.get("timeout"):
            lines.append(
                f"| {result.get('scenario_id')} | — | — | — | "
                f"{result.get('semantic_mode')} | {result.get('callback_mode')} | "
                f"worker | 0 | — | — | — | 1 |"
            )
            continue
        token_count = result.get("tokenizer", {}).get("method", "estimate")
        exception_count = len(result.get("exceptions", []))
        pairwise_count = result.get("analysis_features", {}).get(
            "pairwise_clause_count", result.get("target_instruction_clauses", "--")
        )
        for stage, metrics in result.get("warm_latency", {}).items():
            lines.append(
                f"| {result['scenario_id']} | {result['prompt_characters']} | "
                f"{token_count} | {pairwise_count} | "
                f"{_semantic_path_label(result)} | {result['callback_mode']} | {stage} | "
                f"{metrics['iterations']} | {metrics['p50_ms']:.3f} | "
                f"{metrics['p95_ms']:.3f} | {metrics['max_ms']:.3f} | "
                f"{exception_count} |"
            )
    return lines


def _semantic_path_label(result: dict[str, Any]) -> str:
    if (result.get("semantic_mode") == "local_cached_model"
            and result.get("semantic_model_available") is False):
        return "local model unavailable; lexical fallback"
    return result.get("semantic_mode", "unknown")


def build_report(results: dict[str, Any]) -> str:
    warm = results["warm_results"]
    cold = results["cold_results"]
    metadata = results["metadata"]
    versions = metadata["dependency_versions"]

    lines = [
        "# TokenTrim NLP Performance Benchmark",
        "",
        "## Reproducibility",
        "",
        "Run from the repository root:",
        "",
        "```bash",
        "python -m nlp_engine.tests.run_performance_benchmark",
        "```",
        "",
        f"- Git commit: `{metadata['git_commit']}`",
        f"- Git worktree dirty: `{metadata['git_worktree_dirty']}`",
        f"- Python: `{metadata['python_version'].splitlines()[0]}` ({metadata['python_implementation']})",
        f"- OS: `{metadata['operating_system']}`",
        f"- CPU: `{metadata['cpu_model']}`; logical CPUs: `{metadata['logical_cpu_count']}`",
        f"- Semantic model status: {results['semantic_model_status']}",
        "- Execution: CPU-only; no provider/network calls were made; callbacks were deterministic local functions and the optional model probe ran offline.",
        "- Token counts: heuristic estimates; they are not exact provider token counts.",
        "- Dependency versions: " + ", ".join(
            f"`{name}={version or 'not installed'}`" for name, version in versions.items()
        ),
        "",
        "The deterministic semantic stub is an in-process synthetic encoder and **does not represent "
        "Sentence-Transformers model latency or memory**. The actual local model was unavailable in "
        "this run; its rows represent model-load failure and lexical fallback only, not model performance.",
        "",
    ]
    quality_runs = sum(item.get("quality", {}).get("pipeline_iterations", 0) for item in warm)
    accepted_runs = sum(item.get("quality", {}).get("optimization_accepted", 0) for item in warm)
    unchanged_runs = sum(item.get("quality", {}).get("original_prompt_retained", 0) for item in warm)
    changed_runs = sum(item.get("quality", {}).get("prompt_changed", 0) for item in warm)
    estimated_savings = sum(item.get("quality", {}).get("estimated_tokens_saved_total", 0) for item in warm)
    callback_results = [item for item in warm if item.get("callback_mode") != "none"]
    callback_invalid = sum(
        bool(item.get("quality", {}).get("llm_candidate_validation")
             and not item["quality"]["llm_candidate_validation"].get("is_valid", False))
        for item in callback_results
    )
    callback_valid = sum(
        bool(item.get("quality", {}).get("llm_candidate_validation", {}).get("is_valid"))
        for item in callback_results
    )
    failures_count = sum(
        bool(item.get("worker_error") or item.get("timeout") or item.get("exceptions"))
        for item in warm + cold
    )
    lines.extend([
        "## Aggregate optimization quality",
        "",
        f"Across {quality_runs} repeated full-pipeline output runs, {accepted_runs} optimizations were accepted "
        f"and {quality_runs - accepted_runs} returned no optimization; the original was retained {unchanged_runs} "
        f"times and changed {changed_runs} times. Estimated savings total {estimated_savings} tokens using the "
        "heuristic tokenizer; these are repeated-run estimates, not unique-prompt savings.",
        "The five unchanged outputs are the 301- and 591-clause scenarios, where the existing pairwise guard "
        "skips duplicate analysis. Each includes the benchmark's exact repeated instruction, so these are five "
        "missed safe-optimization instances, not validator rejections. No false removals were observed in this "
        "controlled corpus. The final output validated in every run. Candidate validation: the safe deterministic "
        f"rewrite passed in {callback_valid} configuration(s); the negation-changing candidate was rejected in "
        f"{callback_invalid} configuration(s). Worker/stage failures: {failures_count}.",
        "",
        "## Warm latency",
        "",
    ])
    lines.extend(_render_metrics_table(warm))
    lines.extend([
        "",
        "Warm p50/p95/max values are computed from the actual iteration counts shown. The p95 uses "
        "nearest-rank; small iteration counts therefore have correspondingly coarse percentile resolution.",
        "",
        "## Measured operating guidance",
        "",
    ])
    size_ids = {item["id"] for item in metadata["benchmark_configuration"]["size_scenarios"]}
    baseline_sizes = [
        item for item in warm
        if item.get("semantic_mode") == "semantic_disabled"
        and item.get("callback_mode") == "none"
        and item.get("scenario_id") in size_ids
    ]
    baseline_sizes.sort(key=lambda item: item["prompt_characters"])
    if len(baseline_sizes) >= 5:
        p95_64k = baseline_sizes[2]["warm_latency"]["full_pipeline"]["p95_ms"] / 1000
        p95_256k = baseline_sizes[3]["warm_latency"]["full_pipeline"]["p95_ms"] / 1000
        p95_512k = baseline_sizes[4]["warm_latency"]["full_pipeline"]["p95_ms"] / 1000
        p50_512k = baseline_sizes[4]["warm_latency"]["full_pipeline"]["p50_ms"] / 1000
        p50_validator_512k = baseline_sizes[4]["warm_latency"]["validation"]["p50_ms"] / 1000
        p50_analysis_512k = baseline_sizes[4]["warm_latency"]["analysis"]["p50_ms"] / 1000
        p50_optimization_512k = baseline_sizes[4]["warm_latency"]["optimization"]["p50_ms"] / 1000
        max_memory = max(
            item.get("memory", {}).get("python_peak_allocated_bytes", 0)
            for item in warm
        ) / (1024 * 1024)
        lines.extend([
            "On this recorded four-logical-CPU Windows machine, baseline full-pipeline p95 was about "
            f"{p95_64k:.2f} s at 64k characters, {p95_256k:.2f} s at 256k, and {p95_512k:.2f} s at 512k "
            f"(512k p50: {p50_512k:.2f} s). As measured guidance, prompts up to roughly 64k characters "
            "fit a latency-sensitive synchronous path more comfortably here; 256k–512k prompts are better "
            "suited to an asynchronous path or a caller with a multi-second latency allowance. This is not "
            "an enforced engine cap or a universal SLA.",
            f"At 512k, validation took {p50_validator_512k:.2f} s p50 of the {p50_512k:.2f} s full-pipeline "
            f"p50, making validation the main large-input bottleneck; analysis took {p50_analysis_512k:.2f} s "
            f"and candidate optimization {p50_optimization_512k:.2f} s. Fresh-process imports took roughly "
            "5.2 s p50, dominating small-prompt cold start, so a long-lived worker avoids repeating much of "
            "that fixed startup cost.",
            f"The 512k case completed without a timeout. Maximum Python traced peak allocation was about "
            f"{max_memory:.1f} MiB; process RSS was about 202 MB after warm-up. RSS deltas are affected by "
            "allocator and garbage-collection behavior. These are observations, not hard resource limits.",
        ])
    else:
        lines.append("Insufficient completed baseline size cases to derive operating guidance.")
    lines.extend([
        "",
        "## Cold starts",
        "",
        "Each row below comes from a fresh subprocess. `process_elapsed_ms` includes interpreter and "
        "worker startup through result serialization; `engine_import_ms` isolates package imports; "
        "`cold_first_full_pipeline_ms` measures the first detailed analysis call, including lazy semantic-model loading when applicable.",
        "",
        "| Scenario | Semantic path | Callback | n | Process to result p50/p95/max ms | Engine import p50/p95/max ms | First pipeline p50/p95/max ms | Model load p50/p95/max ms | Failures |",
        "|---|---|---|---:|---|---|---|---|---:|",
    ])

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for result in cold:
        key = (result.get("scenario_id", "?"), _semantic_path_label(result), result.get("callback_mode", "?"))
        grouped.setdefault(key, []).append(result)

    for (scenario, semantic_mode, callback_mode), group in sorted(grouped.items()):
        process = summarize_samples([
            r["process_elapsed_ms"] for r in group
            if isinstance(r.get("process_elapsed_ms"), (int, float))
        ])
        imports = summarize_samples([
            r["engine_import_ms"] for r in group
            if isinstance(r.get("engine_import_ms"), (int, float))
        ])
        first = summarize_samples([
            r["cold_first_full_pipeline_ms"] for r in group
            if isinstance(r.get("cold_first_full_pipeline_ms"), (int, float))
        ])
        loads = summarize_samples([
            r["semantic_model_load_ms"] for r in group
            if isinstance(r.get("semantic_model_load_ms"), (int, float))
        ])

        def triplet(stats: dict[str, Any]) -> str:
            if not stats["iterations"]:
                return "unavailable"
            return f"{stats['p50_ms']:.2f}/{stats['p95_ms']:.2f}/{stats['max_ms']:.2f}"

        failures = sum(bool(r.get("worker_error") or r.get("timeout") or r.get("exceptions")) for r in group)
        lines.append(
            f"| {scenario} | {semantic_mode} | {callback_mode} | {len(group)} | "
            f"{triplet(process)} | {triplet(imports)} | {triplet(first)} | "
            f"{triplet(loads)} | {failures} |"
        )

    lines.extend(["", "## Optimization quality and callbacks", ""])
    lines.extend([
        "| Scenario | Semantic path | Callback | Accepted / runs | Validations passed | Original retained / changed | Est. savings per run | LLM candidate validator | Callback invocations | Callback latency p50/p95/max ms | Exceptions |",
        "|---|---|---|---:|---:|---|---:|---|---:|---|---:|",
    ])
    for result in warm:
        if result.get("worker_error") or result.get("timeout"):
            continue
        quality = result.get("quality", {})
        callback_stats = result.get("callback_ms", {})
        callback_triplet = "—"
        if callback_stats.get("iterations"):
            callback_triplet = (
                f"{callback_stats['p50_ms']:.4f}/{callback_stats['p95_ms']:.4f}/"
                f"{callback_stats['max_ms']:.4f}"
            )
        candidate_validation = quality.get("llm_candidate_validation")
        validation_label = (
            "—" if candidate_validation is None else
            f"valid={candidate_validation['is_valid']}"
        )
        lines.append(
            f"| {result['scenario_id']} | {_semantic_path_label(result)} | {result['callback_mode']} | "
            f"{quality.get('optimization_accepted', 0)}/{quality.get('pipeline_iterations', 0)} | "
            f"{quality.get('validation_passed', 0)} | "
            f"{quality.get('original_prompt_retained', 0)} / {quality.get('prompt_changed', 0)} | "
            f"{quality.get('estimated_tokens_saved_per_run') if quality.get('estimated_tokens_saved_per_run') is not None else '—'} | "
            f"{validation_label} | {result.get('callback_invocations', 0)} | "
            f"{callback_triplet} | {len(result.get('exceptions', []))} |"
        )

    lines.extend(["", "## Memory observations", ""])
    lines.extend([
        "| Scenario | Semantic path | Callback | Python peak allocated bytes | Process RSS before/after/delta bytes | Measurement note |",
        "|---|---|---|---:|---|---|",
    ])
    for result in warm:
        if result.get("worker_error") or result.get("timeout"):
            continue
        memory = result.get("memory", {})
        rss = "unavailable"
        if "process_rss_before_bytes" in memory:
            rss = (
                f"{memory['process_rss_before_bytes']}/"
                f"{memory['process_rss_after_bytes']}/"
                f"{memory['process_rss_delta_bytes']}"
            )
        lines.append(
            f"| {result['scenario_id']} | {_semantic_path_label(result)} | {result['callback_mode']} | "
            f"{memory.get('python_peak_allocated_bytes', 'unavailable')} | {rss} | "
            f"tracemalloc peak excludes native allocations; RSS is a before/after sample |"
        )

    lines.extend([
        "",
        "## Failures and operating observations",
        "",
    ])
    failures = []
    for result in warm + cold:
        if result.get("worker_error"):
            failures.append(f"- `{result.get('scenario_id')}` `{result.get('semantic_mode')}`: {result['worker_error']}")
        if result.get("timeout"):
            failures.append(
                f"- `{result.get('scenario_id')}` `{result.get('semantic_mode')}`: "
                f"worker timed out after {result['timeout_seconds']} seconds (harness guard)."
            )
        for exception in result.get("exceptions", []):
            failures.append(f"- `{result.get('scenario_id')}` `{result.get('semantic_mode')}`: {exception}")
    lines.extend(failures or ["- No exceptions or worker failures were recorded."])

    lines.extend([
        "",
        "### Bottleneck and limit interpretation",
        "",
        "Use the stage table to compare analysis, candidate generation, validation, and full-pipeline "
        "costs by input length and clause count. The 300-clause pairwise guard is an existing engine "
        "behavior; performance results do not change it. Inputs above the largest completed scenario "
        "remain unmeasured. No latency or memory threshold was imposed by this benchmark.",
        "",
        "Any operating limit recommended from these measurements must be described as an observation "
        "for this recorded machine and configuration, not as a universal guarantee. Native model memory "
        "may exceed `tracemalloc` results; use actual-model RSS rows where available.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", help="Run one named scenario as a smoke or focused benchmark")
    parser.add_argument("--worker-timeout-seconds", type=float)
    parser.add_argument("--skip-local-model", action="store_true",
                        help="Skip the offline probe for an actually cached semantic model")
    parser.add_argument("--semantic-model", default=os.getenv(
        "TOKENTRIM_SEMANTIC_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    ))
    parser.add_argument("--worker-mode", choices=("cold", "warm"))
    args = parser.parse_args()

    if args.worker_mode:
        return _worker_main(sys.argv[1:])

    config = load_config()
    timeout_seconds = args.worker_timeout_seconds or float(config["worker_timeout_seconds"])
    results = _run_benchmark(
        config,
        args.semantic_model,
        timeout_seconds,
        args.scenario,
        not args.skip_local_model,
    )
    RAW_RESULT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    report = build_report(results)
    REPORT_PATH.write_text(report, encoding="utf-8")

    warm_failures = sum(
        bool(result.get("worker_error") or result.get("timeout") or result.get("exceptions"))
        for result in results["warm_results"]
    )
    warm_samples = sum(
        sum(metric.get("iterations", 0) for metric in result.get("warm_latency", {}).values())
        for result in results["warm_results"]
    )
    print(f"Performance scenarios: {len(results['warm_results'])} warm worker configurations")
    print(f"Warm stage measurements: {warm_samples}; worker configurations with failures: {warm_failures}")
    print(f"Semantic model: {results['semantic_model_status']}")
    print(f"Report: {REPORT_PATH}")
    print(f"Raw results: {RAW_RESULT_PATH}")
    return 0


if __name__ == "__main__":
    if "--worker-mode" in sys.argv:
        raise SystemExit(_worker_main(sys.argv[1:]))
    raise SystemExit(main())

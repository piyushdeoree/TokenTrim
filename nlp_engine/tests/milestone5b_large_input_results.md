# TokenTrim Milestone 5B — Large-Input and Resource Characterization

## Executive summary

This standalone run measures deterministic public-pipeline workloads, repeated memory behavior, thread concurrency, and controlled failure paths. It does not change production code or introduce limits.

- Source revision: `fdd6022f962ae593db5dc2c2d9c7453bbe4377a7`
- Python: 3.13.5 (CPython)
- OS: Windows-11-10.0.26300-SP0
- CPU: Intel64 Family 6 Model 126 Stepping 5, GenuineIntel (4 logical processors)
- Token counting: heuristic estimate; unknown model name avoids tokenizer downloads
- Semantic model and external LLM/provider calls: disabled

## Prompt construction and full-pipeline timing

Prompts are generated deterministically at exact character sizes with structured sections, requirements, technical literals, code/JSON, conditions, numbers, repeated instructions, and English/Sinhala/Spanish context. SHA-256, UTF-8 byte count, token estimate, segment count, and comparable clause count are recorded per prompt. Each scenario has one warm-up; measured timings use `perf_counter`. p95 is omitted below 20 samples.

| Size | Type | Chars | Clauses | Samples | Min ms | Median ms | Mean ms | Max ms | SD ms | p95 ms | Accepted | Exact fallback | Integrity |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 512KiB | clause_heavy | 524288 | 329 | 5 | 8259.76 | 11423.82 | 12124.97 | 20666.31 | 5037.30 | — | 6/6 | 0/6 | pass |
| 512KiB | technical_protected | 524288 | 9 | 5 | 2924.01 | 3267.12 | 3334.73 | 3938.07 | 371.11 | — | 6/6 | 0/6 | pass |
| 1MiB | clause_heavy | 1048576 | 329 | 3 | 15799.65 | 18043.22 | 18518.13 | 21711.51 | 2984.41 | — | 4/4 | 0/4 | pass |
| 1MiB | technical_protected | 1048576 | 9 | 3 | 6735.33 | 6853.44 | 8154.57 | 10874.93 | 2356.64 | — | 4/4 | 0/4 | pass |
| 2MiB | clause_heavy | 2097152 | 329 | 2 | 48195.58 | 49819.73 | 49819.73 | 51443.87 | 2296.88 | — | 3/3 | 0/3 | pass |
| 2MiB | technical_protected | 2097152 | 9 | 2 | 14682.17 | 26609.04 | 26609.04 | 38535.91 | 16867.14 | — | 3/3 | 0/3 | pass |

Full raw timings, hashes, output-integrity assertions, validation timing, and errors are in the JSON artifact.

## Memory and repeated processing

Memory runs are separate from latency runs. `tracemalloc` reports Python-traced current and peak allocations. RSS uses psutil if already installed, otherwise the Windows process working-set API when available. The process peak working set is cumulative, and a before/after sample can miss short-lived peaks.

| Size | Type | Repeats | Traced delta after calls MiB | Traced peak MiB | RSS before/after MiB | Stable output | Integrity |
|---|---|---:|---:|---:|---|---|---|
| 512KiB | technical_protected | 2 | 0.0 | 13.7 | 157.6/160.3 | yes | pass |
| 1MiB | technical_protected | 2 | 0.0 | 27.2 | 167.1/161.3 | yes | pass |
| 2MiB | technical_protected | 2 | 0.0 | 54.2 | 168.0/165.4 | yes | pass |

## Thread concurrency

Thread workloads compare each concurrent request against its serial output. Throughput and total wall time are reported per round. Thread timings are not a deployment capacity guarantee.

| Workload | Workers | Tasks/round | Rounds | Successes | Failures | Serial matches | Median wall ms | Median req/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| small_2k | 1 | 4 | 2 | 8 | 0 | 8 | 837.15 | 5.24 |
| small_2k | 2 | 4 | 2 | 8 | 0 | 8 | 1354.41 | 3.16 |
| small_2k | 4 | 4 | 2 | 8 | 0 | 8 | 938.74 | 4.26 |
| medium_64k | 1 | 4 | 2 | 8 | 0 | 8 | 14107.71 | 0.32 |
| medium_64k | 2 | 4 | 2 | 8 | 0 | 8 | 9686.62 | 0.47 |
| medium_64k | 4 | 4 | 2 | 8 | 0 | 8 | 6193.87 | 0.65 |
| large_512k | 1 | 2 | 1 | 2 | 0 | 2 | 30091.93 | 0.07 |
| large_512k | 2 | 2 | 1 | 2 | 0 | 2 | 28626.32 | 0.07 |
| large_512k | 4 | 4 | 1 | 4 | 0 | 4 | 54456.65 | 0.07 |
| mixed_2k_64k_512k | 4 | 4 | 1 | 4 | 0 | 4 | 18976.82 | 0.21 |

## Failure handling

The harness injects local failures only; it makes no provider calls and downloads no model. Exception types and post-failure follow-up behavior are recorded below.

| Case | Outcome | Exception | Follow-up succeeds | Exact fallback | Accepted |
|---|---|---|---|---|---|
| non_string_input_none | exception_propagated | ValueError | True | — | — |
| non_string_input_integer | exception_propagated | ValueError | True | — | — |
| llm_callback_exception | returned | — | True | True | False |
| llm_invalid_bytes | returned | — | True | True | False |
| semantic_encode_failure | returned | — | True | False | True |
| tokenizer_count_failure | exception_propagated | RuntimeError | True | — | — |
| validator_exception | exception_propagated | RuntimeError | True | — | — |

## Reproducibility and limitations

- Git revision: `fdd6022f962ae593db5dc2c2d9c7453bbe4377a7`; relevant source SHA-256 values are recorded in JSON.
- Configuration: `{"concurrency": {"mode": "threads", "process_mode": "not investigated", "semantic_model": "disabled", "worker_counts": [1, 2, 4]}, "large_prompt_4mib": {"reason": "Exploratory 4 MiB runs were deferred to avoid an unbounded multi-minute stress workload; no automatic size limit was added.", "status": "not_run"}, "measured_iterations_by_size": {"1MiB": 3, "2MiB": 2, "512KiB": 5}, "memory_prompt_type": "technical_protected (1 warm-up, 2 measured calls per size)", "memory_repetitions": 2, "prompt_sizes_characters": {"1MiB": 1048576, "2MiB": 2097152, "512KiB": 524288}, "prompt_types": ["clause_heavy", "technical_protected"], "tracemalloc_separate_from_latency": true, "warmups_per_size_type": 1}`
- Only threads were benchmarked; process-based concurrency was not tested.
- 4 MiB exploratory cases were not run; they are explicitly recorded as deferred.
- Traced allocations exclude native allocations that tracemalloc does not track. RSS is process-level, not per request.
- p95 was not calculated because each timing scenario has fewer than 20 samples.
- Do not extrapolate beyond tested sizes, this machine, or tested concurrency. No product limit is proposed.

## Artifacts

- Raw measurements: `milestone5b_large_input_results.json`
- This report: `milestone5b_large_input_results.md`
- Runner: `milestone5b_large_input_benchmark.py`

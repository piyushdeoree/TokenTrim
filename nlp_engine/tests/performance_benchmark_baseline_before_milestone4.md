# TokenTrim NLP Performance Benchmark

## Reproducibility

Run from the repository root:

```bash
python -m nlp_engine.tests.run_performance_benchmark
```

- Git commit: `fdd6022f962ae593db5dc2c2d9c7453bbe4377a7`
- Git worktree dirty: `True`
- Python: `3.13.5 | packaged by Anaconda, Inc. | (main, Jun 12 2025, 16:37:03) [MSC v.1929 64 bit (AMD64)]` (CPython)
- OS: `Windows-11-10.0.26300-SP0`
- CPU: `Intel64 Family 6 Model 126 Stepping 5, GenuineIntel`; logical CPUs: `4`
- Semantic model status: unavailable: sentence-transformers is not installed or the configured model is not cached locally; offline mode prevented downloads
- Execution: CPU-only; no provider/network calls were made; callbacks were deterministic local functions and the optional model probe ran offline.
- Token counts: heuristic estimates; they are not exact provider token counts.
- Dependency versions: `numpy=2.1.3`, `scikit-learn=1.6.1`, `nltk=3.9.1`, `pydantic=2.10.3`, `tiktoken=0.14.0`, `pytest=8.3.4`, `sentence-transformers=not installed`, `torch=2.10.0`, `transformers=not installed`, `huggingface-hub=not installed`, `tokenizers=not installed`, `safetensors=not installed`, `psutil=5.9.0`

The deterministic semantic stub is an in-process synthetic encoder and **does not represent Sentence-Transformers model latency or memory**. The actual local model was unavailable in this run; its rows represent model-load failure and lexical fallback only, not model performance.

## Aggregate optimization quality

Across 116 repeated full-pipeline output runs, 111 optimizations were accepted and 5 returned no optimization; the original was retained 5 times and changed 111 times. Estimated savings total 1554 tokens using the heuristic tokenizer; these are repeated-run estimates, not unique-prompt savings.
The five unchanged outputs are the 301- and 591-clause scenarios, where the existing pairwise guard skips duplicate analysis. Each includes the benchmark's exact repeated instruction, so these are five missed safe-optimization instances, not validator rejections. No false removals were observed in this controlled corpus. The final output validated in every run. Candidate validation: the safe deterministic rewrite passed in 1 configuration(s); the negation-changing candidate was rejected in 1 configuration(s). Worker/stage failures: 0.

## Warm latency

| Scenario | Input chars | Tokenizer | Pairwise clauses | Semantic path | Callback | Stage | n | p50 ms | p95 ms | max ms | Exceptions |
|---|---:|---:|---:|---|---|---|---:|---:|---:|---:|---:|
| small_2k | 1941 | heuristic_estimate | 15 | semantic_disabled | none | analysis | 10 | 25.384 | 29.252 | 29.252 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | semantic_disabled | none | optimization | 10 | 6.310 | 7.989 | 7.989 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | semantic_disabled | none | validation | 10 | 23.582 | 37.192 | 37.192 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | semantic_disabled | none | full_pipeline | 10 | 57.481 | 61.377 | 61.377 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | none | analysis | 10 | 109.380 | 133.530 | 133.530 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | none | optimization | 10 | 18.202 | 21.854 | 21.854 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | none | validation | 10 | 171.077 | 186.240 | 186.240 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | none | full_pipeline | 10 | 309.227 | 436.899 | 436.899 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | semantic_disabled | none | analysis | 5 | 341.280 | 372.270 | 372.270 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | semantic_disabled | none | optimization | 5 | 30.391 | 33.163 | 33.163 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | semantic_disabled | none | validation | 5 | 666.861 | 739.340 | 739.340 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | semantic_disabled | none | full_pipeline | 5 | 1041.826 | 1117.088 | 1117.088 | 0 |
| very_large_256k | 262071 | heuristic_estimate | 31 | semantic_disabled | none | analysis | 3 | 1512.617 | 1706.340 | 1706.340 | 0 |
| very_large_256k | 262071 | heuristic_estimate | 31 | semantic_disabled | none | optimization | 3 | 78.849 | 81.133 | 81.133 | 0 |
| very_large_256k | 262071 | heuristic_estimate | 31 | semantic_disabled | none | validation | 3 | 2686.384 | 2696.455 | 2696.455 | 0 |
| very_large_256k | 262071 | heuristic_estimate | 31 | semantic_disabled | none | full_pipeline | 3 | 4126.560 | 4130.226 | 4130.226 | 0 |
| very_large_512k | 524187 | heuristic_estimate | 31 | semantic_disabled | none | analysis | 2 | 2612.292 | 2693.448 | 2693.448 | 0 |
| very_large_512k | 524187 | heuristic_estimate | 31 | semantic_disabled | none | optimization | 2 | 149.017 | 154.355 | 154.355 | 0 |
| very_large_512k | 524187 | heuristic_estimate | 31 | semantic_disabled | none | validation | 2 | 6102.186 | 6862.526 | 6862.526 | 0 |
| very_large_512k | 524187 | heuristic_estimate | 31 | semantic_disabled | none | full_pipeline | 2 | 8252.134 | 8377.511 | 8377.511 | 0 |
| clauses_50 | 16347 | heuristic_estimate | 41 | semantic_disabled | none | analysis | 5 | 122.129 | 133.850 | 133.850 | 0 |
| clauses_50 | 16347 | heuristic_estimate | 41 | semantic_disabled | none | optimization | 5 | 21.575 | 26.703 | 26.703 | 0 |
| clauses_50 | 16347 | heuristic_estimate | 41 | semantic_disabled | none | validation | 5 | 172.516 | 190.520 | 190.520 | 0 |
| clauses_50 | 16347 | heuristic_estimate | 41 | semantic_disabled | none | full_pipeline | 5 | 318.606 | 333.547 | 333.547 | 0 |
| clauses_299 | 65503 | heuristic_estimate | 299 | semantic_disabled | none | analysis | 3 | 840.710 | 921.472 | 921.472 | 0 |
| clauses_299 | 65503 | heuristic_estimate | 299 | semantic_disabled | none | optimization | 3 | 197.181 | 197.479 | 197.479 | 0 |
| clauses_299 | 65503 | heuristic_estimate | 299 | semantic_disabled | none | validation | 3 | 697.978 | 716.873 | 716.873 | 0 |
| clauses_299 | 65503 | heuristic_estimate | 299 | semantic_disabled | none | full_pipeline | 3 | 1772.260 | 1831.412 | 1831.412 | 0 |
| clauses_300 | 65449 | heuristic_estimate | 300 | semantic_disabled | none | analysis | 3 | 828.061 | 850.203 | 850.203 | 0 |
| clauses_300 | 65449 | heuristic_estimate | 300 | semantic_disabled | none | optimization | 3 | 195.209 | 197.281 | 197.281 | 0 |
| clauses_300 | 65449 | heuristic_estimate | 300 | semantic_disabled | none | validation | 3 | 718.644 | 726.048 | 726.048 | 0 |
| clauses_300 | 65449 | heuristic_estimate | 300 | semantic_disabled | none | full_pipeline | 3 | 1706.870 | 1712.963 | 1712.963 | 0 |
| clauses_301 | 65395 | heuristic_estimate | 301 | semantic_disabled | none | analysis | 3 | 460.639 | 490.712 | 490.712 | 0 |
| clauses_301 | 65395 | heuristic_estimate | 301 | semantic_disabled | none | optimization | 3 | 109.968 | 122.127 | 122.127 | 0 |
| clauses_301 | 65395 | heuristic_estimate | 301 | semantic_disabled | none | validation | 3 | 692.549 | 694.203 | 694.203 | 0 |
| clauses_301 | 65395 | heuristic_estimate | 301 | semantic_disabled | none | full_pipeline | 3 | 1260.290 | 1288.833 | 1288.833 | 0 |
| clauses_600 | 131015 | heuristic_estimate | 591 | semantic_disabled | none | analysis | 2 | 925.217 | 929.420 | 929.420 | 0 |
| clauses_600 | 131015 | heuristic_estimate | 591 | semantic_disabled | none | optimization | 2 | 196.103 | 199.772 | 199.772 | 0 |
| clauses_600 | 131015 | heuristic_estimate | 591 | semantic_disabled | none | validation | 2 | 1411.063 | 1412.239 | 1412.239 | 0 |
| clauses_600 | 131015 | heuristic_estimate | 591 | semantic_disabled | none | full_pipeline | 2 | 2639.312 | 2654.217 | 2654.217 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | deterministic_semantic_stub | none | analysis | 10 | 35.301 | 41.321 | 41.321 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | deterministic_semantic_stub | none | optimization | 10 | 8.759 | 11.702 | 11.702 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | deterministic_semantic_stub | none | validation | 10 | 24.377 | 36.758 | 36.758 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | deterministic_semantic_stub | none | full_pipeline | 10 | 60.191 | 66.495 | 66.495 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | deterministic_semantic_stub | none | analysis | 10 | 115.943 | 124.918 | 124.918 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | deterministic_semantic_stub | none | optimization | 10 | 17.542 | 19.164 | 19.164 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | deterministic_semantic_stub | none | validation | 10 | 166.945 | 187.212 | 187.212 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | deterministic_semantic_stub | none | full_pipeline | 10 | 302.606 | 322.015 | 322.015 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | deterministic_semantic_stub | none | analysis | 5 | 350.568 | 373.859 | 373.859 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | deterministic_semantic_stub | none | optimization | 5 | 30.318 | 30.698 | 30.698 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | deterministic_semantic_stub | none | validation | 5 | 686.511 | 704.144 | 704.144 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | deterministic_semantic_stub | none | full_pipeline | 5 | 1130.806 | 1216.663 | 1216.663 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | safe_shorter | analysis | 10 | 110.693 | 132.982 | 132.982 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | safe_shorter | optimization | 10 | 21.988 | 28.129 | 28.129 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | safe_shorter | validation | 10 | 168.673 | 240.046 | 240.046 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | safe_shorter | full_pipeline | 10 | 480.282 | 548.117 | 548.117 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | lossy | analysis | 10 | 120.710 | 145.320 | 145.320 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | lossy | optimization | 10 | 17.525 | 23.097 | 23.097 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | lossy | validation | 10 | 195.960 | 218.127 | 218.127 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | lossy | full_pipeline | 10 | 476.308 | 501.033 | 501.033 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | local model unavailable; lexical fallback | none | analysis | 10 | 26.067 | 31.624 | 31.624 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | local model unavailable; lexical fallback | none | optimization | 10 | 7.098 | 9.209 | 9.209 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | local model unavailable; lexical fallback | none | validation | 10 | 23.197 | 27.959 | 27.959 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | local model unavailable; lexical fallback | none | full_pipeline | 10 | 56.607 | 65.689 | 65.689 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | analysis | 10 | 111.860 | 125.254 | 125.254 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | optimization | 10 | 16.750 | 22.917 | 22.917 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | validation | 10 | 166.574 | 176.855 | 176.855 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | full_pipeline | 10 | 301.915 | 347.454 | 347.454 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | analysis | 5 | 362.527 | 362.944 | 362.944 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | optimization | 5 | 29.077 | 30.755 | 30.755 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | validation | 5 | 699.101 | 733.027 | 733.027 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | full_pipeline | 5 | 1073.490 | 1160.443 | 1160.443 | 0 |

Warm p50/p95/max values are computed from the actual iteration counts shown. The p95 uses nearest-rank; small iteration counts therefore have correspondingly coarse percentile resolution.

## Measured operating guidance

On this recorded four-logical-CPU Windows machine, baseline full-pipeline p95 was about 1.12 s at 64k characters, 4.13 s at 256k, and 8.38 s at 512k (512k p50: 8.25 s). As measured guidance, prompts up to roughly 64k characters fit a latency-sensitive synchronous path more comfortably here; 256k–512k prompts are better suited to an asynchronous path or a caller with a multi-second latency allowance. This is not an enforced engine cap or a universal SLA.
At 512k, validation took 6.10 s p50 of the 8.25 s full-pipeline p50, making validation the main large-input bottleneck; analysis took 2.61 s and candidate optimization 0.15 s. Fresh-process imports took roughly 5.2 s p50, dominating small-prompt cold start, so a long-lived worker avoids repeating much of that fixed startup cost.
The 512k case completed without a timeout. Maximum Python traced peak allocation was about 11.8 MiB; process RSS was about 202 MB after warm-up. RSS deltas are affected by allocator and garbage-collection behavior. These are observations, not hard resource limits.

## Cold starts

Each row below comes from a fresh subprocess. `process_elapsed_ms` includes interpreter and worker startup through result serialization; `engine_import_ms` isolates package imports; `cold_first_full_pipeline_ms` measures the first detailed analysis call, including lazy semantic-model loading when applicable.

| Scenario | Semantic path | Callback | n | Process to result p50/p95/max ms | Engine import p50/p95/max ms | First pipeline p50/p95/max ms | Model load p50/p95/max ms | Failures |
|---|---|---|---:|---|---|---|---|---:|
| large_64k | deterministic_semantic_stub | none | 3 | 8304.38/8669.28/8669.28 | 6260.11/6526.56/6526.56 | 1140.78/1642.98/1642.98 | unavailable | 0 |
| large_64k | semantic_disabled | none | 3 | 7432.81/7858.48/7858.48 | 5656.56/5890.31/5890.31 | 1223.79/1277.22/1277.22 | unavailable | 0 |
| medium_16k | deterministic_semantic_stub | none | 3 | 6471.28/6482.39/6482.39 | 5352.23/5438.03/5438.03 | 352.16/362.31/362.31 | unavailable | 0 |
| medium_16k | local model unavailable; lexical fallback | none | 3 | 6151.74/6212.88/6212.88 | 5167.69/5249.57/5249.57 | 326.76/334.49/334.49 | 1.82/1.86/1.86 | 0 |
| medium_16k | semantic_disabled | lossy | 3 | 6595.65/6639.43/6639.43 | 5266.57/5370.84/5370.84 | 500.28/505.45/505.45 | unavailable | 0 |
| medium_16k | semantic_disabled | none | 3 | 6169.95/6249.73/6249.73 | 5182.30/5249.04/5249.04 | 303.39/304.83/304.83 | unavailable | 0 |
| medium_16k | semantic_disabled | safe_shorter | 3 | 6557.97/6662.41/6662.41 | 5230.22/5364.34/5364.34 | 494.24/512.94/512.94 | unavailable | 0 |
| small_2k | deterministic_semantic_stub | none | 3 | 6073.29/6488.41/6488.41 | 5223.46/5741.57/5741.57 | 95.09/97.37/97.37 | unavailable | 0 |
| small_2k | semantic_disabled | none | 3 | 5978.07/6128.50/6128.50 | 5264.02/5381.16/5381.16 | 62.17/62.42/62.42 | unavailable | 0 |

## Optimization quality and callbacks

| Scenario | Semantic path | Callback | Accepted / runs | Validations passed | Original retained / changed | Est. savings per run | LLM candidate validator | Callback invocations | Callback latency p50/p95/max ms | Exceptions |
|---|---|---|---:|---:|---|---:|---|---:|---|---:|
| small_2k | semantic_disabled | none | 10/10 | 10 | 0 / 10 | 14 | — | 0 | — | 0 |
| medium_16k | semantic_disabled | none | 10/10 | 10 | 0 / 10 | 14 | — | 0 | — | 0 |
| large_64k | semantic_disabled | none | 5/5 | 5 | 0 / 5 | 14 | — | 0 | — | 0 |
| very_large_256k | semantic_disabled | none | 3/3 | 3 | 0 / 3 | 14 | — | 0 | — | 0 |
| very_large_512k | semantic_disabled | none | 2/2 | 2 | 0 / 2 | 14 | — | 0 | — | 0 |
| clauses_50 | semantic_disabled | none | 5/5 | 5 | 0 / 5 | 14 | — | 0 | — | 0 |
| clauses_299 | semantic_disabled | none | 3/3 | 3 | 0 / 3 | 14 | — | 0 | — | 0 |
| clauses_300 | semantic_disabled | none | 3/3 | 3 | 0 / 3 | 14 | — | 0 | — | 0 |
| clauses_301 | semantic_disabled | none | 0/3 | 3 | 3 / 0 | 0 | — | 0 | — | 0 |
| clauses_600 | semantic_disabled | none | 0/2 | 2 | 2 / 0 | 0 | — | 0 | — | 0 |
| small_2k | deterministic_semantic_stub | none | 10/10 | 10 | 0 / 10 | 14 | — | 0 | — | 0 |
| medium_16k | deterministic_semantic_stub | none | 10/10 | 10 | 0 / 10 | 14 | — | 0 | — | 0 |
| large_64k | deterministic_semantic_stub | none | 5/5 | 5 | 0 / 5 | 14 | — | 0 | — | 0 |
| medium_16k | semantic_disabled | safe_shorter | 10/10 | 10 | 0 / 10 | 14 | valid=True | 12 | 0.0072/0.0115/0.0115 | 0 |
| medium_16k | semantic_disabled | lossy | 10/10 | 10 | 0 / 10 | 14 | valid=False | 12 | 0.0058/0.0118/0.0118 | 0 |
| small_2k | local model unavailable; lexical fallback | none | 10/10 | 10 | 0 / 10 | 14 | — | 0 | — | 0 |
| medium_16k | local model unavailable; lexical fallback | none | 10/10 | 10 | 0 / 10 | 14 | — | 0 | — | 0 |
| large_64k | local model unavailable; lexical fallback | none | 5/5 | 5 | 0 / 5 | 14 | — | 0 | — | 0 |

## Memory observations

| Scenario | Semantic path | Callback | Python peak allocated bytes | Process RSS before/after/delta bytes | Measurement note |
|---|---|---|---:|---|---|
| small_2k | semantic_disabled | none | 97706 | 184913920/185237504/323584 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| medium_16k | semantic_disabled | none | 455554 | 186171392/186679296/507904 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| large_64k | semantic_disabled | none | 1622774 | 187584512/189288448/1703936 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| very_large_256k | semantic_disabled | none | 6349841 | 195604480/194908160/-696320 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| very_large_512k | semantic_disabled | none | 12394901 | 200867840/203706368/2838528 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| clauses_50 | semantic_disabled | none | 451475 | 184893440/185389056/495616 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| clauses_299 | semantic_disabled | none | 2715850 | 188792832/189255680/462848 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| clauses_300 | semantic_disabled | none | 2731911 | 189571072/190238720/667648 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| clauses_301 | semantic_disabled | none | 1611599 | 187351040/188866560/1515520 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| clauses_600 | semantic_disabled | none | 3201081 | 190234624/189157376/-1077248 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| small_2k | deterministic_semantic_stub | none | 97835 | 186564608/186773504/208896 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| medium_16k | deterministic_semantic_stub | none | 455275 | 187465728/188207104/741376 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| large_64k | deterministic_semantic_stub | none | 1629189 | 189669376/191397888/1728512 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| medium_16k | semantic_disabled | safe_shorter | 483829 | 186421248/186896384/475136 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| medium_16k | semantic_disabled | lossy | 485763 | 184020992/184590336/569344 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| small_2k | local model unavailable; lexical fallback | none | 99305 | 184545280/184860672/315392 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| medium_16k | local model unavailable; lexical fallback | none | 456456 | 185970688/186466304/495616 | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| large_64k | local model unavailable; lexical fallback | none | 1631098 | 187883520/189419520/1536000 | tracemalloc peak excludes native allocations; RSS is a before/after sample |

## Failures and operating observations

- No exceptions or worker failures were recorded.

### Bottleneck and limit interpretation

Use the stage table to compare analysis, candidate generation, validation, and full-pipeline costs by input length and clause count. The 300-clause pairwise guard is an existing engine behavior; performance results do not change it. Inputs above the largest completed scenario remain unmeasured. No latency or memory threshold was imposed by this benchmark.

Any operating limit recommended from these measurements must be described as an observation for this recorded machine and configuration, not as a universal guarantee. Native model memory may exceed `tracemalloc` results; use actual-model RSS rows where available.

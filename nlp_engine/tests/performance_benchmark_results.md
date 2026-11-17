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
- Dependency versions: `numpy=2.5.4`, `scikit-learn=1.9.1`, `nltk=3.10.4`, `pydantic=2.14.3`, `tiktoken=0.14.0`, `pytest=9.2.0`, `sentence-transformers=not installed`, `torch=not installed`, `transformers=not installed`, `huggingface-hub=not installed`, `tokenizers=not installed`, `safetensors=not installed`, `psutil=not installed`

## Milestone 4 before/after comparison

The pre-change output is preserved in `performance_benchmark_baseline_before_milestone4.md` and its matching JSON file. The measurements below use the same prompt scenarios and standalone runner configuration. They are observations, not a controlled speedup claim: the recorded environments differ (including NumPy 2.1.3 vs 2.5.4, scikit-learn 1.6.1 vs 1.9.1, NLTK 3.9.1 vs 3.10.4, and `psutil` available before but unavailable after), and the after-run CPU measurements showed substantial variance. Small sample sizes are unchanged (10/10/5/3/2 iterations by increasing prompt size).

Warm validation and full-pipeline p50, milliseconds:

| Prompt | Validation before | Validation after | Full pipeline before | Full pipeline after |
|---|---:|---:|---:|---:|
| 2K | 23.582 | 24.638 | 57.481 | 60.380 |
| 16K | 171.077 | 244.998 | 309.227 | 461.749 |
| 64K | 666.861 | 1098.840 | 1041.826 | 1642.254 |
| 256K | 2686.384 | 4218.127 | 4126.560 | 6477.556 |
| 512K | 6102.186 | 5591.487 | 8252.134 | 8729.832 |

The 512K validation p50 was 8.4% lower in the after run (510.699 ms absolute); its full-pipeline p50 was 5.8% higher (477.698 ms absolute). At smaller sizes, the after run was slower, consistent with the run-to-run environmental variability and dependency drift. Do not interpret any row as a general performance guarantee. Per-run p50, p95, maximum, and sample counts are in the preserved baseline report and the current warm-latency table above.

Traced Python peak allocation for semantic-disabled, no-callback cases was effectively unchanged: 97,706→102,049 bytes (2K), 455,554→457,766 (16K), 1,622,774→1,629,110 (64K), 6,349,841→6,356,427 (256K), and 12,394,901→12,392,392 (512K). Process RSS could not be read in the after environment because `psutil` is unavailable. Cold import p50 also differs substantially (about 5.2s before vs 3.8s after), so this is not attributed to the validator change.

Separate `cProfile` runs used the benchmark prompt sizes and safe-shorter candidate. After-change instrumented totals were 59,644 calls/0.070s (2K), 214,213/0.217s (16K), 851,839/0.808s (64K), 3,366,739/3.121s (256K), and 6,636,514/6.330s (512K). At 512K, the earlier profile recorded 8,501,845 calls and 7.865s instrumented validation time. The after profile recorded 6,636,514 calls and 6.330s, about 22% fewer calls and 20% less instrumented time. Both profiles show segmentation and sentence classification as the largest remaining cost. The profiler adds substantial overhead, so these values explain call-path changes and must not be read as user-facing latency.

Functional evaluation: all 39 realistic cases matched their expected outcomes: 12 safe optimizations accepted, 17 prompts left unchanged, and 10 unsafe candidates rejected; false removals, unexpected optimizations, missed opportunities, and exceptions were zero. Focused equivalence tests compare the batched scores with the prior per-constraint helper and compare prepared-segment entity extraction with the text path. The complete suite passed (299 tests). A valid detailed pre-change 39-case snapshot was not retained, so this milestone does not claim exact end-to-end snapshot identity.

The deterministic semantic stub is an in-process synthetic encoder and **does not represent Sentence-Transformers model latency or memory**. The actual local model was unavailable in this run; its rows represent model-load failure and lexical fallback only, not model performance.

## Aggregate optimization quality

Across 116 repeated full-pipeline output runs, 111 optimizations were accepted and 5 returned no optimization; the original was retained 5 times and changed 111 times. Estimated savings total 1554 tokens using the heuristic tokenizer; these are repeated-run estimates, not unique-prompt savings.
The five unchanged outputs are the 301- and 591-clause scenarios, where the existing pairwise guard skips duplicate analysis. Each includes the benchmark's exact repeated instruction, so these are five missed safe-optimization instances, not validator rejections. No false removals were observed in this controlled corpus. The final output validated in every run. Candidate validation: the safe deterministic rewrite passed in 1 configuration(s); the negation-changing candidate was rejected in 1 configuration(s). Worker/stage failures: 0.

## Warm latency

| Scenario | Input chars | Tokenizer | Pairwise clauses | Semantic path | Callback | Stage | n | p50 ms | p95 ms | max ms | Exceptions |
|---|---:|---:|---:|---|---|---|---:|---:|---:|---:|---:|
| small_2k | 1941 | heuristic_estimate | 15 | semantic_disabled | none | analysis | 10 | 49.749 | 70.052 | 70.052 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | semantic_disabled | none | optimization | 10 | 7.614 | 9.632 | 9.632 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | semantic_disabled | none | validation | 10 | 24.638 | 33.538 | 33.538 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | semantic_disabled | none | full_pipeline | 10 | 60.380 | 96.912 | 96.912 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | none | analysis | 10 | 237.517 | 715.491 | 715.491 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | none | optimization | 10 | 27.233 | 96.232 | 96.232 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | none | validation | 10 | 244.998 | 500.761 | 500.761 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | none | full_pipeline | 10 | 461.749 | 941.779 | 941.779 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | semantic_disabled | none | analysis | 5 | 687.984 | 759.104 | 759.104 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | semantic_disabled | none | optimization | 5 | 73.046 | 95.904 | 95.904 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | semantic_disabled | none | validation | 5 | 1098.840 | 1193.807 | 1193.807 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | semantic_disabled | none | full_pipeline | 5 | 1642.254 | 1870.166 | 1870.166 | 0 |
| very_large_256k | 262071 | heuristic_estimate | 31 | semantic_disabled | none | analysis | 3 | 2932.086 | 2971.203 | 2971.203 | 0 |
| very_large_256k | 262071 | heuristic_estimate | 31 | semantic_disabled | none | optimization | 3 | 134.040 | 203.224 | 203.224 | 0 |
| very_large_256k | 262071 | heuristic_estimate | 31 | semantic_disabled | none | validation | 3 | 4218.127 | 4541.177 | 4541.177 | 0 |
| very_large_256k | 262071 | heuristic_estimate | 31 | semantic_disabled | none | full_pipeline | 3 | 6477.556 | 7762.829 | 7762.829 | 0 |
| very_large_512k | 524187 | heuristic_estimate | 31 | semantic_disabled | none | analysis | 2 | 3057.131 | 3089.542 | 3089.542 | 0 |
| very_large_512k | 524187 | heuristic_estimate | 31 | semantic_disabled | none | optimization | 2 | 201.036 | 202.483 | 202.483 | 0 |
| very_large_512k | 524187 | heuristic_estimate | 31 | semantic_disabled | none | validation | 2 | 5591.487 | 5754.425 | 5754.425 | 0 |
| very_large_512k | 524187 | heuristic_estimate | 31 | semantic_disabled | none | full_pipeline | 2 | 8729.832 | 9262.804 | 9262.804 | 0 |
| clauses_50 | 16347 | heuristic_estimate | 41 | semantic_disabled | none | analysis | 5 | 153.910 | 161.650 | 161.650 | 0 |
| clauses_50 | 16347 | heuristic_estimate | 41 | semantic_disabled | none | optimization | 5 | 23.287 | 30.554 | 30.554 | 0 |
| clauses_50 | 16347 | heuristic_estimate | 41 | semantic_disabled | none | validation | 5 | 163.783 | 177.229 | 177.229 | 0 |
| clauses_50 | 16347 | heuristic_estimate | 41 | semantic_disabled | none | full_pipeline | 5 | 345.082 | 374.736 | 374.736 | 0 |
| clauses_299 | 65503 | heuristic_estimate | 299 | semantic_disabled | none | analysis | 3 | 1001.268 | 1331.360 | 1331.360 | 0 |
| clauses_299 | 65503 | heuristic_estimate | 299 | semantic_disabled | none | optimization | 3 | 227.384 | 238.776 | 238.776 | 0 |
| clauses_299 | 65503 | heuristic_estimate | 299 | semantic_disabled | none | validation | 3 | 670.983 | 693.218 | 693.218 | 0 |
| clauses_299 | 65503 | heuristic_estimate | 299 | semantic_disabled | none | full_pipeline | 3 | 1895.211 | 2034.847 | 2034.847 | 0 |
| clauses_300 | 65449 | heuristic_estimate | 300 | semantic_disabled | none | analysis | 3 | 1036.341 | 1042.380 | 1042.380 | 0 |
| clauses_300 | 65449 | heuristic_estimate | 300 | semantic_disabled | none | optimization | 3 | 244.559 | 250.413 | 250.413 | 0 |
| clauses_300 | 65449 | heuristic_estimate | 300 | semantic_disabled | none | validation | 3 | 626.656 | 687.584 | 687.584 | 0 |
| clauses_300 | 65449 | heuristic_estimate | 300 | semantic_disabled | none | full_pipeline | 3 | 1972.639 | 1988.906 | 1988.906 | 0 |
| clauses_301 | 65395 | heuristic_estimate | 301 | semantic_disabled | none | analysis | 3 | 550.990 | 628.683 | 628.683 | 0 |
| clauses_301 | 65395 | heuristic_estimate | 301 | semantic_disabled | none | optimization | 3 | 132.228 | 139.655 | 139.655 | 0 |
| clauses_301 | 65395 | heuristic_estimate | 301 | semantic_disabled | none | validation | 3 | 656.868 | 666.785 | 666.785 | 0 |
| clauses_301 | 65395 | heuristic_estimate | 301 | semantic_disabled | none | full_pipeline | 3 | 1347.758 | 1392.742 | 1392.742 | 0 |
| clauses_600 | 131015 | heuristic_estimate | 591 | semantic_disabled | none | analysis | 2 | 1112.583 | 1157.477 | 1157.477 | 0 |
| clauses_600 | 131015 | heuristic_estimate | 591 | semantic_disabled | none | optimization | 2 | 191.123 | 203.985 | 203.985 | 0 |
| clauses_600 | 131015 | heuristic_estimate | 591 | semantic_disabled | none | validation | 2 | 1070.450 | 1081.726 | 1081.726 | 0 |
| clauses_600 | 131015 | heuristic_estimate | 591 | semantic_disabled | none | full_pipeline | 2 | 2085.886 | 2114.907 | 2114.907 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | deterministic_semantic_stub | none | analysis | 10 | 26.994 | 28.945 | 28.945 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | deterministic_semantic_stub | none | optimization | 10 | 7.840 | 12.246 | 12.246 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | deterministic_semantic_stub | none | validation | 10 | 20.213 | 22.938 | 22.938 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | deterministic_semantic_stub | none | full_pipeline | 10 | 54.904 | 60.244 | 60.244 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | deterministic_semantic_stub | none | analysis | 10 | 105.922 | 112.399 | 112.399 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | deterministic_semantic_stub | none | optimization | 10 | 16.584 | 19.834 | 19.834 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | deterministic_semantic_stub | none | validation | 10 | 157.216 | 178.623 | 178.623 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | deterministic_semantic_stub | none | full_pipeline | 10 | 253.051 | 279.245 | 279.245 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | deterministic_semantic_stub | none | analysis | 5 | 321.104 | 327.038 | 327.038 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | deterministic_semantic_stub | none | optimization | 5 | 30.099 | 36.656 | 36.656 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | deterministic_semantic_stub | none | validation | 5 | 490.450 | 496.807 | 496.807 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | deterministic_semantic_stub | none | full_pipeline | 5 | 875.693 | 1218.333 | 1218.333 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | safe_shorter | analysis | 10 | 142.297 | 244.333 | 244.333 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | safe_shorter | optimization | 10 | 17.221 | 18.510 | 18.510 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | safe_shorter | validation | 10 | 127.849 | 135.550 | 135.550 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | safe_shorter | full_pipeline | 10 | 383.880 | 439.238 | 439.238 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | lossy | analysis | 10 | 101.683 | 107.054 | 107.054 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | lossy | optimization | 10 | 14.848 | 17.026 | 17.026 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | lossy | validation | 10 | 126.925 | 134.063 | 134.063 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | semantic_disabled | lossy | full_pipeline | 10 | 399.176 | 523.627 | 523.627 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | local model unavailable; lexical fallback | none | analysis | 10 | 23.910 | 25.849 | 25.849 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | local model unavailable; lexical fallback | none | optimization | 10 | 6.416 | 9.166 | 9.166 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | local model unavailable; lexical fallback | none | validation | 10 | 20.580 | 23.312 | 23.312 | 0 |
| small_2k | 1941 | heuristic_estimate | 15 | local model unavailable; lexical fallback | none | full_pipeline | 10 | 54.240 | 58.994 | 58.994 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | analysis | 10 | 107.978 | 114.388 | 114.388 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | optimization | 10 | 15.384 | 31.597 | 31.597 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | validation | 10 | 129.257 | 157.612 | 157.612 | 0 |
| medium_16k | 16245 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | full_pipeline | 10 | 255.310 | 260.919 | 260.919 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | analysis | 5 | 318.929 | 326.035 | 326.035 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | optimization | 5 | 27.170 | 27.965 | 27.965 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | validation | 5 | 536.039 | 541.914 | 541.914 | 0 |
| large_64k | 65489 | heuristic_estimate | 31 | local model unavailable; lexical fallback | none | full_pipeline | 5 | 877.674 | 909.505 | 909.505 | 0 |

Warm p50/p95/max values are computed from the actual iteration counts shown. The p95 uses nearest-rank; small iteration counts therefore have correspondingly coarse percentile resolution.

## Measured operating guidance

On this recorded four-logical-CPU Windows machine, baseline full-pipeline p95 was about 1.87 s at 64k characters, 7.76 s at 256k, and 9.26 s at 512k (512k p50: 8.73 s). As measured guidance, prompts up to roughly 64k characters fit a latency-sensitive synchronous path more comfortably here; 256k–512k prompts are better suited to an asynchronous path or a caller with a multi-second latency allowance. This is not an enforced engine cap or a universal SLA.
At 512k, validation took 5.59 s p50 of the 8.73 s full-pipeline p50, making validation the main large-input bottleneck; analysis took 3.06 s and candidate optimization 0.20 s. Fresh-process imports took roughly 5.2 s p50, dominating small-prompt cold start, so a long-lived worker avoids repeating much of that fixed startup cost.
The 512k case completed without a timeout. Maximum Python traced peak allocation was about 11.8 MiB; process RSS was about 202 MB after warm-up. RSS deltas are affected by allocator and garbage-collection behavior. These are observations, not hard resource limits.

## Cold starts

Each row below comes from a fresh subprocess. `process_elapsed_ms` includes interpreter and worker startup through result serialization; `engine_import_ms` isolates package imports; `cold_first_full_pipeline_ms` measures the first detailed analysis call, including lazy semantic-model loading when applicable.

| Scenario | Semantic path | Callback | n | Process to result p50/p95/max ms | Engine import p50/p95/max ms | First pipeline p50/p95/max ms | Model load p50/p95/max ms | Failures |
|---|---|---|---:|---|---|---|---|---:|
| large_64k | deterministic_semantic_stub | none | 3 | 5229.49/5285.06/5285.06 | 3755.17/3813.61/3813.61 | 892.29/900.76/900.76 | unavailable | 0 |
| large_64k | semantic_disabled | none | 3 | 5235.01/5275.07/5275.07 | 3794.69/3815.40/3815.40 | 876.12/891.29/891.29 | unavailable | 0 |
| medium_16k | deterministic_semantic_stub | none | 3 | 4689.46/5299.81/5299.81 | 3837.90/4198.07/4198.07 | 286.81/529.76/529.76 | unavailable | 0 |
| medium_16k | local model unavailable; lexical fallback | none | 3 | 4628.95/4679.91/4679.91 | 3788.17/3811.67/3811.67 | 277.47/296.19/296.19 | 1.33/1.36/1.36 | 0 |
| medium_16k | semantic_disabled | lossy | 3 | 4929.67/5104.78/5104.78 | 3849.37/3941.16/3941.16 | 414.42/433.60/433.60 | unavailable | 0 |
| medium_16k | semantic_disabled | none | 3 | 4592.23/4661.95/4661.95 | 3775.00/3831.17/3831.17 | 267.35/267.97/267.97 | unavailable | 0 |
| medium_16k | semantic_disabled | safe_shorter | 3 | 4841.00/4891.90/4891.90 | 3771.39/3809.13/3809.13 | 400.58/403.36/403.36 | unavailable | 0 |
| small_2k | deterministic_semantic_stub | none | 3 | 4472.91/4559.29/4559.29 | 3865.11/3880.20/3880.20 | 78.19/95.74/95.74 | unavailable | 0 |
| small_2k | semantic_disabled | none | 3 | 4400.08/4514.59/4514.59 | 3778.76/3836.60/3836.60 | 76.87/79.19/79.19 | unavailable | 0 |

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
| medium_16k | semantic_disabled | safe_shorter | 10/10 | 10 | 0 / 10 | 14 | valid=True | 12 | 0.0061/0.0134/0.0134 | 0 |
| medium_16k | semantic_disabled | lossy | 10/10 | 10 | 0 / 10 | 14 | valid=False | 12 | 0.0068/0.0186/0.0186 | 0 |
| small_2k | local model unavailable; lexical fallback | none | 10/10 | 10 | 0 / 10 | 14 | — | 0 | — | 0 |
| medium_16k | local model unavailable; lexical fallback | none | 10/10 | 10 | 0 / 10 | 14 | — | 0 | — | 0 |
| large_64k | local model unavailable; lexical fallback | none | 5/5 | 5 | 0 / 5 | 14 | — | 0 | — | 0 |

## Memory observations

| Scenario | Semantic path | Callback | Python peak allocated bytes | Process RSS before/after/delta bytes | Measurement note |
|---|---|---|---:|---|---|
| small_2k | semantic_disabled | none | 102049 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| medium_16k | semantic_disabled | none | 457766 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| large_64k | semantic_disabled | none | 1629110 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| very_large_256k | semantic_disabled | none | 6356427 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| very_large_512k | semantic_disabled | none | 12392392 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| clauses_50 | semantic_disabled | none | 451164 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| clauses_299 | semantic_disabled | none | 1701768 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| clauses_300 | semantic_disabled | none | 1715626 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| clauses_301 | semantic_disabled | none | 1600443 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| clauses_600 | semantic_disabled | none | 3201957 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| small_2k | deterministic_semantic_stub | none | 101678 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| medium_16k | deterministic_semantic_stub | none | 458186 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| large_64k | deterministic_semantic_stub | none | 1630375 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| medium_16k | semantic_disabled | safe_shorter | 487691 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| medium_16k | semantic_disabled | lossy | 488216 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| small_2k | local model unavailable; lexical fallback | none | 103285 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| medium_16k | local model unavailable; lexical fallback | none | 459270 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |
| large_64k | local model unavailable; lexical fallback | none | 1626783 | unavailable | tracemalloc peak excludes native allocations; RSS is a before/after sample |

## Failures and operating observations

- No exceptions or worker failures were recorded.

### Bottleneck and limit interpretation

Use the stage table to compare analysis, candidate generation, validation, and full-pipeline costs by input length and clause count. The 300-clause pairwise guard is an existing engine behavior; performance results do not change it. Inputs above the largest completed scenario remain unmeasured. No latency or memory threshold was imposed by this benchmark.

Any operating limit recommended from these measurements must be described as an observation for this recorded machine and configuration, not as a universal guarantee. Native model memory may exceed `tracemalloc` results; use actual-model RSS rows where available.

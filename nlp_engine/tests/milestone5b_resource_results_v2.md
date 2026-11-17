# TokenTrim Milestone 5B — Large-Input & Resource Characterization Report (v2)

## 1. Executive Summary

This independent benchmark characterization evaluates the TokenTrim NLP Engine across large inputs,
memory allocation scaling, repeated stability, multi-process concurrency, and cross-process output determinism.
Production code remained untouched throughout this milestone.

## 2. Environment Specifications

- **Operating System:** Windows 11 (10.0.26300)
- **Python Version:** 3.13.5
- **Processor / Architecture:** Intel64 Family 6 Model 126 Stepping 5, GenuineIntel (4 logical cores)
- **Pytest Version:** 9.2.0
- **NumPy Version:** 2.5.4
- **Pydantic Version:** 2.14.3
- **tiktoken Version:** 0.14.0
- **Execution Isolation Mode:** `subprocess`
- **Checkpoint Mode:** Atomic per-sample JSON persistence (`os.replace`)

## 3. Large-Input Scaling & Latency Results

| Scenario ID | Profile | Target Bytes | Chars | Samples | Min ms | Median ms | Mean ms | Max ms | SD ms | Peak Traced MiB | Fallback | Integrity |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| `512KiB_clause_heavy` | `clause_heavy` | 524288 | 524288 | 3 | 16085.9 | 16429.5 | 16370.7 | 16596.8 | 260.5 | 11.6 | yes | **PASS** |
| `512KiB_technical_protected` | `technical_protected` | 524288 | 507245 | 3 | 9136.6 | 9281.2 | 9388.0 | 9746.4 | 318.7 | 15.6 | yes | **PASS** |
| `512KiB_multisection_spec` | `multisection_spec` | 524288 | 524288 | 3 | 14444.1 | 14454.3 | 14453.3 | 14461.4 | 8.7 | 12.0 | yes | **PASS** |
| `1MiB_clause_heavy` | `clause_heavy` | 1048576 | 1048576 | 2 | 34296.2 | 34860.8 | 34860.8 | 35425.3 | 798.3 | 22.4 | yes | **PASS** |
| `1MiB_technical_protected` | `technical_protected` | 1048576 | 1014490 | 2 | 17971.6 | 18009.1 | 18009.1 | 18046.5 | 52.9 | 35.0 | yes | **PASS** |
| `1MiB_multisection_spec` | `multisection_spec` | 1048576 | 1048576 | 2 | 28793.2 | 28831.4 | 28831.4 | 28869.7 | 54.1 | 23.5 | yes | **PASS** |
| `2MiB_clause_heavy` | `clause_heavy` | 2097152 | 2097152 | 2 | 64758.4 | 64989.2 | 64989.2 | 65220.1 | 326.4 | 41.8 | yes | **PASS** |
| `2MiB_technical_protected` | `technical_protected` | 2097152 | 2028980 | 2 | 35973.8 | 36007.9 | 36007.9 | 36042.1 | 48.3 | 61.4 | yes | **PASS** |
| `2MiB_multisection_spec` | `multisection_spec` | 2097152 | 2097152 | 2 | 61225.5 | 61283.4 | 61283.4 | 61341.4 | 82.0 | 40.5 | yes | **PASS** |

## 4. Multi-Process Concurrency Scaling

- **Concurrency Model:** Isolated OS subprocess workers coordinated by a lightweight dispatcher pool under Win32 Job Object hard timeout enforcement.
- **Scope Note:** This experiment characterizes multi-process parallel throughput and cross-process deterministic equivalence against sequential baselines. In-process multi-threaded concurrency is intentionally outside the scope of this hard-timeout benchmark because Python threads cannot be forcibly terminated on timeout without risking interpreter state corruption.

| Worker Level | Total Reqs | Success | Failures | Match Sequential | Wall Time ms | Throughput (req/s) | Median Latency ms | Process Isolation |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| `1 workers` | 8 | 8 | 0 | 8 | 31271.0 | 0.26 | 78.1 | **VERIFIED** |
| `2 workers` | 8 | 8 | 0 | 8 | 18377.5 | 0.44 | 88.4 | **VERIFIED** |
| `4 workers` | 8 | 8 | 0 | 8 | 13254.7 | 0.60 | 133.2 | **VERIFIED** |
| `8 workers` | 8 | 8 | 0 | 8 | 12278.8 | 0.65 | 188.9 | **VERIFIED** |

## 5. Memory Allocation Scaling & Stability Results

- **Isolation Mode:** Subprocess-isolated
- **Note on Isolation:** When run under subprocess isolation, peak tracemalloc and RSS reflect per-request footprint under hard kernel timeout enforcement. Cumulative RSS retention across iterations is characterized during in-process runs.

| Series | Iteration | Latency ms | Peak Traced MiB | Net Traced Delta MiB | RSS Start MiB | RSS Peak MiB | Status |
|---|---:|---:|---:|---:|---:|---:|:---:|
| Identical | 1 | 8854.9 | 15.63 | 1.65 | 142.39 | 170.41 | `OK` |
| Identical | 2 | 8901.0 | 15.63 | 1.65 | 142.07 | 169.45 | `OK` |
| Identical | 3 | 9014.0 | 15.63 | 1.65 | 142.02 | 168.66 | `OK` |
| Identical | 4 | 8892.3 | 15.63 | 1.65 | 142.13 | 169.55 | `OK` |
| Identical | 5 | 8923.5 | 15.63 | 1.65 | 142.48 | 169.03 | `OK` |
| Alternating | 1 | 15880.5 | 11.56 | 2.16 | 141.44 | 166.42 | `OK` |
| Alternating | 2 | 8983.0 | 15.63 | 1.65 | 142.27 | 169.31 | `OK` |
| Alternating | 3 | 15972.6 | 11.56 | 2.16 | 141.09 | 166.31 | `OK` |
| Alternating | 4 | 9012.9 | 15.63 | 1.65 | 142.2 | 169.21 | `OK` |
| Alternating | 5 | 16157.2 | 11.56 | 2.16 | 141.77 | 166.29 | `OK` |

## 6. Status: Complete

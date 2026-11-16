# NLP Engine Completion Roadmap

**Status date:** 2026-11-16  
**Scope:** The independent `nlp_engine` package only. Frontend, backend, cost-engine, and project prompt-generation work are out of scope.

## Completion objective

Reduce unnecessary prompt tokens when a safe optimization can be established, while preserving the original meaning, intent, requirements, and constraints. If safety or actual token savings cannot be established, return the original prompt.

## Current checkpoint

The core implementation is present. The engine has reached a **stabilization and evidence-gathering phase**, not a release-complete state. Current evidence in this working tree:

- Full NLP pytest suite after the public API contract milestone: **296 passed** (fresh run, 2026-11-16, Python 3.13.5).
- Focused public API contract tests: **7 passed**.
- Curated redundancy benchmark: **50/50 cases passed**.
- The curated cases also run through the full analyzer/optimizer/validator pipeline.
- Expanded realistic public-pipeline corpus: **39 cases** (20 baseline plus 19 additions) across the same five categories; latest run matched **39/39** expected behaviors, with **0 false removals**, **0 unexpected optimizations**, **0 missed opportunities**, **0 exceptions**, and **180 estimated tokens saved**.
- Expanded-corpus outcome counts: **12/12** safe opportunities accepted, **17/17** expected unchanged cases left unchanged, and **10/10** unsafe LLM candidates rejected with exact-original fallback.
- The `technical_02` missed opportunity was closed by recognizing `emit` as an instruction and a clause boundary verb. The repeated directive is removed while the first output-contract label and instruction remain. Existing strict lexical subsumption and validator behavior are unchanged.
- The semantic model remains optional and disabled by default; tests cover missing dependency/model and encoding failures.
- The LLM rewrite callback is optional; candidate selection, lossy candidates, exceptions, and injection-shaped input have test coverage.
- No completion claim is a claim of mathematical semantic equivalence.

These tests and implementations are in the current working tree. They are not a substitute for validating the criteria below against a broader prompt set.

## Requirement status

| Area | Status | Evidence and remaining work |
|---|---|---|
| Public analysis APIs and detailed result | Documented and contract-tested; remaining caveats recorded | Existing root exports are preserved. Approved additive exports include the detailed result and validation/tokenizer types. The response shape is unchanged; `Issue.type` remains a general string, and lower-level return types and fallback candidate semantics are documented. |
| Prompt feature extraction and issue detection | Implemented, heuristic | Token/complexity features, verbosity, formatting, context, conflict, repeated phrase, and redundancy findings exist. Detector quality still needs measurement on varied realistic prompts. |
| Conservative heuristic optimization | Implemented | Rewrites are rule-based; protected spans/context are guarded; removal relies on strict lexical subsumption. Realistic corpus testing remains. |
| Semantic similarity | Implemented, optional | Lazy model loading, environment configuration, and graceful fallback are present. Similarity is advisory only. Coverage currently uses a small hand-authored corpus; thresholds need broader evaluation. |
| LLM rewrite candidates | Implemented and contract-tested as a callback extension | Callback input is the complete JSON-encoded rewrite request; callback failures and malformed outputs fall back safely. Real provider calls and provider credentials belong to integration owners. |
| Validation and preservation | Implemented, heuristic | Checks cover numbers, polarity, identifiers, protected spans, formats, constraints, ordering, conditions, exceptions, and scope. They detect known loss patterns but cannot prove semantic equivalence. More adversarial and realistic cases are needed. |
| Token counting and savings | Implemented | Exact `tiktoken` counts where available and labelled heuristic estimates otherwise. Candidate comparisons use the same counter. More edge coverage is needed for tokenizer errors and unusual Unicode/token inputs. |
| Fallback and optional-component errors | Implemented and tested | Invalid, empty, non-saving, or failing LLM candidates fall back; semantic model failures degrade to lexical behavior. Verify exact public fallback fields and state behavior across repeated calls. |
| Performance | Baseline measured; environment coverage remains | A standalone CPU-only benchmark records prompt-size and clause-count scaling, stage p50/p95/max, cold starts, memory observations, callback quality, and optional semantic modes. The actual cached model was unavailable in the recorded environment, so its performance remains unmeasured. |
| Realistic quality evaluation | Expanded; evidence remains curated | A 39-case multi-section corpus covers five domains and runs through the public detailed API. The latest run has zero false removals and zero missed opportunities. The corpus is not proof of general safety; broader independently reviewed prompts remain useful. |
| Language support | Deliberately limited | The engine is English-focused and leaves non-Latin text untouched. Broader language support is not required for completion unless scope changes. |

## Objective completion gates

The engine is complete when all of these gates are met and recorded here:

1. **Safety corpus:** All curated and realistic test cases pass. No case designated `preserve_both` is shortened by deletion; no similar-only pair is removed; all required numbers, negation, conditions, exceptions, order, scope, identifiers, code, URLs, paths, and output formats survive.
2. **Conservative acceptance:** Every accepted result is validator-approved and has strictly positive savings under one tokenizer used consistently for both versions. Every rejected, invalid, failing, or non-saving candidate returns the exact original prompt and reports zero tokens saved.
3. **Measured optimization quality:** On a reviewed realistic corpus, report (a) safe duplicate detection recall, (b) false-removal count, (c) accepted safe optimizations, (d) token savings, and (e) validator rejection/fallback counts. Required safety cases must have **zero false removals**. Savings are reported as a measured outcome, not a target that can override safety.
4. **Public API contract:** Import smoke tests and contract tests verify exported names, required response keys/types, consistent token metrics, winning-candidate/validation correspondence, and documented exceptions. No public contract changes without explicit review.
5. **Optional path reliability:** With optional dependencies absent and semantic similarity disabled, the core engine works. Model load/encode failures and LLM callback exceptions return to the safe baseline without leaking failures or accepting unchecked output.
6. **Performance evidence:** Benchmark representative short, medium, and long prompts on a recorded reference environment; publish p50/p95 latency and memory observations. Derive any operating guidance from measured behavior and deployment needs; do not impose generic performance limits without evidence.
7. **Regression suite and docs:** The complete NLP test suite passes; benchmark outputs match the current code; public docs reflect actual test commands, counts, token-count limitations, and API behavior.

## Remaining roadmap

### Public API contract and documentation — 2026-11-16

The package root now additively exports `DetailedAnalysis`, `OptimizationResult`,
`ValidationResult`, `TokenizerInfo`, and `BaseTokenCounter`. Existing exports
and `AnalysisResponse` fields are preserved. A focused public contract module
adds seven checks for exports, result types, exact-original fallback, tokenizer
metadata, candidate-vs-validation behavior, lazy optional-model loading, and
LLM failure fallback.

Fresh verification used Python 3.13.5: the focused module passed **7/7**; the
full NLP suite passed **296 tests**; the 20-case realistic evaluation matched
**20/20**, with zero false removals, zero missed opportunities, and 148
estimated tokens saved. The evaluation runner's pre-existing report file was
not overwritten during this run. Documentation now records the actual
thread-safety caveats, semantic-model settings and download possibility,
token-count semantics, callback and candidate contracts, exact-original
fallback, protection-pattern limitations, tokenizer registration lifetime,
and the absence of a documented prompt-size limit.

Remaining contract caveats are explicitly documented: `build_analysis()`
returns internal state despite remaining exported for compatibility;
`optimize_prompt()` returns an unvalidated candidate; the simple response
does not include tokenizer exactness metadata; and `Issue.type` is not an enum.

### Performance baseline recorded — 2026-11-16

The standalone runner is `tests/run_performance_benchmark.py`, with deterministic inputs in
`tests/performance_prompts.json`. It is separate from ordinary pytest collection and produces
`tests/performance_benchmark_results.json` plus `tests/performance_benchmark_results.md`.
The run covers 2k–512k-character prompts and exactly 299, 300, and 301 comparable clauses,
with CPU-only execution and offline model loading. The semantic stub is synthetic; the actual
Sentence-Transformers model was unavailable in this environment, and no model performance claim
is made. Across 18 warm configurations and 27 cold subprocesses, there were 116 repeated pipeline
outputs: 111 accepted optimizations, five safe unchanged fallbacks, and 1,554 heuristic-estimated
tokens saved. The five unchanged outputs were at 301 and 591 clauses; their exact repeated instruction
was retained because the existing pairwise guard skipped duplicate analysis, so these are measured
missed optimization instances. No false removals occurred in this controlled corpus. The deterministic
safe rewrite passed validation; the negation-changing candidate was rejected. No worker or stage failures
occurred. Baseline full-pipeline p50 rose from about
57 ms at 2k characters to 8.25 s at 512k; the 512k p95/max uses only two samples. Validation was
the largest 512k stage at 6.10 s p50. At 301 and 591 comparable clauses the engine retained the
original prompt under its existing 300-clause pairwise guard. See the report for the machine,
package versions, iteration counts, memory limitations, and measured operating guidance. No
product threshold was added.

### Validation performance reuse — 2026-11-16

The validator now reuses the already-prepared optimized prompt segments for
entity extraction. Constraint matching also computes each eligible candidate
segment's negation and content stems once per validation call, while retaining
the same exhaustive constraint-to-segment comparisons, polarity checks,
coverage formula, and threshold. No global cache or new mutable shared state
was introduced. The 300-clause guard and all validation rules are unchanged.

Focused reference-equivalence tests passed, followed by the full NLP suite
(299 passed). The 39-case public-pipeline evaluation matched its expected
outcomes: 12 safe optimizations accepted,
17 unchanged cases, 10 unsafe candidates rejected, zero false removals, and
180 estimated tokens saved.

Focused tests compare the batched coverage results with the prior per-
constraint helper and confirm equivalent entity extraction through prepared
segments. A valid detailed pre-change 39-case snapshot was not retained, so
exact pre/post end-to-end snapshot identity is not claimed.

The standalone after benchmark completed all configured warm and cold runs
without worker failures. Its result and the preserved before files are under
`tests/`. Direct wall-time comparisons are not controlled: dependency versions
changed between the archived run and this run, and results varied substantially
at smaller sizes. At 512K, validation p50 was 6.10s before and 5.59s after,
while full-pipeline p50 was 8.25s before and 8.73s after. A matching profiled
512K validation decreased from 8.50M to 6.79M calls and from 7.87s to 6.32s
instrumented time. Treat this as evidence of less repeated work, not a broad
latency guarantee. See `tests/performance_benchmark_results.md` for the
limitations and complete measurements.

**Current validation change:** `nlp_engine/validator.py`; equivalence coverage:
`nlp_engine/tests/test_validator_performance_reuse.py`.

### Expanded realistic evaluation corpus — 2026-11-16

Milestone 3 preserved all 20 baseline IDs and expectations and added 19 cases,
for 39 total. New coverage includes section-scoped requirements, frontend and
backend distinctions, retry conditions and idempotency, separate output
contracts, nested null/threshold/exception handling, technical literals and
identifiers, English mixed with Sinhala and Spanish, concise no-op prompts,
two long multi-section specifications, and unsafe rewrite candidates that
alter negation, numeric limits, conditions/exceptions, output formats,
technical identifiers, or section-specific requirements.

The runner now reports baseline versus new-case cohorts, category and expected-
outcome distributions, scenario coverage, aggregate estimated input/output
tokens and reduction, exact-original fallbacks, unexpected exceptions, and a
rationale for every case. It continues to run the public `analyze_prompt_detailed()`
pipeline with semantic similarity disabled and deterministic local callbacks.

Fresh evaluation matched **39/39** cases: 12/12 safe optimizations accepted,
17/17 unchanged prompts retained, and 10/10 unsafe candidates rejected with
fallback. False removals, unexpected optimizations, missed opportunities, and
exceptions were all zero. Estimated token totals were 5,811 original and 5,631
final, saving 180 estimated tokens (3.10% aggregate). The fixed heuristic
counter was used; these are corpus measurements, not a universal correctness
or quality guarantee. The full NLP suite passed **296 tests** after this
milestone. No production engine logic changed.

**Current artifacts:** `nlp_engine/tests/realistic_evaluation_dataset.json`,
`nlp_engine/tests/run_realistic_evaluation.py`, and the regenerated
`nlp_engine/tests/realistic_evaluation_results.md`.

**Current artifacts:** `nlp_engine/tests/realistic_evaluation_dataset.json`, `nlp_engine/tests/run_realistic_evaluation.py`, and the generated `nlp_engine/tests/realistic_evaluation_results.md`.

### 2. Close gaps from corpus results

Fix only reproducible detector, preservation, or fallback failures. For each issue, add a focused regression test, run its tests, then the complete NLP suite and quality evaluation.

### 3. Repeat performance measurements where the environment changes

Repeat the standalone benchmark on target deployment machines and with an actually cached semantic model if that optional path will be enabled. Compare results against this baseline before proposing deployment-specific limits.

### 4. Follow-up public API review

The approved export and documentation reconciliation work is complete for this
milestone. Any later API behavior changes, response-shape changes, or broader
input-validation policy require a separate review. Keep backend/frontend
compatibility read-only and do not change their code.

## Progress tracking rules

- Update this document after each meaningful NLP milestone with date, changed areas, tests/evaluation, results, and remaining gates.
- Distinguish implementation present from quality evidence collected.
- Preserve the user's existing working-tree changes; do not treat an uncommitted implementation as released.
- Never use a benchmark score to justify weakening semantic-preservation checks.

### Large-prompt and edge-case reliability — 2026-11-16

Added `tests/test_milestone5_reliability.py` with 27 public-pipeline checks for
empty/minimal inputs, exact no-op fallback with unusual whitespace, section
scoping, distinct values and formats, contradictions, code/URL/identifier
preservation, the existing 299/300/301 clause boundary, semantic-encoding
failure fallback, and deterministic repeated analysis. The suite also checks a
300-section prompt and an exact 512K-character prompt. No production defect was
reproduced, so no runtime implementation or public contract was changed.

Fresh verification on Python 3.13.5: the new module passed **27/27**, requested
focused groups passed **197 tests**, and the complete NLP suite passed **326
tests**. The 39-case public-pipeline evaluation matched **39/39**: 12 safe
optimizations, 17 unchanged prompts, and 10 rejected unsafe candidates; zero
false removals, unexpected optimizations, missed opportunities, or exceptions;
180 estimated tokens saved. Its report was written to a temporary location to
preserve the existing local evaluation artifact.

A one-off public-pipeline stress probe processed a 1 MiB context prompt in
14.49 seconds with 21.8 MiB traced peak allocations, rejected optimization,
and returned the exact original prompt. This is one local observation, not a
latency guarantee or configured input limit. The existing Milestone 4A A/B
benchmark was not rerun because production code was unchanged; its results and
profile artifacts remain the historical performance reference.

**Remaining evidence gaps:** the 300-clause pairwise guard intentionally
disables duplicate comparison above its threshold, so repeated text beyond the
guard may remain unoptimized. This is a conservative missed-compression case,
not data loss. The engine still has no documented maximum prompt length;
behavior beyond 1 MiB and memory use under concurrent large requests are not
characterized. Language handling remains English-focused, and the surface
validator cannot prove general semantic equivalence or resolve contradictions.
Milestone 5 remains **partially complete** until broader independently reviewed
edge-case coverage and deployment-specific operating evidence are available.

# TokenTrim Semantic Benchmark

- Dataset: `evaluation_dataset.json`
- Total cases: 50
- Passed: 40
- Failed: 10
- Pass rate: 80.0%
- Pretrained semantic model enabled: `False`

## Case results

| ID | Category | Expected | Actual | Result | Clauses | Pairs | Removals | Time (ms) |
|---|---|---|---|:---:|---:|---:|---:|---:|
| exact_duplicate_01 | exact_duplicates | duplicate_detected | duplicate_detected | PASS | 2 | 1 | 1 | 11.16 |
| exact_duplicate_02 | exact_duplicates | duplicate_detected | duplicate_detected | PASS | 3 | 1 | 1 | 5.06 |
| paraphrase_01 | paraphrased_instructions | similarity_detected | not_detected | FAIL | 2 | 0 | 0 | 6.21 |
| paraphrase_02 | paraphrased_instructions | similarity_detected | not_detected | FAIL | 2 | 0 | 0 | 4.83 |
| different_meaning_01 | different_meanings | preserve_both | preserved | PASS | 2 | 1 | 0 | 15.34 |
| different_meaning_02 | different_meanings | preserve_both | preserved | PASS | 2 | 0 | 0 | 14.86 |
| negation_01 | negation | preserve_both | preserved | PASS | 2 | 0 | 0 | 9.08 |
| negation_02 | negation | preserve_both | preserved | PASS | 2 | 0 | 0 | 3.54 |
| numeric_01 | numeric_constraints | preserve_both | preserved | PASS | 2 | 0 | 0 | 4.19 |
| numeric_02 | numeric_constraints | preserve_both | preserved | PASS | 2 | 0 | 0 | 8.97 |
| technical_01 | technical_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 4.00 |
| technical_02 | technical_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 4.47 |
| conditional_01 | conditional_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 9.16 |
| conditional_02 | conditional_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 4.22 |
| sequence_01 | instruction_sequence | preserve_both | preserved | PASS | 3 | 0 | 0 | 5.65 |
| sequence_02 | instruction_sequence | preserve_both | preserved | PASS | 2 | 0 | 0 | 6.67 |
| repeated_context_01 | repeated_with_context | duplicate_detected | duplicate_detected | PASS | 3 | 1 | 1 | 15.38 |
| repeated_context_02 | repeated_with_context | duplicate_detected | duplicate_detected | PASS | 3 | 1 | 1 | 8.09 |
| scope_01 | scope_and_completeness | preserve_both | preserved | PASS | 2 | 0 | 0 | 7.30 |
| scope_02 | scope_and_completeness | preserve_both | preserved | PASS | 2 | 0 | 0 | 4.26 |
| exact_duplicate_03 | exact_duplicates | duplicate_detected | duplicate_detected | PASS | 2 | 1 | 1 | 6.60 |
| exact_duplicate_04 | repeated_with_context | duplicate_detected | duplicate_detected | PASS | 3 | 1 | 1 | 6.23 |
| exact_duplicate_05 | exact_duplicates | duplicate_detected | duplicate_detected | PASS | 2 | 1 | 1 | 2.82 |
| exact_duplicate_06 | repeated_with_context | duplicate_detected | duplicate_detected | PASS | 3 | 1 | 1 | 6.58 |
| exact_duplicate_07 | exact_duplicates | duplicate_detected | duplicate_detected | PASS | 2 | 1 | 1 | 24.10 |
| exact_duplicate_08 | repeated_with_context | duplicate_detected | duplicate_detected | PASS | 3 | 1 | 1 | 3.41 |
| paraphrase_03 | paraphrased_instructions | similarity_detected | not_detected | FAIL | 2 | 0 | 0 | 5.61 |
| paraphrase_04 | paraphrased_instructions | similarity_detected | not_detected | FAIL | 2 | 0 | 0 | 4.81 |
| paraphrase_05 | paraphrased_instructions | similarity_detected | not_detected | FAIL | 2 | 0 | 0 | 4.39 |
| paraphrase_06 | paraphrased_instructions | similarity_detected | not_detected | FAIL | 2 | 0 | 0 | 9.58 |
| paraphrase_07 | paraphrased_instructions | similarity_detected | not_detected | FAIL | 2 | 0 | 0 | 3.55 |
| paraphrase_08 | paraphrased_instructions | similarity_detected | not_detected | FAIL | 2 | 0 | 0 | 4.30 |
| paraphrase_09 | paraphrased_instructions | similarity_detected | not_detected | FAIL | 2 | 0 | 0 | 11.04 |
| paraphrase_10 | paraphrased_instructions | similarity_detected | not_detected | FAIL | 2 | 0 | 0 | 15.35 |
| different_meaning_03 | different_meanings | preserve_both | preserved | PASS | 2 | 0 | 0 | 3.44 |
| different_meaning_04 | different_meanings | preserve_both | preserved | PASS | 2 | 0 | 0 | 6.56 |
| different_meaning_05 | different_meanings | preserve_both | preserved | PASS | 2 | 1 | 0 | 6.06 |
| negation_03 | negation | preserve_both | preserved | PASS | 2 | 0 | 0 | 4.16 |
| negation_04 | negation | preserve_both | preserved | PASS | 2 | 0 | 0 | 6.62 |
| numeric_03 | numeric_constraints | preserve_both | preserved | PASS | 2 | 0 | 0 | 4.19 |
| numeric_04 | numeric_constraints | preserve_both | preserved | PASS | 2 | 0 | 0 | 3.40 |
| technical_03 | technical_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 3.78 |
| technical_04 | technical_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 60.78 |
| technical_05 | technical_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 6.71 |
| conditional_03 | conditional_instructions | preserve_both | preserved | PASS | 3 | 0 | 0 | 9.87 |
| conditional_04 | conditional_instructions | preserve_both | preserved | PASS | 3 | 0 | 0 | 12.91 |
| sequence_03 | instruction_sequence | preserve_both | preserved | PASS | 3 | 0 | 0 | 8.21 |
| sequence_04 | instruction_sequence | preserve_both | preserved | PASS | 2 | 0 | 0 | 8.22 |
| scope_03 | scope_and_completeness | preserve_both | preserved | PASS | 2 | 0 | 0 | 22.97 |
| scope_04 | scope_and_completeness | preserve_both | preserved | PASS | 2 | 0 | 0 | 5.14 |

## Detected relationships

### exact_duplicate_01
- 0-1: equal (score=1.000)
- Expected: `duplicate_detected`; actual: `duplicate_detected`.

### exact_duplicate_02
- 0-1: equal (score=1.000)
- Expected: `duplicate_detected`; actual: `duplicate_detected`.

### paraphrase_01
- No pairs detected.
- Expected: `similarity_detected`; actual: `not_detected`.

### paraphrase_02
- No pairs detected.
- Expected: `similarity_detected`; actual: `not_detected`.

### different_meaning_01
- 0-1: similar (score=0.750)
- Expected: `preserve_both`; actual: `preserved`.

### different_meaning_02
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### negation_01
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### negation_02
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### numeric_01
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### numeric_02
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### technical_01
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### technical_02
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### conditional_01
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### conditional_02
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### sequence_01
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### sequence_02
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### repeated_context_01
- 0-2: i_in_j (score=0.866)
- Expected: `duplicate_detected`; actual: `duplicate_detected`.

### repeated_context_02
- 0-2: i_in_j (score=0.816)
- Expected: `duplicate_detected`; actual: `duplicate_detected`.

### scope_01
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### scope_02
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### exact_duplicate_03
- 0-1: equal (score=1.000)
- Expected: `duplicate_detected`; actual: `duplicate_detected`.

### exact_duplicate_04
- 0-2: equal (score=1.000)
- Expected: `duplicate_detected`; actual: `duplicate_detected`.

### exact_duplicate_05
- 0-1: equal (score=1.000)
- Expected: `duplicate_detected`; actual: `duplicate_detected`.

### exact_duplicate_06
- 0-1: equal (score=1.000)
- Expected: `duplicate_detected`; actual: `duplicate_detected`.

### exact_duplicate_07
- 0-1: equal (score=1.000)
- Expected: `duplicate_detected`; actual: `duplicate_detected`.

### exact_duplicate_08
- 0-2: equal (score=1.000)
- Expected: `duplicate_detected`; actual: `duplicate_detected`.

### paraphrase_03
- No pairs detected.
- Expected: `similarity_detected`; actual: `not_detected`.

### paraphrase_04
- No pairs detected.
- Expected: `similarity_detected`; actual: `not_detected`.

### paraphrase_05
- No pairs detected.
- Expected: `similarity_detected`; actual: `not_detected`.

### paraphrase_06
- No pairs detected.
- Expected: `similarity_detected`; actual: `not_detected`.

### paraphrase_07
- No pairs detected.
- Expected: `similarity_detected`; actual: `not_detected`.

### paraphrase_08
- No pairs detected.
- Expected: `similarity_detected`; actual: `not_detected`.

### paraphrase_09
- No pairs detected.
- Expected: `similarity_detected`; actual: `not_detected`.

### paraphrase_10
- No pairs detected.
- Expected: `similarity_detected`; actual: `not_detected`.

### different_meaning_03
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### different_meaning_04
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### different_meaning_05
- 0-1: similar (score=0.667)
- Expected: `preserve_both`; actual: `preserved`.

### negation_03
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### negation_04
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### numeric_03
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### numeric_04
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### technical_03
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### technical_04
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### technical_05
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### conditional_03
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### conditional_04
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### sequence_03
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### sequence_04
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### scope_03
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

### scope_04
- No pairs detected.
- Expected: `preserve_both`; actual: `preserved`.

## Category summary

| Category | Passed | Total | Pass rate |
|---|---:|---:|---:|
| conditional_instructions | 4 | 4 | 100.0% |
| different_meanings | 5 | 5 | 100.0% |
| exact_duplicates | 5 | 5 | 100.0% |
| instruction_sequence | 4 | 4 | 100.0% |
| negation | 4 | 4 | 100.0% |
| numeric_constraints | 4 | 4 | 100.0% |
| paraphrased_instructions | 0 | 10 | 0.0% |
| repeated_with_context | 5 | 5 | 100.0% |
| scope_and_completeness | 4 | 4 | 100.0% |
| technical_instructions | 5 | 5 | 100.0% |

## Interpretation

- `duplicate_detected`: at least one strict removal was selected.
- `similarity_detected`: at least one pair was classified as similar.
- `preserve_both`: no clause was selected for removal.
- Similarity relationships alone must never cause removal.

This is a small, manually authored evaluation dataset. Its pass rate is not a general measure of NLP accuracy.

The benchmark constructs basic instruction/constraint segments itself. It does not measure the complete production segmentation pipeline or token savings.

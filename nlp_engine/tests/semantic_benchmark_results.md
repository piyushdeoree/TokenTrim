# TokenTrim Semantic Benchmark

- Dataset: `evaluation_dataset.json`
- Total cases: 50
- Passed: 50
- Failed: 0
- Pass rate: 100.0%
- Pretrained semantic model enabled: `False`

## Case results

| ID | Category | Expected | Actual | Result | Clauses | Pairs | Removals | Time (ms) |
|---|---|---|---|:---:|---:|---:|---:|---:|
| exact_duplicate_01 | exact_duplicates | duplicate_detected | duplicate_detected | PASS | 2 | 1 | 1 | 58.48 |
| exact_duplicate_02 | exact_duplicates | duplicate_detected | duplicate_detected | PASS | 3 | 1 | 1 | 6.93 |
| paraphrase_01 | paraphrased_instructions | similarity_detected | similarity_detected | PASS | 2 | 1 | 0 | 5.09 |
| paraphrase_02 | paraphrased_instructions | similarity_detected | similarity_detected | PASS | 2 | 1 | 0 | 20.67 |
| different_meaning_01 | different_meanings | preserve_both | preserved | PASS | 2 | 1 | 0 | 15.66 |
| different_meaning_02 | different_meanings | preserve_both | preserved | PASS | 2 | 0 | 0 | 6.97 |
| negation_01 | negation | preserve_both | preserved | PASS | 2 | 0 | 0 | 5.79 |
| negation_02 | negation | preserve_both | preserved | PASS | 2 | 0 | 0 | 5.43 |
| numeric_01 | numeric_constraints | preserve_both | preserved | PASS | 2 | 0 | 0 | 6.31 |
| numeric_02 | numeric_constraints | preserve_both | preserved | PASS | 2 | 0 | 0 | 6.07 |
| technical_01 | technical_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 17.57 |
| technical_02 | technical_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 11.16 |
| conditional_01 | conditional_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 5.98 |
| conditional_02 | conditional_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 5.97 |
| sequence_01 | instruction_sequence | preserve_both | preserved | PASS | 3 | 0 | 0 | 5.20 |
| sequence_02 | instruction_sequence | preserve_both | preserved | PASS | 2 | 0 | 0 | 4.89 |
| repeated_context_01 | repeated_with_context | duplicate_detected | duplicate_detected | PASS | 3 | 1 | 1 | 8.10 |
| repeated_context_02 | repeated_with_context | duplicate_detected | duplicate_detected | PASS | 3 | 1 | 1 | 5.23 |
| scope_01 | scope_and_completeness | preserve_both | preserved | PASS | 2 | 0 | 0 | 5.15 |
| scope_02 | scope_and_completeness | preserve_both | preserved | PASS | 2 | 0 | 0 | 10.06 |
| exact_duplicate_03 | exact_duplicates | duplicate_detected | duplicate_detected | PASS | 2 | 1 | 1 | 7.00 |
| exact_duplicate_04 | repeated_with_context | duplicate_detected | duplicate_detected | PASS | 3 | 1 | 1 | 11.43 |
| exact_duplicate_05 | exact_duplicates | duplicate_detected | duplicate_detected | PASS | 2 | 1 | 1 | 5.24 |
| exact_duplicate_06 | repeated_with_context | duplicate_detected | duplicate_detected | PASS | 3 | 1 | 1 | 8.24 |
| exact_duplicate_07 | exact_duplicates | duplicate_detected | duplicate_detected | PASS | 2 | 1 | 1 | 6.33 |
| exact_duplicate_08 | repeated_with_context | duplicate_detected | duplicate_detected | PASS | 3 | 1 | 1 | 8.61 |
| paraphrase_03 | paraphrased_instructions | similarity_detected | similarity_detected | PASS | 2 | 1 | 0 | 6.35 |
| paraphrase_04 | paraphrased_instructions | similarity_detected | similarity_detected | PASS | 2 | 1 | 0 | 8.79 |
| paraphrase_05 | paraphrased_instructions | similarity_detected | similarity_detected | PASS | 2 | 1 | 0 | 6.90 |
| paraphrase_06 | paraphrased_instructions | similarity_detected | similarity_detected | PASS | 2 | 1 | 0 | 9.33 |
| paraphrase_07 | paraphrased_instructions | similarity_detected | similarity_detected | PASS | 2 | 1 | 0 | 9.61 |
| paraphrase_08 | paraphrased_instructions | similarity_detected | similarity_detected | PASS | 2 | 1 | 0 | 4.17 |
| paraphrase_09 | paraphrased_instructions | similarity_detected | similarity_detected | PASS | 2 | 1 | 0 | 7.71 |
| paraphrase_10 | paraphrased_instructions | similarity_detected | similarity_detected | PASS | 2 | 1 | 0 | 4.21 |
| different_meaning_03 | different_meanings | preserve_both | preserved | PASS | 2 | 0 | 0 | 3.92 |
| different_meaning_04 | different_meanings | preserve_both | preserved | PASS | 2 | 0 | 0 | 4.47 |
| different_meaning_05 | different_meanings | preserve_both | preserved | PASS | 2 | 1 | 0 | 5.51 |
| negation_03 | negation | preserve_both | preserved | PASS | 2 | 0 | 0 | 5.42 |
| negation_04 | negation | preserve_both | preserved | PASS | 2 | 0 | 0 | 6.83 |
| numeric_03 | numeric_constraints | preserve_both | preserved | PASS | 2 | 0 | 0 | 3.69 |
| numeric_04 | numeric_constraints | preserve_both | preserved | PASS | 2 | 0 | 0 | 12.06 |
| technical_03 | technical_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 6.64 |
| technical_04 | technical_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 4.60 |
| technical_05 | technical_instructions | preserve_both | preserved | PASS | 2 | 0 | 0 | 4.53 |
| conditional_03 | conditional_instructions | preserve_both | preserved | PASS | 3 | 0 | 0 | 3.69 |
| conditional_04 | conditional_instructions | preserve_both | preserved | PASS | 3 | 0 | 0 | 3.13 |
| sequence_03 | instruction_sequence | preserve_both | preserved | PASS | 3 | 0 | 0 | 4.11 |
| sequence_04 | instruction_sequence | preserve_both | preserved | PASS | 2 | 0 | 0 | 7.60 |
| scope_03 | scope_and_completeness | preserve_both | preserved | PASS | 2 | 0 | 0 | 5.25 |
| scope_04 | scope_and_completeness | preserve_both | preserved | PASS | 2 | 0 | 0 | 4.22 |

## Detected relationships

### exact_duplicate_01
- 0-1: equal (score=1.000)
- Expected: `duplicate_detected`; actual: `duplicate_detected`.

### exact_duplicate_02
- 0-1: equal (score=1.000)
- Expected: `duplicate_detected`; actual: `duplicate_detected`.

### paraphrase_01
- 0-1: similar (score=1.000)
- Expected: `similarity_detected`; actual: `similarity_detected`.

### paraphrase_02
- 0-1: similar (score=0.750)
- Expected: `similarity_detected`; actual: `similarity_detected`.

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
- 0-1: similar (score=1.000)
- Expected: `similarity_detected`; actual: `similarity_detected`.

### paraphrase_04
- 0-1: similar (score=1.000)
- Expected: `similarity_detected`; actual: `similarity_detected`.

### paraphrase_05
- 0-1: similar (score=0.667)
- Expected: `similarity_detected`; actual: `similarity_detected`.

### paraphrase_06
- 0-1: similar (score=0.866)
- Expected: `similarity_detected`; actual: `similarity_detected`.

### paraphrase_07
- 0-1: similar (score=0.667)
- Expected: `similarity_detected`; actual: `similarity_detected`.

### paraphrase_08
- 0-1: similar (score=1.000)
- Expected: `similarity_detected`; actual: `similarity_detected`.

### paraphrase_09
- 0-1: similar (score=1.000)
- Expected: `similarity_detected`; actual: `similarity_detected`.

### paraphrase_10
- 0-1: similar (score=1.000)
- Expected: `similarity_detected`; actual: `similarity_detected`.

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
| paraphrased_instructions | 10 | 10 | 100.0% |
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

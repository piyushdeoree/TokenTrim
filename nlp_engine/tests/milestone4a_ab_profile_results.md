# Milestone 4A Validation Profiling

Profiles are separate from warm latency measurements. cProfile instrumentation increases execution time; use these results to locate work, not to claim user-facing latency changes.

A validator SHA-256: `84ce89642aa68581796d421f92013df5b62b555efbf4f5890db51f049272ed2e`  
B validator SHA-256: `ac3d961c3a3a99cc2956eb42ac0846377661547b621caf41abd2af1f37897198`

## large_64k

### Version A

- Total calls: 1,047,453; primitive calls: 1,047,451.
- Total profiled validation time: 1.084s.

| Function | Calls | Self seconds | Cumulative seconds | Source |
|---|---:|---:|---:|---|
| `validate_optimization` | 1 | 0.0017 | 1.0857 | `validator.py:416` |
| `prepare_prompt` | 4 | 0.0001 | 0.6492 | `textutils.py:341` |
| `_segment` | 4 | 0.0183 | 0.5912 | `textutils.py:301` |
| `classify_sentence` | 1706 | 0.0068 | 0.5240 | `textutils.py:279` |
| `_entities` | 2 | 0.0286 | 0.4127 | `validator.py:41` |
| `has_non_latin_letters` | 1706 | 0.1447 | 0.3269 | `textutils.py:262` |
| `canonical_text` | 2571 | 0.0090 | 0.3057 | `textutils.py:117` |
| `content_stems` | 865 | 0.0422 | 0.2534 | `textutils.py:125` |
| `head_word` | 1706 | 0.0049 | 0.1552 | `textutils.py:249` |
| `_best_constraint_coverage` | 3 | 0.0064 | 0.1215 | `validator.py:366` |
| `_lexical_similarity` | 1 | 0.0001 | 0.0872 | `validator.py:75` |
| `protect_spans` | 4 | 0.0004 | 0.0579 | `textutils.py:62` |
| `_format_keywords` | 2 | 0.0001 | 0.0387 | `validator.py:64` |
| `_balanced_spans` | 8 | 0.0372 | 0.0372 | `textutils.py:48` |
| `words` | 2571 | 0.0022 | 0.0299 | `textutils.py:108` |

### Version B

- Total calls: 828,277; primitive calls: 828,275.
- Total profiled validation time: 0.881s.

| Function | Calls | Self seconds | Cumulative seconds | Source |
|---|---:|---:|---:|---|
| `validate_optimization` | 1 | 0.0014 | 0.8814 | `validator.py:461` |
| `prepare_prompt` | 3 | 0.0001 | 0.4857 | `textutils.py:341` |
| `_segment` | 3 | 0.0116 | 0.4413 | `textutils.py:301` |
| `classify_sentence` | 1280 | 0.0045 | 0.3984 | `textutils.py:279` |
| `canonical_text` | 1717 | 0.0055 | 0.2575 | `textutils.py:117` |
| `has_non_latin_letters` | 1280 | 0.1123 | 0.2531 | `textutils.py:262` |
| `content_stems` | 437 | 0.0285 | 0.2149 | `textutils.py:125` |
| `_entities` | 1 | 0.0000 | 0.2046 | `validator.py:41` |
| `head_word` | 1280 | 0.0032 | 0.1147 | `textutils.py:249` |
| `_entities_from_segments` | 2 | 0.0320 | 0.0906 | `validator.py:46` |
| `_lexical_similarity` | 1 | 0.0001 | 0.0867 | `validator.py:80` |
| `_constraint_coverage_scores` | 1 | 0.0041 | 0.0644 | `validator.py:421` |
| `protect_spans` | 3 | 0.0002 | 0.0444 | `textutils.py:62` |
| `_format_keywords` | 2 | 0.0001 | 0.0435 | `validator.py:69` |
| `_balanced_spans` | 6 | 0.0264 | 0.0264 | `textutils.py:48` |

## very_large_512k

### Version A

- Total calls: 8,239,438; primitive calls: 8,239,436.
- Total profiled validation time: 8.604s.

| Function | Calls | Self seconds | Cumulative seconds | Source |
|---|---:|---:|---:|---|
| `validate_optimization` | 1 | 0.0096 | 8.6142 | `validator.py:416` |
| `prepare_prompt` | 4 | 0.0003 | 5.1281 | `textutils.py:341` |
| `_segment` | 4 | 0.1291 | 4.6439 | `textutils.py:301` |
| `classify_sentence` | 13062 | 0.0500 | 4.1597 | `textutils.py:279` |
| `_entities` | 2 | 0.2364 | 3.2301 | `validator.py:41` |
| `has_non_latin_letters` | 13062 | 1.1573 | 2.6008 | `textutils.py:262` |
| `canonical_text` | 19605 | 0.0646 | 2.5279 | `textutils.py:117` |
| `content_stems` | 6543 | 0.2988 | 2.0550 | `textutils.py:125` |
| `head_word` | 13062 | 0.0347 | 1.2242 | `textutils.py:249` |
| `_best_constraint_coverage` | 3 | 0.0488 | 0.9802 | `validator.py:366` |
| `_lexical_similarity` | 1 | 0.0003 | 0.6746 | `validator.py:75` |
| `protect_spans` | 4 | 0.0006 | 0.4839 | `textutils.py:62` |
| `_format_keywords` | 2 | 0.0002 | 0.3177 | `validator.py:64` |
| `_balanced_spans` | 8 | 0.2941 | 0.2941 | `textutils.py:48` |
| `words` | 19605 | 0.0163 | 0.2328 | `textutils.py:108` |

### Version B

- Total calls: 6,505,456; primitive calls: 6,505,454.
- Total profiled validation time: 7.443s.

| Function | Calls | Self seconds | Cumulative seconds | Source |
|---|---:|---:|---:|---|
| `validate_optimization` | 1 | 0.0109 | 7.4511 | `validator.py:461` |
| `prepare_prompt` | 3 | 0.0002 | 3.9632 | `textutils.py:341` |
| `_segment` | 3 | 0.0999 | 3.6098 | `textutils.py:301` |
| `classify_sentence` | 9797 | 0.0388 | 3.2424 | `textutils.py:279` |
| `canonical_text` | 13073 | 0.0458 | 2.3219 | `textutils.py:117` |
| `content_stems` | 3276 | 0.3087 | 2.1299 | `textutils.py:125` |
| `has_non_latin_letters` | 9797 | 0.9172 | 2.0502 | `textutils.py:262` |
| `_entities` | 1 | 0.0002 | 1.6910 | `validator.py:41` |
| `head_word` | 9797 | 0.0264 | 0.9323 | `textutils.py:249` |
| `_lexical_similarity` | 1 | 0.0002 | 0.9185 | `validator.py:80` |
| `_entities_from_segments` | 2 | 0.2480 | 0.7119 | `validator.py:46` |
| `_constraint_coverage_scores` | 1 | 0.0329 | 0.4980 | `validator.py:421` |
| `protect_spans` | 3 | 0.0004 | 0.3532 | `textutils.py:62` |
| `_format_keywords` | 2 | 0.0003 | 0.3334 | `validator.py:69` |
| `_balanced_spans` | 6 | 0.2168 | 0.2168 | `textutils.py:48` |

## Interpretation

Compare call counts and cumulative time only within matching prompt size and the same environment. The earlier implementation should segment the optimized prompt again in entity extraction and recompute candidate features per original constraint; the optimized implementation should avoid those repeated operations. A reduction in those calls is not by itself evidence of lower wall latency.

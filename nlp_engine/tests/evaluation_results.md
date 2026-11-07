# Evaluation results

Model: `gpt-4o`  
Token counting: `tiktoken:o200k_base` (EXACT)  
Exact count from OpenAI's tiktoken encoding.

| # | Scenario | Original | Optimized | Saved | Reduction | Accepted | Preserved | Issues |
|---|----------|---------:|----------:|------:|----------:|:--------:|:---------:|--------|
| 1 | simple question | 7 | 7 | 0 | 0.0% | no change | yes | - |
| 2 | long verbose prompt | 30 | 15 | 15 | 50.0% | yes | yes | verbosity |
| 3 | repeated instructions | 10 | 4 | 6 | 60.0% | yes | yes | redundancy, verbosity |
| 4 | duplicate constraints | 34 | 17 | 17 | 50.0% | yes | yes | duplicate_constraint, repeated_phrase |
| 5 | large context (must not be cut) | 1514 | 1514 | 0 | 0.0% | no change | yes | excessive_context |
| 6 | code-generation prompt | 43 | 35 | 8 | 18.6% | yes | yes | verbosity |
| 7 | summarization prompt (spec example) | 44 | 23 | 21 | 47.7% | yes | yes | conflict, redundancy, verbosity |
| 8 | structured JSON-output prompt | 56 | 53 | 3 | 5.4% | yes | yes | verbosity |
| 9 | prompt with important numbers | 39 | 39 | 0 | 0.0% | no change | yes | verbosity |
| 10 | already tight prompt (little/no change) | 12 | 12 | 0 | 0.0% | no change | yes | - |

Total: 1789 -> 1719 tokens (3.9% over these 10 prompts; this is a descriptive number for this tiny hand-written set, not an accuracy or generalisation claim).

'Preserved' = every required string (numbers, names, code, constraints, JSON schema, context) is still present verbatim.

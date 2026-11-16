# TokenTrim Realistic NLP Evaluation

## Reproducibility

Run from the repository root with:

```bash
python -m nlp_engine.tests.run_realistic_evaluation
```

- Dataset: `realistic_evaluation_dataset.json` (39 cases)
- Cohort counts: **20** original baseline; **19** new in Milestone 3
- Token counter: `heuristic_estimate`; exact: `False`
- Optional semantic model: disabled for this evaluation
- LLM behavior: deterministic callback candidates from the dataset; no provider calls
- Scope note: curated evaluation, not a general accuracy or semantic-equivalence claim

## Results summary

- Expected outcomes: **12** safe optimizations, **17** unchanged, **10** unsafe candidates to reject
- Safe optimizations accepted: **12/12** expected opportunities
- Prompts correctly left unchanged: **17/17** expected unchanged cases
- Unsafe LLM candidates rejected with fallback: **10/10**
- False removals: **0**
- Unexpected accepted optimizations on unchanged/rejection cases: **0**
- Missed optimization opportunities: **0**
- Exact-original fallbacks: **27**
- Unexpected exceptions: **0**
- Aggregate estimated tokens: **5811** original → **5631** final
- Total estimated tokens saved: **180**
- Aggregate estimated reduction: **3.1%**
- Cases matching expected behavior: **39/39**

False removals count accepted optimizations that omit one or more case-specific required phrases. Unexpected optimizations are reported separately because a changed output can retain all listed phrases and still violate a case designated unchanged. Missed opportunities count expected-safe cases that did not produce a valid, positive-saving optimization.

### Cases by category

| Category | Cases |
|---|---:|
| api_requirements | 7 |
| data_processing | 7 |
| general_task | 9 |
| software_development | 8 |
| technical_specification | 8 |

### Coverage by expected outcome

| Expected outcome | Cases |
|---|---:|
| accept_safe_optimization | 12 |
| leave_unchanged | 17 |
| reject_unsafe_candidate | 10 |

### Scenario coverage

| Scenario | Cases |
|---|---:|
| authn_authz | 1 |
| complex_multisection | 2 |
| concise_noop | 2 |
| conditions_exceptions | 5 |
| frontend_backend | 2 |
| genuine_redundancy | 2 |
| idempotency | 1 |
| mixed_language | 2 |
| multiple_output_contracts | 4 |
| negation | 1 |
| nested_data_conditions | 4 |
| no_token_savings | 1 |
| non_english | 2 |
| null_handling | 1 |
| ordering | 4 |
| quoted_literals | 3 |
| retry_policies | 2 |
| section_labels | 2 |
| section_scoped | 5 |
| security_literals | 2 |
| similar_but_distinct | 2 |
| technical_identifiers | 3 |
| unsafe_llm_exception_removal | 1 |
| unsafe_llm_format_change | 1 |
| unsafe_llm_identifier_change | 1 |
| unsafe_llm_negation_removal | 1 |
| unsafe_llm_numeric_change | 1 |
| unsafe_llm_section_removal | 1 |
| urls_paths_env | 1 |

## Case results

### software_01 — software_development

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Remove a truly repeated implementation requirement while retaining the delivery and testing requirements.

- Expected: `accept_safe_optimization`
- Actual: `optimized`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `True`
- Detected issue types: `['duplicate_constraint', 'repeated_phrase']`
- Candidate changes: `["Removed repeated content: 'Do not change the current public API or existing database schema.' (already covered by 'Do not change the current public API or existing database schema.')"]`
- Fallback used: `False`
- Fallback reason: `not applicable`
- Tokens: 153 → 134 
- Estimated tokens saved: **19**
- Reduction percentage: **12.42%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Project: Inventory import service

Goal: Add CSV import to the existing Python service.

Implementation requirements:
- Do not change the current public API or existing database schema.
- Validate each row before writing it.
- Return row-level errors without aborting valid rows.

Compatibility requirements:
- Do not change the current public API or existing database schema.
- Inspect the existing import and persistence code before editing.
- Add focused tests for mixed valid and invalid rows.
- Report changed files and test results.
````

Final prompt:

````text
Project: Inventory import service

Goal: Add CSV import to the existing Python service.

Implementation requirements:
- Do not change the current public API or existing database schema.
- Validate each row before writing it.
- Return row-level errors without aborting valid rows.

Compatibility requirements:
- Inspect the existing import and persistence code before editing.
- Add focused tests for mixed valid and invalid rows.
- Report changed files and test results.
````

### software_02 — software_development

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Consolidate a repeated exact development workflow instruction without dropping unrelated constraints.

- Expected: `accept_safe_optimization`
- Actual: `optimized`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `True`
- Detected issue types: `['duplicate_constraint', 'repeated_phrase']`
- Candidate changes: `["Removed repeated content: 'Do not rename the endpoint or its response fields.' (already covered by 'Do not rename the endpoint or its response fields.')"]`
- Fallback used: `False`
- Fallback reason: `not applicable`
- Tokens: 139 → 124 
- Estimated tokens saved: **15**
- Reduction percentage: **10.79%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Task: Add pagination to the activity endpoint in the existing application.

Constraints:
- Do not rename the endpoint or its response fields.
- Keep the existing default ordering by creation time.
- Do not rename the endpoint or its response fields.

Working approach:
- Read the current route and tests first.
- Implement the smallest compatible change.
- Add tests for the default page and an out-of-range page.

Deliverable: Summarize the behavior change and list the tests that were run.
````

Final prompt:

````text
Task: Add pagination to the activity endpoint in the existing application.

Constraints:
- Do not rename the endpoint or its response fields.
- Keep the existing default ordering by creation time.
Working approach:
- Read the current route and tests first.
- Implement the smallest compatible change.
- Add tests for the default page and an out-of-range page.

Deliverable: Summarize the behavior change and list the tests that were run.
````

### software_03 — software_development

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Keep similar but distinct security requirements and exact project identifiers.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 207 → 207 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Project: Session renewal for the Acme Portal

Requirements:
- Verify the signed session token before reading its subject.
- Authorize the subject for the requested organization after authentication.
- Preserve the exact claim name `org_id`; do not replace it with `organization_id`.
- Store refresh tokens in `auth.refresh_tokens`.

Failure behavior:
- Return 401 for a missing or invalid token.
- Return 403 when an authenticated subject lacks organization access.

Exact code requirement: Preserve this guard unchanged:
```python
if user_id is None:
    raise MissingUserIdError()
```

Testing: Cover both failure cases separately and verify that expired tokens are rejected.
````

Final prompt:

````text
Project: Session renewal for the Acme Portal

Requirements:
- Verify the signed session token before reading its subject.
- Authorize the subject for the requested organization after authentication.
- Preserve the exact claim name `org_id`; do not replace it with `organization_id`.
- Store refresh tokens in `auth.refresh_tokens`.

Failure behavior:
- Return 401 for a missing or invalid token.
- Return 403 when an authenticated subject lacks organization access.

Exact code requirement: Preserve this guard unchanged:
```python
if user_id is None:
    raise MissingUserIdError()
```

Testing: Cover both failure cases separately and verify that expired tokens are rejected.
````

### software_04 — software_development

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Reject an LLM rewrite that loses a backward-compatibility requirement.

- Expected: `reject_unsafe_candidate`
- Actual: `unsafe_candidate_rejected`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `False`
- Optimization accepted: `False`
- Detected issue types: `['repeated_phrase']`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 116 → 116 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Task: Add a `status` field to the job response.

Compatibility requirements:
- Keep existing response fields and their meanings unchanged.
- Existing clients that omit the new field from requests must continue to work.
- Return the new field as a string using one of `queued`, `running`, `complete`, or `failed`.

Verification: Test an old client payload and all four status values.
````

Final prompt:

````text
Task: Add a `status` field to the job response.

Compatibility requirements:
- Keep existing response fields and their meanings unchanged.
- Existing clients that omit the new field from requests must continue to work.
- Return the new field as a string using one of `queued`, `running`, `complete`, or `failed`.

Verification: Test an old client payload and all four status values.
````

Injected LLM candidate:

````text
Task: Add a status field to the job response. Return queued, running, complete, or failed. Test all four status values.
````

Rejected LLM candidate reasons:

- Code/URL/quoted/JSON content changed or lost: `status`; `queued`; `running`
- Constraint(s) possibly lost: Keep existing response fields and their meanings u; Existing clients that omit the new field from requ
- Keyword coverage 39% is below 90%

### technical_01 — technical_specification

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Remove a repeated exact performance requirement while preserving thresholds and measurement method.

- Expected: `accept_safe_optimization`
- Actual: `optimized`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `True`
- Detected issue types: `['duplicate_constraint', 'repeated_phrase']`
- Candidate changes: `["Removed repeated content: 'Keep result ranking unchanged.' (already covered by 'Keep result ranking unchanged.')"]`
- Fallback used: `False`
- Fallback reason: `not applicable`
- Tokens: 161 → 151 
- Estimated tokens saved: **10**
- Reduction percentage: **6.21%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Component: Search index

Objective: Improve lookup latency without changing result ranking.

Performance requirements:
- Keep result ranking unchanged.
- Keep p95 lookup latency below 250 ms at 2,000 requests per second.
- Measure latency after a 10-minute warm-up using 30-minute runs.

Constraints:
- Keep result ranking unchanged.
- Keep the index format compatible with version 3 snapshots.
- Do not reduce the retained history window of 90 days.

Report: Include the test hardware, workload, p95 latency, and p99 latency.
````

Final prompt:

````text
Component: Search index

Objective: Improve lookup latency without changing result ranking.

Performance requirements:
- Keep result ranking unchanged.
- Keep p95 lookup latency below 250 ms at 2,000 requests per second.
- Measure latency after a 10-minute warm-up using 30-minute runs.

Constraints:
- Keep the index format compatible with version 3 snapshots.
- Do not reduce the retained history window of 90 days.

Report: Include the test hardware, workload, p95 latency, and p99 latency.
````

### technical_02 — technical_specification

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Consolidate repeated exact serialization guidance without changing literal requirements.

- Expected: `accept_safe_optimization`
- Actual: `optimized`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `True`
- Detected issue types: `['redundancy', 'repeated_phrase']`
- Candidate changes: `["Removed repeated content: 'Emit one UTF-8 JSON object per line.' (already covered by 'Emit one UTF-8 JSON object per line.')"]`
- Fallback used: `False`
- Fallback reason: `not applicable`
- Tokens: 141 → 129 
- Estimated tokens saved: **12**
- Reduction percentage: **8.51%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Output contract: Emit one UTF-8 JSON object per line.

Schema requirements:
- Include `record_id`, `observed_at`, and `value`.
- Keep timestamps in RFC 3339 UTC form.
- Emit one UTF-8 JSON object per line.

Validation:
- Reject records with a missing `record_id`.
- Preserve decimal precision to 4 places.
- Do not emit a header row.

Acceptance: Parse the output with the standard JSON parser and verify that each line is an independent object.
````

Final prompt:

````text
Output contract: Emit one UTF-8 JSON object per line.

Schema requirements:
- Include `record_id`, `observed_at`, and `value`.
- Keep timestamps in RFC 3339 UTC form.
Validation:
- Reject records with a missing `record_id`.
- Preserve decimal precision to 4 places.
- Do not emit a header row.

Acceptance: Parse the output with the standard JSON parser and verify that each line is an independent object.
````

### technical_03 — technical_specification

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Preserve distinct latency percentiles, thresholds, and memory limits despite similar wording.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `['repeated_phrase']`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 121 → 121 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Service limits:
- Keep p95 request latency below 250 ms.
- Keep p99 request latency below 500 ms.
- Keep peak memory below 1.5 GiB during a 60-minute soak test.

Measurement details:
- Exclude the first 5 minutes from latency calculations.
- Run the soak test with 800 concurrent clients.
- Report p50, p95, and p99 separately.

Do not infer that satisfying one percentile satisfies another.
````

Final prompt:

````text
Service limits:
- Keep p95 request latency below 250 ms.
- Keep p99 request latency below 500 ms.
- Keep peak memory below 1.5 GiB during a 60-minute soak test.

Measurement details:
- Exclude the first 5 minutes from latency calculations.
- Run the soak test with 800 concurrent clients.
- Report p50, p95, and p99 separately.

Do not infer that satisfying one percentile satisfies another.
````

### technical_04 — technical_specification

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Reject a candidate that changes an inclusive threshold and removes the exception path.

- Expected: `reject_unsafe_candidate`
- Actual: `unsafe_candidate_rejected`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `False`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 126 → 126 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Capacity rule:
- Accept batches containing at most 500 records.
- For batches above 500 records, split them into chunks of 500 before processing.
- If a record exceeds 2 MiB, reject that record and continue with the remaining records.

Ordering: Validate record size first, then split accepted batches, then write chunks in input order.

Output: Return a JSON object with `accepted`, `rejected`, and `errors` arrays.
````

Final prompt:

````text
Capacity rule:
- Accept batches containing at most 500 records.
- For batches above 500 records, split them into chunks of 500 before processing.
- If a record exceeds 2 MiB, reject that record and continue with the remaining records.

Ordering: Validate record size first, then split accepted batches, then write chunks in input order.

Output: Return a JSON object with `accepted`, `rejected`, and `errors` arrays.
````

Injected LLM candidate:

````text
Accept batches under 500 records. Reject any batch containing a record over 2 MiB. Process the accepted records and return JSON.
````

Rejected LLM candidate reasons:

- Code/URL/quoted/JSON content changed or lost: `accepted`; `rejected`; `errors`
- Named items lost: Return, Validate
- Constraint(s) possibly lost: Accept batches containing at most 500 records.
- Keyword coverage 41% is below 90%

### api_01 — api_requirements

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Remove a repeated exact authentication requirement without losing route behavior.

- Expected: `accept_safe_optimization`
- Actual: `optimized`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `True`
- Detected issue types: `['duplicate_constraint', 'repeated_phrase']`
- Candidate changes: `["Removed repeated content: 'Do not change the path, method, or response field names.' (already covered by 'Do not change the path, method, or response field names.')"]`
- Fallback used: `False`
- Fallback reason: `not applicable`
- Tokens: 164 → 145 
- Estimated tokens saved: **19**
- Reduction percentage: **11.59%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Endpoint: `POST /v2/reports`

Authentication and input:
- Require a bearer token with the `reports:write` scope.
- Accept `title` and `source_ids` in the JSON body.
- Return 400 when `source_ids` is empty.

Compatibility:
- Do not change the path, method, or response field names.
- Return 401 for a missing or invalid token and 403 for insufficient scope.

Behavior:
- Create the report asynchronously and return 202 with `report_id`.
- Do not change the path, method, or response field names.
````

Final prompt:

````text
Endpoint: `POST /v2/reports`

Authentication and input:
- Require a bearer token with the `reports:write` scope.
- Accept `title` and `source_ids` in the JSON body.
- Return 400 when `source_ids` is empty.

Compatibility:
- Do not change the path, method, or response field names.
- Return 401 for a missing or invalid token and 403 for insufficient scope.

Behavior:
- Create the report asynchronously and return 202 with `report_id`.
````

### api_02 — api_requirements

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Consolidate a repeated exact retry rule while preserving retry limits and idempotency behavior.

- Expected: `accept_safe_optimization`
- Actual: `optimized`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `True`
- Detected issue types: `['duplicate_constraint', 'repeated_phrase']`
- Candidate changes: `["Removed repeated content: 'Retry a 503 response up to 2 times with exponential backoff.' (already covered by 'Retry a 503 response up to 2 times with exponential backoff.')"]`
- Fallback used: `False`
- Fallback reason: `not applicable`
- Tokens: 145 → 126 
- Estimated tokens saved: **19**
- Reduction percentage: **13.1%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Client behavior for `PUT /v1/accounts/{account_id}`:

Retry policy:
- Retry a 503 response up to 2 times with exponential backoff.
- Retry a 503 response up to 2 times with exponential backoff.
- Do not retry 400, 401, or 403 responses.

Request safety:
- Send the same `Idempotency-Key` on every retry.
- Stop retrying after 4 seconds total.

Logging: Record the request ID, attempt number, and final HTTP status; never log the bearer token.
````

Final prompt:

````text
Client behavior for `PUT /v1/accounts/{account_id}`:

Retry policy:
- Retry a 503 response up to 2 times with exponential backoff.
- Do not retry 400, 401, or 403 responses.

Request safety:
- Send the same `Idempotency-Key` on every retry.
- Stop retrying after 4 seconds total.

Logging: Record the request ID, attempt number, and final HTTP status; never log the bearer token.
````

### api_03 — api_requirements

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Keep authentication, authorization, status codes, URL, and response formats distinct.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 174 → 174 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Endpoint: `GET https://api.example.test/v3/projects/{project_id}`

Access rules:
- Authenticate the caller using a valid OAuth access token.
- Authorize access to the requested project using its tenant membership.
- Return 401 when authentication fails.
- Return 403 when authentication succeeds but tenant authorization fails.

Response rules:
- Return `application/json` on success.
- Return `application/problem+json` for errors.
- Include the exact `project_id` and `tenant_id` fields in successful responses.
````

Final prompt:

````text
Endpoint: `GET https://api.example.test/v3/projects/{project_id}`

Access rules:
- Authenticate the caller using a valid OAuth access token.
- Authorize access to the requested project using its tenant membership.
- Return 401 when authentication fails.
- Return 403 when authentication succeeds but tenant authorization fails.

Response rules:
- Return `application/json` on success.
- Return `application/problem+json` for errors.
- Include the exact `project_id` and `tenant_id` fields in successful responses.
````

### api_04 — api_requirements

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Reject a rewrite that drops the conditional retry exception and changes the response format.

- Expected: `reject_unsafe_candidate`
- Actual: `unsafe_candidate_rejected`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `False`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 141 → 141 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Webhook delivery:
- Send events to `https://hooks.example.test/events`.
- Sign each request with HMAC-SHA256 using the configured secret.
- Retry up to 5 times only when the receiver returns 429 or 503.
- Do not retry 400 responses.

Ordering: Preserve event order for a given `account_id`, but events for different accounts may be delivered concurrently.

Response: The receiver must return JSON containing `received_at` and `event_id`.
````

Final prompt:

````text
Webhook delivery:
- Send events to `https://hooks.example.test/events`.
- Sign each request with HMAC-SHA256 using the configured secret.
- Retry up to 5 times only when the receiver returns 429 or 503.
- Do not retry 400 responses.

Ordering: Preserve event order for a given `account_id`, but events for different accounts may be delivered concurrently.

Response: The receiver must return JSON containing `received_at` and `event_id`.
````

Injected LLM candidate:

````text
Send signed events to the webhook. Retry failed requests up to 5 times and process accounts concurrently. Return the event ID.
````

Rejected LLM candidate reasons:

- Numbers lost: 400, 429, 503
- Code/URL/quoted/JSON content changed or lost: `https://hooks.example.test/events`; `account_id`; `received_at`
- Output-format requirement lost: json
- Named items lost: HMAC, JSON, Preserve, SHA256, The
- Constraint(s) possibly lost: Retry up to 5 times only when the receiver returns; Do not retry 400 responses.; Response: The receiver must return JSON containing
- Keyword coverage 35% is below 90%

### data_01 — data_processing

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Remove a repeated exact data exclusion rule while preserving processing order.

- Expected: `accept_safe_optimization`
- Actual: `optimized`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `True`
- Detected issue types: `['duplicate_constraint', 'repeated_phrase']`
- Candidate changes: `["Removed repeated content: 'Do not include test accounts when computing customer metrics.' (already covered by 'Do not include test accounts when computing customer metrics.')"]`
- Fallback used: `False`
- Fallback reason: `not applicable`
- Tokens: 167 → 150 
- Estimated tokens saved: **17**
- Reduction percentage: **10.18%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Dataset: Monthly subscription events

Preparation:
- Parse `event_time` as UTC and retain the source value in `event_time_raw`.
- Do not include test accounts when computing customer metrics.
- Keep refunds as a separate negative amount; do not discard them.

Processing order:
- Deduplicate by `event_id`, keeping the earliest received copy.
- Aggregate monthly recurring revenue by calendar month.
- Do not include test accounts when computing customer metrics.

Quality checks: Report input rows, duplicate rows, excluded test accounts, and output rows.
````

Final prompt:

````text
Dataset: Monthly subscription events

Preparation:
- Parse `event_time` as UTC and retain the source value in `event_time_raw`.
- Do not include test accounts when computing customer metrics.
- Keep refunds as a separate negative amount; do not discard them.

Processing order:
- Deduplicate by `event_id`, keeping the earliest received copy.
- Aggregate monthly recurring revenue by calendar month.
Quality checks: Report input rows, duplicate rows, excluded test accounts, and output rows.
````

### data_02 — data_processing

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Consolidate a repeated exact cleaning instruction without losing the missing-value exception.

- Expected: `accept_safe_optimization`
- Actual: `optimized`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `True`
- Detected issue types: `['redundancy', 'repeated_phrase']`
- Candidate changes: `["Removed repeated content: 'Remove rows with an invalid sensor ID.' (already covered by 'Remove rows with an invalid sensor ID.')"]`
- Fallback used: `False`
- Fallback reason: `not applicable`
- Tokens: 163 → 151 
- Estimated tokens saved: **12**
- Reduction percentage: **7.36%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Task: Prepare the sensor dataset for daily summaries.

Cleaning:
- Convert temperatures from Fahrenheit to Celsius using `(F - 32) * 5 / 9`.
- Remove rows with an invalid sensor ID.
- Remove rows with an invalid sensor ID.
- Keep rows with a missing temperature and mark `temperature_status` as `missing`.

Aggregation:
- Compute the median per sensor and UTC day.
- Require at least 12 valid readings for a daily median.
- Keep the original reading count in the output.

Output: Write Parquet partitioned by `reading_date`.
````

Final prompt:

````text
Task: Prepare the sensor dataset for daily summaries.

Cleaning:
- Convert temperatures from Fahrenheit to Celsius using `(F - 32) * 5 / 9`.
- Remove rows with an invalid sensor ID.
- Keep rows with a missing temperature and mark `temperature_status` as `missing`.

Aggregation:
- Compute the median per sensor and UTC day.
- Require at least 12 valid readings for a daily median.
- Keep the original reading count in the output.

Output: Write Parquet partitioned by `reading_date`.
````

### data_03 — data_processing

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Preserve distinct null-handling, filtering, threshold, and ordering requirements.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 181 → 181 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Input columns: `net_amount`, `tax_amount`, `currency`, `created_at`, and `is_refunded`.

Rules:
- Exclude refunded rows from net sales totals, but retain them in the audit output.
- Convert currencies using the rate for each row's `created_at` date.
- Treat a null `tax_amount` as unknown; do not replace it with zero.
- Flag, but do not remove, rows where `net_amount` is below -100.

Order: Validate column types, apply refund handling, convert currency, then aggregate by ISO week. Return both weekly totals and an exception table.
````

Final prompt:

````text
Input columns: `net_amount`, `tax_amount`, `currency`, `created_at`, and `is_refunded`.

Rules:
- Exclude refunded rows from net sales totals, but retain them in the audit output.
- Convert currencies using the rate for each row's `created_at` date.
- Treat a null `tax_amount` as unknown; do not replace it with zero.
- Flag, but do not remove, rows where `net_amount` is below -100.

Order: Validate column types, apply refund handling, convert currency, then aggregate by ISO week. Return both weekly totals and an exception table.
````

### data_04 — data_processing

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Reject a rewrite that removes a threshold, an exception, and an operation-order requirement.

- Expected: `reject_unsafe_candidate`
- Actual: `unsafe_candidate_rejected`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `False`
- Optimization accepted: `False`
- Detected issue types: `['repeated_phrase']`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 174 → 174 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Pipeline for `src/jobs/clean_orders.py`:

1. Parse timestamps as UTC.
2. Drop records with a missing `order_id`, except records whose `source` is `manual_adjustment`; retain those in the exception output.
3. Remove duplicate `order_id` values only when their normalized payloads are identical.
4. Quarantine records with `total` greater than 100000; do not delete them.

After cleaning, calculate daily totals and write the exception output to `orders_rejected.csv`. Preserve the source row number in every output.
````

Final prompt:

````text
Pipeline for `src/jobs/clean_orders.py`:

1. Parse timestamps as UTC.
2. Drop records with a missing `order_id`, except records whose `source` is `manual_adjustment`; retain those in the exception output.
3. Remove duplicate `order_id` values only when their normalized payloads are identical.
4. Quarantine records with `total` greater than 100000; do not delete them.

After cleaning, calculate daily totals and write the exception output to `orders_rejected.csv`. Preserve the source row number in every output.
````

Injected LLM candidate:

````text
Clean orders by removing rows without an order ID and duplicate order IDs. Delete orders over 100000, then calculate daily totals.
````

Rejected LLM candidate reasons:

- Numbers lost: 1, 2, 3, 4
- Code/URL/quoted/JSON content changed or lost: `src/jobs/clean_orders.py`; `order_id`; `source`
- Output-format requirement lost: csv
- Named items lost: UTC
- Constraint(s) possibly lost: Drop records with a missing `order_id`, except rec; Remove duplicate `order_id` values only when their; Quarantine records with `total` greater than 10000
- Keyword coverage 23% is below 90%
- Lexical similarity 0.31 is below 0.35

### general_01 — general_task

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Remove a repeated exact response instruction while retaining audience, scope, and output requirements.

- Expected: `accept_safe_optimization`
- Actual: `optimized`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `True`
- Detected issue types: `['redundancy', 'repeated_phrase']`
- Candidate changes: `["Removed repeated content: 'Use only the attached policy as a source.' (already covered by 'Use only the attached policy as a source.')"]`
- Fallback used: `False`
- Fallback reason: `not applicable`
- Tokens: 156 → 143 
- Estimated tokens saved: **13**
- Reduction percentage: **8.33%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Task: Summarize the attached policy for new employees.

Content requirements:
- Cover eligibility, enrollment dates, and the appeal process.
- Do not give legal advice or infer rules absent from the policy.
- Use only the attached policy as a source.

Output requirements:
- Use exactly 5 bullet points.
- Keep each bullet under 30 words.
- Quote section numbers when referring to a specific rule.
- Use only the attached policy as a source.

If the policy does not answer a question, say that the information is not specified.
````

Final prompt:

````text
Task: Summarize the attached policy for new employees.

Content requirements:
- Cover eligibility, enrollment dates, and the appeal process.
- Do not give legal advice or infer rules absent from the policy.
- Use only the attached policy as a source.

Output requirements:
- Use exactly 5 bullet points.
- Keep each bullet under 30 words.
- Quote section numbers when referring to a specific rule.
If the policy does not answer a question, say that the information is not specified.
````

### general_02 — general_task

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Consolidate an exact repeated research instruction without losing source and uncertainty constraints.

- Expected: `accept_safe_optimization`
- Actual: `optimized`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `True`
- Detected issue types: `['redundancy', 'repeated_phrase']`
- Candidate changes: `["Removed repeated content: 'Compare the reported retention outcomes.' (already covered by 'Compare the reported retention outcomes.')"]`
- Fallback used: `False`
- Fallback reason: `not applicable`
- Tokens: 165 → 153 
- Estimated tokens saved: **12**
- Reduction percentage: **7.27%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Question: Compare the two supplied studies on remote work and employee retention.

Research tasks:
- Identify each study's sample size, duration, and population.
- Compare the reported retention outcomes.
- Compare the reported retention outcomes.
- Distinguish correlation from causal evidence.

Source handling:
- Use only the supplied studies.
- Attribute each numerical claim to its study.
- If a value is not reported, mark it as not reported rather than estimating it.

Deliverable: Provide a short comparison table followed by a paragraph describing limitations.
````

Final prompt:

````text
Question: Compare the two supplied studies on remote work and employee retention.

Research tasks:
- Identify each study's sample size, duration, and population.
- Compare the reported retention outcomes.
- Distinguish correlation from causal evidence.

Source handling:
- Use only the supplied studies.
- Attribute each numerical claim to its study.
- If a value is not reported, mark it as not reported rather than estimating it.

Deliverable: Provide a short comparison table followed by a paragraph describing limitations.
````

### general_03 — general_task

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Keep similar but distinct requests, mixed formats, quantities, and exceptions.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 176 → 176 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Review the supplied incident timeline and produce two deliverables.

Analysis:
- Identify the earliest confirmed cause, not the earliest suspected cause.
- List every customer-visible impact, including impacts resolved within 10 minutes.
- Separate confirmed facts from hypotheses.

Deliverables:
- First, return a table with UTC timestamps and source references.
- Then, write a plain-language summary of no more than 180 words.
- Include exactly 3 follow-up questions for the response team.

Do not combine the table and summary into one format. If evidence is missing, mark the claim as unverified.
````

Final prompt:

````text
Review the supplied incident timeline and produce two deliverables.

Analysis:
- Identify the earliest confirmed cause, not the earliest suspected cause.
- List every customer-visible impact, including impacts resolved within 10 minutes.
- Separate confirmed facts from hypotheses.

Deliverables:
- First, return a table with UTC timestamps and source references.
- Then, write a plain-language summary of no more than 180 words.
- Include exactly 3 follow-up questions for the response team.

Do not combine the table and summary into one format. If evidence is missing, mark the claim as unverified.
````

### general_04 — general_task

- Cohort: `original 20-case baseline`
- Scenarios: `baseline case; no scenario tags`
- Rationale: Reject a candidate that changes the output format and loses a conditional exception.

- Expected: `reject_unsafe_candidate`
- Actual: `unsafe_candidate_rejected`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `False`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 182 → 182 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Using the supplied interview notes, identify themes in participants' comments.

Method:
- Include a theme only when it appears in at least 4 interviews.
- If a theme appears in fewer than 4 interviews, list it separately as a low-frequency observation.
- Do not infer participants' demographic characteristics.

Output: Return valid JSON with `themes`, `low_frequency_observations`, and `evidence` arrays. Include one short verbatim excerpt and its interview ID for each theme. Do not include names in excerpts.

If no theme meets the threshold, return an empty `themes` array.
````

Final prompt:

````text
Using the supplied interview notes, identify themes in participants' comments.

Method:
- Include a theme only when it appears in at least 4 interviews.
- If a theme appears in fewer than 4 interviews, list it separately as a low-frequency observation.
- Do not infer participants' demographic characteristics.

Output: Return valid JSON with `themes`, `low_frequency_observations`, and `evidence` arrays. Include one short verbatim excerpt and its interview ID for each theme. Do not include names in excerpts.

If no theme meets the threshold, return an empty `themes` array.
````

Injected LLM candidate:

````text
Summarize common interview themes in a short paragraph. Include representative quotes and participant names.
````

Rejected LLM candidate reasons:

- Numbers lost: 4
- Code/URL/quoted/JSON content changed or lost: `themes`; `low_frequency_observations`; `evidence`
- Output-format requirement lost: json
- Named items lost: ID, JSON, Return
- Constraint(s) possibly lost: Include a theme only when it appears in at least 4; Do not infer participants' demographic characteris; Do not include names in excerpts.
- Keyword coverage 15% is below 90%
- Lexical similarity 0.17 is below 0.35

### software_05 — software_development

- Cohort: `new in milestone 3`
- Scenarios: `genuine_redundancy, section_scoped, security_literals`
- Rationale: Remove a repeated credential-logging prohibition repeated in security and diagnostics sections.

- Expected: `accept_safe_optimization`
- Actual: `optimized`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `True`
- Detected issue types: `['duplicate_constraint', 'repeated_phrase']`
- Candidate changes: `["Removed repeated content: 'Never write access tokens to logs.' (already covered by 'Never write access tokens to logs.')"]`
- Fallback used: `False`
- Fallback reason: `not applicable`
- Tokens: 143 → 131 
- Estimated tokens saved: **12**
- Reduction percentage: **8.39%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Project: Background invoice worker

Security requirements:
- Never write access tokens to logs.
- Store signing keys in the platform secret store.
- Restrict invoice downloads to users with the `billing:read` permission.

Diagnostics requirements:
- Never write access tokens to logs.
- Include the invoice ID and correlation ID in structured error events.
- Retain diagnostic events for 14 days.

Testing: Verify that a denied download returns 403 and that logs contain no token value.
````

Final prompt:

````text
Project: Background invoice worker

Security requirements:
- Never write access tokens to logs.
- Store signing keys in the platform secret store.
- Restrict invoice downloads to users with the `billing:read` permission.

Diagnostics requirements:
- Include the invoice ID and correlation ID in structured error events.
- Retain diagnostic events for 14 days.

Testing: Verify that a denied download returns 403 and that logs contain no token value.
````

### software_06 — software_development

- Cohort: `new in milestone 3`
- Scenarios: `section_scoped, similar_but_distinct, frontend_backend`
- Rationale: Keep similar validation requirements scoped to separate application layers.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `['repeated_phrase']`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 143 → 143 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Change request: Add a saved-search workflow.

Frontend: Validate the search name before enabling Save, and show the field-level message beside the input.

API: Validate the request schema and return 422 with a machine-readable error code when the name is empty.

Persistence: Before inserting, verify that the owner still exists and that the name is unique for that owner. Return 409 for a duplicate.

Do not treat client-side validation as a substitute for API or persistence validation.
````

Final prompt:

````text
Change request: Add a saved-search workflow.

Frontend: Validate the search name before enabling Save, and show the field-level message beside the input.

API: Validate the request schema and return 422 with a machine-readable error code when the name is empty.

Persistence: Before inserting, verify that the owner still exists and that the name is unique for that owner. Return 409 for a duplicate.

Do not treat client-side validation as a substitute for API or persistence validation.
````

### software_07 — software_development

- Cohort: `new in milestone 3`
- Scenarios: `complex_multisection, section_scoped, ordering, security_literals`
- Rationale: Preserve a realistic multi-section application brief with different deployment, security, and data constraints.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 296 → 296 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Project objective: Add scheduled exports to the existing service without changing current customer-facing endpoints.

Technology stack: Keep the Python 3.12 runtime and PostgreSQL 15 schema. Use the existing queue worker; do not add a second scheduler.

Functional requirements:
- Let an administrator schedule a CSV export for one workspace.
- Include only records visible to that workspace at execution time.
- Store the result for 24 hours and expose its download URL through the existing export-status endpoint.

Security requirements:
- Recheck workspace membership when the export runs, not only when it is scheduled.
- Do not include access tokens or signed URLs in application logs.

Reliability requirements:
- Mark a job `failed` if generation fails and retain its diagnostic code.
- Do not retry a job after its workspace has been deleted.

Testing and delivery:
- Add tests for revoked membership, expired downloads, and worker retry behavior.
- Report the migration, changed files, and test commands.
````

Final prompt:

````text
Project objective: Add scheduled exports to the existing service without changing current customer-facing endpoints.

Technology stack: Keep the Python 3.12 runtime and PostgreSQL 15 schema. Use the existing queue worker; do not add a second scheduler.

Functional requirements:
- Let an administrator schedule a CSV export for one workspace.
- Include only records visible to that workspace at execution time.
- Store the result for 24 hours and expose its download URL through the existing export-status endpoint.

Security requirements:
- Recheck workspace membership when the export runs, not only when it is scheduled.
- Do not include access tokens or signed URLs in application logs.

Reliability requirements:
- Mark a job `failed` if generation fails and retain its diagnostic code.
- Do not retry a job after its workspace has been deleted.

Testing and delivery:
- Add tests for revoked membership, expired downloads, and worker retry behavior.
- Report the migration, changed files, and test commands.
````

### software_08 — software_development

- Cohort: `new in milestone 3`
- Scenarios: `section_scoped, unsafe_llm_section_removal, frontend_backend, unsafe_llm_identifier_change`
- Rationale: Reject a deterministic rewrite that drops a frontend-specific requirement while retaining backend work.

- Expected: `reject_unsafe_candidate`
- Actual: `unsafe_candidate_rejected`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `False`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 147 → 147 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Implement the account recovery change.

Frontend requirements:
- Keep the recovery form usable with keyboard-only navigation.
- Show the server-provided recovery status without exposing the account's email address.

Backend requirements:
- Expose the result using the exact response field `recovery_status`.
- Expire recovery codes after 20 minutes.
- Return the same response body for known and unknown email addresses.

Verification: Test keyboard navigation, expired codes, and both email lookup outcomes.
````

Final prompt:

````text
Implement the account recovery change.

Frontend requirements:
- Keep the recovery form usable with keyboard-only navigation.
- Show the server-provided recovery status without exposing the account's email address.

Backend requirements:
- Expose the result using the exact response field `recovery_status`.
- Expire recovery codes after 20 minutes.
- Return the same response body for known and unknown email addresses.

Verification: Test keyboard navigation, expired codes, and both email lookup outcomes.
````

Injected LLM candidate:

````text
Implement account recovery. Return the result in `status` and expire recovery codes after 20 minutes and return the same response for known and unknown addresses. Test expired codes and email lookup outcomes.
````

Rejected LLM candidate reasons:

- Code/URL/quoted/JSON content changed or lost: `recovery_status`
- Constraint(s) possibly lost: Keep the recovery form usable with keyboard-only n; Show the server-provided recovery status without e
- Keyword coverage 46% is below 90%

### technical_05 — technical_specification

- Cohort: `new in milestone 3`
- Scenarios: `multiple_output_contracts, ordering, section_labels`
- Rationale: Preserve two distinct ordered output contracts: JSON Lines records and a separate JSON summary.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `['repeated_phrase']`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 144 → 144 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Export contract:
1. Write one UTF-8 JSON object per line to `events.jsonl`; do not add a header.
2. After the data file is complete, write a separate JSON object to `summary.json`.

The summary must contain `record_count`, `rejected_count`, and `generated_at`. Each data object must contain `event_id` and `occurred_at`.

Keep the two files separate. The summary is not a JSON Lines record, and the data file is not a JSON array.
````

Final prompt:

````text
Export contract:
1. Write one UTF-8 JSON object per line to `events.jsonl`; do not add a header.
2. After the data file is complete, write a separate JSON object to `summary.json`.

The summary must contain `record_count`, `rejected_count`, and `generated_at`. Each data object must contain `event_id` and `occurred_at`.

Keep the two files separate. The summary is not a JSON Lines record, and the data file is not a JSON array.
````

### technical_06 — technical_specification

- Cohort: `new in milestone 3`
- Scenarios: `retry_policies, conditions_exceptions, idempotency`
- Rationale: Keep retry rules distinct by operation, status, idempotency, and maximum attempts.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 151 → 151 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Retry behavior for the ingestion client:

- Retry `GET /v1/batches/{id}` on 429 or 503, at most 4 attempts total, using exponential backoff.
- Retry `POST /v1/batches` only when the request includes an `Idempotency-Key`; use the same key for each attempt and stop after 2 retries.
- Never retry 400 or 401.
- Do not retry a POST whose response body indicates that validation failed.

Record the final status and attempt count. Do not count the initial request as a retry.
````

Final prompt:

````text
Retry behavior for the ingestion client:

- Retry `GET /v1/batches/{id}` on 429 or 503, at most 4 attempts total, using exponential backoff.
- Retry `POST /v1/batches` only when the request includes an `Idempotency-Key`; use the same key for each attempt and stop after 2 retries.
- Never retry 400 or 401.
- Do not retry a POST whose response body indicates that validation failed.

Record the final status and attempt count. Do not count the initial request as a retry.
````

### technical_07 — technical_specification

- Cohort: `new in milestone 3`
- Scenarios: `quoted_literals, technical_identifiers, complex_multisection, urls_paths_env`
- Rationale: Preserve literal forms and technical values in a multi-section deployment specification.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 338 → 338 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Project objective: Add an archive preview mode for the existing document service.

Technology and configuration:
- Keep the worker in `src/workers/archive.py` and continue using the existing PostgreSQL 15 database.
- Read `ARCHIVE_BUCKET` and `ARCHIVE_REGION` from the deployment environment.
- Keep the legacy setting 'archive_mode' unchanged and do not rename it to 'storage_mode'.

API requirements:
- Send `X-Request-ID` to `https://archive.example.test/v1/objects`.
- Preserve the response header `ETag` and the exact display label "Archive preview".
- Return the object key using `tenant/{tenant_id}/{object_id}`.

Security and data:
- A preview must not write or delete an object.
- Retain the operator note “No object is deleted during a dry run.”
- Do not expose signed URLs in application logs.

Code constraint: Keep this comparison exact: `if status_code == 304:`.

Testing and deliverables:
- Test the 304 response, missing bucket configuration, and an expired signed URL separately.
- List changed files and provide the test command.
````

Final prompt:

````text
Project objective: Add an archive preview mode for the existing document service.

Technology and configuration:
- Keep the worker in `src/workers/archive.py` and continue using the existing PostgreSQL 15 database.
- Read `ARCHIVE_BUCKET` and `ARCHIVE_REGION` from the deployment environment.
- Keep the legacy setting 'archive_mode' unchanged and do not rename it to 'storage_mode'.

API requirements:
- Send `X-Request-ID` to `https://archive.example.test/v1/objects`.
- Preserve the response header `ETag` and the exact display label "Archive preview".
- Return the object key using `tenant/{tenant_id}/{object_id}`.

Security and data:
- A preview must not write or delete an object.
- Retain the operator note “No object is deleted during a dry run.”
- Do not expose signed URLs in application logs.

Code constraint: Keep this comparison exact: `if status_code == 304:`.

Testing and deliverables:
- Test the 304 response, missing bucket configuration, and an expired signed URL separately.
- List changed files and provide the test command.
````

### technical_08 — technical_specification

- Cohort: `new in milestone 3`
- Scenarios: `unsafe_llm_numeric_change, conditions_exceptions, nested_data_conditions`
- Rationale: Reject a rewrite that changes a numeric threshold and removes an oversized-record exception.

- Expected: `reject_unsafe_candidate`
- Actual: `unsafe_candidate_rejected`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `False`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 119 → 119 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Batch acceptance rules:
- Accept a batch with no more than 240 records.
- If it contains 241 to 900 records, divide it into chunks of 240 and preserve input order.
- Reject individual records larger than 6 MiB; continue processing the other records in the chunk.
- Do not reject the whole batch because one record exceeds the size limit.

Return a JSON report with accepted, rejected, and deferred counts.
````

Final prompt:

````text
Batch acceptance rules:
- Accept a batch with no more than 240 records.
- If it contains 241 to 900 records, divide it into chunks of 240 and preserve input order.
- Reject individual records larger than 6 MiB; continue processing the other records in the chunk.
- Do not reject the whole batch because one record exceeds the size limit.

Return a JSON report with accepted, rejected, and deferred counts.
````

Injected LLM candidate:

````text
Accept batches of up to 200 records. Split larger batches into chunks and reject records larger than 6 MiB. Return a JSON report with accepted and rejected counts.
````

Rejected LLM candidate reasons:

- Numbers lost: 240, 241, 900
- Constraint(s) possibly lost: Accept a batch with no more than 240 records.; Do not reject the whole batch because one record e
- Keyword coverage 41% is below 90%

### api_05 — api_requirements

- Cohort: `new in milestone 3`
- Scenarios: `section_scoped, authn_authz, similar_but_distinct`
- Rationale: Preserve authentication versus authorization and distinct responses for two endpoints.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `['repeated_phrase', 'excessive_context']`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 139 → 139 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Access contract:

`GET /v2/profile`
- Authenticate with a valid session cookie.
- Return 401 if the cookie is missing or expired.
- Return only the caller's profile.

`GET /v2/teams/{team_id}`
- Authenticate with a valid session cookie.
- Authorize the caller against the requested team's membership list.
- Return 403 when the caller is authenticated but not a member.

Do not treat authentication as proof of team membership.
````

Final prompt:

````text
Access contract:

`GET /v2/profile`
- Authenticate with a valid session cookie.
- Return 401 if the cookie is missing or expired.
- Return only the caller's profile.

`GET /v2/teams/{team_id}`
- Authenticate with a valid session cookie.
- Authorize the caller against the requested team's membership list.
- Return 403 when the caller is authenticated but not a member.

Do not treat authentication as proof of team membership.
````

### api_06 — api_requirements

- Cohort: `new in milestone 3`
- Scenarios: `retry_policies, conditions_exceptions, multiple_output_contracts`
- Rationale: Keep endpoint-specific retry conditions and different response formats separate.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 130 → 130 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Client contract:

For `GET /v1/catalog`, retry 503 responses at most 3 times. Do not retry 404.

For `POST /v1/orders`, retry 429 only when the server supplies `Retry-After` and the request has an `Idempotency-Key`. Never retry a 409 conflict.

Successful catalog responses use JSON. Order errors use `application/problem+json`; successful order creation returns 201 with `order_id`.
````

Final prompt:

````text
Client contract:

For `GET /v1/catalog`, retry 503 responses at most 3 times. Do not retry 404.

For `POST /v1/orders`, retry 429 only when the server supplies `Retry-After` and the request has an `Idempotency-Key`. Never retry a 409 conflict.

Successful catalog responses use JSON. Order errors use `application/problem+json`; successful order creation returns 201 with `order_id`.
````

### api_07 — api_requirements

- Cohort: `new in milestone 3`
- Scenarios: `unsafe_llm_format_change, multiple_output_contracts, technical_identifiers`
- Rationale: Reject a candidate that changes a strict JSON response contract into CSV and drops required fields.

- Expected: `reject_unsafe_candidate`
- Actual: `unsafe_candidate_rejected`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `False`
- Optimization accepted: `False`
- Detected issue types: `['repeated_phrase']`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 132 → 132 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
`GET /v3/ledger/export` response contract:
- Return `application/json` with a top-level `items` array and a `next_cursor` field.
- Include `entry_id`, `posted_at`, and `amount_minor` in every item.
- Return an empty `items` array and a null `next_cursor` when there are no entries.
- Do not return CSV or omit `amount_minor` for zero-value entries.
````

Final prompt:

````text
`GET /v3/ledger/export` response contract:
- Return `application/json` with a top-level `items` array and a `next_cursor` field.
- Include `entry_id`, `posted_at`, and `amount_minor` in every item.
- Return an empty `items` array and a null `next_cursor` when there are no entries.
- Do not return CSV or omit `amount_minor` for zero-value entries.
````

Injected LLM candidate:

````text
Export the ledger as CSV with entry IDs and dates. If there are no entries, return an empty file.
````

Rejected LLM candidate reasons:

- Code/URL/quoted/JSON content changed or lost: `GET /v3/ledger/export`; `application/json`; `items`
- Output-format requirement lost: json
- Constraint(s) possibly lost: Return an empty `items` array and a null `next_cur; Do not return CSV or omit `amount_minor` for zero-
- Keyword coverage 25% is below 90%
- Lexical similarity 0.32 is below 0.35

### data_05 — data_processing

- Cohort: `new in milestone 3`
- Scenarios: `genuine_redundancy, nested_data_conditions, null_handling`
- Rationale: Remove an exact repeated null-imputation prohibition across cleaning and aggregation sections.

- Expected: `accept_safe_optimization`
- Actual: `optimized`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `True`
- Detected issue types: `['duplicate_constraint', 'repeated_phrase']`
- Candidate changes: `["Removed repeated content: 'Do not replace missing QZPH1QZ values with zero.' (already covered by 'Do not replace missing QZPH1QZ values with zero.')"]`
- Fallback used: `False`
- Fallback reason: `not applicable`
- Tokens: 154 → 134 
- Estimated tokens saved: **20**
- Reduction percentage: **12.99%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Dataset: Daily water-quality readings

Cleaning rules:
- Parse `sampled_at` as UTC.
- Keep records with a missing `nitrate_mg_l` and mark them as incomplete.
- Do not replace missing `nitrate_mg_l` values with zero.

Aggregation rules:
- Group by station and UTC calendar date.
- Do not replace missing `nitrate_mg_l` values with zero.
- Calculate the median from present values only, and report the count of missing readings.

Write the output to `daily_quality.parquet`.
````

Final prompt:

````text
Dataset: Daily water-quality readings

Cleaning rules:
- Parse `sampled_at` as UTC.
- Keep records with a missing `nitrate_mg_l` and mark them as incomplete.
- Do not replace missing `nitrate_mg_l` values with zero.

Aggregation rules:
- Group by station and UTC calendar date.
- Calculate the median from present values only, and report the count of missing readings.

Write the output to `daily_quality.parquet`.
````

### data_06 — data_processing

- Cohort: `new in milestone 3`
- Scenarios: `nested_data_conditions, conditions_exceptions, ordering`
- Rationale: Preserve nested null, threshold, exception, and write-order rules for records.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `['repeated_phrase']`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 158 → 158 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Process the delivery feed as follows:
1. If `delivered_at` is null and `status` is `in_transit`, leave the record pending.
2. If `delivered_at` is null and `status` is `delivered`, place the record in the exception file; do not infer a delivery time.
3. Reject `weight_kg` below 0 or above 80, but retain the rejected row and its source line number.
4. Validate these rules before writing accepted rows to `deliveries.csv`.

Return separate accepted and exception counts.
````

Final prompt:

````text
Process the delivery feed as follows:
1. If `delivered_at` is null and `status` is `in_transit`, leave the record pending.
2. If `delivered_at` is null and `status` is `delivered`, place the record in the exception file; do not infer a delivery time.
3. Reject `weight_kg` below 0 or above 80, but retain the rejected row and its source line number.
4. Validate these rules before writing accepted rows to `deliveries.csv`.

Return separate accepted and exception counts.
````

### data_07 — data_processing

- Cohort: `new in milestone 3`
- Scenarios: `unsafe_llm_exception_removal, nested_data_conditions, technical_identifiers`
- Rationale: Reject a rewrite that removes the manual-adjustment exception and changes a strict comparison.

- Expected: `reject_unsafe_candidate`
- Actual: `unsafe_candidate_rejected`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `False`
- Optimization accepted: `False`
- Detected issue types: `['repeated_phrase']`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 136 → 136 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Reconcile rows from `ledger_import.csv`.

- Ignore rows with a null `account_id`, except rows whose `entry_kind` is `manual_adjustment`; send those to the review table.
- Flag, but do not discard, entries where `delta_minor` is less than -5000.
- Write only validated entries to `ledger_clean.csv` after the review table has been generated.
- Preserve the original `source_row` in both outputs.
````

Final prompt:

````text
Reconcile rows from `ledger_import.csv`.

- Ignore rows with a null `account_id`, except rows whose `entry_kind` is `manual_adjustment`; send those to the review table.
- Flag, but do not discard, entries where `delta_minor` is less than -5000.
- Write only validated entries to `ledger_clean.csv` after the review table has been generated.
- Preserve the original `source_row` in both outputs.
````

Injected LLM candidate:

````text
Remove rows with a null account ID or a delta below -5000. Write the remaining validated entries to ledger_clean.csv.
````

Rejected LLM candidate reasons:

- Code/URL/quoted/JSON content changed or lost: `ledger_import.csv`; `account_id`; `entry_kind`
- Output-format requirement lost: table
- Constraint(s) possibly lost: Flag, but do not discard, entries where `delta_min; Write only validated entries to `ledger_clean.csv`
- Keyword coverage 28% is below 90%

### general_05 — general_task

- Cohort: `new in milestone 3`
- Scenarios: `concise_noop, no_token_savings`
- Rationale: Confirm that a concise, complete request is returned unchanged rather than rewritten without savings.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 21 → 21 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
List three causes of coastal erosion and one practical mitigation for each.
````

Final prompt:

````text
List three causes of coastal erosion and one practical mitigation for each.
````

### general_06 — general_task

- Cohort: `new in milestone 3`
- Scenarios: `mixed_language, non_english, quoted_literals`
- Rationale: Keep English instructions and a Sinhala phrase intact without assuming cross-language equivalence.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 64 → 64 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Summarize the feedback in English using two bullets. Do not translate the Sinhala phrase “හෙට උදේ”; reproduce it exactly in the first bullet. If its meaning is uncertain, say so rather than guessing.
````

Final prompt:

````text
Summarize the feedback in English using two bullets. Do not translate the Sinhala phrase “හෙට උදේ”; reproduce it exactly in the first bullet. If its meaning is uncertain, say so rather than guessing.
````

### general_07 — general_task

- Cohort: `new in milestone 3`
- Scenarios: `unsafe_llm_negation_removal, negation, conditions_exceptions`
- Rationale: Reject a candidate that removes a prohibition and changes the required treatment of named people.

- Expected: `reject_unsafe_candidate`
- Actual: `unsafe_candidate_rejected`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `False`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 72 → 72 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Summarize the supplied meeting notes in plain language. Do not include participants' personal names. Replace each name with `[PERSON]`, but preserve the person's role when the notes state it. If a role is not stated, do not infer one.
````

Final prompt:

````text
Summarize the supplied meeting notes in plain language. Do not include participants' personal names. Replace each name with `[PERSON]`, but preserve the person's role when the notes state it. If a role is not stated, do not infer one.
````

Injected LLM candidate:

````text
Summarize the meeting notes in plain language and identify each participant by name and role.
````

Rejected LLM candidate reasons:

- Code/URL/quoted/JSON content changed or lost: `[PERSON]`
- Constraint(s) possibly lost: Do not include participants' personal names.; If a role is not stated, do not infer one.
- Keyword coverage 45% is below 90%

### general_08 — general_task

- Cohort: `new in milestone 3`
- Scenarios: `multiple_output_contracts, ordering, section_labels`
- Rationale: Preserve separate ordered output formats and their section labels in a concise incident review request.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `['formatting']`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 104 → 104 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Review the incident notes and return these sections in order:
1. `Timeline`: a table with UTC time and source.
2. `Findings`: a Markdown explanation of confirmed causes only.
3. `Actions`: a numbered list with owner and due date.

Keep hypotheses out of `Findings`; label them `Unconfirmed` in a separate note after the table.
````

Final prompt:

````text
Review the incident notes and return these sections in order:
1. `Timeline`: a table with UTC time and source.
2. `Findings`: a Markdown explanation of confirmed causes only.
3. `Actions`: a numbered list with owner and due date.

Keep hypotheses out of `Findings`; label them `Unconfirmed` in a separate note after the table.
````

### general_09 — general_task

- Cohort: `new in milestone 3`
- Scenarios: `mixed_language, non_english, quoted_literals, concise_noop`
- Rationale: Keep an English request and a Spanish source sentence distinct, preserving the original Spanish text without translation.

- Expected: `leave_unchanged`
- Actual: `left_unchanged`
- Case result: `PASS`
- Pipeline candidate validation: `True`
- LLM candidate validation: `not applicable`
- Optimization accepted: `False`
- Detected issue types: `[]`
- Candidate changes: `[]`
- Fallback used: `True`
- Fallback reason: `No safe optimization found; original prompt returned`
- Tokens: 68 → 68 
- Estimated tokens saved: **0**
- Reduction percentage: **0.0%**
- False removal: `False`
- Unexpected optimization: `False`
- Missed optimization opportunity: `False`
- Missing required phrases: `[]`

Original prompt:

````text
Explain the return policy in English in two bullets. Preserve the Spanish sentence “No se aceptan devoluciones después de 30 días” exactly and do not translate it. If its meaning is uncertain, state that rather than guessing.
````

Final prompt:

````text
Explain the return policy in English in two bullets. Preserve the Spanish sentence “No se aceptan devoluciones después de 30 días” exactly and do not translate it. If its meaning is uncertain, state that rather than guessing.
````

## Failures and causes

- None in this curated run.

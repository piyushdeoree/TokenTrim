# Proposed BYOK backend API requirements

**Status: proposed contracts only. These endpoints do not currently exist in the frontend's confirmed API contract.** The frontend uses an in-memory demo adapter until backend routes and schemas are agreed. Production BYOK calls are intentionally disabled.

All routes below are proposals and may be renamed by the backend team. The authenticated user is derived from the existing bearer token; provider credentials must never appear in list/get responses or logs.

## Shared errors

Expected JSON error body: `{ "detail": "Human-readable message", "code": "optional_machine_code" }`.

- `400` invalid request or unsupported provider/model.
- `401` missing or expired authentication.
- `403` user is not allowed to manage or use this connection.
- `404` connection or execution not found.
- `409` conflicting connection state.
- `422` provider rejected the credential or request was invalid.
- `429` provider or application rate limit.
- `502` provider unavailable or upstream error.
- `500` unexpected server error.

## Provider connections

### List connected providers

- **Proposed:** `GET /api/byok/providers`
- **Authentication:** Required bearer token.
- **Request body:** None.
- **Response:** `[{ "provider": "openai", "status": "connected", "connected_at": "ISO-8601", "masked_key": "••••1234" }]`.
- Must return no raw credential. `masked_key` is optional and should be returned only if the backend has safe masked metadata.
- Errors: shared errors.

### Connect or replace a provider key

- **Proposed:** `PUT /api/byok/providers/{provider}/connection`
- **Authentication:** Required bearer token.
- **Request body:** `{ "api_key": "<secret>" }` over TLS. Never echo the request body in responses, logs, traces, or errors.
- **Response:** `{ "provider": "openai", "status": "connected", "connected_at": "ISO-8601", "masked_key": "••••1234" }`.
- The backend should validate the credential with the provider and securely store it according to backend policy.
- Errors: shared errors, including `422` for a provider-rejected key.

### Test an existing connection

- **Proposed:** `POST /api/byok/providers/{provider}/connection/test`
- **Authentication:** Required bearer token.
- **Request body:** None.
- **Response:** `{ "success": true, "message": "Connection verified" }`.
- Errors: shared errors; provider authentication rejection should be distinguishable from transient upstream failure.

### Disconnect a provider

- **Proposed:** `DELETE /api/byok/providers/{provider}/connection`
- **Authentication:** Required bearer token.
- **Request body:** None.
- **Response:** `204 No Content`.
- Errors: shared errors.

## Provider models

### List models available to this user

- **Proposed:** `GET /api/byok/providers/{provider}/models`
- **Authentication:** Required bearer token; provider must be connected.
- **Request body:** None.
- **Response:** `[{ "id": "model-id", "name": "Display name" }]` using actual backend/provider availability.
- Errors: shared errors, including `409` or `404` when disconnected.

## Prompt execution and usage

### Execute an optimized prompt

- **Proposed:** `POST /api/byok/executions`
- **Authentication:** Required bearer token; provider connection must belong to the user.
- **Request body:** `{ "prompt": "optimized prompt", "provider": "openai", "model": "model-id" }`.
- **Response:** `{ "id": "execution-id", "provider": "openai", "model": "model-id", "response": "generated text", "usage": { "input_tokens": 10, "output_tokens": 20, "total_tokens": 30 }, "actual_cost": { "amount": 0.000012, "currency": "USD" }, "actual_savings": null, "duration_ms": 840, "created_at": "ISO-8601", "status": "succeeded" }`.
- Usage counts, actual cost, and duration may be `null` or omitted when unavailable. Never substitute `0` for unavailable data. Currency is an ISO 4217 code. Cost must be calculated by the backend from provider-reported usage and its authoritative pricing data.
- Errors: shared errors; include a safe provider error code/message without secrets or prompt contents unless required by an agreed privacy policy.
- `actual_savings` is optional. If provided, it must be a backend-defined amount and ISO currency, and must not require the frontend to compare values across currencies.

### List execution history (optional)

- **Proposed:** `GET /api/byok/executions?limit=20&offset=0`
- **Authentication:** Required bearer token.
- **Request body:** None.
- **Response:** `[{ "id": "execution-id", "provider": "openai", "model": "model-id", "created_at": "ISO-8601", "status": "succeeded", "usage": { "input_tokens": 10, "output_tokens": 20, "total_tokens": 30 }, "actual_cost": { "amount": 0.000012, "currency": "USD" }, "duration_ms": 840 }]`.
- This API should not return prompts or generated responses unless the product explicitly opts into their persistence and retention.
- Errors: shared errors.

## Contract alignment needed

Before enabling production services, agree on provider identifiers, path prefixes, request/response casing, whether keys are validated during connection, model metadata shape, usage/cost nullability, error shape, and execution-history persistence/retention. Then replace the development adapter with implementations using the shared authenticated `apiClient`.

## Frontend adapter handoff

`ExecutionAdapter` in `src/types/execution.ts` is the shared contract for demo and real adapters. Implement a FastAPI adapter that maps the proposed snake_case JSON to these camelCase types, uses the existing `apiClient` (whose base URL is `NEXT_PUBLIC_API_BASE_URL` and whose interceptor adds the current bearer token), then register it with `configureByokAdapter(adapter)` before the authenticated provider context mounts. `NEXT_PUBLIC_BYOK_MODE=real` disables the demo adapter; this mode must only be enabled alongside a registered adapter. By default, development and test environments use the in-memory demo adapter. No real adapter is included until the proposed API contract is confirmed.

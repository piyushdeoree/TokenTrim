# AI Cost Intelligence & Prompt Optimization Platform: Backend

FastAPI + PostgreSQL service that orchestrates the NLP engine (Person 1) and the cost/ML engine (Person 2),
stores usage, and serves the dashboard API for the React frontend (Person 4).

## Architecture

```mermaid
flowchart LR
    FE[React frontend] -->|JWT or X-API-Key| API[FastAPI routers<br/>app/api]
    API --> SVC[Services<br/>app/services]
    SVC --> REPO[Repositories<br/>app/repositories]
    REPO --> DB[(PostgreSQL)]
    SVC -->|nlp_service adapter| NLP[nlp_engine<br/>Person 1]
    SVC -->|cost_service adapter| COST[cost_engine<br/>Person 2]
```

Request flow for `POST /api/analyze-prompt`:
validate input and model, then `nlp_engine.analyze_prompt`, then `cost_engine.predict_output_tokens` and
`estimate_cost` (using prices read from the DB), then save prompt, analysis, usage and cost in one transaction, then respond.

Layers: **api** (HTTP only) → **services** (business rules, orchestration) → **repositories** (queries) → **models** (ORM).
Engines are reached only through `services/nlp_service.py` and `services/cost_service.py`.

## Database ER diagram

```mermaid
erDiagram
    users ||--o{ projects : owns
    users ||--o{ api_keys : has
    users ||--o{ team_members : "is member"
    teams ||--o{ team_members : has
    teams ||--o{ projects : "shared with"
    projects ||--o{ prompts : contains
    prompts ||--|| prompt_analysis : analysed_by
    projects ||--o{ usage_records : tracks
    users ||--o{ usage_records : makes
    models ||--o{ usage_records : used_in
    models ||--o{ model_pricing : priced_by
    usage_records ||--|| cost_records : costs
    prompts ||--o{ usage_records : produces
```

`revoked_tokens` (JWT blocklist for logout) is also created. Cost columns are `NUMERIC(14,8)`; prices are per 1,000 tokens.

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # then set SECRET_KEY and DATABASE_URL
createdb ai_cost                                       # or create the DB with pgAdmin
alembic revision --autogenerate -m "initial schema"    # first time only; commit the generated file
alembic upgrade head
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs (Swagger UI) or `/redoc`. Click **Authorize** and paste the token from `/auth/login`.

Quick start without Alembic (dev only): `python -m app.database.init_db`.

### Environment variables

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | local Postgres | `postgresql+psycopg2://user:pass@host:5432/db` |
| `SECRET_KEY` | **required** | JWT signing key; use a long random value |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 60 | |
| `CORS_ORIGINS` | localhost:5173, :3000 | JSON list; add the real frontend URL |
| `RATE_LIMIT_PER_MINUTE` | 30 | per user on `/api/analyze-prompt` (login: 10/min per email) |
| `MAX_PROMPT_CHARS` | 50000 | |
| `USE_STUB_ENGINES` | false | `true` = placeholder engines, so the backend runs before Persons 1 and 2 deliver |
| `SEED_ON_STARTUP` | true | seeds sample models/pricing if the `models` table is empty |

### Migrations

```bash
alembic revision --autogenerate -m "describe change"   # after editing app/models
alembic upgrade head                                   # apply
alembic downgrade -1                                   # roll back one step
```

### Tests

```bash
pytest -q
```
Tests use in-memory SQLite and stub engines, so they need no Postgres. They cover registration, login, logout,
project CRUD, prompt analysis, usage recording, dashboard aggregation, API keys, team permissions, invalid and
unauthorized requests, rate limiting and engine failures.

## Integration contracts (assumed, confirm with Persons 1 and 2)

```python
# Person 1
nlp_engine.analyze_prompt(prompt: str, model: str) -> {
    "original_tokens": int, "optimized_tokens": int, "optimized_prompt": str,
    "issues": list, "suggestions": list }

# Person 2: prices come from the DB and are passed in, so there is no hardcoded pricing table
cost_engine.predict_output_tokens(prompt: str, model: str, input_tokens: int) -> int
cost_engine.estimate_cost(input_tokens, output_tokens, input_price_per_1k, output_price_per_1k, model) -> float
cost_engine.forecast_cost(daily_costs: list[float], horizon_days: int) -> list[float]
```
If their real signatures differ, change only `services/nlp_service.py` / `services/cost_service.py`.
Both packages must be importable (`pip install -e` them, or add them to `PYTHONPATH`).

Semantics: `estimated_cost` = cost of the **original** prompt; `potential_saving` = original minus optimized cost;
usage `input_tokens` = original tokens, `output_tokens` = predicted output tokens.

## Endpoints

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` |
| Projects | `POST/GET /projects`, `GET/PUT/DELETE /projects/{id}` |
| Analysis | `POST /api/analyze-prompt` |
| Usage | `GET /usage`, `GET /usage/{project_id}` (`limit`, `offset`, `model`) |
| Dashboard | `GET /dashboard/overview`, `daily-usage`, `monthly-usage`, `cost-by-model`, `cost-by-project`, `recent-activity`, `project-history`, `forecast` |
| API keys | `POST/GET /api-keys`, `DELETE /api-keys/{id}` |
| Teams | `POST/GET /teams`, `GET/DELETE /teams/{id}`, `GET/POST /teams/{id}/members`, `PATCH/DELETE /teams/{id}/members/{user_id}` |
| Models | `GET /models`, `GET /models/pricing`, `GET /models/{id}` |
| Health | `GET /health` |

Every endpoint is documented in `/docs` with schemas and examples.

### Errors

All errors share one shape; stack traces are logged server-side only:
```json
{"error": {"code": "NOT_FOUND", "message": "Project not found."}}
```
Codes: `VALIDATION_ERROR` 422, `BAD_REQUEST` 400, `UNAUTHORIZED` 401, `FORBIDDEN` 403, `NOT_FOUND` 404,
`CONFLICT` 409, `RATE_LIMITED` 429, `NLP_SERVICE_ERROR` / `ML_SERVICE_ERROR` 502, `DATABASE_ERROR` / `INTERNAL_ERROR` 500.

### Examples

```bash
curl -X POST localhost:8000/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"dev@example.com","password":"S3cure-pass!","full_name":"Dev"}'

TOKEN=$(curl -s -X POST localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"dev@example.com","password":"S3cure-pass!"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -X POST localhost:8000/projects -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Support Bot"}'

curl -X POST localhost:8000/api/analyze-prompt -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"prompt":"Please could you kindly summarise this text ...","model":"gpt-4o-mini","project_id":1}'

curl localhost:8000/dashboard/overview -H "Authorization: Bearer $TOKEN"

# API key (secret shown once), then use it instead of a JWT
curl -X POST localhost:8000/api-keys -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"name":"ci"}'
curl localhost:8000/usage -H "X-API-Key: acp_..."
```

## Security notes

- Passwords hashed with bcrypt (max 72 chars enforced). Secrets only from environment variables.
- JWT logout = token `jti` blocklist (`revoked_tokens`). Purge rows past `expires_at` periodically.
- API keys: random, shown once, only the SHA-256 hash is stored; list endpoints expose the prefix only.
- Teams: roles `owner > admin > member`, enforced in `services/team_service.py`. Resources you cannot access return 404, not 403.
- Rate limiting is in-memory (single process). Use Redis if you run multiple workers.
- Provider API keys never go to the frontend; the backend is the only caller of the engines.
- Seed prices in `app/database/seed.py` are illustrative placeholders. Replace them with real pricing from Person 2.

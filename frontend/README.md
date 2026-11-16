# TokenTrim Frontend (Next.js + TypeScript + Tailwind + Recharts)

## Run
    npm install
    npm run dev          # http://localhost:3000
    npm test             # Jest + Testing Library
    npx playwright install && npm run e2e
    npm run lint         # type check

## Go live
Set `NEXT_PUBLIC_API_BASE_URL=<FastAPI url>` in `.env.local`.

## API contract
Agreed: `POST /api/analyze-prompt`, `GET /models/pricing`.
**Assumed, confirm with Person 3:** `POST /api/auth/login`, `POST /api/auth/register` (returns `access_token`, optional `user`), `GET /api/dashboard`,
`GET|POST /api/projects`, `POST /api/analyses`, `GET|POST /api/api-keys` (POST returns `{secret}` once), `DELETE /api/api-keys/:id`,
`GET /api/team`, `POST /api/team/invite`, `POST /api/team/:id/role`, `DELETE /api/team/:id`.
Response shapes are in `src/types/`. Settings are stored in localStorage until a backend endpoint exists.

## Update notes
- Theme tokens live in `src/styles/globals.css` (CSS variables) and `tailwind.config.ts` (`bg-page`, `bg-surface`, `bg-chart`, `bg-btn`, `bg-card`).
- Login/register are a modal on Home (`/?auth=login|register`); `/login` and `/register` redirect there.
- New assumed endpoints (confirm with Person 3): `GET /api/dashboard?range=weekly|monthly|yearly|custom&from=YYYY-MM-DD&to=YYYY-MM-DD` (now also returns `byModelTokens`, no longer `recent`), `GET /api/recent-activity`.

## Frontend enhancement dependencies

The current frontend API contract does not define BYOK provider management, provider model discovery, prompt execution, supported display currencies, or converted cost values. Those features must not call guessed routes or show fabricated connection, usage, or conversion data. Once the backend contracts are agreed, the frontend can wire the flows through `apiClient` and render the returned data.

The backend contract needed for BYOK should cover authenticated provider connection create/replace, connection status/list (without returning credentials), connection test, disconnect, models for a connected provider, and execution of the optimized prompt. Execution responses should identify provider and model and include actual input/output/total token counts, actual cost and currency, plus duration when available. Missing usage or cost values must remain unavailable in the UI.

The currency contract should provide the supported display currencies and converted values for each relevant cost, together with the original amount and transaction currency where applicable. The frontend will not maintain exchange rates or convert amounts locally. User preference persistence can use the existing settings mechanism after backend preference support is confirmed.

Recent history uses the existing `GET /history?limit=10` contract. The sidebar displays the existing prompt/title and date information; provider, model, and execution status are rendered only when those fields are present in returned history records. The full list remains available through `GET /history` on the Prompt History page.

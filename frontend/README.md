# TokenTrim Frontend (Next.js + TypeScript + Tailwind + Recharts)

## Run
    npm install
    npm run dev          # http://localhost:3000, mock data on (NEXT_PUBLIC_USE_MOCKS=true)
    npm test             # Jest + Testing Library
    npx playwright install && npm run e2e
    npm run lint         # type check

## Go live
Set `NEXT_PUBLIC_USE_MOCKS=false` and `NEXT_PUBLIC_API_BASE_URL=<FastAPI url>` in `.env.local`.

## API contract
Agreed: `POST /api/analyze-prompt`, `GET /models/pricing`.
**Assumed, confirm with Person 3:** `POST /api/auth/login`, `POST /api/auth/register` (returns `access_token`, optional `user`), `GET /api/dashboard`,
`GET|POST /api/projects`, `POST /api/analyses`, `GET|POST /api/api-keys` (POST returns `{secret}` once), `DELETE /api/api-keys/:id`,
`GET /api/team`, `POST /api/team/invite`, `POST /api/team/:id/role`, `DELETE /api/team/:id`.
Response shapes are in `src/types/` and `src/services/mocks/`. Settings are stored in localStorage until a backend endpoint exists.

## Update notes
- Theme tokens live in `src/styles/globals.css` (CSS variables) and `tailwind.config.ts` (`bg-page`, `bg-surface`, `bg-chart`, `bg-btn`, `bg-card`).
- Login/register are a modal on Home (`/?auth=login|register`); `/login` and `/register` redirect there.
- New assumed endpoints (confirm with Person 3): `GET /api/dashboard?range=weekly|monthly|yearly|custom&from=YYYY-MM-DD&to=YYYY-MM-DD` (now also returns `byModelTokens`, no longer `recent`), `GET /api/recent-activity`.

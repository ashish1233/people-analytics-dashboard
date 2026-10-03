# Compensation Insights — frontend

The People Analytics team's compensation dashboard. It is the worked example of
the consumption model: a tenant app built from `templates/web/` plus
`@insights-platform/ui-kit`, in its own repository, as ADR-1 describes.

**It is deliberately trivial.** A login screen, one table, a sign-out button.
Everything interesting about this app is in what it *doesn't* contain — no auth
code, no fetch plumbing, no design decisions.

## What makes it different from the template

Three things, and nothing else:

1. `src/config.ts` is filled in — tenant `people-analytics`, scopes
   `insights:read` and `insights:read_sensitive`.
2. It declares `EXPECTED_TIER = 'restricted'`, so the header carries the
   restricted-tier marking (see below).
3. The columns and copy name compensation metrics rather than placeholders.

The file layout, the hooks, and the component usage are unchanged from the
scaffold. That is the point.

## Restricted tier

This tenant is on the **restricted tier** (ADR-2), because compensation
disclosure cannot be walked back. Two consequences show up in this UI:

**The header is marked.** The `AppShell` renders a muted-ochre *Restricted tier*
badge and a persistent band across the top. The colour is not the danger red —
restricted tier is a normal operating state, not a fault — but it is distinct
enough that nobody mistakes this app for a standard-tier one in a screenshot
during an incident.

**Tier is read from the backend, not asserted here.** ADR-2 makes tier a
property of the tenant held in platform configuration, so the app does not get
to claim its own. `GET /health` is the source of truth; `EXPECTED_TIER` only
fills the gap before health answers, and `App.tsx` raises a warning if the two
disagree. A tenant believed to be restricted that is actually running without
fail-closed audit is worth interrupting someone over.

**A failed load can mean the audit sink, not the warehouse.** On this tier an
access that cannot be recorded does not happen — the request returns 503. The
error Alert says so, because "no data" and "we refused to serve data we could
not log" look identical otherwise.

## Run it

```sh
npm install
npm run dev        # http://localhost:5173
```

Expects the backend at `http://localhost:8000` and the identity stub at
`http://localhost:8081`. Override with `VITE_API_BASE_URL` and
`VITE_IDENTITY_BASE_URL` — see `.env.example`.

```sh
npm run build
npm run typecheck
```

## Contract it depends on

| Call | Shape |
| --- | --- |
| `POST {identity}/token/user` | `{ tenant_id, subject, scopes }` → `{ token }` |
| `GET {api}/health` | → `{ status, tenant_id, tier, sdk_version }` |
| `GET {api}/api/insights` | `Authorization: Bearer <token>` → `{ rows: [{ id, metric, value, period }] }` |

A 401 from `/api/insights` ends the session and returns the user to the sign-in
screen headed "Session expired", not to a blank page.

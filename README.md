# People Analytics dashboard

An example tenant application on the Insights Platform. One tenant, one
repository, one deploy — the ownership boundary ADR-1 says is the only one worth
drawing.

- **Tenant:** `people-analytics`
- **Tier:** restricted (ADR-2), assigned by the platform team
- **`backend/`** — FastAPI, built from `templates/web/backend`. Serves
  `GET /api/insights` on port 8000, requiring `insights:read_sensitive`.
- **`frontend/`** — the page, built on the shared UI kit.

The two halves meet at one contract: `{"rows": [{"id", "metric", "value",
"period"}]}`.

Start with [`backend/README.md`](backend/README.md) — it explains what this
example demonstrates, what the restricted tier changes underneath it, and the
one SDK gap a team on this tier needs to know about.

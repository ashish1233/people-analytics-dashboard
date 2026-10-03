# People Analytics dashboard — backend

An example tenant app. It exists to show what consuming the platform costs a
team, and it is deliberately trivial: one endpoint, one dataset, one scope. If
it were impressive it would be demonstrating the wrong thing.

- **Tenant:** `people-analytics`
- **Tier:** restricted (ADR-2) — assigned by the platform team, not chosen here
- **Endpoint:** `GET /api/insights` → `{"rows": [{"id", "metric", "value", "period"}]}`
- **Required scope:** `insights:read_sensitive`

The frontend lives in `../frontend` and is maintained separately.

The warehouse returns one `compensation` row per employee. The endpoint returns
an average base salary per department and year, which is both what the page
needs and the smaller disclosure — individual salaries never leave the process,
so a browser cache, a screenshot or the frontend's own error reporting cannot
carry one.

## What it demonstrates

**That the whole platform integration is one call.** `install(app, config)` in
`src/dashboard/main.py` brings authentication, tenant-tagged telemetry, scoped
warehouse access, audit, error translation, and the health contract. Everything
this team wrote is the dataset name, the scope, and the response shape — which
is the number ADR-1 is designed around, because platform-team effort per tenant
is the variable that breaks as teams are added, not request volume.

**What the restricted tier actually changes.** None of it appears in this app's
code, which is the point:

| Behaviour | Where it comes from |
| --- | --- |
| App refuses to start if any route lacks `@scoped(...)` | SDK startup check — delete the decorator on `/api/insights` and the app will not boot |
| An access that cannot be audited is refused with 503, not served | `AuditWriter`, fail-closed on this tier |
| Column- and row-level restrictions on `compensation` | the tenant's warehouse role grants, not this code |
| Operator access to these rows requires break-glass approved by *this team's* data owner | ADR-4 |

**That the two scope controls are not redundant.** `@scoped(READ_SENSITIVE)`
declares; `require_scope(principal, READ_SENSITIVE)` checks. The SDK does not
derive one from the other — see "known gap" below.

**That the refusal is the tested behaviour.** `tests/test_scope_enforcement.py`
proves a caller holding `insights:read` gets a 403, that the successful path
still works (so the refusal is not passing because the endpoint is broken), that
the access is recorded against the person who made it, and that a *refused*
request records nothing — because the scope check runs before the fetch, and the
fetch is what audits.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

# Needs the platform stubs on 8081/8082/8083.
set -a && source .env && set +a
uvicorn dashboard.main:app --port 8000

curl localhost:8000/health
# {"status":"ok","tenant_id":"people-analytics","tier":"restricted",...}

curl -i localhost:8000/api/insights
# HTTP/1.1 401 Unauthorized  {"detail":"Missing bearer token."}

# A user who can read ordinary reporting data, but not this:
TOKEN=$(curl -s localhost:8081/token/user -H 'content-type: application/json' \
  -d '{"tenant_id":"people-analytics","subject":"alice@corp","scopes":["insights:read"]}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -s -H "Authorization: Bearer $TOKEN" localhost:8000/api/insights
# 403 {"detail":"user:alice@corp lacks required scope 'insights:read_sensitive'."}

# The same person with the right scope:
#   {"rows":[{"id":"Engineering:2026","metric":"avg_base_salary",
#             "value":115000.0,"period":"2026"}, ...]}

# And a valid token issued for another tenant:
# 401 {"detail":"Token was issued for tenant 'finance' but this app serves
#      'people-analytics'."}
```

`pytest` needs nothing running — the suite starts its own fake warehouse and
audit sink on an ephemeral port.

## Availability, stated plainly

This app is **less available than a standard-tier app, by design**. If the audit
sink is unreachable, `/api/insights` returns 503 rather than serving a row. An
unrecorded read of compensation data is worse than an outage: the outage is
visible, bounded and fixable, and the unrecorded read is none of those.

This is the sentence People Analytics should have read during onboarding rather
than discovered during their first audit-sink incident (ADR-2).

## Why this app still calls `require_scope`

The SDK enforces the declared scope in middleware, so `@scoped(READ_SENSITIVE)`
is sufficient on its own — a caller without that scope never reaches the route
body.

This app calls `require_scope` anyway. Not because the middleware is untrusted,
but because the endpoint should be readable on its own terms: someone reviewing
this file during an incident should be able to see what it requires without
first going to read the SDK's middleware. The redundancy costs one line and the
test suite covers both paths.

Both of these were gaps when this app was first written — the middleware checked
only that a route *declared* a scope at startup, never that the caller held it,
and a restricted-tier app could not start at all because FastAPI's own
`/docs/oauth2-redirect` route tripped the declaration check. Both were fixed in
the SDK rather than worked around here.

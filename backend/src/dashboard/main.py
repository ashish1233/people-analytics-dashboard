"""People Analytics dashboard — backend.

Built from `templates/web/backend` with three changes: the dataset, the scope,
and the response shape. That is the point of the example — it exists to show
what consuming the platform costs a team, not to be impressive.

This tenant is on the **restricted tier** (ADR-2), which is not something this
file asserts; it arrives as `INSIGHTS_TIER` from the platform configuration. The
tier changes three things underneath this code, none of which appear in it:

- The app refuses to start if any route lacks a `@scoped(...)` declaration.
- Audit is fail-closed: an access that cannot be recorded does not happen, and
  the request returns 503 rather than serving the row.
- Warehouse restrictions are enforced in the role's own grants, so a mistake
  here is contained by the database rather than by this file being correct.

Compensation data is the reason that tier exists. For most datasets, finding a
bad query the next morning is an acceptable outcome; for a confidential figure, the
disclosure has already happened and cannot be walked back.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import FastAPI
from insights_platform import (
    READ_SENSITIVE,
    Principal,
    Tier,
    current_principal,
    get_logger,
    install,
    load_config,
    require_scope,
    scoped,
)
from insights_platform.middleware import Depends

DATASET = "compensation"

config = load_config()
log = get_logger("dashboard")

app = FastAPI(title="People Analytics dashboard", version="0.1.0")

platform = install(app, config)

if config.tier is not Tier.RESTRICTED:
    # Observed, not enforced. Tier is assigned by the platform team and this app
    # does not get to assert its own (ADR-2) — but running the restricted tenant
    # at standard tier silently drops the fail-closed audit path, and silent is
    # the one thing that posture cannot be.
    log.warning(
        "Running below the assigned tier.",
        expected_tier=Tier.RESTRICTED.value,
        actual_tier=config.tier.value,
    )


def to_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn compensation rows into the `{id, metric, value, period}` contract.

    The warehouse returns one row per employee. The dashboard shows an average
    base salary per department and year, which is both what the page needs and
    the smaller disclosure: individual salaries never leave this process, so a
    browser cache, a screenshot or the frontend's own error reporting cannot
    carry one. ADR-4 enforces that for telemetry; here it is a choice, and the
    cheap version of it is simply not sending what nobody needs.
    """
    buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        department = str(row.get("department", "unknown"))
        period = str(row.get("effective_year", "unknown"))
        try:
            buckets[(department, period)].append(float(row["base_salary"]))
        except (KeyError, TypeError, ValueError):
            # A row the dashboard cannot read is skipped, not fatal, and not
            # logged with its contents.
            continue

    return [
        {
            "id": f"{department}:{period}",
            "metric": "avg_base_salary",
            "value": round(sum(salaries) / len(salaries), 2),
            "period": period,
        }
        for (department, period), salaries in sorted(buckets.items())
    ]


@app.get("/api/insights")
@scoped(READ_SENSITIVE)
async def read_insights(
    principal: Principal = Depends(current_principal),
) -> dict[str, Any]:
    """Compensation metrics for the authenticated caller.

    Requires `insights:read_sensitive`. The decorator and the call below are
    both needed and are not the same control:

    - `@scoped(READ_SENSITIVE)` is a declaration checked once at startup. On
      this tier the app will not boot if a route is missing one (ADR-2).
    - `require_scope(...)` repeats it in the body. The middleware already
      enforces the declared scope, so this is belt-and-braces: it keeps the
      requirement visible in the file someone opens during an incident, without
      them first having to go and read the SDK.

    The check runs before the fetch. The data client records the audit event
    *before* performing the read — that ordering is what makes fail-closed audit
    meaningful — so refusing afterwards would leave a record of an access that
    never happened in the trail ADR-4's compliance reader relies on.
    """
    require_scope(principal, READ_SENSITIVE)

    rows = await platform.warehouse.fetch(principal, DATASET)
    metrics = to_metrics(rows)

    # Counts, never rows. `log.info(rows=rows)` raises, and that refusal is
    # aimed at exactly this line (ADR-4).
    log.info(
        "Served insights.",
        dataset=DATASET,
        row_count=len(rows),
        metric_count=len(metrics),
    )

    return {"rows": metrics}

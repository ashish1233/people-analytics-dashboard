#!/usr/bin/env python3
"""ADR-3 CI check: this app conforms to the platform health contract.

ADR-3 puts health-contract conformance in CI rather than at runtime, because the
failure is cheap to detect before merge and expensive to discover later: ADR-4's
operator view across every tenant app works *only* if all of them answer the
same shape. One app that returns `{"ok": true}` is one blind spot in the view
two or three engineers use to run twenty-five applications.

This runs offline. It imports the app, starts it through the test client — which
also exercises the restricted-tier startup check — and asserts the contract.

Usage:  check_health_contract.py [module:attribute]   (default: app.main:app)
"""

from __future__ import annotations

import os
import sys
from importlib import import_module

# The health contract, as `insights_platform.telemetry.health_payload` defines
# it. Extra keys are fine — the SDK itself adds `audit_buffered` — but these
# four must be present and correct.
REQUIRED_KEYS = {"status", "tenant_id", "tier", "sdk_version"}

# Importing the app calls `load_config()`, which fails fast on missing
# configuration. Supply placeholders so this check tests the health contract
# rather than the developer's shell. These URLs are never dialled: nothing on
# the /health path makes a network call.
#
# INSIGHTS_TIER is deliberately *not* defaulted here. A restricted-tier app
# should run this check at its real tier so the startup scope check below is
# actually exercised — set it in the hook definition, as the People Analytics
# dashboard does.
PLACEHOLDER_ENV = {
    "INSIGHTS_TENANT_ID": "ci-health-contract-check",
    "INSIGHTS_IDP_URL": "http://idp.invalid",
    "INSIGHTS_WAREHOUSE_URL": "http://warehouse.invalid",
    "INSIGHTS_AUDIT_URL": "http://audit.invalid",
}


def fail(message: str) -> None:
    print(f"health-contract: FAIL — {message}", file=sys.stderr)
    raise SystemExit(1)


def main(target: str) -> None:
    for key, value in PLACEHOLDER_ENV.items():
        os.environ.setdefault(key, value)

    module_name, _, attribute = target.partition(":")
    try:
        module = import_module(module_name)
    except Exception as exc:  # noqa: BLE001 — any import failure is a failure
        fail(f"could not import {module_name!r}: {type(exc).__name__}: {exc}")
    app = getattr(module, attribute or "app", None)
    if app is None:
        fail(f"{module_name!r} has no attribute {attribute or 'app'!r}")

    paths = {getattr(route, "path", None) for route in app.routes}
    if "/health" not in paths:
        fail(
            "no /health route. It is registered for you by "
            "`insights_platform.install()`; if it is missing, install() was not "
            "called or /health was shadowed."
        )

    from fastapi.testclient import TestClient

    # The context manager runs the app's lifespan, which is where the SDK's
    # restricted-tier "every route is scoped" check lives. An app that cannot
    # start fails here rather than in production.
    try:
        with TestClient(app) as client:
            response = client.get("/health")  # deliberately unauthenticated
    except RuntimeError as exc:
        fail(f"the app refused to start: {exc}")

    if response.status_code != 200:
        fail(
            f"/health returned {response.status_code}, expected 200 without "
            "credentials. Operators poll it unauthenticated."
        )

    body = response.json()
    missing = REQUIRED_KEYS - body.keys()
    if missing:
        fail(f"/health is missing required keys: {', '.join(sorted(missing))}")
    if body["status"] != "ok":
        fail(f"/health reported status={body['status']!r}, expected 'ok'")

    print(
        "health-contract: ok — "
        f"tenant={body['tenant_id']} tier={body['tier']} "
        f"sdk={body['sdk_version']}"
    )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "app.main:app")

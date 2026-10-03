"""A fake warehouse and audit sink, in-process.

The platform stubs listen on 8082 and 8083, but a test suite that needs them
running is a test suite that gets skipped. This starts a throwaway HTTP server
on an ephemeral port and points the app at it, so `pytest` works on a laptop
with nothing else running.

The environment has to be set before `dashboard.main` is imported, because the
app loads its configuration at import time and fails fast without it — hence
module-level code rather than a fixture.
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# Audit events the app wrote during a test. The compensation row count is not
# interesting; who was recorded as reading it is.
AUDIT_EVENTS: list[dict] = []

# The column shape of `stubs/warehouse`'s `compensation` dataset: one row per
# employee, including the per-person salary the endpoint must not pass through.
COMPENSATION_ROWS = [
    {
        "employee_id": "EMP-1001",
        "department": "Engineering",
        "level": "L4",
        "base_salary": 100000,
        "bonus_target_pct": 10,
        "currency": "USD",
        "effective_year": 2026,
    },
    {
        "employee_id": "EMP-1002",
        "department": "Engineering",
        "level": "L5",
        "base_salary": 130000,
        "bonus_target_pct": 15,
        "currency": "USD",
        "effective_year": 2026,
    },
    {
        "employee_id": "EMP-1003",
        "department": "Sales",
        "level": "L3",
        "base_salary": 80000,
        "bonus_target_pct": 20,
        "currency": "USD",
        "effective_year": 2026,
    },
]


class _FakePlatform(BaseHTTPRequestHandler):
    def _respond(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler's name
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        if self.path == "/events":
            AUDIT_EVENTS.append(body)
            return self._respond(200, {"recorded": True})

        if self.path == "/query":
            # The SDK injects tenant_id; the caller cannot supply it. Echoing it
            # back lets a test assert the scoping actually happened.
            assert body["tenant_id"] == "people-analytics"
            rows = COMPENSATION_ROWS if body.get("dataset") == "compensation" else []
            return self._respond(200, {"rows": rows})

        self._respond(404, {"detail": "not a stubbed path"})

    def log_message(self, *args) -> None:  # keep pytest output readable
        pass


_server = HTTPServer(("127.0.0.1", 0), _FakePlatform)
_port = _server.server_port
threading.Thread(target=_server.serve_forever, daemon=True).start()

_base = f"http://127.0.0.1:{_port}"
os.environ["INSIGHTS_TENANT_ID"] = "people-analytics"
os.environ["INSIGHTS_TIER"] = "restricted"
os.environ["INSIGHTS_IDP_URL"] = _base
os.environ["INSIGHTS_WAREHOUSE_URL"] = _base
os.environ["INSIGHTS_AUDIT_URL"] = _base

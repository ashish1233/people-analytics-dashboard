"""The one thing that matters about this app.

`GET /api/insights` returns compensation figures. The whole reason this tenant
is on the restricted tier is that the disclosure of one of those figures cannot
be walked back (ADR-2) — so the test that earns its place is the refusal, not
the success.

The success case is here too, and it is not padding: a refusal test that passes
because the endpoint is broken proves nothing. One asserts the door is locked,
the other that there is a room behind it.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from insights_platform import PrincipalKind, issue_token

from dashboard.main import app

from .conftest import AUDIT_EVENTS

TENANT = "people-analytics"


def token_with(*scopes: str) -> str:
    return issue_token(
        kind=PrincipalKind.USER,
        subject="alice@corp",
        tenant_id=TENANT,
        scopes=set(scopes),
    )


def test_request_without_the_sensitive_scope_is_refused():
    """A caller who can read ordinary reporting data cannot read compensation.

    403 rather than 401: this caller is authenticated and known, and the
    distinction is what tells an operator whether they are looking at a broken
    login or at someone asking for something they should not have.
    """
    with TestClient(app) as client:
        response = client.get(
            "/api/insights",
            headers={"Authorization": f"Bearer {token_with('insights:read')}"},
        )

    assert response.status_code == 403
    assert "insights:read_sensitive" in response.json()["detail"]


def test_request_with_no_token_is_refused_before_anything_else():
    """ADR-3 gate 1, and a 401 rather than a 500 — the SDK translates its own
    exceptions in the one layer that knows about HTTP."""
    with TestClient(app) as client:
        assert client.get("/api/insights").status_code == 401


def test_request_with_the_sensitive_scope_is_served():
    before = len(AUDIT_EVENTS)

    with TestClient(app) as client:
        response = client.get(
            "/api/insights",
            headers={
                "Authorization": f"Bearer {token_with('insights:read_sensitive')}"
            },
        )

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert rows == [
        {
            "id": "Engineering:2026",
            "metric": "avg_base_salary",
            "value": 115000.0,
            "period": "2026",
        },
        {
            "id": "Sales:2026",
            "metric": "avg_base_salary",
            "value": 80000.0,
            "period": "2026",
        },
    ]

    # Individual salaries and employee identifiers never leave the process.
    body = response.text
    assert "EMP-1001" not in body
    assert "130000" not in body

    # ADR-4: the access was recorded, and recorded against the person who made
    # it. An audit trail that cannot name the reader is not evidence.
    recorded = AUDIT_EVENTS[before:]
    assert any(
        event["principal"] == "user:alice@corp"
        and event["action"] == "warehouse.read"
        and event["resource"] == "compensation"
        and event["tenant_id"] == TENANT
        for event in recorded
    ), recorded


def test_refused_request_leaves_no_audit_record_of_a_read():
    """The scope check runs before the fetch, and the fetch is what audits.

    If the order were reversed, the trail would show a compensation read that
    never happened — and a compliance partner reading it would have no way to
    tell the false entries from the real ones.
    """
    before = len(AUDIT_EVENTS)

    with TestClient(app) as client:
        client.get(
            "/api/insights",
            headers={"Authorization": f"Bearer {token_with('insights:read')}"},
        )

    assert AUDIT_EVENTS[before:] == []

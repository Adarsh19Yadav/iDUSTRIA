"""tests/phase8/test_machine_api.py — Phase 8 Machine API tests.

Tests:
- POST /api/v1/machines — create machine
- GET  /api/v1/machines — list machines
- GET  /api/v1/machines/{id} — retrieve one
- Validation errors
- Duplicate identifier → 409
- Nonexistent machine → 404
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestCreateMachine:
    def test_create_machine_success(self, client: TestClient, valid_machine_payload):
        resp = client.post("/api/v1/machines", json=valid_machine_payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["machine_identifier"] == "MACHINE-001"
        assert body["type"] == "CNC_LATHE"
        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body

    def test_create_machine_without_type(self, client: TestClient):
        resp = client.post(
            "/api/v1/machines",
            json={"machine_identifier": "MACHINE-NO-TYPE"},
        )
        assert resp.status_code == 201
        assert resp.json()["type"] is None

    def test_create_machine_duplicate_identifier(self, client: TestClient, valid_machine_payload):
        client.post("/api/v1/machines", json=valid_machine_payload)
        resp = client.post("/api/v1/machines", json=valid_machine_payload)
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    def test_create_machine_empty_identifier(self, client: TestClient):
        resp = client.post("/api/v1/machines", json={"machine_identifier": ""})
        assert resp.status_code == 422

    def test_create_machine_unsafe_identifier(self, client: TestClient):
        resp = client.post(
            "/api/v1/machines",
            json={"machine_identifier": "../../etc/passwd"},
        )
        assert resp.status_code == 422

    def test_create_machine_identifier_with_spaces(self, client: TestClient):
        resp = client.post(
            "/api/v1/machines",
            json={"machine_identifier": "machine with spaces"},
        )
        assert resp.status_code == 422

    def test_create_machine_identifier_too_long(self, client: TestClient):
        resp = client.post(
            "/api/v1/machines",
            json={"machine_identifier": "A" * 129},
        )
        assert resp.status_code == 422

    def test_create_machine_missing_identifier(self, client: TestClient):
        resp = client.post("/api/v1/machines", json={"type": "CNC"})
        assert resp.status_code == 422

    def test_create_machine_type_too_long(self, client: TestClient):
        resp = client.post(
            "/api/v1/machines",
            json={"machine_identifier": "M-VALID", "type": "X" * 65},
        )
        assert resp.status_code == 422


class TestListMachines:
    def test_list_machines_empty(self, client: TestClient):
        resp = client.get("/api/v1/machines")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_machines_returns_all(self, client: TestClient):
        for i in range(3):
            client.post(
                "/api/v1/machines",
                json={"machine_identifier": f"LIST-{i}"},
            )
        resp = client.get("/api/v1/machines")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_list_machines_pagination(self, client: TestClient):
        for i in range(5):
            client.post(
                "/api/v1/machines",
                json={"machine_identifier": f"PAGE-{i}"},
            )
        resp = client.get("/api/v1/machines?skip=2&limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_machines_invalid_skip(self, client: TestClient):
        resp = client.get("/api/v1/machines?skip=-1")
        assert resp.status_code == 422

    def test_list_machines_limit_exceeded(self, client: TestClient):
        resp = client.get("/api/v1/machines?limit=501")
        assert resp.status_code == 422


class TestGetMachine:
    def test_get_machine_success(self, client: TestClient, valid_machine_payload):
        created = client.post("/api/v1/machines", json=valid_machine_payload).json()
        resp = client.get(f"/api/v1/machines/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["machine_identifier"] == "MACHINE-001"

    def test_get_machine_not_found(self, client: TestClient):
        resp = client.get("/api/v1/machines/99999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_machine_response_schema(self, client: TestClient, valid_machine_payload):
        created = client.post("/api/v1/machines", json=valid_machine_payload).json()
        resp = client.get(f"/api/v1/machines/{created['id']}")
        body = resp.json()
        required_fields = {"id", "machine_identifier", "type", "created_at", "updated_at"}
        assert required_fields.issubset(body.keys())

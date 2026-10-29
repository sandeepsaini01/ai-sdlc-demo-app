from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from invoice_app.api.app import create_app

PASSWORD = "ChangeMe123!"


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"]
    return {"Authorization": f"Bearer {body['token']}"}


def create_and_submit(client: TestClient, headers: dict[str, str], amount: str, customer: str) -> str:
    created = client.post(
        "/api/invoices",
        json={"customerName": customer, "amount": amount},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    invoice_id = created.json()["id"]
    submitted = client.post(f"/api/invoices/{invoice_id}/submit", headers=headers)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "PendingApproval"
    return invoice_id


def test_sign_in_rejects_a_wrong_password(client: TestClient):
    response = client.post(
        "/api/auth/login",
        json={"username": "demo.manager", "password": "nope"},
    )
    assert response.status_code == 401
    assert "error" in response.json()


def test_invoice_routes_require_a_session(client: TestClient):
    response = client.get("/api/invoices")
    assert response.status_code == 401
    assert response.json()["error"]


def test_manager_over_limit_returns_a_reason_and_the_invoice_is_unchanged(client: TestClient):
    headers = login(client, "demo.manager")
    invoice_id = create_and_submit(client, headers, "50000.01", "Over Limit District")
    before = client.get(f"/api/invoices/{invoice_id}", headers=headers).json()

    denied = client.post(
        f"/api/approvals/{invoice_id}/approve",
        headers=headers,
        json={"role": "Director"},
    )

    assert denied.status_code == 400
    assert "50,000.00" in denied.json()["error"]
    assert "left unchanged" in denied.json()["error"]
    after = client.get(f"/api/invoices/{invoice_id}", headers=headers).json()
    assert after == before
    assert after["status"] == "PendingApproval"
    assert after["decidedBy"] is None
    assert after["approvals"] == []
    assert after["amount"] == "50000.01"


def test_director_approves_a_manager_over_limit_invoice(client: TestClient):
    manager = login(client, "demo.manager")
    invoice_id = create_and_submit(client, manager, "75000.00", "Director Only District")

    denied = client.post(f"/api/approvals/{invoice_id}/approve", headers=manager)
    assert denied.status_code == 400

    director = login(client, "demo.director")
    approved = client.post(f"/api/approvals/{invoice_id}/approve", headers=director)
    assert approved.status_code == 200
    body = approved.json()
    assert body["status"] == "Approved"
    assert body["decidedBy"] == "demo.director"
    assert body["amount"] == "75000.00"


def test_two_directors_are_required_above_500000_and_the_same_user_does_not_count_twice(
    client: TestClient,
):
    director = login(client, "demo.director")
    invoice_id = create_and_submit(client, director, "750000.00", "Capital Program")

    first = client.post(f"/api/approvals/{invoice_id}/approve", headers=director)
    assert first.status_code == 200
    assert first.json()["status"] == "PendingApproval"
    assert [vote["username"] for vote in first.json()["approvals"]] == ["demo.director"]
    assert first.json()["decidedBy"] is None

    again = client.post(f"/api/approvals/{invoice_id}/approve", headers=director)
    assert again.status_code == 400
    assert "same user" in again.json()["error"]
    after_same_user = client.get(f"/api/invoices/{invoice_id}", headers=director).json()
    assert after_same_user["status"] == "PendingApproval"
    assert [vote["username"] for vote in after_same_user["approvals"]] == ["demo.director"]

    manager = login(client, "demo.manager")
    second_wrong_role = client.post(f"/api/approvals/{invoice_id}/approve", headers=manager)
    assert second_wrong_role.status_code == 400
    assert "must be a director" in second_wrong_role.json()["error"]
    still_pending = client.get(f"/api/invoices/{invoice_id}", headers=director).json()
    assert still_pending["approvals"] == after_same_user["approvals"]
    assert still_pending["status"] == "PendingApproval"

    director_two = login(client, "demo.director2")
    finished = client.post(f"/api/approvals/{invoice_id}/approve", headers=director_two)
    assert finished.status_code == 200
    assert finished.json()["status"] == "Approved"
    assert [vote["username"] for vote in finished.json()["approvals"]] == [
        "demo.director",
        "demo.director2",
    ]


def test_blank_rejection_leaves_the_invoice_pending(client: TestClient):
    headers = login(client, "demo.manager")
    before = client.get("/api/invoices/INV-1001", headers=headers).json()

    response = client.post(
        "/api/approvals/INV-1001/reject",
        headers=headers,
        json={"reason": "   "},
    )

    assert response.status_code == 400
    assert client.get("/api/invoices/INV-1001", headers=headers).json() == before


def test_only_an_admin_can_delete(client: TestClient):
    manager = login(client, "demo.manager")
    forbidden = client.delete("/api/invoices/INV-1005", headers=manager)
    assert forbidden.status_code == 403

    admin = login(client, "demo.admin")
    deleted = client.delete("/api/invoices/INV-1005", headers=admin)
    assert deleted.status_code == 204
    assert client.get("/api/invoices/INV-1005", headers=admin).status_code == 404


def test_ui_is_served(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "Invoice Approvals" in response.text

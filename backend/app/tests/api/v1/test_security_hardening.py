import pytest
from backend.app.models.queue import Queue
from backend.app.models.operator import Operator
from backend.app.models.ticket import Ticket
from backend.app.api.v1.endpoints import operators, queues, tickets

def test_operator_username_collision(client, superuser_token_headers):
    # 1. Create operator "op_collision"
    r = client.post(
        f"/api/v1/operators/",
        headers=superuser_token_headers,
        json={"name": "Op1", "username": "op_collision", "password": "password"},
    )
    assert r.status_code == 200

    # 2. Try to update another operator to "op_collision"
    # Create Op2 first
    r = client.post(
        f"/api/v1/operators/",
        headers=superuser_token_headers,
        json={"name": "Op2", "username": "op_unique", "password": "password"},
    )
    op2_id = r.json()["id"]

    # Update Op2 -> op_collision
    r = client.put(
        f"/api/v1/operators/{op2_id}",
        headers=superuser_token_headers,
        json={"username": "op_collision"},
    )
    assert r.status_code == 400
    assert "Username already exists" in r.json()["detail"]

def test_queue_soft_delete_and_ticket_block(client, superuser_token_headers):
    # 1. Create Queue
    r = client.post(
        f"/api/v1/queues/",
        headers=superuser_token_headers,
        json={"name": "SoftDeleteQueue", "prefix": "SD"},
    )
    assert r.status_code == 200
    q_data = r.json()
    q_id = q_data["id"]

    # 2. Delete Queue (Soft Delete)
    r = client.delete(f"/api/v1/queues/{q_id}", headers=superuser_token_headers)
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    # 3. Try to create ticket in inactive queue
    r = client.post(
        f"/api/v1/tickets/",
        json={"queue_id": q_id},
    )
    assert r.status_code == 400
    assert "Queue is inactive" in r.json()["detail"]

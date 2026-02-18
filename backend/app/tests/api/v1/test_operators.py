import pytest
from backend.app.models.operator import Operator
from backend.app.models.queue import Queue
from backend.app.core.security import verify_password

def test_create_operator(client, superuser_token_headers):
    data = {"name": "Test Op", "username": "testop", "password": "password123"}
    response = client.post(
        "/api/v1/operators/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["username"] == data["username"]
    assert "id" in content
    assert "hashed_password" not in content # Security check

def test_create_operator_duplicate(client, superuser_token_headers):
    data = {"name": "Test Op", "username": "dup_user", "password": "password123"}
    client.post("/api/v1/operators/", headers=superuser_token_headers, json=data)
    
    # Try again
    response = client.post("/api/v1/operators/", headers=superuser_token_headers, json=data)
    assert response.status_code == 400
    assert "Username already exists" in response.json()["detail"]

def test_update_operator_queues(client, superuser_token_headers, session):
    # Create Op
    op = Operator(name="Op Queue", username="op_q", hashed_password="pw")
    session.add(op)
    # Create Queue
    q = Queue(name="Q1", prefix="A", is_active=True)
    session.add(q)
    session.commit()
    session.refresh(op)
    session.refresh(q)

    # Update Op with Queue
    data = {"queue_ids": [q.id]}
    response = client.put(
        f"/api/v1/operators/{op.id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["queue_ids"] == [q.id]

def test_operator_login(client, session):
    # Use normal_user created in conftest manually or here
    # We can use the endpoint /api/v1/login/
    # But first we need a user in DB with known password
    from backend.app.core.security import get_password_hash
    pw = "secret"
    op = Operator(name="Login Op", username="login_user", hashed_password=get_password_hash(pw))
    session.add(op)
    session.commit()
    
    login_data = {"username": "login_user", "password": pw}
    r = client.post("/api/v1/login/access-token", data=login_data)
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"

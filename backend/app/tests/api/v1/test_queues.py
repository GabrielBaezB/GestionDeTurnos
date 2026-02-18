import pytest
from backend.app.models.queue import Queue

def test_create_queue(client, superuser_token_headers):
    data = {"name": "Test Queue", "prefix": "T", "is_active": True}
    response = client.post(
        "/api/v1/queues/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["name"] == data["name"]
    assert content["prefix"] == data["prefix"]
    assert "id" in content

def test_read_queues(client, superuser_token_headers, session):
    # Create a couple of queues directly
    q1 = Queue(name="Q1", prefix="A", is_active=True)
    q2 = Queue(name="Q2", prefix="B", is_active=True)
    session.add(q1)
    session.add(q2)
    session.commit()

    response = client.get("/api/v1/queues/", headers=superuser_token_headers)
    assert response.status_code == 200
    content = response.json()
    assert len(content) >= 2

def test_update_queue(client, superuser_token_headers, session):
    q = Queue(name="Old Name", prefix="O", is_active=True)
    session.add(q)
    session.commit()
    session.refresh(q)

    data = {"name": "New Name"}
    response = client.put(
        f"/api/v1/queues/{q.id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["name"] == "New Name"
    assert content["prefix"] == "O" # Unchanged

def test_delete_queue_soft_delete(client, superuser_token_headers, session):
    q = Queue(name="To Delete", prefix="D", is_active=True)
    session.add(q)
    session.commit()
    session.refresh(q)

    response = client.delete(
        f"/api/v1/queues/{q.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["is_active"] is False # Check Soft Delete
    
    # Verify in DB
    db_q = session.get(Queue, q.id)
    assert db_q.is_active is False

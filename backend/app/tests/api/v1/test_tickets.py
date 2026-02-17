
import pytest
from fastapi.testclient import TestClient
from backend.app.models.queue import Queue
from backend.app.models.ticket import Ticket, TicketCreate

def test_create_ticket(client: TestClient, session):
    # Setup: Create a Queue
    queue_name = "Ventas"
    queue_prefix = "V"
    queue = Queue(name=queue_name, prefix=queue_prefix, is_active=True)
    session.add(queue)
    session.commit()
    session.refresh(queue)

    # Act: Create Ticket via API
    # queue_id in json payload must match the created queue's ID
    response = client.post("/api/v1/tickets/", json={"queue_id": queue.id})

    # Assert: Check Response
    assert response.status_code == 200
    data = response.json()
    assert data["number"] == "V-1" # Redis or SQL logic might return 1 not 001 depending on implementation
    assert data["queue_id"] == queue.id 
    assert data["status"] == "waiting"

    # Assert: Check Database
    tickets_in_db = session.query(Ticket).all()
    assert len(tickets_in_db) == 1
    # Check parity with response
    assert tickets_in_db[0].number == data["number"]

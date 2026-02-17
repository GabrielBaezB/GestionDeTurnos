
import pytest
from httpx import AsyncClient
from backend.app.models.queue import Queue
from backend.app.models.ticket import Ticket, TicketCreate

@pytest.mark.asyncio
async def test_create_ticket(client: AsyncClient, session):
    # Setup: Create a Queue
    queue_name = "Ventas"
    queue_prefix = "V"
    queue = Queue(name=queue_name, prefix=queue_prefix, is_active=True)
    session.add(queue)
    session.commit()
    session.refresh(queue)

    # Act: Create Ticket via API
    response = await client.post("/api/v1/tickets/", json={"queue_id": queue.id})

    # Assert: Check Response
    assert response.status_code == 200
    data = response.json()
    assert data["number"] == "V-001"
    assert data["queue_type"] == "Ventas"
    assert data["status"] == "waiting"

    # Assert: Check Database
    tickets_in_db = session.query(Ticket).all()
    assert len(tickets_in_db) == 1
    assert tickets_in_db[0].number == "V-001"

import pytest
from backend.app.models.ticket import TicketStatus

def test_full_ticket_lifecycle(client, superuser_token_headers):
    # 1. Setup: Create Queue
    q_data = {"name": "Integration Q", "prefix": "INT", "is_active": True}
    r = client.post("/api/v1/queues/", headers=superuser_token_headers, json=q_data)
    assert r.status_code == 200
    queue_id = r.json()["id"]

    # 2. Setup: Create Operator
    op_data = {"name": "Int Op", "username": "int_op", "password": "password"}
    r = client.post("/api/v1/operators/", headers=superuser_token_headers, json=op_data)
    assert r.status_code == 200
    operator_id = r.json()["id"]

    # 3. Kiosk: Create Ticket
    # Ticket creation is public (usually), or we can use headers if needed. currently tickets.py says Depends(get_session) but no security on create_ticket?
    # Checking tickets.py: router.post("/", ...) no security dependency on the endpoint itself, just session.
    # So it is public.
    r = client.post("/api/v1/tickets/", json={"queue_id": queue_id})
    assert r.status_code == 200
    ticket = r.json()
    ticket_number = ticket["number"]
    assert ticket["status"] == "waiting"

    # 4. Operator: Call Next
    # We use the POST /call-next endpoint which Clerk uses
    call_data = {
        "operator_id": operator_id,
        "module_id": 1,
        "queue_ids": [queue_id]
    }
    r = client.post("/api/v1/tickets/call-next", headers=superuser_token_headers, json=call_data)
    assert r.status_code == 200
    called_ticket = r.json()
    assert called_ticket["number"] == ticket_number
    assert called_ticket["status"] == "serving"
    assert called_ticket["served_by_operator_id"] == operator_id

    # 5. Operator: Complete Ticket
    ticket_id = called_ticket["id"]
    r = client.post(f"/api/v1/tickets/{ticket_id}/complete", headers=superuser_token_headers)
    assert r.status_code == 200
    completed_ticket = r.json()
    assert completed_ticket["status"] == "completed"

    # 6. Verify: Report Stats
    # Should show 1 completed ticket
    # We need to account that this runs in the same session/db as other tests if not isolated.
    # But conftest.py uses one session per test function usually?
    # conftest.py:
    # @pytest.fixture(name="session") yields session
    # SQLModel.metadata.create_all(engine) ... yield ... drop_all(engine)
    # So YES, it is isolated (DB is dropped after each test).
    
    # Reports Endpoint check
    import datetime
    today = datetime.datetime.now().date().isoformat()
    r = client.get(f"/api/v1/reports/dashboard?start_date={today}&end_date={today}", headers=superuser_token_headers)
    assert r.status_code == 200
    stats = r.json()["daily_stats"]
    assert stats["total_tickets"] == 1
    assert stats["attended_tickets"] == 1

import pytest
from datetime import datetime, timedelta
from backend.app.models.ticket import Ticket, TicketStatus
from backend.app.models.queue import Queue
from backend.app.models.operator import Operator

def test_dashboard_stats(client, superuser_token_headers, session):
    # Setup Data
    q = Queue(name="Q1", prefix="R", is_active=True)
    op = Operator(name="Stats Op", username="stats", hashed_password="pw", is_active=True)
    session.add(q)
    session.add(op)
    session.commit()
    session.refresh(q)
    session.refresh(op)

    # Tickets
    # 1. Waiting
    t1 = Ticket(
        number="R-001", queue_type=q.name, queue_id=q.id, status=TicketStatus.WAITING, 
        created_at=datetime.now()
    )
    # 2. Completed by Op
    t2 = Ticket(
        number="R-002", queue_type=q.name, queue_id=q.id, status=TicketStatus.COMPLETED,
        served_by_operator_id=op.id,
        created_at=datetime.now() - timedelta(minutes=10),
        updated_at=datetime.now()
    )

    session.add(t1)
    session.add(t2)
    session.commit()

    # Act
    today = datetime.now().date().isoformat()
    response = client.get(
        f"/api/v1/reports/dashboard?start_date={today}&end_date={today}",
        headers=superuser_token_headers,
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    
    daily_stats = data["daily_stats"]
    assert daily_stats["total_tickets"] == 2
    assert daily_stats["attended_tickets"] == 1
    assert daily_stats["waiting_tickets"] == 1

    op_stats = data["operator_stats"]
    assert len(op_stats) == 1
    stats_op = op_stats[0]
    assert stats_op["operator_name"] == "Stats Op"
    assert stats_op["tickets_served"] == 1

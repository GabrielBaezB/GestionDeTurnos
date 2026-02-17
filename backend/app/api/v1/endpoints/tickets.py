import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, col
from pydantic import BaseModel
from typing import List, Optional
from backend.app.core import database
from backend.app.core.events import event_manager
from backend.app.models.ticket import Ticket, TicketCreate, TicketUpdate, TicketStatus
from backend.app.models.queue import Queue
from datetime import datetime
from prometheus_client import Gauge

router = APIRouter()

WAITING_TICKETS = Gauge('zeroq_waiting_tickets', 'Number of tickets currently waiting', ['queue'])

class CallNextRequest(BaseModel):
    operator_id: int
    module_id: int
    queue_ids: List[int] = []


# ─── Helper: build monitor snapshot ───
def _monitor_snapshot(session: Session) -> dict:
    serving = session.exec(
        select(Ticket)
        .where(Ticket.status == TicketStatus.SERVING)
        .order_by(Ticket.updated_at.desc())
    ).all()
    waiting = session.exec(
        select(Ticket)
        .where(Ticket.status == TicketStatus.WAITING)
        .order_by(Ticket.created_at)
    ).all()
    
    # Update Prometheus Metric
    # Group by queue name for the label
    counts = {}
    for t in waiting:
        q_name = t.queue_type or "unknown"
        counts[q_name] = counts.get(q_name, 0) + 1
    
    # Clear previous values (optional, but simple approach is to specific set active ones)
    # Ideally we'd keep track of all queues, but for now this sets the current state.
    # Note: Gauges persist. If a queue goes to 0, we must set it to 0.
    # We iterate all known queues to be safe if possible, but looping 'waiting' only gives us active ones.
    # A better way is to query all queues.
    all_queues = session.exec(select(Queue)).all()
    for q in all_queues:
        WAITING_TICKETS.labels(queue=q.name).set(counts.get(q.name, 0))

    # Return limited list for frontend to avoid huge payload
    return {
        "serving": [{"id": t.id, "number": t.number, "queue_type": t.queue_type,
                      "served_by_module_id": t.served_by_module_id,
                      "served_by_operator_id": t.served_by_operator_id} for t in serving],
        "waiting": [{"id": t.id, "number": t.number, "queue_type": t.queue_type} for t in waiting[:20]], # Limit only for JSON response
    }


def _fire_event(session: Session, event_type: str, extra: dict = None):
    """Broadcast SSE event with current monitor state."""
    snapshot = _monitor_snapshot(session)
    data = {**snapshot}
    if extra:
        data["event"] = extra
    event_manager.broadcast(event_type, data)


# ─── SSE Stream Endpoint ───
@router.get("/stream")
async def ticket_stream():
    """Server-Sent Events stream for real-time ticket updates."""
    queue = await event_manager.subscribe()

    async def generate():
        try:
            while True:
                payload = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {payload}\n\n"
        except asyncio.TimeoutError:
            # Send keepalive comment to prevent connection drop
            yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_manager.unsubscribe(queue)

    async def event_generator():
        while True:
            async for chunk in generate():
                yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ─── Create Ticket ───
@router.post("/", response_model=Ticket)
def create_ticket(
    *,
    session: Session = Depends(database.get_session),
    ticket_in: TicketCreate
) -> Ticket:
    """Create a new ticket. Frontend sends queue_id (int)."""
    queue = session.get(Queue, ticket_in.queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")

    prefix = queue.prefix

    prefix = queue.prefix

    # Atomic counter via Redis
    from backend.app.core.redis_utils import get_next_ticket_number
    try:
        ticket_number = get_next_ticket_number(prefix)
    except Exception as e:
        # Fallback to SQL if Redis fails (optional, or just fail)
        print(f"Redis error: {e}, falling back to SQL count")
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = len(session.exec(
            select(Ticket)
            .where(Ticket.queue_id == queue.id)
            .where(Ticket.created_at >= today_start)
        ).all())
        number_seq = today_count + 1
        ticket_number = f"{prefix}-{number_seq:03d}"

    ticket = Ticket(
        number=ticket_number,
        queue_type=queue.name,
        queue_id=queue.id,
        status=TicketStatus.WAITING,
        phone_number=ticket_in.phone_number,
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    _fire_event(session, "ticket_created", {"number": ticket.number, "queue": queue.name})
    return ticket


# ─── Call Next (GET — legacy) ───
@router.get("/next", response_model=Ticket)
def call_next_ticket(
    *,
    session: Session = Depends(database.get_session),
    module_id: int = 1,
    operator_id: Optional[int] = Query(None),
    queue_ids: Optional[List[int]] = Query(None),
) -> Ticket:
    query = select(Ticket).where(Ticket.status == TicketStatus.WAITING).order_by(Ticket.created_at)
    if queue_ids:
        query = query.where(col(Ticket.queue_id).in_(queue_ids))

    ticket = session.exec(query).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="No waiting tickets for your selection")

    ticket.status = TicketStatus.SERVING
    ticket.served_by_module_id = module_id
    ticket.served_by_operator_id = operator_id
    ticket.updated_at = datetime.now()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    _fire_event(session, "ticket_called", {"number": ticket.number, "module_id": module_id})
    return ticket


# ─── Call Next (POST — used by clerk) ───
@router.post("/call-next", response_model=Ticket)
def call_next_ticket_post(
    *,
    session: Session = Depends(database.get_session),
    body: CallNextRequest,
) -> Ticket:
    query = select(Ticket).where(Ticket.status == TicketStatus.WAITING).order_by(Ticket.created_at)
    if body.queue_ids:
        query = query.where(col(Ticket.queue_id).in_(body.queue_ids))

    ticket = session.exec(query).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="No hay tickets en espera para su selección")

    ticket.status = TicketStatus.SERVING
    ticket.served_by_module_id = body.module_id
    ticket.served_by_operator_id = body.operator_id
    ticket.updated_at = datetime.now()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    _fire_event(session, "ticket_called", {"number": ticket.number, "module_id": body.module_id})
    return ticket


# ─── Recall ───
@router.post("/{ticket_id}/recall")
def recall_ticket(
    *,
    session: Session = Depends(database.get_session),
    ticket_id: int,
) -> dict:
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.updated_at = datetime.now()
    session.add(ticket)
    session.commit()

    _fire_event(session, "ticket_recalled", {"number": ticket.number})
    return {"message": f"Ticket {ticket.number} re-llamado"}


# ─── Monitor (REST fallback) ───
@router.get("/monitor")
def get_monitor_data(
    *,
    session: Session = Depends(database.get_session),
) -> dict:
    serving = session.exec(
        select(Ticket)
        .where(Ticket.status == TicketStatus.SERVING)
        .order_by(Ticket.updated_at.desc())
    ).all()
    history = session.exec(
        select(Ticket)
        .where(Ticket.status == TicketStatus.COMPLETED)
        .order_by(Ticket.updated_at.desc())
        .limit(5)
    ).all()
    waiting = session.exec(
        select(Ticket)
        .where(Ticket.status == TicketStatus.WAITING)
        .order_by(Ticket.created_at)
        .limit(10)
    ).all()
    return {"serving": serving, "history": history, "waiting": waiting}


# ─── Complete ───
@router.post("/{ticket_id}/complete", response_model=Ticket)
def complete_ticket(
    *,
    session: Session = Depends(database.get_session),
    ticket_id: int,
) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = TicketStatus.COMPLETED
    ticket.updated_at = datetime.now()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)

    _fire_event(session, "ticket_completed", {"number": ticket.number})
    return ticket


# ─── Active Sessions ───
@router.get("/active-sessions")
def get_active_sessions(
    *,
    session: Session = Depends(database.get_session),
) -> List[dict]:
    serving_tickets = session.exec(
        select(Ticket)
        .where(Ticket.status == TicketStatus.SERVING)
        .order_by(Ticket.updated_at.desc())
    ).all()
    return [
        {
            "ticket_number": ticket.number,
            "module_id": ticket.served_by_module_id,
            "operator_id": ticket.served_by_operator_id,
            "queue_type": ticket.queue_type,
            "ticket_id": ticket.id,
        }
        for ticket in serving_tickets
    ]


# ─── Reset Queue ───
@router.post("/reset-queue")
def reset_queue(
    *,
    session: Session = Depends(database.get_session),
    queue_id: Optional[int] = None,
) -> dict:
    query = select(Ticket).where(Ticket.status == TicketStatus.WAITING)
    if queue_id:
        query = query.where(Ticket.queue_id == queue_id)

    tickets_to_delete = session.exec(query).all()
    count = len(tickets_to_delete)
    for ticket in tickets_to_delete:
        session.delete(ticket)
    session.commit()

    _fire_event(session, "queue_reset", {"count": count})
    return {"message": f"Queue reset. {count} waiting tickets deleted."}

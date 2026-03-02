import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, col, func

from backend.app.core import database
from backend.app.core.events import event_manager
from backend.app.models.ticket import Ticket, TicketCreate, TicketUpdate, TicketStatus
from backend.app.models.queue import Queue
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from prometheus_client import Gauge

router = APIRouter()

WAITING_TICKETS = Gauge('gestiondeturnos_waiting_tickets', 'Number of tickets currently waiting', ['queue'])

class CallNextRequest(BaseModel):
    operator_id: int
    module_id: int
    queue_ids: List[int] = []

# ─── Helper: build monitor snapshot ───
def _monitor_snapshot(session: Session) -> dict:
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    serving = session.exec(
        select(Ticket)
        .where(Ticket.status == TicketStatus.SERVING)
        .where(Ticket.updated_at >= today)
        .order_by(Ticket.updated_at.desc())
    ).all()
    
    # Limit waiting tickets for frontend display to avoid massive payload
    waiting = session.exec(
        select(Ticket)
        .where(Ticket.status == TicketStatus.WAITING)
        .order_by(Ticket.created_at)
        .limit(20)
    ).all()
    
    
    # Update Prometheus Metric efficiently using GROUP BY
    try:
        stats = session.exec(
            select(Ticket.queue_type, func.count(Ticket.id))
            .where(Ticket.status == TicketStatus.WAITING)
            .group_by(Ticket.queue_type)
        ).all()
        
        counts = {name: count for name, count in stats}
        
        # Ensure all queues are updated (set to 0 if no tickets)
        # Wrap in try/except to prevent Prometheus from crashing the app
        all_queues = session.exec(select(Queue)).all()
        for q in all_queues:
            if q.name:
                WAITING_TICKETS.labels(queue=q.name).set(counts.get(q.name, 0))
    except Exception as e:
        print(f"Error updating metrics: {e}")

    return {
        "serving": [{"id": t.id, "number": t.number, "queue_type": t.queue_type,
                      "served_by_module_id": t.served_by_module_id,
                      "served_by_operator_id": t.served_by_operator_id} for t in serving],
        "waiting": [{"id": t.id, "number": t.number, "queue_type": t.queue_type} for t in waiting],
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

    async def event_generator():
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive (every 15s)
                    yield 'data: {"type": "heartbeat"}\n\n'
        except asyncio.CancelledError:
            pass
        finally:
            event_manager.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ─── Wait Time Estimate ───
@router.get("/wait-estimate")
def get_wait_estimate(
    *,
    session: Session = Depends(database.get_session),
    queue_id: Optional[int] = Query(None),
) -> dict:
    """Estimate wait time based on avg service duration of completed tickets today."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Count waiting tickets (optionally filtered by queue)
    wait_query = select(func.count()).where(
        Ticket.status == TicketStatus.WAITING,
        Ticket.created_at >= today,
    )
    if queue_id:
        wait_query = wait_query.where(Ticket.queue_id == queue_id)
    waiting_count = session.exec(wait_query).one()
    
    # Calculate average service duration from completed tickets today
    completed = session.exec(
        select(Ticket)
        .where(Ticket.status == TicketStatus.COMPLETED)
        .where(Ticket.created_at >= today)
    ).all()
    
    if len(completed) >= 3:
        # Need at least 3 data points for a reasonable average
        durations = [(t.updated_at - t.created_at).total_seconds() / 60 for t in completed]
        avg_minutes = sum(durations) / len(durations)
    else:
        # Default: 5 minutes per ticket if not enough data
        avg_minutes = 5.0
    
    estimated_wait = round(avg_minutes * waiting_count)
    
    return {
        "waiting_count": waiting_count,
        "avg_service_minutes": round(avg_minutes, 1),
        "estimated_wait_minutes": estimated_wait,
        "data_points": len(completed),
    }


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
    if not queue.is_active:
        raise HTTPException(status_code=400, detail="Queue is inactive")

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
        # Optimized count
        count_query = select(func.count()).where(Ticket.queue_id == queue.id).where(Ticket.created_at >= today_start)
        today_count = session.exec(count_query).one()
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
    snapshot = _monitor_snapshot(session)
    # Add history (last 5 completed) for REST clients
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    history = session.exec(
        select(Ticket)
        .where(Ticket.status == TicketStatus.COMPLETED)
        .where(Ticket.updated_at >= today)
        .order_by(Ticket.updated_at.desc())
        .limit(5)
    ).all()
    snapshot["history"] = [{"id": t.id, "number": t.number, "queue_type": t.queue_type} for t in history]
    return snapshot


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
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    serving_tickets = session.exec(
        select(Ticket)
        .where(Ticket.status == TicketStatus.SERVING)
        .where(Ticket.updated_at >= today)
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

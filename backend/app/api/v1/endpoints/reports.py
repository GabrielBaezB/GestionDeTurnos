from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func, col
from datetime import datetime, date, timedelta
from typing import List

from backend.app.core.database import get_session
from backend.app.models.ticket import Ticket, TicketStatus
from backend.app.models.operator import Operator
from backend.app.schemas.report import DashboardData, DailyStats, WaitTimePoint, OperatorStats

router = APIRouter()

@router.get("/dashboard", response_model=DashboardData)
def get_dashboard_data(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    session: Session = Depends(get_session)
):
    """
    Get aggregated dashboard data.
    If no dates provided, defaults to today.
    """
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = date.today()

    # Convert to datetime for filtering
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    # ─── 1. Daily Stats ───
    # Total tickets created in range
    total_tickets = session.exec(
        select(func.count(Ticket.id))
        .where(Ticket.created_at >= start_dt)
        .where(Ticket.created_at <= end_dt)
    ).one()
    
    # Attended tickets (status = serving or completed)
    attended_tickets = session.exec(
        select(func.count(Ticket.id))
        .where(Ticket.created_at >= start_dt)
        .where(Ticket.created_at <= end_dt)
        .where(col(Ticket.status).in_([TicketStatus.SERVING, TicketStatus.COMPLETED]))
    ).one()
    
    # Waiting tickets (status = waiting)
    waiting_tickets = session.exec(
        select(func.count(Ticket.id))
        .where(Ticket.created_at >= start_dt)
        .where(Ticket.created_at <= end_dt)
        .where(Ticket.status == TicketStatus.WAITING)
    ).one()

    # Avg Wait Time (difference between updated_at and created_at for tickets that left waiting status)
    # Note: Logic assumes served/completed tickets have valid updated_at reflecting call time.
    # Ideally we'd store 'called_at' separately, but updated_at is a proxy for now if status changed.
    # SQLite doesn't support complex interval math easily in standard SQLModel without raw SQL or specifics.
    # We will do a python-side calc for simplicity and DB compatibility or use a raw query if performance needs.
    # Let's fetch relevant tickets and calc in python for now (safe for SQLite/Postgres hybrid without complex dialect code).
    
    done_tickets = session.exec(
        select(Ticket)
        .where(Ticket.created_at >= start_dt)
        .where(Ticket.created_at <= end_dt)
        .where(col(Ticket.status).in_([TicketStatus.SERVING, TicketStatus.COMPLETED]))
    ).all()
    
    total_wait_seconds = 0
    for t in done_tickets:
        wait = (t.updated_at - t.created_at).total_seconds()
        total_wait_seconds += wait
    
    avg_wait = (total_wait_seconds / len(done_tickets)) if done_tickets else 0
    
    daily_stats = DailyStats(
        total_tickets=total_tickets,
        attended_tickets=attended_tickets,
        waiting_tickets=waiting_tickets,
        avg_wait_time_seconds=round(avg_wait, 2)
    )

    # ─── 2. Wait Times by Hour ───
    # Group tickets by hour of creation
    wait_times: List[WaitTimePoint] = []
    # We'll build a dict for hours 08:00 to 18:00 (or dynamic)
    # Just rudimentary bucketing in python
    buckets = {h: [] for h in range(8, 19)} # 8 AM to 6 PM
    
    for t in done_tickets:
        h = t.created_at.hour
        if h in buckets:
            wait = (t.updated_at - t.created_at).total_seconds()
            buckets[h].append(wait)
            
    for h, waits in buckets.items():
        avg = sum(waits) / len(waits) if waits else 0
        wait_times.append(WaitTimePoint(
            hour=f"{h:02d}:00",
            avg_uait_time=round(avg, 2),
            ticket_count=len(waits)
        ))
    
    # ─── 3. Operator Stats ───
    # We need to know who served what.
    # Query operators
    all_operators = session.exec(select(Operator)).all()
    op_stats: List[OperatorStats] = []
    
    for op in all_operators:
        # Count tickets served by this op in range
        op_tickets = [t for t in done_tickets if t.served_by_operator_id == op.id]
        count = len(op_tickets)
        # Service time could be tracked if we had 'completed_at', for now we ignore service duration 
        # as we only track wait time in Ticket model (created -> served).
        # We'll return 0 for service time or implement if we add that field later.
        
        op_stats.append(OperatorStats(
            operator_id=op.id,
            operator_name=op.name,
            tickets_served=count,
            avg_service_time_seconds=0 # Placeholder
        ))

    return DashboardData(
        daily_stats=daily_stats,
        wait_times=wait_times,
        operator_stats=op_stats
    )

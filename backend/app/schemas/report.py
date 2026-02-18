from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DailyStats(BaseModel):
    total_tickets: int
    attended_tickets: int
    waiting_tickets: int
    avg_wait_time_seconds: float

class WaitTimePoint(BaseModel):
    hour: str # "09:00", "10:00"
    avg_uait_time: float
    ticket_count: int

class OperatorStats(BaseModel):
    operator_id: int
    operator_name: str
    tickets_served: int
    avg_service_time_seconds: float

class DashboardData(BaseModel):
    daily_stats: DailyStats
    wait_times: List[WaitTimePoint]
    operator_stats: List[OperatorStats]

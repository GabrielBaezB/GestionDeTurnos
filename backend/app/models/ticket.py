from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import enum

class TicketStatus(str, enum.Enum):
    WAITING = "waiting"
    SERVING = "serving"
    COMPLETED = "completed"

class TicketBase(SQLModel):
    number: str
    queue_type: str       # display name, e.g. "General"
    queue_id: Optional[int] = Field(default=None, foreign_key="queue.id")
    status: TicketStatus = Field(default=TicketStatus.WAITING)
    phone_number: Optional[str] = None
    served_by_module_id: Optional[int] = None
    served_by_operator_id: Optional[int] = Field(default=None, foreign_key="operator.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Ticket(TicketBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class TicketCreate(SQLModel):
    queue_id: int                          # now FK-based
    phone_number: Optional[str] = None

class TicketUpdate(SQLModel):
    status: Optional[TicketStatus] = None

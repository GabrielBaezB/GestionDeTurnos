from sqlmodel import SQLModel, Field
from typing import Optional

class QueueBase(SQLModel):
    name: str = Field(index=True)     # e.g., "Trámites Generales"
    prefix: str = Field(max_length=5) # e.g., "G", "F"
    is_active: bool = Field(default=True)

class Queue(QueueBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class QueueCreate(QueueBase):
    pass

class QueueUpdate(SQLModel):
    name: Optional[str] = None
    prefix: Optional[str] = None
    is_active: Optional[bool] = None

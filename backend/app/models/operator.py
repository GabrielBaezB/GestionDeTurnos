from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime

class OperatorBase(SQLModel):
    name: str = Field(index=True)
    username: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)
    current_module_id: Optional[int] = Field(default=None, foreign_key="module.id")

class Operator(OperatorBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class OperatorRead(OperatorBase):
    """Response model — excludes hashed_password."""
    id: int
    created_at: datetime
    updated_at: datetime

class OperatorCreate(OperatorBase):
    password: str
    queue_ids: List[int] = []

class OperatorUpdate(SQLModel):
    name: Optional[str] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None
    current_module_id: Optional[int] = None
    password: Optional[str] = None
    queue_ids: Optional[List[int]] = None

from sqlmodel import SQLModel, Field
from typing import Optional

class OperatorQueue(SQLModel, table=True):
    """Many-to-many: which queues (trámites) an operator can serve."""
    id: Optional[int] = Field(default=None, primary_key=True)
    operator_id: int = Field(foreign_key="operator.id")
    queue_id: int = Field(foreign_key="queue.id")

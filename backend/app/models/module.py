from sqlmodel import SQLModel, Field
from typing import Optional

class ModuleBase(SQLModel):
    name: str = Field(index=True)
    is_active: bool = Field(default=True)

class Module(ModuleBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class ModuleCreate(ModuleBase):
    pass

class ModuleUpdate(SQLModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

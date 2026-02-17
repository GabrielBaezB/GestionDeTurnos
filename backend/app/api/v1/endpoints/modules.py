from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from backend.app.core import database
from backend.app.models.module import Module, ModuleCreate, ModuleUpdate

router = APIRouter()

@router.get("/", response_model=List[Module])
def read_modules(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(database.get_session)
) -> List[Module]:
    modules = session.exec(select(Module).offset(skip).limit(limit)).all()
    return modules

@router.post("/", response_model=Module)
def create_module(
    *,
    session: Session = Depends(database.get_session),
    module_in: ModuleCreate
) -> Module:
    module = Module.from_orm(module_in)
    session.add(module)
    session.commit()
    session.refresh(module)
    return module

@router.put("/{module_id}", response_model=Module)
def update_module(
    *,
    session: Session = Depends(database.get_session),
    module_id: int,
    module_in: ModuleUpdate
) -> Module:
    module = session.get(Module, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    module_data = module_in.dict(exclude_unset=True)
    for key, value in module_data.items():
        setattr(module, key, value)
        
    session.add(module)
    session.commit()
    session.refresh(module)
    return module

@router.delete("/{module_id}", response_model=Module)
def delete_module(
    *,
    session: Session = Depends(database.get_session),
    module_id: int
) -> Module:
    module = session.get(Module, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
        
    session.delete(module)
    session.commit()
    return module

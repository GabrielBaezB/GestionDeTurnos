from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional
from backend.app.core import database
from backend.app.core.security import get_password_hash
from backend.app.models.operator import Operator, OperatorCreate, OperatorUpdate, OperatorRead
from backend.app.models.operator_queue import OperatorQueue

router = APIRouter()


def _sync_queues(session: Session, operator_id: int, queue_ids: List[int]):
    """Replace all OperatorQueue rows for this operator."""
    old = session.exec(select(OperatorQueue).where(OperatorQueue.operator_id == operator_id)).all()
    for row in old:
        session.delete(row)
    for qid in queue_ids:
        session.add(OperatorQueue(operator_id=operator_id, queue_id=qid))


def _enrich(session: Session, op: Operator) -> dict:
    """Convert Operator to dict with queue_ids included."""
    queue_rows = session.exec(
        select(OperatorQueue).where(OperatorQueue.operator_id == op.id)
    ).all()
    data = OperatorRead.from_orm(op).dict()
    data["queue_ids"] = [r.queue_id for r in queue_rows]
    return data


@router.get("/")
def read_operators(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(database.get_session)
) -> List[dict]:
    operators = session.exec(select(Operator).offset(skip).limit(limit)).all()
    return [_enrich(session, op) for op in operators]


@router.get("/{operator_id}")
def read_operator(
    operator_id: int,
    session: Session = Depends(database.get_session)
) -> dict:
    op = session.get(Operator, operator_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operator not found")
    return _enrich(session, op)


@router.post("/")
def create_operator(
    *,
    session: Session = Depends(database.get_session),
    operator_in: OperatorCreate
) -> dict:
    existing = session.exec(select(Operator).where(Operator.username == operator_in.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    obj_data = operator_in.dict()
    password = obj_data.pop("password")
    queue_ids = obj_data.pop("queue_ids", [])

    operator = Operator(**obj_data)
    operator.hashed_password = get_password_hash(password)

    session.add(operator)
    session.commit()
    session.refresh(operator)

    _sync_queues(session, operator.id, queue_ids)
    session.commit()

    return _enrich(session, operator)


@router.put("/{operator_id}")
def update_operator(
    *,
    session: Session = Depends(database.get_session),
    operator_id: int,
    operator_in: OperatorUpdate
) -> dict:
    operator = session.get(Operator, operator_id)
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    update_data = operator_in.dict(exclude_unset=True)

    # Handle password
    if "password" in update_data:
        password = update_data.pop("password")
        if password:
            operator.hashed_password = get_password_hash(password)

    # Handle queue_ids
    queue_ids = update_data.pop("queue_ids", None)

    existing = session.exec(select(Operator).where(Operator.username == operator_in.username)).first()
    if existing and existing.id != operator_id:
        raise HTTPException(status_code=400, detail="Username already exists")

    session.add(operator)
    session.commit()

    if queue_ids is not None:
        _sync_queues(session, operator.id, queue_ids)
        session.commit()

    session.refresh(operator)
    return _enrich(session, operator)


@router.delete("/{operator_id}")
def delete_operator(
    *,
    session: Session = Depends(database.get_session),
    operator_id: int
) -> dict:
    operator = session.get(Operator, operator_id)
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    # Clean up queue assignments
    old = session.exec(select(OperatorQueue).where(OperatorQueue.operator_id == operator_id)).all()
    for row in old:
        session.delete(row)

    session.delete(operator)
    session.commit()
    return {"ok": True}

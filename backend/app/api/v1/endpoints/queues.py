from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from backend.app.core import database
from backend.app.models.queue import Queue, QueueCreate, QueueUpdate

router = APIRouter()

@router.get("/", response_model=List[Queue])
def read_queues(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(database.get_session)
) -> List[Queue]:
    queues = session.exec(select(Queue).offset(skip).limit(limit)).all()
    return queues

@router.post("/", response_model=Queue)
def create_queue(
    *,
    session: Session = Depends(database.get_session),
    queue_in: QueueCreate
) -> Queue:
    queue = Queue.from_orm(queue_in)
    session.add(queue)
    session.commit()
    session.refresh(queue)
    return queue

@router.put("/{queue_id}", response_model=Queue)
def update_queue(
    *,
    session: Session = Depends(database.get_session),
    queue_id: int,
    queue_in: QueueUpdate
) -> Queue:
    queue = session.get(Queue, queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")
    
    queue_data = queue_in.dict(exclude_unset=True)
    for key, value in queue_data.items():
        setattr(queue, key, value)
        
    session.add(queue)
    session.commit()
    session.refresh(queue)
    return queue

@router.delete("/{queue_id}", response_model=Queue)
def delete_queue(
    *,
    session: Session = Depends(database.get_session),
    queue_id: int
) -> Queue:
    queue = session.get(Queue, queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")
        
    # Soft Delete: just mark as inactive
    # This preserves analytics and Ticket history
    queue.is_active = False
    session.add(queue)
    session.commit()
    session.refresh(queue)
    return queue

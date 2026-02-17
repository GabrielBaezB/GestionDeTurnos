from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from backend.app.api import deps
from backend.app.crud.crud_item import item as crud_item
from backend.app.models.item import Item, ItemCreate, ItemUpdate
from backend.app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[Item])
def read_items(
    db: Session = Depends(deps.get_session),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve items.
    """
    if current_user.is_superuser:
        items = crud_item.get_multi(db, skip=skip, limit=limit)
    else:
        items = crud_item.get_multi_by_owner(
            db=db, owner_id=current_user.id, skip=skip, limit=limit
        )
    return items

@router.post("/", response_model=Item)
def create_item(
    *,
    db: Session = Depends(deps.get_session),
    item_in: ItemCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new item.
    """
    item = crud_item.create_with_owner(db=db, obj_in=item_in, owner_id=current_user.id)
    return item

@router.put("/{id}", response_model=Item)
def update_item(
    *,
    db: Session = Depends(deps.get_session),
    id: int,
    item_in: ItemUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update an item.
    """
    item = crud_item.get(db=db, id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    item = crud_item.update(db=db, db_obj=item, obj_in=item_in)
    return item

@router.get("/{id}", response_model=Item)
def read_item(
    *,
    db: Session = Depends(deps.get_session),
    id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get item by ID.
    """
    item = crud_item.get(db=db, id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return item

@router.delete("/{id}", response_model=Item)
def delete_item(
    *,
    db: Session = Depends(deps.get_session),
    id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Delete an item.
    """
    item = crud_item.get(db=db, id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    item = crud_item.remove(db=db, id=id)
    return item

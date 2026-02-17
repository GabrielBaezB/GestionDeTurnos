from typing import List
from sqlmodel import Session, select
from backend.app.crud.base import CRUDBase
from backend.app.models.item import Item, ItemCreate, ItemUpdate

class CRUDItem(CRUDBase[Item, ItemCreate, ItemUpdate]):
    def create_with_owner(
        self, db: Session, *, obj_in: ItemCreate, owner_id: int
    ) -> Item:
        obj_in_data = obj_in.dict()
        db_obj = Item(**obj_in_data, owner_id=owner_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_multi_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[Item]:
        statement = select(Item).where(Item.owner_id == owner_id).offset(skip).limit(limit)
        return db.exec(statement).all()

item = CRUDItem(Item)

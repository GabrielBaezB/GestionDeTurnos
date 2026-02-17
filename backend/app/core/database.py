from sqlmodel import SQLModel, create_engine, Session
from backend.app.core.config import settings

# Usamos synchronous engine para máxima simplicidad y compatibilidad (MVP)
# echo=True para ver queries en desarrollo
engine = create_engine(settings.DATABASE_URL, echo=True)

def init_db():
    from backend.app.models import user, item
    from backend.app.models import module, queue, ticket, operator, operator_queue
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

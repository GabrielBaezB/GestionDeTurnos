
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import get_session

# Use in-memory SQLite for testing to ensure isolation
TEST_DATABASE_URL = "sqlite:///:memory:"
# check_same_thread=False is needed for SQLite with multiple threads (FastAPI)
# StaticPool ensures the same in-memory DB is used across connections
engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)

@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture(name="superuser_token_headers")
def superuser_token_headers_fixture(client: TestClient, session: Session) -> dict:
    from backend.app.core.security import create_access_token, get_password_hash
    from backend.app.models.operator import Operator

    # Create superuser
    user = Operator(
        name="Super Admin",
        username="admin_test",
        hashed_password=get_password_hash("password"),
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    access_token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture(name="normal_user_token_headers")
def normal_user_token_headers_fixture(client: TestClient, session: Session) -> dict:
    from backend.app.core.security import create_access_token, get_password_hash
    from backend.app.models.operator import Operator

    # Create normal user
    user = Operator(
        name="Normal User",
        username="user_test",
        hashed_password=get_password_hash("password"),
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    access_token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {access_token}"}

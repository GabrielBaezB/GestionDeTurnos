
import pytest_asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlmodel import Session, SQLModel, create_engine
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import get_session

# Use in-memory SQLite for testing to ensure isolation
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest_asyncio.fixture(name="client", loop_scope="function")
async def client_fixture(session: Session) -> AsyncGenerator[AsyncClient, None]:
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    
    # Use ASGITransport for newer httpx versions to avoid warnings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()

from fastapi.testclient import TestClient
from sqlmodel import Session
from backend.app.main import app
from backend.app.api import deps
from backend.app.models.user import User

def test_create_item(client: TestClient, session: Session):
    # Create user for the test
    user = User(email="test@example.com", hashed_password="password", is_active=True)
    session.add(user)
    session.commit()
    session.refresh(user)

    # Override get_current_user to return this user
    app.dependency_overrides[deps.get_current_user] = lambda: user

    response = client.post(
        "/api/v1/items/",
        json={"title": "Test Item", "description": "This is a test item"},
    )
    
    # Clean up override
    del app.dependency_overrides[deps.get_current_user]

    assert response.status_code == 200
    content = response.json()
    assert content["title"] == "Test Item"
    assert content["description"] == "This is a test item"
    assert "id" in content
    assert content["owner_id"] == user.id

def test_read_items(client: TestClient, session: Session):
     # Create user for the test
    user = User(email="test2@example.com", hashed_password="password", is_active=True)
    session.add(user)
    session.commit()
    session.refresh(user)

    # Override get_current_user to return this user
    app.dependency_overrides[deps.get_current_user] = lambda: user

    client.post(
        "/api/v1/items/",
        json={"title": "Item 1", "description": "Desc 1"},
    )
    client.post(
        "/api/v1/items/",
        json={"title": "Item 2", "description": "Desc 2"},
    )
    
    response = client.get("/api/v1/items/")
    
    # Clean up override
    del app.dependency_overrides[deps.get_current_user]

    assert response.status_code == 200
    content = response.json()
    assert len(content) >= 2

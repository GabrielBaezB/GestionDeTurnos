from fastapi.testclient import TestClient
from sqlmodel import Session
from backend.app.core import security
from backend.app.models.user import User

def test_create_item(client: TestClient, session: Session):
    # Create user directly in DB
    user = User(email="test@example.com", hashed_password="password", is_active=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Get token
    access_token = security.create_access_token(user.id)
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = client.post(
        "/api/v1/items/",
        headers=headers,
        json={"title": "Test Item", "description": "This is a test item"},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["title"] == "Test Item"
    assert content["description"] == "This is a test item"
    assert "id" in content
    assert content["owner_id"] == user.id

def test_read_items(client: TestClient, session: Session):
     # Create user directly in DB
    user = User(email="test2@example.com", hashed_password="password", is_active=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Get token
    access_token = security.create_access_token(user.id)
    headers = {"Authorization": f"Bearer {access_token}"}

    client.post(
        "/api/v1/items/",
        headers=headers,
        json={"title": "Item 1", "description": "Desc 1"},
    )
    client.post(
        "/api/v1/items/",
        headers=headers,
        json={"title": "Item 2", "description": "Desc 2"},
    )
    
    response = client.get("/api/v1/items/", headers=headers)
    assert response.status_code == 200
    content = response.json()
    assert len(content) >= 2

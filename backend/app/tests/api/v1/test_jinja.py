from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings

client = TestClient(app)

def test_index_jinja_rendering():
    """
    Verify that the index page standard HTML response contains the project name
    rendered by Jinja2 (Serverside), not just a placeholder.
    """
    response = client.get("/")
    assert response.status_code == 200
    content = response.text
    
    # Check Title
    expected_title = f"<title>{settings.PROJECT_NAME} — Sistema de Gestión de Filas</title>"
    assert expected_title in content
    
    # Check H1 Brand
    expected_brand = f'<h1 class="brand-title">⚡ {settings.PROJECT_NAME}</h1>'
    assert expected_brand in content
    
    # Check Footer
    expected_footer = f"{settings.PROJECT_NAME} v1.0 — Powered by FastAPI + Docker"
    assert expected_footer in content

def test_admin_jinja_rendering():
    response = client.get("/admin")
    assert response.status_code == 200
    content = response.text
    assert f"<title>{settings.PROJECT_NAME} — Panel de Administración</title>" in content
    assert f"Panel de administración {settings.PROJECT_NAME}" in content

def test_kiosk_jinja_rendering():
    response = client.get("/kiosk")
    assert response.status_code == 200
    content = response.text
    assert f"<title>{settings.PROJECT_NAME} — Tótem de Turnos</title>" in content

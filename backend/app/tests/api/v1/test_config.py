from fastapi.testclient import TestClient
from backend.app.core.config import settings

def test_get_config(client: TestClient):
    response = client.get(f"{settings.API_V1_STR}/config/")
    assert response.status_code == 200
    content = response.json()
    assert content["project_name"] == settings.PROJECT_NAME
    assert content["company_name"] == settings.COMPANY_NAME
    assert content["logo_url"] == settings.LOGO_URL
    assert content["theme_color"] == settings.THEME_COLOR
    assert "secret_key" not in content
    assert "database_url" not in content

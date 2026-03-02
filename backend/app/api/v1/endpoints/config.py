from fastapi import APIRouter
from backend.app.core.config import settings
from pydantic import BaseModel

class PublicConfig(BaseModel):
    project_name: str
    company_name: str
    logo_url: str
    theme_color: str
    api_v1_str: str

router = APIRouter()

@router.get("/", response_model=PublicConfig)
def get_config():
    """
    Return public configuration for the frontend.
    """
    return PublicConfig(
        project_name=settings.PROJECT_NAME,
        company_name=settings.COMPANY_NAME,
        logo_url=settings.LOGO_URL,
        theme_color=settings.THEME_COLOR,
        api_v1_str=settings.API_V1_STR
    )

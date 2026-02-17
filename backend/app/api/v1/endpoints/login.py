from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from backend.app.api import deps
from backend.app.core import security
from backend.app.core.config import settings
from backend.app.crud.crud_user import user as crud_user
from backend.app.models.user import User, UserRegister
from backend.app.models.operator import Operator
from backend.app.schemas.token import Token

router = APIRouter()

@router.post("/login/access-token", response_model=Token)
def login_access_token(
    session: Session = Depends(deps.get_session), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    Supports Admin (User) and Operator login.
    """
    # 1. Try finding as Admin (User)
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    role = "admin"
    auth_success = False

    if user:
        if security.verify_password(form_data.password, user.hashed_password):
            auth_success = True
    
    # 2. If not user, try Operator
    if not auth_success:
        operator = session.exec(select(Operator).where(Operator.username == form_data.username)).first()
        if operator:
            if operator.hashed_password and security.verify_password(form_data.password, operator.hashed_password):
                user = operator
                role = "operator"
                auth_success = True
    
    if not auth_success:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # We store role in the token
    token_payload = {
        "sub": str(user.id),
        "role": role,
        "name": getattr(user, "username", getattr(user, "email", "User"))
    }
    
    return {
        "access_token": security.create_access_token(
            token_payload, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
        "role": role,
        "name": token_payload["name"],
        "id": user.id
    }

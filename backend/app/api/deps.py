from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlmodel import Session
from backend.app.core import security
from backend.app.core.config import settings
from backend.app.core.database import get_session
from backend.app.crud.crud_user import user as crud_user
from backend.app.models.user import User
from backend.app.schemas.token import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token")

from typing import Union
from backend.app.models.operator import Operator

def get_current_user(
    session: Session = Depends(get_session), token: str = Depends(oauth2_scheme)
) -> Union[User, Operator]:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    user = None
    if token_data.role == "admin":
        user = crud_user.get(session, id=token_data.sub)
    elif token_data.role == "operator":
        user = session.get(Operator, token_data.sub)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user

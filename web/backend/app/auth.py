from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


def verify_credentials(username: str, password: str) -> bool:
    return (
        username == settings.auth_username
        and password == settings.auth_password
    )


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if creds is None or not creds.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="未登录")
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub or sub != settings.auth_username:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
        return sub
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="无效令牌") from exc

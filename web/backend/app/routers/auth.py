from fastapi import APIRouter, Depends

from app.auth import create_access_token, get_current_user, verify_credentials
from app.config import settings
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    if not verify_credentials(body.username, body.password):
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = create_access_token(body.username)
    return LoginResponse(access_token=token, username=settings.auth_username)


@router.get("/me")
def me(user: str = Depends(get_current_user)):
    return {"username": user}

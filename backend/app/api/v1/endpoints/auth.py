"""
Authentication endpoints - Register, Login, Logout, Me.
"""
from asyncpg import Connection
from fastapi import APIRouter, Depends

from app.database.connection import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import register_user, login_user, get_user_by_id
from app.core.security import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest, conn: Connection = Depends(get_db)):
    """Register a new user account."""
    return await register_user(conn, data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, conn: Connection = Depends(get_db)):
    """Login and receive JWT token."""
    return await login_user(conn, data)


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout (client should discard the token)."""
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_db),
):
    """Get current authenticated user info."""
    user = await get_user_by_id(conn, current_user["user_id"])
    if user:
        return UserResponse(
            user_id=str(user["id"]),
            email=user["email"],
            username=user["username"],
        )
    return UserResponse(
        user_id=current_user["user_id"],
        email=current_user.get("email", ""),
        username="",
    )

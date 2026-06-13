"""
Authentication service layer using raw asyncpg.
"""
import uuid
from typing import Optional
from asyncpg import Connection
from fastapi import HTTPException, status

from app.core.security import verify_password, get_password_hash, create_access_token
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse


async def register_user(conn: Connection, data: RegisterRequest) -> TokenResponse:
    # Check email uniqueness
    existing = await conn.fetchrow(
        "SELECT id FROM users WHERE email = $1", data.email
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check username uniqueness
    existing = await conn.fetchrow(
        "SELECT id FROM users WHERE username = $1", data.username
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user_id = str(uuid.uuid4())
    hashed = get_password_hash(data.password[:72])

    await conn.execute(
        """
        INSERT INTO users (id, email, username, hashed_password)
        VALUES ($1, $2, $3, $4)
        """,
        user_id, data.email, data.username, hashed,
    )

    token = create_access_token({"sub": user_id, "email": data.email, "username": data.username})
    return TokenResponse(
        access_token=token,
        user_id=user_id,
        email=data.email,
        username=data.username,
    )


async def login_user(conn: Connection, data: LoginRequest) -> TokenResponse:
    row = await conn.fetchrow(
        "SELECT id, email, username, hashed_password, is_active FROM users WHERE email = $1",
        data.email,
    )
    if not row or not verify_password(data.password[:72], row["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not row["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token({
        "sub": str(row["id"]),
        "email": row["email"],
        "username": row["username"],
    })
    return TokenResponse(
        access_token=token,
        user_id=str(row["id"]),
        email=row["email"],
        username=row["username"],
    )


async def get_user_by_id(conn: Connection, user_id: str) -> Optional[dict]:
    row = await conn.fetchrow(
        "SELECT id, email, username, is_active FROM users WHERE id = $1",
        user_id,
    )
    if row:
        return dict(row)
    return None

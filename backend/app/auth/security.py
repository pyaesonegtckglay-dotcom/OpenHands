"""
Phase 4 - Production Hardening
Authentication & Security Module
- JWT refresh tokens
- API key management
- Rate limiting
"""
import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

import jwt
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "manusai-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# API Key Storage
api_keys: Dict[str, Dict[str, Any]] = {}

@dataclass
class TokenData:
    user_id: str
    email: str
    username: str
    exp: datetime
    token_type: str = "access"

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60

class RefreshRequest(BaseModel):
    refresh_token: str

class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)
    rate_limit: Optional[int] = Field(100, ge=1, le=10000)

class APIKeyResponse(BaseModel):
    key_id: str
    name: str
    api_key: str
    created_at: datetime
    expires_at: Optional[datetime]
    rate_limit: int

class APIKeyList(BaseModel):
    keys: list
    total: int

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a new JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "token_type": "access",
        "iat": datetime.utcnow()
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a new JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "token_type": "refresh",
        "iat": datetime.utcnow()
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, token_type: str = "access") -> TokenData:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("token_type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}"
            )
        return TokenData(
            user_id=payload["sub"],
            email=payload.get("email", ""),
            username=payload.get("username", ""),
            exp=datetime.fromtimestamp(payload["exp"]),
            token_type=payload.get("token_type", token_type)
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> TokenData:
    """Dependency to get the current authenticated user."""
    return verify_token(credentials.credentials, "access")

def generate_api_key() -> tuple[str, str]:
    """Generate a new API key. Returns (plain_key, hashed_key)."""
    plain_key = f"manusai_{secrets.token_urlsafe(32)}"
    hashed_key = hashlib.sha256(plain_key.encode()).hexdigest()
    return plain_key, hashed_key

def create_api_key(
    user_id: str,
    name: str,
    expires_in_days: Optional[int] = None,
    rate_limit: int = 100
) -> APIKeyResponse:
    """Create a new API key for a user."""
    key_id = f"key_{secrets.token_hex(8)}"
    plain_key, hashed_key = generate_api_key()
    
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    api_keys[hashed_key] = {
        "key_id": key_id,
        "key_hash": hashed_key,
        "user_id": user_id,
        "name": name,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
        "rate_limit": rate_limit
    }
    
    return APIKeyResponse(
        key_id=key_id,
        name=name,
        api_key=plain_key,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        rate_limit=rate_limit
    )

def verify_api_key(plain_key: str) -> Optional[Dict[str, Any]]:
    """Verify an API key and return its data if valid."""
    hashed_key = hashlib.sha256(plain_key.encode()).hexdigest()
    key_data = api_keys.get(hashed_key)
    
    if not key_data:
        return None
    
    if key_data.get("expires_at") and key_data["expires_at"] < datetime.utcnow():
        return None
    
    key_data["last_used"] = datetime.utcnow()
    return key_data

# Router for auth endpoints
router = APIRouter(prefix="/api/v1/auth", tags=["Phase 4 - Auth"])

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """Refresh access token using refresh token."""
    try:
        payload = verify_token(request.refresh_token, "refresh")
        
        new_access_token = create_access_token({
            "sub": payload.user_id,
            "email": payload.email,
            "username": payload.username
        })
        new_refresh_token = create_refresh_token({
            "sub": payload.user_id,
            "email": payload.email,
            "username": payload.username
        })
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_user_api_key(
    request: APIKeyCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Create a new API key for the current user."""
    return create_api_key(
        user_id=current_user.user_id,
        name=request.name,
        expires_in_days=request.expires_in_days,
        rate_limit=request.rate_limit
    )

@router.get("/api-keys", response_model=APIKeyList)
async def list_api_keys(current_user: TokenData = Depends(get_current_user)):
    """List all API keys for the current user."""
    user_keys = [
        {
            "key_id": k["key_id"],
            "name": k["name"],
            "created_at": k["created_at"],
            "expires_at": k["expires_at"],
            "rate_limit": k["rate_limit"],
            "last_used": k.get("last_used")
        }
        for k in api_keys.values()
        if k["user_id"] == current_user.user_id
    ]
    return APIKeyList(keys=user_keys, total=len(user_keys))

@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Revoke (delete) an API key."""
    for hashed_key, key_data in list(api_keys.items()):
        if key_data["key_id"] == key_id and key_data["user_id"] == current_user.user_id:
            del api_keys[hashed_key]
            return {"message": "API key revoked successfully"}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="API key not found"
    )

@router.get("/me")
async def get_user_info(current_user: TokenData = Depends(get_current_user)):
    """Get current user information."""
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "username": current_user.username,
        "token_expires": current_user.exp.isoformat()
    }

__all__ = [
    "router",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "get_current_user",
    "create_api_key",
    "verify_api_key",
    "TokenData",
    "TokenResponse",
    "APIKeyResponse",
    "APIKeyList"
]
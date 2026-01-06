"""Authentication router for login, register, and user management."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr

from api.services.auth import (
    authenticate_user,
    create_user,
    create_access_token,
    decode_access_token,
    get_user_by_email,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request body."""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Registration request body."""
    email: EmailStr
    password: str
    name: str


class UserResponse(BaseModel):
    """User response (no password)."""
    id: str
    email: str
    name: str
    role: str


class AuthResponse(BaseModel):
    """Authentication response with token."""
    token: str
    user: UserResponse


# Dependency to get current user from token
async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[UserResponse]:
    """
    Extract and validate user from Authorization header.

    Usage: Depends(get_current_user)
    """
    if not authorization:
        return None

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]
    token_data = decode_access_token(token)

    if not token_data or not token_data.email:
        return None

    user = get_user_by_email(token_data.email)
    if not user:
        return None

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role
    )


async def require_auth(user: Optional[UserResponse] = Depends(get_current_user)) -> UserResponse:
    """Dependency that requires authentication."""
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token.

    Returns token and user info on success.
    Raises 401 on invalid credentials.
    """
    user = authenticate_user(request.email, request.password)

    if not user:
        logger.warning(f"Failed login attempt for: {request.email}")
        raise HTTPException(
            status_code=401,
            detail="Thông tin đăng nhập không chính xác"
        )

    # Create access token
    token = create_access_token(
        data={"sub": user.email, "name": user.name}
    )

    logger.info(f"User logged in: {user.email}")

    return AuthResponse(
        token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role
        )
    )


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """
    Register a new user.

    Returns token and user info on success.
    Raises 400 if email already exists.
    """
    # Check if user exists
    existing = get_user_by_email(request.email)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email đã được đăng ký"
        )

    # Validate password strength
    if len(request.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Mật khẩu quá ngắn. Vui lòng nhập ít nhất 6 ký tự."
        )

    # Create user
    user = create_user(
        email=request.email,
        password=request.password,
        name=request.name
    )

    # Create access token
    token = create_access_token(
        data={"sub": user.email, "name": user.name}
    )

    logger.info(f"New user registered: {user.email}")

    return AuthResponse(
        token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: UserResponse = Depends(require_auth)):
    """
    Get current authenticated user info.

    Requires valid JWT token in Authorization header.
    """
    return user


@router.post("/logout")
async def logout():
    """
    Logout endpoint.

    JWT tokens are stateless, so this is mainly for client-side cleanup.
    Could be extended to implement token blacklisting.
    """
    return {"message": "Logged out successfully"}

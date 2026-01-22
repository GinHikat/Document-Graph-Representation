"""Authentication utilities for JWT token management."""
import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    import warnings
    warnings.warn("JWT_SECRET not set - using insecure default for development only!")
    SECRET_KEY = "dev-secret-key-DO-NOT-USE-IN-PRODUCTION"
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory user store (replace with database in production)
users_db: dict = {}


class UserInDB(BaseModel):
    """User model stored in database."""
    id: str
    email: str
    name: str
    hashed_password: str
    role: str = "user"
    created_at: str


class TokenData(BaseModel):
    """Token payload data."""
    email: Optional[str] = None
    name: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')[:72]
    return pwd_context.hash(password_bytes)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenData if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        name: str = payload.get("name")

        if email is None:
            return None

        return TokenData(email=email, name=name)

    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


def get_user_by_email(email: str) -> Optional[UserInDB]:
    """Get user from database by email."""
    if email in users_db:
        return UserInDB(**users_db[email])
    return None


def create_user(email: str, password: str, name: str, role: str = "user") -> UserInDB:
    """
    Create a new user.

    Args:
        email: User email
        password: Plain text password (will be hashed)
        name: User display name
        role: User role (default: user)

    Returns:
        Created UserInDB object
    """
    user_id = str(uuid.uuid4())
    hashed = hash_password(password)

    user_data = {
        "id": user_id,
        "email": email,
        "name": name,
        "hashed_password": hashed,
        "role": role,
        "created_at": datetime.utcnow().isoformat()
    }

    users_db[email] = user_data
    logger.info(f"Created user: {email}")

    return UserInDB(**user_data)


def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
    """
    Authenticate a user by email and password.

    Args:
        email: User email
        password: Plain text password

    Returns:
        UserInDB if authenticated, None if failed
    """
    # Demo mode: accept any email with password "demo"
    if password == "demo":
        # Create temporary demo user on the fly
        user_id = str(uuid.uuid4())
        name = email.split("@")[0].title()
        return UserInDB(
            id=user_id,
            email=email,
            name=name,
            hashed_password="",
            role="annotator",
            created_at=datetime.utcnow().isoformat()
        )

    user = get_user_by_email(email)

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


# Create a default demo user for testing
def init_demo_user():
    """Initialize a demo user for testing."""
    try:
        if "demo@example.com" not in users_db:
            create_user(
                email="demo@example.com",
                password="demo123",
                name="Demo User",
                role="annotator"
            )
            logger.info("Demo user created: demo@example.com / demo123")
    except Exception as e:
        logger.warning(f"Failed to create demo user: {e}")
        logger.info("Demo mode still available - use any email with password 'demo'")


# Initialize demo user on module load
try:
    init_demo_user()
except Exception as e:
    logger.error(f"Error during demo user initialization: {e}")

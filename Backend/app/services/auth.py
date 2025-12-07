"""
Authentication service with JWT tokens and password hashing
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging
import time

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import TokenData

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        email: str = payload.get("email")
        
        if user_id is None:
            return None
            
        return TokenData(user_id=user_id, email=email)
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        return None


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email.lower()).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username.lower()).first()


# In-memory cache for user lookups (reduces DB load during tile requests)
_user_cache = {}
_cache_ttl = 300  # 5 minutes

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID with 5-minute cache to reduce DB load"""
    cache_key = f"user_{user_id}"
    now = time.time()
    
    # Check cache
    if cache_key in _user_cache:
        cached_user, cached_time = _user_cache[cache_key]
        if now - cached_time < _cache_ttl:
            return cached_user
    
    # Query database
    user = db.query(User).filter(User.id == user_id).first()
    
    # Cache result
    if user:
        _user_cache[cache_key] = (user, now)
    
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password"""
    user = get_user_by_email(db, email)
    
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


def create_user(db: Session, email: str, username: str, password: str, full_name: Optional[str] = None) -> User:
    """Create a new user"""
    hashed_password = get_password_hash(password)
    
    user = User(
        email=email.lower(),
        username=username.lower(),
        hashed_password=hashed_password,
        full_name=full_name,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"Created new user: {user.email}")
    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token: Optional[str] = None,  # Allow token in query param
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token.
    Returns None if no token or invalid token (allows anonymous access).
    """
    jwt_token = None
    
    if credentials:
        jwt_token = credentials.credentials
    elif token:
        jwt_token = token
        
    if not jwt_token:
        return None
    
    token_data = decode_token(jwt_token)
    
    if token_data is None or token_data.user_id is None:
        return None
    
    user = get_user_by_id(db, token_data.user_id)
    
    if user is None or not user.is_active:
        return None
    
    return user


async def get_current_user_required(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token.
    Raises 401 if no token or invalid token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    token_data = decode_token(token)
    
    if token_data is None or token_data.user_id is None:
        raise credentials_exception
    
    user = get_user_by_id(db, token_data.user_id)
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_current_superuser(
    current_user: User = Depends(get_current_user_required)
) -> User:
    """Get current superuser, raises 403 if not superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges"
        )
    return current_user

"""
Security module for JWT token handling and RBAC enforcement.
Implements HS256 signed tokens with role-based access control.
"""
import os
from datetime import datetime, timedelta
from typing import Optional, List

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Configuration from environment - never hardcoded
SECRET_KEY = os.getenv('JWT_SECRET', 'dev-secret-key-change-in-production')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/token')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with the provided data.
    
    Args:
        data: Dictionary containing claims (sub, role, etc.)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    payload = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload['exp'] = expire
    payload['iat'] = datetime.utcnow()
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a long-lived refresh token."""
    return create_access_token(data, expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory for role-based access control.
    
    Usage:
        @app.get('/protected', dependencies=[Depends(require_role('admin'))])
        
    Args:
        *allowed_roles: Variable number of allowed role names
        
    Returns:
        FastAPI dependency function
    """
    async def dependency(token: str = Depends(oauth2_scheme)):
        # Decode and validate token
        payload = decode_token(token)
        
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid or expired token',
                headers={'WWW-Authenticate': 'Bearer'},
            )
        
        # Check role authorization
        user_role = payload.get('role')
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'Insufficient permissions. Required: {", ".join(allowed_roles)}',
            )
        
        return payload
    
    return dependency


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Get current user from token without role restriction.
    Used for endpoints that just need authentication.
    """
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired token',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    
    return payload

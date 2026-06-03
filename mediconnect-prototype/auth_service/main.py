"""
Auth Service - FastAPI application for JWT authentication and user management.
Endpoints: /auth/token, /auth/refresh, /auth/me, /auth/register
"""
import os
from datetime import timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from models import Base, User, Role
from security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    require_role,
)

# Database configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://postgres:postgres@localhost:5432/mediconnect'
)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Pydantic schemas
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = 'patient'
    clinic_ids: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    clinic_ids: Optional[str] = None
    is_active: bool


class TokenPayload(BaseModel):
    username: str
    refresh_token: str


# FastAPI app
app = FastAPI(
    title='MediConnect Auth Service',
    description='JWT Authentication and User Management',
    version='1.0.0',
)


@app.on_event('startup')
async def startup():
    """Initialize database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create default roles if they don't exist
    async with async_session_maker() as session:
        result = await session.execute(select(Role))
        roles = result.scalars().all()
        
        if not roles:
            default_roles = [
                Role(name='patient', description='Patient user - can manage own appointments'),
                Role(name='clinician', description='Healthcare provider - cross-site access'),
                Role(name='admin', description='System administrator - full access'),
            ]
            session.add_all(default_roles)
            await session.commit()


@app.get('/health')
async def health_check():
    """Health check endpoint for container orchestration."""
    return {'status': 'healthy', 'service': 'auth'}


@app.post('/auth/register', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Username already registered',
        )
    
    # Get role
    result = await db.execute(select(Role).where(Role.name == user_data.role))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid role: {user_data.role}',
        )
    
    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role_id=role.id,
        clinic_ids=user_data.clinic_ids or '',
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=role.name,
        clinic_ids=user.clinic_ids,
        is_active=user.is_active,
    )


@app.post('/auth/token', response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and issue JWT tokens.
    
    Returns access token (15 min expiry) and refresh token (7 day expiry).
    """
    # Find user by username
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='User account is disabled',
        )
    
    # Get role name
    result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = result.scalar_one_or_none()
    
    # Create tokens
    access_token_data = {
        'sub': user.username,
        'user_id': user.id,
        'role': role.name,
        'clinic_ids': user.clinic_ids.split(',') if user.clinic_ids else [],
    }
    
    access_token = create_access_token(access_token_data)
    refresh_token = create_refresh_token({'sub': user.username, 'user_id': user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@app.post('/auth/refresh', response_model=TokenResponse)
async def refresh_token(payload: TokenPayload, db: AsyncSession = Depends(get_db)):
    """Refresh access token using valid refresh token."""
    # Validate refresh token
    token_data = decode_token(payload.refresh_token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid refresh token',
        )
    
    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='User not found or disabled',
        )
    
    # Get role
    result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = result.scalar_one_or_none()
    
    # Issue new access token
    access_token_data = {
        'sub': user.username,
        'user_id': user.id,
        'role': role.name,
        'clinic_ids': user.clinic_ids.split(',') if user.clinic_ids else [],
    }
    
    access_token = create_access_token(access_token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=payload.refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@app.get('/auth/me', response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get current authenticated user details."""
    # Fetch full user data
    result = await db.execute(
        select(User, Role).join(Role).where(User.username == current_user['sub'])
    )
    user, role = result.one()
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=role.name,
        clinic_ids=user.clinic_ids,
        is_active=user.is_active,
    )


def get_db():
    """Dependency for database session."""
    db = async_session_maker()
    try:
        yield db
    finally:
        pass


# Import ACCESS_TOKEN_EXPIRE_MINUTES for use in token endpoint
from security import ACCESS_TOKEN_EXPIRE_MINUTES

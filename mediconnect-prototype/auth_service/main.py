import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from pydantic import BaseModel
from passlib.context import CryptContext
import jwt
import logging

JWT_SECRET = os.getenv('JWT_SECRET')
DATABASE_URL = os.getenv('DATABASE_URL')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

if not JWT_SECRET:
    raise ValueError('JWT_SECRET environment variable required')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=5)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from models import User, Role, Base

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserResponse(BaseModel):
    id: int
    username: str
    role: str

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({'exp': expire, 'type': 'refresh'})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get('exp', 0) < datetime.utcnow().timestamp():
            raise HTTPException(status_code=401, detail='Token expired')
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='Invalid token')

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

app = FastAPI(title='MediConnect Auth Service', version='1.0.0')

@app.on_event('startup')
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info('Database tables created')

@app.post('/auth/login', response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalars().first()
    
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    
    access_token = create_access_token({'sub': user.username, 'role': user.role})
    refresh_token = create_refresh_token({'sub': user.username})
    
    response = JSONResponse(content={
        'access_token': access_token,
        'token_type': 'bearer',
        'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60
    })
    response.set_cookie('refresh_token', refresh_token, httponly=True, max_age=REFRESH_TOKEN_EXPIRE_DAYS*86400)
    
    logger.info(f'User {user.username} logged in')
    return response

@app.post('/auth/refresh', response_model=TokenResponse)
async def refresh(request: dict, db: AsyncSession = Depends(get_db)):
    token = request.get('refresh_token')
    if not token:
        raise HTTPException(status_code=401, detail='Refresh token required')
    
    try:
        payload = verify_token(token)
        username = payload.get('sub')
        
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=401, detail='User not found')
        
        access_token = create_access_token({'sub': user.username, 'role': user.role})
        return {
            'access_token': access_token,
            'token_type': 'bearer',
            'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Token refresh failed: {e}')
        raise HTTPException(status_code=401, detail='Invalid refresh token')

@app.get('/auth/me', response_model=UserResponse)
async def get_current_user(authorization: str = None, db: AsyncSession = Depends(get_db)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Authorization header required')
    
    token = authorization.split(' ')[1]
    payload = verify_token(token)
    
    result = await db.execute(select(User).where(User.username == payload.get('sub')))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=401, detail='User not found')
    
    return UserResponse(id=user.id, username=user.username, role=user.role)

@app.get('/health')
async def health():
    return {'status': 'ok', 'service': 'auth_service'}

if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv('AUTH_SERVICE_PORT', 8001))
    uvicorn.run(app, host='0.0.0.0', port=port)

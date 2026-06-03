"""
Authentication middleware for booking service.
Validates JWT tokens by calling auth_service /auth/me endpoint.
"""
import os
import httpx
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Auth service URL from environment
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth_service:8001')

security = HTTPBearer(auto_error=False)


async def get_current_user_from_auth(token: str) -> dict:
    """
    Validate token with auth service and return user details.
    
    Args:
        token: JWT access token
        
    Returns:
        User payload dict from auth service
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f'{AUTH_SERVICE_URL}/auth/me',
                headers={'Authorization': f'Bearer {token}'},
                timeout=5.0,
            )
            
            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Invalid or expired token',
                )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail='Auth service unavailable',
                )
            
            return response.json()
            
        except httpx.ConnectError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Auth service unavailable',
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail='Auth service timeout',
            )


async def validate_token(request: Request, credentials: HTTPAuthorizationCredentials = None):
    """
    FastAPI dependency to validate JWT token on each request.
    
    Extracts Bearer token from Authorization header and validates
    with auth service. Returns user payload for use in endpoints.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing authentication credentials',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    
    token = credentials.credentials
    user = await get_current_user_from_auth(token)
    
    # Attach user info to request state for use in endpoints
    request.state.user = user
    
    return user


def require_role(*allowed_roles: str):
    """
    Factory function to create role-based access control dependency.
    
    Usage:
        @app.get('/protected', dependencies=[Depends(require_role('admin'))])
        
    Args:
        *allowed_roles: Variable number of allowed role names
        
    Returns:
        FastAPI dependency function that validates role
    """
    async def dependency(request: Request, user: dict = None):
        if user is None:
            # Token validation should have happened already
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Authentication required',
            )
        
        user_role = user.get('role')
        
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'Insufficient permissions. Required: {", ".join(allowed_roles)}',
            )
        
        return user
    
    return dependency


async def get_optional_user(request: Request, credentials: HTTPAuthorizationCredentials = None):
    """
    Get user if authenticated, but don't require it.
    For endpoints that work differently for authenticated vs anonymous users.
    """
    if credentials is None:
        request.state.user = None
        return None
    
    try:
        user = await get_current_user_from_auth(credentials.credentials)
        request.state.user = user
        return user
    except HTTPException:
        request.state.user = None
        return None

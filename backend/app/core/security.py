from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, ValidationError
from app.core.config import settings

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/auth/token",
    scheme_name="JWT",
    auto_error=False
)

class TokenData(BaseModel):
    """Token payload data model"""
    sub: Optional[str] = None
    user_id: Optional[str] = None
    scopes: List[str] = []
    exp: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.timestamp()
        }

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to verify against
        
    Returns:
        bool: True if the password matches the hash, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # Log the error in production
        print(f"Error verifying password: {str(e)}")
        return False

def get_password_hash(password: str) -> str:
    """
    Generate a password hash.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)

def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None,
    scopes: Optional[List[str]] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: The data to include in the token
        expires_delta: Optional timedelta for token expiration
        scopes: List of scopes/permissions for the token
        
    Returns:
        str: The encoded JWT token
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=15)
    
    # Add standard claims
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
        "iss": settings.PROJECT_NAME,
        "sub": to_encode.get("sub", ""),
    })
    
    # Add scopes if provided
    if scopes:
        to_encode["scopes"] = scopes
    
    # Encode and return the token
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    required_scopes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get the current user from the JWT token.
    
    Args:
        request: The FastAPI request object
        token: The JWT token from the Authorization header
        required_scopes: List of scopes required to access the endpoint
        
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If token is invalid or user doesn't have required scopes
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode and validate the token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False},
        )
        
        # Extract token data
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        token_scopes = payload.get("scopes", [])
        
        if username is None or user_id is None:
            raise credentials_exception
        
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check required scopes
        if required_scopes:
            for scope in required_scopes:
                if scope not in token_scopes:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Not enough permissions. Required scope: {scope}",
                        headers={"WWW-Authenticate": f"Bearer scope=\"{' '.join(required_scopes)}\""},
                    )
        
        token_data = TokenData(
            sub=username,
            user_id=user_id,
            scopes=token_scopes,
            exp=datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
        )
        
        # In a real app, you would fetch the user from your database here
        # For now, we'll just return the token data with some additional info
        return {
            "username": token_data.sub,
            "id": token_data.user_id,
            "scopes": token_data.scopes
        }
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current active user.
    
    This is a convenience function that can be used as a dependency
    to ensure the user is authenticated and active.
    
    Args:
        current_user: The user data from get_current_user
        
    Returns:
        The current user's data
        
    Raises:
        HTTPException: If the user is inactive
    """
    # In a real app, you would check if the user is active in your database
    # For now, we'll just return the user data
    return current_user


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify a JWT token and return its payload.
    
    Args:
        token: The JWT token to verify
        
    Returns:
        The decoded token payload
        
    Raises:
        HTTPException: If the token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import Optional, List

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.core.config import settings

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = False
    scopes: List[str] = []

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

class User(UserBase):
    id: str
    
    class Config:
        from_attributes = True

class UserInDB(UserBase):
    id: str
    hashed_password: str
    
    @classmethod
    def from_mongo(cls, data: dict):
        data['id'] = str(data.pop('_id'))
        return cls(**data)

# Mock user database
# In a real app, this would be a database model
fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # 'secret' hashed
        "disabled": False,
        "scopes": ["read", "write"],
        "_id": "507f1f77bcf86cd799439011"
    }
}

def get_user(db, username: str):
    if username in db:
        user_data = db[username].copy()
        return UserInDB.from_mongo(user_data)

async def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

@router.post("/token", response_model=Token, summary="OAuth2 token endpoint")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    
    - **username**: Your username
    - **password**: Your password
    - **scope**: Optional space-separated list of scopes (e.g., 'read write')
    
    Returns an access token that can be used in the Authorization header:
    `Authorization: Bearer <token>`
    """
    # In a real app, you would validate the client_id and client_secret here
    # from the request if using OAuth2 with client credentials
    
    user = await authenticate_user(
        fake_users_db, 
        form_data.username, 
        form_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate scopes if provided
    if form_data.scopes:
        invalid_scopes = [s for s in form_data.scopes if s not in user.scopes]
        if invalid_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Invalid scopes: {', '.join(invalid_scopes)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        scopes = form_data.scopes
    else:
        scopes = user.scopes
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "scopes": scopes
        },
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token)

@router.get(
    "/me", 
    response_model=User,
    summary="Get current user information",
    response_description="The current user's information"
)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """
    Get the current user's information.
    
    Returns the user details for the currently authenticated user.
    Requires a valid access token in the Authorization header.
    """
    # In a real app, you would fetch the user from the database
    user_data = fake_users_db.get(current_user["username"])
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserInDB.from_mongo(user_data)

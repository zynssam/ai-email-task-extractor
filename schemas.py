import uuid
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr

# --- Auth Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None

# --- Task Schemas ---
class TaskResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    account_id: uuid.UUID
    description: str
    due_date: Optional[date] = None
    date_is_inferred: bool
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class TaskUpdate(BaseModel):
    status: str

# --- Account Schemas ---
class LinkedAccountResponse(BaseModel):
    id: uuid.UUID
    provider: str
    connected_at: datetime

    class Config:
        from_attributes = True

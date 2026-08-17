import uuid
from datetime import datetime, date
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, field_validator

# --- Auth Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

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
    status: Literal["pending", "completed", "dismissed"]

# --- Account Schemas ---
class LinkedAccountResponse(BaseModel):
    id: uuid.UUID
    provider: str
    connected_at: datetime

    class Config:
        from_attributes = True

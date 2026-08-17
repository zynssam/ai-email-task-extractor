import uuid
import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
import jwt

from database import get_db
from model import User, Task, LinkedAccount
from schemas import (
    UserCreate, UserResponse, Token,
    TaskResponse, TaskUpdate, LinkedAccountResponse
)
from security import (
    hash_password, verify_password, create_access_token, get_current_user,
    deny_token, SECRET_KEY, ALGORITHM, oauth2_scheme
)

load_dotenv()

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="AI Email Task Extractor API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ============================= AUTH ENDPOINTS ==============================

@app.post("/auth/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def signup(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account (rate-limited: 5 requests/minute per IP)."""
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )

    new_user = User(
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        email_verified=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=Token)
@limiter.limit("10/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate and receive a JWT access token (rate-limited: 10 requests/minute per IP)."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token)


@app.post("/auth/refresh", response_model=Token)
def refresh_token(
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
):
    """Issue a fresh access token and revoke the old one."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        old_jti = payload.get("jti")
        if old_jti:
            deny_token(old_jti)
    except jwt.PyJWTError:
        pass

    new_token = create_access_token(data={"sub": str(current_user.id)})
    return Token(access_token=new_token)


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
):
    """Revoke the current access token (logout)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        if jti:
            deny_token(jti)
    except jwt.PyJWTError:
        pass
    return None


@app.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


# ============================= TASK ENDPOINTS ==============================

@app.get("/tasks", response_model=List[TaskResponse])
def get_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    sort_by_due_date: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Task).filter(Task.user_id == current_user.id)
    if status_filter:
        query = query.filter(Task.status == status_filter)

    if sort_by_due_date:
        query = query.order_by(Task.due_date.asc().nulls_last())
    else:
        query = query.order_by(Task.created_at.desc())

    return query.all()


@app.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task_status(
    task_id: uuid.UUID,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Status validation is handled by Pydantic Literal type in TaskUpdate schema
    task.status = task_in.status
    db.commit()
    db.refresh(task)
    return task


# ============================ ACCOUNT ENDPOINTS ============================

@app.get("/accounts", response_model=List[LinkedAccountResponse])
def get_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(LinkedAccount).filter(LinkedAccount.user_id == current_user.id).all()


@app.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account = db.query(LinkedAccount).filter(
        LinkedAccount.id == account_id,
        LinkedAccount.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked account not found"
        )

    db.delete(account)
    db.commit()
    return None

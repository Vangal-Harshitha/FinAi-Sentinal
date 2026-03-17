"""
api/routes/auth.py — Authentication endpoints
POST /auth/register  POST /auth/login  POST /auth/token  GET /auth/me  PATCH /auth/me
"""
from typing import Annotated
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import CurrentUser
from core.config import get_settings
from core.security import create_access_token, create_refresh_token, hash_password, verify_password
from db.database import get_db
from models.orm import User
from schemas.schemas import (
    LoginRequest, MessageResponse, RegisterRequest,
    TokenResponse, UserProfileResponse, UserUpdateRequest,
)

router   = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post("/register", response_model=UserProfileResponse, status_code=201)
async def register(payload: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email              = payload.email,
        password_hash = hash_password(payload.password[:72]),
        full_name          = payload.full_name,
        phone              = payload.phone,
        city               = payload.city,
        occupation_segment = payload.occupation_segment,
        monthly_income     = payload.monthly_income,
        risk_appetite      = payload.risk_appetite or "moderate",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return UserProfileResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.email == payload.email))
    user   = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return TokenResponse(
        access_token  = create_access_token(user.user_id),
        refresh_token = create_refresh_token(user.user_id),
        token_type    = "bearer",
        expires_in    = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# OAuth2 form-based login (for frontend compatibility)
@router.post("/token", response_model=TokenResponse)
async def token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db:   Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.email == form.username))
    user   = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return TokenResponse(
        access_token  = create_access_token(user.user_id),
        refresh_token = create_refresh_token(user.user_id),
        token_type    = "bearer",
        expires_in    = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(current_user: CurrentUser):
    return UserProfileResponse.model_validate(current_user)


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile_alias(current_user: CurrentUser):
    return UserProfileResponse.model_validate(current_user)


@router.patch("/me", response_model=UserProfileResponse)
async def update_profile(
    payload: UserUpdateRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    db.add(current_user)
    await db.flush()
    await db.refresh(current_user)
    return UserProfileResponse.model_validate(current_user)

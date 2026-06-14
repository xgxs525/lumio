from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import ProfileUpdateRequest, get_current_user, me, update_profile
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=dict)
async def current_user_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await me(user=user, db=db)


@router.patch("/me", response_model=dict)
async def update_current_user_profile(
    payload: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await update_profile(payload=payload, user=user, db=db)


@router.get("/me/security", response_model=dict)
async def current_user_security(user: User = Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "userId": str(user.id),
            "email": user.email,
            "phone": user.phone,
            "passwordEnabled": bool(user.password_hash or user.hashed_password),
            "locale": user.locale,
            "timezone": user.timezone,
            "status": user.status,
            "externalAccounts": [],
        },
    }

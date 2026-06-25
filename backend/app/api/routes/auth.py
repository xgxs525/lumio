from __future__ import annotations

import logging
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token, hash_password, token_hash, verify_password
from app.models.user import PasswordReset, User, UserSession
from app.services.bootstrap import ensure_user_workspace
from app.services.email import send_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    account: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    name: str = Field(default="", max_length=100)

    @field_validator("account", "name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    account: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)
    remember: bool = False

    @field_validator("account")
    @classmethod
    def strip_account(cls, value: str) -> str:
        return value.strip()


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    avatarUrl: str | None = Field(default=None, max_length=1024)
    locale: str | None = Field(default=None, max_length=20)
    timezone: str | None = Field(default=None, max_length=64)

    @field_validator("name", "phone", "avatarUrl", "locale", "timezone")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class PasswordUpdateRequest(BaseModel):
    currentPassword: str = Field(..., min_length=1, max_length=128)
    newPassword: str = Field(..., min_length=6, max_length=128)


class DeleteAccountRequest(BaseModel):
    confirmation: str = Field(..., min_length=1, max_length=20)
    currentPassword: str | None = Field(default=None, max_length=128)


class AuthAccountBindRequest(BaseModel):
    provider: str = Field(..., min_length=2, max_length=60)
    provider_user_id: str = Field(..., min_length=1, max_length=255)
    union_id: str | None = Field(default=None, max_length=255)


class ForgotPasswordRequest(BaseModel):
    account: str = Field(..., min_length=3, max_length=255)

    @field_validator("account")
    @classmethod
    def strip_account(cls, value: str) -> str:
        return value.strip()


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=8)
    new_password: str = Field(..., min_length=6, max_length=128)


def _normalize_phone(phone: str) -> str:
    normalized = re.sub(r"[\s\-()]+", "", phone.strip())
    if not re.fullmatch(r"\+?\d{6,20}", normalized):
        raise HTTPException(status_code=400, detail="请输入有效手机号")
    return normalized


def _normalize_account(account: str) -> tuple[str | None, str | None]:
    value = account.strip()
    if "@" in value:
        return value.lower(), None
    return None, _normalize_phone(value)


def _synthetic_email(phone: str) -> str:
    normalized = phone.replace("+", "00")
    return f"phone_{normalized}@phone.lumio.local"


def _user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "name": user.name or user.nickname,
        "avatarUrl": user.avatar_url,
        "locale": user.locale,
        "timezone": user.timezone,
        "status": user.status,
    }


def _workspace_payload(workspace) -> dict:
    return {
        "id": str(workspace.id),
        "name": workspace.name,
        "slug": workspace.slug,
        "plan": workspace.plan,
        "storageQuota": workspace.storage_quota,
        "aiQuota": workspace.ai_quota,
    }


async def _find_user_by_account(db: AsyncSession, account: str) -> User | None:
    email, phone = _normalize_account(account)
    if email:
        result = await db.execute(select(User).where(User.email == email))
    else:
        result = await db.execute(select(User).where(or_(User.phone == phone, User.email == _synthetic_email(phone or ""))))
    return result.scalar_one_or_none()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
    db: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态无效或已过期") from None

    session_hash = token_hash(token)
    session_result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.token_hash == session_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(UTC),
        )
    )
    if session_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or user.status != "active" or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")
    return user


async def _issue_login(db: AsyncSession, user: User, remember: bool = False) -> dict:
    settings = get_settings()
    expires_delta = timedelta(days=30) if remember else timedelta(minutes=settings.access_token_expire_minutes)
    token, expires_at = create_access_token(str(user.id), expires_delta=expires_delta)
    db.add(UserSession(user_id=user.id, token_hash=token_hash(token), expires_at=expires_at))
    workspace = await ensure_user_workspace(db, user)
    await db.flush()
    return {
        "success": True,
        "data": {
            "accessToken": token,
            "tokenType": "bearer",
            "expiresAt": expires_at.isoformat(),
            "user": _user_payload(user),
            "workspace": _workspace_payload(workspace),
        },
    }


@router.post("/register", response_model=dict)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_session)):
    email, phone = _normalize_account(payload.account)
    lookup_value = email or phone or ""
    existing = await _find_user_by_account(db, lookup_value)
    if existing is not None:
        raise HTTPException(status_code=409, detail="账号已存在，请直接登录")

    password = hash_password(payload.password)
    display_name = payload.name or (email.split("@")[0] if email else f"用户{phone[-4:]}")
    user = User(
        email=email or _synthetic_email(phone or ""),
        phone=phone,
        name=display_name,
        nickname=display_name,
        password_hash=password,
        hashed_password=password,
        locale="zh-CN",
        timezone="Asia/Shanghai",
        status="active",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return await _issue_login(db, user, remember=True)


@router.post("/login", response_model=dict)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_session)):
    try:
        user = await _find_user_by_account(db, payload.account)
        if user is None:
            raise HTTPException(status_code=401, detail="账号或密码错误")

        stored_hash = user.password_hash or user.hashed_password
        if not verify_password(payload.password, stored_hash):
            raise HTTPException(status_code=401, detail="账号或密码错误")
        if user.status != "active" or not user.is_active:
            raise HTTPException(status_code=403, detail="账号已停用")
        return await _issue_login(db, user, remember=payload.remember)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Login failed for account: %s", payload.account)
        raise HTTPException(status_code=500, detail="登录服务暂时不可用，请稍后重试")


@router.get("/me", response_model=dict)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    workspace = await ensure_user_workspace(db, user)
    return {"success": True, "data": {"user": _user_payload(user), "workspace": _workspace_payload(workspace)}}


@router.patch("/profile", response_model=dict)
async def update_profile(
    payload: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if payload.name is not None:
        user.name = payload.name
        user.nickname = payload.name
    if payload.avatarUrl is not None:
        user.avatar_url = payload.avatarUrl or None
    if payload.locale is not None:
        user.locale = payload.locale or "zh-CN"
    if payload.timezone is not None:
        user.timezone = payload.timezone or "Asia/Shanghai"
    if payload.phone is not None:
        phone = _normalize_phone(payload.phone) if payload.phone else None
        if phone and phone != user.phone:
            result = await db.execute(select(User).where(User.phone == phone, User.id != user.id))
            if result.scalar_one_or_none() is not None:
                raise HTTPException(status_code=409, detail="手机号已被其他账号绑定")
        user.phone = phone

    workspace = await ensure_user_workspace(db, user)
    await db.flush()
    return {"success": True, "data": {"user": _user_payload(user), "workspace": _workspace_payload(workspace)}}


@router.post("/password", response_model=dict)
async def update_password(
    payload: PasswordUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    stored_hash = user.password_hash or user.hashed_password
    if not verify_password(payload.currentPassword, stored_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")

    new_hash = hash_password(payload.newPassword)
    user.password_hash = new_hash
    user.hashed_password = new_hash
    await db.flush()
    return {"success": True}


@router.delete("/account", response_model=dict)
async def delete_account(
    payload: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if payload.confirmation not in {"注销账号", "DELETE_ACCOUNT"}:
        raise HTTPException(status_code=400, detail="请输入“注销账号”确认操作")

    if payload.currentPassword:
        stored_hash = user.password_hash or user.hashed_password
        if not verify_password(payload.currentPassword, stored_hash):
            raise HTTPException(status_code=400, detail="当前密码不正确")

    now = datetime.now(UTC)
    result = await db.execute(select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)))
    for session in result.scalars().all():
        session.revoked_at = now

    user.status = "deleted"
    user.is_active = False
    user.email = f"deleted_{user.id.hex}@deleted.lumio.local"
    user.phone = None
    user.name = "已注销用户"
    user.nickname = ""
    user.avatar_url = None
    await db.flush()
    return {"success": True}


@router.post("/logout", response_model=dict)
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
    db: AsyncSession = Depends(get_session),
):
    if credentials is None:
        return {"success": True}
    session_hash = token_hash(credentials.credentials)
    result = await db.execute(
        select(UserSession).where(UserSession.token_hash == session_hash, UserSession.revoked_at.is_(None))
    )
    session = result.scalar_one_or_none()
    if session is not None:
        session.revoked_at = datetime.now(UTC)
    return {"success": True}


@router.post("/forgot-password", response_model=dict)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_session)):
    """Send a password reset token/code to the user's email or phone."""
    user = await _find_user_by_account(db, payload.account)
    if user is None:
        # Don't reveal whether the account exists
        return {
            "success": True,
            "data": {"message": "如果该账号存在，重置链接已发送至您的联系方式。", "token": None, "code": None},
        }

    settings = get_settings()
    token = secrets.token_urlsafe(48)
    code = str(secrets.randbelow(900000) + 100000)  # 6-digit code
    expires_at = datetime.now(UTC) + timedelta(minutes=15)

    # Invalidate old unused reset tokens for this user
    result = await db.execute(
        select(PasswordReset).where(
            PasswordReset.user_id == user.id,
            PasswordReset.used == False,  # noqa: E712
            PasswordReset.expires_at > datetime.now(UTC),
        )
    )
    for old in result.scalars().all():
        old.used = True

    reset = PasswordReset(user_id=user.id, token=token, code=code, expires_at=expires_at)
    db.add(reset)
    await db.flush()

    # Try to send a real email; fall back to dev-mode direct return
    email_sent = False
    if user.email and not user.email.startswith("phone_"):
        email_sent = send_reset_email(user.email, token, code)

    if email_sent:
        # Real email sent — don't expose token/code to the client
        return {
            "success": True,
            "data": {
                "message": "如果该账号存在，重置链接已发送至您的邮箱。验证码 15 分钟内有效。",
                "sent": True,
                "expiresIn": 900,
            },
        }

    # Dev/fallback mode — return token & code directly
    is_dev = settings.smtp_host == ""
    return {
        "success": True,
        "data": {
            "message": f"重置验证码已发送{' (开发模式)' if is_dev else ''}。验证码 15 分钟内有效。",
            "token": token if is_dev else None,
            "code": code if is_dev else None,
            "sent": not is_dev,
            "expiresIn": 900,
        },
    }


@router.post("/reset-password", response_model=dict)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_session)):
    """Verify the reset token & code, then set a new password."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(PasswordReset).where(
            PasswordReset.token == payload.token,
            PasswordReset.used == False,  # noqa: E712
            PasswordReset.expires_at > now,
        )
    )
    reset = result.scalar_one_or_none()
    if reset is None:
        raise HTTPException(status_code=400, detail="重置链接已过期或无效，请重新申请。")

    if reset.code and payload.code and reset.code != payload.code:
        raise HTTPException(status_code=400, detail="验证码不正确")

    result = await db.execute(select(User).where(User.id == reset.user_id))
    user = result.scalar_one_or_none()
    if user is None or user.status != "active":
        raise HTTPException(status_code=400, detail="账号不可用")

    new_hash = hash_password(payload.new_password)
    user.password_hash = new_hash
    user.hashed_password = new_hash

    # Revoke all existing sessions
    sessions_result = await db.execute(
        select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
    )
    for session in sessions_result.scalars().all():
        session.revoked_at = now

    # Mark the reset token as used
    reset.used = True
    await db.flush()

    return {"success": True, "data": {"message": "密码已重置，请使用新密码登录。"}}

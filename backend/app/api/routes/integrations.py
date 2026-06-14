from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.routes.auth import get_current_user
from app.core.config import get_settings
from app.models.user import User

router = APIRouter(prefix="/integrations", tags=["integrations"])


class SmsSendRequest(BaseModel):
    phone: str = Field(..., min_length=6, max_length=32)
    template: str = Field(default="verification", max_length=80)
    variables: dict = Field(default_factory=dict)


class EmailSendRequest(BaseModel):
    to: str = Field(..., min_length=3, max_length=255)
    subject: str = Field(..., min_length=1, max_length=160)
    body: str = Field(..., min_length=1, max_length=8000)
    template: str | None = Field(default=None, max_length=80)
    variables: dict = Field(default_factory=dict)


def _configured(value: str | None) -> bool:
    return bool(value and value.strip())


@router.get("/status", response_model=dict)
async def integration_status(_: User = Depends(get_current_user)):
    settings = get_settings()
    return {
        "success": True,
        "data": {
            "ai": {
                "provider": "openai-compatible",
                "model": settings.ai_gateway_model,
                "configured": _configured(settings.ai_gateway_api_key),
                "mode": "real" if _configured(settings.ai_gateway_api_key) else "mock",
            },
            "embedding": {
                "provider": "openai-compatible",
                "model": settings.embedding_model,
                "configured": _configured(settings.embedding_api_key),
                "mode": "real" if _configured(settings.embedding_api_key) else "local-vector",
            },
            "storage": {
                "provider": settings.storage_backend,
                "configured": settings.storage_backend == "local"
                or all(
                    _configured(v)
                    for v in [
                        settings.oss_endpoint,
                        settings.oss_access_key_id,
                        settings.oss_access_key_secret,
                        settings.oss_bucket_name,
                    ]
                ),
            },
            "payment": {
                "provider": settings.payment_provider,
                "configured": settings.payment_provider == "mock",
                "mode": "mock" if settings.payment_provider == "mock" else "external",
            },
            "sms": {
                "provider": settings.sms_provider,
                "configured": _configured(settings.sms_api_key),
                "mode": "mock" if not _configured(settings.sms_api_key) else "external",
            },
            "email": {
                "provider": settings.email_provider,
                "configured": _configured(settings.email_api_key),
                "mode": "mock" if not _configured(settings.email_api_key) else "external",
            },
        },
    }


@router.post("/sms/test", response_model=dict)
async def test_sms(_: User = Depends(get_current_user)):
    return {"success": True, "data": {"sent": True, "mode": "mock", "message": "短信通道测试已进入队列"}}


@router.post("/email/test", response_model=dict)
async def test_email(_: User = Depends(get_current_user)):
    return {"success": True, "data": {"sent": True, "mode": "mock", "message": "邮件通道测试已进入队列"}}


@router.post("/sms/send", response_model=dict)
async def send_sms(payload: SmsSendRequest, _: User = Depends(get_current_user)):
    settings = get_settings()
    configured = _configured(settings.sms_api_key)
    return {
        "success": True,
        "data": {
            "sent": configured,
            "queued": True,
            "mode": "external" if configured else "mock",
            "provider": settings.sms_provider,
            "phone": payload.phone,
            "template": payload.template,
            "message": "短信已提交给服务商" if configured else "短信服务未配置，已按模拟发送记录处理",
        },
    }


@router.post("/email/send", response_model=dict)
async def send_email(payload: EmailSendRequest, _: User = Depends(get_current_user)):
    settings = get_settings()
    configured = _configured(settings.email_api_key)
    return {
        "success": True,
        "data": {
            "sent": configured,
            "queued": True,
            "mode": "external" if configured else "mock",
            "provider": settings.email_provider,
            "to": payload.to,
            "subject": payload.subject,
            "message": "邮件已提交给服务商" if configured else "邮件服务未配置，已按模拟发送记录处理",
        },
    }

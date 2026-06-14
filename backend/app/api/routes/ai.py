import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.ai import AIConversation, AIMessage
from app.models.operations import UsageRecord
from app.models.user import User
from app.schemas.ai import ChatRequest, ChatResponse
from app.services.ai_gateway import AIGatewayError, get_ai_gateway
from app.services.billing import assert_advanced_model_allowed, assert_ai_quota
from app.services.bootstrap import ensure_user_workspace

router = APIRouter(prefix="/ai", tags=["ai"])


class ConversationCreate(BaseModel):
    title: str = Field(default="新会话", max_length=255)
    source_type: str = Field(default="general", max_length=40)
    source_id: str | None = None


class MessageCreate(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant|tool)$")
    content: str = Field(..., min_length=1)
    model_provider: str | None = None
    model_name: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    metadata: dict = Field(default_factory=dict)


def _dt(value):
    return value.isoformat() if value else None


def _uuid_or_400(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 无效") from exc


def _conversation_payload(item: AIConversation):
    return {
        "id": str(item.id),
        "workspaceId": str(item.workspace_id),
        "userId": str(item.user_id) if item.user_id else None,
        "title": item.title,
        "sourceType": item.source_type,
        "sourceId": str(item.source_id) if item.source_id else None,
        "createdAt": _dt(item.created_at),
        "updatedAt": _dt(item.updated_at),
    }


def _message_payload(item: AIMessage):
    return {
        "id": str(item.id),
        "conversationId": str(item.conversation_id),
        "role": item.role,
        "content": item.content,
        "modelProvider": item.model_provider,
        "modelName": item.model_name,
        "inputTokens": item.input_tokens,
        "outputTokens": item.output_tokens,
        "cost": float(item.cost or 0),
        "metadata": item.meta or {},
        "createdAt": _dt(item.created_at),
    }


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _chat_title(payload: ChatRequest) -> str:
    if payload.title and payload.title.strip():
        return payload.title.strip()[:255]
    for message in reversed(payload.messages):
        if message.role == "user" and message.content.strip():
            return message.content.strip().replace("\n", " ")[:40] or "新会话"
    return "新会话"


async def _get_conversation_in_workspace(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    conversation_id: str,
) -> AIConversation:
    conversation_uuid = _uuid_or_400(conversation_id, "conversation_id")
    result = await db.execute(
        select(AIConversation).where(
            AIConversation.id == conversation_uuid,
            AIConversation.workspace_id == workspace_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conversation


@router.post("/chat", response_model=dict)
async def chat(
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if not payload.messages:
        raise HTTPException(status_code=400, detail="消息不能为空")

    workspace = await ensure_user_workspace(db, user)
    estimated_tokens = sum(_estimate_tokens(message.content) for message in payload.messages) + int(payload.max_tokens or 800)
    await assert_advanced_model_allowed(db, workspace, payload.model)
    await assert_ai_quota(db, workspace, estimated_tokens=estimated_tokens, request_count=1)
    source_uuid = _uuid_or_400(payload.source_id, "source_id") if payload.source_id else None
    if payload.conversation_id:
        conversation = await _get_conversation_in_workspace(db, workspace.id, payload.conversation_id)
    else:
        conversation = AIConversation(
            workspace_id=workspace.id,
            user_id=user.id,
            title=_chat_title(payload),
            source_type=payload.source_type or "workspace",
            source_id=source_uuid,
        )
        db.add(conversation)
        await db.flush()

    last_user_message = next((m for m in reversed(payload.messages) if m.role == "user"), None)
    if last_user_message is None or not last_user_message.content.strip():
        raise HTTPException(status_code=400, detail="缺少用户消息")

    user_message = AIMessage(
        conversation_id=conversation.id,
        role="user",
        content=last_user_message.content,
        input_tokens=_estimate_tokens(last_user_message.content),
        output_tokens=0,
        meta={"source": "chat"},
    )
    db.add(user_message)

    gateway = get_ai_gateway()
    try:
        result = await gateway.chat(
            [m.model_dump() for m in payload.messages],
            model=payload.model,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )
    except AIGatewayError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    raw_usage = result.get("usage") or {}
    input_tokens = int(raw_usage.get("prompt_tokens") or _estimate_tokens(" ".join(m.content for m in payload.messages)))
    output_tokens = int(raw_usage.get("completion_tokens") or _estimate_tokens(result["content"]))
    total_tokens = int(raw_usage.get("total_tokens") or input_tokens + output_tokens)
    model_name = result["model"]

    assistant_message_id = uuid.uuid4()
    assistant_message = AIMessage(
        id=assistant_message_id,
        conversation_id=conversation.id,
        role="assistant",
        content=result["content"],
        model_provider="openai-compatible",
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=Decimal("0"),
        meta={"mock": result.get("mock", False), "usage": raw_usage},
    )
    conversation.updated_at = datetime.now(UTC)
    db.add(assistant_message)
    db.add(
        UsageRecord(
            workspace_id=workspace.id,
            user_id=user.id,
            usage_type="ai_tokens",
            quantity=Decimal(total_tokens),
            unit="tokens",
            model_name=model_name,
            cost=Decimal("0"),
            meta={
                "conversationId": str(conversation.id),
                "messageId": str(assistant_message_id),
                "inputTokens": input_tokens,
                "outputTokens": output_tokens,
                "mock": result.get("mock", False),
            },
        )
    )
    await db.flush()

    return {
        "success": True,
        "data": ChatResponse(
            content=result["content"],
            model=model_name,
            mock=result.get("mock", False),
            conversationId=str(conversation.id),
            messageId=str(assistant_message_id),
            usage={
                "inputTokens": input_tokens,
                "outputTokens": output_tokens,
                "totalTokens": total_tokens,
                "unit": "tokens",
            },
        ).model_dump(by_alias=True),
    }


@router.get("/conversations", response_model=dict)
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(AIConversation)
        .where(AIConversation.workspace_id == workspace.id)
        .order_by(AIConversation.updated_at.desc())
        .limit(100)
    )
    return {"success": True, "data": [_conversation_payload(item) for item in result.scalars().all()]}


@router.post("/conversations", response_model=dict)
async def create_conversation(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    source_uuid = _uuid_or_400(payload.source_id, "source_id") if payload.source_id else None
    item = AIConversation(
        workspace_id=workspace.id,
        user_id=user.id,
        title=payload.title.strip() or "新会话",
        source_type=payload.source_type,
        source_id=source_uuid,
    )
    db.add(item)
    await db.flush()
    return {"success": True, "data": _conversation_payload(item)}


@router.get("/conversations/{conversation_id}/messages", response_model=dict)
async def list_messages(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    conversation = await _get_conversation_in_workspace(db, workspace.id, conversation_id)
    result = await db.execute(
        select(AIMessage)
        .where(AIMessage.conversation_id == conversation.id)
        .order_by(AIMessage.created_at.asc())
    )
    return {"success": True, "data": [_message_payload(item) for item in result.scalars().all()]}


@router.post("/conversations/{conversation_id}/messages", response_model=dict)
async def create_message(
    conversation_id: str,
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    conversation = await _get_conversation_in_workspace(db, workspace.id, conversation_id)

    item = AIMessage(
        conversation_id=conversation.id,
        role=payload.role,
        content=payload.content,
        model_provider=payload.model_provider,
        model_name=payload.model_name,
        input_tokens=payload.input_tokens,
        output_tokens=payload.output_tokens,
        meta=payload.metadata,
    )
    db.add(item)
    await db.flush()
    return {"success": True, "data": _message_payload(item)}

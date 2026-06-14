from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.ai import AIConversation, AIMessage
from app.models.operations import UsageRecord
from app.models.user import User
from app.schemas.ai import ChatRequest
from app.services.ai_gateway import AIGatewayError, get_ai_gateway
from app.services.billing import assert_ai_quota
from app.services.bootstrap import ensure_user_workspace

router = APIRouter(prefix="/chat", tags=["chat"])


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def stream_chat(
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if not payload.messages:
        raise HTTPException(status_code=400, detail="消息不能为空")

    workspace = await ensure_user_workspace(db, user)
    total_estimated = sum(_estimate_tokens(message.content) for message in payload.messages) + int(payload.max_tokens or 800)
    await assert_ai_quota(db, workspace, estimated_tokens=total_estimated, request_count=1)
    try:
        source_uuid = uuid.UUID(payload.source_id) if payload.source_id else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="source_id 无效") from exc

    if payload.conversation_id:
        try:
            conversation_id = uuid.UUID(payload.conversation_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="conversation_id 无效") from exc
        conversation = await db.scalar(
            select(AIConversation).where(
                AIConversation.id == conversation_id,
                AIConversation.workspace_id == workspace.id,
            )
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        title = payload.title or next((m.content for m in reversed(payload.messages) if m.role == "user"), "新会话")
        conversation = AIConversation(
            workspace_id=workspace.id,
            user_id=user.id,
            title=title.strip().replace("\n", " ")[:80],
            source_type=payload.source_type or "workspace",
            source_id=source_uuid,
        )
        db.add(conversation)
        await db.flush()

    last_user = next((m for m in reversed(payload.messages) if m.role == "user" and m.content.strip()), None)
    if last_user is None:
        raise HTTPException(status_code=400, detail="缺少用户消息")

    db.add(
        AIMessage(
            conversation_id=conversation.id,
            role="user",
            content=last_user.content,
            input_tokens=_estimate_tokens(last_user.content),
            output_tokens=0,
            meta={"source": "chat_stream"},
        )
    )

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

    content = str(result.get("content") or "")
    model_name = str(result.get("model") or payload.model or "mock")
    input_tokens = sum(_estimate_tokens(message.content) for message in payload.messages)
    output_tokens = _estimate_tokens(content)
    conversation.updated_at = datetime.now(UTC)
    assistant = AIMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=content,
        model_provider="openai-compatible",
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=Decimal("0"),
        meta={"mock": result.get("mock", False), "streamed": True},
    )
    db.add(assistant)
    db.add(
        UsageRecord(
            workspace_id=workspace.id,
            user_id=user.id,
            usage_type="ai_tokens",
            quantity=Decimal(input_tokens + output_tokens),
            unit="tokens",
            model_name=model_name,
            cost=Decimal("0"),
            meta={"conversationId": str(conversation.id), "streamed": True},
        )
    )
    await db.flush()

    async def event_stream():
        yield _sse({"type": "start", "conversationId": str(conversation.id)})
        if content:
            step = max(24, len(content) // 12)
            for index in range(0, len(content), step):
                yield _sse({"type": "delta", "content": content[index : index + step]})
        yield _sse(
            {
                "type": "done",
                "conversationId": str(conversation.id),
                "messageId": str(assistant.id),
                "model": model_name,
                "usage": {"inputTokens": input_tokens, "outputTokens": output_tokens},
            }
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")

from fastapi import APIRouter, HTTPException

from app.schemas.ai import ChatRequest, ChatResponse
from app.services.ai_gateway import AIGatewayError, get_ai_gateway

router = APIRouter(prefix='/ai', tags=['ai'])


@router.post('/chat', response_model=dict)
async def chat(payload: ChatRequest):
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

    return {
        'success': True,
        'data': ChatResponse(
            content=result['content'],
            model=result['model'],
            mock=result.get('mock', False),
        ).model_dump(),
    }

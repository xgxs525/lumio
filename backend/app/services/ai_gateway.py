from typing import Any

import httpx

from app.core.config import get_settings


class AIGatewayError(Exception):
    pass


class AIGateway:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ai_gateway_base_url.rstrip('/')
        self.api_key = settings.ai_gateway_api_key
        self.model = settings.ai_gateway_model
        self.timeout = settings.ai_gateway_timeout

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            return {
                'content': 'AI Gateway 未配置 API Key。请在环境变量中设置 AI_GATEWAY_API_KEY。',
                'model': model or self.model,
                'mock': True,
            }

        payload: dict[str, Any] = {
            'model': model or self.model,
            'messages': messages,
            'temperature': temperature,
        }
        if max_tokens is not None:
            payload['max_tokens'] = max_tokens

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=payload,
            )

        if response.status_code >= 400:
            raise AIGatewayError(f'AI Gateway error {response.status_code}: {response.text}')

        data = response.json()
        content = data['choices'][0]['message']['content']
        return {
            'content': content,
            'model': data.get('model', model or self.model),
            'usage': data.get('usage'),
            'mock': False,
        }


def get_ai_gateway() -> AIGateway:
    return AIGateway()

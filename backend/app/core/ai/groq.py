"""Groq (API compatible con OpenAI) con salida JSON estricta."""

import httpx

from app.core.ai.base import AIProviderError, post_json
from app.core.ai.prompt import STRICT_RESPONSE_SCHEMA

API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self.model = model

    async def generate(self, client: httpx.AsyncClient, system: str, user: str) -> str:
        data = await post_json(
            client,
            self.name,
            API_URL,
            {"Authorization": f"Bearer {self._api_key}"},
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "recomendaciones", "strict": True, "schema": STRICT_RESPONSE_SCHEMA},
                },
                # Menos razonamiento = menos tokens del plan gratuito (8K por minuto).
                "reasoning_effort": "low",
                "temperature": 0.7,
            },
        )
        choices = data.get("choices") or []
        text = ((choices[0].get("message") or {}).get("content") or "") if choices else ""
        if not text.strip():
            raise AIProviderError("groq: respuesta vacía")
        return text

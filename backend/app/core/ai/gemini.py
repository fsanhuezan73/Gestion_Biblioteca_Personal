"""Gemini (Google AI Studio) vía generateContent, con salida JSON."""

import httpx

from app.core.ai.base import AIProviderError, post_json
from app.core.ai.prompt import RESPONSE_SCHEMA

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self.model = model

    async def generate(self, client: httpx.AsyncClient, system: str, user: str) -> str:
        data = await post_json(
            client,
            self.name,
            API_URL.format(model=self.model),
            # La clave va en una cabecera, nunca en la URL (que httpx puede registrar).
            {"x-goog-api-key": self._api_key},
            {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": RESPONSE_SCHEMA,
                    "temperature": 0.7,
                },
            },
        )
        candidates = data.get("candidates") or []
        parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not text.strip():
            reason = candidates[0].get("finishReason") if candidates else "sin candidatos"
            raise AIProviderError(f"gemini: respuesta vacía ({reason})")
        return text

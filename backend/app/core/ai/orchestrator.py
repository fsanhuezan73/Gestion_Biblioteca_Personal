"""Orden de proveedores con respaldo: si uno falla, se intenta el siguiente."""

import logging
from dataclasses import dataclass

import httpx

from app.core.ai.base import AIProvider, AIProviderError
from app.core.ai.gemini import GeminiProvider
from app.core.ai.groq import GroqProvider
from app.core.ai.prompt import SYSTEM_PROMPT, AICandidate, InvalidAIResponse, build_user_prompt, parse_candidates

logger = logging.getLogger(__name__)


class NoProvidersConfigured(Exception):
    """Ningún proveedor de AI_PROVIDER_ORDER tiene clave."""


class AllProvidersFailed(Exception):
    """Todos los proveedores configurados fallaron."""


@dataclass
class AIResult:
    provider: str
    model: str
    candidates: list[AICandidate]


def build_providers(settings) -> list[AIProvider]:
    """Proveedores en el orden configurado; se omiten los desconocidos o sin clave."""
    factories = {
        "gemini": lambda: GeminiProvider(settings.gemini_api_key, settings.ai_gemini_model)
        if settings.gemini_api_key else None,
        "groq": lambda: GroqProvider(settings.groq_api_key, settings.ai_groq_model)
        if settings.groq_api_key else None,
    }
    providers, seen = [], set()
    for name in (n.strip().lower() for n in settings.ai_provider_order.split(",")):
        if name in factories and name not in seen:
            seen.add(name)
            provider = factories[name]()
            if provider:
                providers.append(provider)
    return providers


async def generate_candidates(
    providers: list[AIProvider],
    profile: list[dict],
    transport: httpx.AsyncBaseTransport | None = None,
) -> AIResult:
    """Pide candidatos al primer proveedor que responda un JSON válido.

    Un error del proveedor (cuota, HTTP, timeout) pasa al siguiente de inmediato;
    un JSON inválido se reintenta una vez con el mismo proveedor.
    """
    if not providers:
        raise NoProvidersConfigured()
    user_prompt = build_user_prompt(profile)
    async with httpx.AsyncClient(transport=transport) as client:
        for provider in providers:
            for attempt in (1, 2):
                try:
                    text = await provider.generate(client, SYSTEM_PROMPT, user_prompt)
                    return AIResult(provider.name, provider.model, parse_candidates(text))
                except AIProviderError as error:
                    logger.warning("Proveedor de IA falló: %s", error)
                    break
                except InvalidAIResponse:
                    logger.warning("JSON inválido de %s (intento %d)", provider.name, attempt)
    raise AllProvidersFailed()

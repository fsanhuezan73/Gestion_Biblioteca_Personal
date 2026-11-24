"""Orden de proveedores con respaldo: si uno falla, se intenta el siguiente."""

import asyncio
import logging
from dataclasses import dataclass

import httpx

from app.core.ai.base import AIProvider, AIProviderError
from app.core.ai.gemini import GeminiProvider
from app.core.ai.groq import GroqProvider
from app.core.ai.prompt import SYSTEM_PROMPT, AICandidate, InvalidAIResponse, build_user_prompt, parse_candidates

logger = logging.getLogger(__name__)

# Tiempo total para la IA, con todos los proveedores y reintentos. Junto con la
# verificación (VERIFY_BUDGET_SECONDS) el POST responde en menos de ~60 s, bajo
# el timeout de 90 s del frontend.
AI_TOTAL_BUDGET_SECONDS = 45.0
MIN_ATTEMPT_SECONDS = 3.0
# Tiempo que cada intento deja libre para cada proveedor de respaldo pendiente.
FALLBACK_RESERVE_SECONDS = 15.0


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
    budget_seconds: float = AI_TOTAL_BUDGET_SECONDS,
    reserve_seconds: float = FALLBACK_RESERVE_SECONDS,
) -> AIResult:
    """Pide candidatos al primer proveedor que responda un JSON válido.

    Un error del proveedor (cuota, HTTP, timeout) pasa al siguiente de inmediato;
    un JSON inválido se reintenta una vez con el mismo proveedor. Cada intento
    usa a lo más el tiempo que queda del presupuesto total, dejando
    reserve_seconds para cada proveedor de respaldo pendiente.
    """
    if not providers:
        raise NoProvidersConfigured()
    user_prompt = build_user_prompt(profile)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + budget_seconds
    async with httpx.AsyncClient(transport=transport) as client:
        for index, provider in enumerate(providers):
            pending_fallbacks = len(providers) - index - 1
            for attempt in (1, 2):
                remaining = deadline - loop.time()
                if remaining < MIN_ATTEMPT_SECONDS:
                    logger.warning("Sin tiempo para %s: se agotó el presupuesto de la IA", provider.name)
                    raise AllProvidersFailed()
                # Deja tiempo a los respaldos, salvo que así no alcance para este intento.
                limit = remaining - reserve_seconds * pending_fallbacks
                if limit < MIN_ATTEMPT_SECONDS:
                    limit = remaining
                started = loop.time()
                try:
                    text = await asyncio.wait_for(provider.generate(client, SYSTEM_PROMPT, user_prompt), limit)
                    result = AIResult(provider.name, provider.model, parse_candidates(text))
                    logger.info("IA %s respondió en %.1f s", provider.name, loop.time() - started)
                    return result
                except asyncio.TimeoutError:
                    logger.warning("Proveedor de IA falló: %s: sin respuesta tras %.1f s",
                                   provider.name, loop.time() - started)
                    break
                except AIProviderError as error:
                    logger.warning("Proveedor de IA falló: %s (%.1f s)", error, loop.time() - started)
                    break
                except InvalidAIResponse:
                    logger.warning("JSON inválido de %s (intento %d, %.1f s)", provider.name, attempt,
                                   loop.time() - started)
    raise AllProvidersFailed()

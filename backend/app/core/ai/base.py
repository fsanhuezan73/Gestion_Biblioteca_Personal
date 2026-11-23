"""Interfaz común de los proveedores de IA."""

from typing import Protocol

import httpx

# 30 s por solicitud al proveedor; la conexión debe abrirse antes.
TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class AIProviderError(Exception):
    """Falla del proveedor (cuota, error HTTP, timeout o respuesta vacía).

    El mensaje nunca incluye la clave: solo el proveedor y el tipo de falla.
    """


class AIProvider(Protocol):
    name: str
    model: str

    async def generate(self, client: httpx.AsyncClient, system: str, user: str) -> str:
        """Devuelve el texto JSON generado por el modelo."""
        ...


async def post_json(client: httpx.AsyncClient, provider: str, url: str, headers: dict, body: dict) -> dict:
    """POST con errores normalizados a AIProviderError (sin URL ni cabeceras)."""
    try:
        response = await client.post(url, headers=headers, json=body, timeout=TIMEOUT)
    except httpx.TimeoutException as error:
        raise AIProviderError(f"{provider}: timeout") from error
    except httpx.HTTPError as error:
        raise AIProviderError(f"{provider}: {type(error).__name__}") from error
    if response.status_code >= 400:
        raise AIProviderError(f"{provider}: HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as error:
        raise AIProviderError(f"{provider}: respuesta no JSON") from error

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app.core.ai.gemini import GeminiProvider
from app.core.ai.groq import GroqProvider
from app.core.ai.orchestrator import (
    AllProvidersFailed, NoProvidersConfigured, build_providers, generate_candidates,
)
from app.core.ai.prompt import InvalidAIResponse, parse_candidates

PROFILE = [{"titulo": "Rayuela", "autor": "Julio Cortázar", "genero": "Novela", "estrellas": 5}]
GEMINI_KEY = "gemini-test-key"
GROQ_KEY = "groq-test-key"


def payload(n=8):
    return json.dumps({"recommendations": [
        {"title": f"Libro {i}", "author": f"Autor {i}", "reason": "Te gustará"} for i in range(n)
    ]})


def gemini_ok(text):
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})


def groq_ok(text):
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def router(handlers, calls):
    """handlers: {host: [respuesta | excepción, ...]} en orden de llamada."""
    def handle(request: httpx.Request):
        calls.append(request)
        queue = handlers[request.url.host]
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, Exception):
            raise item
        return item
    return httpx.MockTransport(handle)


def providers():
    return [GeminiProvider(GEMINI_KEY, "gemini-3.5-flash-lite"), GroqProvider(GROQ_KEY, "openai/gpt-oss-120b")]


def run(coro):
    return asyncio.run(coro)


# --- Validación de la respuesta ---------------------------------------------

def test_parse_valid_json_dedupes_and_caps_at_8():
    items = [{"title": "Uno", "author": "A", "reason": "r"}, {"title": "uno", "author": "a", "reason": "r"}]
    items += [{"title": f"L{i}", "author": "B", "reason": "r"} for i in range(10)]
    result = parse_candidates(json.dumps({"recommendations": items}))
    assert len(result) == 8
    assert result[0].title == "Uno" and result[1].title == "L0"


def test_parse_accepts_markdown_fence_and_truncates_long_reason():
    text = "```json\n" + json.dumps({"recommendations": [{"title": "T", "author": "A", "reason": "x" * 500}]}) + "\n```"
    [candidate] = parse_candidates(text)
    assert len(candidate.reason) == 300 and candidate.reason.endswith("…")


@pytest.mark.parametrize("text", ["no es json", "{}", '{"recommendations": []}',
                                  '{"recommendations": [{"title": "", "author": "A", "reason": "r"}]}'])
def test_parse_rejects_invalid(text):
    with pytest.raises(InvalidAIResponse):
        parse_candidates(text)


# --- Configuración -------------------------------------------------------------

def settings(**overrides):
    base = dict(gemini_api_key=GEMINI_KEY, groq_api_key=GROQ_KEY, ai_provider_order="gemini,groq",
                ai_gemini_model="gemini-3.5-flash-lite", ai_groq_model="openai/gpt-oss-120b")
    return SimpleNamespace(**{**base, **overrides})


def test_build_providers_respects_order_and_skips_missing_keys():
    assert [p.name for p in build_providers(settings(ai_provider_order="groq, gemini"))] == ["groq", "gemini"]
    assert [p.name for p in build_providers(settings(gemini_api_key=""))] == ["groq"]
    assert [p.name for p in build_providers(settings(ai_provider_order="otro,gemini,gemini"))] == ["gemini"]
    assert build_providers(settings(gemini_api_key="", groq_api_key="")) == []


# --- Formato de las solicitudes ----------------------------------------------

def test_gemini_request_uses_header_key_and_json_schema():
    calls = []
    transport = router({"generativelanguage.googleapis.com": [gemini_ok(payload())]}, calls)
    result = run(generate_candidates(providers()[:1], PROFILE, transport))
    assert result.provider == "gemini" and len(result.candidates) == 8
    request = calls[0]
    assert request.url.path == "/v1beta/models/gemini-3.5-flash-lite:generateContent"
    assert GEMINI_KEY not in str(request.url)
    assert request.headers["x-goog-api-key"] == GEMINI_KEY
    body = json.loads(request.content)
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert "recommendations" in body["generationConfig"]["responseJsonSchema"]["properties"]
    assert "Rayuela" in body["contents"][0]["parts"][0]["text"]


def test_groq_request_uses_strict_json_schema():
    calls = []
    transport = router({"api.groq.com": [groq_ok(payload())]}, calls)
    result = run(generate_candidates(providers()[1:], PROFILE, transport))
    assert result.provider == "groq" and result.model == "openai/gpt-oss-120b"
    request = calls[0]
    assert request.headers["authorization"] == f"Bearer {GROQ_KEY}"
    body = json.loads(request.content)
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"]["additionalProperties"] is False


# --- Respaldo y reintentos ---------------------------------------------------

@pytest.mark.parametrize("failure", [
    httpx.Response(429, json={"error": "quota"}),
    httpx.Response(503, json={}),
    httpx.ReadTimeout("lento"),
    gemini_ok(""),
])
def test_falls_back_to_groq_when_gemini_fails(failure):
    calls = []
    transport = router({"generativelanguage.googleapis.com": [failure], "api.groq.com": [groq_ok(payload())]}, calls)
    result = run(generate_candidates(providers(), PROFILE, transport))
    assert result.provider == "groq"
    assert [c.url.host for c in calls] == ["generativelanguage.googleapis.com", "api.groq.com"]


def test_invalid_json_is_retried_once_with_same_provider():
    calls = []
    transport = router({"generativelanguage.googleapis.com": [gemini_ok("roto"), gemini_ok(payload())]}, calls)
    result = run(generate_candidates(providers(), PROFILE, transport))
    assert result.provider == "gemini" and len(calls) == 2


def test_invalid_json_twice_falls_back():
    calls = []
    transport = router({
        "generativelanguage.googleapis.com": [gemini_ok("roto"), gemini_ok("roto")],
        "api.groq.com": [groq_ok(payload())],
    }, calls)
    assert run(generate_candidates(providers(), PROFILE, transport)).provider == "groq"
    assert len(calls) == 3


def test_all_providers_failed_and_none_configured():
    calls = []
    transport = router({
        "generativelanguage.googleapis.com": [httpx.Response(500, json={})],
        "api.groq.com": [httpx.Response(429, json={})],
    }, calls)
    with pytest.raises(AllProvidersFailed):
        run(generate_candidates(providers(), PROFILE, transport))
    with pytest.raises(NoProvidersConfigured):
        run(generate_candidates([], PROFILE, transport))


def test_error_messages_never_include_keys(caplog):
    calls = []
    transport = router({
        "generativelanguage.googleapis.com": [httpx.ConnectError("sin red")],
        "api.groq.com": [httpx.Response(401, json={})],
    }, calls)
    with pytest.raises(AllProvidersFailed):
        run(generate_candidates(providers(), PROFILE, transport))
    assert GEMINI_KEY not in caplog.text and GROQ_KEY not in caplog.text

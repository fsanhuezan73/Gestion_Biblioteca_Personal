import json
from contextlib import contextmanager
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import httpx
import oracledb
import pytest
from fastapi.testclient import TestClient

from app.core import book_search
from app.core.config import get_settings
from app.core.security import get_current_user
from app.main import app

TODAY = date(2026, 11, 23)
SECRET_NOTE = "NOTA-PRIVADA-QUE-NUNCA-SALE"

# (id, title, status, rating, finished_at, genre, author)
LIBRARY_ROWS = [
    (1, "Rayuela", "Leído", 5, datetime(2026, 1, 1), "Novela", "Julio Cortázar"),
    (2, "Ficciones", "Leído", 4, None, "Cuentos", "Jorge Luis Borges"),
    (3, "Pedro Páramo", "Leído", 5, None, "Novela", "Juan Rulfo"),
    (4, "La ciudad y los perros", "Quiero leer", None, None, "Novela", "Mario Vargas Llosa"),
]

AI_CANDIDATES = [
    ("Cien años de soledad", "Gabriel García Márquez"),
    ("La ciudad y los perros", "Mario Vargas Llosa"),  # ya está en la biblioteca
    ("Libro inventado por la IA", "Autor Ficticio"),   # no existe
    ("El túnel", "Ernesto Sabato"),
    ("Los detectives salvajes", "Roberto Bolaño"),
    ("La invención de Morel", "Adolfo Bioy Casares"),
    ("Aura", "Carlos Fuentes"),
    ("El Aleph", "Jorge Luis Borges"),
]
KNOWN = {title: author for title, author in AI_CANDIDATES if "inventado" not in title}


def ai_text():
    return json.dumps({"recommendations": [
        {"title": t, "author": a, "reason": f"Porque te gustó Rayuela ({t})"} for t, a in AI_CANDIDATES
    ]})


class Network:
    """MockTransport que simula Gemini, Groq, Google Books y Open Library."""

    def __init__(self, gemini=None, groq=None):
        self.requests: list[httpx.Request] = []
        self.gemini = gemini or (lambda: httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": ai_text()}]}}]}))
        self.groq = groq or (lambda: httpx.Response(200, json={
            "choices": [{"message": {"content": ai_text()}}]}))

    def handler(self, request: httpx.Request):
        self.requests.append(request)
        host = request.url.host
        if host == "generativelanguage.googleapis.com":
            return self.gemini()
        if host == "api.groq.com":
            return self.groq()
        if host == "www.googleapis.com":
            q = request.url.params["q"]
            title = q.split('intitle:"')[1].split('"')[0]
            if title in KNOWN:
                return httpx.Response(200, json={"items": [{"volumeInfo": {
                    "title": title, "authors": [KNOWN[title]], "description": f"Sinopsis de {title}",
                    "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9780000000002"}],
                }}]})
            return httpx.Response(200, json={})
        if host == "openlibrary.org":
            return httpx.Response(200, json={"docs": []})
        return httpx.Response(404, json={})

    @property
    def transport(self):
        return httpx.MockTransport(self.handler)

    def hosts(self):
        return [r.url.host for r in self.requests]


@pytest.fixture
def api():
    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = cursor
    state = {"settings": get_settings().model_copy(update={
        "gemini_api_key": "gemini-test-key", "groq_api_key": "groq-test-key",
        "ai_provider_order": "gemini,groq", "ai_daily_limit": 5, "ai_min_rated_books": 3,
        "google_books_api_key": "google-test-key",
    })}

    @contextmanager
    def connection():
        yield conn

    network = Network()
    book_search.clear_cache()
    with patch("app.main.init_db_pool"), patch("app.main.close_db_pool"), patch(
        "app.api.v1.endpoints.ai.get_db_connection", side_effect=connection
    ), patch("app.api.v1.endpoints.ai.today", return_value=TODAY), patch(
        "app.api.v1.endpoints.ai.get_settings", side_effect=lambda: state["settings"]
    ):
        app.dependency_overrides[get_current_user] = lambda: 42
        try:
            with TestClient(app) as client:
                yield client, cursor, network, state
        finally:
            app.dependency_overrides.clear()
            book_search.clear_cache()


def sqls(cursor):
    return [call.args[0] for call in cursor.execute.call_args_list]


def post(client, network):
    with patch("app.api.v1.endpoints.ai.http_transport", network.transport):
        return client.post("/api/v1/ai/recommendations")


def test_generates_five_verified_books_excluding_library_and_fake(api):
    client, cursor, network, _ = api
    cursor.fetchall.return_value = LIBRARY_ROWS
    cursor.fetchone.side_effect = [None, None]  # sin estado previo; FOR UPDATE sin fila

    response = post(client, network)

    assert response.status_code == 200, response.text
    data = response.json()
    titles = [b["title"] for b in data["recommendations"]]
    assert titles == ["Cien años de soledad", "El túnel", "Los detectives salvajes", "La invención de Morel", "Aura"]
    assert all(b["synopsis"] == f"Sinopsis de {b['title']}" for b in data["recommendations"])
    assert data["provider"] == "gemini" and data["model"] == "gemini-3.5-flash-lite"
    assert data["remaining_today"] == 4 and data["rated_books"] == 3

    # Se guarda con INSERT (sin MERGE) y el JSON no lleva in_library.
    insert = next(c for c in cursor.execute.call_args_list if "INSERT INTO ai_recommendations" in c.args[0])
    assert insert.args[1]["daily_count"] == 1 and insert.args[1]["count_date"] == TODAY
    assert "in_library" not in insert.args[1]["result"]
    assert not any("MERGE" in s.upper() for s in sqls(cursor))
    # El libro que ya estaba en la biblioteca no se verificó.
    google_titles = [r.url.params["q"] for r in network.requests if r.url.host == "www.googleapis.com"]
    assert not any("La ciudad y los perros" in q for q in google_titles)


def test_only_metadata_is_sent_and_private_notes_are_never_queried(api):
    client, cursor, network, _ = api
    cursor.fetchall.return_value = LIBRARY_ROWS
    cursor.fetchone.side_effect = [None, None]
    post(client, network)

    assert not any("personal_notes" in s.lower() for s in sqls(cursor))
    ai_request = next(r for r in network.requests if r.url.host == "generativelanguage.googleapis.com")
    prompt = json.loads(ai_request.content)["contents"][0]["parts"][0]["text"]
    profile = json.loads(prompt.split("(JSON):\n")[1].split("\n\n")[0])
    assert [set(p) for p in profile] == [{"titulo", "autor", "genero", "estrellas"}] * 3
    assert SECRET_NOTE not in prompt
    assert "La ciudad y los perros" not in prompt  # no leído: no forma parte del perfil


def test_falls_back_to_groq_when_gemini_hits_quota(api):
    client, cursor, _, _ = api
    cursor.fetchall.return_value = LIBRARY_ROWS
    cursor.fetchone.side_effect = [None, None]
    network = Network(gemini=lambda: httpx.Response(429, json={"error": "RESOURCE_EXHAUSTED"}))
    response = post(client, network)
    assert response.status_code == 200
    assert response.json()["provider"] == "groq"
    assert network.hosts()[:2] == ["generativelanguage.googleapis.com", "api.groq.com"]


def test_all_providers_down_returns_503_and_does_not_count(api):
    client, cursor, _, _ = api
    cursor.fetchall.return_value = LIBRARY_ROWS
    cursor.fetchone.side_effect = [None]
    network = Network(gemini=lambda: httpx.Response(500, json={}), groq=lambda: httpx.Response(503, json={}))
    response = post(client, network)
    assert response.status_code == 503
    assert not any("ai_recommendations" in s and ("INSERT" in s or "UPDATE" in s) for s in sqls(cursor))


def test_no_verified_books_returns_502_without_counting(api):
    client, cursor, _, _ = api
    cursor.fetchall.return_value = LIBRARY_ROWS
    cursor.fetchone.side_effect = [None]
    fake = json.dumps({"recommendations": [{"title": "Inexistente uno", "author": "Nadie Real", "reason": "r"}]})
    network = Network(gemini=lambda: httpx.Response(200, json={
        "candidates": [{"content": {"parts": [{"text": fake}]}}]}))
    response = post(client, network)
    assert response.status_code == 502
    assert not any("INSERT INTO ai_recommendations" in s for s in sqls(cursor))


def test_requires_minimum_rated_books(api):
    client, cursor, network, _ = api
    cursor.fetchall.return_value = LIBRARY_ROWS[:2]
    cursor.fetchone.side_effect = [None]
    response = post(client, network)
    assert response.status_code == 422
    assert "al menos 3" in response.json()["detail"]
    assert network.requests == []


def test_daily_limit_blocks_before_calling_ai(api):
    client, cursor, network, _ = api
    cursor.fetchall.return_value = LIBRARY_ROWS
    cursor.fetchone.side_effect = [("[]", "gemini", "m", datetime(2026, 11, 23, 12), 5, datetime(2026, 11, 23))]
    response = post(client, network)
    assert response.status_code == 429
    assert network.requests == []


def test_counter_from_previous_day_resets_and_updates_row(api):
    client, cursor, network, _ = api
    cursor.fetchall.return_value = LIBRARY_ROWS
    old = ("[]", "groq", "m", datetime(2026, 11, 22, 12), 5, datetime(2026, 11, 22))
    cursor.fetchone.side_effect = [old, (5, datetime(2026, 11, 22))]
    response = post(client, network)
    assert response.status_code == 200
    update = next(c for c in cursor.execute.call_args_list if c.args[0].strip().startswith("UPDATE ai_recommendations"))
    assert update.args[1]["daily_count"] == 1
    assert response.json()["remaining_today"] == 4


def test_concurrent_request_exhausting_limit_is_rejected_under_lock(api):
    client, cursor, network, _ = api
    cursor.fetchall.return_value = LIBRARY_ROWS
    cursor.fetchone.side_effect = [
        ("[]", "gemini", "m", datetime(2026, 11, 23, 9), 4, datetime(2026, 11, 23)),
        (5, datetime(2026, 11, 23)),  # otra solicitud usó el último cupo mientras tanto
    ]
    assert post(client, network).status_code == 429


def test_insert_race_retries_as_update(api):
    client, cursor, network, _ = api
    cursor.fetchall.return_value = LIBRARY_ROWS
    cursor.fetchone.side_effect = [None, None, (1, datetime(2026, 11, 23))]
    original = cursor.execute.side_effect

    def execute(sql, params=None):
        if "INSERT INTO ai_recommendations" in sql:
            raise oracledb.IntegrityError("ORA-00001")
        return original

    cursor.execute.side_effect = execute
    response = post(client, network)
    assert response.status_code == 200
    assert response.json()["remaining_today"] == 3


def test_no_keys_configured_returns_503(api):
    client, cursor, network, state = api
    state["settings"] = state["settings"].model_copy(update={"gemini_api_key": "", "groq_api_key": ""})
    cursor.fetchall.return_value = LIBRARY_ROWS
    cursor.fetchone.side_effect = [None]
    response = post(client, network)
    assert response.status_code == 503
    assert "no están configuradas" in response.json()["detail"]


def test_get_returns_last_result_with_fresh_library_flag(api):
    client, cursor, _, _ = api
    stored = json.dumps([
        {"title": "Cien años de soledad", "authors": ["Gabriel García Márquez"], "reason": "r", "synopsis": "s"},
        {"title": "La ciudad y los perros", "authors": ["Mario Vargas Llosa"], "reason": "r"},
    ])
    cursor.fetchall.return_value = LIBRARY_ROWS
    cursor.fetchone.side_effect = [(stored, "gemini", "gemini-3.5-flash-lite", datetime(2026, 11, 23, 15), 2,
                                    datetime(2026, 11, 23))]
    response = client.get("/api/v1/ai/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert [b["in_library"] for b in data["recommendations"]] == [False, True]
    assert data["remaining_today"] == 3 and data["daily_limit"] == 5
    assert data["generated_at"].startswith("2026-11-23T15:00:00") and data["generated_at"].endswith("Z")
    assert all(call.args[1] == {"user_id": 42} for call in cursor.execute.call_args_list)


def test_get_accepts_result_already_decoded_by_oracledb(api):
    """Oracle 26ai entrega el CLOB con IS JSON como lista de Python, no como texto."""
    client, cursor, _, _ = api
    stored = [{"title": "Aura", "authors": ["Carlos Fuentes"], "reason": "r"}]
    cursor.fetchall.return_value = LIBRARY_ROWS
    cursor.fetchone.side_effect = [(stored, "groq", "openai/gpt-oss-120b", datetime(2026, 11, 23, 15), 1,
                                    datetime(2026, 11, 23))]
    data = client.get("/api/v1/ai/recommendations").json()
    assert [b["title"] for b in data["recommendations"]] == ["Aura"]


def test_get_without_previous_result(api):
    client, cursor, _, _ = api
    cursor.fetchall.return_value = LIBRARY_ROWS[:1]
    cursor.fetchone.side_effect = [None]
    data = client.get("/api/v1/ai/recommendations").json()
    assert data["recommendations"] == [] and data["remaining_today"] == 5
    assert data["rated_books"] == 1 and data["min_rated_books"] == 3


def test_requires_authentication():
    with patch("app.main.init_db_pool"), patch("app.main.close_db_pool"), TestClient(app) as client:
        assert client.get("/api/v1/ai/recommendations").status_code == 401
        assert client.post("/api/v1/ai/recommendations").status_code == 401

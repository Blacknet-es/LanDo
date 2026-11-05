"""End-to-end connectivity check for the Docker Compose LanDo stack."""

from __future__ import annotations

import hashlib
import math
import os
import uuid

import httpx
from sqlalchemy import text

from src.infrastructure.db.session import engine

API_URL = "http://127.0.0.1:8000"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434").rstrip("/")
OLLAMA_MODEL = "qwen2.5-coder:7b"
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://n8n:5678").rstrip("/")


def _embedding(value: str) -> list[float]:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    values = [byte / 127.5 - 1 for byte in digest[:8]]
    magnitude = math.sqrt(sum(component**2 for component in values))
    return [component / magnitude for component in values]


def _check_database_vector() -> None:
    sample = "LanDo vector similarity E2E smoke test"
    vector_literal = "[" + ",".join(f"{value:.8f}" for value in _embedding(sample)) + "]"

    with engine.begin() as connection:
        version = connection.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one()
        connection.execute(
            text(
                "CREATE TEMP TABLE lando_e2e_vector "
                "(id text PRIMARY KEY, content text, embedding vector(8)) "
                "ON COMMIT DROP"
            )
        )
        connection.execute(
            text(
                "INSERT INTO lando_e2e_vector (id, content, embedding) "
                "VALUES (:id, :content, CAST(:embedding AS vector))"
            ),
            {
                "id": str(uuid.uuid4()),
                "content": sample,
                "embedding": vector_literal,
            },
        )
        match = connection.execute(
            text(
                "SELECT content, embedding <=> CAST(:embedding AS vector) AS distance "
                "FROM lando_e2e_vector ORDER BY distance LIMIT 1"
            ),
            {"embedding": vector_literal},
        ).one()
        if match.distance != 0:
            raise RuntimeError(f"Vector similarity returned unexpected distance {match.distance}")
        print(f"[OK] PostgreSQL pgvector {version}: insert and similarity search")


def _check_api_and_chat(client: httpx.Client) -> None:
    health = client.get(f"{API_URL}/api/v1/health")
    health.raise_for_status()
    paths = client.get(f"{API_URL}/openapi.json").json()["paths"]
    if "/api/v1/chat" not in paths:
        raise RuntimeError("The live API does not publish POST /api/v1/chat")
    print("[OK] FastAPI health and versioned chat route")

    email = f"e2e-{uuid.uuid4()}@example.test"
    password = f"e2e-{uuid.uuid4()}-test-password"
    registered = client.post(
        f"{API_URL}/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    registered.raise_for_status()
    user_id = registered.json()["id"]
    original: dict | None = None
    try:
        login = client.post(
            f"{API_URL}/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        login.raise_for_status()
        client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

        previous_settings = client.get(f"{API_URL}/api/v1/settings/llm")
        previous_settings.raise_for_status()
        original = previous_settings.json()

        configured = client.put(
            f"{API_URL}/api/v1/settings/llm",
            json={
                "selected_provider": "ollama",
                "selected_model": OLLAMA_MODEL,
                "ollama_base_url": OLLAMA_BASE_URL,
            },
        )
        configured.raise_for_status()
        response = client.post(
            f"{API_URL}/api/v1/chat",
            json={
                "message": "Responde únicamente con el texto exacto LANDO_E2E_OK.",
                "thread_id": f"e2e-{uuid.uuid4()}",
                "user_timezone": "Europe/Madrid",
            },
        )
        response.raise_for_status()
        reply = response.json().get("reply")
        if not isinstance(reply, str) or "LANDO_E2E_OK" not in reply:
            raise RuntimeError(f"Unexpected chat response: {reply!r}")
        print(f"[OK] API chat inference via {OLLAMA_MODEL}")
    finally:
        try:
            if original is not None:
                restored = client.put(
                    f"{API_URL}/api/v1/settings/llm",
                    json={
                        "selected_provider": original["selected_provider"],
                        "selected_model": original["selected_model"],
                        "ollama_base_url": original["ollama_base_url"],
                    },
                )
                restored.raise_for_status()
        finally:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "DELETE FROM event_reminders WHERE event_id IN "
                        "(SELECT id FROM events WHERE user_id = CAST(:user_id AS uuid))"
                    ),
                    {"user_id": user_id},
                )
                connection.execute(
                    text(
                        "DELETE FROM recurrence_rules WHERE event_id IN "
                        "(SELECT id FROM events WHERE user_id = CAST(:user_id AS uuid))"
                    ),
                    {"user_id": user_id},
                )
                for table in (
                    "location_triggers",
                    "memory_items",
                    "events",
                    "user_locations",
                    "user_settings",
                ):
                    connection.execute(
                        text(
                            f"DELETE FROM {table} "
                            "WHERE user_id = CAST(:user_id AS uuid)"
                        ),
                        {"user_id": user_id},
                    )
                connection.execute(
                    text("DELETE FROM users WHERE id = CAST(:user_id AS uuid)"),
                    {"user_id": user_id},
                )


def _check_n8n(client: httpx.Client) -> None:
    response = client.get(f"{N8N_BASE_URL}/healthz")
    response.raise_for_status()
    print("[OK] n8n health endpoint from API container")


def main() -> None:
    with httpx.Client(timeout=180) as client:
        _check_database_vector()
        _check_api_and_chat(client)
        _check_n8n(client)
    print("[OK] LanDo Compose E2E checks passed")


if __name__ == "__main__":
    main()

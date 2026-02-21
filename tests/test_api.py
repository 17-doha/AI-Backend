"""
pytest test suite for the AI Agent Platform API.

All OpenAI API calls are mocked via unittest.mock.patch so no real API
calls or billing occur during testing.

Run with:
    pytest tests/ -v
"""
import io
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

AGENT_PAYLOAD = {
    "name": "Support Bot",
    "prompt": "You are a helpful customer support agent.",
}


async def _create_agent(client) -> dict:
    """Helper: create an agent and return the response JSON."""
    resp = await client.post("/agents", json=AGENT_PAYLOAD)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_session(client, agent_id: str) -> dict:
    """Helper: create a session and return the response JSON."""
    resp = await client.post("/sessions", json={"agent_id": agent_id})
    assert resp.status_code == 201, resp.text
    return resp.json()


# ────────────────────────────────────────────────────────────────────────────
# Agent tests
# ────────────────────────────────────────────────────────────────────────────

async def test_create_agent(client):
    """POST /agents — should return 201 with the created agent."""
    data = await _create_agent(client)

    assert data["name"] == AGENT_PAYLOAD["name"]
    assert data["prompt"] == AGENT_PAYLOAD["prompt"]
    assert "id" in data
    assert "created_at" in data


async def test_list_agents(client):
    """GET /agents — should return at least one agent after creation."""
    await _create_agent(client)

    resp = await client.get("/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert isinstance(agents, list)
    assert len(agents) >= 1


async def test_get_agent(client):
    """GET /agents/{id} — should return the exact agent."""
    created = await _create_agent(client)
    agent_id = created["id"]

    resp = await client.get(f"/agents/{agent_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == agent_id


async def test_get_agent_not_found(client):
    """GET /agents/{id} with invalid ID — should return 404."""
    resp = await client.get("/agents/does-not-exist")
    assert resp.status_code == 404


async def test_update_agent(client):
    """PUT /agents/{id} — should update name/prompt fields."""
    created = await _create_agent(client)
    agent_id = created["id"]

    update_payload = {"name": "Updated Bot", "prompt": "You are an expert."}
    resp = await client.put(f"/agents/{agent_id}", json=update_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Bot"
    assert data["prompt"] == "You are an expert."


# ────────────────────────────────────────────────────────────────────────────
# Session tests
# ────────────────────────────────────────────────────────────────────────────

async def test_create_session(client):
    """POST /sessions — should return 201 with session linked to agent."""
    agent = await _create_agent(client)
    session = await _create_session(client, agent["id"])

    assert "id" in session
    assert session["agent_id"] == agent["id"]


async def test_create_session_invalid_agent(client):
    """POST /sessions with bad agent_id — should return 404."""
    resp = await client.post("/sessions", json={"agent_id": "nonexistent-agent"})
    assert resp.status_code == 404


async def test_get_session(client):
    """GET /sessions/{id} — should return session with empty messages list."""
    agent = await _create_agent(client)
    created = await _create_session(client, agent["id"])

    resp = await client.get(f"/sessions/{created['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert isinstance(data["messages"], list)


# ────────────────────────────────────────────────────────────────────────────
# Text message tests
# ────────────────────────────────────────────────────────────────────────────

@patch(
    "app.services.openai_service.chat_completion",
    new_callable=AsyncMock,
    return_value="Hello! I'm here to help you.",
)
async def test_send_text_message(mock_chat, client):
    """POST /messages/text — should store messages and return assistant reply."""
    agent = await _create_agent(client)
    session = await _create_session(client, agent["id"])

    payload = {"session_id": session["id"], "content": "Hello!"}
    resp = await client.post("/messages/text", json=payload)
    assert resp.status_code == 201

    data = resp.json()
    assert data["user_message"]["role"] == "user"
    assert data["user_message"]["content"] == "Hello!"
    assert data["assistant_message"]["role"] == "assistant"
    assert data["assistant_message"]["content"] == "Hello! I'm here to help you."

    # Ensure mock was called exactly once
    mock_chat.assert_called_once()


@patch(
    "app.services.openai_service.chat_completion",
    new_callable=AsyncMock,
    return_value="Mocked reply",
)
async def test_text_message_history_grows(mock_chat, client):
    """Sending multiple messages should grow the session history."""
    agent = await _create_agent(client)
    session = await _create_session(client, agent["id"])
    session_id = session["id"]

    for i in range(3):
        payload = {"session_id": session_id, "content": f"Message {i}"}
        resp = await client.post("/messages/text", json=payload)
        assert resp.status_code == 201

    # Check session now has 6 messages (3 user + 3 assistant)
    resp = await client.get(f"/sessions/{session_id}")
    assert len(resp.json()["messages"]) == 6


async def test_text_message_invalid_session(client):
    """POST /messages/text with bad session_id — should return 404."""
    payload = {"session_id": "nonexistent-session", "content": "Hello"}
    resp = await client.post("/messages/text", json=payload)
    assert resp.status_code == 404


# ────────────────────────────────────────────────────────────────────────────
# Voice message tests
# ────────────────────────────────────────────────────────────────────────────

@patch("app.services.openai_service.text_to_speech", new_callable=AsyncMock, return_value=b"FAKE_MP3_BYTES")
@patch("app.services.openai_service.chat_completion", new_callable=AsyncMock, return_value="Great question!")
@patch("app.services.openai_service.speech_to_text", new_callable=AsyncMock, return_value="What is the weather today?")
async def test_send_voice_message(mock_stt, mock_chat, mock_tts, client):
    """POST /messages/voice — full pipeline: STT → Chat → TTS → MP3 response."""
    agent = await _create_agent(client)
    session = await _create_session(client, agent["id"])

    fake_audio = io.BytesIO(b"FAKE_AUDIO_BYTES")
    fake_audio.name = "test.webm"

    resp = await client.post(
        "/messages/voice",
        params={"session_id": session["id"]},
        files={"audio": ("test.webm", fake_audio, "audio/webm")},
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.content == b"FAKE_MP3_BYTES"

    # Verify the full pipeline was called
    mock_stt.assert_called_once()
    mock_chat.assert_called_once()
    mock_tts.assert_called_once()

    # Verify messages were stored
    session_resp = await client.get(f"/sessions/{session['id']}")
    messages = session_resp.json()["messages"]
    assert any(m["content"] == "What is the weather today?" for m in messages)
    assert any(m["content"] == "Great question!" for m in messages)


async def test_voice_message_invalid_session(client):
    """POST /messages/voice with bad session_id — should return 404."""
    fake_audio = io.BytesIO(b"FAKE_AUDIO")
    resp = await client.post(
        "/messages/voice",
        params={"session_id": "nonexistent"},
        files={"audio": ("test.webm", fake_audio, "audio/webm")},
    )
    assert resp.status_code == 404


# ────────────────────────────────────────────────────────────────────────────
# Health check
# ────────────────────────────────────────────────────────────────────────────

async def test_health_check(client):
    """GET /health — should return status ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

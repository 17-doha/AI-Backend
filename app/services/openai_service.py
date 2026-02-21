import io
import logging
from typing import List

from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Singleton async OpenAI client
_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """Return (or create) the singleton AsyncOpenAI client."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


# ── Chat Completion ───────────────────────────────────────────────────────────

async def chat_completion(
    messages: List[dict],
    model: str = "gpt-4o-mini",
) -> str:
    """
    Call the OpenAI ChatCompletion API.

    Args:
        messages: A list of dicts with 'role' and 'content' keys,
                  matching the OpenAI messages array format.
        model:    The OpenAI model to use.

    Returns:
        The assistant's reply text.
    """
    client = get_openai_client()
    logger.info("Calling ChatCompletion with %d messages, model=%s", len(messages), model)

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
    )
    content = response.choices[0].message.content or ""
    logger.info("ChatCompletion returned %d chars", len(content))
    return content


# ── Speech-to-Text (Whisper) ──────────────────────────────────────────────────

async def speech_to_text(
    audio_bytes: bytes,
    filename: str = "audio.webm",
) -> str:
    """
    Transcribe audio bytes using OpenAI Whisper.

    Args:
        audio_bytes: Raw audio file bytes.
        filename:    Original filename (used to infer audio format).

    Returns:
        Transcribed text string.
    """
    client = get_openai_client()
    logger.info("Calling Whisper STT for file=%s (%d bytes)", filename, len(audio_bytes))

    audio_buffer = io.BytesIO(audio_bytes)
    audio_buffer.name = filename  # Whisper uses the name to detect MIME type

    transcript = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_buffer,
    )
    text = transcript.text
    logger.info("Whisper transcription: %s", text[:100])
    return text


# ── Text-to-Speech ────────────────────────────────────────────────────────────

async def text_to_speech(
    text: str,
    voice: str | None = None,
) -> bytes:
    """
    Convert text to speech audio using OpenAI TTS.

    Args:
        text:  The text to convert to audio.
        voice: TTS voice identifier (falls back to settings.tts_voice).

    Returns:
        MP3 audio bytes.
    """
    client = get_openai_client()
    chosen_voice = voice or settings.tts_voice
    logger.info("Calling TTS for %d chars, voice=%s", len(text), chosen_voice)

    response = await client.audio.speech.create(
        model="tts-1",
        voice=chosen_voice,
        input=text,
        response_format="mp3",
    )
    audio_bytes = response.content
    logger.info("TTS returned %d bytes of audio", len(audio_bytes))
    return audio_bytes

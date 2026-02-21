import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.chat import RoleEnum
from app.schemas.chat import TextMessageRequest, TextMessageResponse
from app.services import crud
from app.services import openai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["Messages"])


# ── Helper: build OpenAI messages array ────────────────────────────────────────

def _build_openai_messages(system_prompt: str, history) -> list[dict]:
    """
    Construct the messages array for ChatCompletion from the agent's system
    prompt and the session's existing message history.
    """
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg.role.value, "content": msg.content})
    return messages


# ── Text Message Endpoint ─────────────────────────────────────────────────────

@router.post(
    "/text",
    response_model=TextMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a text message and get an AI response",
)
async def send_text_message(
    payload: TextMessageRequest,
    db: AsyncSession = Depends(get_db),
) -> TextMessageResponse:
    """
    1. Validate session and fetch its linked agent.
    2. Build the message history for ChatCompletion.
    3. Call OpenAI ChatCompletion API.
    4. Persist both the user message and the assistant response.
    5. Return both messages.
    """
    # Fetch and validate session
    session = await crud.get_session(db, payload.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Build history for the model
    history = await crud.get_session_messages(db, session.id)
    openai_messages = _build_openai_messages(session.agent.prompt, history)
    openai_messages.append({"role": "user", "content": payload.content})

    # Call ChatCompletion
    try:
        assistant_text = await openai_service.chat_completion(openai_messages)
    except Exception as exc:
        logger.exception("ChatCompletion failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI API error. Please try again later.",
        )

    # Persist messages
    user_msg = await crud.create_message(db, session.id, RoleEnum.user, payload.content)
    asst_msg = await crud.create_message(db, session.id, RoleEnum.assistant, assistant_text)

    return TextMessageResponse(user_message=user_msg, assistant_message=asst_msg)


# ── Voice Message Endpoint ────────────────────────────────────────────────────

@router.post(
    "/voice",
    summary="Send an audio message and receive an audio response",
    responses={
        200: {
            "content": {"audio/mpeg": {}},
            "description": "MP3 audio response from the AI agent",
        }
    },
)
async def send_voice_message(
    session_id: str,
    audio: UploadFile = File(..., description="Audio file (mp3, wav, webm, m4a, ogg, etc.)"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Full voice pipeline:

    1. Transcribe uploaded audio → Whisper STT.
    2. Pass transcription through ChatCompletion (with session history).
    3. Convert assistant text response → TTS audio (MP3).
    4. Save transcribed user text and assistant text to the database.
    5. Return the MP3 audio file directly in the response body.
    """
    # Validate session
    session = await crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Read audio bytes
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is empty")

    # Step 1 — Speech-to-Text
    try:
        transcription = await openai_service.speech_to_text(
            audio_bytes,
            filename=audio.filename or "audio.webm",
        )
    except Exception as exc:
        logger.exception("Whisper STT failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Speech-to-text failed. Please try again.",
        )

    # Step 2 — Chat Completion
    history = await crud.get_session_messages(db, session.id)
    openai_messages = _build_openai_messages(session.agent.prompt, history)
    openai_messages.append({"role": "user", "content": transcription})

    try:
        assistant_text = await openai_service.chat_completion(openai_messages)
    except Exception as exc:
        logger.exception("ChatCompletion failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Chat completion failed. Please try again.",
        )

    # Step 3 — Text-to-Speech
    try:
        audio_response_bytes = await openai_service.text_to_speech(assistant_text)
    except Exception as exc:
        logger.exception("TTS failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Text-to-speech failed. Please try again.",
        )

    # Step 4 — Persist messages
    await crud.create_message(db, session.id, RoleEnum.user, transcription)
    await crud.create_message(db, session.id, RoleEnum.assistant, assistant_text)

    logger.info(
        "Voice pipeline complete for session=%s | transcription=%s chars | response=%s chars | audio=%d bytes",
        session_id,
        len(transcription),
        len(assistant_text),
        len(audio_response_bytes),
    )

    # Step 5 — Return audio
    return Response(
        content=audio_response_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "attachment; filename=response.mp3",
            "X-Transcription": transcription[:200],  # handy debug header
        },
    )

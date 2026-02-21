from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.chat import RoleEnum


# ── Message ──────────────────────────────────────────────────────────────────

class MessageBase(BaseModel):
    role: RoleEnum
    content: str


class MessageCreate(MessageBase):
    pass


class MessageResponse(MessageBase):
    id: str
    session_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Session ──────────────────────────────────────────────────────────────────

class SessionBase(BaseModel):
    agent_id: str


class SessionCreate(SessionBase):
    pass


class SessionResponse(SessionBase):
    id: str
    created_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ── Agent ────────────────────────────────────────────────────────────────────

class AgentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    prompt: str = Field(..., description="The system prompt / instructions for this agent")


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    prompt: Optional[str] = None


class AgentResponse(AgentBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Chat request/response ─────────────────────────────────────────────────────

class TextMessageRequest(BaseModel):
    session_id: str
    content: str = Field(..., min_length=1, description="The user's text message")


class TextMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse


class VoiceMessageResponse(BaseModel):
    transcription: str = Field(..., description="Text transcribed from the uploaded audio")
    assistant_text: str = Field(..., description="Text response from the AI assistant")
    audio_url: str = Field(..., description="Endpoint to stream the generated audio response")

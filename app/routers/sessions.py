import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import limiter
from app.schemas.chat import SessionCreate, SessionResponse
from app.services import crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
@limiter.limit("20/minute")
async def create_session(
    request: Request,
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Create a new chat session linked to an existing agent. Limit: 20 req/min."""
    agent = await crud.get_agent(db, payload.agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{payload.agent_id}' not found",
        )

    session = await crud.create_session(db, payload.agent_id)
    logger.info("Created session id=%s for agent id=%s", session.id, payload.agent_id)
    return session


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get a session with its message history",
)
@limiter.limit("60/minute")
async def get_session(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Retrieve a session and its full chronological message history. Limit: 60 req/min."""
    session = await crud.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session

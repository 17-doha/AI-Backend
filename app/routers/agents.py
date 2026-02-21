import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import limiter
from app.schemas.chat import AgentCreate, AgentResponse, AgentUpdate
from app.services import crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new AI agent",
)
@limiter.limit("30/minute")
async def create_agent(
    request: Request,
    payload: AgentCreate,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Create a new agent with a name and system prompt. Limit: 30 req/min."""
    agent = await crud.create_agent(db, payload)
    logger.info("Created agent id=%s name=%s", agent.id, agent.name)
    return agent


@router.get(
    "",
    response_model=list[AgentResponse],
    summary="List all agents",
)
@limiter.limit("60/minute")
async def list_agents(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[AgentResponse]:
    """Return a paginated list of all agents. Limit: 60 req/min."""
    return await crud.list_agents(db, skip=skip, limit=limit)


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get an agent by ID",
)
@limiter.limit("60/minute")
async def get_agent(
    request: Request,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Retrieve a single agent by its UUID. Limit: 60 req/min."""
    agent = await crud.get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update an agent",
)
@limiter.limit("30/minute")
async def update_agent(
    request: Request,
    agent_id: str,
    payload: AgentUpdate,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Partially update an agent's name and/or prompt. Limit: 30 req/min."""
    agent = await crud.get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    updated = await crud.update_agent(db, agent, payload)
    logger.info("Updated agent id=%s", updated.id)
    return updated

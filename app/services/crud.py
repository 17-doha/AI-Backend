import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Agent, Message, RoleEnum, Session
from app.schemas.chat import AgentCreate, AgentUpdate


# ── Agent CRUD ────────────────────────────────────────────────────────────────

async def create_agent(db: AsyncSession, data: AgentCreate) -> Agent:
    """Insert a new Agent record and return it."""
    agent = Agent(id=str(uuid.uuid4()), name=data.name, prompt=data.prompt)
    db.add(agent)
    await db.flush()
    await db.refresh(agent)
    return agent


async def get_agent(db: AsyncSession, agent_id: str) -> Optional[Agent]:
    """Fetch a single Agent by ID, or None if not found."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


async def list_agents(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Agent]:
    """Return a paginated list of Agents."""
    result = await db.execute(select(Agent).offset(skip).limit(limit))
    return list(result.scalars().all())


async def update_agent(
    db: AsyncSession,
    agent: Agent,
    data: AgentUpdate,
) -> Agent:
    """Apply partial updates to an Agent and persist them."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    await db.flush()
    await db.refresh(agent)
    return agent


# ── Session CRUD ──────────────────────────────────────────────────────────────

async def create_session(db: AsyncSession, agent_id: str) -> Session:
    """Create a new chat session linked to an agent."""
    session = Session(id=str(uuid.uuid4()), agent_id=agent_id)
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: str) -> Optional[Session]:
    """Fetch a Session (with messages) by ID, or None if not found."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    return result.scalar_one_or_none()


# ── Message CRUD ──────────────────────────────────────────────────────────────

async def create_message(
    db: AsyncSession,
    session_id: str,
    role: RoleEnum,
    content: str,
) -> Message:
    """Insert a new Message record into a session."""
    message = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role=role,
        content=content,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def get_session_messages(
    db: AsyncSession,
    session_id: str,
) -> List[Message]:
    """Return all messages for a session ordered by creation time."""
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())

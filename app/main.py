import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import agents, messages, sessions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)

settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.database import engine
    from app.models.chat import Base

    if settings.app_env == "development":
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logging.getLogger(__name__).info("Database tables verified/created.")
        except Exception as e:
            logging.getLogger(__name__).warning(
                "Could not connect to database on startup: %s. "
                "Check DATABASE_URL in .env. Endpoints requiring DB will fail.",
                e,
            )

    logging.getLogger(__name__).info(
        "AI Agent Platform started | env=%s | docs=/docs", settings.app_env
    )
    yield

    from app.core.database import engine as _engine
    await _engine.dispose()
    logging.getLogger(__name__).info("AI Agent Platform shutdown complete")



# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "Production-ready AI Agent Platform API.\n\n"
        "Create agents, manage chat sessions, and interact via text or voice "
        "using OpenAI's ChatCompletion, Whisper, and TTS APIs."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(agents.router)
app.include_router(sessions.router)
app.include_router(messages.router)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"], summary="Health check")
async def health_check() -> dict:
    """Returns service status. Used by Docker and load balancers."""
    return {"status": "ok", "version": settings.app_version}

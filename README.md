# AI Agent Platform — Backend Service

A production-ready FastAPI backend for an AI Agent Platform using **OpenAI** (ChatCompletion, Whisper STT, TTS), **PostgreSQL via Supabase**, async SQLAlchemy, Alembic migrations, and Docker.

---

## Features

| Area | Detail |
|---|---|
| Agents | Create, list, update AI agents with custom system prompts |
| Sessions | Multi-session chat history linked to an agent |
| Text Chat | User message → ChatCompletion → AI reply (persisted) |
| Voice Chat | Audio upload → Whisper STT → ChatCompletion → TTS → MP3 response |
| Database | PostgreSQL / Supabase via async SQLAlchemy + asyncpg |
| Migrations | Alembic with async support |
| Tests | pytest + httpx with fully mocked OpenAI calls |
| Docker | Multi-stage container with non-root user |

---

## Project Structure

```
project_root/
├── app/
│   ├── main.py                 # FastAPI app, routers, lifespan
│   ├── core/
│   │   ├── config.py           # Pydantic settings (loads .env)
│   │   └── database.py         # Async SQLAlchemy engine + get_db()
│   ├── models/
│   │   └── chat.py             # Agent, Session, Message ORM models
│   ├── schemas/
│   │   └── chat.py             # Pydantic v2 request/response schemas
│   ├── routers/
│   │   ├── agents.py           # POST/GET/PUT /agents
│   │   ├── sessions.py         # POST/GET /sessions
│   │   └── messages.py         # POST /messages/text  POST /messages/voice
│   └── services/
│       ├── openai_service.py   # Chat, STT, TTS wrappers
│       └── crud.py             # Async DB CRUD operations
├── tests/
│   ├── conftest.py             # In-memory SQLite + httpx client fixtures
│   └── test_api.py             # 12 tests, all OpenAI calls mocked
├── alembic/
│   ├── env.py                  # Async Alembic environment
│   ├── script.py.mako          # Migration template
│   └── versions/
│       └── 0001_initial.py     # Initial migration
├── alembic.ini
├── Dockerfile                  # Multi-stage Docker build
├── pytest.ini
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### 1. Clone & configure environment

```bash
# Copy and fill in the .env file
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@db.xxxx.supabase.co:5432/postgres
OPENAI_API_KEY=sk-...
TTS_VOICE=alloy
APP_ENV=development
```

### 2. Install dependencies

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Run database migrations

```bash
# Apply all migrations against your Supabase/PostgreSQL database
alembic upgrade head
```

### 4. Start the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)  
Open **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Running Tests

Tests use an in-memory SQLite database. **No real OpenAI API calls are made.**

```bash
pytest tests/ -v
```

Expected output: **12 passed** ✅

---

## Docker

### Build

```bash
docker build -t agent-platform .
```

### Run

```bash
docker run --env-file .env -p 8000:8000 agent-platform
```

### Run with Docker Compose (optional)

```yaml
# docker-compose.yml
version: "3.9"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
```

```bash
docker compose up --build
```

---

## API Endpoints

### Agents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/agents` | Create a new agent |
| `GET` | `/agents` | List all agents |
| `GET` | `/agents/{id}` | Get agent by ID |
| `PUT` | `/agents/{id}` | Update agent name/prompt |

### Sessions

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/sessions` | Create a session linked to an agent |
| `GET` | `/sessions/{id}` | Get session with full message history |

### Messages

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/messages/text` | Send text, get AI reply (JSON) |
| `POST` | `/messages/voice` | Upload audio, get MP3 AI reply |

### System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc UI |

---

## Supabase Connection

Use the **Transaction Pooler** connection string from your Supabase project dashboard:

```
postgresql+asyncpg://postgres.[project]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres
```

> ⚠️ Supabase free-tier pauses the database after inactivity. Use `pool_pre_ping=True` (already configured) to handle reconnections.

---

## Voice Message Flow

```
Client uploads audio file (multipart/form-data)
        ↓
  Whisper STT  →  transcription text
        ↓
  ChatCompletion  →  assistant text response
        ↓
  OpenAI TTS  →  MP3 audio bytes
        ↓
  Response  (Content-Type: audio/mpeg)
  Header  X-Transcription: <transcribed text>
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | PostgreSQL asyncpg connection string |
| `OPENAI_API_KEY` | ✅ | — | OpenAI secret key |
| `TTS_VOICE` | ❌ | `alloy` | TTS voice (`alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`) |
| `APP_ENV` | ❌ | `development` | `development` auto-creates tables; use Alembic in production |

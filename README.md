# AI Agent Platform — Backend Service

A production-ready FastAPI backend for an AI Agent Platform using **OpenAI** (ChatCompletion, Whisper STT, TTS), **SQLite** via async SQLAlchemy + aiosqlite, and a Streamlit frontend.

---

## Features

| Area | Detail |
|---|---|
| Agents | Create, list, update AI agents with custom system prompts |
| Sessions | Multi-session chat history linked to an agent |
| Text Chat | User message → ChatCompletion → AI reply (persisted) |
| Voice Chat | Audio upload → Whisper STT → ChatCompletion → TTS → MP3 response |
| Database | SQLite via async SQLAlchemy + aiosqlite |
| Tests | pytest + httpx with fully mocked OpenAI calls |
| Docker | Multi-stage container with non-root user |
| Frontend | Streamlit UI with agent management, chat, and voice recording |

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
├── frontend.py                 # Streamlit UI
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
cp .env.example .env
```

Edit `.env` — the only required value is your OpenAI key:

```env
DATABASE_URL=sqlite+aiosqlite:///./agent_platform.db
OPENAI_API_KEY=sk-...
TTS_VOICE=alloy
APP_ENV=development
```

### 2. Install dependencies

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Start the backend

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The SQLite database (`agent_platform.db`) is created automatically on first startup.  
Open **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Start the frontend

```bash
streamlit run frontend.py
```

Open: [http://localhost:8501](http://localhost:8501)

---

## Running Tests

```bash
pytest tests/ -v
```

Tests use an in-memory SQLite database. **No real OpenAI API calls are made.** Expected: **12 passed** ✅

---

## Docker

### Build & run

```bash
docker build -t agent-platform .
docker run --env-file .env -p 8000:8000 agent-platform
```

> The SQLite database file is stored inside the container. Mount a volume to persist data:
> ```bash
> docker run --env-file .env -p 8000:8000 -v $(pwd)/data:/app/data agent-platform
> ```
> And set `DATABASE_URL=sqlite+aiosqlite:///./data/agent_platform.db` in `.env`.

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
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ❌ | `sqlite+aiosqlite:///./agent_platform.db` | SQLite path |
| `OPENAI_API_KEY` | ✅ | — | OpenAI secret key |
| `TTS_VOICE` | ❌ | `alloy` | TTS voice (`alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`) |
| `APP_ENV` | ❌ | `development` | `development` auto-creates DB tables on startup |

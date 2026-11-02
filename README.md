# SupportFlow AI

> Production-oriented portfolio demo. Status: **Phase 1, project skeleton**

[![CI](https://github.com/UygarYildiz/SupportFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/UygarYildiz/SupportFlow/actions/workflows/ci.yml)

SupportFlow AI is a support operations platform for e-commerce teams. It triages incoming customer tickets, looks up order and customer data, applies company policy, and drafts replies and action proposals with the evidence they are based on. The AI never changes anything on its own: every state-changing action (address change, refund request) is a proposal that an authorized employee approves, and a deterministic, idempotent executor applies it exactly once with a full audit trail.

The demo runs against **NovaShop**, a fictional online store with synthetic data only.

## Documentation

- [Requirements](docs/REQUIREMENTS.md): problem, roles, access model, scenarios, scope
- [Architecture](docs/ARCHITECTURE.md): components, layers, key flows
- [Decisions](docs/DECISIONS.md): architecture decision records

## Tech stack

FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL · LangGraph · Gemini API · React · TypeScript · Vite · Docker Compose · GitHub Actions

## Run locally

Prerequisites: [Docker](https://docs.docker.com/get-docker/), [uv](https://docs.astral.sh/uv/), Node.js 24+.

```bash
git clone https://github.com/UygarYildiz/SupportFlow.git
cd SupportFlow
cp .env.example .env
```

**Option A: everything in containers**

```bash
docker compose up --build
```

**Option B: database in Docker, apps on the host** (faster reloads)

```bash
docker compose up -d db

cd backend
uv sync
uv run poe migrate
uv run poe dev          # http://localhost:8000  (API docs: /docs)

cd ../frontend          # in a second terminal
npm install
npm run dev             # http://localhost:5173
```

Open http://localhost:5173. The status page shows whether the API and the database are reachable.

Postgres is published on host port **5433** so it doesn't collide with a locally installed Postgres. Change `POSTGRES_HOST_PORT` and the URLs in `.env` if needed.

## Development

| Task | Command (backend: run in `backend/`) |
|---|---|
| All backend checks (what CI runs) | `uv run poe check` |
| Tests | `uv run poe test` |
| A single test | `uv run pytest tests/test_health.py::test_health_returns_ok_without_touching_dependencies` |
| Lint / format / type check | `uv run poe lint` · `uv run poe format` · `uv run poe typecheck` |
| New migration | `uv run alembic revision --autogenerate -m "describe change"` |
| Frontend checks (in `frontend/`) | `npm run lint` · `npm run typecheck` · `npm run build` |

Tests marked `db` use the separate `supportflow_test` database, which is created automatically when the compose Postgres volume is first initialized.

The demo video and screenshots will be added as the project progresses.

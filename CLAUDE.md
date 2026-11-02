# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

Phases 0–2 are done: FastAPI app with demo JWT auth (`agent_user`/`admin`), customers/orders/tickets/ticket_events with Alembic migrations, ticket state machine and NovaShop policy rules in `app/domain/`, services in `app/services/`, `/api/v1` routers, an idempotent demo seed, a Vite + React status page, Docker Compose and GitHub Actions CI. No AI code yet (Phase 3 next). `ROADMAP.md` (Turkish) is the plan and phase tracker; `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md` and `docs/DECISIONS.md` (English) define scope, module boundaries and ADRs.

SupportFlow AI is a portfolio project: a customer-support operations platform for a fictional e-commerce company (**NovaShop**). It classifies incoming tickets, looks up mock order/CRM data and company policies, drafts replies and action proposals, and routes any state-changing action through human approval. Use only synthetic data, never real customer data.

## How work is organized

- Work proceeds phase by phase (Faz 0–12 in `ROADMAP.md`), grouped into Block A (MVP: Phases 0–6 + 11-A, released as `v0.1.0`), Block B (RAG, MCP, live deploy) and Block C (optional: n8n, advanced hardening, V2). **Do not add a later phase's technology early.** For example: no RAG/pgvector before Phase 7, no MCP before Phase 8, no n8n before Phase 9, no Redis/Celery unless a real need appears.
- **Everything in the repo is in English** (code, comments, commits, docs, UI). `ROADMAP.md` is the owner's personal plan and stays in Turkish. Converse with the user in Turkish.
- Take on one issue or one vertical slice at a time. Before coding, present a 5–10 step plan and the files that will change.
- **Keep `ROADMAP.md` in sync with the work:** tick `[ ]` → `[x]` yourself as items are actually completed and verified, and add or adjust items when plans change. Don't tick anything that wasn't verified.
- **End every task with a short summary report in Turkish:** what was done, changed files, actual test/command output, roadmap items ticked, known risks or open points, how to verify manually, and the next step. The owner relies on these reports to keep the project context.
- Record architectural choices as short ADRs in `docs/DECISIONS.md`.
- Each phase ends with a commit whose message is suggested in the roadmap (e.g. `feat: implement ticket and mock order domain`).
- Architectural decisions live in `docs/DECISIONS.md` (ADR-001…ADR-010). Don't contradict them without writing a new ADR.
- Dev machine: Windows 11. uv, Node.js and git are installed; Python versions are managed by uv. Remote: `https://github.com/UygarYildiz/SupportFlow` (`main`).

## Stack

Python 3.12 with **uv** (`uv.lock` committed), FastAPI + Pydantic, **sync** SQLAlchemy 2 + psycopg 3 + Alembic (ADR-004), PostgreSQL (later pgvector), LangGraph, React + TypeScript + Vite (Tailwind from Phase 6), pytest + httpx, Ruff + Pyright, oxlint for the frontend, Docker Compose, GitHub Actions. LLM provider is the **Gemini API** via the `google-genai` SDK behind an `LLMClient` interface; model name comes from `GEMINI_MODEL` (ADR-009). The SDK may only be imported inside `app/agent/` adapters. The Python backend needs a container host. Don't assume it runs on Cloudflare Workers (only the frontend may go to Cloudflare Pages).

Target layout (create modules when their phase starts): `backend/app/{api,core,db,domain,services,integrations,agent,rag,schemas}`, `backend/tests/{unit,integration,agent,fixtures}`, `backend/scripts/seed_demo.py`, `frontend/src/...`, `docs/`, `evals/`, `automation/` (n8n exports).

## Architecture invariants (non-negotiable)

These span multiple modules and are the core of the project:

- **Modular monolith.** Domain rules live in `domain/` and `services/`, never in route files or agent nodes. `domain/` and `services/` must not import LangGraph or n8n, so they stay testable without the agent.
- **LLM output is an untrusted suggestion.** The agent only produces an `ActionProposal`. It never performs writes. Every external write goes through a single action executor that enforces deterministic policy, server-side RBAC and a recorded human approval (ADR-002).
- **Treat as data, never as instructions:** ticket text, RAG documents, MCP tool results and webhook payloads. Prompt injection must not escalate privileges or trigger actions.
- **Never fabricate.** For a nonexistent or inaccessible order, return 404 / `needs_info` / human review. Backend verifies any IDs the model cites as evidence.
- **Idempotency.** LangGraph may re-run nodes after interrupt/resume, so side-effecting steps must be idempotent: `idempotency_key` + DB unique constraint + transaction. Double approvals, webhook replays and double-clicks must yield exactly one side effect (409 or an idempotent response).
- **Approval happens outside the graph (ADR-006).** The LangGraph run persists a `pending` `ActionProposal` and ends. It never waits on `interrupt()` in the MVP. `POST /api/v1/proposals/{id}/decision` calls the domain `ActionExecutor` directly. `app/agent/` must not import the executor. Pending approvals live in the business DB, so they survive restarts. After approval, re-check current order state (TOCTOU). Use optimistic locking via `expected_proposal_version`. Proposal payloads are immutable once approved. Expired proposals never auto-execute. On an unknown external outcome, reconcile rather than blindly retry.
- **Analysis runs are background jobs (ADR-005).** `POST /tickets/{id}/analyze` writes an `agent_runs` row (`queued`), returns 202 + `run_id`, and an in-process worker executes it. A partial unique index allows one active run per ticket (409 otherwise). On startup, runs left `running` are marked `failed` with reason `interrupted`.
- **Agent tools are scoped to the ticket's customer.** Take `customer_id` from run state, never from LLM-supplied arguments. An order belonging to another customer → `not_found`.
- **Auth from Phase 2 (ADR-007):** seeded users, short-lived JWT, `get_current_user` / `require_role` dependencies on every endpoint except `/health` and `/ready`. Roles are `agent_user` and `admin`. Action-type → approver-role rules live in `domain/` (e.g. refunds require `admin`).
- **Ticket and proposal statuses are separate (ADR-008).** Ticket: `new → triaging → awaiting_review → resolved`, plus `needs_info`, `failed`. Proposal: `pending → approved → executing → executed | failed`, `pending → rejected | expired`. Invalid transitions return 409.
- `LLM_MODE=fake|live`: tests, CI and the public demo use `fake`.
- **MCP** (Phase 8) is a read-only adapter over the same authorized services. **n8n** (Phase 9) only connects external events and notifications. The backend owns all business rules, and the ticket system must work with n8n down.
- **Tests never call a paid LLM API.** Use the fake/stub `LLMClient` adapter. Mock all external services.
- Every request, agent run and job carries `correlation_id` / `ticket_id` / `run_id`. Redact PII and secrets from logs.

## Acceptance targets

Scenarios S1–S6 (§1.3), the access model (§1.5) and test matrix TC-01…TC-20 (§6) in `ROADMAP.md` define expected behavior. Convert them into backend integration tests and `evals/scenarios.jsonl`. P0 cases (unapproved action never executes, double approval yields one action, no fabricated orders, cross-customer access denied, injection doesn't escalate) are mandatory regression tests.

## Commands

Local Postgres runs in Docker on host port **5433** (5432 is taken on the dev machine). `.env` lives in the repo root and is read by `app/core/config.py`. Docker commands work from PowerShell; the Git Bash shell may not have `docker` on PATH.

```bash
docker compose up -d db              # Postgres only (creates supportflow + supportflow_test DBs)
docker compose up --build            # db + backend (:8000) + frontend (:5173)

# backend/ (uv + poethepoet tasks defined in pyproject.toml)
uv run poe check                     # ruff lint + format check + pyright + pytest (what CI runs)
uv run poe test                      # pytest; tests marked `db` need the compose Postgres
uv run pytest tests/integration/test_tickets.py::test_list_filters_and_paginates   # single test
uv run poe dev                       # uvicorn --reload on :8000
uv run poe migrate                   # alembic upgrade head
uv run poe seed [--reset]            # idempotent NovaShop demo data (password: DEMO_USER_PASSWORD)
uv run pytest -m "not db"            # unit tests only, no Docker needed
uv run alembic revision --autogenerate -m "..."

# frontend/
npm run dev | npm run lint | npm run typecheck | npm run build
```

Code conventions (backend):
- Request flow: router (`app/api/v1/*`, thin) → service (`app/services/*`, owns the transaction and calls `commit()`) → domain (`app/domain/*`, pure Python, no SQLAlchemy/FastAPI).
- Services raise domain errors (`NotFoundError`, `InvalidStateTransitionError`, `BusinessRuleViolationError`); `app/api/errors.py` maps them to 404/409/422. Don't raise `HTTPException` from services.
- Auth dependencies live in `app/api/deps.py`: `CurrentUser`, `StaffUser` (any staff role), `AdminUser`. Every new business endpoint must take one of them.
- Enums are `StrEnum`s in `app/domain/enums.py`, stored via `app.db.types.str_enum` (VARCHAR + CHECK, ADR-010).
- Anything acting on behalf of a ticket (agent tools, policy checks) must use `OrderService.get_customer_order(customer_id, order_id)`, never `get_order`.
- Policy rules take the current time as a parameter (`PolicyService(clock=...)`). Don't call `datetime.now()` inside domain code.

Testing conventions:
- `app.main.create_app()` is the factory; tests override dependencies via `app.dependency_overrides`.
- `tests/unit/` is pure (no DB). `tests/integration/` uses the `db_session` fixture: one transaction per test, rolled back at the end (service `commit()`s become savepoints). The session start migrates the test DB from base to head. Tests using the DB are auto-marked `db`.
- Build data with `tests/factories.py` (`make_user`, `make_customer`, `make_order`, `make_ticket`). Authenticate with the `admin`/`agent` fixtures plus `auth_headers(user)`.
- DB tests point at `TEST_DATABASE_URL`. Never point tests at the dev database.
- New ORM model modules must be imported in `alembic/env.py` for autogenerate to see them. `tests/test_migrations.py` checks that upgrade/downgrade round-trips.
- The frontend calls the backend only through `src/lib/api.ts`. Vite proxies `/api`, `/health` and `/ready` to the backend, so no CORS setup is needed in dev.

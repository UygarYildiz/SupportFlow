# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

Phases 0–6 are done (MVP): backend (auth, tickets/orders, LangGraph analysis, approvals with an idempotent executor, audit) and a React dashboard (`frontend/`, design in `docs/DESIGN.md`). The owner's first design review is done (role-aware overview, see the review log in `docs/DESIGN.md`), and scenario evals exist (`evals/scenarios.jsonl`, `uv run poe eval`). Phase 11-A is in progress: CI and README are done; the Turkish localization and the documentation system (docs map, API/development/operations guides, glossary, CHANGELOG, CONTRIBUTING, PR template, `poe docs` drift check) are done. Turkish screenshots, a live eval on the Turkish set (13/13) and `docs/DEMO_SCRIPT.md` (rehearsed end to end) are done. Left: the demo video (recorded by the owner) and its README link, branch protection, making the repo public, release v0.1.0. `ROADMAP.md` is the plan and phase tracker; `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md` and `docs/DECISIONS.md` define scope, module boundaries and ADRs.

## How work is organized

- Work proceeds phase by phase (Faz 0–12 in `ROADMAP.md`), grouped into Block A (MVP: Phases 0–6 + 11-A, released as `v0.1.0`), Block B (RAG, MCP, live deploy) and Block C (optional: n8n, advanced hardening, V2). **Do not add a later phase's technology early.** For example: no RAG/pgvector before Phase 7, no MCP before Phase 8, no n8n before Phase 9, no Redis/Celery unless a real need appears.
- Use only synthetic data (fictional NovaShop), never real customer data.
- **Language: Turkish-first for everything a reader or user sees.** The project is open source and presented to Turkish employers. In Turkish: `README.md`, `docs/`, UI copy, API error messages and policy reasons, NovaShop demo data (customers, ticket messages), model-written drafts/summaries, eval scenario texts, release notes and PR descriptions. In English: code identifiers, code comments, commit messages, enum values, log keys, and the `CLAUDE.md` files (they are instructions for Claude). Converse with the user in Turkish.
- Take on one issue or one vertical slice at a time. Before coding, present a 5–10 step plan and the files that will change.
- **Keep `ROADMAP.md` in sync with the work:** tick `[ ]` → `[x]` yourself as items are actually completed and verified, and add or adjust items when plans change. Don't tick anything that wasn't verified.
- **Keep the docs current as part of every task, not afterwards.** `docs/README.md` is the docs map: each fact has one home, and its "Ne değişince ne güncellenir" table says which documents a change touches (new endpoint → `docs/API.md`, new env var → `.env.example` + `docs/OPERATIONS.md`, new control → `docs/SECURITY.md`, new term → `docs/GLOSSARY.md`, user-visible change → `CHANGELOG.md` "Yayınlanmamış", etc.). Link instead of copying. `uv run poe docs` (also run by `poe check` via `tests/unit/test_docs.py`) fails on broken links/anchors, API drift against OpenAPI, unknown ADR numbers and unmapped docs; a new doc under `docs/` must be added to the map.
- **End every task with a short summary report in Turkish:** what was done, changed files, actual test/command output, docs updated, roadmap items ticked, known risks or open points, how to verify manually, and the next step. The owner relies on these reports to keep the project context.
- Each phase ends with a commit whose message is suggested in the roadmap (e.g. `feat: implement ticket and mock order domain`).
- Architectural decisions live in `docs/DECISIONS.md` (ADR-001…ADR-014). Threats and the tests that prove each control are in `docs/SECURITY.md`; keep it in sync when adding controls. Don't contradict them without writing a new ADR.
- Dev machine: Windows 11. uv, Node.js and git are installed; Python versions are managed by uv. Remote: `https://github.com/UygarYildiz/SupportFlow` (`main`).

## Stack

The Python backend needs a container host; don't assume it runs on Cloudflare Workers (only the frontend may go to Cloudflare Pages). Package versions and tools are in `backend/pyproject.toml` and `frontend/package.json`; key choices are recorded as ADRs.

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
uv run poe seed [--reset]            # idempotent NovaShop demo data (password: DEMO_USER_PASSWORD)
uv run pytest -m "not db"            # unit tests only, no Docker needed
uv run poe dev                       # uvicorn --reload on :8000
uv run poe migrate                   # alembic upgrade head
uv run poe docs                      # docs drift check (links, anchors, API.md vs OpenAPI, ADRs, docs map)
uv run alembic revision --autogenerate -m "..."

# frontend/
npm run dev | npm run lint | npm run typecheck | npm test | npm run build   # CI runs lint, typecheck, test, build
npm run gen:api                      # regenerate src/api/schema.d.ts from the running backend's OpenAPI
```

Module-specific conventions load automatically from `backend/CLAUDE.md` and `frontend/CLAUDE.md` when working in those directories.

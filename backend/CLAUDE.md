# Backend conventions

Loaded when working under `backend/`. Project-wide rules and architecture invariants are in the root `CLAUDE.md`.

## Code

- Request flow: router (`app/api/v1/*`, thin) → service (`app/services/*`, owns the transaction and calls `commit()`) → domain (`app/domain/*`, pure Python, no SQLAlchemy/FastAPI).
- Services raise domain errors (`NotFoundError`, `InvalidStateTransitionError`, `BusinessRuleViolationError`); `app/api/errors.py` maps them to 404/409/422. Don't raise `HTTPException` from services.
- Auth dependencies live in `app/api/deps.py`: `CurrentUser`, `StaffUser` (any staff role), `AdminUser`. Every new business endpoint must take one of them.
- Enums are `StrEnum`s in `app/domain/enums.py`, stored via `app.db.types.str_enum` (VARCHAR + CHECK, ADR-010).
- Anything acting on behalf of a ticket (agent tools, policy checks) must use `OrderService.get_customer_order(customer_id, order_id)`, never `get_order`.
- `app/agent/` may import services and domain; `domain/` and `services/` must never import `app/agent/` or the Google SDK. Only `app/agent/llm/gemini.py` imports `google.genai`.
- The graph's model outputs are `IntentClassification` and `DraftReply` (`app/agent/schemas.py`), parsed in `AnalysisGraph._ask`; never store or log raw model output. Bump `PROMPT_VERSION` in `app/agent/prompts.py` whenever prompt wording changes.
- Keep decisions out of the model: order scope (`_focus_order`), policy (`check_policy`), action proposals (`plan_action`) and evidence (`assemble_result`) are pure code with unit tests. New graph nodes return `(state_update, step_summary)`; the summary goes to `agent_run_steps`, so keep it small and free of customer text.
- Agent tools must go through the allowlist in `app/agent/tools.py` and stay read-only and customer-scoped. Adding a tool means adding it to `ALLOWED_TOOLS`, `DatabaseTools` and `tests.fakes.InMemoryTools`.
- Default model `gemini-3.5-flash-lite` (free-tier quota; `gemini-3.8-flash` hit 429 quickly, 2.5 models are 404 for new users). When calling the live API from scripts, space requests out (a few seconds apart) to stay within free-tier limits.
- State changes to orders happen only in `app/integrations/mock_orders.py`, called only from `ProposalService._execute` after an approval. Never add another write path, and never let `app/agent/` import `app.integrations`, `ProposalService` or the executor (a test enforces this).
- Every proposal transition goes through `ProposalService._move` (status check + `version += 1`) and writes a ticket event and an audit entry in the same transaction. Audit `details` pass through `redact()`; `audit_logs` is append-only at the database level.
- Policy rules take the current time as a parameter (`PolicyService(clock=...)`). Don't call `datetime.now()` inside domain code.

## Tests

- `app.main.create_app()` is the app factory; tests override dependencies via `app.dependency_overrides`.
- `tests/unit/` is pure (no DB). `tests/integration/` uses the `db_session` fixture: one transaction per test, rolled back at the end (service `commit()`s become savepoints). The session start migrates the test DB from base to head. Tests using the DB are auto-marked `db`.
- Analysis tests: the `app` fixture runs background tasks synchronously against the test session and uses `llm_slot.client` (default `FakeLLMClient`). Swap it with `tests.fakes.ScriptedLLMClient(intent_output(...), draft_output(...))`; each analysis makes two calls in that order (unless it fails earlier). Graph unit tests use `InMemoryTools` and `ListRecorder` (no DB). Tests never call Gemini.
- `make_proposal(session, ticket, order, ...)` creates a pending proposal as an analysis would. In tests that edit data and then hit an endpoint that may `rollback()` (409 paths), `db_session.commit()` the edit first; otherwise the rollback reverts it with the request's savepoint.
- Build data with `tests/factories.py` (`make_user`, `make_customer`, `make_order`, `make_ticket`). Authenticate with the `admin`/`agent` fixtures plus `auth_headers(user)`.
- DB tests point at `TEST_DATABASE_URL`. Never point tests at the dev database.
- New ORM model modules must be imported in `alembic/env.py` for autogenerate to see them. `tests/integration/test_migrations.py` checks that upgrade/downgrade round-trips.

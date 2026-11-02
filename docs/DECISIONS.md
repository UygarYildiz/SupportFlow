# Architecture Decision Records

Each record: decision, reason, alternatives, and when to revisit.

## ADR-001: Modular monolith

**Decision:** One FastAPI application with separate `domain`, `services`, `agent`, `integrations` and `api` modules and enforced dependency rules (see [ARCHITECTURE.md](ARCHITECTURE.md)).
**Reason:** Keeps operational complexity low for a single developer while preserving clear boundaries that can be split later.
**Alternatives:** Microservices (rejected: deployment and consistency overhead with no current benefit).
**Revisit when:** Components need independent scaling or separate teams own them.

## ADR-002: The LLM cannot perform write actions

**Decision:** The agent only creates `ActionProposal` records. A deterministic `ActionExecutor` applies changes after verifying the approver's role, the policy and the current state.
**Reason:** Prevents unauthorized, duplicated or hallucination-driven changes. An agent's request is never a permission.
**Alternatives:** Letting the model call write tools directly (rejected).

## ADR-003: REST and service interfaces first, MCP later

**Decision:** Domain services are built and tested through Python interfaces and REST endpoints. MCP (Phase 8) is added later as a read-only adapter over the same services.
**Reason:** Keeps the tool protocol from leaking into business logic, and the core works without it.

## ADR-004: Synchronous SQLAlchemy with psycopg 3

**Decision:** The MVP uses synchronous SQLAlchemy 2 with the psycopg 3 driver and Alembic migrations.
**Reason:** Simpler to debug and test; traffic is low. psycopg 3 is also what LangGraph's Postgres checkpointer uses, should we need it later.
**Alternatives:** Fully async stack with asyncpg.
**Revisit when:** Measured concurrency problems appear.

## ADR-005: Analysis runs are persisted background jobs

**Decision:** `POST /tickets/{id}/analyze` inserts an `agent_runs` row with status `queued` and returns `202` with the run ID. An in-process worker executes it. A partial unique index allows one active run per ticket. On startup, runs left `running` are marked `failed` with reason `interrupted`.
**Reason:** Keeps LLM latency out of the HTTP request and avoids extra infrastructure.
**Alternatives:** Synchronous request (rejected: timeouts, poor UX); Celery/RQ with Redis (deferred to V2).
**Revisit when:** Load requires separate worker processes or runs must survive restarts.

## ADR-006: Approval and execution happen outside the agent graph

**Decision:** The graph persists a `pending` proposal and ends. The decision endpoint calls the `ActionExecutor` in the domain layer. Pending approvals are stored in the business database, not in a graph checkpoint.
**Reason:** No graph node re-runs after approval, so duplicate side effects are impossible by design. Pending approvals survive restarts, and the executor is testable without the agent.
**Alternatives:** LangGraph `interrupt()` with a Postgres checkpointer and resume after approval (deferred to V2).
**Revisit when:** The agent must continue multi-step work after a human decision.

## ADR-007: Demo authentication from Phase 2

**Decision:** Seeded users, short-lived JWTs, and `get_current_user` / `require_role` FastAPI dependencies on every endpoint except `/health` and `/ready`. Roles: `agent_user`, `admin`. Approver roles per action type are defined in `domain/`.
**Reason:** Approval and data-access rules are testable from the start; adding auth late would mean rewriting services.
**Alternatives:** External identity provider (required for production, out of scope for the demo).

## ADR-008: Ticket and proposal statuses are separate

**Decision:** `approved` / `rejected` are proposal statuses only. The ticket has its own lifecycle, and one ticket can have several proposals.
**Reason:** Mixing two lifecycles in one status field leads to inconsistent states.

## ADR-009: Gemini API as the LLM provider

**Decision:** Use the Gemini API through Google's official `google-genai` Python SDK, behind an `LLMClient` interface (`generate_structured`, timeout, retry, token usage). Structured output uses a JSON schema derived from Pydantic models, and every response is still validated with Pydantic. The model name is configuration (`GEMINI_MODEL`). Phase 3 pins a specific version instead of a `-latest` alias, so the model cannot change underneath tests and evals. Default: `gemini-3.5-flash-lite`. On 2026-11-02 the free-tier quota of `gemini-3.8-flash` was exhausted after a few dozen calls (HTTP 429) and older models returned 404 for new users; the lite model keeps development within the free quota. Switching models is a configuration change only. `LLM_MODE=fake` uses a deterministic `FakeLLMClient` for tests, CI and the public demo.
**Reason:** Native structured output support, a free tier suitable for development, and a single provider keeps the adapter simple.
**Consequences:** Free-tier terms may allow the provider to use submitted data; this is acceptable only because all data is synthetic. Never send real customer data. The API key lives only in server-side environment variables.
**Alternatives:** Other providers remain possible by implementing `LLMClient`; no domain or route code depends on the SDK.

## ADR-010: Persistence conventions

**Decision:**
- Customers and orders keep the string IDs of the (mock) external system (`CUS-0001`, `ORD-1001`). Tickets and users, which this system owns, use integer identity keys.
- Status enums are stored as `VARCHAR` with a `CHECK` constraint, not native PostgreSQL enums.
- A ticket's order must belong to the ticket's customer. The service checks it, and a composite foreign key `(order_id, customer_id) → orders(id, customer_id)` enforces it in the database as well.
- Services own the unit of work and commit; route handlers never touch the session directly.
- Timestamps are timezone-aware UTC.

**Reason:** Readable external IDs are what customers and the LLM will reference ("ORD-1001"). `CHECK` constraints keep integrity without `ALTER TYPE` migrations when values are added. Ownership is a security rule, so it gets a database-level guarantee in addition to application code.
**Alternatives:** UUIDs everywhere (less readable in demos and prompts); native enums (harder to evolve).

## ADR-011: Analysis graph with deterministic decisions around two model calls

**Decision:** The analysis is a LangGraph state graph (`app/agent/graph.py`) with nine nodes. Only two call the model: `classify` (intent, referenced order, requested address) and `draft` (summary and reply). Everything that decides something is plain code:
- which order is in scope (the model's order reference is used only if the customer actually wrote that ID);
- which policy applies to which category, and its result (`PolicyService`);
- whether an action may be proposed (`plan_action`: policy must allow it, and never when the message contains instructions aimed at the system);
- which cited evidence is valid (`assemble_result`).

Tools are an explicit allowlist (`get_order`, `get_customer_orders`, `get_customer_tickets`, `get_policy`) bound to the ticket's customer from the database. The model does not choose tools; nodes call them. Every node is recorded in `agent_run_steps` (duration, small summary, tool calls). Limits: graph step limit, token budget per run, run deadline. No checkpointer is used (ADR-006).

**Reason:** A model call can be wrong, fooled or unavailable. Keeping it to classification and wording makes every consequential decision testable without a model, explainable in the UI and identical across providers. Two focused calls are cheaper and easier to validate than one large prompt or free tool use.
**Alternatives:** One prompt doing everything (Phase 3; harder to control and explain); a ReAct-style agent choosing its own tools (more flexible, but authorization and determinism become harder to guarantee; reconsider for V2 read-only research tasks).

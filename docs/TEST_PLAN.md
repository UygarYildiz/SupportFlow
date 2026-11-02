# Test plan

How the requirements are verified. Backend tests run against a real PostgreSQL test database (each test in a rolled-back transaction); no test calls the paid LLM API.

```bash
cd backend && uv run poe check        # lint, format, types, 132 tests
cd frontend && npm test               # 17 component tests (Vitest + Testing Library)
```

## Scenarios (docs/REQUIREMENTS.md section 5)

| Scenario | Verified by |
|---|---|
| S1 Where is my order | `test_analysis_records_every_graph_step` (policy check, verified evidence, no action) |
| S2 Damaged item → refund request | `test_allowed_refund_cases_propose_a_refund_request`, `test_agent_user_cannot_decide_a_refund_but_admin_can` |
| S3 Address change | `test_allowed_address_change_produces_a_pending_proposal`, `test_ticket_to_ai_proposal_to_approval_to_single_change` |
| S4 Unknown order | `test_unknown_and_foreign_orders_lead_to_needs_info`, `test_order_request_without_a_usable_order_asks_for_it_and_skips_policy` |
| S5 Refund outside the window | `test_refund_outside_the_return_window_gets_no_proposal` |
| S6 Previous request | `test_previous_tickets_reach_the_draft_for_follow_ups` |

## Test matrix (ROADMAP §6)

| ID | Case | Status | Verified by |
|---|---|---|---|
| TC-01 | Address change on unshipped order → pending proposal | Covered | `test_allowed_address_change_produces_a_pending_proposal` |
| TC-02 | Approved → address updated once, audit written | Covered | `test_approval_executes_the_change_exactly_once`, `test_audit_trail_is_redacted_admin_only_and_append_only` |
| TC-03 | Rejected → address unchanged | Covered | `test_reject_ends_the_proposal_without_any_change` |
| TC-04 | Approved twice → one action | Covered | `test_second_approval_is_rejected_and_changes_nothing`, `test_idempotency_key_prevents_a_second_effect_even_if_called_again` |
| TC-05 | Order ships before approval → blocked with reason | Covered | `test_order_shipped_after_proposal_blocks_the_address_change` |
| TC-06 | Unknown order → `needs_info`, nothing invented | Covered | `test_unknown_and_foreign_orders_lead_to_needs_info` |
| TC-07 | Another customer's order → no leak | Covered | `test_database_tools_are_scoped_to_one_customer`, `test_scoped_lookup_treats_another_customers_order_as_missing` |
| TC-08 | Invalid model JSON → controlled failure | Covered | `test_invalid_model_output_is_a_controlled_failure`, `test_invalid_model_output_fails_the_run_safely_and_allows_retry` |
| TC-09 | LLM timeout → retries, then failed run | Covered | `test_transient_errors_are_retried_with_growing_backoff`, `test_llm_outage_fails_the_run_with_a_stable_code` |
| TC-10 | Prompt injection "act as admin" | Covered | `test_prompt_injection_changes_nothing_but_the_analysis` |
| TC-11 | Malicious instructions in a policy source | Phase 7 (RAG) | |
| TC-12 | Webhook replay | Phase 9 (n8n) | |
| TC-13 | Restart while an approval is pending | Covered | `test_ticket_to_ai_proposal_to_approval_to_single_change`, `test_restart_between_decision_and_execution_is_reconciled_once` |
| TC-14 | MCP tool with unauthorized order | Phase 8 (MCP) | |
| TC-15 | Policy version changed | Phase 7 (RAG) | |
| TC-16 | Database unreachable → `/ready` 503 | Covered | `test_ready_returns_503_when_database_is_unreachable` |
| TC-17 | Two concurrent analyses → one runs | Covered | `test_second_analysis_request_while_queued_is_rejected`, `test_database_allows_only_one_active_run_per_ticket` |
| TC-18 | Model passes another customer's order ID | Covered | `test_model_cannot_point_the_agent_at_an_order_the_customer_never_mentioned`, `test_database_tools_are_scoped_to_one_customer` |
| TC-19 | Agent user approves a refund → 403 | Covered | `test_agent_user_cannot_decide_a_refund_but_admin_can` |
| TC-20 | Restart during a run | Covered | `test_restart_marks_unfinished_runs_as_interrupted` |

## Frontend (Phase 6 acceptance)

| Requirement | Verified by |
|---|---|
| Empty list shows a meaningful message | `TicketsPage.test.tsx`: explains an empty inbox |
| API error is never shown as success | `TicketsPage.test.tsx`: clear error; `ProposalCard.test.tsx`: conflict instead of success |
| Double submit is blocked; the shown version is sent | `ProposalCard.test.tsx`: blocks a second click while applying |
| Unauthorized roles get no decision buttons (the API also refuses: TC-19) | `ProposalCard.test.tsx`: no decision buttons |
| Wrong credentials explained | `LoginPage.test.tsx` |
| Overview counts link to the filtered list | `DashboardPage.test.tsx`: links each status count |
| Role difference is visible: agents see refunds as "waiting for an admin", admins decide them and see the audit trail | `DashboardPage.test.tsx`: agent never asks for the audit trail; admin gets every decision; `ProposalCard.test.tsx`: "Admin only" marker |
| Demo data shows both roles at work, through the real analysis/approval path and without a paid model | `test_seed.py::test_demo_activity_shows_both_approval_roles_and_is_idempotent` |

Visual checks are done with screenshots at 1440px and 390px wide (login, overview as agent and as admin, tickets, ticket detail in each state, approvals, stamp after decision).

## Known gaps

- No browser end-to-end tests in CI yet (Phase 10).
- No load or concurrency tests beyond row locks and unique constraints.
- Live-model quality is checked manually with the scenario tickets; there is no automated eval set yet (Phase 7/10).

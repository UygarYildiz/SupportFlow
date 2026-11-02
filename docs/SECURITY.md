# Security

SupportFlow AI lets a language model read customer messages and suggest changes to orders. The design assumes the model can be **wrong, fooled or unavailable**, and that ticket text can be **hostile**. This document lists the threats considered, the controls in place and the tests that prove them. It is a portfolio demo with synthetic data; production gaps are listed at the end.

## Trust model

| Source | Trusted? | Handling |
|---|---|---|
| Ticket subject and message | No | Treated as data inside delimiter tags it cannot close; never used for authorization |
| Model output | No | Validated against strict schemas; used only for classification, parameters and wording |
| Model-cited order IDs | No | Kept only if retrieved for this customer; others dropped and flagged |
| Tool results (orders, policy) | Yes (our own database) | Read-only and scoped to the ticket's customer |
| Staff identity and role | Yes, after authentication | Re-read from the database on every request |

## Threats and controls

| # | Threat | Controls | Verified by |
|---|---|---|---|
| T1 | **Prompt injection**: the ticket tells the model to act as admin, refund everything, change addresses | Customer text is delimited and neutralized; both prompts state it is untrusted. The model cannot act: actions are decided by `plan_action` (policy must allow; never when `instructions_aimed_at_system`). Even a fooled model only produces a draft that a human reviews. | `test_prompt_injection_changes_nothing_but_the_analysis`, `test_customer_text_cannot_break_out_of_its_delimiters`, `test_instructions_aimed_at_the_system_never_produce_an_action` |
| T2 | **Action without approval** | The agent has no write tools; `app/agent/` cannot import execution code. Proposals start `pending`; only `POST /proposals/{id}/decision` with `approve` reaches the executor. | `test_proposal_alone_never_changes_anything`, `test_analysis_never_modifies_orders`, `test_agent_code_cannot_reach_the_executor` |
| T3 | **Unauthorized approval** (e.g. an agent user approving a refund) | Approver roles per action type in `app/domain/proposals.py`, enforced server-side before any state is revealed (403). The UI hint `can_decide` is informational only. | `test_agent_user_cannot_decide_a_refund_but_admin_can`, `test_admin_only_endpoint_rejects_agent_users` |
| T4 | **Double execution** (double click, two reviewers, retries, restart mid-way) | Optimistic locking (`expected_version`) and row lock on the proposal; status machine with final states; idempotency key per proposal with a unique constraint; one execution row per proposal; startup reconciliation re-applies at most once. | `test_second_approval_is_rejected_and_changes_nothing`, `test_idempotency_key_prevents_a_second_effect_even_if_called_again`, `test_restart_between_decision_and_execution_is_reconciled_once` |
| T5 | **Time of check vs. time of use**: the order ships between proposal and approval | The order system locks the order and re-checks the policy right before changing it; a failed re-check ends the proposal as `failed` with the reason. | `test_order_shipped_after_proposal_blocks_the_address_change` |
| T6 | **Proposal tampering** after review (payload changed in the database) | SHA-256 fingerprint of type, order and payload stored at creation and verified before execution; mismatch → 409 and an `proposal.integrity_failed` audit entry. | `test_tampered_payload_cannot_be_executed` |
| T7 | **Stale decisions** (approving something nobody looked at for days) | Proposals expire after `PROPOSAL_TTL_HOURS` (48); expired proposals never execute; a new analysis supersedes older pending proposals. | `test_expired_proposal_never_executes`, `test_one_open_proposal_per_ticket_and_new_analysis_supersedes` |
| T8 | **Cross-customer data leak** (asking about someone else's order) | Every lookup on behalf of a ticket is customer-scoped; a foreign order is indistinguishable from a missing one; a composite foreign key ties ticket and proposal orders to the customer. | `test_unknown_and_foreign_orders_lead_to_needs_info`, `test_database_tools_are_scoped_to_one_customer`, `test_database_also_enforces_order_ownership` |
| T9 | **Fabricated facts** (invented order status, tracking, policy) | Drafts are written only from retrieved facts; unknown orders force `needs_info`; unverified evidence is removed and flagged. | `test_unverified_evidence_is_dropped_and_flags_review`, `test_order_request_without_a_usable_order_asks_for_it_and_skips_policy` |
| T10 | **Audit tampering** | Audit entries are written in the same transaction as the change; a database trigger rejects UPDATE and DELETE on `audit_logs`; read access is admin only. | `test_audit_trail_is_redacted_admin_only_and_append_only` |
| T11 | **Personal data in logs** | Audit details redact address and e-mail fields; raw model output is never stored or logged; step summaries contain IDs and counts, not customer text. | `test_audit_details_redact_personal_data` |
| T12 | **Account discovery and session abuse** | Identical login failure for unknown user, wrong password and inactive account (with constant-time dummy hash); short-lived JWTs; deactivation takes effect immediately; production refuses the development JWT secret. | `test_login_failures_are_indistinguishable`, `test_deactivated_user_loses_access_immediately`, `test_production_refuses_the_development_secret` |
| T13 | **Cost and availability abuse of the LLM** | Public demo runs `LLM_MODE=fake`; per-run token budget, step limit and deadline; retries only for transient errors with backoff; one active analysis per ticket. | `test_token_budget_stops_the_run`, `test_expired_deadline_stops_before_the_next_node`, `test_database_allows_only_one_active_run_per_ticket` |
| T14 | **Secret leakage** | Secrets only in `.env` (git-ignored) or CI secrets; the Gemini key is a `SecretStr` and never logged; provider error messages are not passed through. | Manual check before each commit (diff scanned for key patterns) |

## Known gaps (production would need)

- A real identity provider (OIDC/SSO) and MFA instead of seeded demo users.
- Rate limiting on login and analysis endpoints; request size limits at the edge.
- A database role for the application without `TRUNCATE`/DDL rights, so the audit trail cannot be wiped (the demo reset script truncates on purpose).
- An "unknown outcome" state and reconciliation against a real external system's idempotency API (the mock order system shares our database, so a rolled-back execution is known to have changed nothing).
- Dependency and secret scanning in CI, plus structured security logging (Phase 10).

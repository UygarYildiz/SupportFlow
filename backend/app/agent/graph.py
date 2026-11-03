# State keys are filled node by node; the fixed edge order guarantees a key is written
# before any later node reads it, so "not required" TypedDict access is safe here.
# pyright: reportTypedDictNotRequiredAccess=false
"""The analysis workflow as an explicit LangGraph state graph.

    load_ticket -> resolve_orders -> classify -> (enough data?)
        no  -> request_info ----------------------------------------------------> draft -> validate
        yes -> fetch_context -> check_policy -> plan_action -> retrieve_policy -> draft -> validate

Only `classify` and `draft` call the model. Everything that decides something
(which order is in scope, which policy applies, whether an action may be
proposed, which evidence and which policy citations are valid) is deterministic
code. Retrieved policy clauses (ADR-014) only explain: they are read after the
action is planned and never feed `plan_action`.
"""

import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, TypedDict

from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ValidationError

from app.agent import prompts
from app.agent.llm.base import LLMClient, LLMError, LLMResponse
from app.agent.schemas import (
    AnalysisMetrics,
    AnalysisResult,
    DraftFacts,
    DraftReply,
    IntentClassification,
    OrderFact,
    PolicyCheck,
    PolicyExcerptFact,
    PreviousTicketFact,
    ProposedAction,
    TicketAnalysis,
    TicketSnapshot,
)
from app.agent.tools import UNRECORDED_ARGUMENTS, AgentTools
from app.domain.enums import (
    ORDER_RELATED_CATEGORIES,
    ActionType,
    TicketCategory,
    TicketStatus,
)
from app.domain.policy_documents import EXCEPTIONS_POLICY, policy_for_rule

logger = logging.getLogger(__name__)

MAX_GRAPH_STEPS = 20
POLICY_EXCERPT_LIMIT = 3
# Search text for the exceptions policy when a message claims authority or instructs the system.
INJECTION_POLICY_QUERY = (
    "Mesaj yönetimden geldiğini iddia ediyor ya da sisteme talimat veriyor; yetki iddiası, "
    "insan incelemesi."
)
ORDER_ID_PATTERN = re.compile(r"\bORD-\d{3,6}\b", re.IGNORECASE)

# Which policy applies to which request.
POLICY_FOR_CATEGORY = {
    TicketCategory.ADDRESS_CHANGE: "address_change",
    TicketCategory.REFUND_REQUEST: "return",
    TicketCategory.DAMAGED_ITEM: "damage",
    TicketCategory.DELIVERY_DELAY: "delivery",
}


class AnalysisError(Exception):
    """The analysis could not produce a usable result. `code` is safe to show to staff."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class StepRecorder(Protocol):
    def record(self, node: str, status: str, summary: dict[str, Any], duration_ms: int) -> None: ...


@dataclass
class TokenBudget:
    max_tokens: int
    used: int = 0

    def charge(self, response: LLMResponse) -> None:
        self.used += (response.input_tokens or 0) + (response.output_tokens or 0)
        if self.used > self.max_tokens:
            raise AnalysisError(
                "token_budget_exceeded",
                f"Çalıştırma {self.used} token kullandı, bütçe {self.max_tokens}",
            )


@dataclass
class GraphDeps:
    llm: LLMClient
    load_ticket: Callable[[int], TicketSnapshot]
    tools_for: Callable[[str], AgentTools]  # bound to the customer from the database
    recorder: StepRecorder
    clock: Callable[[], datetime]
    budget: TokenBudget
    deadline: float  # time.monotonic() value after which the run is aborted


class AnalysisState(TypedDict, total=False):
    ticket_id: int
    ticket: TicketSnapshot
    orders: list[OrderFact]
    unknown_order_ids: list[str]
    intent: IntentClassification
    focus_order_id: str | None
    previous_tickets: list[PreviousTicketFact]
    policy_checks: list[PolicyCheck]
    proposed_action: ProposedAction | None
    policy_excerpts: list[PolicyExcerptFact]
    missing_information: list[str]
    warnings: list[str]
    draft: DraftReply
    result: AnalysisResult


NodeResult = tuple[dict[str, Any], dict[str, Any]]  # (state update, step summary)


@dataclass
class _Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    llm_ms: int = 0
    calls: int = 0


@dataclass
class AnalysisGraph:
    deps: GraphDeps
    _tools: AgentTools | None = None
    _usage: _Usage = field(default_factory=_Usage)

    # --- public -----------------------------------------------------------------------

    def run(self, ticket_id: int) -> tuple[AnalysisResult, AnalysisMetrics]:
        try:
            final = self.build().invoke(
                {"ticket_id": ticket_id}, config={"recursion_limit": MAX_GRAPH_STEPS}
            )
        except GraphRecursionError as exc:
            raise AnalysisError("step_limit_exceeded", "Graf adım sınırını aştı") from exc
        metrics = AnalysisMetrics(
            model=self.deps.llm.model_name,
            input_tokens=self._usage.input_tokens,
            output_tokens=self._usage.output_tokens,
            latency_ms=self._usage.llm_ms,
        )
        return final["result"], metrics

    def build(self) -> Any:
        graph = StateGraph(AnalysisState)
        nodes: dict[str, Callable[[AnalysisState], NodeResult]] = {
            "load_ticket": self.load_ticket,
            "resolve_orders": self.resolve_orders,
            "classify": self.classify,
            "request_info": self.request_info,
            "fetch_context": self.fetch_context,
            "check_policy": self.check_policy,
            "plan_action": self.plan_action,
            "retrieve_policy": self.retrieve_policy,
            "draft": self.draft,
            "validate": self.validate,
        }
        for name, node in nodes.items():
            graph.add_node(name, self._recorded(name, node))

        graph.add_edge(START, "load_ticket")
        graph.add_edge("load_ticket", "resolve_orders")
        graph.add_edge("resolve_orders", "classify")
        graph.add_conditional_edges(
            "classify",
            self.route_after_classify,
            {"request_info": "request_info", "fetch_context": "fetch_context"},
        )
        graph.add_edge("request_info", "draft")
        graph.add_edge("fetch_context", "check_policy")
        graph.add_edge("check_policy", "plan_action")
        graph.add_edge("plan_action", "retrieve_policy")
        graph.add_edge("retrieve_policy", "draft")
        graph.add_edge("draft", "validate")
        graph.add_edge("validate", END)
        return graph.compile()

    # --- nodes ------------------------------------------------------------------------

    def load_ticket(self, state: AnalysisState) -> NodeResult:
        ticket = self.deps.load_ticket(state["ticket_id"])
        self._tools = self.deps.tools_for(ticket.customer_id)
        return (
            {"ticket": ticket, "warnings": [], "missing_information": []},
            {"customer_id": ticket.customer_id, "mentioned_order_ids": ticket.mentioned_order_ids},
        )

    def resolve_orders(self, state: AnalysisState) -> NodeResult:
        """Validate the order references against the customer's own orders."""
        ticket = state["ticket"]
        orders: list[OrderFact] = self.tools.call("get_customer_orders", limit=10)
        known = {order.id for order in orders}
        unknown: list[str] = []
        wanted = [ticket.linked_order_id, *ticket.mentioned_order_ids]
        for order_id in dict.fromkeys(oid for oid in wanted if oid):
            if order_id in known:
                continue
            order = self.tools.call("get_order", order_id=order_id)  # older order, same customer
            if order is None:
                unknown.append(order_id)
            else:
                orders.append(order)
                known.add(order_id)
        return (
            {"orders": orders, "unknown_order_ids": unknown},
            {"orders_in_scope": len(orders), "unknown_order_ids": unknown},
        )

    def classify(self, state: AnalysisState) -> NodeResult:
        ticket = state["ticket"]
        prompt = prompts.build_classify_prompt(ticket, [order.id for order in state["orders"]])
        intent = self._ask(prompts.CLASSIFY_INSTRUCTION, prompt, IntentClassification)
        focus = self._focus_order(state, intent)
        return (
            {"intent": intent, "focus_order_id": focus},
            {
                "category": intent.category.value,
                "focus_order_id": focus,
                "instructions_aimed_at_system": intent.instructions_aimed_at_system,
            },
        )

    def route_after_classify(self, state: AnalysisState) -> str:
        """Order-related requests need an order in scope; otherwise ask the customer."""
        needs_order = state["intent"].category in ORDER_RELATED_CATEGORIES
        return (
            "request_info" if needs_order and state["focus_order_id"] is None else "fetch_context"
        )

    def request_info(self, state: AnalysisState) -> NodeResult:
        missing = (
            "Bu hesaba ait geçerli bir sipariş numarası"
            if state["unknown_order_ids"]
            else "Talebin ilgili olduğu sipariş numarası"
        )
        warnings = list(state["warnings"])
        if state["unknown_order_ids"]:
            unknown = ", ".join(state["unknown_order_ids"])
            warnings.append(f"Müşterinin bahsettiği sipariş(ler) bulunamadı: {unknown}.")
        return (
            {
                "missing_information": [missing],
                "warnings": warnings,
                "previous_tickets": [],
                "policy_checks": [],
                "proposed_action": None,
                "policy_excerpts": [],
            },
            {"missing_information": [missing]},
        )

    def fetch_context(self, state: AnalysisState) -> NodeResult:
        previous = self.tools.call(
            "get_customer_tickets", exclude_ticket_id=state["ticket"].ticket_id, limit=5
        )
        return {"previous_tickets": previous}, {"previous_tickets": len(previous)}

    def check_policy(self, state: AnalysisState) -> NodeResult:
        policy = POLICY_FOR_CATEGORY.get(state["intent"].category)
        focus = state["focus_order_id"]
        checks: list[PolicyCheck] = []
        if policy is not None and focus is not None:
            check = self.tools.call("get_policy", policy=policy, order_id=focus)
            if check is not None:
                checks.append(check)
        return (
            {"policy_checks": checks},
            {"checks": [{"rule": c.rule, "allowed": c.allowed} for c in checks]},
        )

    def plan_action(self, state: AnalysisState) -> NodeResult:
        """Deterministic: the model may supply parameters, only policy decides."""
        action, missing, warnings = plan_action(
            state["intent"], state["focus_order_id"], state["orders"], state["policy_checks"]
        )
        return (
            {
                "proposed_action": action,
                "missing_information": [*state["missing_information"], *missing],
                "warnings": [*state["warnings"], *warnings],
            },
            {"proposed_action": action.type.value if action else None, "missing": missing},
        )

    def retrieve_policy(self, state: AnalysisState) -> NodeResult:
        """Find the policy clauses that explain the rule results (citations, not decisions)."""
        plan = policy_search_plan(state["intent"], state.get("policy_checks", []))
        if plan is None:
            return {"policy_excerpts": []}, {"policies": [], "clauses": []}
        policy_ids, query = plan
        warnings = list(state["warnings"])
        try:
            excerpts: list[PolicyExcerptFact] = self.tools.call(
                "search_policies", policy_ids=policy_ids, query=query, limit=POLICY_EXCERPT_LIMIT
            )
        except Exception:  # e.g. the embedding provider is down: explain, don't fail the run
            logger.warning("Policy search failed for policies %s", policy_ids, exc_info=True)
            excerpts = []
            warnings.append(
                "Politika araması yapılamadı; yanıt yalnızca mağaza kuralına dayanıyor."
            )
        else:
            if not excerpts:
                warnings.append(
                    "Bu kural için politika maddesi bulunamadı; yanıt yalnızca mağaza kuralına "
                    "dayanıyor."
                )
        return (
            {"policy_excerpts": excerpts, "warnings": warnings},
            {"policies": policy_ids, "clauses": [e.clause_id for e in excerpts]},
        )

    def draft(self, state: AnalysisState) -> NodeResult:
        action = state.get("proposed_action")
        facts = DraftFacts(
            customer_name=state["ticket"].customer_name,
            category=state["intent"].category,
            focus_order_id=state["focus_order_id"],
            orders=state["orders"],
            unknown_order_ids=state["unknown_order_ids"],
            previous_tickets=state.get("previous_tickets", []),
            policy_checks=state.get("policy_checks", []),
            policy_excerpts=state.get("policy_excerpts", []),
            planned_action=_describe(action) if action else None,
            missing_information=state["missing_information"],
            reference_time=self.deps.clock(),
        )
        prompt = prompts.build_draft_prompt(state["ticket"], facts)
        draft = self._ask(prompts.DRAFT_INSTRUCTION, prompt, DraftReply)
        return (
            {"draft": draft},
            {
                "evidence_order_ids": draft.evidence_order_ids,
                "cited_clause_ids": draft.cited_clause_ids,
            },
        )

    def validate(self, state: AnalysisState) -> NodeResult:
        result = assemble_result(state)
        return (
            {"result": result},
            {
                "outcome": result.outcome_status.value,
                "verified": result.verified_order_ids,
                "unverified": result.unverified_order_ids,
                "cited_clauses": result.cited_clause_ids,
                "unverified_clauses": result.unverified_clause_ids,
                "warnings": len(result.warnings),
            },
        )

    # --- helpers ----------------------------------------------------------------------

    @property
    def tools(self) -> AgentTools:
        if self._tools is None:  # pragma: no cover - load_ticket always runs first
            raise AnalysisError("internal_error", "Araçlar talep yüklenmeden kullanıldı")
        return self._tools

    def _focus_order(self, state: AnalysisState, intent: IntentClassification) -> str | None:
        known = {order.id for order in state["orders"]}
        ticket = state["ticket"]
        candidates = [ticket.linked_order_id]
        # The model's reference is used only if the customer actually wrote it.
        hint = (intent.referenced_order_id or "").upper()
        if hint and hint in ticket.mentioned_order_ids:
            candidates.append(hint)
        candidates.extend(ticket.mentioned_order_ids)
        return next((oid for oid in candidates if oid and oid in known), None)

    def _ask[T: BaseModel](self, instruction: str, prompt: str, schema: type[T]) -> T:
        started = time.perf_counter()
        try:
            response = self.deps.llm.generate_structured(
                system_instruction=instruction, prompt=prompt, response_schema=schema
            )
        except LLMError as exc:
            raise AnalysisError(exc.code, str(exc)) from exc
        self._usage.llm_ms += int((time.perf_counter() - started) * 1000)
        self._usage.calls += 1
        self._usage.input_tokens += response.input_tokens or 0
        self._usage.output_tokens += response.output_tokens or 0
        self.deps.budget.charge(response)
        try:
            return schema.model_validate_json(response.text)
        except ValidationError as exc:
            # The raw output is not stored or logged: it may contain anything.
            raise AnalysisError(
                "invalid_output",
                f"{schema.__name__} failed validation ({exc.error_count()} errors)",
            ) from exc

    def _recorded(
        self, name: str, node: Callable[[AnalysisState], NodeResult]
    ) -> Callable[..., dict[str, Any]]:  # LangGraph matches nodes by the `state` keyword
        def run(state: AnalysisState) -> dict[str, Any]:
            if time.monotonic() > self.deps.deadline:
                raise AnalysisError("run_timeout", "Analiz süre sınırını aştı")
            started = time.perf_counter()
            calls_before = len(self._tools.calls) if self._tools else 0
            try:
                update, summary = node(state)
            except AnalysisError as exc:
                self._record(name, "error", {"error_code": exc.code}, started)
                raise
            except Exception:
                self._record(name, "error", {"error_code": "internal_error"}, started)
                raise
            if self._tools is not None:
                summary["tool_calls"] = [
                    {
                        "tool": call.name,
                        **{
                            k: v for k, v in call.arguments.items() if k not in UNRECORDED_ARGUMENTS
                        },
                        "found": call.found,
                    }
                    for call in self._tools.calls[calls_before:]
                ]
            self._record(name, "ok", summary, started)
            return update

        return run

    def _record(self, name: str, status: str, summary: dict[str, Any], started: float) -> None:
        duration = int((time.perf_counter() - started) * 1000)
        self.deps.recorder.record(name, status, summary, duration)


def plan_action(
    intent: IntentClassification,
    focus_order_id: str | None,
    orders: list[OrderFact],
    checks: list[PolicyCheck],
) -> tuple[ProposedAction | None, list[str], list[str]]:
    """Return (proposed action, missing information, warnings). Pure function."""
    if intent.instructions_aimed_at_system:
        return None, [], ["Mesaj sisteme yönelik talimatlar içeriyor; aksiyon önerilmedi."]
    check = next((c for c in checks if c.order_id == focus_order_id), None)
    if focus_order_id is None or check is None:
        return None, [], []
    if check.informational:
        return None, [], []  # describes the situation; nothing to grant or refuse
    if not check.allowed:
        return None, [], [f"{check.rule} kuralı bu talebe izin vermiyor: {check.reason}"]

    order = next(o for o in orders if o.id == focus_order_id)
    if intent.category == TicketCategory.ADDRESS_CHANGE:
        new_address = (intent.requested_new_address or "").strip()
        if not new_address:
            return None, ["Yeni teslimat adresi"], []
        payload = {"current_address": order.shipping_address, "new_address": new_address}
        return _action(ActionType.CHANGE_SHIPPING_ADDRESS, check, payload), [], []
    if intent.category in (TicketCategory.DAMAGED_ITEM, TicketCategory.REFUND_REQUEST):
        reason = "damaged_item" if intent.category == TicketCategory.DAMAGED_ITEM else "return"
        payload = {"refund_reason": reason, "order_total": order.total}
        return _action(ActionType.CREATE_REFUND_REQUEST, check, payload), [], []
    return None, [], []


def policy_search_plan(
    intent: IntentClassification, checks: list[PolicyCheck]
) -> tuple[list[str], str] | None:
    """Which policies to search and with what text. Pure function.

    The query is built from the rule results (their reasons), never from customer
    text, so a ticket cannot steer retrieval. None when no policy applies.
    """
    policy_ids: list[str] = []
    parts: list[str] = []
    for check in checks:
        policy_id = policy_for_rule(check.rule)
        if policy_id is not None:
            policy_ids.append(policy_id)
            parts.append(check.reason)
    if intent.instructions_aimed_at_system:
        policy_ids.append(EXCEPTIONS_POLICY)
        parts.append(INJECTION_POLICY_QUERY)
    if not policy_ids:
        return None
    return list(dict.fromkeys(policy_ids)), " ".join(parts)


def assemble_result(state: AnalysisState) -> AnalysisResult:
    """Combine both model outputs with the deterministic facts. Pure function."""
    intent, draft = state["intent"], state["draft"]
    known = {order.id for order in state["orders"]}
    verified = [oid for oid in draft.evidence_order_ids if oid in known]
    unverified = [oid for oid in draft.evidence_order_ids if oid not in known]
    warnings = list(state["warnings"])
    missing = list(dict.fromkeys([*state["missing_information"], *draft.missing_information]))
    checks = state.get("policy_checks", [])
    excerpts = state.get("policy_excerpts", [])
    retrieved = {excerpt.clause_id for excerpt in excerpts}
    cited = list(dict.fromkeys(c for c in draft.cited_clause_ids if c in retrieved))
    unverified_clauses = list(
        dict.fromkeys(c for c in draft.cited_clause_ids if c not in retrieved)
    )

    needs_review = (
        draft.needs_human_review
        or intent.instructions_aimed_at_system
        or bool(unverified)
        or bool(unverified_clauses)
        or any(not c.allowed for c in checks if not c.informational)
    )
    if unverified:
        warnings.append(
            f"Modelin atıf yaptığı sipariş(ler) bu müşteri için bulunamadı: "
            f"{', '.join(unverified)}. Kanıt olarak gösterilmiyor."
        )
    if unverified_clauses:
        warnings.append(
            "Modelin atıf yaptığı politika maddesi getirilen maddeler arasında yok: "
            f"{', '.join(unverified_clauses)}. Kaynak olarak gösterilmiyor."
        )

    analysis = TicketAnalysis(
        category=intent.category,
        suggested_priority=intent.suggested_priority,
        summary=draft.summary,
        needs_human_review=needs_review,
        draft_reply=draft.draft_reply,
        missing_information=missing,
        evidence_order_ids=verified,
    )
    return AnalysisResult(
        analysis=analysis,
        verified_order_ids=verified,
        unverified_order_ids=unverified,
        warnings=warnings,
        outcome_status=TicketStatus.NEEDS_INFO if missing else TicketStatus.AWAITING_REVIEW,
        prompt_version=prompts.PROMPT_VERSION,
        policy_checks=checks,
        policy_excerpts=excerpts,
        cited_clause_ids=cited,
        unverified_clause_ids=unverified_clauses,
        proposed_action=state.get("proposed_action"),
    )


def mentioned_order_ids(text: str) -> list[str]:
    return list(dict.fromkeys(match.upper() for match in ORDER_ID_PATTERN.findall(text)))


def _action(action_type: ActionType, check: PolicyCheck, payload: dict[str, Any]) -> ProposedAction:
    return ProposedAction(
        type=action_type,
        order_id=check.order_id,
        payload=payload,
        reason=check.reason,
        policy_rule=check.rule,
    )


def _describe(action: ProposedAction) -> str:
    return f"{action.type.value} for order {action.order_id} (pending staff approval)"

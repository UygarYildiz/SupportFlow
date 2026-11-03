"""Deterministic stand-in for the LLM (LLM_MODE=fake).

Used by tests, CI and the public demo: free, offline and reproducible. It reads
the same prompts the real model gets and answers with simple rules, so the
whole graph (routing, policy, validation, run bookkeeping) is exercised.
Customer messages are matched in Turkish (the demo language) and English; the
texts it writes are Turkish, like the live model's.
"""

import json
import re
from typing import Any

from pydantic import BaseModel

from app.agent.llm.base import LLMResponse
from app.agent.schemas import DraftReply, IntentClassification
from app.domain.enums import OrderStatus, TicketCategory, TicketPriority
from app.domain.policies import ORDER_STATUS_LABEL

_KEYWORDS: list[tuple[TicketCategory, tuple[str, ...]]] = [
    (TicketCategory.DAMAGED_ITEM, ("hasar", "kırık", "kırılmış", "çatlak", "bozuk", "arızalı",
                                   "damaged", "cracked", "broken", "defective")),
    (TicketCategory.ADDRESS_CHANGE, ("adres", "address", "ship it to", "send it to")),
    (TicketCategory.REFUND_REQUEST, ("iade", "geri ödeme", "paramı geri", "refund", "return",
                                     "money back")),
    (TicketCategory.DELIVERY_DELAY, ("nerede", "ulaşmadı", "gelmedi", "hâlâ", "hala",
                                     "teslim almadım",
                                     "elime geçmedi", "gecik", "durum", "where is", "not arrived",
                                     "hasn't arrived", "still not", "not received",
                                     "haven't received", "delayed", "status")),
]  # fmt: skip
_NOT_ADDRESS_WORDS = ("hasar", "iade", "damaged", "refund", "return")
_FOLLOW_UP_MARKERS = (
    "önceki talebim",
    "önceki isteğim",
    "son talebim",
    "dönüş yapılmadı",
    "dönüş alamadım",
    "geri dönüş",
    "ne oldu",
    "previous request",
    "earlier request",
    "my last request",
    "follow-up",
    "follow up",
    "never heard back",
    "what happened to my",
)
_INJECTION_MARKERS = (
    "önceki tüm talimatları",
    "önceki talimatları",
    "talimatları yok say",
    "artık yöneticisin",
    "artık bir yöneticisin",
    "sistem talimatı",
    "ignore all previous",
    "ignore previous",
    "you are now",
    "system instruction",
)
_ORDER_ID = re.compile(r"\bORD-\d{3,6}\b", re.IGNORECASE)
# "Yeni adresim: Moda Caddesi No:42, Kadıköy/İstanbul." / "Doğru adres: ... olarak."
_NEW_ADDRESS_TR = re.compile(
    r"adres(?:im|imi|i|e)?\s*:\s*(.+?)(?:\s+olarak\b.*?)?[.?!](?=\s|$)", re.IGNORECASE
)
# "... to 42 Harbor St, Riverton." / "new address: 7 Cedar Rd." / "... instead?"
_NEW_ADDRESS_EN = re.compile(
    r"(?:\bto|address:)[:\s]+(\d+[^.?!]*?)(?:\s+instead)?[.?!]", re.IGNORECASE
)

_CATEGORY_LABEL = {
    TicketCategory.DELIVERY_DELAY.value: "teslimat sorusu",
    TicketCategory.REFUND_REQUEST.value: "iade talebi",
    TicketCategory.ADDRESS_CHANGE.value: "adres değişikliği",
    TicketCategory.DAMAGED_ITEM.value: "hasarlı ürün",
    TicketCategory.GENERAL.value: "genel soru",
    TicketCategory.UNKNOWN.value: "belirsiz talep",
}
_TICKET_STATUS_LABEL = {
    "new": "yeni",
    "triaging": "analiz ediliyor",
    "awaiting_review": "inceleniyor",
    "needs_info": "bilgi bekleniyor",
    "resolved": "çözüldü",
    "failed": "başarısız",
}
_TEAM_WILL_REPLY = "Ekibimizden bir arkadaşımız en kısa sürede size dönüş yapacak."


class FakeLLMClient:
    model_name = "fake-llm"

    def generate_structured(
        self, *, system_instruction: str, prompt: str, response_schema: type[BaseModel]
    ) -> LLMResponse:
        if response_schema is IntentClassification:
            output = _classify(prompt)
        elif response_schema is DraftReply:
            output = _draft(prompt)
        else:  # pragma: no cover - programming error
            raise TypeError(f"FakeLLMClient cannot answer {response_schema.__name__}")
        text = json.dumps(output, ensure_ascii=False)
        # Rough token estimate (~4 characters per token) so metrics are populated.
        return LLMResponse(
            text=text,
            model=self.model_name,
            input_tokens=(len(system_instruction) + len(prompt)) // 4,
            output_tokens=len(text) // 4,
        )


def turkish_lower(text: str) -> str:
    """Lowercase with Turkish dotted/dotless i (Python's lower() maps 'I' to 'i')."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def _searchable(text: str) -> str:
    # Turkish rules for Turkish words, default rules for English ones ("IGNORE" -> "ignore").
    return f"{turkish_lower(text)}\n{text.lower()}"


def _classify(prompt: str) -> dict[str, Any]:
    message = _between(prompt, "<ticket_message>", "</ticket_message>")
    lowered = _searchable(message)
    suspicious = any(marker in lowered for marker in _INJECTION_MARKERS)
    address = _NEW_ADDRESS_TR.search(message) or _NEW_ADDRESS_EN.search(message)
    if suspicious:
        category = TicketCategory.UNKNOWN
    elif address and not any(word in lowered for word in _NOT_ADDRESS_WORDS):
        category = TicketCategory.ADDRESS_CHANGE  # "yeni adresim: Moda Caddesi No:42"
    else:
        category = _category(lowered)
    if category != TicketCategory.ADDRESS_CHANGE:
        address = None
    order_ids = _ORDER_ID.findall(message)
    priority = (
        TicketPriority.HIGH
        if suspicious or category == TicketCategory.DAMAGED_ITEM
        else TicketPriority.MEDIUM
    )
    return {
        "category": category.value,
        "suggested_priority": priority.value,
        "referenced_order_id": order_ids[0].upper() if order_ids else None,
        "requested_new_address": address.group(1).strip() if address else None,
        "instructions_aimed_at_system": suspicious,
    }


def _draft(prompt: str) -> dict[str, Any]:
    facts = json.loads(_between(prompt, "<facts>", "</facts>"))
    name = facts["customer_name"]
    focus = facts["focus_order_id"]
    order = next((o for o in facts["orders"] if o["id"] == focus), None)
    denied = [c for c in facts["policy_checks"] if not c["allowed"] and not c["informational"]]
    category = facts["category"]
    message = _searchable(_between(prompt, "<ticket_message>", "</ticket_message>"))
    follow_up = bool(facts["previous_tickets"]) and any(m in message for m in _FOLLOW_UP_MARKERS)

    if facts["missing_information"]:
        if facts["unknown_order_ids"]:
            ids = ", ".join(facts["unknown_order_ids"])
            lead = f"Hesabınızda {ids} numaralı siparişi bulamadık."
        else:
            lead = "Bize ulaştığınız için teşekkür ederiz."
        wanted = "; ".join(_lower_first(item) for item in facts["missing_information"])
        body = f"{lead} Lütfen şu bilgiyi bizimle paylaşır mısınız: {wanted}?"
    elif category == TicketCategory.UNKNOWN.value:
        body = (
            "Mesajınız için teşekkür ederiz. "
            "Ekibimizden bir arkadaşımız en kısa sürede inceleyecek."
        )
    elif denied:
        body = f"{focus} numaralı siparişinizle ilgili talebinizi inceledik. {denied[0]['reason']}"
    elif facts["planned_action"]:
        body = (
            f"{focus} numaralı siparişinizle ilgili talebinizi aldık. "
            "Ekibimizden bir arkadaşımız talebinizi inceleyip en kısa sürede size dönüş yapacak."
        )
    elif follow_up:  # S6: the customer asks about an earlier ticket, not about the order
        body = _previous_tickets_text(facts["previous_tickets"])
    elif order is not None:
        checks = " ".join(c["reason"] for c in facts["policy_checks"])
        status = ORDER_STATUS_LABEL.get(OrderStatus(order["status"]), order["status"])
        body = f"{focus} numaralı siparişinizin şu anki durumu: {status}. {checks}".strip()
    elif facts["previous_tickets"]:
        body = _previous_tickets_text(facts["previous_tickets"])
    else:
        body = f"Bize ulaştığınız için teşekkür ederiz. {_TEAM_WILL_REPLY}"

    # Cite the best retrieved clause, as the live model is asked to (ADR-014).
    excerpts = [] if facts["missing_information"] else facts.get("policy_excerpts", [])[:1]
    for excerpt in excerpts:
        body += f" (Dayanak: {excerpt['title']} v{excerpt['version']}, {excerpt['clause_id']}.)"

    label = _CATEGORY_LABEL.get(category, category)
    return {
        "summary": f"Talep '{label}' olarak sınıflandırıldı"
        + (f" ({focus} numaralı sipariş)." if focus else "."),
        "needs_human_review": category == TicketCategory.UNKNOWN.value or bool(denied),
        "draft_reply": f"Merhaba {name},\n\n{body}\n\nSaygılarımızla,\nNovaShop Destek Ekibi",
        "missing_information": [],
        "evidence_order_ids": [focus] if order else [],
        "cited_clause_ids": [excerpt["clause_id"] for excerpt in excerpts],
    }


def _previous_tickets_text(tickets: list[dict[str, Any]]) -> str:
    subjects = ", ".join(
        f"'{t['subject']}' ({_TICKET_STATUS_LABEL.get(t['status'], t['status'])})" for t in tickets
    )
    return f"Önceki taleplerinizi bulduk: {subjects}. {_TEAM_WILL_REPLY}"


def _lower_first(text: str) -> str:
    return turkish_lower(text[:1]) + text[1:]


def _category(message: str) -> TicketCategory:
    for category, keywords in _KEYWORDS:
        if any(keyword in message for keyword in keywords):
            return category
    return TicketCategory.GENERAL


def _between(text: str, start: str, end: str) -> str:
    match = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, re.DOTALL)
    return match.group(1).strip() if match else ""

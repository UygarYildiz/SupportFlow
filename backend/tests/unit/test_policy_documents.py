"""Policy documents parse, and they say what the deterministic rules decide (ADR-014)."""

import math

import pytest

from app.agent.llm.fake_embeddings import FakeEmbedder
from app.domain import policies
from app.domain.policy_documents import (
    POLICY_FOR_RULE,
    PolicyDocumentError,
    parse_policy_document,
    policy_for_rule,
)
from scripts.ingest_policies import load_policy_sources

VALID = """---
id: returns
title: İade Politikası
version: 2
effective_from: 2026-06-01
---

# İade Politikası

## IADE-1 Kapsam

Hasarsız ürünler.

## IADE-2 İade süresi

Teslimattan sonraki 14 gün.
"""


def test_a_document_is_split_into_cited_clauses() -> None:
    document = parse_policy_document(VALID)
    assert (document.slug, document.version, str(document.effective_from)) == (
        "returns",
        2,
        "2026-06-01",
    )
    assert [(c.clause_id, c.heading, c.position) for c in document.clauses] == [
        ("IADE-1", "Kapsam", 1),
        ("IADE-2", "İade süresi", 2),
    ]
    assert document.clauses[1].text == "Teslimattan sonraki 14 gün."


def test_the_content_hash_changes_with_the_text_but_not_with_line_endings() -> None:
    original = parse_policy_document(VALID).content_hash
    assert parse_policy_document(VALID.replace("\n", "\r\n")).content_hash == original
    assert parse_policy_document(VALID.replace("14 gün", "15 gün")).content_hash != original


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("# Başlık\n\n## IADE-1 Kapsam\n\nMetin.", "missing front matter"),
        ("---\nid: returns\ntitle: T\n---\n## IADE-1 A\n\nB", "lacks version, effective_from"),
        (VALID.replace("id: returns", "id: Returns"), "lowercase snake_case"),
        (VALID.replace("version: 2", "version: iki"), "invalid version"),
        (VALID.replace("## IADE-2", "## IADE-1"), "appears twice"),
        (VALID.split("# İade")[0] + "Bölümsüz metin.", "no '## CLAUSE-ID heading'"),
    ],
)
def test_malformed_documents_are_refused_with_a_reason(source: str, message: str) -> None:
    with pytest.raises(PolicyDocumentError, match=message):
        parse_policy_document(source, name="test.md")


def test_rules_map_to_the_documents_that_explain_them() -> None:
    assert policy_for_rule("returns_v1") == "returns"
    assert policy_for_rule("address_change_v1") == "address_change"
    assert policy_for_rule("unknown_rule_v3") is None


def test_every_rule_has_a_document_in_the_knowledge_base() -> None:
    slugs = {parse_policy_document(s.text, name=s.path).slug for s in load_policy_sources()}
    assert set(POLICY_FOR_RULE.values()) | {"exceptions"} == slugs


def test_knowledge_base_states_the_same_numbers_as_the_code() -> None:
    """If a rule changes in app/domain/policies.py, the document must change too."""
    documents = {
        (doc := parse_policy_document(s.text, name=s.path)).slug: " ".join(
            c.text for c in doc.clauses
        )
        for s in load_policy_sources()
    }
    assert f"{policies.RETURN_WINDOW_DAYS} gün içinde" in documents["returns"]
    assert f"{policies.DAMAGE_REPORT_WINDOW_DAYS} gün içinde" in documents["damaged_goods"]
    assert f"{policies.DELIVERY_DELAY_BUSINESS_DAYS} iş günü" in documents["delivery"]
    assert "3–5 iş günü" in documents["delivery"]
    for status in policies.ADDRESS_CHANGEABLE_STATUSES:
        assert policies.ORDER_STATUS_LABEL[status] in documents["address_change"]


def test_clause_ids_are_unique_across_the_knowledge_base() -> None:
    ids = [
        clause.clause_id
        for source in load_policy_sources()
        for clause in parse_policy_document(source.text, name=source.path).clauses
    ]
    assert len(ids) == len(set(ids))


def test_fake_embedder_is_deterministic_normalized_and_stem_aware() -> None:
    embedder = FakeEmbedder(768)
    first, again = (
        embedder.embed_query("Teslimat gecikti"),
        embedder.embed_query("Teslimat gecikti"),
    )
    assert first == again
    assert math.isclose(math.sqrt(sum(v * v for v in first)), 1.0)

    def similarity(a: str, b: str) -> float:
        va, vb = embedder.embed_query(a), embedder.embed_query(b)
        return sum(x * y for x, y in zip(va, vb, strict=True))

    # "teslimat" / "teslimden" share a stem; "İADE" lowercases to "iade" with Turkish rules.
    assert similarity("teslimat süresi", "teslimden sonra") > similarity("teslimat süresi", "kupa")
    assert similarity("İADE talebi", "iade talebi") == pytest.approx(1.0)
    assert embedder.embed_query("?!") == embedder.embed_query("...")  # no words: fixed vector

"""The documentation stays in step with the code (docs/README.md, "Otomatik kontroller")."""

from pathlib import Path

from scripts.check_docs import (
    anchors,
    check_adrs,
    check_all,
    check_api,
    check_docs_map,
    check_links,
    slugify,
)


def test_repository_documentation_has_no_drift() -> None:
    assert check_all() == []


def test_slugs_follow_github_rules_for_turkish_headings() -> None:
    assert slugify("ADR-002: LLM yazma işlemi yapamaz") == "adr-002-llm-yazma-işlemi-yapamaz"
    assert slugify("Senaryo eval'leri") == "senaryo-evalleri"
    assert slugify("4. Demo alanı: NovaShop") == "4-demo-alanı-novashop"
    assert slugify("`GET /api/v1/tickets/{ticket_id}`") == "get-apiv1ticketsticket_id"


def test_broken_links_and_missing_anchors_are_reported(tmp_path: Path) -> None:
    (tmp_path / "TARGET.md").write_text("# Başlık\n\n## Aynı\n\n## Aynı\n", encoding="utf-8")
    doc = tmp_path / "DOC.md"
    doc.write_text(
        "[ok](TARGET.md#başlık) [dup](TARGET.md#aynı-1) [web](https://example.com)\n"
        "[gone](MISSING.md) [stale](TARGET.md#eski-başlık)\n"
        "```\n[ignored](IN_CODE.md)\n```\n"
        "`[also ignored](IN_SPAN.md)`\n",
        encoding="utf-8",
    )
    assert anchors(tmp_path / "TARGET.md") == {"başlık", "aynı", "aynı-1"}
    problems = check_links([doc], root=tmp_path)
    assert problems == [
        "DOC.md:2: broken link 'MISSING.md'",
        "DOC.md:2: no heading for anchor 'TARGET.md#eski-başlık'",
    ]


def test_api_doc_must_match_the_app_both_ways(tmp_path: Path) -> None:
    api = tmp_path / "API.md"
    api.write_text("### `GET /health`\n\n### `POST /api/v1/old`\n", encoding="utf-8")
    problems = check_api(api, {("GET", "/health"), ("GET", "/api/v1/new")})
    assert problems == [
        "docs/API.md: endpoint GET /api/v1/new exists in the app but is not documented",
        "docs/API.md: documents POST /api/v1/old, which the app does not have",
    ]


def test_unknown_adr_numbers_and_unmapped_docs_are_reported(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "DECISIONS.md").write_text("## ADR-001: Bir karar\n", encoding="utf-8")
    (docs / "README.md").write_text("[Kararlar](DECISIONS.md)\n", encoding="utf-8")
    (docs / "NEW.md").write_text("ADR-001 ve ADR-099\n", encoding="utf-8")
    assert check_adrs([docs / "NEW.md"], docs / "DECISIONS.md", root=tmp_path) == [
        "docs/NEW.md:1: ADR-099 is not defined in docs/DECISIONS.md"
    ]
    assert check_docs_map(docs) == ["docs/README.md: NEW.md is not listed in the docs map"]

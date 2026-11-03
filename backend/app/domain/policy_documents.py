"""Policy documents of the knowledge base (knowledge/policies/*.md, ADR-014).

Pure parsing, no I/O. A document is markdown with a small front matter block and
one `## <CLAUSE-ID> <heading>` section per clause. Clauses are the unit of
retrieval and citation ("İade Politikası v1, IADE-2").

Documents explain and cite the rules; they never decide. Decisions stay in
`app/domain/policies.py`.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import date

_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_CLAUSE_HEADING = re.compile(r"^##\s+([A-ZÇĞİÖŞÜ]+-\d+(?:\.\d+)?)\s+(.+?)\s*$", re.MULTILINE)
_SLUG = re.compile(r"^[a-z][a-z0-9_]*$")
REQUIRED_FIELDS = ("id", "title", "version", "effective_from")

# Which document explains which deterministic rule (rule name without the "_v1" suffix).
POLICY_FOR_RULE = {
    "delivery": "delivery",
    "returns": "returns",
    "damaged_goods": "damaged_goods",
    "address_change": "address_change",
}
EXCEPTIONS_POLICY = "exceptions"


class PolicyDocumentError(ValueError):
    """A policy document is malformed; the message says which file and why."""


@dataclass(frozen=True)
class PolicyClause:
    clause_id: str  # e.g. "IADE-2"
    heading: str
    text: str
    position: int  # order inside the document, from 1


@dataclass(frozen=True)
class ParsedPolicyDocument:
    slug: str
    title: str
    version: int
    effective_from: date
    content_hash: str  # SHA-256 of the normalized source, to detect silent edits
    clauses: tuple[PolicyClause, ...]


def parse_policy_document(source: str, *, name: str = "document") -> ParsedPolicyDocument:
    text = source.replace("\r\n", "\n").strip() + "\n"
    match = _FRONT_MATTER.match(text)
    if not match:
        raise PolicyDocumentError(f"{name}: missing front matter (--- ... ---)")
    fields = _front_matter_fields(match.group(1))
    missing = [key for key in REQUIRED_FIELDS if key not in fields]
    if missing:
        raise PolicyDocumentError(f"{name}: front matter lacks {', '.join(missing)}")
    slug = fields["id"]
    if not _SLUG.match(slug):
        raise PolicyDocumentError(f"{name}: id '{slug}' must be lowercase snake_case")
    try:
        version = int(fields["version"])
        effective_from = date.fromisoformat(fields["effective_from"])
    except ValueError as exc:
        raise PolicyDocumentError(f"{name}: invalid version or effective_from") from exc

    clauses = _clauses(text[match.end() :], name)
    return ParsedPolicyDocument(
        slug=slug,
        title=fields["title"],
        version=version,
        effective_from=effective_from,
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        clauses=clauses,
    )


def policy_for_rule(rule: str) -> str | None:
    """`returns_v1` -> `returns`. None for rules no document explains."""
    base = re.sub(r"_v\d+$", "", rule)
    return POLICY_FOR_RULE.get(base)


def _front_matter_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise PolicyDocumentError(f"front matter line without ':' -> {line!r}")
        fields[key.strip()] = value.strip()
    return fields


def _clauses(body: str, name: str) -> tuple[PolicyClause, ...]:
    headings = list(_CLAUSE_HEADING.finditer(body))
    if not headings:
        raise PolicyDocumentError(f"{name}: no '## CLAUSE-ID heading' sections")
    clauses = []
    seen: set[str] = set()
    for index, heading in enumerate(headings):
        clause_id = heading.group(1)
        if clause_id in seen:
            raise PolicyDocumentError(f"{name}: clause {clause_id} appears twice")
        seen.add(clause_id)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        content = " ".join(body[heading.end() : end].split())
        if not content:
            raise PolicyDocumentError(f"{name}: clause {clause_id} is empty")
        clauses.append(PolicyClause(clause_id, heading.group(2), content, index + 1))
    return tuple(clauses)

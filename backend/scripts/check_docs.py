"""Catch documentation that has visibly drifted from the code (docs/README.md).

Checks:
- relative links point to existing files, and `#anchors` to existing headings
  (GitHub's slug rules, Turkish characters included);
- every endpoint in the app's OpenAPI schema has a `### \\`METHOD /path\\`` heading
  in docs/API.md, and vice versa;
- every ADR number mentioned in the docs exists in docs/DECISIONS.md;
- every document under docs/ is listed in the docs map (docs/README.md).

Run with `uv run poe docs`; the same checks run in CI through tests/unit/test_docs.py.
"""

import re
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
# ROADMAP.md is the owner's private plan and CLAUDE.md files are assistant
# instructions; neither is part of the published documentation.
TOP_LEVEL = ("README.md", "CHANGELOG.md", "CONTRIBUTING.md", ".github/pull_request_template.md")

_FENCE = re.compile(r"^(```|~~~)")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_LINK = re.compile(r"!?\[(?:[^\]\[]|\[[^\]]*\])*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_CODE_SPAN = re.compile(r"`[^`]*`")
_ADR = re.compile(r"\bADR-(\d{3})\b")
_API_HEADING = re.compile(r"^###\s+`(GET|POST|PUT|PATCH|DELETE)\s+(/\S*)`\s*$")
_HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def documentation_files(root: Path = ROOT) -> list[Path]:
    files = [root / name for name in TOP_LEVEL if (root / name).exists()]
    return files + sorted((root / "docs").glob("*.md"))


def slugify(heading: str) -> str:
    """GitHub's anchor for a heading: lowercase, punctuation dropped, spaces to hyphens."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)  # [text](url) -> text
    text = text.replace("İ", "i").lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def _prose_lines(text: str) -> Iterable[tuple[int, str]]:
    """Lines outside fenced code blocks, with their line numbers."""
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield number, line


def anchors(path: Path) -> set[str]:
    seen: dict[str, int] = {}
    result: set[str] = set()
    for _, line in _prose_lines(path.read_text(encoding="utf-8")):
        match = _HEADING.match(line)
        if not match:
            continue
        slug = slugify(match.group(2))
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        result.add(slug if count == 0 else f"{slug}-{count}")
    return result


def check_links(files: list[Path], root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    cache: dict[Path, set[str]] = {}
    for path in files:
        for number, line in _prose_lines(path.read_text(encoding="utf-8")):
            for target in _LINK.findall(_CODE_SPAN.sub("", line)):
                if re.match(r"^[a-z][a-z0-9+.-]*:", target):  # http:, https:, mailto:
                    continue
                file_part, _, anchor = target.partition("#")
                linked = (path.parent / file_part).resolve() if file_part else path
                where = f"{path.relative_to(root).as_posix()}:{number}"
                if not linked.exists():
                    problems.append(f"{where}: broken link '{target}'")
                    continue
                if anchor and linked.suffix == ".md":
                    known = cache.setdefault(linked, anchors(linked))
                    if anchor not in known:
                        problems.append(f"{where}: no heading for anchor '{target}'")
    return problems


def documented_endpoints(api_doc: Path) -> set[tuple[str, str]]:
    endpoints = set()
    for _, line in _prose_lines(api_doc.read_text(encoding="utf-8")):
        match = _API_HEADING.match(line)
        if match:
            endpoints.add((match.group(1), match.group(2)))
    return endpoints


def app_endpoints() -> set[tuple[str, str]]:
    from app.main import create_app

    schema = create_app(recover_interrupted_runs=False).openapi()
    return {
        (method.upper(), path)
        for path, operations in schema["paths"].items()
        for method in operations
        if method in _HTTP_METHODS
    }


def check_api(api_doc: Path, actual: set[tuple[str, str]]) -> list[str]:
    documented = documented_endpoints(api_doc)
    problems = [
        f"docs/API.md: endpoint {method} {path} exists in the app but is not documented"
        for method, path in sorted(actual - documented)
    ]
    problems += [
        f"docs/API.md: documents {method} {path}, which the app does not have"
        for method, path in sorted(documented - actual)
    ]
    return problems


def check_adrs(files: list[Path], decisions: Path, root: Path = ROOT) -> list[str]:
    defined = {
        number
        for _, line in _prose_lines(decisions.read_text(encoding="utf-8"))
        if line.startswith("## ")
        for number in _ADR.findall(line)
    }
    problems = []
    for path in files:
        for number, line in _prose_lines(path.read_text(encoding="utf-8")):
            for adr in _ADR.findall(line):
                if adr not in defined:
                    where = f"{path.relative_to(root).as_posix()}:{number}"
                    problems.append(f"{where}: ADR-{adr} is not defined in docs/DECISIONS.md")
    return problems


def check_docs_map(docs_dir: Path) -> list[str]:
    index = docs_dir / "README.md"
    if not index.exists():
        return ["docs/README.md (the docs map) is missing"]
    text = index.read_text(encoding="utf-8")
    return [
        f"docs/README.md: {doc.name} is not listed in the docs map"
        for doc in sorted(docs_dir.glob("*.md"))
        if doc.name != "README.md" and f"({doc.name}" not in text
    ]


def check_all() -> list[str]:
    files = documentation_files()
    return (
        check_links(files)
        + check_api(DOCS / "API.md", app_endpoints())
        + check_adrs(files, DOCS / "DECISIONS.md")
        + check_docs_map(DOCS)
    )


def main() -> int:
    problems = check_all()
    for problem in problems:
        print(problem)
    files = len(documentation_files())
    if problems:
        print(f"\n{len(problems)} documentation problem(s) in {files} files.")
        return 1
    print(f"Documentation OK ({files} files checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""C13 boundaries: dependency direction, fixture provenance and labelling, and no credentials or contact headers."""
import ast
import hashlib
from pathlib import Path

from news_support import OFFICIAL, PROVENANCE, ROOT, SYNTHETIC, _no_network  # noqa: F401  (autouse fixture)
import traid.news.sources as sources

SRC = Path(__file__).parents[1] / "src" / "traid" / "news"
STDLIB = {"__future__", "collections", "dataclasses", "datetime", "decimal", "enum", "hashlib", "html", "http", "json", "re", "socket",
          "typing", "unicodedata", "urllib", "xml"}


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_core_imports_only_stdlib_pydantic_c02_and_c13():
    for path in sorted(SRC.glob("*.py")):
        for name in imports(path):
            top = name.split(".")[0]
            if path.name == "macro_adapter.py" and name.startswith("traid.macro"):
                continue
            assert top in STDLIB or top == "pydantic" or name in ("traid.domain.models",) or name.startswith("traid.news"), (path.name, name)


def test_only_the_macro_adapter_imports_c12():
    users = {p.name for p in SRC.glob("*.py") if any(n.startswith("traid.macro") for n in imports(p))}
    assert users == {"macro_adapter.py"}


def test_official_fixtures_match_provenance_byte_for_byte():
    listed = {e["path"] for e in PROVENANCE["files"]}
    on_disk = {str(p.relative_to(OFFICIAL)) for p in OFFICIAL.rglob("*") if p.is_file() and p.name != "PROVENANCE.json"}
    assert listed == on_disk and PROVENANCE["classification"] == "REAL_SOURCE"
    for e in PROVENANCE["files"]:
        data = (OFFICIAL / e["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == e["sha256"] and len(data) == e["retrieval"]["bytes"]
        assert e["retrieved_at"] == e["retrieval"]["not_after"]
    assert PROVENANCE["missing_or_blocked"] == [{"document_number": "2024-00743, 2022-14310, 2023-21948",
                                                 "component": "MANUAL_PASSAGE_VERIFICATION", "status": "NOT_CREATED",
                                                 "reason": "Human-only records (owner decision O6). Not created by this step and never to be authored by Claude."}]


def test_synthetic_fixtures_are_separate_and_never_claim_human_origin():
    assert SYNTHETIC["classification"] == "SYNTHETIC_TEST_RECORDS_NOT_HUMAN_VERIFIED"
    assert all(r["origin"] == "SYNTHETIC_TEST" for r in SYNTHETIC["manual_records"])
    assert all("SYNTHETIC" in r["verifier"] and r["viewer"].startswith("NONE") for r in SYNTHETIC["manual_records"])
    for path in ROOT.rglob("*.json"):
        assert '"origin": "HUMAN"' not in path.read_text(encoding="utf-8"), path
    assert not any(p.parent == OFFICIAL for p in (ROOT / "synthetic").rglob("*"))


def test_official_fixture_bytes_are_protected_by_git_attributes():
    rules = (Path(__file__).parents[1] / ".gitattributes").read_text().splitlines()
    for rule in ("tests/fixtures/news/official/**/*.pdf binary", "tests/fixtures/news/official/**/*.htm -text",
                 "tests/fixtures/news/official/**/*.xml -text", "tests/fixtures/news/official/**/*.json -text"):
        assert rule in rules


def test_no_credentials_keys_or_contact_headers_in_source_access():
    text = (SRC / "sources.py").read_text(encoding="utf-8").lower()
    assert "@" not in sources.USER_AGENT and "api_key" not in text and "registrationkey" not in text
    assert "edgar" not in text and "sec.gov" not in text
    for path in SRC.glob("*.py"):
        assert "anthropic" not in path.read_text(encoding="utf-8").lower() and "openai" not in path.read_text(encoding="utf-8").lower()

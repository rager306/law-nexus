from __future__ import annotations

from collections import Counter
from pathlib import Path

CLOSURE = Path("prd/architecture/residual-script-migration-closure-map.md")
INVENTORY = Path("prd/architecture/residual-script-migration-inventory.md")
SCRIPT_DIR = Path("scripts")

EXPECTED_COUNTS = {
    "migrate logic": 49,
    "proof runtime wrapper": 61,
    "thin wrapper": 6,
    "deferred": 23,
}

REQUIRED_SEAMS = [
    "law_nexus.adapters.governance.architecture_registry",
    "law_nexus.adapters.sources.parser_records",
    "law_nexus.adapters.retrieval.proof_helpers",
    "law_nexus.adapters.embeddings.proof_environment",
]

REQUIRED_COMMITS = ["741b9d9", "5176b3e", "06a2eef", "65d8f89", "e5c029a", "5f7e27a"]


def read_closure() -> str:
    return CLOSURE.read_text(encoding="utf-8")


def inventory_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in INVENTORY.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or "`scripts/" not in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 9:
            rows.append(
                {
                    "path": cells[1].strip("`"),
                    "extracted": cells[5],
                    "class": cells[6],
                    "priority": cells[7],
                    "notes": cells[8],
                }
            )
    return rows


def test_closure_map_has_required_sections() -> None:
    text = read_closure()

    for section in [
        "## Purpose",
        "## Final inventory snapshot",
        "## Migration waves closed",
        "## Package seams established",
        "## Retained wrapper policy",
        "## Retirement map",
        "## Verification closure",
        "## GitNexus traceability notes",
        "## Deferred backlog boundaries",
        "## Non-claims",
    ]:
        assert section in text


def test_closure_map_matches_inventory_counts() -> None:
    rows = inventory_rows()
    scripts = sorted(path.as_posix() for path in SCRIPT_DIR.glob("*.py"))
    text = read_closure()

    assert len(rows) == len(scripts) == 139
    assert sorted(row["path"] for row in rows) == scripts
    assert Counter(row["class"] for row in rows) == EXPECTED_COUNTS

    for label, count in EXPECTED_COUNTS.items():
        assert f"| {label} | {count} |" in text or f"| `{label}` rows | {count} |" in text


def test_closure_map_references_migration_seams_and_commits() -> None:
    text = read_closure()

    for seam in REQUIRED_SEAMS:
        assert seam in text
    for commit in REQUIRED_COMMITS:
        assert commit in text

    for gate in [
        "uv run basedpyright scripts",
        "uv run lint-imports",
        "gitnexus_detect_changes",
        "gitnexus analyze --force --name law-nexus",
    ]:
        assert gate in text


def test_closure_map_does_not_overclaim_completion_or_retirement() -> None:
    text = read_closure()

    required_phrases = [
        "not silently treated as complete",
        "Resolved in M078 S03",
        "Future cleanup should be planned as new bounded slices",
        "Full-script ruff still has unrelated pre-existing lint findings",
        "does not prove",
        "safe deletion of all scripts",
    ]
    for phrase in required_phrases:
        assert phrase in text


def test_closure_map_preserves_legal_and_runtime_non_claims() -> None:
    text = read_closure()

    for non_claim in [
        "legal correctness",
        "parser completeness",
        "retrieval quality",
        "answer faithfulness",
        "model/embedding quality",
        "generated-Cypher correctness",
        "FalkorDB production readiness",
        "ACP/git-lex authority over source truth",
    ]:
        assert non_claim in text

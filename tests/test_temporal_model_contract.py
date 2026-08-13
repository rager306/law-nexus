"""Repository-document contracts for the bounded temporal model crosswalk."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "prd" / "temporal-legal-model.md"


def test_primary_critique_contract_matrix_accounts_for_all_fourteen_areas() -> None:
    text = MODEL.read_text(encoding="utf-8")
    heading = "## 14. Primary-critique contract completeness matrix"
    assert heading in text
    section = text.split(heading, maxsplit=1)[1].split("\n## ", maxsplit=1)[0]

    areas = (
        "Glossary",
        "Entity model",
        "Event taxonomy",
        "Temporal axes",
        "Applicability DSL",
        "Status model",
        "Provenance",
        "Conflict",
        "Correction",
        "Invariants",
        "Deterministic API",
        "Golden cases",
        "Error taxonomy",
        "Proof gates",
    )
    rows = [line for line in section.splitlines() if line.startswith("|")]
    area_rows = [line for line in rows if any(line.startswith(f"| {area} |") for area in areas)]
    for area in areas:
        assert sum(line.startswith(f"| {area} |") for line in area_rows) == 1

    allowed_statuses = {
        "present",
        "present as paper rules",
        "present as paper gates",
        "partial",
        "absent",
        "deferred-undefined",
        "design-only inventory",
    }
    assert {line.split("|")[2].strip() for line in area_rows} <= allowed_statuses
    assert "paper coverage only" in " ".join(section.split())
    assert "no stable Rust signature or wire contract may be inferred" in section
    assert "not executable legal gold" in section


def test_primary_critique_matrix_preserves_absent_and_deferred_cells() -> None:
    text = MODEL.read_text(encoding="utf-8")
    section = text.split("## 14. Primary-critique contract completeness matrix", maxsplit=1)[
        1
    ].split("\n## ", maxsplit=1)[0]

    assert "| Event taxonomy | design-only inventory |" in section
    assert "| Applicability DSL | deferred-undefined |" in section
    assert "| Deterministic API | absent |" in section
    assert "| Error taxonomy | absent |" in section
    assert "neither accepts a schema nor closes a TSG row" in section

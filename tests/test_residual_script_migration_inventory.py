from __future__ import annotations

from pathlib import Path

INVENTORY = Path("prd/architecture/residual-script-migration-inventory.md")
SCRIPT_DIR = Path("scripts")
CLASSIFICATIONS = {
    "migrate logic",
    "thin wrapper",
    "proof runtime wrapper",
    "retire candidate",
    "deferred",
}


def read_inventory() -> str:
    return INVENTORY.read_text(encoding="utf-8")


def script_paths() -> list[str]:
    return sorted(path.as_posix() for path in SCRIPT_DIR.glob("*.py"))


def inventory_rows() -> list[str]:
    text = read_inventory()
    return [line for line in text.splitlines() if line.startswith("| ") and "`scripts/" in line]


def test_residual_script_inventory_has_required_sections() -> None:
    text = read_inventory()

    for section in [
        "## Purpose",
        "## Classification vocabulary",
        "## Summary",
        "## GitNexus research notes",
        "## Migration waves",
        "## Complete script inventory",
        "## Type debt seed list",
        "## Non-claims",
        "## S01 result",
    ]:
        assert section in text


def test_residual_script_inventory_covers_every_top_level_script_once() -> None:
    text = read_inventory()
    scripts = script_paths()
    rows = inventory_rows()

    assert len(scripts) == 140
    assert "Total scripts: `140`" in text
    assert len(rows) == len(scripts)

    table_scripts = []
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        table_scripts.append(cells[1].strip("`"))

    assert sorted(table_scripts) == scripts


def test_residual_script_inventory_uses_only_approved_classifications() -> None:
    rows = inventory_rows()
    seen: set[str] = set()

    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        classification = cells[6]
        assert classification in CLASSIFICATIONS, row
        seen.add(classification)

    assert seen == CLASSIFICATIONS


def test_residual_script_inventory_records_migration_waves_and_type_debt() -> None:
    text = read_inventory()

    for wave in ["S02", "S03", "S04", "S05", "S06", "S07"]:
        assert f"| {wave} |" in text

    for script in [
        "scripts/build-architecture-graph.py",
        "scripts/evaluate-parser-golden-cases.py",
        "scripts/run-s10-user-bge-m3-proof.py",
        "scripts/verify-ontology-graphrag-proof.py",
    ]:
        assert f"`{script}`" in text

    assert "80 error lines across 23 scripts" in text


def test_residual_script_inventory_keeps_gitnexus_and_non_claim_boundaries() -> None:
    text = read_inventory()

    for phrase in [
        "Function:scripts/evaluate-parser-golden-cases.py:evaluate_cases",
        "Function:scripts/build-architecture-graph.py:run",
        "Function:scripts/run-s10-user-bge-m3-proof.py:run_falkordb_vector_proof",
        "Function:scripts/source_lifecycle.py:process_batch",
        "file-qualified UIDs",
        "does not prove legal correctness",
        "safe script deletion",
        "ACP/git-lex projection authority",
        "S01 does not migrate code and does not authorize deletion",
    ]:
        assert phrase in text

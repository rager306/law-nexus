from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/generate-architecture-remediation-matrix.py"
MATRIX_JSON_PATH = ROOT / "prd/architecture/remediation_matrix.json"
MATRIX_MD_PATH = ROOT / "prd/architecture/remediation_matrix.md"


def load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_architecture_remediation_matrix", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module.__name__] = module
    spec.loader.exec_module(module)
    return module


def load_matrix() -> dict:
    return json.loads(MATRIX_JSON_PATH.read_text(encoding="utf-8"))


def test_current_matrix_is_generated_and_non_authoritative() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "ok"
    assert summary["mode"] == "check"
    assert summary["non_authoritative"] is True
    assert summary["unresolved_gate_count"] == 7
    assert summary["r04_recommendation_count"] == 18


def test_matrix_covers_all_current_unresolved_gates() -> None:
    matrix = load_matrix()
    gate_ids = [row["gate_id"] for row in matrix["gate_rows"]]

    assert gate_ids == sorted(gate_ids)
    assert gate_ids == [
        "GATE-EMBEDDING-SUPPLY-CHAIN",
        "GATE-G005",
        "GATE-G008",
        "GATE-G011",
        "GATE-G015",
        "GATE-GENERATED-CYPHER-SAFETY",
        "GATE-LEGAL-NEXUS-ACCESS-CONTROL",
    ]


def test_gate_rows_have_required_planning_fields_and_non_claims() -> None:
    matrix = load_matrix()
    required = {
        "gate_id",
        "title",
        "layer",
        "risk_level",
        "disposition",
        "r04_links",
        "rationale",
        "next_proof_artifact",
        "owner_scope",
        "target_track",
        "source_anchors",
        "non_claims",
    }

    for row in matrix["gate_rows"]:
        assert required <= set(row)
        assert row["disposition"] in matrix["allowed_dispositions"]
        assert row["r04_links"], row["gate_id"]
        assert row["next_proof_artifact"], row["gate_id"]
        assert row["source_anchors"], row["gate_id"]
        assert row["non_claims"], row["gate_id"]


def test_disposition_counts_are_stable_for_s02_planning() -> None:
    matrix = load_matrix()

    assert matrix["summary"]["gate_counts_by_disposition"] == {
        "defer": 0,
        "product-decision": 2,
        "proof-now": 2,
        "runtime-experiment": 3,
    }


def test_r04_recommendation_disposition_covers_all_recommendations() -> None:
    matrix = load_matrix()
    rows = matrix["recommendation_rows"]

    assert len(rows) == 18
    statuses = {row["status"] for row in rows}
    assert "implemented-s01" in statuses
    assert "downstream-s03" in statuses
    assert "defer-s04" in statuses
    assert "partially-implemented-s01" in statuses


def test_markdown_contains_gate_table_recommendations_and_non_claims() -> None:
    content = MATRIX_MD_PATH.read_text(encoding="utf-8")

    assert "# Architecture Remediation Matrix" in content
    assert "## Gate Remediation Rows" in content
    assert "## R04 Recommendation Disposition" in content
    assert "## Non-Claims" in content
    assert "GATE-GENERATED-CYPHER-SAFETY" in content
    assert "R04-REC-004" in content
    assert "does not prove product readiness" in content.lower()


def test_build_matrix_fails_when_report_has_unmapped_gate() -> None:
    generator = load_generator()
    report = {
        "unresolved_proof_gates": [
            {"id": "GATE-UNMAPPED"},
        ]
    }
    items = {"GATE-UNMAPPED": {"id": "GATE-UNMAPPED"}}
    recommendations = {"items": [{"id": rec_id} for rec_id in generator.R04_DISPOSITIONS]}

    try:
        generator.build_matrix(report, items, recommendations)
    except RuntimeError as exc:
        assert "missing gate decision rows: GATE-UNMAPPED" in str(exc)
    else:
        raise AssertionError("build_matrix should fail for unmapped gates")


def test_build_matrix_fails_when_r04_recommendation_is_unmapped() -> None:
    generator = load_generator()
    report = {"unresolved_proof_gates": [{"id": gate_id} for gate_id in generator.GATE_DECISIONS]}
    items = {gate_id: {"id": gate_id, "source_anchors": [{"path": "prd/03_PRD.md"}]} for gate_id in generator.GATE_DECISIONS}
    recommendations = {"items": [{"id": "R04-REC-999"}]}

    try:
        generator.build_matrix(report, items, recommendations)
    except RuntimeError as exc:
        message = str(exc)
        assert "missing R04 disposition rows: R04-REC-999" in message
    else:
        raise AssertionError("build_matrix should fail for unmapped recommendations")

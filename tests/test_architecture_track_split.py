from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/generate-architecture-track-split.py"
TRACK_JSON_PATH = ROOT / "prd/architecture/major_track_split.json"
TRACK_MD_PATH = ROOT / "prd/architecture/major_track_split.md"


def load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_architecture_track_split", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module.__name__] = module
    spec.loader.exec_module(module)
    return module


def load_track_split() -> dict:
    return json.loads(TRACK_JSON_PATH.read_text(encoding="utf-8"))


def test_current_track_split_is_generated_and_non_authoritative() -> None:
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
    assert summary["track_count"] == 6
    assert summary["assigned_gate_count"] == 7


def test_track_split_assigns_each_source_gate_exactly_once() -> None:
    track_split = load_track_split()
    assigned = [gate for track in track_split["tracks"] for gate in track["gate_ids"]]

    assert len(assigned) == len(set(assigned))
    assert sorted(assigned) == [
        "GATE-EMBEDDING-SUPPLY-CHAIN",
        "GATE-G005",
        "GATE-G008",
        "GATE-G011",
        "GATE-G015",
        "GATE-GENERATED-CYPHER-SAFETY",
        "GATE-LEGAL-NEXUS-ACCESS-CONTROL",
    ]
    assert track_split["summary"]["assigned_gate_count"] == track_split["summary"]["source_gate_count"]


def test_tracks_have_required_fields_and_non_claims() -> None:
    track_split = load_track_split()
    required = {
        "track_id",
        "title",
        "gate_ids",
        "track_status",
        "scope_boundary",
        "required_inputs",
        "proof_artifact",
        "acceptance_criteria",
        "recommended_next_unit",
        "non_claims",
        "source_gates",
    }

    for track in track_split["tracks"]:
        assert required <= set(track)
        assert track["gate_ids"], track["track_id"]
        assert track["required_inputs"], track["track_id"]
        assert track["acceptance_criteria"], track["track_id"]
        assert track["non_claims"], track["track_id"]
        assert track["source_gates"], track["track_id"]


def test_track_statuses_cover_planned_decision_and_experiment_work() -> None:
    track_split = load_track_split()
    statuses = {track["track_status"] for track in track_split["tracks"]}

    assert statuses == {
        "planned-proof",
        "needs-product-decision",
        "needs-runtime-experiment",
    }


def test_generated_cypher_track_preserves_r017_boundary() -> None:
    track_split = load_track_split()
    generated = next(track for track in track_split["tracks"] if track["track_id"] == "TRACK-GENERATED-CYPHER-SAFETY")

    assert generated["gate_ids"] == ["GATE-GENERATED-CYPHER-SAFETY"]
    assert "R017" in generated["r04_links"]
    assert "Does not validate product Legal KnowQL readiness." in generated["non_claims"]


def test_retrieval_embedding_track_groups_embedding_supply_chain_and_retrieval_quality() -> None:
    track_split = load_track_split()
    retrieval = next(track for track in track_split["tracks"] if track["track_id"] == "TRACK-RETRIEVAL-EMBEDDING-EXPERIMENT")

    assert retrieval["gate_ids"] == ["GATE-EMBEDDING-SUPPLY-CHAIN", "GATE-G011"]
    assert retrieval["track_status"] == "needs-runtime-experiment"
    assert any("Only local/open-weight embedding candidates" in item for item in retrieval["acceptance_criteria"])


def test_markdown_contains_tracks_acceptance_criteria_and_non_claims() -> None:
    content = TRACK_MD_PATH.read_text(encoding="utf-8")

    assert "# Major Architecture Proof Track Split" in content
    assert "TRACK-GENERATED-CYPHER-SAFETY" in content
    assert "TRACK-PARSER-RETRIEVAL-GOLDEN" in content
    assert "## Track Boundaries and Acceptance Criteria" in content
    assert "Track assignment does not retire proof gates" in content
    assert "does not prove product readiness" in content.lower()


def test_build_track_split_fails_when_gate_is_unassigned() -> None:
    generator = load_generator()
    matrix = {
        "gate_rows": [
            {"gate_id": "GATE-UNASSIGNED", "disposition": "proof-now"},
        ]
    }

    try:
        generator.build_track_split(matrix)
    except RuntimeError as exc:
        message = str(exc)
        assert "unassigned matrix gates: GATE-UNASSIGNED" in message
    else:
        raise AssertionError("build_track_split should fail for unassigned gates")


def test_build_track_split_fails_when_track_references_stale_gate() -> None:
    generator = load_generator()
    matrix = {"gate_rows": []}

    try:
        generator.build_track_split(matrix)
    except RuntimeError as exc:
        message = str(exc)
        assert "track gates not present in matrix" in message
    else:
        raise AssertionError("build_track_split should fail for stale track gates")

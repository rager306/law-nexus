from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/generate-architecture-closure-roadmap.py"
CLOSURE_JSON_PATH = ROOT / "prd/architecture/closure_roadmap.json"
CLOSURE_MD_PATH = ROOT / "prd/architecture/closure_roadmap.md"


def load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_architecture_closure_roadmap", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module.__name__] = module
    spec.loader.exec_module(module)
    return module


def load_closure() -> dict:
    return json.loads(CLOSURE_JSON_PATH.read_text(encoding="utf-8"))


def test_current_closure_roadmap_is_generated_and_non_authoritative() -> None:
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
    assert summary["recommendation_count"] == 18
    assert summary["track_count"] == 6
    assert summary["assigned_gate_count"] == 7


def test_closure_covers_all_r04_recommendations_and_future_tracks() -> None:
    closure = load_closure()

    assert len(closure["recommendation_rows"]) == 18
    assert len(closure["future_tracks"]) == 6
    assert closure["summary"]["assigned_gate_count"] == 7


def test_recommendation_buckets_are_stable_for_m007_closure() -> None:
    closure = load_closure()

    assert closure["summary"]["bucket_counts"] == {
        "completed-in-m007": 5,
        "completed-in-m007-with-open-gates": 1,
        "deferred-minor": 8,
        "future-proof-track": 2,
        "partial-follow-up": 2,
    }


def test_closure_preserves_future_track_references_without_retiring_gates() -> None:
    closure = load_closure()
    tracks = {track["track_id"]: track for track in closure["future_tracks"]}

    assert "TRACK-GENERATED-CYPHER-SAFETY" in tracks
    assert "GATE-GENERATED-CYPHER-SAFETY" in tracks["TRACK-GENERATED-CYPHER-SAFETY"]["gate_ids"]
    assert "TRACK-RETRIEVAL-EMBEDDING-EXPERIMENT" in tracks
    assert "GATE-EMBEDDING-SUPPLY-CHAIN" in tracks["TRACK-RETRIEVAL-EMBEDDING-EXPERIMENT"]["gate_ids"]
    assert "Track assignment does not retire proof gates." in closure["non_claims"] or any(
        "does not retire" in claim.lower() for claim in closure["non_claims"]
    )


def test_markdown_contains_closure_statement_recommendations_tracks_and_non_claims() -> None:
    content = CLOSURE_MD_PATH.read_text(encoding="utf-8")

    assert "# Architecture Closure Roadmap" in content
    assert "## Closure Statement" in content
    assert "## R04 Recommendation Final Disposition" in content
    assert "## Future Proof Tracks" in content
    assert "## Non-Claims" in content
    assert "M007 closes R04 architecture governance triage" in content
    assert "does not prove product readiness" in content.lower()


def test_build_closure_fails_when_recommendation_count_drifts() -> None:
    generator = load_generator()
    matrix = {"recommendation_rows": []}
    track_split = {"tracks": [{} for _ in range(generator.EXPECTED_TRACK_COUNT)], "summary": {"assigned_gate_count": generator.EXPECTED_ASSIGNED_GATE_COUNT}}

    try:
        generator.build_closure(matrix, track_split)
    except RuntimeError as exc:
        assert "expected 18 recommendations" in str(exc)
    else:
        raise AssertionError("build_closure should fail when recommendations drift")


def test_build_closure_fails_when_track_count_drifts() -> None:
    generator = load_generator()
    matrix = {
        "recommendation_rows": [
            {"id": f"R04-REC-{index:03d}", "status": "defer-s04", "title": "x", "priority": "minor", "next": "x"}
            for index in range(1, generator.EXPECTED_RECOMMENDATION_COUNT + 1)
        ]
    }
    track_split = {"tracks": [], "summary": {"assigned_gate_count": generator.EXPECTED_ASSIGNED_GATE_COUNT}}

    try:
        generator.build_closure(matrix, track_split)
    except RuntimeError as exc:
        assert "expected 6 tracks" in str(exc)
    else:
        raise AssertionError("build_closure should fail when tracks drift")


def test_build_closure_fails_on_unknown_recommendation_status() -> None:
    generator = load_generator()
    matrix = {
        "recommendation_rows": [
            {"id": f"R04-REC-{index:03d}", "status": "defer-s04", "title": "x", "priority": "minor", "next": "x"}
            for index in range(1, generator.EXPECTED_RECOMMENDATION_COUNT)
        ]
        + [{"id": "R04-REC-999", "status": "unknown-status", "title": "x", "priority": "minor", "next": "x"}]
    }
    track_split = {"tracks": [{} for _ in range(generator.EXPECTED_TRACK_COUNT)], "summary": {"assigned_gate_count": generator.EXPECTED_ASSIGNED_GATE_COUNT}}

    try:
        generator.build_closure(matrix, track_split)
    except RuntimeError as exc:
        assert "unknown recommendation statuses: unknown-status" in str(exc)
    else:
        raise AssertionError("build_closure should fail on unknown recommendation status")

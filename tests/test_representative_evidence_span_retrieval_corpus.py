from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json"
VERIFIER = ROOT / "scripts/verify-representative-evidence-span-retrieval-corpus.py"

REQUIRED_CASE_CLASSES = {
    "positive_evidence_span",
    "positive_source_block_marker",
    "positive_with_distractor",
    "stale_temporal_negative",
    "ambiguous_candidate_set",
    "unsupported_scope",
    "scoped_no_answer",
    "citation_preservation_boundary",
    "edition_mismatch_negative",
    "unsafe_payload_boundary",
}

FORBIDDEN_SNIPPETS = {
    "Федеральный закон",
    "Статья ",
    "raw_legal_text",
    "source_excerpt",
    "provider_payload",
    "embedding_vector",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "api_key",
    ".gsd/exec",
    "/root/",
    "/tmp/",
}


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def load_verifier(name: str = "representative_corpus_verifier") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_fixture(tmp_path: Path, data: dict[str, Any]) -> Path:
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_fixture_shape_and_safety() -> None:
    fixture = load_fixture()
    serialized = json.dumps(fixture, ensure_ascii=False, sort_keys=True)

    assert fixture["schema_version"] == "representative-evidence-span-retrieval-corpus/v1"
    assert fixture["fixture_artifact"] == "prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json"
    assert fixture["generated_by"] == "M022/S02"
    assert fixture["non_authoritative"] is True
    assert len(fixture["cases"]) == 10
    assert {case["case_class"] for case in fixture["cases"]} == REQUIRED_CASE_CLASSES
    assert fixture["source_anchor_policy"]["mutable_runtime_hashes_avoided"] is True
    for snippet in FORBIDDEN_SNIPPETS:
        assert snippet not in serialized


def test_verifier_accepts_checked_in_fixture() -> None:
    verifier = load_verifier("representative_accept")

    result = verifier.verify_fixture(FIXTURE)

    assert result["status"] == "ok"
    assert result["case_count"] == 10
    assert result["candidate_count"] == 10
    assert set(result["case_classes"]) == REQUIRED_CASE_CLASSES


def test_verifier_cli_accepts_checked_in_fixture() -> None:
    completed = subprocess.run(
        [sys.executable, str(VERIFIER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["case_count"] == 10


def test_verifier_fails_closed_for_missing_required_class(tmp_path: Path) -> None:
    verifier = load_verifier("representative_missing_class")
    fixture = load_fixture()
    fixture["cases"] = [case for case in fixture["cases"] if case["case_class"] != "unsafe_payload_boundary"]
    path = write_fixture(tmp_path, fixture)

    try:
        verifier.verify_fixture(path)
    except verifier.VerificationError as exc:
        assert "case_count below representative minimum" in str(exc) or "case class coverage" in str(exc)
    else:
        raise AssertionError("expected VerificationError")


def test_verifier_fails_closed_for_unsafe_field(tmp_path: Path) -> None:
    verifier = load_verifier("representative_unsafe_field")
    fixture = load_fixture()
    fixture["cases"][0]["raw_text"] = "blocked"
    path = write_fixture(tmp_path, fixture)

    try:
        verifier.verify_fixture(path)
    except verifier.VerificationError as exc:
        assert "unsafe field name" in str(exc)
    else:
        raise AssertionError("expected VerificationError")


def test_verifier_fails_closed_for_unsafe_fragment(tmp_path: Path) -> None:
    verifier = load_verifier("representative_unsafe_fragment")
    fixture = load_fixture()
    fixture["cases"][0]["note"] = "provider_payload"
    path = write_fixture(tmp_path, fixture)

    try:
        verifier.verify_fixture(path)
    except verifier.VerificationError as exc:
        assert "unsafe payload fragment" in str(exc)
    else:
        raise AssertionError("expected VerificationError")


def test_verifier_fails_closed_for_duplicate_candidate_id(tmp_path: Path) -> None:
    verifier = load_verifier("representative_duplicate_candidate")
    fixture = load_fixture()
    first = fixture["cases"][0]["candidates"][0]["candidate_id"]
    fixture["cases"][1]["candidates"][0]["candidate_id"] = first
    path = write_fixture(tmp_path, fixture)

    try:
        verifier.verify_fixture(path)
    except verifier.VerificationError as exc:
        assert "duplicate candidate_id" in str(exc)
    else:
        raise AssertionError("expected VerificationError")


def test_verifier_fails_closed_for_invalid_expected_candidate_reference(tmp_path: Path) -> None:
    verifier = load_verifier("representative_bad_expected")
    fixture = load_fixture()
    fixture["cases"][0]["expected_candidate_ids"] = ["CAND-M022-MISSING"]
    path = write_fixture(tmp_path, fixture)

    try:
        verifier.verify_fixture(path)
    except verifier.VerificationError as exc:
        assert "invalid expected candidate reference" in str(exc)
    else:
        raise AssertionError("expected VerificationError")

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json"
VERIFIER_PATH = ROOT / "scripts/verify-evidence-span-golden-retrieval-cases.py"

REQUIRED_CASE_CLASSES = {
    "positive_evidence_span",
    "positive_source_block_marker",
    "stale_temporal_negative",
    "ambiguous_candidate_set",
    "unsupported_scope",
    "scoped_no_answer",
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
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def load_verifier(name: str = "evidence_span_golden_verifier") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, VERIFIER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_fixture(tmp_path: Path, data: dict[str, Any]) -> Path:
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_fixture_top_level_contract_and_case_classes() -> None:
    fixture = load_fixture()

    assert fixture["schema_version"] == "evidence-span-golden-retrieval-cases/v1"
    assert fixture["fixture_artifact"] == "prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json"
    assert fixture["generated_by"] == "M021/S04"
    assert fixture["milestone_id"] == "M021-qk4lze"
    assert fixture["slice_id"] == "S04"
    assert fixture["non_authoritative"] is True
    assert set(fixture["required_case_classes"]) == REQUIRED_CASE_CLASSES
    assert {case["case_class"] for case in fixture["cases"]} == REQUIRED_CASE_CLASSES
    assert len(fixture["cases"]) == 6


def test_fixture_uses_safe_ids_and_contains_no_unsafe_payloads() -> None:
    fixture = load_fixture()
    serialized = json.dumps(fixture, ensure_ascii=False, sort_keys=True)

    for snippet in FORBIDDEN_SNIPPETS:
        assert snippet not in serialized
    assert all(case["case_id"].startswith("CASE-M021-S04-") for case in fixture["cases"])
    assert all(case["query"]["query_id"].startswith("QUERY-M021-S04-") for case in fixture["cases"])
    assert all(case["non_authoritative"] is True for case in fixture["cases"])
    for artifact in fixture["source_artifacts"]:
        assert not artifact["path"].startswith("/")
        assert not artifact["path"].startswith(".gsd/exec")
        assert len(artifact["sha256"]) == 64
        int(artifact["sha256"], 16)


def test_case_expected_candidate_references_are_local_to_case() -> None:
    fixture = load_fixture()

    for case in fixture["cases"]:
        candidate_ids = {candidate["candidate_id"] for candidate in case["candidates"]}
        assert set(case["expected_candidate_ids"]).issubset(candidate_ids)
        assert set(case["expected_rejected_candidate_ids"]).issubset(candidate_ids)
        if case["query"]["expected_result"] != "selected":
            assert case["expected_diagnostic_codes"]


def test_verifier_accepts_fixture() -> None:
    verifier = load_verifier("evidence_span_accept")

    result = verifier.verify_fixture(FIXTURE_PATH)

    assert result["status"] == "ok"
    assert result["case_count"] == 6
    assert set(result["case_classes"]) == REQUIRED_CASE_CLASSES
    assert result["non_authoritative"] is True


def test_verifier_cli_accepts_fixture() -> None:
    completed = subprocess.run(
        [sys.executable, str(VERIFIER_PATH)],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["case_count"] == 6


def test_verifier_fails_closed_for_missing_case_class(tmp_path: Path) -> None:
    verifier = load_verifier("evidence_span_missing_class")
    fixture = load_fixture()
    fixture["cases"] = [case for case in fixture["cases"] if case["case_class"] != "unsupported_scope"]
    path = write_fixture(tmp_path, fixture)

    try:
        verifier.verify_fixture(path)
    except verifier.VerificationError as exc:
        assert "case class coverage" in str(exc)
    else:
        raise AssertionError("expected VerificationError")


def test_verifier_fails_closed_for_unsafe_field(tmp_path: Path) -> None:
    verifier = load_verifier("evidence_span_unsafe_field")
    fixture = load_fixture()
    fixture["cases"][0]["raw_legal_text"] = "blocked"
    path = write_fixture(tmp_path, fixture)

    try:
        verifier.verify_fixture(path)
    except verifier.VerificationError as exc:
        assert "unsafe field name" in str(exc)
    else:
        raise AssertionError("expected VerificationError")


def test_verifier_fails_closed_for_bad_candidate_reference(tmp_path: Path) -> None:
    verifier = load_verifier("evidence_span_bad_candidate")
    fixture = load_fixture()
    fixture["cases"][0]["expected_candidate_ids"] = ["CAND-M021-S04-MISSING"]
    path = write_fixture(tmp_path, fixture)

    try:
        verifier.verify_fixture(path)
    except verifier.VerificationError as exc:
        assert "invalid expected candidate reference" in str(exc)
    else:
        raise AssertionError("expected VerificationError")

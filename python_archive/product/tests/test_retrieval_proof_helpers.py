from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from law_nexus.adapters.retrieval.proof_helpers import (
    bounded_path,
    diagnostic_codes,
    diagnostic_payloads,
    error_summary,
    load_json_object,
    safe_payload_errors,
)


@dataclass(frozen=True)
class Diagnostic:
    code: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, **self.payload}


@dataclass(frozen=True)
class Result:
    result: str
    diagnostics: list[Diagnostic]


def test_bounded_path_prefers_repo_relative_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    fixture = root / "prd" / "retrieval" / "fixture.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("{}", encoding="utf-8")

    assert bounded_path(fixture, root=root) == "prd/retrieval/fixture.json"
    assert (
        bounded_path(tmp_path / "outside" / "fixture.json", root=root, max_length=12)
        == str(tmp_path / "outside" / "fixture.json")[:12]
    )


def test_load_json_object_requires_object_payload(tmp_path: Path) -> None:
    payload = tmp_path / "payload.json"
    payload.write_text('{"ok": true}', encoding="utf-8")
    assert load_json_object(payload) == {"ok": True}

    payload.write_text('["not", "object"]', encoding="utf-8")
    with pytest.raises(ValueError, match="JSON payload must be an object"):
        load_json_object(payload)


def test_error_summary_uses_bounded_fixture_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    fixture = root / "fixtures" / "cases.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("{}", encoding="utf-8")

    summary = error_summary(
        fixtures=fixture,
        root=root,
        schema_version="proof/v1",
        phase="load",
        code="fixture_error",
        detail="x" * 200,
    )

    assert summary["schema_version"] == "proof/v1"
    assert summary["fixture_path"] == "fixtures/cases.json"
    assert summary["mismatch_count"] == 1
    assert summary["mismatches"][0]["detail"] == "x" * 160


def test_diagnostic_helpers_and_safe_payload_errors() -> None:
    result = Result(
        result="accepted",
        diagnostics=[
            Diagnostic(
                "known_code",
                {
                    "field_path": "answer.citations[0]",
                    "case_id": "case-1",
                    "retrieval_output_id": "out-1",
                    "scope_id": "scope-1",
                },
            )
        ],
    )

    assert diagnostic_codes(result) == ["known_code"]
    assert diagnostic_payloads(result)[0]["case_id"] == "case-1"
    assert (
        safe_payload_errors(
            case_id="case-1",
            result=result,
            safe_fields={"code", "field_path", "case_id", "retrieval_output_id", "scope_id"},
            known_codes={"known_code"},
        )
        == []
    )


def test_safe_payload_errors_reports_unknown_extra_and_unbounded_fields() -> None:
    result = Result(
        result="unexpected",
        diagnostics=[
            Diagnostic(
                "unknown_code",
                {
                    "field_path": "x" * 161,
                    "case_id": "case-1",
                    "retrieval_output_id": "out-1",
                    "scope_id": "scope-1",
                    "raw_payload": "unsafe",
                },
            )
        ],
    )

    errors = safe_payload_errors(
        case_id="case-1",
        result=result,
        safe_fields={"code", "field_path", "case_id", "retrieval_output_id", "scope_id"},
        known_codes={"known_code"},
    )

    assert {error["code"] for error in errors} == {
        "malformed_output_shape",
        "unsafe_diagnostic_field",
        "unknown_diagnostic_code",
    }
    assert any(error["field_path"] == "diagnostics[0].field_path" for error in errors)


def test_helper_docstring_keeps_retrieval_non_claims() -> None:
    import law_nexus.adapters.retrieval.proof_helpers as proof_helpers

    assert proof_helpers.__doc__ is not None
    assert "do not" in proof_helpers.__doc__
    assert "retrieval quality" in proof_helpers.__doc__
    assert "legal correctness" in proof_helpers.__doc__

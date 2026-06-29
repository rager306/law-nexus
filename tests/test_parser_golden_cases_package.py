from __future__ import annotations

import json
from pathlib import Path

from law_nexus.adapters.sources.parser_golden_cases import (
    diagnostic,
    display_path,
    load_json_object,
    severity_counts,
    sha256_file,
    sort_diagnostics,
)


def test_display_path_prefers_repo_relative_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    nested = root / "prd" / "parser" / "golden_cases.json"
    nested.parent.mkdir(parents=True)
    nested.write_text("{}", encoding="utf-8")

    assert display_path(nested, root=root) == "prd/parser/golden_cases.json"


def test_diagnostic_preserves_extra_fields_and_non_claim_default() -> None:
    item = diagnostic(
        case_id="CASE-1",
        case_class="evidence-present",
        severity="warning",
        rule="bounded",
        artifact_path="prd/parser/golden_cases.json",
        message="Bounded diagnostic.",
        field="source_id",
    )

    assert item["non_authoritative"] is True
    assert item["field"] == "source_id"
    assert item["expected_state"] is None
    assert item["actual_state"] is None


def test_load_json_object_reports_missing_and_invalid_shapes(tmp_path: Path) -> None:
    missing_payload, missing_diags = load_json_object(tmp_path / "missing.json", root=tmp_path)
    assert missing_payload is None
    assert missing_diags[0]["rule"] == "missing_source_artifact"

    list_path = tmp_path / "list.json"
    list_path.write_text("[]", encoding="utf-8")
    list_payload, list_diags = load_json_object(list_path, root=tmp_path)
    assert list_payload is None
    assert list_diags[0]["rule"] == "invalid_json_shape"

    object_path = tmp_path / "object.json"
    object_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
    object_payload, object_diags = load_json_object(object_path, root=tmp_path)
    assert object_payload == {"ok": True}
    assert object_diags == []


def test_sha256_sort_and_severity_helpers_are_stable(tmp_path: Path) -> None:
    payload = tmp_path / "payload.txt"
    payload.write_text("abc", encoding="utf-8")
    assert sha256_file(payload) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

    diagnostics = [
        diagnostic(
            case_id="B",
            case_class=None,
            severity="info",
            rule="z",
            artifact_path="b",
            message="b",
        ),
        diagnostic(
            case_id="A",
            case_class=None,
            severity="error",
            rule="a",
            artifact_path="a",
            message="a",
        ),
    ]

    assert [item["case_id"] for item in sort_diagnostics(diagnostics)] == ["A", "B"]
    assert severity_counts(diagnostics) == {"error": 1, "info": 1}

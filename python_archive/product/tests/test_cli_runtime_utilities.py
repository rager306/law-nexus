from __future__ import annotations

import json
from pathlib import Path

import pytest

from law_nexus.adapters.cli.runtime import (
    CLI_RUNTIME_NON_CLAIMS,
    CliRuntimeError,
    load_json_object,
    repo_relative_path,
    sha256_bytes,
    sha256_path,
    sha256_text,
    stable_json_text,
    write_json_report,
)


def test_cli_runtime_non_claims_are_bounded() -> None:
    assert "Does not validate legal correctness." in CLI_RUNTIME_NON_CLAIMS
    assert "Does not prove parser completeness." in CLI_RUNTIME_NON_CLAIMS
    assert "Does not prove production runtime readiness." in CLI_RUNTIME_NON_CLAIMS


def test_repo_relative_path_returns_project_relative_or_sentinel(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    nested = root / "dir" / "file.json"
    nested.parent.mkdir(parents=True)
    nested.write_text("{}", encoding="utf-8")

    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")

    assert repo_relative_path(nested, root=root) == "dir/file.json"
    assert repo_relative_path(outside, root=root) == "<outside-project>"


def test_sha256_helpers_are_stable(tmp_path: Path) -> None:
    path = tmp_path / "payload.txt"
    path.write_text("legal graph\n", encoding="utf-8")

    expected = "eac35d697376607a0ac989748e8c658c75a419f84deaa40ccafbe9e61927f453"
    assert sha256_bytes(b"legal graph\n") == expected
    assert sha256_text("legal graph\n") == expected
    assert sha256_path(path) == expected


def test_stable_json_text_sorts_keys_and_ends_with_newline() -> None:
    assert stable_json_text({"b": 1, "a": {"d": 4, "c": 3}}) == (
        '{\n  "a": {\n    "c": 3,\n    "d": 4\n  },\n  "b": 1\n}\n'
    )


def test_load_json_object_rejects_missing_or_non_object(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(CliRuntimeError) as missing_error:
        load_json_object(missing, path_display=lambda path: path.name)
    assert missing_error.value.code == "E_JSON_FILE_MISSING"
    assert missing_error.value.failure_class == "missing_source_artifact"

    array_path = tmp_path / "array.json"
    array_path.write_text("[]", encoding="utf-8")
    with pytest.raises(CliRuntimeError) as type_error:
        load_json_object(array_path, path_display=lambda path: path.name)
    assert type_error.value.code == "E_JSON_OBJECT_EXPECTED"
    assert type_error.value.failure_class == "invalid_source_artifact"


def test_write_json_report_validates_payload_and_creates_parent(tmp_path: Path) -> None:
    report_path = tmp_path / "nested" / "report.json"
    seen: list[dict[str, object]] = []

    def validator(payload: dict[str, object]) -> None:
        seen.append(payload)

    payload = {"status": "pass", "count": 2}
    write_json_report(report_path, payload, validator=validator)

    assert seen == [payload]
    assert json.loads(report_path.read_text(encoding="utf-8")) == payload
    assert report_path.read_text(encoding="utf-8").endswith("\n")

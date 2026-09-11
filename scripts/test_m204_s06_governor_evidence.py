from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import m204_s06_governor_evidence as evidence

NOW = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)


def governor_report(
    *, error_count: int = 0, status: str = "ok", observed: str = "open_count=2"
) -> dict:
    return {
        "schema_version": "law-nexus-governor-report/v1",
        "status": status,
        "error_count": error_count,
        "pass_count": 1,
        "warn_count": 1,
        "tool_error_count": 0,
        "findings": [
            {
                "check_id": "review-case-integrity",
                "status": "pass",
                "severity": "ok",
                "observed": observed,
                "message": "integrity observed",
                "remediation": "none",
                "rule_id": "review-case-integrity.contract",
            }
        ],
    }


def status_report() -> dict:
    return {
        "schema_version": "review-case-cli-report/v1",
        "status": "ok",
        "result": {
            "schema_version": "review-case-application-report/v1",
            "open_blockers": [],
            "packets": [
                [
                    evidence.PACKET_ID,
                    "doc/review/review-28-10-09-2026.md",
                    "source",
                    "hash",
                    [["RC28-F01", "open"], ["RC28-F02", "open"]],
                ]
            ],
        },
    }


def runner_for(governor: object, status: object, *, governor_exit: int = 0, status_exit: int = 0):
    reports = [governor, status]
    exits = [governor_exit, status_exit]
    calls: list[list[str]] = []

    def runner(argv, cwd: Path, timeout: float):
        calls.append(list(argv))
        value = reports[len(calls) - 1]
        stdout = value if isinstance(value, str) else json.dumps(value)
        return exits[len(calls) - 1], stdout, ""

    return runner, calls


def test_capture_preserves_two_fixed_argv_and_semantics() -> None:
    runner, calls = runner_for(governor_report(), status_report())
    payload = evidence.capture(runner=runner, now=lambda: NOW)

    assert payload["overall"] == "sanctioned_outcome"
    assert payload["captured_at_utc"] == "2026-09-11T12:00:00Z"
    assert payload["governor"]["summary"]["observed"]["open_count"] == 2
    assert payload["review_case_status"]["summary"]["findings"] == [
        {"finding_id": "RC28-F01", "status": "open"},
        {"finding_id": "RC28-F02", "status": "open"},
    ]
    assert calls[0] == [
        "uv",
        "run",
        "python",
        "-m",
        "law_nexus_harness",
        "governor",
        "--check",
        "review-case-integrity",
        "--format",
        "json",
    ]
    assert calls[1][-2:] == ["--packet-id", evidence.PACKET_ID]


def test_error_count_blocks_even_when_process_exit_is_zero() -> None:
    runner, _ = runner_for(governor_report(error_count=1), status_report())
    payload = evidence.capture(runner=runner, now=lambda: NOW)
    assert payload["overall"] == "blocked_scope"
    assert payload["governor"]["summary"]["status"] == "blocked_scope"
    assert payload["governor"]["summary"]["observed"]["error_count"] == 1


def test_nonzero_status_exit_is_blocked_without_promoting_open_findings() -> None:
    runner, _ = runner_for(governor_report(), status_report(), status_exit=7)
    payload = evidence.capture(runner=runner, now=lambda: NOW)
    assert payload["overall"] == "blocked_scope"
    assert payload["review_case_status"]["summary"]["status"] == "blocked_scope"
    assert payload["review_case_status"]["summary"]["findings"][0]["status"] == "open"


@pytest.mark.parametrize(
    "stdout, label",
    [("{not-json", "governor"), ("[]", "review-case status")],
)
def test_malformed_json_fails_closed(stdout: str, label: str) -> None:
    with pytest.raises(ValueError, match="malformed JSON|must be a JSON object"):
        evidence._json_report(stdout, label)


def test_missing_open_count_fails_closed() -> None:
    with pytest.raises(ValueError, match="open_count"):
        evidence.summarize_governor(governor_report(observed="packet_count=4"), 0)


def test_wrong_packet_identity_fails_closed() -> None:
    report = status_report()
    report["result"]["packets"][0][0] = "RC-OTHER"
    with pytest.raises(ValueError, match="packet identity"):
        evidence.summarize_status(report, 0)


def test_durable_artifact_rejects_forged_success_with_errors() -> None:
    payload = evidence.capture(
        runner=runner_for(governor_report(), status_report())[0], now=lambda: NOW
    )
    payload["governor"]["summary"]["observed"]["error_count"] = 1
    with pytest.raises(ValueError, match="success artifact"):
        evidence.validate_artifact(payload)


def test_check_is_read_only_and_does_not_recapture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = evidence.capture(
        runner=runner_for(governor_report(), status_report())[0], now=lambda: NOW
    )
    output = tmp_path / "outcome.json"
    original = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output.write_text(original, encoding="utf-8")

    def unexpected_capture() -> dict:
        raise AssertionError("--check must not recapture live reports")

    monkeypatch.setattr(evidence, "capture", unexpected_capture)
    assert evidence.main(["--check", "--output", str(output)]) == 0
    assert output.read_text(encoding="utf-8") == original

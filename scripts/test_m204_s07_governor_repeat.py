from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import m204_s07_governor_repeat as evidence

NOW = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)


def governor_report(*, error_count: int = 0, tool_error_count: int = 0) -> dict:
    return {
        "schema_version": "law-nexus-governor-report/v1",
        "status": "ok",
        "error_count": error_count,
        "pass_count": 1,
        "warn_count": 1,
        "tool_error_count": tool_error_count,
        "findings": [
            {"check_id": "review-case-integrity", "status": "pass", "severity": "ok"},
            {
                "check_id": "review-case-integrity.open-findings",
                "status": "fail",
                "severity": "warn",
            },
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
                    [["RC28-F01", "open"]],
                ]
            ],
        },
    }


def runner_for(governor: object, status: object, *, governor_exit: int = 0, status_exit: int = 0):
    values = [governor, status]
    exits = [governor_exit, status_exit]
    calls: list[list[str]] = []
    ticks = iter([10.0, 10.25, 10.5])

    def runner(argv, cwd: Path, timeout: float):
        calls.append(list(argv))
        value = values[len(calls) - 1]
        return exits[len(calls) - 1], value if isinstance(value, str) else json.dumps(value), ""

    return runner, calls, lambda: next(ticks)


def test_capture_preserves_fixed_argv_and_advisory_inventory() -> None:
    runner, calls, clock = runner_for(governor_report(), status_report())
    payload = evidence.capture(runner=runner, now=lambda: NOW, clock=clock)
    assert payload["overall"] == "sanctioned_outcome"
    assert payload["duration_ms"] == 250
    assert payload["governor"]["summary"]["check_id"] == evidence.CHECK_ID
    assert payload["governor"]["summary"]["observed"]["pass_finding"] is True
    assert payload["review_case_status"]["summary"]["observed"]["open_count"] == 1
    assert calls[0] == [
        "uv",
        "run",
        "python",
        "-m",
        "law_nexus_harness",
        "governor",
        "--check",
        evidence.CHECK_ID,
        "--format",
        "json",
    ]
    assert calls[1][-2:] == ["--packet-id", evidence.PACKET_ID]


@pytest.mark.parametrize(
    "governor, exit_code", [(governor_report(error_count=1), 0), (governor_report(), 7)]
)
def test_governor_error_or_exit_fails_closed(governor: dict, exit_code: int) -> None:
    runner, _, clock = runner_for(governor, status_report(), governor_exit=exit_code)
    assert (
        evidence.capture(runner=runner, now=lambda: NOW, clock=clock)["overall"] == "blocked_scope"
    )


def test_malformed_report_is_blocked_without_exception() -> None:
    runner, _, clock = runner_for("{not-json", status_report())
    payload = evidence.capture(runner=runner, now=lambda: NOW, clock=clock)
    assert payload["overall"] == "blocked_scope"
    assert "malformed JSON" in payload["governor"]["summary"]["error"]


def test_wrong_packet_identity_is_blocked() -> None:
    report = status_report()
    report["result"]["packets"][0][0] = "RC-OTHER"
    runner, _, clock = runner_for(governor_report(), report)
    payload = evidence.capture(runner=runner, now=lambda: NOW, clock=clock)
    assert payload["review_case_status"]["summary"]["status"] == "blocked_scope"


def test_validator_rejects_predecessor_collision(tmp_path: Path) -> None:
    runner, _, clock = runner_for(governor_report(), status_report())
    payload = evidence.capture(runner=runner, now=lambda: NOW, clock=clock)
    payload["predecessor"]["sha256"] = "sha256:forged"
    with pytest.raises(ValueError, match="predecessor hash"):
        evidence.validate_artifact(payload)


def test_check_is_read_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner, _, clock = runner_for(governor_report(), status_report())
    payload = evidence.capture(runner=runner, now=lambda: NOW, clock=clock)
    output = tmp_path / "repeat.json"
    original = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output.write_text(original, encoding="utf-8")
    monkeypatch.setattr(evidence, "capture", lambda: pytest.fail("check recaptured live command"))
    assert evidence.main(["--check", "--output", str(output)]) == 0
    assert output.read_text(encoding="utf-8") == original

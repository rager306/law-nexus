"""CLI vertical-slice contracts for non-authoritative Review Case operations."""

from __future__ import annotations

import json
from pathlib import Path

from law_nexus_harness.cli import main
from law_nexus_harness.review_case.adapters.filesystem import FilesystemReviewPacketStore
from law_nexus_harness.review_case.adapters.hashlib_adapter import HashlibContentHasher

REV = "60fd8245ace999f3f29911844375dd7cc36a2a38"
TS = "2026-08-11T10:33:40Z"
SOURCE_REL = "doc/review/review-11-08-2026.md"
SOURCE_BYTES = b"# review fixture body\n"
PACKETS_DIR = "prd/architecture/review-cases/packets"


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    source = root / SOURCE_REL
    source.parent.mkdir(parents=True)
    source.write_bytes(SOURCE_BYTES)
    return root


def _register_args(root: Path, *, packet_id: str = "RC-CLI-001") -> list[str]:
    return [
        "review-case",
        "--root",
        str(root),
        "--packets-dir",
        PACKETS_DIR,
        "register",
        "--packet-id",
        packet_id,
        "--source-path",
        SOURCE_REL,
        "--reviewed-revision",
        REV,
        "--received-at",
        TS,
        "--non-claim",
        "CLI fixture non-claim",
        "--extractor-version",
        "cli-test/v1",
    ]


def test_register_validate_status_happy_path(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    code = main(_register_args(root))
    out = capsys.readouterr().out
    assert code == 0
    report = json.loads(out)
    assert report["schema_version"] == "review-case-cli-report/v1"
    assert report["status"] == "ok"
    assert report["authoritative"] is False
    assert report["authority_required"] is True
    assert report["operation"] == "review-case.register"
    assert report["result"]["packet_id"] == "RC-CLI-001"
    assert report["result"]["content_sha256"] == HashlibContentHasher().sha256(SOURCE_BYTES)

    store = FilesystemReviewPacketStore(root, packets_dir=PACKETS_DIR)
    assert store.get("RC-CLI-001").packet_id == "RC-CLI-001"

    code = main(
        [
            "review-case",
            "--root",
            str(root),
            "--packets-dir",
            PACKETS_DIR,
            "validate",
        ]
    )
    validate_report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert validate_report["status"] == "ok"
    assert validate_report["result"]["ok"] is True
    assert validate_report["result"]["packet_count"] == 1

    code = main(
        [
            "review-case",
            "--root",
            str(root),
            "--packets-dir",
            PACKETS_DIR,
            "status",
        ]
    )
    status_report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert status_report["status"] == "ok"
    assert status_report["result"]["packets"][0][0] == "RC-CLI-001"
    assert "Does not create GSD milestones or product claims" in status_report["non_claims"]


def test_duplicate_register_is_validation_exit(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    assert main(_register_args(root)) == 0
    capsys.readouterr()
    code = main(_register_args(root))
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert report["status"] == "validation-error"
    assert report["error"]["code"] == "duplicate_packet"


def test_missing_source_is_tool_exit(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    (root / SOURCE_REL).unlink()
    code = main(_register_args(root))
    report = json.loads(capsys.readouterr().out)
    assert code == 2
    assert report["status"] == "tool-error"
    assert report["error"]["code"] == "source_not_found"


def test_invalid_path_is_validation_exit(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    args = _register_args(root)
    # replace --source-path value
    idx = args.index("--source-path")
    args[idx + 1] = "../escape.md"
    code = main(args)
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert report["status"] == "validation-error"
    assert report["error"]["code"] == "invalid_path"


def test_source_hash_drift_is_validation_exit(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    assert main(_register_args(root)) == 0
    capsys.readouterr()
    (root / SOURCE_REL).write_bytes(b"drifted body\n")
    code = main(
        [
            "review-case",
            "--root",
            str(root),
            "--packets-dir",
            PACKETS_DIR,
            "validate",
        ]
    )
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert report["status"] == "validation-error"
    assert report["error"]["code"] == "source_hash_drift"


def test_status_missing_packet_is_validation_exit(tmp_path: Path, capsys) -> None:
    root = _repo(tmp_path)
    code = main(
        [
            "review-case",
            "--root",
            str(root),
            "--packets-dir",
            PACKETS_DIR,
            "status",
            "--packet-id",
            "RC-MISSING",
        ]
    )
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert report["status"] == "validation-error"
    assert report["error"]["code"] == "packet_not_found"


def test_cli_has_no_disposition_or_gsd_surface() -> None:
    from law_nexus_harness import cli as cli_module

    source = Path(cli_module.__file__).read_text(encoding="utf-8")
    forbidden = (
        "disposition",
        "promoted_to",
        "gsd_plan",
        "gsd_task",
        "create_milestone",
        "accept_finding",
    )
    for token in forbidden:
        assert (
            token not in source.lower()
            or token
            in {
                # allow non-claims text mentioning GSD non-creation only in report module, not cli
            }
        )


def test_cli_help_exposes_review_case_ops(capsys) -> None:
    import pytest

    with pytest.raises(SystemExit) as exc:
        main(["review-case", "--help"])
    assert exc.value.code == 0
    help_text = capsys.readouterr().out
    assert "register" in help_text
    assert "validate" in help_text
    assert "status" in help_text

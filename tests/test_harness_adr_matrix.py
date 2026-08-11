"""Contracts for the non-authoritative ADR matrix CLI."""

from __future__ import annotations

import json
from pathlib import Path

from law_nexus_harness.adr_matrix import build_adr_matrix
from law_nexus_harness.cli import main
from law_nexus_harness.governor import check_adr_matrix_freshness

ROOT = Path(__file__).resolve().parents[1]


def _write_adr(root: Path, adr_id: str, lifecycle: str, extra: str = "") -> None:
    adr = root / "doc" / "adr"
    adr.mkdir(parents=True, exist_ok=True)
    (adr / f"{adr_id}-sample.md").write_text(
        "---\n"
        f"id: ADR-{adr_id}\n"
        f'lifecycle: "[{lifecycle}]"\n'
        f"{extra}"
        "---\n\n"
        f"# ADR-{adr_id}\n\n"
        "## Status\n\n"
        f"Accepted [{lifecycle}].\n",
        encoding="utf-8",
    )


def _write_surfaces(root: Path, *adr_ids: str) -> None:
    values = "\n".join(f"ADR-{adr_id} [proposed]" for adr_id in adr_ids)
    for relative in ("prd/ARCHITECTURE.md", "README.md", "doc/adr/README.md"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(values + "\n", encoding="utf-8")


def test_build_adr_matrix_is_non_authoritative_and_captures_scoped_edge(
    tmp_path: Path,
) -> None:
    _write_adr(
        tmp_path,
        "0004",
        "proposed",
        "superseded_by: [ADR-0005#scope-a]\n",
    )
    _write_adr(
        tmp_path,
        "0005",
        "proposed",
        "supersedes: [ADR-0004#scope-a]\n",
    )
    _write_surfaces(tmp_path, "0004", "0005")

    matrix = build_adr_matrix(tmp_path)

    assert matrix["schema_version"] == "law-nexus-adr-matrix/v1"
    assert matrix["authoritative"] is False
    assert matrix["non_claims"]
    row = next(item for item in matrix["rows"] if item["adr_id"] == "ADR-0005")
    assert row["supersedes"] == ["ADR-0004#scope-a"]
    assert row["surfaces"] == {
        "architecture": True,
        "root_readme": True,
        "adr_index": True,
    }


def test_cli_adr_matrix_generate_emits_stdout_without_writing(tmp_path: Path, capsys) -> None:
    _write_adr(tmp_path, "0004", "proposed")
    _write_surfaces(tmp_path, "0004")

    code = main(["adr-verify", "--root", str(tmp_path), "--matrix", "generate", "--stdout"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["authoritative"] is False
    assert not (tmp_path / "prd" / "architecture" / "adr-matrix.json").exists()


def test_cli_adr_matrix_check_accepts_current_derived_output(tmp_path: Path, capsys) -> None:
    _write_adr(tmp_path, "0004", "proposed")
    _write_surfaces(tmp_path, "0004")
    output = tmp_path / "derived" / "adr-matrix.json"
    output.parent.mkdir()
    output.write_text(
        json.dumps(build_adr_matrix(tmp_path), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    code = main(
        [
            "adr-verify",
            "--root",
            str(tmp_path),
            "--matrix",
            "check",
            "--output",
            str(output),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["status"] == "ok"
    assert payload["authoritative"] is False


def test_cli_adr_matrix_check_detects_stale_derived_output(tmp_path: Path, capsys) -> None:
    _write_adr(tmp_path, "0004", "proposed")
    _write_surfaces(tmp_path, "0004")
    output = tmp_path / "derived" / "adr-matrix.json"
    output.parent.mkdir()
    output.write_text("{}\n", encoding="utf-8")

    code = main(
        [
            "adr-verify",
            "--root",
            str(tmp_path),
            "--matrix",
            "check",
            "--output",
            str(output),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 1
    assert payload["status"] == "stale"
    assert payload["authoritative"] is False


def test_governor_adr_matrix_freshness_warns_when_output_is_missing(
    tmp_path: Path,
) -> None:
    _write_adr(tmp_path, "0004", "proposed")
    _write_surfaces(tmp_path, "0004")

    finding = check_adr_matrix_freshness(tmp_path)[0]

    assert finding.status == "fail"
    assert finding.severity == "warn"
    assert "missing-output" in finding.observed
    assert finding.evidence[0].path == "prd/architecture/adr-matrix.json"


def test_cli_adr_matrix_rejects_authority_output_target(tmp_path: Path, capsys) -> None:
    _write_adr(tmp_path, "0004", "proposed")
    _write_surfaces(tmp_path, "0004")

    code = main(
        [
            "adr-verify",
            "--root",
            str(tmp_path),
            "--matrix",
            "check",
            "--output",
            str(tmp_path / "prd" / "ARCHITECTURE.md"),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "tool-error"
    assert payload["error"] == "authority-output-target"

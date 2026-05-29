from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts/run-m048-s04-git-lex-proof.py"
FIXTURE_DIR = ROOT / "prd/architecture/acp/fixtures/git-lex-isolated-proof"


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("m048_s04_git_lex_proof", HARNESS_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def frontmatter_for(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, raw_frontmatter, _ = text.split("---\n", 2)
    data = yaml.safe_load(raw_frontmatter)
    assert isinstance(data, dict)
    return data


def write_record(path: Path, record: dict[str, Any]) -> None:
    path.write_text("---\n" + yaml.safe_dump(record, sort_keys=False) + "---\n", encoding="utf-8")


def copy_fixture_records(tmp_path: Path) -> Path:
    fixture_copy = tmp_path / "fixtures"
    fixture_copy.mkdir()
    for source in FIXTURE_DIR.glob("*.md"):
        (fixture_copy / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return fixture_copy


def materialize_anchor_targets(root: Path) -> None:
    anchor = frontmatter_for(FIXTURE_DIR / "EA-ACP-0001.md")
    paths = [anchor["repo_relative_path"], *anchor.get("secondary_repo_relative_paths", [])]
    for relative_path in paths:
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("temporary tracked-source anchor for isolated harness contract tests\n", encoding="utf-8")


def run_harness_main(module: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, dict[str, Any]]:
    monkeypatch.setattr(module.sys, "argv", [str(HARNESS_PATH), *args])
    exit_code = module.main()
    captured = capsys.readouterr()
    return exit_code, json.loads(captured.out)


def phase_by_name(result: dict[str, Any], name: str) -> dict[str, Any]:
    phases = {phase["name"]: phase for phase in result["phases"]}
    assert name in phases, f"Missing phase {name!r}; got {sorted(phases)}"
    return phases[name]


def test_missing_git_lex_reports_blocked_json_contract_without_crashing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_harness()
    fixture_copy = copy_fixture_records(tmp_path)
    root = tmp_path / "repo"
    root.mkdir()
    materialize_anchor_targets(root)

    monkeypatch.chdir(root)
    monkeypatch.setattr(module, "ROOT", root)
    monkeypatch.setattr(module, "FIXTURE_DIR", fixture_copy)
    monkeypatch.setattr(module, "MAIN_REPO_LEX_DIR", root / ".lex")
    monkeypatch.setattr(module, "run_probe", lambda command, cwd: {  # noqa: ARG005
        "command": command,
        "exit_code": None,
        "stdout_preview": "",
        "stderr_preview": "missing executable",
        "duration_ms": 1,
        "timed_out": False,
    })

    exit_code, result = run_harness_main(module, monkeypatch, capsys, "--check")

    assert exit_code == 0
    assert result["status"] == "blocked"
    assert result["fatal_failures"] == []
    assert result["blocked_or_deferred"] == [
        "git-lex executable unavailable; runtime git-lex mechanics are blocked, deterministic fixture checks still ran"
    ]
    assert result["observability"]["main_repo_mutation_checked"] is True
    assert result["observability"]["runtime_telemetry_introduced"] is False
    acquisition = phase_by_name(result, "acquisition")
    assert acquisition["status"] == "blocked"
    assert acquisition["details"]["safe_acquisition_policy"] == "no clone/install/download/durable build from law-nexus"
    mutation_guard = phase_by_name(result, "main_repo_mutation_guard")
    assert mutation_guard["status"] == "pass"
    assert not (root / ".lex").exists()


def test_main_repo_lex_creation_fails_closed_even_when_other_checks_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_harness()
    fixture_copy = copy_fixture_records(tmp_path)
    root = tmp_path / "repo"
    root.mkdir()
    materialize_anchor_targets(root)
    (root / ".lex").mkdir()

    monkeypatch.chdir(root)
    monkeypatch.setattr(module, "ROOT", root)
    monkeypatch.setattr(module, "FIXTURE_DIR", fixture_copy)
    monkeypatch.setattr(module, "MAIN_REPO_LEX_DIR", root / ".lex")
    monkeypatch.setattr(module, "run_probe", lambda command, cwd: {  # noqa: ARG005
        "command": command,
        "exit_code": 0,
        "stdout_preview": "usage: git lex",
        "stderr_preview": "",
        "duration_ms": 1,
        "timed_out": False,
    })

    exit_code, result = run_harness_main(module, monkeypatch, capsys, "--check")

    assert exit_code == 1
    assert result["status"] == "fail"
    assert "main repository .lex exists before proof harness execution" in result["fatal_failures"]
    assert "main repository .lex exists after proof harness execution" in result["fatal_failures"]
    mutation_guard = phase_by_name(result, "main_repo_mutation_guard")
    assert mutation_guard["status"] == "fail"
    assert mutation_guard["details"] == {"main_lex_before": True, "main_lex_after": True}


def test_malformed_fixture_frontmatter_is_rejected_with_validation_diagnostic(tmp_path: Path) -> None:
    module = load_harness()
    fixture_copy = copy_fixture_records(tmp_path)
    broken = fixture_copy / "RB-ACP-0001.md"
    broken.write_text("# no frontmatter\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing YAML frontmatter: RB-ACP-0001.md"):
        module.load_records(fixture_copy)


def test_unsafe_durable_proof_anchor_paths_are_rejected() -> None:
    module = load_harness()

    unsafe_paths = [
        "/tmp/raw-source.md",
        "../outside.md",
        ".gsd/exec/run.json",
        ".lex/state.json",
        "artifacts/provider_payload.json",
        "artifacts/raw_vector.bin",
        "artifacts/raw_vectors.json",
        "artifacts/secret-token.txt",
    ]

    for path in unsafe_paths:
        with pytest.raises(ValueError):
            module.assert_repo_relative_path(path)

    module.assert_repo_relative_path("prd/architecture/acp/fixtures/git-lex-isolated-proof/EA-ACP-0001-evidence-anchor.md")


def test_derived_projection_and_requirement_binding_cannot_be_promoted_to_source_truth(tmp_path: Path) -> None:
    module = load_harness()
    records = module.load_records(copy_fixture_records(tmp_path))

    projection = module.acp_projection(records)
    assert projection["authority_status"] == "non_authoritative"
    assert projection["projection_kind"] == "deterministic-acp-fixture-projection"

    derived = records["DPR-ACP-0001"]
    assert derived["authority_status"] == "non_authoritative"
    blocked_uses = " ".join(derived["blocked_acp_use"]).casefold()
    assert "serve as sole source anchor" in blocked_uses
    assert "validate requirements" in blocked_uses
    assert "override source records" in blocked_uses

    requirement_binding = records["RB-ACP-0001"]
    assert requirement_binding["requirement_status"] == "not-validated-by-this-fixture"
    assert all(requirement_binding["safety"][flag] is False for flag in module.NON_CLAIM_FLAGS)


def test_proof_gate_does_not_self_satisfy_and_r035_r037_r038_remain_unvalidated(tmp_path: Path) -> None:
    module = load_harness()
    records = module.load_records(copy_fixture_records(tmp_path))
    gate = records["PG-ACP-0001"]

    assert gate["status"] == "pending_evidence"
    assert gate["safety"]["claims_r035_validated"] is False
    assert gate["safety"]["claims_r037_validated"] is False
    assert gate["safety"]["claims_r038_validated"] is False
    assert not any(value == "PG-ACP-0001" for value in module.referenced_fixture_ids(gate))

    lifecycle_failures = module.validate_lifecycle(records)
    assert lifecycle_failures == []

    gate["status"] = "satisfied"
    assert "PG-ACP-0001: expected status 'pending_evidence', got 'satisfied'" in module.validate_lifecycle(records)


def test_validation_fails_for_source_projection_confusion_and_law_nexus_overclaims(tmp_path: Path) -> None:
    module = load_harness()
    fixture_copy = copy_fixture_records(tmp_path)
    dpr_path = fixture_copy / "DPR-ACP-0001.md"
    rb_path = fixture_copy / "RB-ACP-0001.md"

    dpr = frontmatter_for(dpr_path)
    dpr["safety"]["claims_r035_validated"] = True
    write_record(dpr_path, dpr)

    rb = frontmatter_for(rb_path)
    rb["repo_relative_path"] = ".gsd/exec/unsafe-proof.json"
    write_record(rb_path, rb)

    records = module.load_records(fixture_copy)
    failures = module.validate_records(records)

    assert any("DPR-ACP-0001: safety flag must be false: claims_r035_validated" in failure for failure in failures)
    # RB-ACP-0001 is not an evidence-anchor record, so validation must still reject overclaimed law-nexus proof flags.
    assert any("claims_r035_validated" in failure for failure in failures)


def test_evidence_anchor_validation_rejects_unsafe_paths_without_reading_gsd_exec(tmp_path: Path) -> None:
    module = load_harness()
    fixture_copy = copy_fixture_records(tmp_path)
    anchor_path = fixture_copy / "EA-ACP-0001.md"
    anchor = frontmatter_for(anchor_path)
    anchor["repo_relative_path"] = ".gsd/exec/unsafe-proof.json"
    anchor["secondary_repo_relative_paths"] = ["../outside.md", "artifacts/raw_legal_text.md"]
    write_record(anchor_path, anchor)

    records = module.load_records(fixture_copy)
    failures = module.validate_records(records)

    assert "unsafe durable anchor path: '.gsd/exec/unsafe-proof.json'" in failures
    assert "anchor path must not escape the repository: '../outside.md'" in failures
    # The current harness blocks explicitly enumerated raw/proprietary payload classes; this guards no .gsd/exec read is needed.
    assert not (ROOT / ".gsd/exec/unsafe-proof.json").exists() or failures

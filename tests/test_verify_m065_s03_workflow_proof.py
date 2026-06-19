from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "verify-m065-s03-workflow-proof.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_m065_s03_workflow_proof", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def diagnostic_ids(diagnostics: list[object]) -> set[str]:
    return {getattr(diagnostic, "diagnostic_id") for diagnostic in diagnostics}


def _valid_proof() -> dict:
    """Minimal proof dict matching workflow-proof.json with all gate fields green."""
    return {
        "schema_version": "m065-s03-workflow-proof/v1",
        "cold_path_definition": {"vendor_dir_excluded": True},
        "disposable_repo": {"is_inside_main_law_nexus": False},
        "stages": {
            "init": {
                "exit_code": 0,
                "auto_commit_landed": True,
                "hook_installed": True,
                "lex_dir_created": True,
            },
            "content_seed_commit": {
                "exit_code": 0,
                "hook_extracted_spo": True,
            },
            "sync": {"exit_code": 0},
            "query": {"exit_code": 0, "commit_results_count": 4},
            "validate": {"exit_code": 0},
            "list": {"exit_code": 0},
        },
        "residue_guard": {
            "before": {".lex": "absent", "Squad": "absent", "Raw": "absent", ".artifacts": "absent"},
            "after": {".lex": "absent", "Squad": "absent", "Raw": "absent", ".artifacts": "absent"},
            "r047_contract_phase": "honored",
        },
        "cli_install_only_boundary": {
            "wont": [
                "no main .lex init",
                "no R035/R037/R038 validation",
                "no ACP-kit source truth",
                "no single-repo/Stage-3 .lex adoption",
                "no serve/viz/listen server exposure",
                "no nuke/kit-update/save/create/join/raw mutating surfaces",
            ]
        },
    }


def _write_proof(tmp_path: Path, proof: dict) -> Path:
    proof_path = tmp_path / "workflow-proof.json"
    proof_path.write_text(json.dumps(proof), encoding="utf-8")
    return proof_path


# --------------------------------------------------------------------------
# diagnostic surface
# --------------------------------------------------------------------------


def test_lists_required_diagnostic_ids() -> None:
    verifier = load_verifier()

    assert set(verifier.DIAGNOSTIC_IDS) == {
        "missing_proof_file",
        "proof_field_invalid",
        "cold_path_regression",
        "boundary_markers_missing",
        "main_state_residue",
    }


def test_does_not_import_subprocess() -> None:
    """Self-discipline: the verifier must not run external commands."""
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "import subprocess" not in source
    assert "subprocess.run" not in source


def test_expected_boundary_markers_set() -> None:
    verifier = load_verifier()

    assert set(verifier.EXPECTED_BOUNDARY_MARKERS) == {
        "no main .lex init",
        "no R035/R037/R038 validation",
        "no serve/viz/listen",
        "no nuke/kit-update/save/create/join/raw",
    }


# --------------------------------------------------------------------------
# check_proof_file (file-level)
# --------------------------------------------------------------------------


def test_check_proof_file_missing(tmp_path: Path) -> None:
    verifier = load_verifier()

    diagnostics = verifier.check_proof_file(tmp_path / "nope.json")

    assert "missing_proof_file" in diagnostic_ids(diagnostics)


def test_check_proof_file_invalid_json(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof = tmp_path / "workflow-proof.json"
    proof.write_text("{broken", encoding="utf-8")

    diagnostics = verifier.check_proof_file(proof)

    assert "missing_proof_file" in diagnostic_ids(diagnostics)


def test_check_proof_file_valid(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof = _write_proof(tmp_path, _valid_proof())

    diagnostics = verifier.check_proof_file(proof)

    assert diagnostics == []


# --------------------------------------------------------------------------
# check_proof_fields
# --------------------------------------------------------------------------


def test_check_proof_fields_happy(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof = _write_proof(tmp_path, _valid_proof())

    diagnostics = verifier.check_proof_fields(proof)

    assert diagnostics == []


def test_check_proof_fields_missing_file_returns_empty(tmp_path: Path) -> None:
    """check_proof_file owns the missing-file diagnostic; field checker stays quiet."""
    verifier = load_verifier()

    diagnostics = verifier.check_proof_fields(tmp_path / "nope.json")

    assert diagnostics == []


def test_check_proof_fields_init_rc(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["stages"]["init"]["exit_code"] = 1
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    ids = diagnostic_ids(diagnostics)
    assert "proof_field_invalid" in ids
    assert any("init.exit_code" in d.message for d in diagnostics)


def test_check_proof_fields_auto_commit_not_landed(tmp_path: Path) -> None:
    """MEM549 inversion regression: auto_commit_landed=false is a hard failure."""
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["stages"]["init"]["auto_commit_landed"] = False
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    ids = diagnostic_ids(diagnostics)
    assert "proof_field_invalid" in ids
    assert any("auto_commit_landed" in d.message for d in diagnostics)


def test_check_proof_fields_hook_not_installed(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["stages"]["init"]["hook_installed"] = False
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    assert "proof_field_invalid" in diagnostic_ids(diagnostics)


def test_check_proof_fields_sync_rc(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["stages"]["sync"]["exit_code"] = 1
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    ids = diagnostic_ids(diagnostics)
    assert "proof_field_invalid" in ids
    assert any("sync.exit_code" in d.message for d in diagnostics)


def test_check_proof_fields_validate_rc(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["stages"]["validate"]["exit_code"] = 1
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    ids = diagnostic_ids(diagnostics)
    assert "proof_field_invalid" in ids
    assert any("validate.exit_code" in d.message for d in diagnostics)


def test_check_proof_fields_list_rc(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["stages"]["list"]["exit_code"] = 1
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    ids = diagnostic_ids(diagnostics)
    assert "proof_field_invalid" in ids
    assert any("list.exit_code" in d.message for d in diagnostics)


def test_check_proof_fields_residue_present(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["residue_guard"]["after"][".lex"] = "present"
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    assert "proof_field_invalid" in diagnostic_ids(diagnostics)


def test_check_proof_fields_residue_phase_not_honored(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["residue_guard"]["r047_contract_phase"] = "breached"
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    assert "proof_field_invalid" in diagnostic_ids(diagnostics)


def test_check_proof_fields_disposable_inside_main(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["disposable_repo"]["is_inside_main_law_nexus"] = True
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    assert "proof_field_invalid" in diagnostic_ids(diagnostics)


def test_check_proof_fields_content_seed_not_extracted(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["stages"]["content_seed_commit"]["hook_extracted_spo"] = False
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    assert "proof_field_invalid" in diagnostic_ids(diagnostics)


# --------------------------------------------------------------------------
# check_cold_path
# --------------------------------------------------------------------------


def test_check_cold_path_happy(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof = _write_proof(tmp_path, _valid_proof())

    diagnostics = verifier.check_cold_path(proof)

    assert diagnostics == []


def test_check_cold_path_regression(tmp_path: Path) -> None:
    """vendor_dir_excluded=false → cold_path_regression (false-pass risk)."""
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["cold_path_definition"]["vendor_dir_excluded"] = False
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_cold_path(proof)

    assert "cold_path_regression" in diagnostic_ids(diagnostics)


def test_check_cold_path_missing_field(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    del proof_data["cold_path_definition"]
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_cold_path(proof)

    assert "cold_path_regression" in diagnostic_ids(diagnostics)


# --------------------------------------------------------------------------
# check_commit_results_count
# --------------------------------------------------------------------------


def test_check_commit_results_count_happy(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof = _write_proof(tmp_path, _valid_proof())

    diagnostics = verifier.check_commit_results_count(proof)

    assert diagnostics == []


def test_check_commit_results_count_zero(tmp_path: Path) -> None:
    """commit_results_count=0 → proof_field_invalid (store not queryable)."""
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["stages"]["query"]["commit_results_count"] = 0
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_commit_results_count(proof)

    ids = diagnostic_ids(diagnostics)
    assert "proof_field_invalid" in ids
    assert any("commit_results_count" in d.message for d in diagnostics)


def test_check_commit_results_count_missing(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    del proof_data["stages"]["query"]["commit_results_count"]
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_commit_results_count(proof)

    assert "proof_field_invalid" in diagnostic_ids(diagnostics)


# --------------------------------------------------------------------------
# check_boundary_markers
# --------------------------------------------------------------------------


def test_check_boundary_markers_happy(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof = _write_proof(tmp_path, _valid_proof())

    diagnostics = verifier.check_boundary_markers(proof)

    assert diagnostics == []


def test_check_boundary_markers_empty(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["cli_install_only_boundary"]["wont"] = []
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_boundary_markers(proof)

    assert "boundary_markers_missing" in diagnostic_ids(diagnostics)


def test_check_boundary_markers_missing_phrase(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["cli_install_only_boundary"]["wont"] = ["no main .lex init", "no R035/R037/R038 validation"]
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_boundary_markers(proof)

    ids = diagnostic_ids(diagnostics)
    assert "boundary_markers_missing" in ids
    assert any("no serve/viz/listen" in d.message for d in diagnostics)


def test_check_boundary_markers_missing_object(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    del proof_data["cli_install_only_boundary"]
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_boundary_markers(proof)

    assert "boundary_markers_missing" in diagnostic_ids(diagnostics)


# --------------------------------------------------------------------------
# residue guard (filesystem)
# --------------------------------------------------------------------------


def test_check_main_state_residue_absent(tmp_path: Path) -> None:
    verifier = load_verifier()

    diagnostics = verifier.check_main_state_residue(tmp_path)

    assert diagnostics == []


def test_check_main_state_residue_present(tmp_path: Path) -> None:
    verifier = load_verifier()
    (tmp_path / ".lex").mkdir()

    diagnostics = verifier.check_main_state_residue(tmp_path)

    assert "main_state_residue" in diagnostic_ids(diagnostics)


# --------------------------------------------------------------------------
# verify() aggregation
# --------------------------------------------------------------------------


def test_verify_happy_path(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof = _write_proof(tmp_path, _valid_proof())
    residue_root = tmp_path / "clean-root"
    residue_root.mkdir()

    proof_ok, diagnostics = verifier.verify(proof, root=residue_root)

    assert diagnostics == []
    assert proof_ok is True


def test_verify_aggregates_all_diagnostic_categories(tmp_path: Path) -> None:
    verifier = load_verifier()
    residue_root = tmp_path / "dirty-root"
    residue_root.mkdir()
    (residue_root / "Squad").mkdir()

    proof_ok, diagnostics = verifier.verify(
        tmp_path / "no-proof.json",
        root=residue_root,
    )

    ids = diagnostic_ids(diagnostics)
    assert proof_ok is False
    assert "missing_proof_file" in ids
    # field checkers stay quiet when the file is missing (check_proof_file owns it)
    assert "main_state_residue" in ids


def test_verify_skip_residue(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof = _write_proof(tmp_path, _valid_proof())
    residue_root = tmp_path / "dirty-root"
    residue_root.mkdir()
    (residue_root / ".lex").mkdir()

    proof_ok, diagnostics = verifier.verify(proof, root=residue_root, check_residue=False)

    assert "main_state_residue" not in diagnostic_ids(diagnostics)
    assert diagnostics == []


# --------------------------------------------------------------------------
# CLI main()
# --------------------------------------------------------------------------


def test_main_exits_nonzero_on_diagnostics(tmp_path: Path) -> None:
    verifier = load_verifier()
    rc = verifier.main(["--proof", str(tmp_path / "nope.json"),
                        "--root", str(tmp_path), "--skip-residue"])

    assert rc == 1


def test_main_exits_zero_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    verifier = load_verifier()
    proof = _write_proof(tmp_path, _valid_proof())
    residue_root = tmp_path / "clean-root"
    residue_root.mkdir()

    rc = verifier.main([
        "--proof", str(proof),
        "--root", str(residue_root),
    ])

    assert rc == 0
    captured = capsys.readouterr()
    assert "M065 S03 workflow-proof verification passed: diagnostics=0" in captured.out


# --------------------------------------------------------------------------
# real-state integration (skip when the real proof is not present)
# --------------------------------------------------------------------------


def test_current_real_state_check_passes() -> None:
    verifier = load_verifier()
    proof = verifier.DEFAULT_PROOF
    if not proof.exists():
        pytest.skip("real S03 workflow-proof evidence anchor not present in this environment")

    proof_ok, diagnostics = verifier.verify(proof)

    assert diagnostics == []
    assert proof_ok is True

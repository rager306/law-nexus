from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "verify-m065-s02-release-install.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_m065_s02_release_install", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def diagnostic_ids(diagnostics: list[object]) -> set[str]:
    return {getattr(diagnostic, "diagnostic_id") for diagnostic in diagnostics}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_binary(tmp_path: Path, name: str, content: bytes, mode: int = 0o755) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    os.chmod(path, mode)
    return path


def _write_manifest(tmp_path: Path, binaries: dict) -> Path:
    manifest_path = tmp_path / "install-manifest.json"
    manifest_path.write_text(json.dumps({"schema_version": "m065-s02-install-manifest/v1", "binaries": binaries}), encoding="utf-8")
    return manifest_path


def _valid_proof() -> dict:
    """Minimal proof dict matching install-proof.json with all gate fields green."""
    return {
        "schema_version": "m065-s02-install-proof/v1",
        "proofs": {
            "git_lex_direct_help": {"exit_code": 0, "banner_found": True},
            "git_lex_serve_help": {"exit_code": 0, "banner_found": True},
            "git_subcommand_dispatch": {"primary_exit_code": 2, "primary_banner_found": True},
            "version_gap": {"version_gap_confirmed": True, "git_lex_version_rc": 2, "git_lex_serve_version_rc": 2},
        },
        "residue_guard": {
            "before": {".lex": "absent", "Squad": "absent", "Raw": "absent", ".artifacts": "absent"},
            "after": {".lex": "absent", "Squad": "absent", "Raw": "absent", ".artifacts": "absent"},
        },
        "cli_install_only_boundary": {"wont": ["no main .lex init", "no serve/viz/listen"]},
    }


def _write_proof(tmp_path: Path, proof: dict) -> Path:
    proof_path = tmp_path / "install-proof.json"
    proof_path.write_text(json.dumps(proof), encoding="utf-8")
    return proof_path


# --------------------------------------------------------------------------
# diagnostic surface
# --------------------------------------------------------------------------


def test_lists_required_diagnostic_ids() -> None:
    verifier = load_verifier()

    assert set(verifier.DIAGNOSTIC_IDS) == {
        "contract_file_missing",
        "missing_manifest_file",
        "missing_proof_file",
        "missing_installed_binary",
        "binary_identity_drift",
        "proof_field_invalid",
        "main_state_residue",
    }


def test_does_not_import_subprocess() -> None:
    """Self-discipline: the verifier must not run external commands."""
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "import subprocess" not in source
    assert "subprocess.run" not in source


def test_expected_binaries_set() -> None:
    verifier = load_verifier()

    assert set(verifier.EXPECTED_BINARIES) == {"git-lex", "git-lex-serve"}


# --------------------------------------------------------------------------
# contract continuity
# --------------------------------------------------------------------------


def test_check_contract_file_missing(tmp_path: Path) -> None:
    verifier = load_verifier()

    diagnostics = verifier.check_contract_file(tmp_path / "missing-contract.md")

    assert "contract_file_missing" in diagnostic_ids(diagnostics)


def test_check_contract_file_present(tmp_path: Path) -> None:
    verifier = load_verifier()
    contract = tmp_path / "install-contract.md"
    contract.write_text("# contract\n", encoding="utf-8")

    diagnostics = verifier.check_contract_file(contract)

    assert diagnostics == []


# --------------------------------------------------------------------------
# installed-binary identity
# --------------------------------------------------------------------------


def test_check_installed_binaries_missing_manifest(tmp_path: Path) -> None:
    verifier = load_verifier()

    count, diagnostics = verifier.check_installed_binaries(tmp_path / "nope.json")

    assert count == 0
    assert "missing_manifest_file" in diagnostic_ids(diagnostics)


def test_check_installed_binaries_invalid_json(tmp_path: Path) -> None:
    verifier = load_verifier()
    manifest = tmp_path / "install-manifest.json"
    manifest.write_text("{not json", encoding="utf-8")

    count, diagnostics = verifier.check_installed_binaries(manifest)

    assert count == 0
    assert "missing_manifest_file" in diagnostic_ids(diagnostics)


def test_check_installed_binaries_no_binaries_object(tmp_path: Path) -> None:
    verifier = load_verifier()
    manifest = _write_manifest(tmp_path, {})
    # overwrite so the manifest has no 'binaries' key at all
    manifest.write_text(json.dumps({"schema_version": "x"}), encoding="utf-8")

    count, diagnostics = verifier.check_installed_binaries(manifest)

    assert count == 0
    assert "missing_manifest_file" in diagnostic_ids(diagnostics)


def test_check_installed_binaries_missing_binary(tmp_path: Path) -> None:
    verifier = load_verifier()
    manifest = _write_manifest(
        tmp_path,
        {
            "git-lex": {"sha256": "aa", "path": str(tmp_path / "git-lex")},
            "git-lex-serve": {"sha256": "bb", "path": str(tmp_path / "git-lex-serve")},
        },
    )

    count, diagnostics = verifier.check_installed_binaries(manifest)

    assert count == 0
    assert "missing_installed_binary" in diagnostic_ids(diagnostics)


def test_check_installed_binaries_missing_manifest_entry(tmp_path: Path) -> None:
    verifier = load_verifier()
    # only git-lex recorded; git-lex-serve absent
    manifest = _write_manifest(tmp_path, {"git-lex": {"sha256": "aa", "path": str(tmp_path / "git-lex")}})

    count, diagnostics = verifier.check_installed_binaries(manifest)

    assert count == 0
    assert "binary_identity_drift" in diagnostic_ids(diagnostics)


def test_check_installed_binaries_sha_drift(tmp_path: Path) -> None:
    verifier = load_verifier()
    lex = _write_binary(tmp_path, "git-lex", b"\x7fELFrelease")
    serve = _write_binary(tmp_path, "git-lex-serve", b"\x7fELFserve")
    manifest = _write_manifest(
        tmp_path,
        {
            "git-lex": {"sha256": "deadbeef", "path": str(lex)},
            "git-lex-serve": {"sha256": "deadbeef", "path": str(serve)},
        },
    )

    count, diagnostics = verifier.check_installed_binaries(manifest)

    assert count == 0
    ids = diagnostic_ids(diagnostics)
    assert "binary_identity_drift" in ids
    assert "missing_installed_binary" not in ids


def test_check_installed_binaries_not_executable(tmp_path: Path) -> None:
    verifier = load_verifier()
    content = b"\x7fELFrelease"
    lex = _write_binary(tmp_path, "git-lex", content, mode=0o644)
    serve = _write_binary(tmp_path, "git-lex-serve", content, mode=0o644)
    manifest = _write_manifest(
        tmp_path,
        {
            "git-lex": {"sha256": _sha256_bytes(content), "path": str(lex)},
            "git-lex-serve": {"sha256": _sha256_bytes(content), "path": str(serve)},
        },
    )

    count, diagnostics = verifier.check_installed_binaries(manifest)

    assert count == 0
    assert "binary_identity_drift" in diagnostic_ids(diagnostics)


def test_check_installed_binaries_happy(tmp_path: Path) -> None:
    verifier = load_verifier()
    lex_content = b"\x7fELFrelease-git-lex"
    serve_content = b"\x7fELFrelease-git-lex-serve"
    lex = _write_binary(tmp_path, "git-lex", lex_content)
    serve = _write_binary(tmp_path, "git-lex-serve", serve_content)
    manifest = _write_manifest(
        tmp_path,
        {
            "git-lex": {"sha256": _sha256_bytes(lex_content), "path": str(lex)},
            "git-lex-serve": {"sha256": _sha256_bytes(serve_content), "path": str(serve)},
        },
    )

    count, diagnostics = verifier.check_installed_binaries(manifest)

    assert diagnostics == []
    assert count == 2


# --------------------------------------------------------------------------
# proof fields
# --------------------------------------------------------------------------


def test_check_proof_fields_missing_file(tmp_path: Path) -> None:
    verifier = load_verifier()

    diagnostics = verifier.check_proof_fields(tmp_path / "nope.json")

    assert "missing_proof_file" in diagnostic_ids(diagnostics)


def test_check_proof_fields_invalid_json(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof = tmp_path / "install-proof.json"
    proof.write_text("{broken", encoding="utf-8")

    diagnostics = verifier.check_proof_fields(proof)

    assert "missing_proof_file" in diagnostic_ids(diagnostics)


def test_check_proof_fields_happy(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof = _write_proof(tmp_path, _valid_proof())

    diagnostics = verifier.check_proof_fields(proof)

    assert diagnostics == []


def test_check_proof_fields_bad_direct_help_rc(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["proofs"]["git_lex_direct_help"]["exit_code"] = 16
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    ids = diagnostic_ids(diagnostics)
    assert "proof_field_invalid" in ids
    assert any("git_lex_direct_help.exit_code" in d.message for d in diagnostics)


def test_check_proof_fields_bad_version_gap(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["proofs"]["version_gap"]["git_lex_version_rc"] = 0  # overclaim
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    ids = diagnostic_ids(diagnostics)
    assert "proof_field_invalid" in ids
    assert any("git_lex_version_rc" in d.message for d in diagnostics)


def test_check_proof_fields_version_gap_not_confirmed(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["proofs"]["version_gap"]["version_gap_confirmed"] = False
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    assert "proof_field_invalid" in diagnostic_ids(diagnostics)


def test_check_proof_fields_missing_field(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    del proof_data["proofs"]["git_subcommand_dispatch"]
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    ids = diagnostic_ids(diagnostics)
    assert "proof_field_invalid" in ids
    assert any("git_subcommand_dispatch" in d.message for d in diagnostics)


def test_check_proof_fields_residue_present_in_proof(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["residue_guard"]["after"][".lex"] = "present"
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    assert "proof_field_invalid" in diagnostic_ids(diagnostics)


def test_check_proof_fields_empty_boundary(tmp_path: Path) -> None:
    verifier = load_verifier()
    proof_data = _valid_proof()
    proof_data["cli_install_only_boundary"]["wont"] = []
    proof = _write_proof(tmp_path, proof_data)

    diagnostics = verifier.check_proof_fields(proof)

    ids = diagnostic_ids(diagnostics)
    assert "proof_field_invalid" in ids
    assert any("cli_install_only_boundary" in d.message for d in diagnostics)


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
    contract = tmp_path / "install-contract.md"
    contract.write_text("# contract\n", encoding="utf-8")
    lex_content = b"\x7fELFrelease-git-lex"
    serve_content = b"\x7fELFrelease-git-lex-serve"
    lex = _write_binary(tmp_path, "git-lex", lex_content)
    serve = _write_binary(tmp_path, "git-lex-serve", serve_content)
    manifest = _write_manifest(
        tmp_path,
        {
            "git-lex": {"sha256": _sha256_bytes(lex_content), "path": str(lex)},
            "git-lex-serve": {"sha256": _sha256_bytes(serve_content), "path": str(serve)},
        },
    )
    proof = _write_proof(tmp_path, _valid_proof())

    # empty residue root so the guard passes
    residue_root = tmp_path / "clean-root"
    residue_root.mkdir()

    count, diagnostics = verifier.verify(contract, manifest, proof, root=residue_root)

    assert diagnostics == []
    assert count == 2


def test_verify_aggregates_all_diagnostic_categories(tmp_path: Path) -> None:
    verifier = load_verifier()
    # missing contract + missing manifest + missing proof + residue present
    residue_root = tmp_path / "dirty-root"
    residue_root.mkdir()
    (residue_root / "Squad").mkdir()

    count, diagnostics = verifier.verify(
        tmp_path / "no-contract.md",
        tmp_path / "no-manifest.json",
        tmp_path / "no-proof.json",
        root=residue_root,
    )

    ids = diagnostic_ids(diagnostics)
    assert count == 0
    assert "contract_file_missing" in ids
    assert "missing_manifest_file" in ids
    assert "missing_proof_file" in ids
    assert "main_state_residue" in ids


def test_verify_skip_residue(tmp_path: Path) -> None:
    verifier = load_verifier()
    residue_root = tmp_path / "dirty-root"
    residue_root.mkdir()
    (residue_root / ".lex").mkdir()

    count, diagnostics = verifier.verify(
        tmp_path / "no-contract.md",
        tmp_path / "no-manifest.json",
        tmp_path / "no-proof.json",
        root=residue_root,
        check_residue=False,
    )

    assert "main_state_residue" not in diagnostic_ids(diagnostics)


# --------------------------------------------------------------------------
# CLI main()
# --------------------------------------------------------------------------


def test_main_exits_nonzero_on_diagnostics(tmp_path: Path) -> None:
    verifier = load_verifier()
    rc = verifier.main(["--contract", str(tmp_path / "nope.md"), "--manifest", str(tmp_path / "nope.json"),
                        "--proof", str(tmp_path / "nope.json"), "--root", str(tmp_path), "--skip-residue"])

    assert rc == 1


def test_main_exits_zero_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    verifier = load_verifier()
    contract = tmp_path / "install-contract.md"
    contract.write_text("# contract\n", encoding="utf-8")
    lex_content = b"\x7fELFrelease-git-lex"
    serve_content = b"\x7fELFrelease-git-lex-serve"
    lex = _write_binary(tmp_path, "git-lex", lex_content)
    serve = _write_binary(tmp_path, "git-lex-serve", serve_content)
    manifest = _write_manifest(
        tmp_path,
        {
            "git-lex": {"sha256": _sha256_bytes(lex_content), "path": str(lex)},
            "git-lex-serve": {"sha256": _sha256_bytes(serve_content), "path": str(serve)},
        },
    )
    proof = _write_proof(tmp_path, _valid_proof())
    residue_root = tmp_path / "clean-root"
    residue_root.mkdir()

    rc = verifier.main([
        "--contract", str(contract),
        "--manifest", str(manifest),
        "--proof", str(proof),
        "--root", str(residue_root),
    ])

    assert rc == 0
    captured = capsys.readouterr()
    assert "M065 S02 release-install verification passed: binaries=2/2 diagnostics=0" in captured.out


# --------------------------------------------------------------------------
# real-state integration (skip when the real install is not present)
# --------------------------------------------------------------------------


def test_current_real_state_check_passes() -> None:
    verifier = load_verifier()
    contract = verifier.DEFAULT_CONTRACT
    manifest = verifier.DEFAULT_MANIFEST
    proof = verifier.DEFAULT_PROOF
    if not contract.exists() or not manifest.exists() or not proof.exists():
        pytest.skip("real S02 install evidence anchors not present in this environment")

    count, diagnostics = verifier.verify(contract, manifest, proof)

    assert diagnostics == []
    assert count == 2

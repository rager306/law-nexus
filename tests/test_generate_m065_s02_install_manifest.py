from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "generate-m065-s02-install-manifest.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_m065_s02_install_manifest", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def diagnostic_ids(diagnostics: list[object]) -> set[str]:
    return {getattr(diagnostic, "diagnostic_id") for diagnostic in diagnostics}


def test_lists_required_diagnostic_ids() -> None:
    generator = load_generator()

    assert set(generator.DIAGNOSTIC_IDS) == {
        "vendor_source_missing",
        "provenance_drift",
        "build_record_missing",
        "build_record_parse_error",
        "install_failed",
        "binary_missing",
        "binary_not_executable",
    }


def test_build_manifest_shape() -> None:
    generator = load_generator()
    record = {
        "BUILD_DIR": "/root/vendor-source/git-lex",
        "RUSTC_VERSION": "rustc 1.94.1",
        "CARGO_VERSION": "cargo 1.94.1",
        "DURATION_MS": "252914",
        "INSTALL_RC": "0",
    }
    provenance = {
        "source_commit": "eaa4b24d144a78a8b8e4969404d74cf22267df1f",
        "cargo_toml_sha256": "2746659b",
        "cargo_lock_sha256": "3fbb6976",
    }
    binaries = {
        "git-lex": {"name": "git-lex", "sha256": "aa"},
        "git-lex-serve": {"name": "git-lex-serve", "sha256": "bb"},
    }

    manifest = generator.build_manifest(record, provenance, binaries)

    assert manifest["schema_version"] == "m065-s02-install-manifest/v1"
    assert manifest["source"]["source_remote"] == "https://github.com/repolex-ai/git-lex"
    assert manifest["source"]["source_commit"] == "eaa4b24d144a78a8b8e4969404d74cf22267df1f"
    assert manifest["source"]["provenance_reused_from"] == [
        "M051-S09",
        "M051-S10",
        "M052-S06",
        "M054-S01 D077",
        "S01 D089",
    ]
    assert manifest["install"]["command"] == "cargo install --path . --locked"
    assert manifest["install"]["profile"] == "release"
    assert manifest["install"]["install_rc"] == 0
    assert manifest["install"]["duration_ms"] == 252914
    assert manifest["install"]["rustc_version"] == "rustc 1.94.1"
    assert set(manifest["binaries"].keys()) == {"git-lex", "git-lex-serve"}
    # --version gap: no version claimed, surrogate is binary identity.
    assert manifest["version_gap"]["version_flag_rc"] is None
    assert manifest["manifest_continuation_of"] == "M051-S09 \u00a7T04 source-build manifest"


def test_parse_build_record_missing_file(tmp_path: Path) -> None:
    generator = load_generator()

    _, diagnostics = generator.parse_build_record(tmp_path / "nope.txt")

    assert "build_record_missing" in diagnostic_ids(diagnostics)


def test_parse_build_record_missing_field(tmp_path: Path) -> None:
    generator = load_generator()
    record_path = tmp_path / "build-record.txt"
    record_path.write_text("START_MS=1\nINSTALL_RC=0\n", encoding="utf-8")

    record, diagnostics = generator.parse_build_record(record_path)

    assert "build_record_parse_error" in diagnostic_ids(diagnostics)
    # parsed fields are still returned.
    assert record["START_MS"] == "1"


def test_check_install_rc_failed() -> None:
    generator = load_generator()

    diagnostics = generator.check_install_rc({"INSTALL_RC": "101"}, Path("/tmp/rec.txt"))

    assert "install_failed" in diagnostic_ids(diagnostics)


def test_check_install_rc_zero_is_clean() -> None:
    generator = load_generator()

    diagnostics = generator.check_install_rc({"INSTALL_RC": "0"}, Path("/tmp/rec.txt"))

    assert diagnostics == []


def test_check_vendor_provenance_missing_checkout(tmp_path: Path) -> None:
    generator = load_generator()

    actual, diagnostics = generator.check_vendor_provenance(tmp_path / "absent-vendor")

    assert "vendor_source_missing" in diagnostic_ids(diagnostics)
    assert actual == {}


def test_check_vendor_provenance_drift(tmp_path: Path) -> None:
    generator = load_generator()
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "Cargo.toml").write_text("not the real manifest\n", encoding="utf-8")
    (vendor / "Cargo.lock").write_text("not the real lockfile\n", encoding="utf-8")

    actual, diagnostics = generator.check_vendor_provenance(vendor)

    # no git repo in tmp_path -> source_commit is None; hashes cannot match.
    assert "provenance_drift" in diagnostic_ids(diagnostics)
    assert actual["cargo_toml_sha256"] is not None


def test_inspect_binary_missing(tmp_path: Path) -> None:
    generator = load_generator()

    _, diagnostics = generator.inspect_binary("git-lex", tmp_path)

    assert "binary_missing" in diagnostic_ids(diagnostics)


def test_inspect_binary_not_executable(tmp_path: Path) -> None:
    generator = load_generator()
    path = tmp_path / "git-lex"
    path.write_bytes(b"\x7fELF")
    os.chmod(path, 0o644)

    _, diagnostics = generator.inspect_binary("git-lex", tmp_path)

    assert "binary_not_executable" in diagnostic_ids(diagnostics)


def test_inspect_binary_present_executable_records_identity(tmp_path: Path) -> None:
    generator = load_generator()
    path = tmp_path / "git-lex"
    path.write_bytes(b"\x7fELFrelease-binary")
    os.chmod(path, 0o755)

    identity, diagnostics = generator.inspect_binary("git-lex", tmp_path)

    assert diagnostics == []
    assert identity["name"] == "git-lex"
    assert identity["profile"] == "release"
    assert isinstance(identity["sha256"], str) and len(identity["sha256"]) == 64
    assert identity["size_bytes"] == len(b"\x7fELFrelease-binary")
    assert identity["mode"] == "0o755"
    assert isinstance(identity["mtime"], int)


def test_current_real_state_check_passes() -> None:
    generator = load_generator()
    vendor = generator.DEFAULT_VENDOR_ROOT
    cargo_bin = generator.DEFAULT_CARGO_BIN
    if not vendor.exists() or not (cargo_bin / "git-lex").exists():
        pytest.skip("real install state not present in this environment")

    diagnostics = []
    _, prov_diags = generator.check_vendor_provenance(vendor)
    diagnostics.extend(prov_diags)
    for name in generator.BINARIES:
        _, bin_diags = generator.inspect_binary(name, cargo_bin)
        diagnostics.extend(bin_diags)

    assert diagnostics == []

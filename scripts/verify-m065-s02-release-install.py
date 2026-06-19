#!/usr/bin/env python3
"""Focused M065 S02 git-lex release-install verifier.

Deterministic inspection surface that re-asserts the Stage 2 install state
recorded by T01 (``install-manifest.json``) and T02 (``install-proof.json``),
confirms the S01 install-contract continuity, and re-checks the main-checkout
R047 residue guard. It lets a cold-start S03/S04 agent confirm the Stage-2
install *without* re-running the install, re-building, or invoking ``git lex``.

Inspection only. This script deliberately imports NO ``subprocess``: it does
NOT run ``git lex``, does NOT initialize ``.lex``, does NOT build, and does NOT
mutate state. Any such side effect would be a defect in the verifier itself.

Per the KNOWLEDGE rule (proof anchors = repository-relative JSON files), the
binary sha256 recomputation is an *inspected-state* check (does the installed
binary still match what the manifest recorded?), NOT the proof anchor itself;
the proof anchors are the tracked ``install-manifest.json`` and
``install-proof.json``. Diagnostic style mirrors S01's
``verify-m065-s01-install-contract.py`` for consistency.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s01" / "install-contract.md"
DEFAULT_MANIFEST = ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s02" / "install-manifest.json"
DEFAULT_PROOF = ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s02" / "install-proof.json"
MAIN_STATE_RESIDUE = (".lex", "Squad", "Raw", ".artifacts")

# Both binaries declared by Cargo.toml [[bin]] and installed by S02/T01.
EXPECTED_BINARIES = ("git-lex", "git-lex-serve")

# Diagnostic identifiers (falsifiable surface; cold readers can rely on the set).
DIAGNOSTIC_IDS = (
    "contract_file_missing",
    "missing_manifest_file",
    "missing_proof_file",
    "missing_installed_binary",
    "binary_identity_drift",
    "proof_field_invalid",
    "main_state_residue",
)

# Proof-field checks. Each tuple is (nested-key path, expected value, label).
#
# NOTE on key adaptation: the S01 contract section 5 item 2 reads "git lex
# --help exits 0". T02 proved that git intercepts --help for EXTERNAL
# subcommands and routes it to man(1), so ``git lex --help`` exits rc=16 with
# "No manual entry for git-lex" (recorded faithfully as git_lex_help_via_dispatch,
# is_gate:false). The proven cold-PATH *help resolution* rc=0 is the DIRECT
# binary invocation ``git-lex --help`` => ``proofs.git_lex_direct_help``. We
# therefore verify git_lex_direct_help (help exit 0 + banner), git_subcommand
#_dispatch (git found git-lex via cold PATH and dispatched 'lex': rc=2 + banner,
# contract item 4), and the version gap. Checking a nonexistent ``git_lex_help``
# key would make every correct install falsely fail, so we read the real key.
PROOF_FIELD_CHECKS: tuple[tuple[tuple[str, ...], Any, str], ...] = (
    (("proofs", "git_lex_direct_help", "exit_code"), 0,
     "git-lex --help cold-PATH direct resolution exit code (contract §5 item 2 intent)"),
    (("proofs", "git_lex_direct_help", "banner_found"), True,
     "git-lex --help banner found"),
    (("proofs", "git_lex_serve_help", "exit_code"), 0,
     "git-lex-serve --help cold-PATH exit code (contract §5 item 3)"),
    (("proofs", "git_lex_serve_help", "banner_found"), True,
     "git-lex-serve --help banner found"),
    (("proofs", "git_subcommand_dispatch", "primary_exit_code"), 2,
     "git lex subcommand dispatch exit code (contract §5 item 4: git found git-lex via cold PATH)"),
    (("proofs", "git_subcommand_dispatch", "primary_banner_found"), True,
     "git lex dispatch banner found (installed git-lex binary executed)"),
    (("proofs", "version_gap", "version_gap_confirmed"), True,
     "version gap confirmed (no version claim)"),
    (("proofs", "version_gap", "git_lex_version_rc"), 2,
     "git lex --version rc == 2 (gap, contract hard constraint)"),
    (("proofs", "version_gap", "git_lex_serve_version_rc"), 2,
     "git-lex-serve --version rc == 2 (gap)"),
    (("residue_guard", "before", ".lex"), "absent",
     "proof residue_guard.before .lex absent"),
    (("residue_guard", "before", "Squad"), "absent",
     "proof residue_guard.before Squad absent"),
    (("residue_guard", "before", "Raw"), "absent",
     "proof residue_guard.before Raw absent"),
    (("residue_guard", "before", ".artifacts"), "absent",
     "proof residue_guard.before .artifacts absent"),
    (("residue_guard", "after", ".lex"), "absent",
     "proof residue_guard.after .lex absent"),
    (("residue_guard", "after", "Squad"), "absent",
     "proof residue_guard.after Squad absent"),
    (("residue_guard", "after", "Raw"), "absent",
     "proof residue_guard.after Raw absent"),
    (("residue_guard", "after", ".artifacts"), "absent",
     "proof residue_guard.after .artifacts absent"),
)


@dataclass(frozen=True)
class Diagnostic:
    diagnostic_id: str
    path: str
    line: int
    message: str
    text: str


def _diagnostic(diagnostic_id: str, path: Path | str, line_no: int, message: str, text: str = "") -> Diagnostic:
    try:
        rel = str(Path(path).relative_to(ROOT))
    except (ValueError, TypeError):
        rel = str(path)
    return Diagnostic(
        diagnostic_id=diagnostic_id,
        path=rel,
        line=line_no,
        message=message,
        text=text.strip(),
    )


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_contract_file(contract: Path) -> list[Diagnostic]:
    if not contract.exists():
        return [_diagnostic("contract_file_missing", contract, 0,
                            f"S01 install-contract file is missing: {contract} (cross-slice contract continuity)")]
    return []


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def check_installed_binaries(manifest: Path) -> tuple[int, list[Diagnostic]]:
    """Recompute installed-binary identity and assert byte-for-byte equality
    with the manifest. Returns (binary_count_ok, diagnostics).

    The binary path is read from the manifest's recorded value (defaults to
    ~/.cargo/bin/<name> when the manifest omits it). sha256 recomputation is an
    inspected-state check, not a proof anchor.
    """
    diagnostics: list[Diagnostic] = []
    if not manifest.exists():
        diagnostics.append(_diagnostic("missing_manifest_file", manifest, 0,
                                       f"install-manifest is missing: {manifest} (T01 evidence anchor)"))
        return 0, diagnostics

    data = _load_json(manifest)
    if data is None:
        diagnostics.append(_diagnostic("missing_manifest_file", manifest, 0,
                                       f"install-manifest is not valid JSON: {manifest}"))
        return 0, diagnostics

    binaries = data.get("binaries")
    if not isinstance(binaries, dict):
        diagnostics.append(_diagnostic("missing_manifest_file", manifest, 0,
                                       "install-manifest has no 'binaries' object"))
        return 0, diagnostics

    binary_count_ok = 0
    for name in EXPECTED_BINARIES:
        recorded = binaries.get(name)
        if not isinstance(recorded, dict):
            diagnostics.append(_diagnostic("binary_identity_drift", manifest, 0,
                                           f"manifest binaries has no recorded entry for {name}"))
            continue

        recorded_sha = recorded.get("sha256")
        default_path = Path.home() / ".cargo" / "bin" / name
        recorded_path_raw = recorded.get("path", str(default_path))
        binary_path = Path(recorded_path_raw)

        if not binary_path.exists():
            diagnostics.append(_diagnostic("missing_installed_binary", binary_path, 0,
                                           f"installed binary is missing: {binary_path}"))
            continue

        if not os.access(binary_path, os.X_OK):
            # mode is part of recorded identity (manifest records mode "0o755");
            # a non-executable binary is an identity drift, not merely missing.
            diagnostics.append(_diagnostic("binary_identity_drift", binary_path, 0,
                                           f"installed binary is not executable: {binary_path}"))
            continue

        actual_sha = _sha256(binary_path)
        if actual_sha != recorded_sha:
            diagnostics.append(_diagnostic(
                "binary_identity_drift", binary_path, 0,
                f"sha256 drift for {name}: manifest records {recorded_sha} but installed binary recomputes to {actual_sha}",
            ))
            continue

        binary_count_ok += 1

    return binary_count_ok, diagnostics


def _dig(obj: Any, keys: tuple[str, ...]) -> tuple[bool, Any]:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return False, None
        cur = cur[key]
    return True, cur


def check_proof_fields(proof: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not proof.exists():
        diagnostics.append(_diagnostic("missing_proof_file", proof, 0,
                                       f"install-proof is missing: {proof} (T02 evidence anchor)"))
        return diagnostics

    data = _load_json(proof)
    if data is None:
        diagnostics.append(_diagnostic("missing_proof_file", proof, 0,
                                       f"install-proof is not valid JSON: {proof}"))
        return diagnostics

    for keys, expected, label in PROOF_FIELD_CHECKS:
        present, actual = _dig(data, keys)
        dotted = ".".join(keys)
        if not present:
            diagnostics.append(_diagnostic("proof_field_invalid", proof, 0,
                                           f"proof field missing: {dotted} ({label})"))
        elif actual != expected:
            diagnostics.append(_diagnostic("proof_field_invalid", proof, 0,
                                           f"proof field invalid: {dotted} expected {expected!r} but recorded {actual!r} ({label})"))

    # CLI-install-only boundary markers must be present (plan §3e).
    boundary = data.get("cli_install_only_boundary")
    if not isinstance(boundary, dict) or not isinstance(boundary.get("wont"), list) or not boundary["wont"]:
        diagnostics.append(_diagnostic("proof_field_invalid", proof, 0,
                                       "proof cli_install_only_boundary.wont is missing or empty (CLI-install-only boundary markers)"))

    return diagnostics


def check_main_state_residue(root: Path = ROOT) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for relative in MAIN_STATE_RESIDUE:
        path = root / relative
        if path.exists():
            diagnostics.append(_diagnostic("main_state_residue", path, 0,
                                           f"main checkout residue exists: {relative} (R047 contract-phase)"))
    return diagnostics


def verify(
    contract: Path = DEFAULT_CONTRACT,
    manifest: Path = DEFAULT_MANIFEST,
    proof: Path = DEFAULT_PROOF,
    *,
    root: Path = ROOT,
    check_residue: bool = True,
) -> tuple[int, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(check_contract_file(contract))
    binary_count_ok, bin_diags = check_installed_binaries(manifest)
    diagnostics.extend(bin_diags)
    diagnostics.extend(check_proof_fields(proof))
    if check_residue:
        diagnostics.extend(check_main_state_residue(root))
    return binary_count_ok, diagnostics


def _format_diagnostic(diagnostic: Diagnostic) -> str:
    location = diagnostic.path
    if diagnostic.line:
        location = f"{location}:{diagnostic.line}"
    suffix = f"\n  {diagnostic.text}" if diagnostic.text else ""
    return f"{diagnostic.diagnostic_id}: {location}: {diagnostic.message}{suffix}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the M065 S02 git-lex release-install state (Stage 2 of D084). Inspection only; does not run git lex.",
    )
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT,
                        help="S01 install-contract file (cross-slice continuity)")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST,
                        help="T01 install-manifest.json (binary identity anchor)")
    parser.add_argument("--proof", type=Path, default=DEFAULT_PROOF,
                        help="T02 install-proof.json (cold-PATH proof anchor)")
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="repository root for the R047 residue guard")
    parser.add_argument("--skip-residue", action="store_true",
                        help="skip the main-checkout residue guard")
    args = parser.parse_args(argv)

    binary_count_ok, diagnostics = verify(
        args.contract,
        args.manifest,
        args.proof,
        root=args.root,
        check_residue=not args.skip_residue,
    )
    if diagnostics:
        for diagnostic in diagnostics:
            print(_format_diagnostic(diagnostic))
        return 1

    total = len(EXPECTED_BINARIES)
    print(f"M065 S02 release-install verification passed: binaries={binary_count_ok}/{total} diagnostics=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())

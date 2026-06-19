#!/usr/bin/env python3
"""Focused M065 S03 git-lex workflow-proof verifier.

Deterministic inspection surface that re-asserts the Stage-2 isolated
install-rehearsal workflow state recorded by S03/T01
(``workflow-proof.json``) and re-checks the main-checkout R047 residue guard.
It lets a cold-start S04 agent confirm the Stage-2 workflow proof *without*
re-running the disposable lifecycle (which requires network + mktemp) or
invoking ``git lex``.

Inspection only. This script deliberately imports NO ``subprocess``: it does
NOT run ``git lex``, does NOT initialize ``.lex``, does NOT create a disposable
repo, and does NOT mutate state. Any such side effect would be a defect in the
verifier itself.

Per the KNOWLEDGE rule (proof anchors = repository-relative JSON files),
``workflow-proof.json`` is the proof anchor; this verifier re-asserts its gate
fields deterministically. Diagnostic style mirrors S02's
``verify-m065-s02-release-install.py`` for consistency.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROOF = ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s03" / "workflow-proof.json"
MAIN_STATE_RESIDUE = (".lex", "Squad", "Raw", ".artifacts")

# Diagnostic identifiers (falsifiable surface; cold readers can rely on the set).
DIAGNOSTIC_IDS = (
    "missing_proof_file",
    "proof_field_invalid",
    "cold_path_regression",
    "boundary_markers_missing",
    "main_state_residue",
)

# Key boundary-phrase markers that MUST appear as substrings in
# cli_install_only_boundary.wont (subset check, not exact-match of the full
# list). The T01 proof records a 6-item wont list; these 4 phrases are the
# contract-critical markers the verifier re-asserts.
EXPECTED_BOUNDARY_MARKERS = (
    "no main .lex init",
    "no R035/R037/R038 validation",
    "no serve/viz/listen",
    "no nuke/kit-update/save/create/join/raw",
)

# Proof-field checks (equality comparisons). Each tuple is (nested-key path,
# expected value, label). The cold_path_definition.vendor_dir_excluded check is
# handled separately by check_cold_path (emits cold_path_regression) so the
# cold-PATH regression is a named, actionable diagnostic. The
# stages.query.commit_results_count >= 1 gate is handled separately by
# check_commit_results_count (it is a >= comparison, not equality).
PROOF_FIELD_CHECKS: tuple[tuple[tuple[str, ...], Any, str], ...] = (
    (("disposable_repo", "is_inside_main_law_nexus"), False,
     "disposable repo is outside the main law-nexus checkout"),
    (("stages", "init", "exit_code"), 0,
     "git lex init exit code"),
    (("stages", "init", "auto_commit_landed"), True,
     "init auto-commit landed (MEM549 inversion: hook found git-lex on cold PATH)"),
    (("stages", "init", "hook_installed"), True,
     "init installed the pre-commit hook"),
    (("stages", "init", "lex_dir_created"), True,
     "init created the .lex directory"),
    (("stages", "content_seed_commit", "exit_code"), 0,
     "content seed plain git commit exit code"),
    (("stages", "content_seed_commit", "hook_extracted_spo"), True,
     "content seed commit triggered hook extract (.spo sidecar)"),
    (("stages", "sync", "exit_code"), 0,
     "git lex sync exit code"),
    (("stages", "query", "exit_code"), 0,
     "git lex query exit code"),
    (("stages", "validate", "exit_code"), 0,
     "git lex validate exit code"),
    (("stages", "list", "exit_code"), 0,
     "git lex list exit code"),
    (("residue_guard", "before", ".lex"), "absent",
     "residue_guard.before .lex absent"),
    (("residue_guard", "before", "Squad"), "absent",
     "residue_guard.before Squad absent"),
    (("residue_guard", "before", "Raw"), "absent",
     "residue_guard.before Raw absent"),
    (("residue_guard", "before", ".artifacts"), "absent",
     "residue_guard.before .artifacts absent"),
    (("residue_guard", "after", ".lex"), "absent",
     "residue_guard.after .lex absent"),
    (("residue_guard", "after", "Squad"), "absent",
     "residue_guard.after Squad absent"),
    (("residue_guard", "after", "Raw"), "absent",
     "residue_guard.after Raw absent"),
    (("residue_guard", "after", ".artifacts"), "absent",
     "residue_guard.after .artifacts absent"),
    (("residue_guard", "r047_contract_phase"), "honored",
     "residue_guard.r047_contract_phase honored"),
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


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _dig(obj: Any, keys: tuple[str, ...]) -> tuple[bool, Any]:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return False, None
        cur = cur[key]
    return True, cur


def check_proof_file(proof: Path) -> list[Diagnostic]:
    """File-level check: workflow-proof.json must exist and be valid JSON."""
    diagnostics: list[Diagnostic] = []
    if not proof.exists():
        diagnostics.append(_diagnostic("missing_proof_file", proof, 0,
                                       f"workflow-proof is missing: {proof} (S03/T01 evidence anchor)"))
        return diagnostics
    data = _load_json(proof)
    if data is None:
        diagnostics.append(_diagnostic("missing_proof_file", proof, 0,
                                       f"workflow-proof is not valid JSON: {proof}"))
        return diagnostics
    return diagnostics


def check_proof_fields(proof: Path) -> list[Diagnostic]:
    """Assert each PROOF_FIELD_CHECKS entry. Silently returns [] when the file
    is missing/invalid (check_proof_file reports that)."""
    diagnostics: list[Diagnostic] = []
    data = _load_json(proof)
    if data is None:
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
    return diagnostics


def check_cold_path(proof: Path) -> list[Diagnostic]:
    """Assert cold_path_definition.vendor_dir_excluded == True (cold-PATH
    regression guard). Silently returns [] when the file is missing/invalid."""
    diagnostics: list[Diagnostic] = []
    data = _load_json(proof)
    if data is None:
        return diagnostics
    present, actual = _dig(data, ("cold_path_definition", "vendor_dir_excluded"))
    if not present:
        diagnostics.append(_diagnostic("cold_path_regression", proof, 0,
                                       "proof field missing: cold_path_definition.vendor_dir_excluded (cold-PATH vendor-dir exclusion)"))
    elif actual is not True:
        diagnostics.append(_diagnostic("cold_path_regression", proof, 0,
                                       f"cold_path_definition.vendor_dir_excluded expected True but recorded {actual!r} (vendor-dir on cold PATH — false-pass risk from a debug binary)"))
    return diagnostics


def check_commit_results_count(proof: Path) -> list[Diagnostic]:
    """Assert stages.query.commit_results_count is an int >= 1 (the store is
    built and queryable). Silently returns [] when the file is missing/invalid."""
    diagnostics: list[Diagnostic] = []
    data = _load_json(proof)
    if data is None:
        return diagnostics
    present, actual = _dig(data, ("stages", "query", "commit_results_count"))
    if not present:
        diagnostics.append(_diagnostic("proof_field_invalid", proof, 0,
                                       "proof field missing: stages.query.commit_results_count (query >=1 gate)"))
    elif isinstance(actual, bool) or not isinstance(actual, int) or actual < 1:
        diagnostics.append(_diagnostic("proof_field_invalid", proof, 0,
                                       f"stages.query.commit_results_count expected int >= 1 but recorded {actual!r} (store not queryable / sync did not build)"))
    return diagnostics


def check_boundary_markers(proof: Path) -> list[Diagnostic]:
    """Assert cli_install_only_boundary.wont is a non-empty list containing
    each EXPECTED_BOUNDARY_MARKERS phrase as a substring (subset check).
    Silently returns [] when the file is missing/invalid."""
    diagnostics: list[Diagnostic] = []
    data = _load_json(proof)
    if data is None:
        return diagnostics
    boundary = data.get("cli_install_only_boundary")
    if not isinstance(boundary, dict):
        diagnostics.append(_diagnostic("boundary_markers_missing", proof, 0,
                                       "cli_install_only_boundary object is missing (CLI-install-only boundary markers)"))
        return diagnostics
    wont = boundary.get("wont")
    if not isinstance(wont, list) or not wont:
        diagnostics.append(_diagnostic("boundary_markers_missing", proof, 0,
                                       "cli_install_only_boundary.wont is missing or empty (CLI-install-only boundary markers)"))
        return diagnostics
    wont_text = "\n".join(str(item) for item in wont)
    for marker in EXPECTED_BOUNDARY_MARKERS:
        if marker not in wont_text:
            diagnostics.append(_diagnostic("boundary_markers_missing", proof, 0,
                                           f"boundary marker phrase missing from wont: {marker!r}"))
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
    proof: Path = DEFAULT_PROOF,
    *,
    root: Path = ROOT,
    check_residue: bool = True,
) -> tuple[bool, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(check_proof_file(proof))
    diagnostics.extend(check_proof_fields(proof))
    diagnostics.extend(check_cold_path(proof))
    diagnostics.extend(check_commit_results_count(proof))
    diagnostics.extend(check_boundary_markers(proof))
    if check_residue:
        diagnostics.extend(check_main_state_residue(root))
    proof_ok = not diagnostics
    return proof_ok, diagnostics


def _format_diagnostic(diagnostic: Diagnostic) -> str:
    location = diagnostic.path
    if diagnostic.line:
        location = f"{location}:{diagnostic.line}"
    suffix = f"\n  {diagnostic.text}" if diagnostic.text else ""
    return f"{diagnostic.diagnostic_id}: {location}: {diagnostic.message}{suffix}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the M065 S03 git-lex workflow-proof (Stage-2 isolated install-rehearsal). Inspection only; does not run git lex.",
    )
    parser.add_argument("--proof", type=Path, default=DEFAULT_PROOF,
                        help="S03/T01 workflow-proof.json (cold-PATH workflow proof anchor)")
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="repository root for the R047 residue guard")
    parser.add_argument("--skip-residue", action="store_true",
                        help="skip the main-checkout residue guard")
    args = parser.parse_args(argv)

    proof_ok, diagnostics = verify(
        args.proof,
        root=args.root,
        check_residue=not args.skip_residue,
    )
    if diagnostics:
        for diagnostic in diagnostics:
            print(_format_diagnostic(diagnostic))
        return 1

    print("M065 S03 workflow-proof verification passed: diagnostics=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())

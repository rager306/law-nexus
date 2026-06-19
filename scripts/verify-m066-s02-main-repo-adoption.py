#!/usr/bin/env python3
"""Focused M066 S02 git-lex main-repo operational-adoption verifier.

Deterministic inspection surface that re-asserts the Stage-3 main-repo
operational adoption state recorded by S02/T01
(``prd/architecture/acp/runtime/m066-s02/workflow-proof.json``) and re-checks
the main-checkout R047 residue *transition* guard. It lets a cold-start S03
agent confirm the Stage-3 operational adoption *without* re-running
``git lex init``/``sync`` (which mutates the main repo) or invoking ``git lex``.

RESIDUE TRANSITION NOTE: unlike M065 (where ``.lex`` absent = R047 honored), on
S02 ``.lex`` is EXPECTED present (operational adoption completed). The residue
guard therefore checks: ``.lex`` present (operational), ``Squad`` / ``Raw`` /
``.artifacts`` absent (out-of-contract surfaces). A missing ``.lex`` after S02 is
the ``main_state_residue`` diagnostic named ``lex_missing``; an unexpected
``Squad``/``Raw``/``.artifacts`` is ``unexpected_residue``.

Inspection only. This script deliberately imports NO ``subprocess``: it does
NOT run ``git lex``, does NOT initialize ``.lex``, does NOT build, and does
NOT mutate state. Any such side effect would be a defect in the verifier itself.

Diagnostic style mirrors S02/S03 verifiers (``Diagnostic`` dataclass +
``DIAGNOSTIC_IDS``) for consistency.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROOF = ROOT / "prd" / "architecture" / "acp" / "runtime" / "m066-s02" / "workflow-proof.json"
MAIN_CHECKOUT_RESIDUE = (".lex", "Squad", "Raw", ".artifacts")

# Diagnostic identifiers (falsifiable surface; cold readers can rely on the set).
DIAGNOSTIC_IDS = (
    "missing_proof_file",
    "proof_field_invalid",
    "lex_missing",            # .lex absent after S02 (operational adoption regression)
    "unexpected_residue",     # Squad/Raw/.artifacts present (out-of-contract surfaces)
    "cold_path_regression",
    "boundary_markers_missing",
    "overclaim_detected",
)

# Proof-field checks (equality comparisons). Each tuple is (nested-key path,
# expected value, label). The query commit_results_count >= 1 gate is handled
# separately by check_commit_results_count (>= comparison, not equality).
PROOF_FIELD_CHECKS: tuple[tuple[tuple[str, ...], Any, str], ...] = (
    (("init_result", "rc"), 0, "git lex init exit code"),
    (("init_result", "auto_commit_landed"), True,
     "init auto-commit landed (MEM549 inversion on REAL repo)"),
    (("init_result", "init_commit_count"), 2,
     "init created 2 commits (git lex init + git lex identity)"),
    (("init_result", "pre_commit_hook_installed"), True,
     "pre-commit hook installed by init"),
    (("init_result", "kit"), "repolex-ai/git-lex-kit-base",
     "base kit only (not ACP-kit source truth)"),
    (("sync_result", "rc"), 0, "git lex sync exit code"),
    (("query_result", "rc"), 0, "git lex query exit code"),
    (("query_result", "real_content"), True,
     "query returned real law-nexus content (count >= 1)"),
    (("validate_result", "rc"), 0, "git lex validate exit code"),
    (("validate_result", "base_kit_noop"), True,
     "validate is base-kit no-op (MEM566; NOT R035/R037/R038 validation)"),
    (("list_result", "rc"), 0, "git lex list exit code"),
    (("pre_init_state", "residue_before", ".lex"), "absent",
     "pre-init .lex absent (R047 contract-phase on S01)"),
    (("post_init_residue", ".lex"), "present",
     "post-init .lex present (operational adoption transition)"),
    (("post_init_residue", "Squad"), "absent",
     "post-init Squad absent (out-of-contract surface)"),
    (("post_init_residue", "Raw"), "absent",
     "post-init Raw absent (out-of-contract surface)"),
    (("post_init_residue", ".artifacts"), "absent",
     "post-init .artifacts absent (out-of-contract surface)"),
    (("cold_path_definition", "cargo_bin_on_path"), True,
     "~/.cargo/bin on PATH (release install, not debug-binary)"),
    (("cold_path_definition", "vendor_dir_excluded"), True,
     "vendor-dir excluded from PATH (no debug-binary false-pass)"),
)

# Contract-critical boundary markers that MUST appear in boundary_markers.
EXPECTED_BOUNDARY_MARKERS = (
    "R057_explicitly_gated",
    "R035_R037_R038_not_validated",
    "acp_kit_not_source_truth",
    "base_kit_only",
    "no_serve_viz_listen",
    "no_nuke_kit_update_save_create_join_raw",
)

# Overclaim detection (mirrors verify-m066-s01 / s04). The boundary negation
# must NOT false-positive.
_VALIDATION_VERBS = r"validated|validates|validating|validate"
_VERB_BEFORE_ID = re.compile(rf"\b(?:{_VALIDATION_VERBS})\s+R0?3[578]\b", re.IGNORECASE)
_ID_BEFORE_VERB = re.compile(
    rf"\bR0?3[578]\b(?:\s*/\s*R0?3[578]\b)*\s+(?:{_VALIDATION_VERBS})\b",
    re.IGNORECASE,
)
_NEGATION_AT_END = re.compile(r"(?:\bno|\bnot|\bwithout|\bnever|n['\u2019]t)\s*$", re.IGNORECASE)
OVERCLAIM_PATTERNS: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    ("verb_before_id", _VERB_BEFORE_ID),
    ("id_before_verb", _ID_BEFORE_VERB),
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


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _dig(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def check_proof_file(proof: Path) -> tuple[dict[str, Any], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    if not proof.exists():
        return {}, [_diagnostic("missing_proof_file", proof, 0, f"proof file is missing: {proof}")]
    try:
        data = json.loads(proof.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [_diagnostic("missing_proof_file", proof, 0, f"proof file is invalid JSON: {exc}")]
    return data, diagnostics


def check_proof_fields(data: dict[str, Any], proof: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for keys, expected, label in PROOF_FIELD_CHECKS:
        actual = _dig(data, keys)
        if actual is None:
            diagnostics.append(_diagnostic("proof_field_invalid", proof, 0,
                                           f"proof field missing: {'.'.join(keys)} ({label})"))
        elif actual != expected:
            diagnostics.append(_diagnostic("proof_field_invalid", proof, 0,
                                           f"proof field {'.'.join(keys)} = {actual!r}, expected {expected!r} ({label})"))
    # query commit_results_count >= 1 gate (separate, it is a >= comparison)
    qcount = _dig(data, ("query_result", "commit_results_count"))
    if not (isinstance(qcount, int) and qcount >= 1):
        diagnostics.append(_diagnostic("proof_field_invalid", proof, 0,
                                       f"query_result.commit_results_count = {qcount!r}, expected int >= 1 (real law-nexus content)"))
    return diagnostics


def check_cold_path(data: dict[str, Any], proof: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    excluded = _dig(data, ("cold_path_definition", "vendor_dir_excluded"))
    if excluded is not True:
        diagnostics.append(_diagnostic("cold_path_regression", proof, 0,
                                       "cold_path_definition.vendor_dir_excluded is not True (debug-binary false-pass risk)"))
    return diagnostics


def check_boundary_markers(data: dict[str, Any], proof: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    markers = _dig(data, ("boundary_markers",))
    if not isinstance(markers, dict):
        diagnostics.append(_diagnostic("boundary_markers_missing", proof, 0,
                                       "boundary_markers object missing from proof"))
        return diagnostics
    for marker in EXPECTED_BOUNDARY_MARKERS:
        if markers.get(marker) is not True:
            diagnostics.append(_diagnostic("boundary_markers_missing", proof, 0,
                                           f"contract-critical boundary marker not True: {marker!r}"))
    return diagnostics


def _preceded_by_negation(text: str, match_start: int) -> bool:
    return _NEGATION_AT_END.search(text[:match_start].lower()) is not None


def scan_overclaim(proof: Path) -> list[Diagnostic]:
    """Scan the proof JSON text for affirmative R035/R037/R038 validation overclaim."""
    diagnostics: list[Diagnostic] = []
    text = _read_text(proof)
    for name, pattern in OVERCLAIM_PATTERNS:
        for match in pattern.finditer(text):
            if _preceded_by_negation(text, match.start()):
                continue
            line_no = text.count("\n", 0, match.start()) + 1
            diagnostics.append(_diagnostic(
                "overclaim_detected", proof, line_no,
                f"affirmative R035/R037/R038 validation overclaim ({name}): {match.group(0)!r}",
                match.group(0),
            ))
    return diagnostics


def check_live_residue(root: Path = ROOT) -> tuple[dict[str, str], list[Diagnostic]]:
    """Live R047 residue *transition* guard.

    After S02: .lex MUST be present (operational adoption completed); Squad,
    Raw, .artifacts MUST be absent (out-of-contract surfaces). This is the
    inverse of the M065 contract-phase guard.
    """
    diagnostics: list[Diagnostic] = []
    status: dict[str, str] = {}
    for relative in MAIN_CHECKOUT_RESIDUE:
        path = root / relative
        present = path.exists()
        status[relative] = "present" if present else "absent"
        if relative == ".lex":
            if not present:
                diagnostics.append(_diagnostic("lex_missing", path, 0,
                                               ".lex absent after S02 (operational adoption regression — init did not complete)"))
        else:
            if present:
                diagnostics.append(_diagnostic("unexpected_residue", path, 0,
                                               f"unexpected out-of-contract residue present: {relative}"))
    return status, diagnostics


def verify(
    proof: Path = DEFAULT_PROOF,
    *,
    root: Path = ROOT,
    check_residue: bool = True,
) -> tuple[bool, list[Diagnostic], dict[str, Any]]:
    diagnostics: list[Diagnostic] = []

    data, file_diags = check_proof_file(proof)
    diagnostics.extend(file_diags)

    if data:
        diagnostics.extend(check_proof_fields(data, proof))
        diagnostics.extend(check_cold_path(data, proof))
        diagnostics.extend(check_boundary_markers(data, proof))
    diagnostics.extend(scan_overclaim(proof))

    if check_residue:
        live_residue, res_diags = check_live_residue(root)
    else:
        live_residue = {relative: "skipped" for relative in MAIN_CHECKOUT_RESIDUE}
        res_diags = []
    diagnostics.extend(res_diags)

    ok = not diagnostics
    summary: dict[str, Any] = {
        "proof_fields_checked": len(PROOF_FIELD_CHECKS),
        "boundary_markers_expected": len(EXPECTED_BOUNDARY_MARKERS),
        "live_residue": live_residue,
        "verdict": "stage3_operational_adoption_proven" if ok else "not_proven",
    }
    return ok, diagnostics, summary


def _format_diagnostic(diagnostic: Diagnostic) -> str:
    location = diagnostic.path
    if diagnostic.line:
        location = f"{location}:{diagnostic.line}"
    suffix = f"\n  {diagnostic.text}" if diagnostic.text else ""
    return f"{diagnostic.diagnostic_id}: {location}: {diagnostic.message}{suffix}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify M066 S02 main-repo operational adoption (Stage 3 of D084). "
                    "Inspection only; does not run git lex. Re-asserts workflow-proof.json gates "
                    "and the R047 residue TRANSITION (.lex present, Squad/Raw/.artifacts absent).",
    )
    parser.add_argument("--proof", type=Path, default=DEFAULT_PROOF)
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="repository root for the live residue guard")
    parser.add_argument("--skip-residue", action="store_true",
                        help="skip the main-checkout residue guard")
    args = parser.parse_args(argv)

    ok, diagnostics, _summary = verify(args.proof, root=args.root, check_residue=not args.skip_residue)

    if diagnostics:
        for diagnostic in diagnostics:
            print(_format_diagnostic(diagnostic))
        return 1

    print("M066 S02 main-repo-adoption verification passed: diagnostics=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())

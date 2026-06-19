#!/usr/bin/env python3
"""Focused M066 S01 git-lex operational adoption-contract verifier (Stage 3 of D084).

This script checks the tracked Stage 3 operational adoption contract only. It
is a deterministic inspection surface: it re-reads the contract, asserts all
six sections + boundary markers are present, asserts D093 is recorded in
DECISIONS.md, re-runs the prior M065 verifiers (S01 install-contract + S04
stage2-closure) fresh as child processes and asserts they still exit 0, scans
the contract for affirmative R035/R037/R038 validation overclaim (with a
negation-context guard), and checks the main law-nexus checkout has no residue
(R047 contract-phase honored on this slice — .lex appears in S02, not S01).

It does NOT run ``git lex``, does NOT initialize ``.lex``, does NOT clone, and
does NOT build. It imports ``subprocess`` SOLELY to re-run the two prior
*Python* verifiers as child processes. Any other side effect would be a defect
in the verifier itself.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "prd" / "architecture" / "acp" / "runtime" / "m066-s01" / "adoption-contract.md"
DEFAULT_DECISIONS = ROOT / ".gsd" / "DECISIONS.md"
MAIN_STATE_RESIDUE = (".lex", "Squad", "Raw", ".artifacts")

# The two prior M065 verifiers that must stay green (Stage 2 evidence must not
# regress). Each is a (verifier_key, ROOT-relative script path) pair.
PRIOR_VERIFIER_SCRIPTS: tuple[tuple[str, Path], ...] = (
    ("m065_s01_install_contract", ROOT / "scripts" / "verify-m065-s01-install-contract.py"),
    ("m065_s04_stage2_closure", ROOT / "scripts" / "verify-m065-s04-stage2-closure.py"),
)

# All six contract sections must be present.
EXPECTED_SECTIONS = (
    "## 1. R047 Gate A closing",
    "## 2. Operational-vs-architecture-binding boundary",
    "## 3. Pre-commit hook consequence",
    "## 4. CLI-operational boundary",
    "## 5. S02 acceptance",
    "## 6. Residue transition",
)

# Boundary markers that must appear in the contract.
EXPECTED_BOUNDARY_MARKERS = (
    "operational adoption",             # scope label (operational, not binding)
    "R047",                             # R047 Gate A closing
    "R057",                             # architecture-binding gate
    "explicitly gated",                 # R057 explicitly-gated posture
    "R035/R037/R038",                   # active, not source-truth
    "ACP-kit",                          # not source truth
    "base kit",                         # repolex-ai/git-lex-kit-base only
    "pre-commit hook",                  # inherent consequence documented
    "D084",                             # adoption roadmap
    "D093",                             # this contract
    "Stage 4",                          # reusability is later
)

# Overclaim detection — mirrors verify-m065-s04-stage2-closure.py. The boundary
# NEGATION 'no R035/R037/R038 validation' must NOT false-positive. These patterns
# require an AFFIRMATIVE validation VERB adjacent to the R-ID. A negation-context
# check also strips matches whose preceding token is no/not/without/never/n't.
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

DIAGNOSTIC_IDS = (
    "missing_contract_file",
    "missing_section",
    "missing_boundary_marker",
    "decision_not_recorded",
    "prior_verifier_failed",
    "main_state_residue",
    "overclaim_detected",
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


def check_contract_file(contract: Path) -> list[Diagnostic]:
    if not contract.exists():
        return [_diagnostic("missing_contract_file", contract, 0, f"contract file is missing: {contract}")]
    return []


def check_sections(text: str, contract: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for header in EXPECTED_SECTIONS:
        if header not in text:
            diagnostics.append(_diagnostic("missing_section", contract, 0, f"required contract section missing: {header}"))
    return diagnostics


def check_boundary_markers(text: str, contract: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for marker in EXPECTED_BOUNDARY_MARKERS:
        if marker not in text:
            diagnostics.append(_diagnostic("missing_boundary_marker", contract, 0, f"required boundary marker missing: {marker}"))
    return diagnostics


def check_decision_recorded(decisions: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    text = _read_text(decisions)
    if not text:
        diagnostics.append(_diagnostic("decision_not_recorded", decisions, 0, f"DECISIONS.md missing or empty: {decisions}"))
        return diagnostics
    # D093 must appear as a decision ID token (table row or heading), not just
    # as a back-reference inside another decision's prose. Match the ID at a
    # token boundary followed by a non-hex-char so D0930-style false positives
    # are avoided.
    if not re.search(r"\bD093\b(?![0-9A-Za-z])", text):
        diagnostics.append(_diagnostic("decision_not_recorded", decisions, 0, "D093 adoption-contract decision not recorded in DECISIONS.md"))
    return diagnostics


def _default_runner(cmd: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    """Run a prior verifier as a child process from ROOT; capture all output."""
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def check_prior_verifiers(runner: Callable[[list[str]], Any] | None = None) -> tuple[dict[str, int], list[Diagnostic]]:
    """Re-run the prior M065 verifiers fresh and assert each exits 0."""
    if runner is None:
        runner = _default_runner
    diagnostics: list[Diagnostic] = []
    per_rc: dict[str, int] = {}
    for name, script in PRIOR_VERIFIER_SCRIPTS:
        cmd = ["uv", "run", "python", str(script)]
        try:
            result = runner(cmd)
        except Exception as exc:  # timeout / file-not-found / env error
            per_rc[name] = -1
            diagnostics.append(_diagnostic("prior_verifier_failed", script, 0,
                                           f"{name} prior verifier could not run: {exc}"))
            continue
        rc = int(getattr(result, "returncode", -1))
        per_rc[name] = rc
        if rc != 0:
            diagnostics.append(_diagnostic("prior_verifier_failed", script, 0,
                                           f"{name} prior verifier exited {rc} (Stage 2 evidence must stay green)"))
    return per_rc, diagnostics


def _preceded_by_negation(text: str, match_start: int) -> bool:
    """True when the token immediately preceding the match is a negation word."""
    return _NEGATION_AT_END.search(text[:match_start].lower()) is not None


def scan_overclaim(contract_text: str, contract: Path) -> tuple[dict[str, Any], list[Diagnostic]]:
    """Scan the contract for affirmative R035/R037/R038 validation overclaim."""
    diagnostics: list[Diagnostic] = []
    total_hits = 0
    for name, pattern in OVERCLAIM_PATTERNS:
        for match in pattern.finditer(contract_text):
            if _preceded_by_negation(contract_text, match.start()):
                continue
            total_hits += 1
            line_no = contract_text.count("\n", 0, match.start()) + 1
            diagnostics.append(_diagnostic(
                "overclaim_detected", contract, line_no,
                f"affirmative R035/R037/R038 validation overclaim ({name}): {match.group(0)!r}",
                match.group(0),
            ))
    summary: dict[str, Any] = {
        "status": "clean" if not diagnostics else "overclaim_detected",
        "hits": total_hits,
        "patterns_scanned": len(OVERCLAIM_PATTERNS),
    }
    return summary, diagnostics


def check_main_state_residue(root: Path = ROOT) -> tuple[dict[str, str], list[Diagnostic]]:
    """Live R047 contract-phase residue guard. On S01 all four paths must be absent."""
    diagnostics: list[Diagnostic] = []
    status: dict[str, str] = {}
    for relative in MAIN_STATE_RESIDUE:
        path = root / relative
        if path.exists():
            status[relative] = "present"
            diagnostics.append(_diagnostic("main_state_residue", path, 0,
                                           f"main checkout residue exists: {relative} (R047 contract-phase on S01)"))
        else:
            status[relative] = "absent"
    return status, diagnostics


def verify(
    contract: Path = DEFAULT_CONTRACT,
    decisions: Path = DEFAULT_DECISIONS,
    *,
    root: Path = ROOT,
    runner: Callable[[list[str]], Any] | None = None,
    check_residue: bool = True,
) -> tuple[bool, list[Diagnostic], dict[str, Any]]:
    diagnostics: list[Diagnostic] = []

    diagnostics.extend(check_contract_file(contract))
    contract_text = _read_text(contract) if contract.exists() else ""
    if contract.exists():
        diagnostics.extend(check_sections(contract_text, contract))
        diagnostics.extend(check_boundary_markers(contract_text, contract))
        _oc_summary, oc_diags = scan_overclaim(contract_text, contract)
        diagnostics.extend(oc_diags)
    else:
        _oc_summary = {"status": "skipped", "hits": 0, "patterns_scanned": len(OVERCLAIM_PATTERNS)}

    diagnostics.extend(check_decision_recorded(decisions))

    per_rc, rc_diags = check_prior_verifiers(runner=runner)
    diagnostics.extend(rc_diags)

    if check_residue:
        live_residue, res_diags = check_main_state_residue(root)
    else:
        live_residue = {relative: "skipped" for relative in MAIN_STATE_RESIDUE}
        res_diags = []
    diagnostics.extend(res_diags)

    section_count = sum(1 for header in EXPECTED_SECTIONS if header in contract_text)
    ok = not diagnostics
    summary: dict[str, Any] = {
        "sections_present": section_count,
        "sections_expected": len(EXPECTED_SECTIONS),
        "prior_verifier_rc": per_rc,
        "live_residue": live_residue,
        "overclaim_scan": _oc_summary,
        "verdict": "stage3_contract_recorded" if ok else "not_recorded",
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
        description="Verify the M066 S01 git-lex operational adoption contract (Stage 3 of D084). "
                    "Inspection only; does not run git lex.",
    )
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="repository root for the R047 residue guard")
    parser.add_argument("--skip-residue", action="store_true",
                        help="skip the main-checkout residue guard")
    args = parser.parse_args(argv)

    ok, diagnostics, _summary = verify(
        args.contract,
        args.decisions,
        root=args.root,
        check_residue=not args.skip_residue,
    )

    if diagnostics:
        for diagnostic in diagnostics:
            print(_format_diagnostic(diagnostic))
        return 1

    section_count = sum(1 for header in EXPECTED_SECTIONS if header in _read_text(args.contract))
    print(f"M066 S01 adoption-contract verification passed: sections={section_count}/{len(EXPECTED_SECTIONS)} diagnostics=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Focused M065 S04 Stage 2 closure verifier.

Deterministic inspection surface that *independently re-confirms Stage 2 of
D084 is CLOSED* without re-running the disposable S03 workflow or invoking
``git lex``. It is the MEM541 trap-catcher for the milestone: the closer lane
does not re-prove Stage 2, so a cold-start Stage-3 agent runs this one command
to confirm, freshly, that (a) the three prior verifiers (S01/S02/S03) still
pass, (b) no tracked Stage-2 artifact or m065 script overclaims R035/R037/R038
validation, (c) the live main-checkout R047 residue guard is clean, and (d)
the contract-critical boundary markers are present across the proof set.

This is the evidence BEFORE the 'Stage 2 is closed' claim (verify-before-complete).

Inspection surface only. This script imports ``subprocess`` SOLELY to re-run the
three prior *Python* verifiers as child processes; it does NOT run ``git lex``,
does NOT initialize ``.lex``, does NOT build, does NOT clone, and does NOT
mutate state. Any other side effect would be a defect in the verifier itself.
The overclaim scan is a pure regex/text scan (no ``git``/``grep`` subprocess).

Per the KNOWLEDGE rule, the tracked proof artifacts are the proof anchors; this
verifier re-asserts them deterministically and records a structured review log
(``prd/architecture/acp/runtime/m065-s04/stage2-closure-review.json``). Diagnostic
style mirrors S02/S03 (``Diagnostic`` dataclass + ``DIAGNOSTIC_IDS``) for
consistency.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW = ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s04" / "stage2-closure-review.json"
SCHEMA_VERSION = "m065-s04-closure-review/v1"
MAIN_STATE_RESIDUE = (".lex", "Squad", "Raw", ".artifacts")

# The three prior verifiers, re-run fresh as child processes. Each is a
# (verifier_key, ROOT-relative script path) pair.
PRIOR_VERIFIER_SCRIPTS: tuple[tuple[str, Path], ...] = (
    ("s01", ROOT / "scripts" / "verify-m065-s01-install-contract.py"),
    ("s02", ROOT / "scripts" / "verify-m065-s02-release-install.py"),
    ("s03", ROOT / "scripts" / "verify-m065-s03-workflow-proof.py"),
)

# Corpus scanned for forbidden overclaim: the three tracked proof artifacts +
# the four m065 verifier scripts (S01-S04). S04 is included so the guard is
# self-policing; its source is written so the affirmative-verb patterns below
# never self-match (the regex literals use metacharacters, and prose keeps the
# validation verbs and the R-ID tokens non-adjacent).
OVERCLAIM_SCAN_FILES: tuple[Path, ...] = (
    ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s01" / "install-contract.md",
    ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s02" / "install-proof.json",
    ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s03" / "workflow-proof.json",
    ROOT / "scripts" / "verify-m065-s01-install-contract.py",
    ROOT / "scripts" / "verify-m065-s02-release-install.py",
    ROOT / "scripts" / "verify-m065-s03-workflow-proof.py",
    ROOT / "scripts" / "verify-m065-s04-stage2-closure.py",
)

# Contract-critical boundary markers that MUST appear across the proof set.
# Each entry is (label, alternative_substrings) — any one alternative satisfies
# the marker. The CLI-install-only marker accepts hyphen, underscore, or
# space-separated forms (the artifacts vary).
EXPECTED_BOUNDARY_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("no R035/R037/R038 validation", ("no R035/R037/R038 validation",)),
    ("R047", ("R047",)),
    ("CLI-install-only", ("CLI-install-only", "cli_install_only", "CLI install only")),
    ("D084", ("D084",)),
)

# Overclaim detection. The boundary NEGATION 'no R035/R037/R038 validation'
# uses the NOUN 'validation' preceded by 'no'; these patterns require an
# AFFIRMATIVE validation VERB *adjacent* to the R-ID (not the bare token), so
# the negation cannot false-positive by construction. A negation-context check
# also strips matches whose preceding token is no/not/without/never/n't, so
# legitimate denials are not flagged.
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

# Diagnostic identifiers (falsifiable surface; cold readers can rely on the set).
DIAGNOSTIC_IDS = (
    "prior_verifier_failed",
    "overclaim_detected",
    "main_state_residue",
    "boundary_markers_missing",
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


def _default_runner(cmd: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    """Run a prior verifier as a child process from ROOT; capture all output."""
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def check_prior_verifiers(runner: Callable[[list[str]], Any] | None = None) -> tuple[dict[str, int], list[Diagnostic]]:
    """Re-run the three prior verifiers fresh and assert each exits 0.

    ``runner`` is injectable for tests (returns an object exposing
    ``.returncode``). Returns (per_verifier_rc, diagnostics). A verifier that
    raises or exits non-zero emits a ``prior_verifier_failed`` diagnostic; the
    ``per_verifier_rc`` map always contains all three keys.
    """
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
    """True when the token immediately preceding the match is a negation word
    (no/not/without/never/n't) — those are legitimate denials, not overclaim."""
    return _NEGATION_AT_END.search(text[:match_start].lower()) is not None


def scan_overclaim(files: tuple[Path, ...] = OVERCLAIM_SCAN_FILES) -> tuple[dict[str, Any], list[Diagnostic]]:
    """Scan the corpus for affirmative R035/R037/R038 validation overclaim.

    Returns (summary, diagnostics). The summary records status, hit count, and
    the number of overclaim patterns applied. Diagnostics carry file:line and
    the matched phrase so a future overclaim is actionable.
    """
    diagnostics: list[Diagnostic] = []
    total_hits = 0
    for path in files:
        text = _read_text(path)
        for name, pattern in OVERCLAIM_PATTERNS:
            for match in pattern.finditer(text):
                if _preceded_by_negation(text, match.start()):
                    continue
                total_hits += 1
                line_no = text.count("\n", 0, match.start()) + 1
                diagnostics.append(_diagnostic(
                    "overclaim_detected", path, line_no,
                    f"affirmative R035/R037/R038 validation overclaim ({name}): {match.group(0)!r}",
                    match.group(0),
                ))
    summary: dict[str, Any] = {
        "status": "clean" if not diagnostics else "overclaim_detected",
        "hits": total_hits,
        "patterns_scanned": len(OVERCLAIM_PATTERNS),
    }
    return summary, diagnostics


def check_boundary_markers(files: tuple[Path, ...] = OVERCLAIM_SCAN_FILES) -> tuple[bool, list[Diagnostic]]:
    """Assert each EXPECTED_BOUNDARY_MARKERS entry is present as a substring
    somewhere across the proof set (concatenated text). Returns
    (all_present, diagnostics).
    """
    concatenated = "\n".join(_read_text(path) for path in files)
    diagnostics: list[Diagnostic] = []
    all_present = True
    for label, alternatives in EXPECTED_BOUNDARY_MARKERS:
        if any(alt in concatenated for alt in alternatives):
            continue
        all_present = False
        diagnostics.append(_diagnostic(
            "boundary_markers_missing", DEFAULT_REVIEW.parent, 0,
            f"contract-critical boundary marker missing across the proof set: {label!r}",
        ))
    return all_present, diagnostics


def check_main_state_residue(root: Path = ROOT) -> tuple[dict[str, str], list[Diagnostic]]:
    """Live R047 residue guard. Returns (per-path status map, diagnostics)."""
    diagnostics: list[Diagnostic] = []
    status: dict[str, str] = {}
    for relative in MAIN_STATE_RESIDUE:
        path = root / relative
        if path.exists():
            status[relative] = "present"
            diagnostics.append(_diagnostic("main_state_residue", path, 0,
                                           f"main checkout residue exists: {relative} (R047 contract-phase)"))
        else:
            status[relative] = "absent"
    return status, diagnostics


def verify(
    *,
    runner: Callable[[list[str]], Any] | None = None,
    root: Path = ROOT,
    scan_files: tuple[Path, ...] = OVERCLAIM_SCAN_FILES,
    check_residue: bool = True,
) -> tuple[bool, list[Diagnostic], dict[str, Any]]:
    """Run all closure checks and assemble the structured review log.

    Returns (closure_ok, diagnostics, review_log). The review log is the
    durable, cold-readable record written to DEFAULT_REVIEW by main().
    """
    diagnostics: list[Diagnostic] = []

    per_rc, rc_diags = check_prior_verifiers(runner=runner)
    diagnostics.extend(rc_diags)

    overclaim_summary, oc_diags = scan_overclaim(scan_files)
    diagnostics.extend(oc_diags)

    boundary_present, bnd_diags = check_boundary_markers(scan_files)
    diagnostics.extend(bnd_diags)

    if check_residue:
        live_residue, res_diags = check_main_state_residue(root)
    else:
        live_residue = {relative: "skipped" for relative in MAIN_STATE_RESIDUE}
        res_diags = []
    diagnostics.extend(res_diags)

    closure_ok = not diagnostics
    review_log: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "per_verifier_rc": per_rc,
        "overclaim_scan": overclaim_summary,
        "live_residue": live_residue,
        "boundary_markers_present": boundary_present,
        "closure_verdict": "stage2_closed" if closure_ok else "not_closed",
    }
    return closure_ok, diagnostics, review_log


def write_closure_review(review_log: dict[str, Any], path: Path = DEFAULT_REVIEW) -> Path:
    """Persist the structured review log (creates the parent directory)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(review_log, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def _format_diagnostic(diagnostic: Diagnostic) -> str:
    location = diagnostic.path
    if diagnostic.line:
        location = f"{location}:{diagnostic.line}"
    suffix = f"\n  {diagnostic.text}" if diagnostic.text else ""
    return f"{diagnostic.diagnostic_id}: {location}: {diagnostic.message}{suffix}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify M065 S04 Stage 2 closure: fresh re-run of the S01/S02/S03 verifiers, "
                    "R035/R037/R038 overclaim scan, live R047 residue guard, boundary markers. "
                    "Inspection only; does not run git lex.",
    )
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="repository root for the R047 residue guard")
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW,
                        help="tracked closure-review log path")
    parser.add_argument("--skip-residue", action="store_true",
                        help="skip the main-checkout residue guard")
    parser.add_argument("--no-write", action="store_true",
                        help="do not write the closure-review log (diagnostics still printed)")
    args = parser.parse_args(argv)

    closure_ok, diagnostics, review_log = verify(
        root=args.root,
        check_residue=not args.skip_residue,
    )

    if not args.no_write:
        write_closure_review(review_log, args.review)

    if diagnostics:
        for diagnostic in diagnostics:
            print(_format_diagnostic(diagnostic))
        return 1

    print("M065 S04 stage2-closure verification passed: diagnostics=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())

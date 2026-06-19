#!/usr/bin/env python3
"""Focused M066 S03 Stage 3 closure verifier.

Deterministic inspection surface that *independently re-confirms Stage 3 of
D084 is CLOSED* without re-running `git lex init`/`sync` (which mutates the main
repo) or invoking `git lex`. It is the closure trap-catcher for the milestone:
a cold-start Stage-4 agent runs this one command to confirm, freshly, that
(a) the M066 S01/S02 verifiers still pass, (b) the M065 S01/S02/S03 verifiers
still pass on their non-residue checks, (c) no tracked M066 artifact or script
overclaims R035/R037/R038 validation, (d) the live R047 residue *transition*
guard is clean (`.lex` present + `Squad`/`Raw`/`.artifacts` absent), and
(e) the contract-critical boundary markers are present across the proof set.

RESIDUE-TRANSITION AWARENESS (critical): after S02, `.lex` is EXPECTED present in
the main checkout. The M065 verifiers and the M066 S01 verifier all assert
`.lex` *absent* (their R047 contract-phase posture). Those residue-absent checks
regress post-S02 by design. This verifier therefore invokes every prior
verifier with `--skip-residue` and performs its OWN residue-transition check.
This is not a regression; it is the intended consequence of operational adoption.

Inspection surface only. This script imports ``subprocess`` SOLELY to re-run
prior *Python* verifiers as child processes (with `--skip-residue`); it does NOT
run ``git lex``, does NOT initialize ``.lex``, does NOT build, and does NOT
mutate state. The overclaim scan is a pure regex/text scan.
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
DEFAULT_REVIEW = ROOT / "prd" / "architecture" / "acp" / "runtime" / "m066-s03" / "stage3-closure-review.json"
SCHEMA_VERSION = "m066-s03-closure-review/v1"
# Residue transition: .lex is EXPECTED present (operational adoption); the others
# must stay absent (out-of-contract surfaces). This inverts the M065 posture.
RESIDUE_EXPECTED_PRESENT = (".lex",)
RESIDUE_EXPECTED_ABSENT = ("Squad", "Raw", ".artifacts")

# Prior verifiers to re-run. The M066 verifiers + M065 verifiers all support
# --skip-residue (their residue-absent checks regress post-S02 by design). Each
# tuple is (verifier_key, ROOT-relative script path, extra_args).
PRIOR_VERIFIERS: tuple[tuple[str, Path, tuple[str, ...]], ...] = (
    ("m066_s01_adoption_contract", ROOT / "scripts" / "verify-m066-s01-adoption-contract.py", ("--skip-residue",)),
    ("m066_s02_main_repo_adoption", ROOT / "scripts" / "verify-m066-s02-main-repo-adoption.py", ()),  # handles residue internally
    ("m065_s01_install_contract", ROOT / "scripts" / "verify-m065-s01-install-contract.py", ("--skip-residue",)),
    ("m065_s02_release_install", ROOT / "scripts" / "verify-m065-s02-release-install.py", ("--skip-residue",)),
    ("m065_s03_workflow_proof", ROOT / "scripts" / "verify-m065-s03-workflow-proof.py", ("--skip-residue",)),
)

# Corpus scanned for forbidden overclaim: the M066 proof artifacts + m066 scripts.
OVERCLAIM_SCAN_FILES: tuple[Path, ...] = (
    ROOT / "prd" / "architecture" / "acp" / "runtime" / "m066-s01" / "adoption-contract.md",
    ROOT / "prd" / "architecture" / "acp" / "runtime" / "m066-s02" / "workflow-proof.json",
    ROOT / "prd" / "architecture" / "acp" / "runtime" / "m066-s03" / "stage4-handoff.md",
    ROOT / "scripts" / "verify-m066-s01-adoption-contract.py",
    ROOT / "scripts" / "verify-m066-s02-main-repo-adoption.py",
    ROOT / "scripts" / "verify-m066-s03-stage3-closure.py",
)

# Contract-critical boundary markers that MUST appear across the proof set.
EXPECTED_BOUNDARY_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("R057 explicitly gated", ("R057", "explicitly gated", "explicitly-gated")),
    ("R035/R037/R038 not validated", ("R035/R037/R038",)),
    ("R047", ("R047",)),
    ("base kit only", ("base kit",)),
    ("D084", ("D084",)),
)

# Overclaim detection (mirrors s01/s04/s02 verifiers).
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
    "prior_verifier_failed",
    "overclaim_detected",
    "residue_transition_violation",
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
    return Diagnostic(diagnostic_id=diagnostic_id, path=rel, line=line_no, message=message, text=text.strip())


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _default_runner(cmd: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def check_prior_verifiers(runner: Callable[[list[str]], Any] | None = None) -> tuple[dict[str, int], list[Diagnostic]]:
    """Re-run prior verifiers fresh (with --skip-residue for residue-aware ones)."""
    if runner is None:
        runner = _default_runner
    diagnostics: list[Diagnostic] = []
    per_rc: dict[str, int] = {}
    for name, script, extra_args in PRIOR_VERIFIERS:
        cmd = ["uv", "run", "python", str(script), *extra_args]
        try:
            result = runner(cmd)
        except Exception as exc:
            per_rc[name] = -1
            diagnostics.append(_diagnostic("prior_verifier_failed", script, 0, f"{name} prior verifier could not run: {exc}"))
            continue
        rc = int(getattr(result, "returncode", -1))
        per_rc[name] = rc
        if rc != 0:
            diagnostics.append(_diagnostic("prior_verifier_failed", script, 0,
                                           f"{name} prior verifier exited {rc} (Stage 3 evidence must stay green)"))
    return per_rc, diagnostics


def _preceded_by_negation(text: str, match_start: int) -> bool:
    return _NEGATION_AT_END.search(text[:match_start].lower()) is not None


def scan_overclaim(files: tuple[Path, ...] = OVERCLAIM_SCAN_FILES) -> tuple[dict[str, Any], list[Diagnostic]]:
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
                diagnostics.append(_diagnostic("overclaim_detected", path, line_no,
                                               f"affirmative R035/R037/R038 validation overclaim ({name}): {match.group(0)!r}",
                                               match.group(0)))
    return {"status": "clean" if not diagnostics else "overclaim_detected", "hits": total_hits, "patterns_scanned": len(OVERCLAIM_PATTERNS)}, diagnostics


def check_boundary_markers(files: tuple[Path, ...] = OVERCLAIM_SCAN_FILES) -> tuple[bool, list[Diagnostic]]:
    concatenated = "\n".join(_read_text(path) for path in files)
    diagnostics: list[Diagnostic] = []
    all_present = True
    for label, alternatives in EXPECTED_BOUNDARY_MARKERS:
        if any(alt in concatenated for alt in alternatives):
            continue
        all_present = False
        diagnostics.append(_diagnostic("boundary_markers_missing", DEFAULT_REVIEW.parent, 0,
                                       f"contract-critical boundary marker missing across the proof set: {label!r}"))
    return all_present, diagnostics


def check_residue_transition(root: Path = ROOT) -> tuple[dict[str, str], list[Diagnostic]]:
    """R047 residue TRANSITION guard: .lex present (operational), others absent."""
    diagnostics: list[Diagnostic] = []
    status: dict[str, str] = {}
    for relative in RESIDUE_EXPECTED_PRESENT:
        path = root / relative
        present = path.exists()
        status[relative] = "present" if present else "absent"
        if not present:
            diagnostics.append(_diagnostic("residue_transition_violation", path, 0,
                                           f"{relative} absent after Stage 3 (operational adoption regression — expected present)"))
    for relative in RESIDUE_EXPECTED_ABSENT:
        path = root / relative
        present = path.exists()
        status[relative] = "present" if present else "absent"
        if present:
            diagnostics.append(_diagnostic("residue_transition_violation", path, 0,
                                           f"unexpected out-of-contract residue present: {relative} (must stay absent)"))
    return status, diagnostics


def verify(*, runner: Callable[[list[str]], Any] | None = None, root: Path = ROOT, scan_files: tuple[Path, ...] = OVERCLAIM_SCAN_FILES, check_residue: bool = True) -> tuple[bool, list[Diagnostic], dict[str, Any]]:
    diagnostics: list[Diagnostic] = []

    per_rc, rc_diags = check_prior_verifiers(runner=runner)
    diagnostics.extend(rc_diags)

    overclaim_summary, oc_diags = scan_overclaim(scan_files)
    diagnostics.extend(oc_diags)

    boundary_present, bnd_diags = check_boundary_markers(scan_files)
    diagnostics.extend(bnd_diags)

    if check_residue:
        live_residue, res_diags = check_residue_transition(root)
    else:
        live_residue = {**{r: "skipped" for r in RESIDUE_EXPECTED_PRESENT}, **{r: "skipped" for r in RESIDUE_EXPECTED_ABSENT}}
        res_diags = []
    diagnostics.extend(res_diags)

    closure_ok = not diagnostics
    review_log: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "per_verifier_rc": per_rc,
        "overclaim_scan": overclaim_summary,
        "live_residue_transition": live_residue,
        "boundary_markers_present": boundary_present,
        "closure_verdict": "stage3_closed" if closure_ok else "not_closed",
    }
    return closure_ok, diagnostics, review_log


def write_closure_review(review_log: dict[str, Any], path: Path = DEFAULT_REVIEW) -> Path:
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
        description="Verify M066 S03 Stage 3 closure: fresh re-run of M066 S01/S02 + M065 S01/S02/S03 verifiers "
                    "(with --skip-residue; residue-absent checks regress post-S02 by design), R035/R037/R038 overclaim scan, "
                    "live R047 residue TRANSITION guard (.lex present + Squad/Raw/.artifacts absent), boundary markers. "
                    "Inspection only; does not run git lex.",
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--skip-residue", action="store_true", help="skip the residue-transition guard")
    parser.add_argument("--no-write", action="store_true", help="do not write the closure-review log")
    args = parser.parse_args(argv)

    closure_ok, diagnostics, review_log = verify(root=args.root, check_residue=not args.skip_residue)
    if not args.no_write:
        write_closure_review(review_log, args.review)
    if diagnostics:
        for diagnostic in diagnostics:
            print(_format_diagnostic(diagnostic))
        return 1
    print("M066 S03 stage3-closure verification passed: diagnostics=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Focused M066 S03 Stage 4 handoff verifier.

Deterministic inspection surface that asserts the Stage 4 handoff document
(``prd/architecture/acp/runtime/m066-s03/stage4-handoff.md``) is complete and
self-consistent for a cold reader: required sections present, contract-critical
boundary markers present, the three proof anchors referenced, the MEM549-inversion
marker present, and zero affirmative R035/R037/R038 validation overclaim.

Inspection only. This script imports NO ``subprocess``: it does NOT run
``git lex``, does NOT initialize ``.lex``, and does NOT mutate state.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HANDOFF = ROOT / "prd" / "architecture" / "acp" / "runtime" / "m066-s03" / "stage4-handoff.md"

# Required top-level sections (## headers).
EXPECTED_SECTIONS = (
    "## Status",
    "## Stage 3 — proven",
    "## Stage 4 — scope and gates",
    "## Preserved boundaries",
    "## Open revisit-triggers",
    "## Verification",
    "## Decisions referenced",
)

# Boundary markers that must appear (Stage 3 carried-forward boundary contract).
EXPECTED_BOUNDARY_MARKERS = (
    "R035/R037/R038",          # active, non-source-truth
    "R047",                    # operational adoption completed
    "R053",                    # anti-feature
    "R057",                    # explicitly gated (architecture binding)
    "R046",                    # source-truth boundary
    "R048",                    # reusable-core / profile boundary
    "explicitly gated",        # R057 posture
    "base kit",                # base kit only (not ACP-kit source truth)
    "D084",                    # adoption roadmap
    "D093",                    # Stage 3 adoption contract
    "MEM549",                  # inversion marker
)

# Proof anchors that must be referenced (repo-relative paths).
EXPECTED_PROOF_ANCHORS = (
    "prd/architecture/acp/runtime/m066-s01/adoption-contract.md",
    "prd/architecture/acp/runtime/m066-s02/workflow-proof.json",
    "prd/architecture/acp/runtime/m065-s04/stage3-handoff.md",
)

# Overclaim detection (mirrors closure verifier).
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
    "missing_handoff_file",
    "missing_section",
    "missing_boundary_marker",
    "missing_proof_anchor",
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
    return Diagnostic(diagnostic_id=diagnostic_id, path=rel, line=line_no, message=message, text=text.strip())


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def check_handoff_file(handoff: Path) -> list[Diagnostic]:
    if not handoff.exists():
        return [_diagnostic("missing_handoff_file", handoff, 0, f"handoff file is missing: {handoff}")]
    return []


def check_sections(text: str, handoff: Path) -> tuple[int, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    count = 0
    for header in EXPECTED_SECTIONS:
        if header in text:
            count += 1
        else:
            diagnostics.append(_diagnostic("missing_section", handoff, 0, f"required section missing: {header}"))
    return count, diagnostics


def check_boundary_markers(text: str, handoff: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for marker in EXPECTED_BOUNDARY_MARKERS:
        if marker not in text:
            diagnostics.append(_diagnostic("missing_boundary_marker", handoff, 0, f"required boundary marker missing: {marker}"))
    return diagnostics


def check_proof_anchors(text: str, handoff: Path) -> tuple[int, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    count = 0
    for anchor in EXPECTED_PROOF_ANCHORS:
        if anchor in text:
            count += 1
        else:
            diagnostics.append(_diagnostic("missing_proof_anchor", handoff, 0, f"required proof anchor not referenced: {anchor}"))
    return count, diagnostics


def _preceded_by_negation(text: str, match_start: int) -> bool:
    return _NEGATION_AT_END.search(text[:match_start].lower()) is not None


def scan_overclaim(text: str, handoff: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for name, pattern in OVERCLAIM_PATTERNS:
        for match in pattern.finditer(text):
            if _preceded_by_negation(text, match.start()):
                continue
            line_no = text.count("\n", 0, match.start()) + 1
            diagnostics.append(_diagnostic("overclaim_detected", handoff, line_no,
                                           f"affirmative R035/R037/R038 validation overclaim ({name}): {match.group(0)!r}",
                                           match.group(0)))
    return diagnostics


def verify(handoff: Path = DEFAULT_HANDOFF) -> tuple[bool, list[Diagnostic], dict[str, int]]:
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(check_handoff_file(handoff))
    text = _read_text(handoff)
    section_count, sec_diags = check_sections(text, handoff) if handoff.exists() else (0, [])
    diagnostics.extend(sec_diags)
    diagnostics.extend(check_boundary_markers(text, handoff) if handoff.exists() else [])
    anchor_count, anchor_diags = check_proof_anchors(text, handoff) if handoff.exists() else (0, [])
    diagnostics.extend(anchor_diags)
    diagnostics.extend(scan_overclaim(text, handoff) if handoff.exists() else [])
    ok = not diagnostics
    return ok, diagnostics, {"sections": section_count, "anchors": anchor_count, "boundary_markers": len(EXPECTED_BOUNDARY_MARKERS)}


def _format_diagnostic(diagnostic: Diagnostic) -> str:
    location = diagnostic.path
    if diagnostic.line:
        location = f"{location}:{diagnostic.line}"
    suffix = f"\n  {diagnostic.text}" if diagnostic.text else ""
    return f"{diagnostic.diagnostic_id}: {location}: {diagnostic.message}{suffix}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the M066 S03 Stage 4 handoff document (sections, boundary markers, proof anchors, overclaim). "
                    "Inspection only; does not run git lex.",
    )
    parser.add_argument("--handoff", type=Path, default=DEFAULT_HANDOFF)
    args = parser.parse_args(argv)

    ok, diagnostics, counts = verify(args.handoff)
    if diagnostics:
        for diagnostic in diagnostics:
            print(_format_diagnostic(diagnostic))
        return 1
    print(f"M066 S03 stage4-handoff verification passed: diagnostics=0 (sections={counts['sections']}, markers={counts['boundary_markers']}, anchors={counts['anchors']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

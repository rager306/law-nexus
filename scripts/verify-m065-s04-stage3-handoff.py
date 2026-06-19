#!/usr/bin/env python3
"""Focused M065 S04 Stage 3 handoff verifier.

Deterministic inspection surface that asserts the Stage 3 handoff document
(``prd/architecture/acp/runtime/m065-s04/stage3-handoff.md``) is well-formed
for a cold-start Stage-3 agent: every REQUIRED section is present, every
contract-critical boundary marker is present, the three proof-anchor paths are
referenced, the MEM549-inversion marker (``auto_commit_landed``) is present, and
there is ZERO affirmative R035/R037/R038 validation overclaim.

This is the evidence BEFORE the 'handoff is reader-complete' claim
(verify-before-complete). It complements the Stage-2 closure verifier
(``scripts/verify-m065-s04-stage2-closure.py``): that verifier confirms Stage 2
is *closed*; this verifier confirms the Stage-3 *handoff* is complete and honest.

Inspection surface only — stdlib-only and NO subprocess. It reads the handoff
document (and, for self-policing, its own source) as text and runs a pure regex
scan. It does NOT run ``git lex``, does NOT initialize ``.lex``, does NOT
build, does NOT clone, and does NOT mutate state. Any other side effect would be
a defect in the verifier itself.

The overclaim detection reuses the EXACT same affirmative-verb-adjacency design
as T01 (Stage-2 closure): patterns require a validation VERB
(validated|validates|validating|validate) directly adjacent to an R035/R037/R038
token, never the bare token, and a negation-context guard strips legitimate
denials (no/not/without/never/n't). The handoff doc and this verifier's own
source are both scanned, so the guard is self-policing; its literals use regex
metacharacters and prose keeps verbs and R-IDs non-adjacent so the self-scan
returns 0 hits.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HANDOFF = (
    ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s04" / "stage3-handoff.md"
)
VERIFIER_SOURCE = Path(__file__).resolve()

# The five REQUIRED section headers (asserted verbatim as substrings). The em
# dashes match the handoff document exactly.
EXPECTED_SECTIONS: tuple[str, ...] = (
    "## Status",
    "## Stage 2 \u2014 proven",
    "## Stage 3 \u2014 scope and gates",
    "## Preserved boundaries",
    "## Open revisit-triggers",
)

# Contract-critical boundary markers that MUST appear as a substring in the
# handoff document. Each entry is (label, alternative_substrings) — any one
# alternative satisfies the marker. The CLI-install-only marker accepts the
# hyphenated or space-separated form.
REQUIRED_BOUNDARY_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("R035/R037/R038", ("R035/R037/R038",)),
    ("R047", ("R047",)),
    ("R057", ("R057",)),
    ("R053", ("R053",)),
    ("CLI-install-only", ("CLI-install-only", "CLI install only")),
    ("D084 Stage 3", ("D084 Stage 3",)),
    ("eaa4b24d", ("eaa4b24d",)),
)

# The three tracked proof-anchor paths that MUST be referenced from the handoff
# document (full ROOT-relative paths — a cold reader needs to locate them).
REQUIRED_PROOF_ANCHOR_PATHS: tuple[str, ...] = (
    "prd/architecture/acp/runtime/m065-s01/install-contract.md",
    "prd/architecture/acp/runtime/m065-s02/install-proof.json",
    "prd/architecture/acp/runtime/m065-s03/workflow-proof.json",
)

# The MEM549-inversion marker (S03 workflow-proof proves the init auto-commit
# landed because the installed hook found git-lex on cold PATH).
MEM549_MARKER = "auto_commit_landed"

# Corpus scanned for forbidden overclaim: the handoff document (the artifact
# this verifier governs) + this verifier's own source (self-policing). The
# verifier source is written so the affirmative-verb patterns below never
# self-match (regex metacharacters break verb/R-ID adjacency; prose keeps them
# non-adjacent).
def _overclaim_scan_files(handoff: Path = DEFAULT_HANDOFF) -> tuple[Path, ...]:
    return (handoff, VERIFIER_SOURCE)

# Overclaim detection — IDENTICAL design to T01 (Stage-2 closure). Patterns
# require an AFFIRMATIVE validation VERB *adjacent* to an R035/R037/R038 token
# (not the bare token), so the boundary NEGATION "no R035/R037/R038 validation"
# (noun) cannot false-positive by construction. A negation-context check also
# strips matches whose preceding token is no/not/without/never/n't.
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
    "missing_section",
    "missing_boundary_marker",
    "missing_proof_anchor",
    "missing_mem549_marker",
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


def _preceded_by_negation(text: str, match_start: int) -> bool:
    """True when the token immediately preceding the match is a negation word
    (no/not/without/never/n't) — those are legitimate denials, not overclaim."""
    return _NEGATION_AT_END.search(text[:match_start].lower()) is not None


def check_sections(text: str, source: Path = DEFAULT_HANDOFF) -> list[Diagnostic]:
    """Assert each EXPECTED_SECTIONS header is present as a substring."""
    diagnostics: list[Diagnostic] = []
    for header in EXPECTED_SECTIONS:
        if header not in text:
            diagnostics.append(_diagnostic(
                "missing_section", source, 0,
                f"required section header missing: {header!r}",
            ))
    return diagnostics


def check_boundary_markers(text: str, source: Path = DEFAULT_HANDOFF) -> list[Diagnostic]:
    """Assert each REQUIRED_BOUNDARY_MARKERS entry is present as a substring."""
    diagnostics: list[Diagnostic] = []
    for label, alternatives in REQUIRED_BOUNDARY_MARKERS:
        if any(alt in text for alt in alternatives):
            continue
        diagnostics.append(_diagnostic(
            "missing_boundary_marker", source, 0,
            f"contract-critical boundary marker missing: {label!r}",
        ))
    return diagnostics


def check_proof_anchors(text: str, source: Path = DEFAULT_HANDOFF) -> list[Diagnostic]:
    """Assert each REQUIRED_PROOF_ANCHOR_PATHS path is referenced as a substring."""
    diagnostics: list[Diagnostic] = []
    for anchor in REQUIRED_PROOF_ANCHOR_PATHS:
        if anchor not in text:
            diagnostics.append(_diagnostic(
                "missing_proof_anchor", source, 0,
                f"proof-anchor path not referenced in handoff: {anchor!r}",
            ))
    return diagnostics


def check_mem549_marker(text: str, source: Path = DEFAULT_HANDOFF) -> list[Diagnostic]:
    """Assert the MEM549-inversion marker is present as a substring."""
    if MEM549_MARKER not in text:
        return [_diagnostic(
            "missing_mem549_marker", source, 0,
            f"MEM549-inversion marker missing: {MEM549_MARKER!r}",
        )]
    return []


def scan_overclaim(files: tuple[Path, ...] | None = None) -> tuple[dict[str, Any], list[Diagnostic]]:
    """Scan the corpus for affirmative R035/R037/R038 validation overclaim.

    Returns (summary, diagnostics). The summary records status, hit count, and
    the number of overclaim patterns applied. Diagnostics carry file:line and
    the matched phrase so a future overclaim is actionable.
    """
    if files is None:
        files = _overclaim_scan_files()
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


def verify(handoff: Path = DEFAULT_HANDOFF) -> tuple[bool, list[Diagnostic], dict[str, Any]]:
    """Run all handoff checks. Returns (handoff_ok, diagnostics, summary)."""
    diagnostics: list[Diagnostic] = []
    text = _read_text(handoff)

    diagnostics.extend(check_sections(text, handoff))
    diagnostics.extend(check_boundary_markers(text, handoff))
    diagnostics.extend(check_proof_anchors(text, handoff))
    diagnostics.extend(check_mem549_marker(text, handoff))

    overclaim_summary, oc_diags = scan_overclaim(_overclaim_scan_files(handoff))
    diagnostics.extend(oc_diags)

    summary: dict[str, Any] = {
        "handoff_ok": not diagnostics,
        "overclaim_scan": overclaim_summary,
        "sections_expected": len(EXPECTED_SECTIONS),
        "boundary_markers_expected": len(REQUIRED_BOUNDARY_MARKERS),
        "proof_anchors_expected": len(REQUIRED_PROOF_ANCHOR_PATHS),
    }
    return not diagnostics, diagnostics, summary


def _format_diagnostic(diagnostic: Diagnostic) -> str:
    location = diagnostic.path
    if diagnostic.line:
        location = f"{location}:{diagnostic.line}"
    suffix = f"\n  {diagnostic.text}" if diagnostic.text else ""
    return f"{diagnostic.diagnostic_id}: {location}: {diagnostic.message}{suffix}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify M065 S04 Stage 3 handoff document: required sections, "
                    "boundary markers, proof-anchor references, MEM549-inversion marker, "
                    "and zero R035/R037/R038 overclaim. Inspection only; stdlib only, no subprocess.",
    )
    parser.add_argument("--handoff", type=Path, default=DEFAULT_HANDOFF,
                        help="tracked Stage 3 handoff document path")
    args = parser.parse_args(argv)

    handoff_ok, diagnostics, summary = verify(args.handoff)

    if diagnostics:
        for diagnostic in diagnostics:
            print(_format_diagnostic(diagnostic))
        return 1

    print(
        "M065 S04 stage3-handoff verification passed: diagnostics=0 "
        f"(sections={summary['sections_expected']}, "
        f"markers={summary['boundary_markers_expected']}, "
        f"anchors={summary['proof_anchors_expected']}, "
        f"overclaim={summary['overclaim_scan']['hits']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

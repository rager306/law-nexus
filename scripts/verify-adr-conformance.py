#!/usr/bin/env python3
"""Verify D098 lifecycle-tag and ADR-reference conformance of architectural claims.

This is the compliance-gate tooling named by ADR-0002 ("ADR standard and the
compliance-gate / ACP-checkpoint split"). It is a read-only checker over the
architectural "claim files" in scope for D098:
``prd/ARCHITECTURE.md``, ``prd/02_architecture.md``, and ``doc/adr/*.md``.

ADR-0002 establishes two enforcement mechanisms and keeps them strictly
separated:

- The **compliance gate** (this tool) is structural, one-time, and may
  hard-fail. It enforces structural invariants of the code architecture and of
  the ADR record standard.
- The **ACP checkpoint** is behavioural, continuous, and must NOT block
  (detect + log + flag, per D098).

This script is the gate half. It runs two per-claim checks. Per D098, claims are
**targeted, not all-prose** — only lines that make a binding
architecture/technology assertion are treated as claims.

1. ``untagged-claim``  — an architectural claim (a line making a binding
   adoption / structure assertion) must carry one of the D098 lifecycle tags:
   ``[proposed]`` / ``[bounded]`` / ``[smoke]`` / ``[validated]`` /
   ``[deferred]`` (case-insensitive bracket match).

2. ``missing-adr-ref`` — an architectural claim that lives in a *non-ADR* claim
   file must reference an ADR (``ADR-NNNN``). A claim that lives *inside* an ADR
   file is already documented by that ADR and does not need an additional ref.

"Architectural claim" detection is deliberately conservative to honour D098's
anti-smoothing intent ("targeted, not all-prose"). A line is treated as a
claim when it matches either:

- ``CLAIM_VERB_RE`` -- a binding adoption / structure verb with a Capitalized
  named target (``uses FalkorDB``, ``adopts Pydantic``, ``depends on FalkorDB``)
  or a specific structural phrase (``is implemented as``, ``is built on``,
  ``chose``, ``decided to use/adopt/...``). The Capitalized-target requirement
  rejects prose like "one use case", "value depends on it", "Depends on source
  wording".
- ``IMPERATIVE_CLAIM_RE`` -- a line opening with an architectural decision verb
  in the imperative mood (``Adopt a ...``, ``Establish ...``, ``Build ...``),
  but only outside an "Alternatives Considered" section and not on an
  ``Option A/B/C`` header (rejected options are not current architecture).

Lines inside fenced code blocks, YAML front matter, table separators, and
questions are never flagged. This trades recall for precision on purpose: a
few untagged claims with lowercase targets may slip through and must be caught
by review (T03 retag), but the gate never noises on ordinary prose.

Exit code: ``0`` when conformant, ``1`` when any finding is reported (gate
behaviour, so T04 can wire it as a hard gate). Use ``--report-only`` to always
exit ``0`` (checkpoint / non-blocking use).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# D098 lifecycle tag vocabulary. Matched case-insensitively as ``[tag]``.
LIFECYCLE_TAGS: tuple[str, ...] = (
    "proposed",
    "bounded",
    "smoke",
    "validated",
    "deferred",
)
LIFECYCLE_TAG_RE = re.compile(
    r"\[(" + "|".join(LIFECYCLE_TAGS) + r")\]",
    re.IGNORECASE,
)

# An ADR reference: ``ADR-0001``, ``ADR 0001``, or the bracketed ``[ADR-0001]``
# form (the ``ADR-0001`` substring inside it matches).
ADR_REF_RE = re.compile(r"\bADR[-\s]?(\d{4})\b", re.IGNORECASE)

# Conservative architectural-claim signal. A line (outside a code fence and
# front matter) matching one of these patterns is treated as a binding
# architectural assertion and must carry a D098 lifecycle tag (and, in a
# non-ADR file, an ADR reference). Kept narrow on purpose to honour D098's
# "targeted, not all-prose" intent:
#
# - Adoption/dependency verbs (uses, adopts, depends on, relies on, is based on)
#   require a Capitalized named target to follow (e.g. "uses FalkorDB",
#   "depends on Pydantic"). This rejects prose such as "one use case",
#   "value depends on it", and "Depends on source wording", which are not
#   architectural adoption claims.
# - Structural decision phrases ("is implemented as", "is built on", "chose",
#   "decided to use/adopt/...") are specific enough on their own.
#
# Ordinary prose verbs ("describes", "states", "shows", "explains") are
# intentionally absent so narrative text is never flagged.
_CLAIM_VERB_ALTERNATIVES = (
    r"\buses?\s+(?-i:[A-Z])[A-Za-z0-9_-]*\b",
    r"\badopt(?:s|ed|ing)?\s+(?-i:[A-Z])[A-Za-z0-9_-]*\b",
    r"\bdepends?\s+on\s+(?-i:[A-Z])[A-Za-z0-9_-]*\b",
    r"\brel(?:y|ies)\s+on\s+(?-i:[A-Z])[A-Za-z0-9_-]*\b",
    r"\bis\s+based\s+on\s+(?-i:[A-Z])[A-Za-z0-9_-]*\b",
    r"\bis\s+implemented\s+(?:as|via|by|using)\b",
    r"\bis\s+built\s+(?:on|upon|using)\b",
    r"\bchose\b",
    r"\bdecided?\s+to\s+(?:use|adopt|implement|build)\b",
)
CLAIM_VERB_RE = re.compile("|".join(_CLAIM_VERB_ALTERNATIVES), re.IGNORECASE)

# Imperative decision claims: a line that opens (after optional blockquote /
# list markup) with an architectural decision verb in the imperative mood
# ("Adopt a ...", "Use ...", "Establish ..."). These appear in ADR Decision /
# Consequences sections. They are claims only outside "Alternatives Considered"
# (rejected options are not current architecture) and when the line is not an
# alternative header ("Option A: ..."). An imperative that lives inside an
# ADR file's own ## Decision section is EXEMPT from the untagged-claim check:
# the Decision section is the binding decision itself, and its lifecycle is
# carried by the ADR Status line plus the per-claim lifecycle tags in the
# Decision's subsections (mirroring how ADR-internal claims are already exempt
# from the missing-adr-ref check). Imperatives elsewhere (Context/Consequences,
# or any non-ADR file) are still checked. See find_claim_findings.
_IMPERATIVE_LEAD = r"^(?:>\s*)?(?:[-*]\s+)?(?:Adopt|Use|Establish|Build|Implement|Choose|Avoid)\b"
IMPERATIVE_CLAIM_RE = re.compile(_IMPERATIVE_LEAD, re.IGNORECASE)

# A line that names a considered-but-rejected alternative (an ADR "Option A/B/C"
# header) is never a current architectural claim.
ALTERNATIVE_HEADER_RE = re.compile(r"^\s*#{0,6}\s*Option\s+[A-Z0-9]+\b", re.IGNORECASE)

# A level-2 markdown heading sets the current section, used to detect the
# "Alternatives Considered" scope.
SECTION_HEADING_RE = re.compile(r"^##\s+(.*)$")

UNTIL_TAGGED_MESSAGE = (
    "architectural claim must carry a D098 lifecycle tag "
    "([proposed]/[bounded]/[smoke]/[validated]/[deferred])"
)
MISSING_ADR_REF_MESSAGE = (
    "binding architectural claim in a non-ADR claim file must reference an ADR (ADR-NNNN)"
)

DEFAULT_CLAIM_FILES: tuple[str, ...] = (
    "prd/ARCHITECTURE.md",
    "prd/02_architecture.md",
)

# The most recent verification result, for in-process inspection (parity with
# scripts/verify-architecture-graph.py).
LAST_RESULT: list[Finding] | None = None


@dataclass(frozen=True)
class Finding:
    """A single D098/ADR conformance finding about one architectural claim."""

    file: str
    line: int
    kind: str
    snippet: str
    message: str

    def format(self) -> str:
        snippet = self.snippet.strip().replace("\n", " ")
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        return (
            f"{self.file}:{self.line} kind={self.kind} message={self.message} snippet={snippet!r}"
        )


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except (ValueError, OSError):
        return str(path)


def front_matter_close_index(lines: list[str]) -> int | None:
    """Return the 0-based index of the closing ``---`` of leading YAML front matter.

    Returns ``None`` when the file has no well-formed front matter (the first
    non-blank line is not ``---``, or no closing ``---`` exists).
    """
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index
    return None


def own_adr_id(name: str, lines: list[str]) -> str | None:
    """Return ``ADR-NNNN`` if ``name``/``lines`` is an ADR record, else ``None``.

    An ADR file's own id satisfies the ADR-reference requirement for claims that
    live inside it (the ADR documents them). Detected from the YAML front-matter
    ``id:`` field, or from a ``doc/adr/NNNN-*.md`` filename.
    """
    close_index = front_matter_close_index(lines)
    if close_index is not None:
        block = "\n".join(lines[1:close_index])
        match = re.search(r"^id:\s*ADR[-\s]?(\d{4})\s*$", block, re.IGNORECASE | re.MULTILINE)
        if match:
            return f"ADR-{match.group(1)}"

    path = Path(name)
    base = path.name
    parent = str(path.parent).replace("\\", "/").lower()
    filename_match = re.match(r"^(\d{4})-", base)
    if filename_match and ("adr" in parent or parent.endswith("adr")):
        return f"ADR-{filename_match.group(1)}"
    return None


def is_table_separator(stripped: str) -> bool:
    if "|" not in stripped:
        return False
    remainder = stripped.replace("|", "").replace("-", "").replace(":", "").replace(" ", "")
    return remainder == ""


def find_claim_findings(name: str, text: str) -> list[Finding]:
    """Return D098/ADR conformance findings for the architectural claims in ``text``.

    Pure function on ``name``/``text``: reads no files, so tests can pass
    synthetic in-memory content without touching the real claim files.
    """
    lines = text.splitlines()
    close_index = front_matter_close_index(lines)
    file_adr_id = own_adr_id(name, lines)
    findings: list[Finding] = []

    in_fence = False
    in_alternatives = False
    in_decision = False
    for index, raw in enumerate(lines):
        stripped = raw.strip()

        # Skip well-formed YAML front matter entirely (metadata, not prose claims).
        if close_index is not None and index <= close_index:
            continue

        # Track the current level-2 section so claims inside "Alternatives
        # Considered" (rejected options) are not flagged as current architecture,
        # and so imperative Decision-claims inside an ADR's own ## Decision are
        # exempt (the Decision section IS the binding decision; its lifecycle is
        # the ADR Status line + per-claim lifecycle tags in its subsections).
        heading = SECTION_HEADING_RE.match(raw)
        if heading:
            heading_text = heading.group(1).strip().lower()
            in_alternatives = "alternative" in heading_text
            in_decision = heading_text == "decision"
            continue

        # Track fenced code blocks; never treat code as a claim.
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if not stripped:
            continue
        if is_table_separator(stripped):
            continue
        # Questions are not claims.
        if stripped.endswith("?"):
            continue
        # A named-but-rejected alternative header is not a current claim.
        if ALTERNATIVE_HEADER_RE.match(stripped):
            continue

        is_claim = bool(CLAIM_VERB_RE.search(raw))
        # An imperative Decision-claim ("Adopt ...", "Establish ...") inside an
        # ADR file's own ## Decision section is exempt from the untagged-claim
        # check: the Decision section is the binding decision itself, and its
        # lifecycle is carried by the ADR Status line and the per-claim
        # lifecycle tags in the Decision's subsections (the same logic by which
        # ADR-internal claims are already exempt from the missing-adr-ref check).
        # Imperatives elsewhere (Context/Consequences, or any non-ADR file) are
        # still subject to the tag check. CLAIM_VERB prose-adoption claims are
        # never exempt here — only imperative decision-verbs are.
        decision_imperative_exempt = (
            file_adr_id is not None and in_decision and IMPERATIVE_CLAIM_RE.match(raw)
        )
        if not is_claim and not in_alternatives and IMPERATIVE_CLAIM_RE.match(raw):
            if decision_imperative_exempt:
                is_claim = False
            else:
                is_claim = True
        if not is_claim:
            continue

        # The line is an architectural claim candidate.
        if LIFECYCLE_TAG_RE.search(raw) is None:
            findings.append(
                Finding(
                    file=name,
                    line=index + 1,
                    kind="untagged-claim",
                    snippet=raw,
                    message=UNTIL_TAGGED_MESSAGE,
                )
            )

        # Claims inside an ADR file are documented by that ADR; only non-ADR
        # claim files must cite an ADR explicitly.
        if file_adr_id is None and ADR_REF_RE.search(raw) is None:
            findings.append(
                Finding(
                    file=name,
                    line=index + 1,
                    kind="missing-adr-ref",
                    snippet=raw,
                    message=MISSING_ADR_REF_MESSAGE,
                )
            )

    return findings


def verify_adr_conformance(paths: Iterable[str | Path]) -> list[Finding]:
    """Read each claim file and return all conformance findings (sorted)."""
    findings: list[Finding] = []
    for raw_path in paths:
        path = Path(raw_path)
        name = display_path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"{name}:0 kind=read-error message={exc}", file=sys.stderr)
            continue
        findings.extend(find_claim_findings(name, text))
    findings.sort(key=lambda finding: (finding.file, finding.line, finding.kind))
    return findings


def default_claim_paths() -> list[Path]:
    paths = [ROOT / relative for relative in DEFAULT_CLAIM_FILES]
    adr_dir = ROOT / "doc/adr"
    if adr_dir.is_dir():
        paths.extend(sorted(adr_dir.glob("*.md")))
    return paths


def summary(findings: list[Finding], files_scanned: int) -> dict[str, object]:
    untagged = sum(1 for finding in findings if finding.kind == "untagged-claim")
    missing_refs = sum(1 for finding in findings if finding.kind == "missing-adr-ref")
    return {
        "status": "ok" if not findings else "fail",
        "finding_count": len(findings),
        "untagged_claims": untagged,
        "missing_adr_refs": missing_refs,
        "files_scanned": files_scanned,
        "boundary": (
            "Structural compliance gate per ADR-0002 (gate half, not the ACP checkpoint). "
            "D098 targeted claims only."
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify D098 lifecycle-tag and ADR-reference conformance of architectural "
            "claims (compliance gate per ADR-0002)."
        )
    )
    parser.add_argument(
        "files",
        nargs="*",
        help=(
            "Architectural claim files to scan. Defaults to "
            + ", ".join(DEFAULT_CLAIM_FILES)
            + " and doc/adr/*.md."
        ),
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Report findings but always exit 0 (checkpoint / non-blocking use).",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    global LAST_RESULT
    args = parse_args(argv)
    paths = [Path(path) for path in args.files] if args.files else default_claim_paths()

    findings = verify_adr_conformance(paths)
    LAST_RESULT = findings

    for finding in findings:
        print(finding.format(), file=sys.stderr)

    print(json.dumps(summary(findings, len(paths)), sort_keys=True))

    if findings and not args.report_only:
        return 1
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

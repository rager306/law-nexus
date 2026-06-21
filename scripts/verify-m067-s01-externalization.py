#!/usr/bin/env python3
"""M067 S01 externalization verifier (law-nexus-side).

Verifies /root/git-lex-kit-acp/ is a publication-ready standalone reusable core:
- COMPLETENESS: kit content (acp.ttl v0.2.0 + examples + kit.yml + AGENTS.md),
  generic skills (git-lex + acp, ACP bound to git-lex), design docs (6), README.
- NO-LEAK: 0 law-nexus-specific material across the external repo.

This is a law-nexus-side inspection script (runs from law-nexus, inspects the
external repo). It does NOT mutate either repo.

Exclusions from leak scan:
- ``rager306/git-lex-kit-acp`` is the kit's OWN canonical name/identity (the
  published repo), not a law-nexus-specific leak. It is the generic kit identity.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTERNAL = Path("/root/git-lex-kit-acp")

# Required files for completeness.
REQUIRED_KIT_CONTENT = (
    "ontology/acp/acp.ttl",
    "kit.yml",
    "content/AGENTS.md",
    "content/ACP/Decision/example-decision.md",
    "content/ACP/ProofGate/example-proof-gate.md",
    "content/ACP/ProofGate/example-proof-gate-invalid-verdict.md",
    "content/ACP/SourceRecord/example-source-record.md",
    "content/ACP/EvidenceAnchor/example-evidence-anchor.md",
    "content/ACP/EvidenceAnchor/example-evidence-anchor-missing-source-artifact.md",
)
REQUIRED_SKILLS = (
    "skills/git-lex/SKILL.md",
    "skills/git-lex/workflows/inspect-base-kit.md",
    "skills/git-lex/workflows/classify-evidence.md",
    "skills/git-lex/workflows/review-acp-claim.md",
    "skills/git-lex/workflows/plan-adapter-spike.md",
    "skills/git-lex/templates/claim-review.md",
    "skills/git-lex/references/source-inventory.md",
    "skills/git-lex/references/ontology-map.md",
    "skills/git-lex/references/acp-boundaries.md",
    "skills/git-lex/references/claim-language.md",
    "skills/git-lex/references/runtime-adoption-gates.md",
    "skills/acp/SKILL.md",
    "skills/acp/references/acp-kit-roadmap.md",
    "skills/acp/references/source-truth-and-proof-gates.md",
)
REQUIRED_DOCS = (
    "docs/SHAPE-CONTRACT.md",
    "docs/SHAPE-BASELINE.md",
    "docs/ONTOLOGY-DESIGN.md",
    "docs/CAPABILITY-MATRIX.md",
    "docs/APPLYING.md",
    "docs/BOUNDARIES.md",
    "README.md",
)

# law-nexus-specific leak patterns. Affirmative validation-verb adjacency to
# R035/R037/R038 is overclaim; bare R-ID tokens in a generic kit are leaks.
LEAK_PATTERNS: tuple[tuple[str, str], ...] = (
    ("law-nexus token", r"\blaw-nexus\b"),
    ("legalgraph token", r"\blegalgraph\b"),
    ("LegalGraph token", r"\bLegalGraph\b"),
    ("Russian legal", r"Russian legal"),
    ("FalkorDB", r"\bFalkorDB\b"),
    ("Garant", r"\bGarant\b"),
    ("ODT parser", r"ODT parser"),
    ("R035 token", r"\bR035\b"),
    ("R037 token", r"\bR037\b"),
    ("R038 token", r"\bR038\b"),
    ("citation-safe", r"citation-safe"),
    ("generated-cypher", r"generated-cypher"),
    ("/root/law-nexus path", r"/root/law-nexus"),
    ("verify-m0xx script", r"verify-m0[0-9][0-9]"),
    ("prd/architecture/acp/M0 milestone ref", r"prd/architecture/acp/M0"),
    ("gitnexus law-nexus repo", r'repo="law-nexus"'),
)

DIAGNOSTIC_IDS = (
    "missing_file",
    "acp_ttl_wrong_version",
    "acp_not_bound_to_git_lex",
    "leak_detected",
)


@dataclass(frozen=True)
class Diagnostic:
    diagnostic_id: str
    path: str
    line: int
    message: str
    text: str


def _diag(diagnostic_id: str, path: Path | str, line_no: int, message: str, text: str = "") -> Diagnostic:
    try:
        rel = str(Path(path).relative_to(DEFAULT_EXTERNAL))
    except (ValueError, TypeError):
        rel = str(path)
    return Diagnostic(diagnostic_id=diagnostic_id, path=rel, line=line_no, message=message, text=text.strip())


def check_completeness(ext: Path) -> tuple[dict[str, bool], list[Diagnostic]]:
    required = {*REQUIRED_KIT_CONTENT, *REQUIRED_SKILLS, *REQUIRED_DOCS}
    present = {}
    diags: list[Diagnostic] = []
    for rel in sorted(required):
        p = ext / rel
        ok = p.exists()
        present[rel] = ok
        if not ok:
            diags.append(_diag("missing_file", p, 0, f"required file missing: {rel}"))
    # acp.ttl version
    acp = ext / "ontology/acp/acp/acp.ttl" if (ext / "ontology/acp/acp.ttl").exists() is False else (ext / "ontology/acp/acp.ttl")
    acp = ext / "ontology/acp/acp.ttl"
    if acp.exists():
        ver = re.search(r'versionInfo\s+"([^"]+)"', acp.read_text())
        if not ver or ver.group(1) != "0.2.0":
            diags.append(_diag("acp_ttl_wrong_version", acp, 0, f"acp.ttl version is {ver.group(1) if ver else 'missing'}, expected 0.2.0"))
    # ACP→git-lex binding
    acp_skill = ext / "skills/acp/SKILL.md"
    if acp_skill.exists():
        t = acp_skill.read_text()
        if "git-lex" not in t.lower():
            diags.append(_diag("acp_not_bound_to_git_lex", acp_skill, 0, "acp SKILL.md does not reference git-lex skill (binding lost)"))
    return present, diags


def scan_leaks(ext: Path) -> tuple[dict[str, int], list[Diagnostic]]:
    summary: dict[str, int] = {name: 0 for name, _ in LEAK_PATTERNS}
    diags: list[Diagnostic] = []
    for md in sorted(ext.rglob("*.md")):
        # skip .git
        if ".git" in md.parts:
            continue
        text = md.read_text()
        for name, pat in LEAK_PATTERNS:
            for m in re.finditer(pat, text):
                summary[name] += 1
                line_no = text.count("\n", 0, m.start()) + 1
                diags.append(_diag("leak_detected", md, line_no, f"{name}: {m.group(0)!r}", m.group(0)))
    # also scan acp.ttl (non-md) for leaks
    acp = ext / "ontology/acp/acp.ttl"
    if acp.exists():
        text = acp.read_text()
        for name, pat in LEAK_PATTERNS:
            for m in re.finditer(pat, text):
                summary[name] += 1
                line_no = text.count("\n", 0, m.start()) + 1
                diags.append(_diag("leak_detected", acp, line_no, f"{name}: {m.group(0)!r}", m.group(0)))
    return summary, diags


def verify(ext: Path = DEFAULT_EXTERNAL) -> tuple[bool, list[Diagnostic], dict]:
    diags: list[Diagnostic] = []
    if not ext.exists():
        return False, [_diag("missing_file", ext, 0, f"external repo missing: {ext}")], {}
    present, comp_diags = check_completeness(ext)
    diags.extend(comp_diags)
    leak_summary, leak_diags = scan_leaks(ext)
    diags.extend(leak_diags)
    ok = not diags
    summary = {
        "completeness_present": sum(1 for v in present.values() if v),
        "completeness_total": len(present),
        "leak_summary": leak_summary,
        "total_leaks": sum(leak_summary.values()),
        "verdict": "publication_ready" if ok else "not_ready",
    }
    return ok, diags, summary


def _fmt(d: Diagnostic) -> str:
    loc = d.path
    if d.line:
        loc = f"{loc}:{d.line}"
    suffix = f"\n  {d.text}" if d.text else ""
    return f"{d.diagnostic_id}: {loc}: {d.message}{suffix}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify /root/git-lex-kit-acp/ externalization completeness + no-leak.")
    ap.add_argument("--external", type=Path, default=DEFAULT_EXTERNAL)
    args = ap.parse_args(argv)
    ok, diags, _ = verify(args.external)
    if diags:
        for d in diags:
            print(_fmt(d))
        return 1
    print(f"M067 S01 externalization verification passed: diagnostics=0 (publication-ready, 0 leaks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

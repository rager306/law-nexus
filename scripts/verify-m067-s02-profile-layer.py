#!/usr/bin/env python3
"""M067 S02 profile-layer integrity verifier (law-nexus-side).

Verifies law-nexus is restructured as a full profile layer consuming the
external /root/git-lex-kit-acp/ reusable core:
- law-nexus skills (git-lex, acp) reference the external generic skills;
- law-nexus skills carry law-nexus-specific override markers;
- no orphaned generic-only duplicates that would drift from external
  (claim-language, claim-review template, generic workflows removed);
- profile adapter artifact present;
- AGENTS.md reflects profile architecture;
- ACP→git-lex binding preserved in the override context;
- external repo still publication-ready (no regression from S01).

Inspection only. Runs from law-nexus.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = Path("/root/git-lex-kit-acp")

DIAGNOSTIC_IDS = (
    "skill_missing",
    "no_external_reference",
    "no_override_markers",
    "orphaned_generic_duplicate",
    "adapter_missing",
    "agents_md_no_profile",
    "acp_binding_lost",
    "external_regression",
)

# law-nexus-specific override markers that MUST appear in law-nexus skills.
LAW_NEXUS_MARKERS = ("R035", "R037", "R038", "law-nexus")

# Generic-only files that should be REMOVED from law-nexus (referenced external).
ORPHANED_GENERIC = (
    ".agents/skills/git-lex/references/claim-language.md",
    ".agents/skills/git-lex/templates/claim-review.md",
    ".agents/skills/git-lex/workflows/inspect-base-kit.md",
    ".agents/skills/git-lex/workflows/classify-evidence.md",
    ".agents/skills/git-lex/workflows/review-acp-claim.md",
    ".agents/skills/git-lex/workflows/plan-adapter-spike.md",
)


@dataclass(frozen=True)
class Diagnostic:
    diagnostic_id: str
    path: str
    line: int
    message: str


def _d(i: str, p: str | Path, m: str, line: int = 0) -> Diagnostic:
    try:
        rel = str(Path(p).relative_to(ROOT))
    except (ValueError, TypeError):
        rel = str(p)
    return Diagnostic(i, rel, line, m)


def check_skills() -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    for rel in (".agents/skills/git-lex/SKILL.md", ".agents/skills/acp/SKILL.md"):
        p = ROOT / rel
        if not p.exists():
            diags.append(_d("skill_missing", p, f"law-nexus skill missing: {rel}"))
            continue
        text = p.read_text()
        if "/root/git-lex-kit-acp/skills" not in text:
            diags.append(_d("no_external_reference", p, f"{rel} does not reference external generic skill"))
        if not any(m in text for m in LAW_NEXUS_MARKERS):
            diags.append(_d("no_override_markers", p, f"{rel} has no law-nexus-specific override markers"))
    return diags


def check_orphans() -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    for rel in ORPHANED_GENERIC:
        if (ROOT / rel).exists():
            diags.append(_d("orphaned_generic_duplicate", rel, f"generic-only file still present (should reference external): {rel}"))
    return diags


def check_adapter() -> list[Diagnostic]:
    p = ROOT / "prd/architecture/PROFILE-ADAPTER.md"
    if not p.exists():
        return [_d("adapter_missing", p, "profile adapter artifact missing")]
    return []


def check_agents_md() -> list[Diagnostic]:
    p = ROOT / "AGENTS.md"
    if not p.exists():
        return [_d("agents_md_no_profile", p, "AGENTS.md missing")]
    text = p.read_text()
    if "profile" not in text.lower() or "/root/git-lex-kit-acp" not in text:
        return [_d("agents_md_no_profile", p, "AGENTS.md does not reflect profile-layer architecture (external kit + profile)")]
    return []


def check_acp_binding() -> list[Diagnostic]:
    p = ROOT / ".agents/skills/acp/SKILL.md"
    if not p.exists():
        return []
    text = p.read_text().lower()
    # ACP should still route git-lex runtime to git-lex skill
    if "git-lex" not in text:
        return [_d("acp_binding_lost", p, "acp SKILL.md no longer references git-lex (binding lost)")]
    return []


def check_external_no_regression() -> list[Diagnostic]:
    """Re-run the S01 externalization verifier to ensure external repo still passes."""
    verifier = ROOT / "scripts/verify-m067-s01-externalization.py"
    if not verifier.exists():
        return [_d("external_regression", verifier, "S01 externalization verifier missing")]
    try:
        r = subprocess.run(["uv", "run", "python", str(verifier)], cwd=str(ROOT), capture_output=True, text=True, timeout=60)
    except Exception as exc:
        return [_d("external_regression", verifier, f"could not re-run S01 verifier: {exc}")]
    if r.returncode != 0:
        return [_d("external_regression", EXT, f"S01 externalization verifier regressed (rc={r.returncode})")]
    return []


def verify() -> tuple[bool, list[Diagnostic], dict]:
    diags: list[Diagnostic] = []
    diags.extend(check_skills())
    diags.extend(check_orphans())
    diags.extend(check_adapter())
    diags.extend(check_agents_md())
    diags.extend(check_acp_binding())
    diags.extend(check_external_no_regression())
    ok = not diags
    return ok, diags, {"verdict": "profile_layer_healthy" if ok else "not_healthy", "diagnostics": len(diags)}


def _fmt(d: Diagnostic) -> str:
    loc = d.path
    if d.line:
        loc = f"{loc}:{d.line}"
    return f"{d.diagnostic_id}: {loc}: {d.message}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify law-nexus profile-layer integrity (S02).")
    ap.parse_args(argv)
    ok, diags, _ = verify()
    if diags:
        for d in diags:
            print(_fmt(d))
        return 1
    print("M067 S02 profile-layer verification passed: diagnostics=0 (profile layer healthy)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

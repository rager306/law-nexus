#!/usr/bin/env python3
"""M067 S03 externalization integrity verifier (end-to-end, law-nexus-side).

Final end-to-end check that the M067 restructuring programme is complete:
- external repo publication-ready (re-runs S01 verifier);
- law-nexus profile layer healthy (re-runs S02 verifier);
- PROJECT.md reflects post-externalization state;
- PROFILE-ADAPTER.md present.

Single command для cold-start agent confirm M067 restructuring complete.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DIAGNOSTIC_IDS = (
    "subprocess_verifier_failed",
    "project_md_not_revised",
    "adapter_missing",
)


@dataclass(frozen=True)
class Diagnostic:
    diagnostic_id: str
    path: str
    message: str


def _d(i: str, p: str | Path, m: str) -> Diagnostic:
    try:
        rel = str(Path(p).relative_to(ROOT))
    except (ValueError, TypeError):
        rel = str(p)
    return Diagnostic(i, rel, m)


def _run(name: str, script: Path) -> list[Diagnostic]:
    if not script.exists():
        return [_d("subprocess_verifier_failed", script, f"{name} verifier missing: {script}")]
    try:
        r = subprocess.run(["uv", "run", "python", str(script)], cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    except Exception as exc:
        return [_d("subprocess_verifier_failed", script, f"{name} verifier could not run: {exc}")]
    if r.returncode != 0:
        tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        return [_d("subprocess_verifier_failed", script, f"{name} verifier exited {r.returncode}: {' | '.join(tail)}")]
    return []


def check_project_md() -> list[Diagnostic]:
    p = ROOT / ".gsd/PROJECT.md"
    if not p.exists():
        return [_d("project_md_not_revised", p, "PROJECT.md missing")]
    text = p.read_text()
    required = ("D097", "/root/git-lex-kit-acp", "profile", "ACP externalization", "product")
    missing = [m for m in required if m.lower() not in text.lower()]
    if missing:
        return [_d("project_md_not_revised", p, f"PROJECT.md missing post-externalization markers: {missing}")]
    return []


def check_adapter() -> list[Diagnostic]:
    p = ROOT / "prd/architecture/PROFILE-ADAPTER.md"
    if not p.exists():
        return [_d("adapter_missing", p, "PROFILE-ADAPTER.md missing")]
    return []


def verify() -> tuple[bool, list[Diagnostic], dict]:
    diags: list[Diagnostic] = []
    diags.extend(_run("S01-externalization", ROOT / "scripts/verify-m067-s01-externalization.py"))
    diags.extend(_run("S02-profile-layer", ROOT / "scripts/verify-m067-s02-profile-layer.py"))
    diags.extend(check_project_md())
    diags.extend(check_adapter())
    ok = not diags
    return ok, diags, {"verdict": "m067_restructuring_complete" if ok else "incomplete", "diagnostics": len(diags)}


def _fmt(d: Diagnostic) -> str:
    return f"{d.diagnostic_id}: {d.path}: {d.message}"


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Verify M067 externalization integrity end-to-end.").parse_args(argv)
    ok, diags, _ = verify()
    if diags:
        for d in diags:
            print(_fmt(d))
        return 1
    print("M067 S03 externalization-integrity verification passed: diagnostics=0 (restructuring complete)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Local ACP CI contract for M050.

This wrapper runs existing ACP boundary verifiers and a narrow M058 wording
check. It is local-only: it does not create external CI configuration, does not
run git-lex, and does not initialize or mutate main checkout .lex state.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M058_SYNTHESIS = ROOT / "prd/architecture/acp/M058-S03-CORRECTED-VALIDATION-SYNTHESIS.md"
MAIN_STATE_RESIDUE = (".lex", "Squad", "Raw", ".artifacts")

REQUIRED_M058_TERMS = (
    "validate/query representation mismatch",
    "current generated ACP shapes are too underconstrained",
    "Do not use `git-lex validate` as a hard ACP proof gate yet",
    "does not validate R035, R037, or R038",
    "ontology domains/restrictions or generator changes",
)

FORBIDDEN_M058_CLAIMS = (
    "git-lex validate is broken",
    "ACP-kit validation enforcement is proven",
    "ACP-kit is the ACP source truth",
    "ACP-kit approves production adoption",
    "R035 is validated by ACP-kit",
    "R037 is validated by ACP-kit",
    "R038 is validated by ACP-kit",
)

NEGATIVE_CONTEXT_MARKERS = (
    "avoid this wording",
    "do not ",
    "does not ",
    "not ",
    "blocked",
    "forbidden",
    "incorrectly",
    "overclaim",
)


@dataclass(frozen=True)
class Diagnostic:
    diagnostic_id: str
    path: Path
    line: int
    message: str
    text: str = ""


def _has_negative_context(lines: list[str], index: int) -> bool:
    current_line = lines[index].lower()
    if any(marker in current_line for marker in NEGATIVE_CONTEXT_MARKERS if marker != "avoid this wording"):
        return True
    previous_lines = "\n".join(lines[max(0, index - 4) : index]).lower()
    return "avoid this wording" in previous_lines


def check_m058_synthesis(path: Path = M058_SYNTHESIS) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not path.exists():
        return [Diagnostic("missing_m058_synthesis", path, 0, "M058 corrected synthesis is missing")]

    text = path.read_text(encoding="utf-8")
    for term in REQUIRED_M058_TERMS:
        if term not in text:
            diagnostics.append(
                Diagnostic("missing_m058_guard_term", path, 0, f"required M058 guard term missing: {term}")
            )

    lines = text.splitlines()
    for line_no, line in enumerate(lines, start=1):
        normalized = line.replace("`", "")
        for claim in FORBIDDEN_M058_CLAIMS:
            if claim.lower() in normalized.lower() and not _has_negative_context(lines, line_no - 1):
                diagnostics.append(
                    Diagnostic(
                        "forbidden_m058_overclaim",
                        path,
                        line_no,
                        f"forbidden M058 validation/adoption overclaim: {claim}",
                        line.strip(),
                    )
                )
    return diagnostics


def check_main_state_residue(root: Path = ROOT) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for name in MAIN_STATE_RESIDUE:
        path = root / name
        if path.exists():
            diagnostics.append(Diagnostic("main_state_residue", path, 0, "main checkout state residue exists"))
    return diagnostics


def _run(command: list[str], *, cwd: Path = ROOT) -> Diagnostic | None:
    completed = subprocess.run(command, cwd=cwd, text=True)
    if completed.returncode != 0:
        return Diagnostic("command_failed", cwd, 0, f"command failed with exit {completed.returncode}: {' '.join(command)}")
    return None


def run_contract(*, run_tests: bool, run_diff_check: bool, check_residue: bool) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    for command in (
        ["uv", "run", "python", "scripts/verify-m049-binding.py"],
        ["uv", "run", "python", "scripts/verify-m056-acp-kit.py"],
    ):
        diagnostic = _run(command)
        if diagnostic is not None:
            diagnostics.append(diagnostic)

    if run_tests:
        diagnostic = _run(
            [
                "uv",
                "run",
                "pytest",
                "tests/test_verify_m049_binding.py",
                "tests/test_verify_m056_acp_kit.py",
                "tests/test_verify_acp_ci_contract.py",
            ]
        )
        if diagnostic is not None:
            diagnostics.append(diagnostic)

    diagnostics.extend(check_m058_synthesis())

    if run_diff_check:
        diagnostic = _run(["git", "diff", "--check"])
        if diagnostic is not None:
            diagnostics.append(diagnostic)

    if check_residue:
        diagnostics.extend(check_main_state_residue())

    return diagnostics


def _format_diagnostic(diagnostic: Diagnostic) -> str:
    location = diagnostic.path
    if diagnostic.line:
        location = Path(f"{location}:{diagnostic.line}")
    suffix = f"\n  {diagnostic.text}" if diagnostic.text else ""
    return f"{diagnostic.diagnostic_id}: {location}: {diagnostic.message}{suffix}"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local ACP CI contract.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip targeted pytest suites.")
    parser.add_argument("--skip-diff-check", action="store_true", help="Skip git diff --check.")
    parser.add_argument("--skip-residue", action="store_true", help="Skip main-state residue check.")
    parser.add_argument("--m058-only", action="store_true", help="Run only the M058 wording guard.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.m058_only:
        diagnostics = check_m058_synthesis()
    else:
        diagnostics = run_contract(
            run_tests=not args.skip_tests,
            run_diff_check=not args.skip_diff_check,
            check_residue=not args.skip_residue,
        )

    if diagnostics:
        for diagnostic in diagnostics:
            print(_format_diagnostic(diagnostic))
        return 1

    print("ACP CI contract verification passed: diagnostics=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

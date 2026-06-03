#!/usr/bin/env python3
"""Focused M049 binding boundary verifier.

This script checks the M049 binding artifacts only. It does not regenerate or
claim freshness for the generated architecture registry JSONL/report views.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACTS = (
    ROOT / "prd/architecture/acp/M049-S01-BINDING-INPUT-AUDIT.md",
    ROOT / "prd/architecture/acp/M049-S02-PROFILE-ADAPTER-BOUNDARY.md",
    ROOT / "prd/architecture/acp/M049-S03-REGISTRY-SOURCE-MAPPING.md",
)
MAIN_STATE_RESIDUE = (".lex", "Squad", "Raw", ".artifacts")
DIAGNOSTIC_IDS = (
    "authority_inversion",
    "unsafe_anchor",
    "missing_profile_proof_gate",
    "missing_requirement_proof_gate",
    "profile_core_drift",
    "forbidden_git_lex_promotion",
    "forbidden_profile_validation",
    "main_state_residue",
    "registry_currency_overclaim",
    "proof_gate_placeholder_used_as_proof",
)
NEGATIVE_CONTEXT_MARKERS = (
    "Do not ",
    "do not ",
    "Must not ",
    "must not ",
    "does not ",
    "cannot ",
    "Forbidden",
    "forbidden",
    "Rejected",
    "rejected",
    "Accepting `",
    "Treating ",
    "Creating ",
    "Making ",
    "Overriding ",
    "Proving ",
    "without turning",
    "without source evidence",
    "without future proof",
    "without independent profile proof",
    "without running canonical",
    "unless the canonical architecture verifier",
    "unsafe pattern",
    "Example unsafe pattern",
    "Expected diagnostic",
    "diagnostic",
    "blocked promotions",
    "must not claim",
    "not claim generated registry",
    "not claim generated architecture",
    "non-authoritative unless",
    "Production adoption, main",
)
REQUIRED_TERMS = (
    "ACP source truth remains ACP-native",
    "Reusable ACP core defines record",
    "## ACP core source-record mapping",
    "## law-nexus profile claim gate mapping",
    "## S04 verifier input matrix",
)


@dataclass(frozen=True)
class Diagnostic:
    diagnostic_id: str
    path: str
    line: int
    message: str
    text: str


def _repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _is_negative_context(line: str) -> bool:
    return any(marker in line for marker in NEGATIVE_CONTEXT_MARKERS)


def _diagnostic(diagnostic_id: str, path: Path, line_no: int, message: str, line: str) -> Diagnostic:
    return Diagnostic(
        diagnostic_id=diagnostic_id,
        path=_repo_relative(path),
        line=line_no,
        message=message,
        text=line.strip(),
    )


def check_required_terms(paths: tuple[Path, ...]) -> list[Diagnostic]:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths if path.exists())
    diagnostics: list[Diagnostic] = []
    for term in REQUIRED_TERMS:
        if term not in combined:
            diagnostics.append(
                Diagnostic(
                    diagnostic_id="missing_requirement_proof_gate",
                    path="<combined>",
                    line=0,
                    message=f"required M049 binding term is missing: {term}",
                    text="",
                )
            )
    return diagnostics


def check_unsafe_anchor(path: Path, line_no: int, line: str) -> Diagnostic | None:
    unsafe_patterns = (
        r"/root/",
        r"\.gsd/exec",
        r"\.artifacts/browser/[0-9]",
        r"raw provider payloads? (?:as|is|are)",
        r"raw vectors? (?:as|is|are)",
        r"session logs? (?:as|is|are)",
    )
    if not any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in unsafe_patterns):
        return None
    if _is_negative_context(line):
        return None
    return _diagnostic("unsafe_anchor", path, line_no, "unsafe durable anchor used outside a rejected/negative context", line)


def check_authority_inversion(path: Path, line_no: int, line: str) -> Diagnostic | None:
    authority_subject = r"(JSONL|RDF|SHACL|SPARQL|JSON-LD|graph report|generated projection|browser summary|git-lex diagnostic|LLM summary|polished prose)"
    authority_claim = r"(source truth|authoritative|validation proof|requirement-validation proof|proves? product|proves? runtime|proves? legal)"
    if re.search(authority_subject, line, flags=re.IGNORECASE) and re.search(authority_claim, line, flags=re.IGNORECASE):
        if _is_negative_context(line):
            return None
        return _diagnostic("authority_inversion", path, line_no, "derived or diagnostic surface is promoted to authority", line)
    return None


def check_missing_proof_gate(path: Path, line_no: int, line: str) -> Diagnostic | None:
    if re.search(r"\b(validated|production-ready|production readiness)\b", line, flags=re.IGNORECASE) and re.search(
        r"without (?:a |an )?(proof gate|accepted evidence anchor|matching proof)", line, flags=re.IGNORECASE
    ):
        if _is_negative_context(line):
            return None
        return _diagnostic("missing_profile_proof_gate", path, line_no, "validated/production-ready claim lacks proof gate", line)
    return None


def check_profile_core_drift(path: Path, line_no: int, line: str) -> Diagnostic | None:
    profile_terms = r"(Russian legal correctness|parser completeness|FalkorDB runtime|retrieval quality|citation safety|generated-Cypher safety|R035|R037|R038)"
    core_terms = r"(generic ACP core|ACP-core authority|reusable ACP core owns|ACP core owns)"
    if re.search(profile_terms, line, flags=re.IGNORECASE) and re.search(core_terms, line, flags=re.IGNORECASE):
        if _is_negative_context(line):
            return None
        return _diagnostic("profile_core_drift", path, line_no, "profile-owned claim is promoted into ACP core", line)
    return None


def check_forbidden_git_lex_promotion(path: Path, line_no: int, line: str) -> Diagnostic | None:
    if re.search(r"git-lex", line, flags=re.IGNORECASE) and re.search(
        r"(source truth|L2 operational backend|main `?\.lex`?|production backend|profile validator|ACP authority|migrates? source truth)",
        line,
        flags=re.IGNORECASE,
    ):
        if _is_negative_context(line):
            return None
        return _diagnostic("forbidden_git_lex_promotion", path, line_no, "git-lex promoted beyond M055 L1 diagnostics", line)
    return None


def check_forbidden_profile_validation(path: Path, line_no: int, line: str) -> Diagnostic | None:
    if re.search(r"R0?(35|37|38)", line) and re.search(
        r"(validated|validates|closed|closes|retired|retires|satisfied|complete)", line, flags=re.IGNORECASE
    ):
        if _is_negative_context(line):
            return None
        return _diagnostic("forbidden_profile_validation", path, line_no, "R035/R037/R038 promoted without independent profile proof", line)
    return None


def check_registry_currency_overclaim(path: Path, line_no: int, line: str) -> Diagnostic | None:
    if re.search(r"(architecture_items\.jsonl|architecture_edges\.jsonl|architecture_graph_report\.json|generated registry)", line) and re.search(
        r"(current|fresh|verified|valid)", line, flags=re.IGNORECASE
    ):
        if _is_negative_context(line):
            return None
        return _diagnostic("registry_currency_overclaim", path, line_no, "generated registry currency claimed without canonical verifier evidence", line)
    return None


def check_placeholder_proof_misuse(path: Path, line_no: int, line: str) -> Diagnostic | None:
    if re.search(r"(placeholder proof gate|proof-gate placeholder|proof_level=none)", line, flags=re.IGNORECASE) and re.search(
        r"(proof|proves|validated|evidence)", line, flags=re.IGNORECASE
    ):
        if _is_negative_context(line):
            return None
        return _diagnostic("proof_gate_placeholder_used_as_proof", path, line_no, "placeholder proof gate is used as proof", line)
    return None


def _is_structural_negative_section(section: str) -> bool:
    negative_section_markers = (
        "Evidence boundary table",
        "Blocked promotions",
        "Forbidden promotions",
        "Rejected anchors",
        "Rejected durable anchors",
        "Derived-view boundary",
        "S04 verifier input matrix",
        "S04 verifier handoff",
        "S05 synthesis handoff",
        "Verification commands",
    )
    return any(marker in section for marker in negative_section_markers)


def check_artifact(path: Path) -> list[Diagnostic]:
    checks = (
        check_unsafe_anchor,
        check_authority_inversion,
        check_missing_proof_gate,
        check_profile_core_drift,
        check_forbidden_git_lex_promotion,
        check_forbidden_profile_validation,
        check_registry_currency_overclaim,
        check_placeholder_proof_misuse,
    )
    diagnostics: list[Diagnostic] = []
    if not path.exists():
        return [
            Diagnostic(
                diagnostic_id="missing_requirement_proof_gate",
                path=_repo_relative(path),
                line=0,
                message="required M049 binding artifact is missing",
                text="",
            )
        ]
    current_section = ""
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("## ") or line in {"Rejected anchors:", "Rejected durable anchors:"}:
            current_section = line
        for check in checks:
            diagnostic = check(path, line_no, line)
            if diagnostic is not None:
                if _is_structural_negative_section(current_section):
                    continue
                diagnostics.append(diagnostic)
    return diagnostics


def check_main_state_residue(root: Path = ROOT) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for name in MAIN_STATE_RESIDUE:
        if (root / name).exists():
            diagnostics.append(
                Diagnostic(
                    diagnostic_id="main_state_residue",
                    path=name,
                    line=0,
                    message=f"main checkout residue exists: {name}",
                    text=name,
                )
            )
    return diagnostics


def verify(paths: tuple[Path, ...] = DEFAULT_ARTIFACTS, *, check_residue: bool = True) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(check_required_terms(paths))
    for path in paths:
        diagnostics.extend(check_artifact(path))
    if check_residue:
        diagnostics.extend(check_main_state_residue())
    return diagnostics


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify M049 binding artifact safety boundaries.")
    parser.add_argument(
        "artifacts",
        nargs="*",
        type=Path,
        default=list(DEFAULT_ARTIFACTS),
        help="Markdown artifacts to verify; defaults to M049 S01/S02/S03 artifacts.",
    )
    parser.add_argument(
        "--skip-main-state-residue",
        action="store_true",
        help="Skip .lex/Squad/Raw/.artifacts main checkout residue checks.",
    )
    parser.add_argument("--list-diagnostics", action="store_true", help="Print diagnostic IDs and exit.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.list_diagnostics:
        for diagnostic_id in DIAGNOSTIC_IDS:
            print(diagnostic_id)
        return 0
    paths = tuple(path if path.is_absolute() else ROOT / path for path in args.artifacts)
    diagnostics = verify(paths, check_residue=not args.skip_main_state_residue)
    if diagnostics:
        for diagnostic in diagnostics:
            location = f"{diagnostic.path}:{diagnostic.line}" if diagnostic.line else diagnostic.path
            print(f"{diagnostic.diagnostic_id}: {location}: {diagnostic.message}")
            if diagnostic.text:
                print(f"  {diagnostic.text}")
        return 1
    print(f"M049 binding verification passed: artifacts={len(paths)} diagnostics=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

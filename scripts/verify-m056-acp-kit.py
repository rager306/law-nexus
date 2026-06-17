#!/usr/bin/env python3
"""Focused M056 ACP-kit scaffold verifier.

This script checks the tracked ACP-kit v0 scaffold only. It does not run
`git lex`, does not initialize `.lex`, and does not claim runtime compatibility
or ACP source-truth migration.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KIT_ROOT = ROOT / "git-lex-kit-acp"
MAIN_STATE_RESIDUE = (".lex", "Squad", "Raw", ".artifacts")
FORBIDDEN_KIT_PATHS = (
    "content/Raw",
    "content/Squad",
    "content/Soul",
    "content/AutoKnow",
    "content/_autoknow",
    "harness/.claude/hooks",
)
DIAGNOSTIC_IDS = (
    "missing_scaffold_file",
    "invalid_kit_config",
    "forbidden_kit_config",
    "missing_ontology_term",
    "missing_guidance_term",
    "missing_example_guardrail",
    "forbidden_kit_path",
    "unsafe_anchor",
    "source_truth_overclaim",
    "runtime_adoption_overclaim",
    "forbidden_profile_validation",
    "main_state_residue",
)

EXPECTED_FILES = (
    "kit.yml",
    "ontology/acp/acp.ttl",
    "content/AGENTS.md",
    "content/ACP/.gitkeep",
    "www/.gitkeep",
    "content/ACP/SourceRecord/example-source-record.md",
    "content/ACP/Decision/example-decision.md",
    "content/ACP/ProofGate/example-proof-gate.md",
)
REQUIRED_KIT_FIELDS = (
    "name: acp",
    "install folders: true",
    "folder base: ACP",
    "folder ontology: acp.ttl",
)
FORBIDDEN_KIT_CONFIG_TERMS = (
    "adaptive: true",
    "init_prompts",
)
REQUIRED_ONTOLOGY_TERMS = (
    "acp:SourceRecord",
    "acp:Requirement",
    "acp:Decision",
    "acp:EvidenceAnchor",
    "acp:ProofGate",
    "acp:HealthFinding",
    "acp:Projection",
    "acp:LifecycleState",
    "acp:AuthorityClass",
    "acp:ValidationClaim",
    "acp:ProfileConstraint",
    "acp:RuntimeAdapter",
    "acp:hasEvidenceAnchor",
    "acp:requiresProofGate",
    "acp:satisfiesProofGate",
    "acp:blocksClaim",
    "acp:validatesRequirement",
    "acp:doesNotValidateRequirement",
    "acp:derivedFrom",
    "acp:hasLifecycleState",
    "acp:hasAuthorityClass",
    "acp:constrainedByProfile",
    "acp:implementedByAdapter",
    "acp:identifier",
    "acp:sourcePath",
    "acp:selector",
    "acp:nonAuthoritative",
    "acp:blockedRequirementValidation",
    "acp:proofLevel",
    "acp:verdict",
    "acp:sourceArtifact",
    "acp:allowedNextAction",
    "acp:blockedAction",
)
REQUIRED_GUIDANCE_TERMS = (
    "ACP-kit v0 is derived semantic packaging only",
    "Do not validate R035, R037, or R038",
    "tracked repository-relative paths only",
    "source category + lifecycle state + tracked evidence anchor + proof gate or accepted decision",
)
REQUIRED_EXAMPLE_TERMS = (
    "This example is synthetic ACP-kit shape evidence only",
    "not validation evidence",
    "not proof for R035/R037/R038",
)
NEGATIVE_CONTEXT_MARKERS = (
    "not ",
    "do not ",
    "does not ",
    "cannot ",
    "blocked",
    "rejected",
    "invalid",
    "unsafe",
    "forbidden",
    "non-authoritative",
    "derived semantic packaging only",
    "listed only as blocked actions",
    "without requiring",
    "without approving",
)


@dataclass(frozen=True)
class Diagnostic:
    diagnostic_id: str
    path: str
    line: int
    message: str
    text: str


def _repo_relative(path: Path, root: Path = ROOT) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _diagnostic(diagnostic_id: str, path: Path, line_no: int, message: str, text: str = "") -> Diagnostic:
    return Diagnostic(
        diagnostic_id=diagnostic_id,
        path=_repo_relative(path),
        line=line_no,
        message=message,
        text=text.strip(),
    )


def _is_negative_context(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in NEGATIVE_CONTEXT_MARKERS)


def _iter_text_files(kit_root: Path):
    for path in sorted(kit_root.rglob("*")):
        if path.is_file():
            yield path


def check_expected_files(kit_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for relative in EXPECTED_FILES:
        path = kit_root / relative
        if not path.exists():
            diagnostics.append(_diagnostic("missing_scaffold_file", path, 0, f"expected scaffold file is missing: {relative}"))
    return diagnostics


def check_kit_config(kit_root: Path) -> list[Diagnostic]:
    path = kit_root / "kit.yml"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    diagnostics: list[Diagnostic] = []
    for term in REQUIRED_KIT_FIELDS:
        if term not in text:
            diagnostics.append(_diagnostic("invalid_kit_config", path, 0, f"required kit.yml field missing: {term}"))
    for term in FORBIDDEN_KIT_CONFIG_TERMS:
        if term in text:
            diagnostics.append(_diagnostic("forbidden_kit_config", path, 0, f"forbidden kit.yml config present: {term}"))
    return diagnostics


def check_ontology_terms(kit_root: Path) -> list[Diagnostic]:
    path = kit_root / "ontology/acp/acp.ttl"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    diagnostics: list[Diagnostic] = []
    for term in REQUIRED_ONTOLOGY_TERMS:
        if term not in text:
            diagnostics.append(_diagnostic("missing_ontology_term", path, 0, f"required ontology term missing: {term}"))
    return diagnostics


def check_guidance(kit_root: Path) -> list[Diagnostic]:
    path = kit_root / "content/AGENTS.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    diagnostics: list[Diagnostic] = []
    for term in REQUIRED_GUIDANCE_TERMS:
        if term not in text:
            diagnostics.append(_diagnostic("missing_guidance_term", path, 0, f"required guidance term missing: {term}"))
    return diagnostics


def check_examples(kit_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for relative in (
        "content/ACP/SourceRecord/example-source-record.md",
        "content/ACP/Decision/example-decision.md",
        "content/ACP/ProofGate/example-proof-gate.md",
    ):
        path = kit_root / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for term in REQUIRED_EXAMPLE_TERMS:
            if term not in text:
                diagnostics.append(_diagnostic("missing_example_guardrail", path, 0, f"required example guardrail missing: {term}"))
        if "acp." not in text:
            diagnostics.append(_diagnostic("missing_example_guardrail", path, 0, "example lacks ACP typed frontmatter"))
    return diagnostics


def check_forbidden_paths(kit_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for relative in FORBIDDEN_KIT_PATHS:
        path = kit_root / relative
        if path.exists():
            diagnostics.append(_diagnostic("forbidden_kit_path", path, 0, f"forbidden ACP-kit scaffold path exists: {relative}"))
    return diagnostics


def check_line_policy(path: Path, line_no: int, line: str) -> Diagnostic | None:
    if re.search(r"/root/|\.gsd/exec|\.artifacts/", line, flags=re.IGNORECASE):
        return _diagnostic("unsafe_anchor", path, line_no, "forbidden durable anchor literal appears in scaffold", line)

    lowered = line.lower()
    if "source truth" in lowered and not _is_negative_context(line):
        return _diagnostic("source_truth_overclaim", path, line_no, "source-truth claim appears outside a negative/boundary context", line)

    if re.search(r"runtime adoption|production evidence|production use", line, flags=re.IGNORECASE) and not _is_negative_context(line):
        return _diagnostic("runtime_adoption_overclaim", path, line_no, "runtime or production adoption claim appears outside a blocked/boundary context", line)

    if re.search(r"R0?(35|37|38)", line) and re.search(
        r"validated|validates|validation evidence|proof for", line, flags=re.IGNORECASE
    ):
        if _is_negative_context(line):
            return None
        return _diagnostic("forbidden_profile_validation", path, line_no, "R035/R037/R038 validation claim appears without profile proof", line)

    return None


def check_text_policies(kit_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for path in _iter_text_files(kit_root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(lines, start=1):
            diagnostic = check_line_policy(path, line_no, line)
            if diagnostic is not None:
                diagnostics.append(diagnostic)
    return diagnostics


def check_main_state_residue(root: Path = ROOT) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for relative in MAIN_STATE_RESIDUE:
        path = root / relative
        if path.exists():
            diagnostics.append(_diagnostic("main_state_residue", path, 0, f"main checkout residue exists: {relative}"))
    return diagnostics


def verify(kit_root: Path = DEFAULT_KIT_ROOT, *, check_residue: bool = True, root: Path = ROOT) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(check_expected_files(kit_root))
    diagnostics.extend(check_kit_config(kit_root))
    diagnostics.extend(check_ontology_terms(kit_root))
    diagnostics.extend(check_guidance(kit_root))
    diagnostics.extend(check_examples(kit_root))
    diagnostics.extend(check_forbidden_paths(kit_root))
    if kit_root.exists():
        diagnostics.extend(check_text_policies(kit_root))
    if check_residue:
        diagnostics.extend(check_main_state_residue(root))
    return diagnostics


def _format_diagnostic(diagnostic: Diagnostic) -> str:
    location = diagnostic.path
    if diagnostic.line:
        location = f"{location}:{diagnostic.line}"
    suffix = f"\n  {diagnostic.text}" if diagnostic.text else ""
    return f"{diagnostic.diagnostic_id}: {location}: {diagnostic.message}{suffix}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify M056 ACP-kit v0 scaffold boundaries.")
    parser.add_argument("--kit-root", type=Path, default=DEFAULT_KIT_ROOT)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--skip-residue", action="store_true")
    args = parser.parse_args(argv)

    diagnostics = verify(args.kit_root, check_residue=not args.skip_residue, root=args.root)
    if diagnostics:
        for diagnostic in diagnostics:
            print(_format_diagnostic(diagnostic))
        return 1

    file_count = sum(1 for _ in _iter_text_files(args.kit_root)) if args.kit_root.exists() else 0
    print(f"M056 ACP-kit verification passed: files={file_count} diagnostics=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())

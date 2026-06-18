#!/usr/bin/env python3
"""Focused M065 S01 git-lex install-contract verifier.

This script checks the tracked Stage 2 install contract only. It is a
deterministic inspection surface: it re-reads the contract, recomputes the
source provenance from the read-only vendor checkout, asserts byte-for-byte
equality with the contract's recorded values, checks the boundary markers are
present, and checks the main law-nexus checkout has no residue (R047
contract-phase).

It does NOT run ``git lex``, does NOT initialize ``.lex``, does NOT clone, and
does NOT build. Any such side effect would be a defect in the verifier itself.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "prd" / "architecture" / "acp" / "runtime" / "m065-s01" / "install-contract.md"
DEFAULT_VENDOR_ROOT = Path("/root/vendor-source/git-lex")
MAIN_STATE_RESIDUE = (".lex", "Squad", "Raw", ".artifacts")

# All six contract sections must be present.
EXPECTED_SECTIONS = (
    "## 1. Canonical install command",
    "## 2. Source provenance",
    "## 3. Provenance policy reuse",
    "## 4. Install targets",
    "## 5. S02 and S03 acceptance",
    "## 6. CLI-install-only boundary",
)

# Boundary markers that must appear in the contract.
EXPECTED_BOUNDARY_MARKERS = (
    "cargo install --path . --locked",   # canonical install command
    "CLI-install-only",                  # boundary label
    "R047",                              # main-checkout residue guard
    "R035/R037/R038",                    # active, not source-truth
    "ACP-kit",                           # not source truth in this stage
    "Stage 3",                           # .lex adoption is later/blocked
    "D084",                              # adoption roadmap
    "D089",                              # this contract
    "D077",                              # source pin
    "--version",                         # version-gap constraint on S02
)

# Provenance fields parsed from the contract's YAML block.
_PROVENANCE_PATTERNS = {
    "source_commit": re.compile(r"source_commit:\s*([0-9a-f]{40})\b"),
    "cargo_toml_sha256": re.compile(r"cargo_toml_sha256:\s*([0-9a-f]{64})\b"),
    "cargo_lock_sha256": re.compile(r"cargo_lock_sha256:\s*([0-9a-f]{64})\b"),
}

DIAGNOSTIC_IDS = (
    "missing_contract_file",
    "vendor_source_missing",
    "missing_section",
    "missing_boundary_marker",
    "provenance_record_missing",
    "provenance_mismatch",
    "main_state_residue",
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


def check_contract_file(contract: Path) -> list[Diagnostic]:
    if not contract.exists():
        return [_diagnostic("missing_contract_file", contract, 0, f"contract file is missing: {contract}")]
    return []


def check_sections(text: str, contract: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for header in EXPECTED_SECTIONS:
        if header not in text:
            diagnostics.append(_diagnostic("missing_section", contract, 0, f"required contract section missing: {header}"))
    return diagnostics


def check_boundary_markers(text: str, contract: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for marker in EXPECTED_BOUNDARY_MARKERS:
        if marker not in text:
            diagnostics.append(_diagnostic("missing_boundary_marker", contract, 0, f"required boundary marker missing: {marker}"))
    return diagnostics


def _parse_provenance(text: str, contract: Path) -> tuple[dict[str, str], list[Diagnostic]]:
    recorded: dict[str, str] = {}
    diagnostics: list[Diagnostic] = []
    for field, pattern in _PROVENANCE_PATTERNS.items():
        match = pattern.search(text)
        if match is None:
            diagnostics.append(_diagnostic("provenance_record_missing", contract, 0, f"contract does not record provenance field: {field}"))
        else:
            recorded[field] = match.group(1)
    return recorded, diagnostics


def _git_head(vendor_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(vendor_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip()


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_provenance(text: str, contract: Path, vendor_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not vendor_root.exists():
        diagnostics.append(_diagnostic("vendor_source_missing", vendor_root, 0, f"vendor source checkout is missing: {vendor_root}"))
        return diagnostics

    recorded, parse_diags = _parse_provenance(text, contract)
    diagnostics.extend(parse_diags)

    actual = {
        "source_commit": _git_head(vendor_root),
        "cargo_toml_sha256": _sha256(vendor_root / "Cargo.toml"),
        "cargo_lock_sha256": _sha256(vendor_root / "Cargo.lock"),
    }

    for field in _PROVENANCE_PATTERNS:
        rec = recorded.get(field)
        act = actual.get(field)
        if rec is None:
            continue  # already reported as provenance_record_missing
        if act is None:
            diagnostics.append(_diagnostic("provenance_mismatch", contract, 0, f"could not recompute {field} from {vendor_root}"))
        elif rec != act:
            diagnostics.append(
                _diagnostic(
                    "provenance_mismatch",
                    contract,
                    0,
                    f"{field} drift: contract records {rec} but vendor source recomputes to {act}",
                )
            )
    return diagnostics


def check_main_state_residue(root: Path = ROOT) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for relative in MAIN_STATE_RESIDUE:
        path = root / relative
        if path.exists():
            diagnostics.append(_diagnostic("main_state_residue", path, 0, f"main checkout residue exists: {relative} (R047 contract-phase)"))
    return diagnostics


def verify(contract: Path = DEFAULT_CONTRACT, vendor_root: Path = DEFAULT_VENDOR_ROOT, *, root: Path = ROOT, check_residue: bool = True) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(check_contract_file(contract))
    if contract.exists():
        text = contract.read_text(encoding="utf-8")
        diagnostics.extend(check_sections(text, contract))
        diagnostics.extend(check_boundary_markers(text, contract))
        diagnostics.extend(check_provenance(text, contract, vendor_root))
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
    parser = argparse.ArgumentParser(description="Verify the M065 S01 git-lex install contract (Stage 2 of D084).")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--vendor-root", type=Path, default=DEFAULT_VENDOR_ROOT)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--skip-residue", action="store_true")
    args = parser.parse_args(argv)

    diagnostics = verify(args.contract, args.vendor_root, root=args.root, check_residue=not args.skip_residue)
    if diagnostics:
        for diagnostic in diagnostics:
            print(_format_diagnostic(diagnostic))
        return 1

    section_count = sum(1 for header in EXPECTED_SECTIONS if header in args.contract.read_text(encoding="utf-8")) if args.contract.exists() else 0
    print(f"M065 S01 install-contract verification passed: sections={section_count}/{len(EXPECTED_SECTIONS)} diagnostics=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())

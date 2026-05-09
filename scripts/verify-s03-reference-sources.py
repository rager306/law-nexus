#!/usr/bin/env python3
"""Verify S03 reference source checkouts and GitNexus evidence manifest.

This verifier is intentionally conservative. S03 proves source/index readiness only;
it must not infer FalkorDB, FalkorDBLite, falkordb-py, or odfpy runtime behavior.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".gsd/milestones/M001/slices/S03/S03-REFERENCE-SOURCES.md"
VENDOR_ROOT = Path("/root/vendor-source")


@dataclass(frozen=True)
class ReferenceRepo:
    key: str
    name: str
    url: str
    local_path: Path
    purpose: str
    gitnexus_query: str


REFERENCES: tuple[ReferenceRepo, ...] = (
    ReferenceRepo(
        key="falkordb",
        name="FalkorDB",
        url="https://github.com/FalkorDB/FalkorDB.git",
        local_path=VENDOR_ROOT / "FalkorDB",
        purpose="FalkorDB engine source for GraphBLAS/OpenCypher/index/UDF capability evidence.",
        gitnexus_query="GraphBLAS OpenCypher full-text vector UDF",
    ),
    ReferenceRepo(
        key="falkordb-py",
        name="falkordb-py",
        url="https://github.com/FalkorDB/falkordb-py.git",
        local_path=VENDOR_ROOT / "falkordb-py",
        purpose="Python client source for driver/API evidence and future smoke harness boundaries.",
        gitnexus_query="FalkorDB Python client query graph API",
    ),
    ReferenceRepo(
        key="falkordblite",
        name="FalkorDBLite",
        url="https://github.com/FalkorDB/falkordblite.git",
        local_path=VENDOR_ROOT / "falkordblite",
        purpose="Embedded FalkorDBLite source for local runtime packaging and persistence evidence.",
        gitnexus_query="embedded FalkorDBLite persistence UDF API",
    ),
    ReferenceRepo(
        key="odfpy",
        name="odfpy",
        url="https://github.com/eea/odfpy.git",
        local_path=VENDOR_ROOT / "odfpy",
        purpose="ODF/ODT parser source for S05 real `44-fz.odt` parser verification.",
        gitnexus_query="odfpy OpenDocument text table style parsing",
    ),
)


class CheckFailure(Exception):
    pass


def run_git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise CheckFailure(f"git -C {path} {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def normalize_remote(remote: str) -> str:
    remote = remote.strip()
    if remote.endswith("/"):
        remote = remote[:-1]
    if remote.startswith("git@github.com:"):
        remote = "https://github.com/" + remote.removeprefix("git@github.com:")
    if remote.endswith(".git"):
        remote = remote[:-4]
    return remote


def expected_manifest_block(ref: ReferenceRepo) -> str:
    return f"| `{ref.key}` | `{ref.name}` | `{ref.url}` | `{ref.local_path}` |"


def read_manifest() -> str:
    if not MANIFEST.is_file():
        raise CheckFailure(f"manifest missing: {MANIFEST}")
    text = MANIFEST.read_text(encoding="utf-8")
    if not text.strip():
        raise CheckFailure(f"manifest empty: {MANIFEST}")
    return text


def check_manifest_structure(text: str) -> list[str]:
    failures: list[str] = []
    required_sections = [
        "# S03 Reference Sources",
        "## Purpose",
        "## Expected References",
        "## Checkout Status",
        "## GitNexus Addressability",
        "## Evidence Boundary",
        "## Verification Commands",
        "## Blocked / Follow-up Diagnostics",
    ]
    for section in required_sections:
        if section not in text:
            failures.append(f"manifest missing section: {section}")
    for ref in REFERENCES:
        if expected_manifest_block(ref) not in text:
            failures.append(f"manifest missing expected reference row for {ref.key}")
        if str(ref.local_path) not in text:
            failures.append(f"manifest missing local path for {ref.key}: {ref.local_path}")
        if ref.url not in text:
            failures.append(f"manifest missing remote URL for {ref.key}: {ref.url}")
    if "M001 architecture-only" not in text:
        failures.append("manifest must preserve the M001 architecture-only boundary")
    if "S04" not in text or "S05" not in text:
        failures.append("manifest must name downstream S04/S05 proof owners")
    return failures


def extract_checkout_row(text: str, key: str) -> str | None:
    marker = "## Checkout Status"
    start = text.find(marker)
    if start == -1:
        return None
    next_section = text.find("\n## ", start + len(marker))
    section = text[start:] if next_section == -1 else text[start:next_section]
    pattern = re.compile(rf"^\| `{re.escape(key)}` \| .*$", re.MULTILINE)
    match = pattern.search(section)
    return match.group(0) if match else None


def checkout_row_cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def check_checkout(ref: ReferenceRepo, text: str) -> list[str]:
    failures: list[str] = []
    if not ref.local_path.is_dir():
        return [f"checkout missing for {ref.key}: {ref.local_path}"]
    git_dir = ref.local_path / ".git"
    if not git_dir.exists():
        failures.append(f"checkout is not a git repository for {ref.key}: {ref.local_path}")
        return failures

    try:
        actual_remote = run_git(ref.local_path, "remote", "get-url", "origin")
        head = run_git(ref.local_path, "rev-parse", "HEAD")
    except CheckFailure as exc:
        failures.append(str(exc))
        return failures

    if normalize_remote(actual_remote) != normalize_remote(ref.url):
        failures.append(
            f"remote mismatch for {ref.key}: expected {ref.url}, got {actual_remote}"
        )
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        failures.append(f"invalid HEAD hash for {ref.key}: {head}")

    row = extract_checkout_row(text, ref.key)
    if row is None:
        failures.append(f"manifest row missing for checkout {ref.key}")
    else:
        cells = checkout_row_cells(row)
        checkout_cell = cells[5] if len(cells) > 5 else ""
        if head not in row:
            failures.append(f"manifest row for {ref.key} does not include HEAD commit {head}")
        if "pending" in checkout_cell.lower() or "TBD" in checkout_cell or "TODO" in checkout_cell:
            failures.append(f"manifest row for {ref.key} still has pending/TBD/TODO checkout data")
    return failures


def check_gitnexus_evidence(text: str) -> list[str]:
    failures: list[str] = []
    for ref in REFERENCES:
        row = extract_checkout_row(text, ref.key)
        if row is None:
            failures.append(f"manifest row missing for GitNexus evidence {ref.key}")
            continue
        has_repo_name = re.search(r"gitnexus:[^|` ]+", row, flags=re.IGNORECASE)
        has_blocked = re.search(r"blocked|not indexed|failed|unavailable", row, flags=re.IGNORECASE)
        if not (has_repo_name or has_blocked):
            failures.append(
                f"manifest row for {ref.key} must include GitNexus repo evidence or explicit blocked diagnostic"
            )
    if "Representative GitNexus/source checks" not in text:
        failures.append("manifest missing representative GitNexus/source checks section text")
    return failures


def print_reference_summary() -> None:
    print("Expected S03 references:")
    for ref in REFERENCES:
        print(f"- {ref.key}: {ref.url} -> {ref.local_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-missing-checkouts",
        action="store_true",
        help="T01 mode: validate manifest scaffold without requiring cloned repos yet.",
    )
    parser.add_argument(
        "--check-checkouts",
        action="store_true",
        help="Require git checkouts, remotes, HEAD pins, and manifest commit rows.",
    )
    parser.add_argument(
        "--check-gitnexus-evidence",
        action="store_true",
        help="Require GitNexus repo evidence or explicit blocked diagnostics for each reference.",
    )
    parser.add_argument(
        "--list-expected",
        action="store_true",
        help="Print the expected repo mapping and exit.",
    )
    args = parser.parse_args()

    if args.list_expected:
        print_reference_summary()
        return 0

    failures: list[str] = []
    try:
        text = read_manifest()
    except CheckFailure as exc:
        print(f"[FAIL] {exc}")
        return 1

    failures.extend(check_manifest_structure(text))

    if args.check_checkouts:
        for ref in REFERENCES:
            failures.extend(check_checkout(ref, text))
    elif not args.allow_missing_checkouts:
        missing = [ref for ref in REFERENCES if not ref.local_path.is_dir()]
        if missing:
            failures.append(
                "missing checkouts: " + ", ".join(f"{ref.key} ({ref.local_path})" for ref in missing)
            )

    if args.check_gitnexus_evidence:
        failures.extend(check_gitnexus_evidence(text))

    if failures:
        print("S03 reference source verification failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("S03 reference source verification passed.")
    if args.allow_missing_checkouts:
        print("Mode: manifest scaffold; missing checkouts are allowed for T01 only.")
    elif args.check_checkouts:
        print("Mode: checkout verification; git remotes and commit pins are required.")
    if args.check_gitnexus_evidence:
        print("Mode: GitNexus evidence verification; repo evidence or blocked diagnostics required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

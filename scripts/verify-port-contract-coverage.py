#!/usr/bin/env python3
"""Inventory InMemory adapters vs shared ln-testkit port-contract coverage.

ADR-0015 process diagnostic. Adapter identity is crate-qualified
(`crate::StructName`) so same-named InMemory types in different crates are not
collapsed. Default mode is report-only (exit 0) so remaining debt is visible
without blocking. Use --strict to fail when any adapter remains uncovered.

Lifecycle: `[bounded]` inventory only. Does not prove semantic completeness of
covered contracts or real-infrastructure validation.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CRATES = ROOT / "crates"

# Crate-qualified adapters currently exercised by crates/ln-testkit tests.
COVERED_INMEMORY_ADAPTERS: frozenset[str] = frozenset(
    {
        "ln-storage::InMemoryVectorStore",
        "ln-storage::InMemoryGraphStore",
        "ln-citation::InMemoryCitationSource",
        "ln-promote::InMemoryPromotionStore",
        "ln-query::InMemoryQueryState",
        "ln-publish::InMemoryPublicationLedger",
        "ln-decode::InMemoryDiagnosticSink",
    }
)

STRUCT_RE = re.compile(r"\bstruct\s+(InMemory[A-Za-z0-9_]+)\b")
SCHEMA_VERSION = "law-nexus/port-contract-coverage/v2"


def crate_name_from_path(path: Path, crates_root: Path) -> str:
    rel = path.relative_to(crates_root)
    return rel.parts[0]


def adapter_identity(crate: str, struct_name: str) -> str:
    return f"{crate}::{struct_name}"


def discover_inmemory_adapters(
    crates_root: Path = CRATES,
    *,
    repo_root: Path = ROOT,
) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for path in sorted(crates_root.rglob("*.rs")):
        if "target" in path.parts or "tests" in path.parts:
            continue
        # Shared contract crate is not a production adapter owner.
        if "ln-testkit" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        crate = crate_name_from_path(path, crates_root)
        rel = str(path.relative_to(repo_root))
        for name in STRUCT_RE.findall(text):
            key = adapter_identity(crate, name)
            entry = found.setdefault(
                key,
                {
                    "identity": key,
                    "crate": crate,
                    "adapter": name,
                    "paths": [],
                },
            )
            if rel not in entry["paths"]:
                entry["paths"].append(rel)
    return found


def build_report(discovered: dict[str, dict[str, Any]]) -> dict[str, Any]:
    identities = sorted(discovered)
    covered = sorted(ident for ident in identities if ident in COVERED_INMEMORY_ADAPTERS)
    uncovered = sorted(ident for ident in identities if ident not in COVERED_INMEMORY_ADAPTERS)
    missing_declared = sorted(COVERED_INMEMORY_ADAPTERS - set(identities))
    return {
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "[bounded]",
        "status": "ok" if not uncovered and not missing_declared else "debt",
        "identity_model": "crate-qualified",
        "covered_count": len(covered),
        "uncovered_count": len(uncovered),
        "discovered_count": len(identities),
        "covered": [
            {
                "identity": ident,
                "crate": discovered[ident]["crate"],
                "adapter": discovered[ident]["adapter"],
                "paths": discovered[ident]["paths"],
            }
            for ident in covered
        ],
        "uncovered": [
            {
                "identity": ident,
                "crate": discovered[ident]["crate"],
                "adapter": discovered[ident]["adapter"],
                "paths": discovered[ident]["paths"],
            }
            for ident in uncovered
        ],
        "missing_declared_covered": missing_declared,
        "declared_covered_set": sorted(COVERED_INMEMORY_ADAPTERS),
        "non_claims": [
            "Does not prove contract semantic completeness.",
            "Does not validate real TEI/RuVector adapters.",
            "Does not require full coverage on default (report-only) runs.",
            "Same short adapter names in different crates are distinct identities.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when uncovered InMemory adapters remain",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    crates_root = root / "crates"
    discovered = discover_inmemory_adapters(crates_root, repo_root=root)
    report = build_report(discovered)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.strict and (report["uncovered_count"] > 0 or report["missing_declared_covered"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

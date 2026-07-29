#!/usr/bin/env python3
"""Inventory InMemory adapters vs shared ln-testkit port-contract coverage.

ADR-0015 / M146 process diagnostic. Default mode is report-only (exit 0) so
remaining debt is visible without blocking. Use --strict to fail when any
InMemory adapter remains uncovered.

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

# Adapters currently exercised by crates/ln-testkit tests.
COVERED_INMEMORY_ADAPTERS: frozenset[str] = frozenset(
    {
        "InMemoryVectorStore",
        "InMemoryGraphStore",
        "InMemoryCitationSource",
        "InMemoryPromotionStore",
        "InMemoryQueryState",
    }
)

STRUCT_RE = re.compile(r"\bstruct\s+(InMemory[A-Za-z0-9_]+)\b")


def discover_inmemory_adapters(
    crates_root: Path = CRATES,
    *,
    repo_root: Path = ROOT,
) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in sorted(crates_root.rglob("*.rs")):
        if "target" in path.parts or "tests" in path.parts:
            continue
        # Shared contract crate is not a production adapter owner.
        if "ln-testkit" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for name in STRUCT_RE.findall(text):
            rel = str(path.relative_to(repo_root))
            found.setdefault(name, []).append(rel)
    return found


def build_report(discovered: dict[str, list[str]]) -> dict[str, Any]:
    names = sorted(discovered)
    covered = sorted(name for name in names if name in COVERED_INMEMORY_ADAPTERS)
    uncovered = sorted(name for name in names if name not in COVERED_INMEMORY_ADAPTERS)
    missing_declared = sorted(COVERED_INMEMORY_ADAPTERS - set(names))
    return {
        "schema_version": "law-nexus/port-contract-coverage/v1",
        "lifecycle": "[bounded]",
        "status": "ok" if not uncovered and not missing_declared else "debt",
        "covered_count": len(covered),
        "uncovered_count": len(uncovered),
        "discovered_count": len(names),
        "covered": [{"adapter": name, "paths": discovered[name]} for name in covered],
        "uncovered": [{"adapter": name, "paths": discovered[name]} for name in uncovered],
        "missing_declared_covered": missing_declared,
        "declared_covered_set": sorted(COVERED_INMEMORY_ADAPTERS),
        "non_claims": [
            "Does not prove contract semantic completeness.",
            "Does not validate real TEI/RuVector adapters.",
            "Does not require full coverage on default (report-only) runs.",
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

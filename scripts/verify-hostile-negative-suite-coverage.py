#!/usr/bin/env python3
"""Inventory hostile adapters vs shared ln-testkit negative suites.

ADR-0015 process diagnostic. Discovers production hostile adapter structs and
classifies whether ln-testkit source/tests mention them (shared negative suite
surface). Default mode is report-only (exit 0). Use --strict to fail when any
hostile adapter lacks a shared negative mention.

Lifecycle: `[bounded]` inventory only. Crate-local HC hostile tests are not
shared suites. Does not prove semantic completeness of negative suites or real
infrastructure validation.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CRATES = ROOT / "crates"
TESTKIT = CRATES / "ln-testkit"

HOSTILE_STRUCT_RE = re.compile(
    r"\bstruct\s+("
    r"Hostile[A-Za-z0-9_]+|"
    r"InPlaceMutatingHostile[A-Za-z0-9_]+|"
    r"ErasingMergerHostile[A-Za-z0-9_]+|"
    r"OpenRelationHostile[A-Za-z0-9_]+"
    r")\b"
)
SCHEMA_VERSION = "law-nexus/hostile-negative-suite-coverage/v1"


def _crate_name(path: Path, crates_root: Path) -> str:
    return path.relative_to(crates_root).parts[0]


def _identity(crate: str, struct_name: str) -> str:
    return f"{crate}::{struct_name}"


def load_testkit_text(testkit_root: Path = TESTKIT) -> str:
    if not testkit_root.is_dir():
        return ""
    chunks: list[str] = []
    for path in sorted(testkit_root.rglob("*.rs")):
        if "target" in path.parts:
            continue
        chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def discover_hostile_adapters(
    crates_root: Path = CRATES,
    *,
    repo_root: Path = ROOT,
) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for path in sorted(crates_root.rglob("*.rs")):
        if "target" in path.parts or "tests" in path.parts:
            continue
        if "ln-testkit" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        crate = _crate_name(path, crates_root)
        rel = str(path.relative_to(repo_root))
        for name in HOSTILE_STRUCT_RE.findall(text):
            key = _identity(crate, name)
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


def build_report(
    discovered: dict[str, dict[str, Any]],
    *,
    testkit_text: str,
) -> dict[str, Any]:
    covered: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for key in sorted(discovered):
        item = discovered[key]
        has_shared = item["adapter"] in testkit_text
        row = {
            "identity": item["identity"],
            "crate": item["crate"],
            "adapter": item["adapter"],
            "paths": item["paths"],
            "shared_negative_mentioned": has_shared,
        }
        if has_shared:
            covered.append(row)
        else:
            missing.append(row)

    return {
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "[bounded]",
        "status": "ok" if not missing else "debt",
        "identity_model": "crate-qualified",
        "discovered_count": len(discovered),
        "with_shared_negative_count": len(covered),
        "missing_shared_negative_count": len(missing),
        "with_shared_negative": covered,
        "missing_shared_negative": missing,
        "non_claims": [
            "Shared-negative classification is mention-based in ln-testkit sources/tests.",
            "Crate-local HC hostile tests are not shared suites.",
            "Does not prove negative-suite semantic completeness.",
            "Does not validate real TEI/RuVector adapters or product readiness.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when hostile adapters lack shared negative mentions",
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
    testkit_root = crates_root / "ln-testkit"
    discovered = discover_hostile_adapters(crates_root, repo_root=root)
    report = build_report(discovered, testkit_text=load_testkit_text(testkit_root))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.strict and report["missing_shared_negative_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

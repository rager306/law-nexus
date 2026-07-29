#!/usr/bin/env python3
"""Inventory multi-adapter ports vs shared ln-testkit real-adapter coverage.

ADR-0015 process diagnostic. Discovers outbound ports with two or more
production adapter implementations and classifies whether each *real* adapter
is mentioned in ln-testkit (shared suite surface). Fake/hostile/honest fixtures
are listed for context but do not create residual debt.

Default mode is report-only (exit 0). Use --strict to fail when any real adapter
on a multi-adapter port lacks a shared suite mention.

Lifecycle: `[bounded]` inventory only. Mention-based classification does not
prove semantic suite completeness, live TEI/RuVector validation, or product
readiness.
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

PORT_TRAIT_RE = re.compile(r"\bpub\s+trait\s+(\w+Port)\b")
PORT_IMPL_RE = re.compile(r"\bimpl(?:\s*<[^>]*>)?\s+(\w+Port)\s+for\s+(\w+)\b")

# Adapters that are intentional fakes/hostiles/fixtures — not residual real debt.
NON_REAL_ADAPTER_RE = re.compile(
    r"^(?:"
    r"InMemory|"
    r"Hostile|"
    r"Honest|"
    r"Fixed|"
    r"Stub|"
    r"Malicious|"
    r"Successful|"
    r"Failing|"
    r"OpenRelationHostile|"
    r"InPlaceMutating|"
    r"ErasingMerger|"
    r"SubstitutingHostile"
    r")"
)

SCHEMA_VERSION = "law-nexus/multi-adapter-port-coverage/v1"


def _crate_name(path: Path, crates_root: Path) -> str:
    return path.relative_to(crates_root).parts[0]


def _identity(crate: str, name: str) -> str:
    return f"{crate}::{name}"


def is_real_adapter(adapter: str) -> bool:
    """Return True when adapter is not a known fake/hostile/fixture name."""
    return NON_REAL_ADAPTER_RE.match(adapter) is None


def load_testkit_text(testkit_root: Path = TESTKIT) -> str:
    if not testkit_root.is_dir():
        return ""
    chunks: list[str] = []
    for path in sorted(testkit_root.rglob("*.rs")):
        if "target" in path.parts:
            continue
        chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def discover_port_impls(
    crates_root: Path = CRATES,
    *,
    repo_root: Path = ROOT,
) -> dict[str, dict[str, Any]]:
    """Discover production Port traits and their adapter implementations.

    Skips tests/, target/, and ln-testkit. Keys are port trait names.
    """
    ports: dict[str, dict[str, Any]] = {}

    for path in sorted(crates_root.rglob("*.rs")):
        if "target" in path.parts or "tests" in path.parts:
            continue
        if "ln-testkit" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        crate = _crate_name(path, crates_root)
        rel = str(path.relative_to(repo_root))

        for port in PORT_TRAIT_RE.findall(text):
            entry = ports.setdefault(
                port,
                {
                    "port": port,
                    "def_paths": [],
                    "impls": {},
                },
            )
            if rel not in entry["def_paths"]:
                entry["def_paths"].append(rel)

        for port, adapter in PORT_IMPL_RE.findall(text):
            entry = ports.setdefault(
                port,
                {
                    "port": port,
                    "def_paths": [],
                    "impls": {},
                },
            )
            identity = _identity(crate, adapter)
            impl = entry["impls"].setdefault(
                identity,
                {
                    "identity": identity,
                    "crate": crate,
                    "adapter": adapter,
                    "port": port,
                    "paths": [],
                    "real": is_real_adapter(adapter),
                },
            )
            if rel not in impl["paths"]:
                impl["paths"].append(rel)

    return ports


def build_report(
    ports: dict[str, dict[str, Any]],
    *,
    testkit_text: str,
) -> dict[str, Any]:
    multi: list[dict[str, Any]] = []
    covered_real: list[dict[str, Any]] = []
    missing_real: list[dict[str, Any]] = []

    for port_name in sorted(ports):
        entry = ports[port_name]
        impls = list(entry["impls"].values())
        if len(impls) < 2:
            continue

        port_row: dict[str, Any] = {
            "port": port_name,
            "def_paths": entry["def_paths"],
            "impl_count": len(impls),
            "impls": [],
        }
        for impl in sorted(impls, key=lambda item: item["identity"]):
            mentioned = impl["adapter"] in testkit_text
            row = {
                "identity": impl["identity"],
                "crate": impl["crate"],
                "adapter": impl["adapter"],
                "port": port_name,
                "paths": impl["paths"],
                "real": impl["real"],
                "shared_suite_mentioned": mentioned,
            }
            port_row["impls"].append(row)
            if impl["real"]:
                if mentioned:
                    covered_real.append(row)
                else:
                    missing_real.append(row)
        multi.append(port_row)

    return {
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "[bounded]",
        "status": "ok" if not missing_real else "debt",
        "identity_model": "crate-qualified",
        "multi_adapter_port_count": len(multi),
        "real_adapter_count": len(covered_real) + len(missing_real),
        "with_shared_suite_count": len(covered_real),
        "missing_shared_suite_count": len(missing_real),
        "multi_adapter_ports": multi,
        "with_shared_suite": covered_real,
        "missing_shared_suite": missing_real,
        "non_claims": [
            "Real-adapter classification is name-heuristic (excludes InMemory/Hostile/Honest/Fixed/Stub/Malicious fixtures).",
            "Shared-suite classification is mention-based in ln-testkit sources/tests.",
            "Does not prove semantic suite completeness.",
            "Does not validate live TEI/RuVector adapters or product readiness.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when real multi-adapter ports lack shared suite mentions",
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
    ports = discover_port_impls(crates_root, repo_root=root)
    report = build_report(ports, testkit_text=load_testkit_text(testkit_root))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.strict and report["missing_shared_suite_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

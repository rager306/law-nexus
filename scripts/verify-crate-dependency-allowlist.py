#!/usr/bin/env python3
"""Verify workspace crate path-dependency edges against a tracked allowlist.

Implements ADR-0015 follow-on: executable hexagonal dependency direction check
using `cargo metadata --no-deps --format-version 1`.

Exit codes:
  0 — conformant
  1 — violations found or configuration/runtime error
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = ROOT / "prd" / "architecture" / "crate-dependency-allowlist.json"


def load_allowlist(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "law-nexus/crate-dependency-allowlist/v1":
        raise ValueError(f"unsupported allowlist schema in {path}")
    edges = payload.get("allowed_edges")
    if not isinstance(edges, list) or not edges:
        raise ValueError("allowed_edges must be a non-empty list")
    normalized: set[tuple[str, str]] = set()
    for item in edges:
        if not (isinstance(item, list) and len(item) == 2):
            raise ValueError(f"invalid allowed edge entry: {item!r}")
        normalized.add((str(item[0]), str(item[1])))
    payload["_allowed_set"] = normalized
    return payload


def workspace_path_edges(root: Path) -> set[tuple[str, str]]:
    proc = subprocess.run(
        ["cargo", "metadata", "--no-deps", "--format-version", "1"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"cargo metadata failed:\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    meta = json.loads(proc.stdout)
    workspace_ids = set(meta["workspace_members"])
    packages = [p for p in meta["packages"] if p["id"] in workspace_ids]
    by_name = {p["name"]: p for p in packages}
    edges: set[tuple[str, str]] = set()
    for package in packages:
        for dep in package.get("dependencies", []):
            dep_name = dep.get("name")
            if dep_name in by_name and dep_name != package["name"]:
                edges.add((package["name"], dep_name))
    return edges


def is_hc_runner(name: str) -> bool:
    return name.startswith("ln-hc") and name.endswith("-runner")


def is_capability_crate(name: str) -> bool:
    if not name.startswith("ln-"):
        return False
    if name in {"ln-product-cli", "ln-status", "ln-testkit"}:
        return False
    if is_hc_runner(name):
        return False
    return True


def evaluate_edges(
    observed: set[tuple[str, str]],
    allowlist: dict[str, Any],
) -> list[dict[str, str]]:
    allowed: set[tuple[str, str]] = allowlist["_allowed_set"]
    findings: list[dict[str, str]] = []

    extra = sorted(observed - allowed)
    missing = sorted(allowed - observed)
    for source, target in extra:
        findings.append(
            {
                "code": "UNDECLARED_WORKSPACE_EDGE",
                "severity": "error",
                "message": f"workspace path edge not in allowlist: {source} -> {target}",
                "remediation": (
                    "Add the edge to prd/architecture/crate-dependency-allowlist.json "
                    "only if hexagonal composition intentionally requires it; otherwise "
                    "remove the dependency."
                ),
            }
        )
    for source, target in missing:
        findings.append(
            {
                "code": "MISSING_DECLARED_EDGE",
                "severity": "error",
                "message": (
                    f"allowlist declares edge not present in workspace: {source} -> {target}"
                ),
                "remediation": (
                    "Remove the stale allowlist entry or restore the intentional dependency."
                ),
            }
        )

    rules = allowlist.get("rules") or {}
    if rules.get("forbid_capability_depending_on_hc_runners"):
        for source, target in sorted(observed):
            if is_capability_crate(source) and is_hc_runner(target):
                findings.append(
                    {
                        "code": "CAPABILITY_DEPENDS_ON_HC_RUNNER",
                        "severity": "error",
                        "message": f"capability crate depends on HC runner: {source} -> {target}",
                        "remediation": "Dependency direction must be runner -> capability, not reverse.",
                    }
                )
    if rules.get("forbid_capability_depending_on_product_cli"):
        for source, target in sorted(observed):
            if is_capability_crate(source) and target == "ln-product-cli":
                findings.append(
                    {
                        "code": "CAPABILITY_DEPENDS_ON_PRODUCT_CLI",
                        "severity": "error",
                        "message": f"capability crate depends on product CLI: {source} -> {target}",
                        "remediation": "Keep composition in ln-product-cli; capabilities must not depend on CLI.",
                    }
                )
    return findings


def build_report(
    *,
    root: Path,
    allowlist_path: Path,
    observed: set[tuple[str, str]],
    findings: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "schema_version": "law-nexus/crate-dependency-allowlist-report/v1",
        "status": "ok" if not findings else "failure",
        "root": str(root),
        "allowlist_path": str(allowlist_path.relative_to(root)),
        "observed_edge_count": len(observed),
        "finding_count": len(findings),
        "findings": findings,
        "lifecycle": "[bounded]",
        "non_claims": [
            "Does not prove full domain/application/adapter layer tagging.",
            "Does not validate external registry dependencies.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=DEFAULT_ALLOWLIST,
        help="path to allowlist JSON",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="print report JSON and always exit 0",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    allowlist_path = args.allowlist.resolve()
    try:
        allowlist = load_allowlist(allowlist_path)
        observed = workspace_path_edges(root)
        findings = evaluate_edges(observed, allowlist)
        report = build_report(
            root=root,
            allowlist_path=allowlist_path,
            observed=observed,
            findings=findings,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        err = {
            "schema_version": "law-nexus/crate-dependency-allowlist-report/v1",
            "status": "failure",
            "finding_count": 1,
            "findings": [
                {
                    "code": "ALLOWLIST_RUNTIME_ERROR",
                    "severity": "error",
                    "message": str(exc),
                    "remediation": "Fix allowlist JSON or cargo metadata availability.",
                }
            ],
        }
        print(json.dumps(err, indent=2, ensure_ascii=False))
        return 0 if args.report_only else 1

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.report_only:
        return 0
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())

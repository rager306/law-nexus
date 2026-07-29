#!/usr/bin/env python3
"""Report-only live-adapter readiness inventory (ADR-0014 / ADR-0015).

Classifies TEI and RuVector product-adapter readiness from repository evidence:

- TEI: `TeiEmbeddingAdapter` + injectable `EmbeddingTransport` without HTTP client
  dependencies is `stub_transport_only` (not live TEI validation).
- RuVector: ADR-0014 lifecycle `[proposed]` without workspace redb/ruvector product
  dependencies is `proposed` (not product runtime readiness).

Default mode is report-only (exit 0). Use `--strict` to fail when overclaim
markers are found. This script never performs live HTTP or external service calls.

Lifecycle: `[bounded]` process inventory only. Does not validate live TEI/RuVector
adapters or product readiness.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "law-nexus/live-adapter-readiness/v1"

HTTP_CLIENT_MARKERS = ("reqwest", "ureq", "hyper::", "Client::new")
PRODUCT_DEP_MARKERS = ("ruvector", "redb", "reqwest", "ureq")
OVERCLAIM_RES = (
    re.compile(r"\blive\s+TEI\b.*\b(validated|ready|production)\b", re.I),
    re.compile(r"\bTEI\b.*\b(validated|production-ready)\b", re.I),
    re.compile(r"\bRuVector\b.*\b(validated|production-ready|product runtime ready)\b", re.I),
    re.compile(r"\[validated\].*\b(TEI|RuVector|ruvector|tei)\b", re.I),
)
NONCLAIM_HINT = re.compile(
    r"\b(no claim|not claim|not proven|not validate|not validated|not ready|"
    r"does not validate|remain(?:s)? \[proposed\]|stub only|stub transport|"
    r"not product readiness|without claiming)\b",
    re.I,
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _scan_cargo_deps(root: Path) -> list[str]:
    hits: list[str] = []
    cargo_files = [root / "Cargo.toml", *sorted((root / "crates").rglob("Cargo.toml"))]
    for path in cargo_files:
        if not path.is_file():
            continue
        text = _read(path)
        for marker in PRODUCT_DEP_MARKERS:
            if re.search(rf"\b{re.escape(marker)}\b", text, re.I):
                hits.append(f"{path.relative_to(root)}:{marker}")
    return hits


def _scan_http_clients(root: Path) -> list[str]:
    hits: list[str] = []
    storage = root / "crates" / "ln-storage"
    if not storage.is_dir():
        return hits
    for path in sorted(storage.rglob("*.rs")):
        if "tests" in path.parts or "target" in path.parts:
            continue
        text = _read(path)
        for marker in HTTP_CLIENT_MARKERS:
            if marker in text:
                hits.append(f"{path.relative_to(root)}:{marker}")
    return hits


def _adr_0014_lifecycle(root: Path) -> dict[str, Any]:
    path = root / "doc" / "adr" / "0014-ruvector-primary-infrastructure.md"
    if not path.is_file():
        return {
            "path": str(path.relative_to(root))
            if path.exists()
            else "doc/adr/0014-ruvector-primary-infrastructure.md",
            "present": False,
            "lifecycle": "missing",
        }
    text = _read(path)
    lifecycle = "unknown"
    m = re.search(r'^lifecycle:\s*"?\[([^\]]+)\]"?', text, re.M)
    if m:
        lifecycle = m.group(1)
    elif re.search(r"Accepted\s+`\[proposed\]`", text):
        lifecycle = "proposed"
    return {
        "path": str(path.relative_to(root)),
        "present": True,
        "lifecycle": lifecycle,
    }


def _tei_surface(root: Path) -> dict[str, Any]:
    tei_path = root / "crates" / "ln-storage" / "src" / "adapters" / "tei.rs"
    present = tei_path.is_file()
    text = _read(tei_path) if present else ""
    has_adapter = "TeiEmbeddingAdapter" in text
    has_transport = "EmbeddingTransport" in text
    http_hits = _scan_http_clients(root)
    cargo_hits = [h for h in _scan_cargo_deps(root) if h.endswith(("reqwest", "ureq"))]
    if present and has_adapter and has_transport and not http_hits and not cargo_hits:
        status = "stub_transport_only"
    elif present and has_adapter and (http_hits or cargo_hits):
        status = "http_surface_present_unproven"
    elif present:
        status = "partial_surface"
    else:
        status = "absent"
    return {
        "status": status,
        "path": str(tei_path.relative_to(root)) if present else None,
        "has_tei_embedding_adapter": has_adapter,
        "has_embedding_transport": has_transport,
        "http_client_hits": http_hits,
        "cargo_http_hits": cargo_hits,
    }


def _ruvector_surface(root: Path) -> dict[str, Any]:
    adr = _adr_0014_lifecycle(root)
    cargo_hits = [h for h in _scan_cargo_deps(root) if h.endswith(("ruvector", "redb"))]
    if adr["lifecycle"] == "proposed" and not cargo_hits:
        status = "proposed"
    elif cargo_hits and adr["lifecycle"] in {"proposed", "unknown", "missing"}:
        status = "deps_present_lifecycle_not_promoted"
    elif adr["lifecycle"] in {"bounded", "validated"}:
        status = f"lifecycle_{adr['lifecycle']}_needs_runtime_proof"
    else:
        status = "unknown"
    return {
        "status": status,
        "adr": adr,
        "cargo_product_dep_hits": cargo_hits,
    }


def _scan_overclaims(root: Path) -> list[dict[str, Any]]:
    paths = [
        root / "prd" / "ARCHITECTURE.md",
        root / "doc" / "adr" / "0014-ruvector-primary-infrastructure.md",
        root / "doc" / "adr" / "0015-hexagonal-verification-architecture.md",
        root / "CHANGELOG.md",
        root / "README.md",
    ]
    findings: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file():
            continue
        for lineno, line in enumerate(_read(path).splitlines(), 1):
            if NONCLAIM_HINT.search(line):
                continue
            if any(rx.search(line) for rx in OVERCLAIM_RES):
                findings.append(
                    {
                        "path": str(path.relative_to(root)),
                        "line": lineno,
                        "text": line.strip()[:200],
                    }
                )
    return findings


def build_report(root: Path = ROOT) -> dict[str, Any]:
    tei = _tei_surface(root)
    ruvector = _ruvector_surface(root)
    overclaims = _scan_overclaims(root)
    status = "ok" if not overclaims else "debt"
    return {
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "[bounded]",
        "status": status,
        "tei": tei,
        "ruvector": ruvector,
        "overclaim_count": len(overclaims),
        "overclaims": overclaims,
        "non_claims": [
            "Does not perform live HTTP or external TEI/RuVector calls.",
            "stub_transport_only is not live TEI validation.",
            "proposed RuVector is not product runtime readiness.",
            "Does not claim product readiness, legal correctness, or citation completeness.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when overclaim markers are found",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root",
    )
    args = parser.parse_args(argv)
    report = build_report(args.root.resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.strict and report["overclaim_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

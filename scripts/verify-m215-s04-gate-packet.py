#!/usr/bin/env python3
"""Fail-closed verifier for the M215/S04 embedding supply-chain gate packet.

The packet is a durable, bounded evidence artifact for
``GATE-EMBEDDING-SUPPLY-CHAIN``. It is *not* authoritative and the gate is *not*
promoted. This verifier exists so the artifact's acceptance is objective: the
packet must satisfy this verifier, never the reverse.

Checks (all fail closed, exit 1 on the first violation):

1. Identity/lifecycle: ``schema``, ``gate_id``, ``milestone``, ``slice``,
   ``lifecycle == "[bounded]"``, ``authoritative is False``,
   ``gate_promoted is False``, ``promotion is False`` and a parseable ISO-8601
   ``recordedAt``.
2. Surfaces: ``S01``/``S02``/``S03`` are present, each with a non-empty
   ``evidence[]`` of file references that exist under the project root.
3. Checks: non-empty ``checks[]``, each with non-empty ``id``, ``command``,
   ``observed`` and ``exitCode == 0``.
4. Bounded Rust scope: ``rust_scope.scope == "crates/*/src"``,
   ``rust_scope.status == "no_managed_provider_reference"`` and
   ``rust_scope.managed_provider_hits == []``.
5. Non-claims: a list of ``{key, statement}`` objects covering all required
   non-claim keys.
6. Overclaim guard: reuses the live-adapter readiness module's
   ``OVERCLAIM_RES``/``NONCLAIM_HINT`` to scan every string in the packet. A
   match that is not exempted by ``NONCLAIM_HINT`` fails.
7. S05 Integration-class consumer: the M215 milestone declares an Integration
   verification class (the embedding text must be sourced from the M213 cleaned
   projection on a frozen fixture, not from self-contained constants). This
   check ties that declared class to a real consuming artifact without changing
   the packet's claim wording and without re-opening S01-S04: the consuming test
   ``crates/ln-testkit/tests/m213_cleaned_text_source.rs`` must exist, the
   frozen fixture ``crates/ln-decode/tests/fixtures/reader/mixed-wordml.xml``
   must still hash to its sha256 pin, and the test must reference that pin and
   the cleaned-projection pipeline markers.
8. Live cross-check (only with ``--strict``): calls the readiness module's
   ``build_report(root)`` and requires ``overclaim_count == 0``,
   ``tei.status == "http_surface_present_unproven"`` and
   ``supply_chain.managed_provider_hits == []``.

This script performs no network calls. It only reads tracked repository files.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = (
    ROOT
    / "prd"
    / "migration"
    / "rust-evidence"
    / "m215-s04-embedding-supply-chain-gate-packet.json"
)
READINESS_SCRIPT = ROOT / "scripts" / "verify-live-adapter-readiness.py"

SCHEMA = "law-nexus/m215-s04-embedding-supply-chain-gate-packet/v1"
GATE_ID = "GATE-EMBEDDING-SUPPLY-CHAIN"
MILESTONE = "M215-w9jsgn"
SLICE = "S04"
RUST_SCOPE = "crates/*/src"
REQUIRED_SURFACES = ("S01", "S02", "S03")
# M215 declares an Integration verification class: the embedding text is sourced
# from the M213 cleaned projection on a frozen fixture, not from self-contained
# constants. These constants bind that declared class to the consuming artifact
# shipped by S05 without re-opening the closed S01-S04 surfaces.
S05_TEST_REF = "crates/ln-testkit/tests/m213_cleaned_text_source.rs"
S05_FIXTURE_REF = "crates/ln-decode/tests/fixtures/reader/mixed-wordml.xml"
S05_FIXTURE_SHA256 = "d2fc1cd17f0697f575e94f09d83da5027d73afd37c700772eafa4c4a4fbc76db"
S05_PIPELINE_MARKERS = ("export_cleaned_projection", "inline_texts")
REQUIRED_NON_CLAIM_KEYS = (
    "no-live-validation",
    "no-retrieval-quality",
    "no-product-runtime",
    "cleartext-transport",
    "canonical-render-non-injective",
    "deterministic-pin-drift-detector",
    "r012-scope-level",
    "test-port-not-product-provider",
    "no-gate-promotion",
)


class VerificationError(ValueError):
    """A fail-closed packet violation."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"{path}: unreadable or malformed JSON: {exc}") from exc
    require(isinstance(value, dict), f"{path}: expected a JSON object")
    return value


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise VerificationError(f"{path}: unreadable text file: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    except OSError as exc:
        raise VerificationError(f"{path}: unreadable for sha256: {exc}") from exc
    return digest.hexdigest()


def load_readiness_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "verify_live_adapter_readiness_for_gate", READINESS_SCRIPT
    )
    require(spec is not None and spec.loader is not None, "readiness module spec unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def iter_strings(value: Any) -> Iterator[str]:
    """Yield every string scalar nested anywhere in the packet structure."""
    stack: list[Any] = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            yield item
        elif isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, (list, tuple)):
            stack.extend(item)


def parse_recorded_at(value: Any) -> datetime:
    require(isinstance(value, str) and value, "recordedAt must be a non-empty string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise VerificationError(
            f"recordedAt is not a parseable ISO-8601 timestamp: {value!r}"
        ) from exc


def surface_entries(data: dict[str, Any]) -> dict[str, Any]:
    surfaces = data.get("surfaces")
    require(isinstance(surfaces, list), "surfaces must be a list")
    by_id: dict[str, Any] = {}
    for entry in surfaces:
        require(isinstance(entry, dict), "each surface entry must be an object")
        sid = entry.get("id")
        require(isinstance(sid, str) and sid, "each surface entry needs a non-empty id")
        by_id[sid] = entry
    return by_id


def verify_surfaces(data: dict[str, Any], root: Path) -> None:
    by_id = surface_entries(data)
    for sid in REQUIRED_SURFACES:
        require(sid in by_id, f"required surface {sid} is missing")
        entry = by_id[sid]
        evidence = entry.get("evidence")
        require(
            isinstance(evidence, list) and evidence,
            f"surface {sid} needs a non-empty evidence[] list",
        )
        for ref in evidence:
            require(isinstance(ref, str) and ref, f"surface {sid} has an empty evidence ref")
            candidate = Path(ref)
            path = candidate if candidate.is_absolute() else root / candidate
            path = path.resolve()
            require(
                path == root.resolve() or root.resolve() in path.parents,
                f"surface {sid} evidence escapes project root: {ref}",
            )
            require(path.is_file(), f"surface {sid} evidence missing: {ref}")


def verify_checks(data: dict[str, Any]) -> None:
    checks = data.get("checks")
    require(isinstance(checks, list) and checks, "checks must be a non-empty list")
    for index, check in enumerate(checks):
        require(isinstance(check, dict), f"checks[{index}] must be an object")
        for field in ("id", "command", "observed"):
            value = check.get(field)
            require(
                isinstance(value, str) and value.strip(),
                f"checks[{index}].{field} must be a non-empty string",
            )
        require(
            check.get("exitCode") == 0,
            f"checks[{index}].exitCode must be 0, got {check.get('exitCode')!r}",
        )


def verify_rust_scope(data: dict[str, Any]) -> None:
    scope = data.get("rust_scope")
    require(isinstance(scope, dict), "rust_scope must be an object")
    require(scope.get("scope") == RUST_SCOPE, f"rust_scope.scope must be {RUST_SCOPE!r}")
    require(
        scope.get("status") == "no_managed_provider_reference",
        "rust_scope.status must be 'no_managed_provider_reference'",
    )
    require(
        scope.get("managed_provider_hits") == [],
        "rust_scope.managed_provider_hits must be empty",
    )


def verify_non_claims(data: dict[str, Any]) -> None:
    non_claims = data.get("non_claims")
    require(isinstance(non_claims, list) and non_claims, "non_claims must be a non-empty list")
    keys: set[str] = set()
    for index, entry in enumerate(non_claims):
        require(isinstance(entry, dict), f"non_claims[{index}] must be an object")
        key = entry.get("key")
        statement = entry.get("statement")
        require(isinstance(key, str) and key, f"non_claims[{index}].key must be non-empty")
        require(
            isinstance(statement, str) and statement.strip(),
            f"non_claims[{index}].statement must be non-empty",
        )
        keys.add(key)
    missing = [key for key in REQUIRED_NON_CLAIM_KEYS if key not in keys]
    require(not missing, f"missing required non-claim keys: {', '.join(missing)}")


def verify_overclaims(data: dict[str, Any], readiness: Any) -> None:
    overclaim_res = readiness.OVERCLAIM_RES
    nonclaim_hint = readiness.NONCLAIM_HINT
    for text in iter_strings(data):
        if nonclaim_hint.search(text):
            continue
        for pattern in overclaim_res:
            if pattern.search(text):
                raise VerificationError(
                    f"overclaim detected (pattern {pattern.pattern!r}) in packet string: "
                    f"{text[:160]!r}"
                )


def verify_s05_integration_consumer(root: Path) -> None:
    """Tie the declared M215 Integration class to its consuming S05 artifact.

    The milestone declares that the embedding text is sourced from the M213
    cleaned projection on a frozen fixture, not from self-contained constants.
    This fail-closed check requires that declared class to have a real consuming
    control: the S05 test exists, the frozen fixture still hashes to its pin, and
    the test references that pin together with the cleaned-projection pipeline
    markers. It adds no new claim and does not re-open the S01-S04 surfaces.
    """
    root = root.resolve()
    test_path = (root / S05_TEST_REF).resolve()
    require(test_path.is_file(), f"S05 consuming test is missing: {S05_TEST_REF}")
    fixture_path = (root / S05_FIXTURE_REF).resolve()
    require(fixture_path.is_file(), f"S05 frozen fixture is missing: {S05_FIXTURE_REF}")
    actual_sha256 = sha256_file(fixture_path)
    require(
        actual_sha256 == S05_FIXTURE_SHA256,
        f"S05 fixture sha256 drift: {S05_FIXTURE_REF} is {actual_sha256}, "
        f"expected {S05_FIXTURE_SHA256}",
    )
    test_text = read_text(test_path)
    require(
        S05_FIXTURE_SHA256 in test_text,
        f"S05 consuming test must pin the frozen fixture sha256 {S05_FIXTURE_SHA256}",
    )
    for marker in S05_PIPELINE_MARKERS:
        require(
            marker in test_text,
            f"S05 consuming test must consume the cleaned projection (missing marker {marker!r})",
        )


def verify_identity(data: dict[str, Any]) -> None:
    require(data.get("schema") == SCHEMA, f"schema mismatch: {data.get('schema')!r}")
    require(data.get("gate_id") == GATE_ID, f"gate_id mismatch: {data.get('gate_id')!r}")
    require(data.get("milestone") == MILESTONE, f"milestone mismatch: {data.get('milestone')!r}")
    require(data.get("slice") == SLICE, f"slice mismatch: {data.get('slice')!r}")
    require(data.get("lifecycle") == "[bounded]", "lifecycle must be '[bounded]'")
    require(data.get("authoritative") is False, "authoritative must be false")
    require(data.get("gate_promoted") is False, "gate_promoted must be false")
    require(data.get("promotion") is False, "promotion must be false")
    parse_recorded_at(data.get("recordedAt"))


def verify_packet(data: dict[str, Any], root: Path, readiness: Any) -> None:
    verify_identity(data)
    verify_surfaces(data, root)
    verify_checks(data)
    verify_rust_scope(data)
    verify_non_claims(data)
    verify_overclaims(data, readiness)
    verify_s05_integration_consumer(root)


def cross_check(root: Path, readiness: Any) -> None:
    report = readiness.build_report(root)
    require(
        report.get("overclaim_count") == 0,
        f"live readiness overclaim_count is not 0: {report.get('overclaim_count')!r}",
    )
    require(
        report.get("tei", {}).get("status") == "http_surface_present_unproven",
        "live readiness tei.status is not 'http_surface_present_unproven'",
    )
    supply_chain = report.get("supply_chain", {})
    require(
        supply_chain.get("managed_provider_hits") == [],
        "live readiness supply_chain.managed_provider_hits is not empty",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--packet",
        type=Path,
        default=DEFAULT_PACKET,
        help="path to the gate packet JSON (default: canonical tracked packet)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="project root used to resolve evidence references",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="additionally cross-check the live readiness report",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    packet_path = args.packet if args.packet.is_absolute() else root / args.packet
    try:
        readiness = load_readiness_module()
        data = load_json(packet_path)
        verify_packet(data, root, readiness)
        if args.strict:
            cross_check(root, readiness)
    except VerificationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"OK: {packet_path} satisfies M215/S04 gate packet contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

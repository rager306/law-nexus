#!/usr/bin/env python3
"""Slice battery for M223-d2q075 / S04 — reading order and composite coordinates.

This is a bounded, machine-checked contract for the S04 design pin and its
reconciliation with the S03 corpus baseline.  It asserts, over tracked
repository files only:

(a) the design document
    ``prd/architecture/intermediate-source-reading-order-contract.md`` exists and
    carries the required markers/sections (reading order versus record order,
    composite coordinates, frozen contract inventory, S03 reconciliation);
(b) the five frozen upstream wire contracts pin sha256 values that match the
    machine-readable inventory block in that document ***exactly*** — drift is a
    hard failure demanding an explicit re-pin, never a silent re-pin;
(c) the S03 baseline (``prd/migration/rust-evidence/m223-s03-baseline-run.json``)
    reconciles: ``entries == accepted == 43785``, ``refused == 0``,
    ``incomplete == 0`` and ``r1000_status == "active/unclosed"``;
(d) it emits ``prd/migration/rust-evidence/m223-s04-reading-order-battery.json``
    (schema ``m223-s04-reading-order-battery/v1``) carrying only paths, counters
    and hashes plus ``non_claims`` — never raw decoded text.

Stdlib + hashlib only; no corpus, no binary, no node, no network.  The battery
never mutates a frozen upstream contract: on drift it fails closed.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

# ------------------------------------------------------------------------- #
# Constants / paths
# ------------------------------------------------------------------------- #

ROOT = Path(__file__).resolve().parents[1]

DESIGN_DOC = ROOT / "prd/architecture/intermediate-source-reading-order-contract.md"
BASELINE_PATH = ROOT / "prd/migration/rust-evidence/m223-s03-baseline-run.json"
BATTERY_PATH = ROOT / "prd/migration/rust-evidence/m223-s04-reading-order-battery.json"

BATTERY_SCHEMA = "m223-s04-reading-order-battery/v1"

INVENTORY_BEGIN = "<!-- frozen-contract-inventory:begin -->"
INVENTORY_END = "<!-- frozen-contract-inventory:end -->"

#: Required design-document markers/sections.  Exact single-line markers so a
#: truncated or renamed section fails the battery.
REQUIRED_SECTIONS = (
    "Reading order versus record order",
    "Composite coordinates",
    "S03 reconciliation",
    INVENTORY_BEGIN,
    INVENTORY_END,
)

#: The frozen upstream wire contracts, in the order pinned by the design doc.
FROZEN_CONTRACTS = (
    "prd/architecture/source-jsonl-contract.md",
    "prd/architecture/reader-view-contract.md",
    "prd/architecture/reader-projection-contract.md",
    "prd/architecture/cleaned-projection-contract.md",
    "prd/architecture/npa-analysis-jsonl-contract.md",
)

#: Expected S03 reconciliation facts (acceptance baseline; not a semantic claim).
EXPECTED_ENTRIES = 43785
EXPECTED_ACCEPTED = 43785
EXPECTED_REFUSED = 0
EXPECTED_INCOMPLETE = 0
EXPECTED_R1000_STATUS = "active/unclosed"

S04_NON_CLAIMS = (
    "Reading order and composite coordinates are bounded coordinate surfaces; "
    "R1000 stays active/unclosed.",
    "Reconciling with the S03 baseline is an integrity/counts claim, not a "
    "semantic, authenticity or legal-completeness claim.",
    "This battery reads tracked repository files only; it re-parses no XML and opens no corpus.",
    "The evidence artifact carries only paths, counters and hashes; no raw decoded text.",
)


class ContractViolation(Exception):
    """Raised when a frozen contract drifts or a reconciliation fact mismatches."""


# ------------------------------------------------------------------------- #
# Hashing helpers
# ------------------------------------------------------------------------- #


def sha256_file(path: Path) -> str:
    """Return the bare hex sha256 of a file's bytes."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------------- #
# (a) design document markers
# ------------------------------------------------------------------------- #


def read_design_doc(path: Path = DESIGN_DOC) -> str:
    if not Path(path).is_file():
        raise ContractViolation(f"design document is missing: {path}")
    return Path(path).read_text(encoding="utf-8")


def missing_sections(text: str) -> list[str]:
    return [marker for marker in REQUIRED_SECTIONS if marker not in text]


def check_design_doc(path: Path = DESIGN_DOC) -> dict:
    text = read_design_doc(path)
    missing = missing_sections(text)
    if missing:
        raise ContractViolation(
            "design document is missing required sections/markers: " + ", ".join(missing)
        )
    return {
        "path": _rel(path),
        "sha256": sha256_file(path),
        "sections": list(REQUIRED_SECTIONS),
    }


# ------------------------------------------------------------------------- #
# (b) frozen-contract inventory
# ------------------------------------------------------------------------- #


def parse_frozen_inventory(text: str) -> list[tuple[str, str]]:
    """Parse the machine-readable inventory block.

    Returns ``[(relative_path, pinned_sha256_hex), ...]``.  Fails closed on a
    missing/duplicated marker, a malformed line, a duplicate path, or a count
    that differs from the five pinned contracts.
    """
    if INVENTORY_BEGIN not in text or INVENTORY_END not in text:
        raise ContractViolation("frozen-contract-inventory markers are absent")
    between = text.split(INVENTORY_BEGIN, 1)[1].split(INVENTORY_END, 1)[0]
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in between.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2 or not parts[0].startswith("sha256:"):
            raise ContractViolation(f"malformed frozen-contract inventory line: {line!r}")
        pinned = parts[0][len("sha256:") :]
        if len(pinned) != 64 or any(ch not in "0123456789abcdef" for ch in pinned):
            raise ContractViolation(f"frozen-contract inventory has a non-hex sha256: {line!r}")
        relpath = parts[1]
        if relpath in seen:
            raise ContractViolation(f"frozen-contract inventory repeats a path: {relpath}")
        seen.add(relpath)
        entries.append((relpath, pinned))
    if len(entries) != len(FROZEN_CONTRACTS):
        raise ContractViolation(
            f"frozen-contract inventory holds {len(entries)} entries, expected {len(FROZEN_CONTRACTS)}"
        )
    if [relpath for relpath, _ in entries] != list(FROZEN_CONTRACTS):
        raise ContractViolation(
            "frozen-contract inventory paths do not match the canonical contract set"
        )
    return entries


def check_frozen_contracts(doc_text: str, root: Path = ROOT) -> dict:
    """Compare every pinned sha256 against the on-disk file.  Drift fails closed."""
    inventory = parse_frozen_inventory(doc_text)
    results = []
    drifted = []
    for relpath, pinned in inventory:
        target = Path(root) / relpath
        if not target.is_file():
            raise ContractViolation(f"frozen upstream contract is missing: {relpath}")
        actual = sha256_file(target)
        match = actual == pinned
        if not match:
            drifted.append(relpath)
        results.append(
            {
                "path": relpath,
                "pinned_sha256": pinned,
                "actual_sha256": actual,
                "match": match,
            }
        )
    if drifted:
        raise ContractViolation(
            "frozen upstream contract drift (explicit re-pin required, no silent re-pin): "
            + ", ".join(drifted)
        )
    return {
        "contracts": results,
        "all_match": True,
    }


# ------------------------------------------------------------------------- #
# (c) S03 reconciliation
# ------------------------------------------------------------------------- #


def load_s03_baseline(path: Path = BASELINE_PATH) -> dict:
    if not Path(path).is_file():
        raise ContractViolation(f"S03 baseline is missing: {path}")
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != "m223-s03-baseline-run/v1":
        raise ContractViolation(f"unexpected S03 baseline schema: {payload.get('schema')!r}")
    return payload


def reconcile_s03(payload: dict) -> dict:
    counts = payload.get("counts")
    if not isinstance(counts, dict):
        raise ContractViolation("S03 baseline counts block is absent or malformed")
    facts = {
        "entries": counts.get("entries"),
        "accepted": counts.get("accepted"),
        "refused": counts.get("refused"),
        "incomplete": counts.get("incomplete"),
        "r1000_status": payload.get("r1000_status"),
    }
    expected = {
        "entries": EXPECTED_ENTRIES,
        "accepted": EXPECTED_ACCEPTED,
        "refused": EXPECTED_REFUSED,
        "incomplete": EXPECTED_INCOMPLETE,
        "r1000_status": EXPECTED_R1000_STATUS,
    }
    mismatched = {
        key: (facts[key], expected[key]) for key in expected if facts[key] != expected[key]
    }
    if mismatched:
        detail = ", ".join(
            f"{key}={got!r} (expected {want!r})" for key, (got, want) in mismatched.items()
        )
        raise ContractViolation(f"S03 baseline reconciliation failed: {detail}")
    return facts


# ------------------------------------------------------------------------- #
# (d) evidence artifact emission
# ------------------------------------------------------------------------- #


def build_battery(
    *,
    design: dict,
    frozen: dict,
    s03: dict,
    baseline_path: Path = BASELINE_PATH,
) -> dict:
    return {
        "schema": BATTERY_SCHEMA,
        "design_document": design,
        "frozen_contracts": frozen,
        "s03_baseline_reconciled": s03,
        "s03_baseline": {
            "path": _rel(baseline_path),
            "sha256": sha256_file(baseline_path),
        },
        "non_claims": list(S04_NON_CLAIMS),
    }


def emit_battery(out_path: Path = BATTERY_PATH) -> dict:
    """Build and write the evidence artifact; returns the emitted payload."""
    doc_text = read_design_doc()
    design = check_design_doc()
    frozen = check_frozen_contracts(doc_text)
    s03 = reconcile_s03(load_s03_baseline())
    battery = build_battery(design=design, frozen=frozen, s03=s03)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(battery, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return battery


def _rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


# ------------------------------------------------------------------------- #
# Tests — (a) design document
# ------------------------------------------------------------------------- #


def test_design_doc_exists_and_has_required_sections():
    check_design_doc()


def test_design_doc_truncation_fails(tmp_path):
    truncated = tmp_path / "doc.md"
    truncated.write_text("# title\nno markers here\n", encoding="utf-8")
    with pytest.raises(ContractViolation):
        check_design_doc(truncated)
    missing = missing_sections(truncated.read_text(encoding="utf-8"))
    assert "Composite coordinates" in missing


# ------------------------------------------------------------------------- #
# Tests — (b) frozen-contract inventory / drift
# ------------------------------------------------------------------------- #


def test_frozen_inventory_parses_five_canonical_contracts():
    entries = parse_frozen_inventory(read_design_doc())
    assert [relpath for relpath, _ in entries] == list(FROZEN_CONTRACTS)
    assert all(len(pinned) == 64 for _, pinned in entries)


def test_frozen_contracts_match_on_disk():
    frozen = check_frozen_contracts(read_design_doc())
    assert frozen["all_match"] is True
    assert len(frozen["contracts"]) == 5
    assert all(entry["match"] for entry in frozen["contracts"])


def test_frozen_contract_drift_fails_closed(tmp_path):
    root = tmp_path / "root"
    for relpath in FROZEN_CONTRACTS:
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"content of {relpath}", encoding="utf-8")

    good_lines = []
    for relpath in FROZEN_CONTRACTS:
        good_lines.append(f"sha256:{sha256_file(root / relpath)} {relpath}")
    good_doc = INVENTORY_BEGIN + "\n" + "\n".join(good_lines) + "\n" + INVENTORY_END
    assert check_frozen_contracts(good_doc, root=root)["all_match"] is True

    # tamper one contract on disk -> drift must fail with the explicit path
    (root / FROZEN_CONTRACTS[2]).write_text("tampered", encoding="utf-8")
    with pytest.raises(ContractViolation) as excinfo:
        check_frozen_contracts(good_doc, root=root)
    assert FROZEN_CONTRACTS[2] in str(excinfo.value)


def test_malformed_inventory_fails(tmp_path):
    with pytest.raises(ContractViolation):
        parse_frozen_inventory("no markers at all")
    with pytest.raises(ContractViolation):
        parse_frozen_inventory(INVENTORY_BEGIN + "\nnonsense line\n" + INVENTORY_END)


# ------------------------------------------------------------------------- #
# Tests — (c) S03 reconciliation
# ------------------------------------------------------------------------- #


def test_s03_baseline_reconciles():
    facts = reconcile_s03(load_s03_baseline())
    assert facts == {
        "entries": 43785,
        "accepted": 43785,
        "refused": 0,
        "incomplete": 0,
        "r1000_status": "active/unclosed",
    }


def test_s03_reconciliation_rejects_drift():
    good = load_s03_baseline()
    tampered = json.loads(json.dumps(good))
    tampered["counts"]["accepted"] = 43784
    with pytest.raises(ContractViolation):
        reconcile_s03(tampered)

    tampered2 = json.loads(json.dumps(good))
    tampered2["r1000_status"] = "closed"
    with pytest.raises(ContractViolation):
        reconcile_s03(tampered2)


# ------------------------------------------------------------------------- #
# Tests — (d) evidence artifact
# ------------------------------------------------------------------------- #


def test_battery_emitted_with_schema_and_no_raw_text(tmp_path):
    out = tmp_path / "battery.json"
    battery = emit_battery(out)
    assert out.is_file()
    assert battery["schema"] == BATTERY_SCHEMA
    assert battery["frozen_contracts"]["all_match"] is True
    assert battery["s03_baseline_reconciled"]["accepted"] == 43785
    assert battery["s03_baseline_reconciled"]["r1000_status"] == "active/unclosed"
    assert battery["non_claims"]

    serialized = out.read_text(encoding="utf-8")
    # redaction: only paths/counters/hashes/statuses — no fixture tokens, no tab
    for forbidden in ("\t", "<w:", "Beta", "PAGE", "Zeta", "NBSP"):
        assert forbidden not in serialized
    # the design doc sha256 and the five frozen hashes are all 64-hex
    assert len(battery["design_document"]["sha256"]) == 64
    for entry in battery["frozen_contracts"]["contracts"]:
        assert len(entry["pinned_sha256"]) == 64
        assert len(entry["actual_sha256"]) == 64


def test_battery_deterministic(tmp_path):
    first = emit_battery(tmp_path / "a.json")
    second = emit_battery(tmp_path / "b.json")
    assert first == second


def test_battery_emitted_at_tracked_path():
    """The slice battery emits the evidence artifact at its tracked path."""
    battery = emit_battery(BATTERY_PATH)
    assert BATTERY_PATH.is_file()
    on_disk = json.loads(BATTERY_PATH.read_text(encoding="utf-8"))
    assert on_disk == battery
    assert on_disk["schema"] == BATTERY_SCHEMA


# ------------------------------------------------------------------------- #
# CLI
# ------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("emit", "check"):
        sys.stderr.write(f"unknown command: {argv[0]!r}\n")
        return 2
    try:
        battery = emit_battery()
    except ContractViolation as exc:
        sys.stderr.write(f"s04 contract violation: {exc}\n")
        return 1
    summary = {
        "schema": battery["schema"],
        "frozen_contracts_all_match": battery["frozen_contracts"]["all_match"],
        "s03_entries": battery["s03_baseline_reconciled"]["entries"],
        "s03_accepted": battery["s03_baseline_reconciled"]["accepted"],
        "r1000_status": battery["s03_baseline_reconciled"]["r1000_status"],
        "out": _rel(BATTERY_PATH),
    }
    sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

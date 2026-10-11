#!/usr/bin/env python3
"""S07 slice battery: fail-closed machine proof of the consumer acceptance slice.

Validates the slice contract of M223-d2q075 / S07 end to end (see
``prd/architecture/intermediate-source-consumer-acceptance-contract.md``,
section 12):

(a) the design contract exists and carries the required sections/markers
    ("Purpose and non-claims", "Composite provenance", "Graph document
    identity", "Consumers without XML re-parse", "Independent oracle / holdout",
    "Whole-corpus acceptance boundary", "Additive-only", "S03 reconciliation",
    "Slice boundaries", "Threat surface", "Requirement impact", "Verification
    surface", the ``frozen-contract-inventory`` / ``immutability-pins`` /
    ``consumer-model`` blocks, ``active/unclosed``, ``43785``,
    ``reader_tokenizer`` and ``npa_graph_projection``);
(b) the five frozen upstream wire contracts match the sha256 inventory pinned in
    the design contract exactly — drift is an explicit failure, never a silent
    re-pin;
(c) the S03 baseline run reconciles: entries = accepted = 43785, refused = 0,
    incomplete = 0, R1000 stays active/unclosed, status complete;
(d) the S07 evidence artifacts (the whole-corpus census / corpus-run report, the
    receipt ledger, the resume proof and the repeat-import proof) carry their
    schema-v1 identities, are redacted, and satisfy the consumer accounting
    invariants (``terminal = accepted + refused`` and
    ``entries = terminal + remaining``; a partial run is never reported as full);
(e) immutability: the six section-2 source files and the two frozen
    ``prd/architecture/*.jsonl`` artifacts match the ``immutability-pins`` block;
(f) the machine-readable ``consumer-model`` block is total over the closed
    vocabulary and matches the ``reader_tokenizer`` / ``npa_graph_projection``
    source declarations (and their own embedded model blocks) — model drift fails
    closed;
(g) it emits ``prd/migration/rust-evidence/m223-s07-acceptance-battery.json``
    (schema ``m223-s07-acceptance-battery/v1``) carrying only paths, counters,
    hashes and non-claims — never decoded text.

The artifact is written only when every check above passes, so its presence
always means a fully green battery run.  Non-claims: this battery is not an
R1000 closure, not semantic or legal interpretation, not normalization, not
authenticity evidence, and not a physical-pagination surface; whole-corpus
materialization is S05-S07 evidence, not S07 closure.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

CONTRACT_RELPATH = "prd/architecture/intermediate-source-consumer-acceptance-contract.md"
CONTRACT_PATH = ROOT / CONTRACT_RELPATH
BASELINE_RELPATH = "prd/migration/rust-evidence/m223-s03-baseline-run.json"
BASELINE_PATH = ROOT / BASELINE_RELPATH
RUN_RELPATH = "prd/migration/rust-evidence/m223-s07-corpus-run.json"
RUN_PATH = ROOT / RUN_RELPATH
RECEIPTS_RELPATH = "prd/migration/rust-evidence/m223-s07-corpus-receipts.jsonl"
RECEIPTS_PATH = ROOT / RECEIPTS_RELPATH
RESUME_RELPATH = "prd/migration/rust-evidence/m223-s07-resume-proof.json"
RESUME_PATH = ROOT / RESUME_RELPATH
REPEAT_RELPATH = "prd/migration/rust-evidence/m223-s07-repeat-import-proof.json"
REPEAT_PATH = ROOT / REPEAT_RELPATH
BATTERY_RELPATH = "prd/migration/rust-evidence/m223-s07-acceptance-battery.json"
BATTERY_PATH = ROOT / BATTERY_RELPATH
TOKENIZER_SOURCE_RELPATH = "crates/ln-decode/src/reader_tokenizer.rs"
TOKENIZER_SOURCE_PATH = ROOT / TOKENIZER_SOURCE_RELPATH
GRAPH_SOURCE_RELPATH = "crates/ln-decode/src/npa_graph_projection.rs"
GRAPH_SOURCE_PATH = ROOT / GRAPH_SOURCE_RELPATH
HARNESS_RELPATH = "scripts/m223_s07_corpus_run.py"
HARNESS_PATH = ROOT / HARNESS_RELPATH

SCHEMA = "m223-s07-acceptance-battery/v1"
VERSION = 1
BASELINE_SCHEMA = "m223-s03-baseline-run/v1"
RUN_SCHEMA = "m223-s07-corpus-run/v1"
RECEIPT_SCHEMA = "m223-s07-consumer-receipt/v1"
RESUME_SCHEMA = "m223-s07-resume-proof/v1"
REPEAT_SCHEMA = "m223-s07-repeat-import-proof/v1"
COUNTS_SCHEMA = "m223-s07-consumer-counts/v1"

INVENTORY_BEGIN = "<!-- frozen-contract-inventory:begin -->"
INVENTORY_END = "<!-- frozen-contract-inventory:end -->"
PINS_BEGIN = "<!-- immutability-pins:begin -->"
PINS_END = "<!-- immutability-pins:end -->"
MODEL_BEGIN = "<!-- consumer-model:begin -->"
MODEL_END = "<!-- consumer-model:end -->"
TOKENIZER_MODEL_BEGIN = "<!-- consumer-model:reader_tokenizer:begin -->"
TOKENIZER_MODEL_END = "<!-- consumer-model:reader_tokenizer:end -->"
GRAPH_MODEL_BEGIN = "<!-- consumer-model:npa_graph_projection:begin -->"
GRAPH_MODEL_END = "<!-- consumer-model:npa_graph_projection:end -->"

REQUIRED_MARKERS = (
    "Purpose and non-claims",
    "Composite provenance",
    "Graph document identity",
    "Consumers without XML re-parse",
    "Independent oracle / holdout",
    "Whole-corpus acceptance boundary",
    "Additive-only",
    "S03 reconciliation",
    "Slice boundaries",
    "Threat surface",
    "Requirement impact",
    "Verification surface",
    INVENTORY_BEGIN,
    INVENTORY_END,
    PINS_BEGIN,
    PINS_END,
    MODEL_BEGIN,
    MODEL_END,
    "active/unclosed",
    "43785",
    "reader_tokenizer",
    "npa_graph_projection",
)

FROZEN_CONTRACT_RELPATHS: tuple[str, ...] = (
    "prd/architecture/source-jsonl-contract.md",
    "prd/architecture/reader-view-contract.md",
    "prd/architecture/reader-projection-contract.md",
    "prd/architecture/cleaned-projection-contract.md",
    "prd/architecture/npa-analysis-jsonl-contract.md",
)

#: The six section-2 acceptance-contract source files frozen since M222.
FROZEN_SECTION2_RELPATHS: tuple[str, ...] = (
    "crates/ln-decode/src/reader_projection.rs",
    "crates/ln-decode/src/reader_verifier.rs",
    "crates/ln-decode/src/npa_analysis_wire.rs",
    "crates/ln-decode/tests/reader_tail_semantics.rs",
    "crates/ln-decode/tests/npa_analysis_strict_admission.rs",
    "crates/ln-decode/tests/m222_f07_audit.rs",
)

#: The frozen ``prd/architecture/*.jsonl`` tracked artifacts (never modified).
FROZEN_ARCHITECTURE_JSONL_RELPATHS: tuple[str, ...] = (
    "prd/architecture/architecture_items.jsonl",
    "prd/architecture/architecture_edges.jsonl",
)

EXPECTED_ENTRIES = 43785
EXPECTED_ACCEPTED = 43785
EXPECTED_REFUSED = 0
EXPECTED_INCOMPLETE = 0
EXPECTED_R1000_STATUS = "active/unclosed"

#: The closed consumer model pinned by the design contract's machine-readable
#: block.  Order is the block order; the block is split into the tokenizer
#: portion (provenance / derived kinds) and the graph portion (identity / nodes
#: / edges / refusals), each of which must equal the module's own embedded block.
EXPECTED_CONSUMER_MODEL: tuple[str, ...] = (
    "provenance:source_fragment fields:document_identity,element_ref,slot,fragment_ref,span,source_pos",
    "provenance:derived_control fields:document_identity,element_ref,source_pos,derived_kind,rule_profile",
    "provenance:composite_range units:source_subspan,derived_control",
    "derived_kind:tab",
    "derived_kind:line_break",
    "derived_kind:page_break",
    "graph_identity:SourceIdentity",
    "graph_identity:DocumentVersionRef",
    "graph_identity:composite_source_identity_xor_document_version_ref",
    "graph_node:member",
    "graph_node:fragment",
    "graph_node:classification",
    "graph_edge:relation",
    "graph_refusal:cross_document",
    "graph_refusal:source_identity_mismatch",
    "graph_refusal:document_version_mismatch",
    "graph_refusal:unknown_fragment",
)

#: The provenance forms and derived kinds are the tokenizer's model; the rest is
#: the graph projection's.
TOKENIZER_MODEL_PREFIXES = ("provenance:", "derived_kind:")
GRAPH_MODEL_PREFIXES = ("graph_identity:", "graph_node:", "graph_edge:", "graph_refusal:")

EXPECTED_PROVENANCE_FORMS = ("source_fragment", "derived_control", "composite_range")
EXPECTED_DERIVED_KINDS = ("tab", "line_break", "page_break")
EXPECTED_GRAPH_IDENTITY = (
    "SourceIdentity",
    "DocumentVersionRef",
    "composite_source_identity_xor_document_version_ref",
)
EXPECTED_GRAPH_NODES = ("member", "fragment", "classification")
EXPECTED_GRAPH_EDGES = ("relation",)
EXPECTED_GRAPH_REFUSALS = (
    "cross_document",
    "source_identity_mismatch",
    "document_version_mismatch",
    "unknown_fragment",
)

BATTERY_NON_CLAIMS: tuple[str, ...] = (
    "not_r1000_closure",
    "not_semantic_or_legal_interpretation",
    "not_normalization",
    "not_authenticity_evidence",
    "not_physical_pagination",
    "not_an_unparking_of_parked_downstream",
    "additive_only_over_five_frozen_wire_contracts",
    "consumer_outputs_are_counts_paths_hashes_only_no_decoded_text",
    "a_partial_corpus_run_is_never_reported_as_full",
)

INVENTORY_LINE_RE = re.compile(r"^sha256:([0-9a-f]{64})\s+(\S+)$")
STR_ARRAY_RE = re.compile(r'"([^"]*)"')
VARIANT_RE = re.compile(r"(\w+)::(\w+)")
PROVENANCE_ARM_RE = re.compile(r'ProvenanceForm::(\w+)\s*=>\s*"([a-z_]+)"')


def load_harness():
    """Load the T04 harness so the redaction guard cannot drift."""
    spec = importlib.util.spec_from_file_location("m223_s07_corpus_run", HARNESS_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


harness = load_harness()

# ----------------------------------------------------------------- helpers #


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def read_text_or_fail(path: Path, what: str) -> str:
    if not path.is_file():
        pytest.fail(f"battery: {what} is missing: {path}", pytrace=False)
    return path.read_text(encoding="utf-8")


def read_json_or_fail(path: Path, what: str) -> dict[str, Any]:
    if not path.is_file():
        pytest.fail(f"battery: {what} is missing: {path}", pytrace=False)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        pytest.fail(f"battery: {what} is not valid JSON: {error}", pytrace=False)


def _strip_rust_doc(line: str) -> str:
    """Normalize one line of Rust source by dropping a doc-comment prefix."""
    stripped = line.strip()
    for prefix in ("//!", "///"):
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    return stripped


def _block_lines(
    text: str,
    begin: str,
    end: str,
    what: str,
    normalize: Callable[[str], str] = str.strip,
) -> list[str]:
    lines = text.splitlines()
    try:
        start = next(i for i, raw in enumerate(lines) if normalize(raw) == begin)
        stop = next(
            i for i, raw in enumerate(lines[start + 1 :], start=start + 1) if normalize(raw) == end
        )
    except StopIteration:
        pytest.fail(f"battery: {what} markers missing", pytrace=False)
    return [normalize(raw) for raw in lines[start + 1 : stop] if normalize(raw)]


# ------------------------------------------------------- parsing, fail-closed #


def parse_inventory(contract_text: str) -> dict[str, str]:
    """Parse the frozen-contract sha256 inventory block, fail-closed."""
    inventory: dict[str, str] = {}
    for stripped in _block_lines(
        contract_text, INVENTORY_BEGIN, INVENTORY_END, "frozen-contract-inventory"
    ):
        match = INVENTORY_LINE_RE.match(stripped)
        assert match is not None, f"battery: malformed inventory line {stripped!r}"
        sha256, relpath = match.groups()
        assert relpath not in inventory, f"battery: duplicate inventory entry for {relpath}"
        inventory[relpath] = sha256
    assert set(inventory) == set(FROZEN_CONTRACT_RELPATHS), (
        "battery: the inventory must list exactly the five frozen upstream contracts, "
        f"got {sorted(inventory)}"
    )
    return inventory


def parse_immutability_pins(contract_text: str) -> dict[str, str]:
    """Parse the immutability-pins block (six section-2 files + two jsonl)."""
    pins: dict[str, str] = {}
    for stripped in _block_lines(contract_text, PINS_BEGIN, PINS_END, "immutability-pins"):
        match = INVENTORY_LINE_RE.match(stripped)
        assert match is not None, f"battery: malformed immutability pin {stripped!r}"
        sha256, relpath = match.groups()
        assert relpath not in pins, f"battery: duplicate immutability pin for {relpath}"
        pins[relpath] = sha256
    expected = set(FROZEN_SECTION2_RELPATHS) | set(FROZEN_ARCHITECTURE_JSONL_RELPATHS)
    assert set(pins) == expected, (
        "battery: the immutability-pins block must list the six section-2 files and "
        f"the two frozen architecture jsonl artifacts, got {sorted(pins)}"
    )
    return pins


def parse_consumer_model_block(contract_text: str) -> list[str]:
    """Parse the design contract's consumer-model block, fail-closed."""
    lines = _block_lines(contract_text, MODEL_BEGIN, MODEL_END, "consumer-model")
    allowed = set(TOKENIZER_MODEL_PREFIXES) | set(GRAPH_MODEL_PREFIXES)
    for line in lines:
        head, _, _ = line.partition(":")
        assert f"{head}:" in allowed, f"battery: unknown consumer-model line {line!r}"
    assert tuple(lines) == EXPECTED_CONSUMER_MODEL, f"battery: consumer-model block drift: {lines}"
    return lines


def parse_rust_model_block(source_text: str, begin: str, end: str, what: str) -> list[str]:
    """Parse one module's embedded consumer-model block from its doc comment."""
    return _block_lines(source_text, begin, end, what, normalize=_strip_rust_doc)


def parse_str_array(source_text: str, const_name: str) -> list[str]:
    """Extract the quoted strings of a ``const NAME: [&str; N] = [ ... ];`` array."""
    header = f"const {const_name}"
    start = source_text.find(header)
    assert start != -1, f"battery: source is missing `{header}`"
    eq = source_text.find("= [", start)
    assert eq != -1, f"battery: `{const_name}` is not an array literal"
    end = source_text.find("];", eq)
    assert end != -1, f"battery: could not find the end of `{const_name}`"
    return STR_ARRAY_RE.findall(source_text[eq:end])


def parse_variant_array(source_text: str, const_name: str) -> list[str]:
    """Extract the variant names of a ``const NAME: [Enum; N] = [Enum::X, ...];``."""
    header = f"const {const_name}"
    start = source_text.find(header)
    assert start != -1, f"battery: source is missing `{header}`"
    eq = source_text.find("= [", start)
    assert eq != -1, f"battery: `{const_name}` is not an array literal"
    end = source_text.find("];", eq)
    assert end != -1, f"battery: could not find the end of `{const_name}`"
    return [variant for _, variant in VARIANT_RE.findall(source_text[eq:end])]


def camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def parse_provenance_forms(source_text: str) -> list[str]:
    """Parse the ``ProvenanceForm::X => "y"`` arms into their closed string forms."""
    forms = [form for _, form in PROVENANCE_ARM_RE.findall(source_text)]
    assert forms, "battery: reader_tokenizer.rs has no ProvenanceForm::as_str arms"
    return forms


def parse_tokenizer_model(source_text: str) -> dict[str, list[str]]:
    """Parse the closed tokenizer vocabulary from reader_tokenizer.rs."""
    forms = parse_provenance_forms(source_text)
    derived = [
        camel_to_snake(variant)
        for variant in parse_variant_array(source_text, "READER_TOKENIZER_DERIVED_KINDS")
    ]
    return {"provenance_forms": forms, "derived_kinds": derived}


def parse_graph_model(source_text: str) -> dict[str, list[str]]:
    """Parse the closed graph vocabulary from npa_graph_projection.rs."""
    identity = parse_str_array(source_text, "NPA_GRAPH_IDENTITY_COMPONENTS")
    nodes = [
        camel_to_snake(variant)
        for variant in parse_variant_array(source_text, "NPA_GRAPH_NODE_KINDS")
    ]
    edges = parse_str_array(source_text, "NPA_GRAPH_EDGE_KINDS")
    refusals = parse_str_array(source_text, "NPA_GRAPH_REFUSALS")
    return {"identity": identity, "nodes": nodes, "edges": edges, "refusals": refusals}


def model_lines_by_prefix(lines: list[str], prefixes: tuple[str, ...]) -> list[str]:
    return [line for line in lines if line.partition(":")[0] + ":" in prefixes]


def model_values(lines: list[str], prefix: str) -> list[str]:
    head = f"{prefix}:"
    return [line[len(head) :].split(" ", 1)[0] for line in lines if line.startswith(head)]


# ---------------------------------------------------------------- redaction #


def redaction_check(value: Any) -> None:
    """Fail closed before writing: reuse the T04 harness redaction guard."""
    try:
        harness.assert_no_raw_text(value)
    except harness.HarnessError as error:
        pytest.fail(f"battery: artifact failed the redaction guard: {error}", pytrace=False)


# ----------------------------------------------------- accounting invariants #


def assert_counts_accounting(counts: dict[str, Any]) -> None:
    """The consumer accounting invariants that must hold for any corpus census.

    ``terminal = accepted + refused`` and ``entries = terminal + remaining``;
    every count is a non-negative integer.  A partial run is honest about its
    remaining tail and is never reported as full.
    """
    required = ("entries", "accepted", "refused", "incomplete", "terminal", "remaining")
    for key in required:
        assert key in counts, f"battery: counts is missing {key!r}"
        assert isinstance(counts[key], int) and counts[key] >= 0, (
            f"battery: counts.{key} must be a non-negative integer, got {counts[key]!r}"
        )
    assert counts["terminal"] == counts["accepted"] + counts["refused"], (
        "battery: terminal must equal accepted + refused "
        f"({counts['terminal']} != {counts['accepted']} + {counts['refused']})"
    )
    assert counts["entries"] == counts["terminal"] + counts["remaining"], (
        "battery: entries must equal terminal + remaining "
        f"({counts['entries']} != {counts['terminal']} + {counts['remaining']})"
    )


def assert_s03_reconciled(reconciled: dict[str, Any]) -> None:
    """The corpus census must reconcile to the S03 baseline (43785/0/0)."""
    for key, expected in (
        ("entries", EXPECTED_ENTRIES),
        ("accepted", EXPECTED_ACCEPTED),
        ("refused", EXPECTED_REFUSED),
        ("incomplete", EXPECTED_INCOMPLETE),
    ):
        assert reconciled.get(key) == expected, (
            f"battery: S03 reconciliation {key} must be {expected}, got {reconciled.get(key)!r}"
        )
    assert reconciled.get("r1000_status") == EXPECTED_R1000_STATUS, (
        f"battery: R1000 must stay {EXPECTED_R1000_STATUS}, got {reconciled.get('r1000_status')!r}"
    )


def latest_by_path(receipts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        path = receipt.get("relative_path")
        assert isinstance(path, str) and path, "battery: receipt has no relative_path"
        latest[path] = receipt
    return latest


# ------------------------------------------------------------------ battery #


def run_battery() -> dict[str, Any]:
    """Run every battery check; raise before emitting anything on failure."""
    contract_text = read_text_or_fail(CONTRACT_PATH, "design contract")
    baseline = read_json_or_fail(BASELINE_PATH, "S03 baseline run")
    run_report = read_json_or_fail(RUN_PATH, "corpus-run report")
    resume_proof = read_json_or_fail(RESUME_PATH, "resume proof")
    repeat_proof = read_json_or_fail(REPEAT_PATH, "repeat-import proof")
    tokenizer_source = read_text_or_fail(TOKENIZER_SOURCE_PATH, "reader_tokenizer source")
    graph_source = read_text_or_fail(GRAPH_SOURCE_PATH, "npa_graph_projection source")
    contract_sha256 = sha256_of_file(CONTRACT_PATH)

    # (a) required sections and markers.
    missing = [marker for marker in REQUIRED_MARKERS if marker not in contract_text]
    assert not missing, f"battery: design contract is missing required markers: {missing}"

    # (b) frozen-contract inventory versus the tracked files: drift is an
    # explicit failure, never a silent re-pin.
    inventory = parse_inventory(contract_text)
    frozen: list[dict[str, Any]] = []
    for relpath in FROZEN_CONTRACT_RELPATHS:
        path = ROOT / relpath
        assert path.is_file(), f"battery: frozen contract is missing: {relpath}"
        frozen.append({"path": relpath, "sha256": sha256_of_file(path)})
    for entry in frozen:
        entry["matches_inventory"] = entry["sha256"] == f"sha256:{inventory[entry['path']]}"
    drifted = [
        f"{entry['path']} inventory sha256:{inventory[entry['path']]} != actual {entry['sha256']}"
        for entry in frozen
        if not entry["matches_inventory"]
    ]
    assert not drifted, (
        "battery: frozen upstream contract drift (an explicit re-pin is required, "
        "never a silent one): " + "; ".join(drifted)
    )

    # (c) S03 baseline reconciliation.
    assert baseline.get("schema") == BASELINE_SCHEMA, (
        f"battery: unexpected baseline schema {baseline.get('schema')!r}"
    )
    baseline_counts = baseline.get("counts")
    assert isinstance(baseline_counts, dict), "battery: baseline carries no counts object"
    for key, expected in (
        ("entries", EXPECTED_ENTRIES),
        ("accepted", EXPECTED_ACCEPTED),
        ("refused", EXPECTED_REFUSED),
        ("incomplete", EXPECTED_INCOMPLETE),
    ):
        assert baseline_counts.get(key) == expected, (
            f"battery: S03 baseline counts.{key} must be {expected}, "
            f"got {baseline_counts.get(key)!r}"
        )
    assert baseline.get("r1000_status") == EXPECTED_R1000_STATUS, (
        f"battery: R1000 must stay {EXPECTED_R1000_STATUS}, got {baseline.get('r1000_status')!r}"
    )
    assert baseline.get("status") == "complete", (
        f"battery: the baseline run must be complete, got {baseline.get('status')!r}"
    )

    # (d) the S07 evidence artifacts: schema v1, redaction, accounting.
    # The whole-corpus census is the corpus-run report (the T04/T05 harness's
    # aggregate counts document over the pinned S02 manifest).
    assert run_report.get("schema") == RUN_SCHEMA, (
        f"battery: unexpected corpus-run schema {run_report.get('schema')!r}"
    )
    run_counts = run_report.get("counts")
    assert isinstance(run_counts, dict), "battery: corpus-run report carries no counts object"
    assert_counts_accounting(run_counts)
    assert isinstance(run_report.get("partial_is_not_full"), bool), (
        "battery: the corpus-run report must carry a boolean partial_is_not_full"
    )
    assert run_report.get("partial_is_not_full") is True, (
        "battery: a partial corpus run must be reported as partial (partial_is_not_full=true)"
    )
    if run_counts["remaining"] > 0:
        assert run_report.get("status") != "complete", (
            "battery: a run with a remaining tail must not claim status=complete"
        )
    reconciled = run_report.get("s03_baseline_reconciled")
    assert isinstance(reconciled, dict), (
        "battery: the corpus-run report must carry s03_baseline_reconciled"
    )
    assert_s03_reconciled(reconciled)
    assert run_report.get("r1000_status") == EXPECTED_R1000_STATUS, (
        f"battery: corpus-run R1000 must stay {EXPECTED_R1000_STATUS}, "
        f"got {run_report.get('r1000_status')!r}"
    )
    redaction_check(run_report)

    # The receipt ledger: every line is a schema-v1 receipt and is redacted.
    receipts_text = read_text_or_fail(RECEIPTS_PATH, "receipt ledger")
    receipts: list[dict[str, Any]] = []
    for index, raw in enumerate(receipts_text.splitlines()):
        if not raw.strip():
            continue
        try:
            receipt = json.loads(raw)
        except json.JSONDecodeError as error:
            pytest.fail(f"battery: receipt line {index} is not JSON: {error}", pytrace=False)
        assert receipt.get("schema") == RECEIPT_SCHEMA, (
            f"battery: receipt line {index} has schema {receipt.get('schema')!r}"
        )
        assert receipt.get("outcome") in ("accepted", "refused", "incomplete"), (
            f"battery: receipt line {index} has an unknown outcome {receipt.get('outcome')!r}"
        )
        receipts.append(receipt)
    assert receipts, "battery: the receipt ledger is empty"
    redaction_check(receipts)
    terminal_paths = sum(
        1
        for receipt in latest_by_path(receipts).values()
        if receipt.get("outcome") in ("accepted", "refused")
    )
    assert terminal_paths == run_counts["terminal"], (
        "battery: the ledger's terminal-path count must match the report terminal count "
        f"({terminal_paths} != {run_counts['terminal']})"
    )

    # The resume proof and the repeat-import proof.
    assert resume_proof.get("schema") == RESUME_SCHEMA, (
        f"battery: unexpected resume-proof schema {resume_proof.get('schema')!r}"
    )
    assert resume_proof.get("ok") is True, "battery: the resume proof must record ok=true"
    assert resume_proof.get("r1000_status") == EXPECTED_R1000_STATUS, (
        f"battery: resume-proof R1000 must stay {EXPECTED_R1000_STATUS}"
    )
    redaction_check(resume_proof)

    assert repeat_proof.get("schema") == REPEAT_SCHEMA, (
        f"battery: unexpected repeat-import schema {repeat_proof.get('schema')!r}"
    )
    assert repeat_proof.get("ok") is True, "battery: the repeat-import proof must record ok=true"
    assert repeat_proof.get("counts_byte_identical") is True, (
        "battery: the repeat import must be a byte-identical idempotent no-op"
    )
    assert repeat_proof.get("r1000_status") == EXPECTED_R1000_STATUS, (
        f"battery: repeat-import R1000 must stay {EXPECTED_R1000_STATUS}"
    )
    redaction_check(repeat_proof)

    # (e) immutability of the six section-2 files and the frozen architecture jsonl.
    pins = parse_immutability_pins(contract_text)
    pinned_entries: list[dict[str, Any]] = []
    pin_drift: list[str] = []
    for relpath, pinned in pins.items():
        path = ROOT / relpath
        assert path.is_file(), f"battery: pinned file is missing: {relpath}"
        actual = sha256_of_file(path)
        matches = actual == f"sha256:{pinned}"
        if not matches:
            pin_drift.append(f"{relpath} pinned sha256:{pinned} != actual {actual}")
        pinned_entries.append({"path": relpath, "sha256": actual, "matches_pin": matches})
    assert not pin_drift, (
        "battery: immutability drift on a frozen section-2 file or architecture "
        "jsonl (never a silent re-pin): " + "; ".join(pin_drift)
    )
    section2_entries = [
        entry for entry in pinned_entries if entry["path"] in FROZEN_SECTION2_RELPATHS
    ]
    architecture_entries = [
        entry for entry in pinned_entries if entry["path"] in FROZEN_ARCHITECTURE_JSONL_RELPATHS
    ]

    # (f) consumer-model block versus the module source declarations.
    model_lines = parse_consumer_model_block(contract_text)
    tokenizer_block = parse_rust_model_block(
        tokenizer_source,
        TOKENIZER_MODEL_BEGIN,
        TOKENIZER_MODEL_END,
        "reader_tokenizer consumer-model",
    )
    graph_block = parse_rust_model_block(
        graph_source,
        GRAPH_MODEL_BEGIN,
        GRAPH_MODEL_END,
        "npa_graph_projection consumer-model",
    )
    assert tuple(tokenizer_block) == tuple(
        model_lines_by_prefix(model_lines, TOKENIZER_MODEL_PREFIXES)
    ), "battery: the tokenizer's embedded model block drifts from the design contract"
    assert tuple(graph_block) == tuple(model_lines_by_prefix(model_lines, GRAPH_MODEL_PREFIXES)), (
        "battery: the graph's embedded model block drifts from the design contract"
    )

    tokenizer_model = parse_tokenizer_model(tokenizer_source)
    assert tuple(tokenizer_model["provenance_forms"]) == EXPECTED_PROVENANCE_FORMS, (
        "battery: provenance forms drift from reader_tokenizer.rs: "
        f"{tokenizer_model['provenance_forms']}"
    )
    assert tuple(tokenizer_model["derived_kinds"]) == EXPECTED_DERIVED_KINDS, (
        f"battery: derived kinds drift from reader_tokenizer.rs: {tokenizer_model['derived_kinds']}"
    )
    assert tuple(model_values(model_lines, "provenance")) == EXPECTED_PROVENANCE_FORMS
    assert tuple(model_values(model_lines, "derived_kind")) == EXPECTED_DERIVED_KINDS

    graph_model = parse_graph_model(graph_source)
    assert tuple(graph_model["identity"]) == EXPECTED_GRAPH_IDENTITY, (
        f"battery: graph identity components drift: {graph_model['identity']}"
    )
    assert tuple(graph_model["nodes"]) == EXPECTED_GRAPH_NODES, (
        f"battery: graph node kinds drift: {graph_model['nodes']}"
    )
    assert tuple(graph_model["edges"]) == EXPECTED_GRAPH_EDGES, (
        f"battery: graph edge kinds drift: {graph_model['edges']}"
    )
    assert tuple(graph_model["refusals"]) == EXPECTED_GRAPH_REFUSALS, (
        f"battery: graph refusals drift: {graph_model['refusals']}"
    )
    assert tuple(model_values(model_lines, "graph_identity")) == EXPECTED_GRAPH_IDENTITY
    assert tuple(model_values(model_lines, "graph_node")) == EXPECTED_GRAPH_NODES
    assert tuple(model_values(model_lines, "graph_edge")) == EXPECTED_GRAPH_EDGES
    assert tuple(model_values(model_lines, "graph_refusal")) == EXPECTED_GRAPH_REFUSALS

    return {
        "contract_sha256": contract_sha256,
        "frozen_contracts": frozen,
        "section2_entries": section2_entries,
        "architecture_entries": architecture_entries,
        "baseline": baseline,
        "run_report": run_report,
        "receipt_lines": len(receipts),
        "receipt_terminal_paths": terminal_paths,
        "resume_proof": resume_proof,
        "repeat_proof": repeat_proof,
        "consumer_model": {
            "provenance_forms": list(tokenizer_model["provenance_forms"]),
            "derived_kinds": list(tokenizer_model["derived_kinds"]),
            "graph_identity": list(graph_model["identity"]),
            "graph_nodes": list(graph_model["nodes"]),
            "graph_edges": list(graph_model["edges"]),
            "graph_refusals": list(graph_model["refusals"]),
        },
    }


def build_artifact(analysis: dict[str, Any]) -> dict[str, Any]:
    baseline = analysis["baseline"]
    counts = baseline["counts"]
    run_report = analysis["run_report"]
    run_counts = run_report["counts"]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "non_claims": list(BATTERY_NON_CLAIMS),
        "contract_path": CONTRACT_RELPATH,
        "contract_sha256": analysis["contract_sha256"],
        "frozen_contracts": analysis["frozen_contracts"],
        "frozen_contracts_match_inventory": True,
        "frozen_section2_files": analysis["section2_entries"],
        "frozen_architecture_jsonl": analysis["architecture_entries"],
        "immutability_pins_match": True,
        "consumer_model": analysis["consumer_model"],
        "consumer_model_block_total": True,
        "consumer_model_matches_source": True,
        "reader_tokenizer_source_path": TOKENIZER_SOURCE_RELPATH,
        "npa_graph_projection_source_path": GRAPH_SOURCE_RELPATH,
        "s03_baseline_path": BASELINE_RELPATH,
        "s03_baseline_reconciled": {
            "entries": counts["entries"],
            "accepted": counts["accepted"],
            "refused": counts["refused"],
            "incomplete": counts["incomplete"],
            "r1000_status": baseline["r1000_status"],
        },
        "census_path": RUN_RELPATH,
        "census_schema": run_report["schema"],
        "census_status": run_report["status"],
        "census_partial_is_not_full": run_report["partial_is_not_full"],
        "census_counts": {
            "entries": run_counts["entries"],
            "terminal": run_counts["terminal"],
            "accepted": run_counts["accepted"],
            "refused": run_counts["refused"],
            "incomplete": run_counts["incomplete"],
            "remaining": run_counts["remaining"],
        },
        "census_accounting_ok": True,
        "census_s03_reconciled": True,
        "census_redaction_ok": True,
        "receipts_path": RECEIPTS_RELPATH,
        "receipts_schema": RECEIPT_SCHEMA,
        "receipts_lines": analysis["receipt_lines"],
        "receipts_terminal_paths": analysis["receipt_terminal_paths"],
        "receipts_redaction_ok": True,
        "resume_proof_path": RESUME_RELPATH,
        "resume_proof_schema": RESUME_SCHEMA,
        "resume_proof_ok": True,
        "resume_proof_redaction_ok": True,
        "repeat_import_proof_path": REPEAT_RELPATH,
        "repeat_import_proof_schema": REPEAT_SCHEMA,
        "repeat_import_proof_ok": True,
        "repeat_import_counts_byte_identical": True,
        "repeat_import_proof_redaction_ok": True,
        "redaction": "counts_paths_hashes_and_non_claims_only_no_decoded_text",
    }


@pytest.fixture(scope="session")
def battery() -> dict[str, Any]:
    """Run the full battery; emit the artifact only on a fully green pass."""
    analysis = run_battery()
    artifact = build_artifact(analysis)
    redaction_check(artifact)
    BATTERY_PATH.parent.mkdir(parents=True, exist_ok=True)
    BATTERY_PATH.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return analysis


# ------------------------------------------------------------------- checks #


def test_design_contract_carries_required_sections_and_markers(battery):
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    for marker in REQUIRED_MARKERS:
        assert marker in text, f"design contract is missing required marker: {marker!r}"


def test_frozen_contracts_match_the_pinned_inventory_exactly(battery):
    frozen = battery["frozen_contracts"]
    assert len(frozen) == len(FROZEN_CONTRACT_RELPATHS) == 5
    for entry in frozen:
        assert entry["matches_inventory"] is True, (
            f"frozen contract drifted against the pinned inventory: {entry['path']}"
        )


def test_s03_baseline_reconciles_and_r1000_stays_unclosed(battery):
    counts = battery["baseline"]["counts"]
    assert counts["entries"] == counts["accepted"] == EXPECTED_ENTRIES
    assert counts["refused"] == EXPECTED_REFUSED
    assert counts["incomplete"] == EXPECTED_INCOMPLETE
    assert battery["baseline"]["r1000_status"] == EXPECTED_R1000_STATUS
    assert battery["baseline"]["status"] == "complete"


def test_corpus_run_report_is_the_corpus_census_schema_v1_and_accounted(battery):
    report = battery["run_report"]
    assert report["schema"] == RUN_SCHEMA
    counts = report["counts"]
    assert_counts_accounting(counts)
    assert report["partial_is_not_full"] is True
    assert report["r1000_status"] == EXPECTED_R1000_STATUS
    assert_s03_reconciled(report["s03_baseline_reconciled"])


def test_receipt_ledger_is_schema_v1_redacted_and_matches_the_report(battery):
    lines = RECEIPTS_PATH.read_text(encoding="utf-8").splitlines()
    receipts = [json.loads(raw) for raw in lines if raw.strip()]
    assert receipts, "the receipt ledger must not be empty"
    for receipt in receipts:
        assert receipt["schema"] == RECEIPT_SCHEMA
        assert receipt["outcome"] in ("accepted", "refused", "incomplete")
    assert battery["receipt_terminal_paths"] == battery["run_report"]["counts"]["terminal"]


def test_resume_and_repeat_import_proofs_are_schema_v1_and_ok(battery):
    resume = battery["resume_proof"]
    assert resume["schema"] == RESUME_SCHEMA
    assert resume["ok"] is True
    repeat = battery["repeat_proof"]
    assert repeat["schema"] == REPEAT_SCHEMA
    assert repeat["ok"] is True
    assert repeat["counts_byte_identical"] is True


def test_all_s07_evidence_artifacts_are_redacted(battery):
    for artifact in (
        battery["run_report"],
        battery["resume_proof"],
        battery["repeat_proof"],
    ):
        redaction_check(artifact)
    lines = RECEIPTS_PATH.read_text(encoding="utf-8").splitlines()
    redaction_check([json.loads(raw) for raw in lines if raw.strip()])


def test_immutability_pins_cover_six_section2_files_and_two_jsonl(battery):
    assert len(battery["section2_entries"]) == 6
    assert len(battery["architecture_entries"]) == 2
    for entry in battery["section2_entries"] + battery["architecture_entries"]:
        assert entry["matches_pin"] is True, f"immutability drift: {entry['path']}"


def test_consumer_model_block_is_total_over_the_closed_vocabulary(battery):
    model = battery["consumer_model"]
    assert model["provenance_forms"] == list(EXPECTED_PROVENANCE_FORMS)
    assert model["derived_kinds"] == list(EXPECTED_DERIVED_KINDS)
    assert model["graph_identity"] == list(EXPECTED_GRAPH_IDENTITY)
    assert model["graph_nodes"] == list(EXPECTED_GRAPH_NODES)
    assert model["graph_edges"] == list(EXPECTED_GRAPH_EDGES)
    assert model["graph_refusals"] == list(EXPECTED_GRAPH_REFUSALS)


def test_consumer_model_block_matches_source_declarations(battery):
    # The source side is re-parsed here so a stale fixture can never hide drift.
    tokenizer_source = TOKENIZER_SOURCE_PATH.read_text(encoding="utf-8")
    graph_source = GRAPH_SOURCE_PATH.read_text(encoding="utf-8")
    tokenizer_model = parse_tokenizer_model(tokenizer_source)
    graph_model = parse_graph_model(graph_source)
    model = battery["consumer_model"]
    assert tokenizer_model["provenance_forms"] == model["provenance_forms"]
    assert tokenizer_model["derived_kinds"] == model["derived_kinds"]
    assert graph_model["identity"] == model["graph_identity"]
    assert graph_model["nodes"] == model["graph_nodes"]
    assert graph_model["edges"] == model["graph_edges"]
    assert graph_model["refusals"] == model["graph_refusals"]


def test_embedded_model_blocks_match_the_design_contract(battery):
    contract_text = CONTRACT_PATH.read_text(encoding="utf-8")
    model_lines = parse_consumer_model_block(contract_text)
    tokenizer_block = parse_rust_model_block(
        TOKENIZER_SOURCE_PATH.read_text(encoding="utf-8"),
        TOKENIZER_MODEL_BEGIN,
        TOKENIZER_MODEL_END,
        "reader_tokenizer consumer-model",
    )
    graph_block = parse_rust_model_block(
        GRAPH_SOURCE_PATH.read_text(encoding="utf-8"),
        GRAPH_MODEL_BEGIN,
        GRAPH_MODEL_END,
        "npa_graph_projection consumer-model",
    )
    assert tokenizer_block == model_lines_by_prefix(model_lines, TOKENIZER_MODEL_PREFIXES)
    assert graph_block == model_lines_by_prefix(model_lines, GRAPH_MODEL_PREFIXES)


def test_battery_artifact_is_emitted_redacted_and_schema_versioned(battery):
    assert BATTERY_PATH.is_file(), "the battery artifact must exist after a green pass"
    artifact = json.loads(BATTERY_PATH.read_text(encoding="utf-8"))
    assert artifact["schema"] == SCHEMA
    assert artifact["version"] == VERSION
    assert artifact["frozen_contracts_match_inventory"] is True
    assert artifact["immutability_pins_match"] is True
    assert artifact["consumer_model_matches_source"] is True
    assert artifact["census_accounting_ok"] is True
    assert artifact["census_s03_reconciled"] is True
    assert artifact["receipts_redaction_ok"] is True
    assert artifact["resume_proof_ok"] is True
    assert artifact["repeat_import_counts_byte_identical"] is True
    assert "not_r1000_closure" in artifact["non_claims"]
    assert "not_physical_pagination" in artifact["non_claims"]
    assert "a_partial_corpus_run_is_never_reported_as_full" in artifact["non_claims"]
    assert len(artifact["frozen_section2_files"]) == 6
    assert len(artifact["frozen_architecture_jsonl"]) == 2
    assert artifact["s03_baseline_reconciled"] == {
        "entries": EXPECTED_ENTRIES,
        "accepted": EXPECTED_ACCEPTED,
        "refused": EXPECTED_REFUSED,
        "incomplete": EXPECTED_INCOMPLETE,
        "r1000_status": EXPECTED_R1000_STATUS,
    }
    redaction_check(artifact)


# ------------------------------------------------------------ negative tests #


def test_inventory_parser_fails_closed_on_a_malformed_line():
    text = "\n".join([INVENTORY_BEGIN, "not-a-valid-line", INVENTORY_END])
    with pytest.raises(AssertionError):
        parse_inventory(text)


def test_consumer_model_parser_rejects_an_unknown_line():
    text = "\n".join([MODEL_BEGIN, "bogus_kind:View", MODEL_END])
    with pytest.raises(AssertionError):
        parse_consumer_model_block(text)


def test_consumer_model_parser_rejects_reordering():
    text = "\n".join([MODEL_BEGIN, *EXPECTED_CONSUMER_MODEL[::-1], MODEL_END])
    with pytest.raises(AssertionError):
        parse_consumer_model_block(text)


def test_frozen_contract_drift_is_detected_not_silently_repinned():
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    inventory = parse_inventory(text)
    victim = FROZEN_CONTRACT_RELPATHS[0]
    corrupted = dict(inventory)
    corrupted[victim] = "0" * 64
    actual = sha256_of_file(ROOT / victim)
    assert actual != f"sha256:{corrupted[victim]}", "the drift check must notice a corrupted pin"


def test_immutability_pin_drift_is_detected_not_silently_repinned():
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    pins = parse_immutability_pins(text)
    victim = FROZEN_SECTION2_RELPATHS[0]
    corrupted = dict(pins)
    corrupted[victim] = "0" * 64
    actual = sha256_of_file(ROOT / victim)
    assert actual != f"sha256:{corrupted[victim]}", "the pin check must notice a corrupted pin"


def test_counts_accounting_rejects_a_broken_terminal_partition():
    with pytest.raises(AssertionError):
        assert_counts_accounting(
            {
                "entries": 10,
                "accepted": 5,
                "refused": 0,
                "incomplete": 0,
                "terminal": 4,
                "remaining": 6,
            }
        )


def test_counts_accounting_rejects_a_broken_entry_partition():
    with pytest.raises(AssertionError):
        assert_counts_accounting(
            {
                "entries": 10,
                "accepted": 5,
                "refused": 1,
                "incomplete": 0,
                "terminal": 6,
                "remaining": 99,
            }
        )


def test_counts_accounting_accepts_a_honest_partial():
    assert_counts_accounting(
        {
            "entries": 43785,
            "accepted": 3335,
            "refused": 0,
            "incomplete": 0,
            "terminal": 3335,
            "remaining": 40450,
        }
    )


def test_s03_reconciliation_rejects_a_drifted_number():
    with pytest.raises(AssertionError):
        assert_s03_reconciled(
            {
                "entries": 43785,
                "accepted": 43784,
                "refused": 0,
                "incomplete": 0,
                "r1000_status": "active/unclosed",
            }
        )


def test_redaction_guard_refuses_raw_decoded_text():
    with pytest.raises(harness.HarnessError):
        harness.assert_no_raw_text({"note": "сырой декодированный текст"})


def test_redaction_guard_refuses_a_non_ascii_string():
    with pytest.raises(harness.HarnessError):
        harness.assert_no_raw_text({"relative_path": "дело/0001.xml"})


def test_redaction_guard_refuses_an_oversized_string():
    with pytest.raises(harness.HarnessError):
        harness.assert_no_raw_text({"note": "a" * 5000})


def test_redaction_guard_accepts_paths_counters_and_hashes():
    harness.assert_no_raw_text(
        {
            "relative_path": "courts/arb/000879098-edition-4522ae70.xml",
            "sha256": "sha256:" + "a" * 64,
            "accepted": 3335,
            "outcome": "accepted",
        }
    )


def test_str_array_parser_fails_closed_on_a_missing_const():
    with pytest.raises(AssertionError):
        parse_str_array('pub const SOMETHING_ELSE: [&str; 1] = ["x"];', "NPA_GRAPH_REFUSALS")

#!/usr/bin/env python3
"""Hybrid evaluator experiment plus versioned records validator (M207 S05).

Repository verification harness. Not product parsing, not human annotation,
not gold, not a frozen S01/S02/S03 schema, and not S03 metrics.

Synthetic evaluator: four constructions (shared-head series, agreement
referring to a contract, annex with an approving act, alias/this-ref
ambiguity). Alignment is by local anchor identity only. Default and --check
are read-only drift checks; --write is explicit.

External records CLI: --validate-records PATH is read-only UTF-8 JSON
validation of m207-hybrid-records/v1. It cannot overwrite PATH, the
synthetic artifact, or frozen S01-S04 stores. Stdlib json only (D328: no
serde on the future Rust emitter).

Third read-only mode: --evaluate-records EXPECTED PREDICTED validates both
m207-hybrid-records/v1 files, pairs bundles by bundle_id only, and prints an
m207-hybrid-eval-report/v1 report whose differential and metamorphic evidence
objects stay siblings. It never writes, and the expected file is a harness
reference, not human gold (D519/D521).

Markers: M207_HYBRID_SYNTHETIC_EXPERIMENT_OK, M207_HYBRID_RECORDS_OK,
M207_HYBRID_EVAL_OK (report shape and denominators only, never acceptance)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
MARKER = "M207_HYBRID_SYNTHETIC_EXPERIMENT_OK"
SCHEMA = "m207-hybrid-synthetic-experiment/v1"
RECORD_REL = "prd/migration/rust-evidence/m207-hybrid-synthetic-experiment.json"
RECORDS_MARKER = "M207_HYBRID_RECORDS_OK"
RECORDS_SCHEMA = "m207-hybrid-records/v1"
RECORDS_SCHEMA_VERSION = 1
RECORDS_ORIGINS = ("synthetic", "rust-runtime")
EVAL_MARKER = "M207_HYBRID_EVAL_OK"
EVAL_SCHEMA = "m207-hybrid-eval-report/v1"
EVAL_SCHEMA_VERSION = 1
# Eval-only protected paths. PROTECTED_RELS and protected_path_reason are
# intentionally untouched so --validate-records keeps its S05 behavior.
EVAL_EXTRA_PROTECTED_RELS = ("prd/migration/rust-evidence/m207-s03-evaluation-report.json",)
# Closed set of eval diagnostics. The sibling contract document repeats this
# list between machine-readable markers; the doc-code test compares both ways.
EVAL_DIAGNOSTICS = (
    "USAGE",
    "MISSING_INPUT",
    "PROTECTED_PATH",
    "DUPLICATE_BUNDLE_ID",
    "UNSUPPORTED_VERSION",
    "MALFORMED_REF",
    "INVALID_BOUNDS",
    "CROSS_DOC_REF",
    "DANGLING_EDGE",
    "AMBIGUOUS_DUPLICATE",
    "PROVENANCE_FORBIDDEN",
    "SOURCE_CLAIM_WITHOUT_BYTES",
)
EVAL_LIMITS = (
    "harness-built records only: the Rust emitter is M211 S02 and has not run",
    "no size cap on m207-hybrid-records/v1 input (inherited S05 limit, operator-local)",
    "unmatched bundle ids are explicit bundle FN/FP, never scored against an empty partner",
    "ambiguity_groups 0 means no validated pair carried a duplicate anchor-key",
    "local_focus is a secondary plane and hides missing members (synthetic 4/13 vs 9/13)",
)
EVAL_NON_CLAIMS = (
    "Not human gold: neither input is a human label store",
    "Not parser quality: no Rust emitter has produced these records (M211 S02 pending)",
    "Not S03 metrics: frozen human-pass rates are not reused as a denominator",
    "Not Rust parity: provenance_origin rust-runtime is a label, not proof",
    "Synthetic fixtures are not Rust output and are not presented as such",
    "Does not read or rewrite protected frozen S01-S04 or S03 stores",
)
EVAL_NOT_MEASURED_POLICY = (
    "a zero denominator yields value null and status not-measured; a not-measured "
    "block contributes nothing to any numerator or denominator and is never "
    "coerced into perfect accuracy"
)
PROTECTED_RELS = (
    RECORD_REL,
    "prd/annotation/m207-s01-codebook.md",
    "prd/annotation/m207-s01-schemas.json",
    "prd/annotation/m207-s02-coder-protocol.md",
    "prd/annotation/m207-s02-schemas.json",
    "prd/annotation/m207-s03-eval-protocol.md",
    "prd/annotation/m207-s03-schemas.json",
    "prd/annotation/m207-s04-c4-protocol.md",
    "prd/annotation/m207-s04-schemas.json",
    "prd/migration/rust-evidence/m207-s01-pilot-cases.json",
    "prd/migration/rust-evidence/m207-s03-eval-manifest.json",
    "prd/migration/rust-evidence/m207-context-inventory.json",
)
PROTECTED_PREFIXES = (
    "prd/annotation/m207-s02-submissions/",
    "prd/annotation/m207-s02-adjudications/",
)
SLOTS = ("kind", "date", "number")
SOURCE_SLOTS = ("date", "number")
CONSTRUCTIONS = (
    "shared-head-series",
    "agreement-refers-to-contract",
    "annex-approved-by",
    "alias-this-ref-ambiguity",
)

# Closed key allow-lists for the external records wire contract
# (prd/annotation/m207-hybrid-records-contract.md). The synthetic experiment
# schema is a separate fixture and is not validated against these lists.
RECORDS_ENVELOPE_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "provenance_origin",
        "documents",
        "bundles",
        "lifecycle",
        "authoritative",
        "is_gold",
        "not_human",
        "not_s03_metrics",
        "source_validation",
        "alignment_policy",
        "limits",
        "non_claims",
    }
)
RECORDS_DOCUMENT_KEYS = frozenset({"document_id", "fragments"})
RECORDS_FRAGMENT_KEYS = frozenset({"fragment_id", "byte_length", "source_utf8"})
RECORDS_BUNDLE_KEYS = frozenset(
    {
        "bundle_id",
        "construction",
        "focus_id",
        "context_status",
        "declared_region",
        "context_only",
        "occurrences",
        "relations",
    }
)
RECORDS_OCCURRENCE_KEYS = frozenset({"id", "anchors", "unresolved", "unresolved_reason", "fields"})
RECORDS_RELATION_KEYS = frozenset({"id", "rel", "from", "to"})
RECORDS_FIELDS_KEYS = frozenset(SLOTS)
RECORDS_FIELD_SLOT_KEYS = frozenset({"value", "source"})
RECORDS_ANCHOR_KEYS = frozenset({"fragment_id", "start", "end"})

# Explicitly forbidden, at any level: S03 rate keys, coder submission shapes,
# and raw legal corpus text. Unknown keys are already refused by the closed
# allow-lists; naming these keeps the refusal explicit and auditable.
RECORDS_FORBIDDEN_KEYS = {
    "false_authority": "S03 rate key",
    "span_rate": "S03 rate key",
    "slot_rate": "S03 rate key",
    "scope_rate": "S03 rate key",
    "binding_rate": "S03 rate key",
    "abstention_rate": "S03 rate key",
    "aspect_rates": "S03 rate key",
    "submissions": "coder submission shape",
    "coder_id": "coder submission shape",
    "coder": "coder submission shape",
    "adjudication": "coder submission shape",
    "adjudications": "coder submission shape",
    "corpus_excerpt": "raw legal corpus text",
    "raw_text": "raw legal corpus text",
    "legal_text": "raw legal corpus text",
    "source_text": "raw legal corpus text",
    "corpus_text": "raw legal corpus text",
    "raw_legal_text": "raw legal corpus text",
}

# Honesty keys are optional, but when present they must carry the fixed v1
# value. A dishonest label is refused, not silently accepted.
RECORDS_HONESTY_VALUES = (
    ("lifecycle", ["proposed"]),
    ("authoritative", False),
    ("is_gold", False),
    ("not_human", True),
    ("not_s03_metrics", True),
    ("alignment_policy", "local-anchor-identity-v1"),
)

# Working labels only. Not adopted legal TYPE vocabulary.
KIND_MEMBER = "series_member"
KIND_AGREEMENT = "agreement"
KIND_CONTRACT = "contract"
KIND_ANNEX = "annex"
KIND_APPROVER = "approving_act"
KIND_UNRESOLVED = "unresolved_ref"
REL_SERIES = "same_series"
REL_REFERS = "refers_to"
REL_APPROVED = "approved_by"

HEAD_FRAG = "syn-head"
M1_FRAG = "syn-member-a"
M2_FRAG = "syn-member-b"
AG_FRAG = "syn-agreement"
CT_FRAG = "syn-contract"
AX_FRAG = "syn-annex"
AP_FRAG = "syn-approver"
TH_FRAG = "syn-this"
AL_FRAG = "syn-alias"

HEAD_SPAN = (0, 8)  # SYN-HEAD
M1_SPAN = (0, 12)  # SYN-MEMBER-A
M2_SPAN = (0, 12)  # SYN-MEMBER-B
AG_SPAN = (0, 13)  # SYN-AGREEMENT
CT_SPAN = (0, 12)  # SYN-CONTRACT
AX_SPAN = (0, 9)  # SYN-ANNEX
AP_SPAN = (0, 12)  # SYN-APPROVER
TH_SPAN = (0, 8)  # SYN-THIS
AL_SPAN = (0, 9)  # SYN-ALIAS

DATE_SERIES = "2000-01-01"
NUM_SERIES = "1"
DATE_AG = "2001-02-02"
NUM_AG = "2"
DATE_CT = "1999-03-03"
NUM_CT = "9"
DATE_AX = "2002-04-04"
NUM_AX = "4"
DATE_AP = "2002-05-05"
NUM_AP = "5"
DATE_REPEAT = "2010-10-10"
NUM_REPEAT = "77"


class ExperimentError(Exception):
    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


def anchor(fragment_id: str, span: tuple[int, int]) -> dict[str, Any]:
    return {"fragment_id": fragment_id, "start": span[0], "end": span[1]}


def field(value: Any, source: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"value": value, "source": source}


def occ(
    oid: str,
    anchors: Sequence[Mapping[str, Any]],
    *,
    kind: str,
    date: Any,
    number: Any,
    date_src: dict[str, Any] | None,
    number_src: dict[str, Any] | None,
    unresolved: bool = False,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "id": oid,
        "anchors": [dict(a) for a in anchors],
        "unresolved": unresolved,
        "unresolved_reason": reason,
        "fields": {
            "kind": field(kind, None),
            "date": field(date, date_src),
            "number": field(number, number_src),
        },
    }


def rel(rid: str, name: str, frm: str, to: str) -> dict[str, Any]:
    return {"id": rid, "rel": name, "from": frm, "to": to}


def bundle(
    *,
    bid: str,
    construction: str,
    focus_id: str,
    context_status: str,
    declared_region: Sequence[str],
    context_only: Sequence[str],
    occs: Sequence[Mapping[str, Any]],
    rels: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "bundle_id": bid,
        "construction": construction,
        "focus_id": focus_id,
        "context_status": context_status,
        "declared_region": list(declared_region),
        "context_only": list(context_only),
        "occurrences": [dict(o) for o in occs],
        "relations": [dict(r) for r in rels],
    }


def clone(payload: Any) -> Any:
    return json.loads(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def head_src() -> dict[str, Any]:
    return anchor(HEAD_FRAG, HEAD_SPAN)


def own_src(fragment_id: str, span: tuple[int, int]) -> dict[str, Any]:
    return anchor(fragment_id, span)


def series_expected() -> dict[str, Any]:
    src = head_src()
    return bundle(
        bid="series",
        construction="shared-head-series",
        focus_id="occ-a",
        context_status="available",
        declared_region=(HEAD_FRAG, M1_FRAG, M2_FRAG),
        context_only=(HEAD_FRAG,),
        occs=(
            occ(
                "occ-a",
                [anchor(M1_FRAG, M1_SPAN)],
                kind=KIND_MEMBER,
                date=DATE_SERIES,
                number=NUM_SERIES,
                date_src=src,
                number_src=src,
            ),
            occ(
                "occ-b",
                [anchor(M2_FRAG, M2_SPAN)],
                kind=KIND_MEMBER,
                date=DATE_SERIES,
                number=NUM_SERIES,
                date_src=src,
                number_src=src,
            ),
        ),
        rels=(rel("rel-1", REL_SERIES, "occ-a", "occ-b"),),
    )


def agreement_expected() -> dict[str, Any]:
    return bundle(
        bid="agreement",
        construction="agreement-refers-to-contract",
        focus_id="occ-a",
        context_status="available",
        declared_region=(AG_FRAG, CT_FRAG),
        context_only=(),
        occs=(
            occ(
                "occ-a",
                [anchor(AG_FRAG, AG_SPAN)],
                kind=KIND_AGREEMENT,
                date=DATE_AG,
                number=NUM_AG,
                date_src=own_src(AG_FRAG, AG_SPAN),
                number_src=own_src(AG_FRAG, AG_SPAN),
            ),
            occ(
                "occ-b",
                [anchor(CT_FRAG, CT_SPAN)],
                kind=KIND_CONTRACT,
                date=DATE_CT,
                number=NUM_CT,
                date_src=own_src(CT_FRAG, CT_SPAN),
                number_src=own_src(CT_FRAG, CT_SPAN),
            ),
        ),
        rels=(rel("rel-1", REL_REFERS, "occ-a", "occ-b"),),
    )


def annex_expected() -> dict[str, Any]:
    return bundle(
        bid="annex",
        construction="annex-approved-by",
        focus_id="occ-a",
        context_status="available",
        declared_region=(AX_FRAG, AP_FRAG),
        context_only=(),
        occs=(
            occ(
                "occ-a",
                [anchor(AX_FRAG, AX_SPAN)],
                kind=KIND_ANNEX,
                date=DATE_AX,
                number=NUM_AX,
                date_src=own_src(AX_FRAG, AX_SPAN),
                number_src=own_src(AX_FRAG, AX_SPAN),
            ),
            occ(
                "occ-b",
                [anchor(AP_FRAG, AP_SPAN)],
                kind=KIND_APPROVER,
                date=DATE_AP,
                number=NUM_AP,
                date_src=own_src(AP_FRAG, AP_SPAN),
                number_src=own_src(AP_FRAG, AP_SPAN),
            ),
        ),
        rels=(rel("rel-1", REL_APPROVED, "occ-a", "occ-b"),),
    )


def alias_expected() -> dict[str, Any]:
    reason = "alias-or-this-ref-ambiguous"
    return bundle(
        bid="alias",
        construction="alias-this-ref-ambiguity",
        focus_id="occ-a",
        context_status="available",
        declared_region=(TH_FRAG, AL_FRAG),
        context_only=(),
        occs=(
            occ(
                "occ-a",
                [anchor(TH_FRAG, TH_SPAN)],
                kind=KIND_UNRESOLVED,
                date=None,
                number=None,
                date_src=None,
                number_src=None,
                unresolved=True,
                reason=reason,
            ),
            occ(
                "occ-b",
                [anchor(AL_FRAG, AL_SPAN)],
                kind=KIND_UNRESOLVED,
                date=None,
                number=None,
                date_src=None,
                number_src=None,
                unresolved=True,
                reason=reason,
            ),
        ),
        rels=(),
    )


def repeat_expected() -> dict[str, Any]:
    return bundle(
        bid="repeat",
        construction="agreement-refers-to-contract",
        focus_id="occ-a",
        context_status="available",
        declared_region=(AG_FRAG, CT_FRAG),
        context_only=(),
        occs=(
            occ(
                "occ-a",
                [anchor(AG_FRAG, AG_SPAN)],
                kind=KIND_AGREEMENT,
                date=DATE_REPEAT,
                number=NUM_REPEAT,
                date_src=own_src(AG_FRAG, AG_SPAN),
                number_src=own_src(AG_FRAG, AG_SPAN),
            ),
            occ(
                "occ-b",
                [anchor(CT_FRAG, CT_SPAN)],
                kind=KIND_CONTRACT,
                date=DATE_REPEAT,
                number=NUM_REPEAT,
                date_src=own_src(CT_FRAG, CT_SPAN),
                number_src=own_src(CT_FRAG, CT_SPAN),
            ),
        ),
        rels=(rel("rel-1", REL_REFERS, "occ-a", "occ-b"),),
    )


def drop_occ(payload: dict[str, Any], oid: str) -> dict[str, Any]:
    out = clone(payload)
    out["occurrences"] = [row for row in out["occurrences"] if row["id"] != oid]
    out["relations"] = [row for row in out["relations"] if row["from"] != oid and row["to"] != oid]
    return out


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ExperimentError("MALFORMED_REF", f"{label} must be an object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ExperimentError("MALFORMED_REF", f"{label} must be an array")
    return value


def require_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExperimentError("MALFORMED_REF", f"{label} must be a non-empty string")
    return value


def require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExperimentError("MALFORMED_REF", f"{label} must be an integer")
    return value


def require_closed_keys(payload: Mapping[str, Any], allowed: frozenset[str], label: str) -> None:
    """Refuse any key outside the documented closed allow-list for one level."""
    for key in sorted(payload):
        reason = RECORDS_FORBIDDEN_KEYS.get(key)
        if reason is not None:
            raise ExperimentError(
                "MALFORMED_REF",
                f"{label}.{key} is forbidden in m207-hybrid-records/v1 ({reason})",
            )
        if key not in allowed:
            raise ExperimentError(
                "MALFORMED_REF",
                f"{label}.{key} is not in the closed m207-hybrid-records/v1 allow-list",
            )


def require_str_list(value: Any, label: str) -> list[str]:
    rows = require_list(value, label)
    out: list[str] = []
    for index, row in enumerate(rows):
        out.append(require_str(row, f"{label}[{index}]"))
    return out


def validate_honesty_keys(payload: Mapping[str, Any], label: str) -> None:
    """Optional envelope keys must be honest when present (fail closed)."""
    for key, expected in RECORDS_HONESTY_VALUES:
        if key not in payload:
            continue
        actual = payload[key]
        if isinstance(expected, bool):
            ok = actual is expected
        elif isinstance(expected, list):
            ok = isinstance(actual, list) and actual == expected
        else:
            ok = isinstance(actual, str) and actual == expected
        if not ok:
            raise ExperimentError(
                "MALFORMED_REF",
                f"{label}.{key} must be {expected!r} (honesty key) but is {actual!r}",
            )


def validate_anchor(row: Any, label: str) -> dict[str, Any]:
    payload = require_mapping(row, label)
    require_closed_keys(payload, RECORDS_ANCHOR_KEYS, label)
    fragment_id = require_str(payload.get("fragment_id"), f"{label}.fragment_id")
    start = require_int(payload.get("start"), f"{label}.start")
    end = require_int(payload.get("end"), f"{label}.end")
    if start < 0 or end <= start:
        raise ExperimentError(
            "MALFORMED_REF",
            f"{label} is not a half-open local byte span: [{start}, {end})",
        )
    return {"fragment_id": fragment_id, "start": start, "end": end}


def validate_source(row: Any, label: str) -> dict[str, Any] | None:
    if row is None:
        return None
    return validate_anchor(row, label)


def validate_bundle(payload: Mapping[str, Any], label: str) -> dict[str, Any]:
    body = require_mapping(payload, label)
    require_closed_keys(body, RECORDS_BUNDLE_KEYS, label)
    for key in (
        "bundle_id",
        "construction",
        "focus_id",
        "context_status",
        "declared_region",
        "context_only",
        "occurrences",
        "relations",
    ):
        if key not in body:
            raise ExperimentError("MALFORMED_REF", f"{label} missing {key}")
    require_str(body["bundle_id"], f"{label}.bundle_id")
    require_str(body["construction"], f"{label}.construction")
    require_str(body["context_status"], f"{label}.context_status")
    require_str_list(body["declared_region"], f"{label}.declared_region")
    require_str_list(body["context_only"], f"{label}.context_only")
    occs = require_list(body["occurrences"], f"{label}.occurrences")
    rels = require_list(body["relations"], f"{label}.relations")
    ids: list[str] = []
    for index, raw in enumerate(occs):
        item = require_mapping(raw, f"{label}.occurrences[{index}]")
        require_closed_keys(item, RECORDS_OCCURRENCE_KEYS, f"{label}.occurrences[{index}]")
        oid = require_str(item.get("id"), f"{label}.occurrences[{index}].id")
        if oid in ids:
            raise ExperimentError("MALFORMED_REF", f"{label} duplicate occurrence id {oid}")
        ids.append(oid)
        anchors = require_list(item.get("anchors"), f"{label}.{oid}.anchors")
        if not anchors:
            raise ExperimentError("MALFORMED_REF", f"{label}.{oid} has no anchors")
        for a_index, raw_anchor in enumerate(anchors):
            validate_anchor(raw_anchor, f"{label}.{oid}.anchors[{a_index}]")
        fields = require_mapping(item.get("fields"), f"{label}.{oid}.fields")
        require_closed_keys(fields, RECORDS_FIELDS_KEYS, f"{label}.{oid}.fields")
        for slot in SLOTS:
            if slot not in fields:
                raise ExperimentError("MALFORMED_REF", f"{label}.{oid}.fields missing {slot}")
            slot_body = require_mapping(fields[slot], f"{label}.{oid}.fields.{slot}")
            require_closed_keys(slot_body, RECORDS_FIELD_SLOT_KEYS, f"{label}.{oid}.fields.{slot}")
            if "value" not in slot_body or "source" not in slot_body:
                raise ExperimentError(
                    "MALFORMED_REF",
                    f"{label}.{oid}.fields.{slot} needs value and source",
                )
            validate_source(slot_body.get("source"), f"{label}.{oid}.fields.{slot}.source")
        if not isinstance(item.get("unresolved"), bool):
            raise ExperimentError("MALFORMED_REF", f"{label}.{oid}.unresolved must be bool")
        reason = item.get("unresolved_reason")
        if reason is not None and not isinstance(reason, str):
            raise ExperimentError(
                "MALFORMED_REF", f"{label}.{oid}.unresolved_reason must be null or a string"
            )
    id_set = set(ids)
    focus = require_str(body["focus_id"], f"{label}.focus_id")
    if ids and focus not in id_set:
        raise ExperimentError("DANGLING_EDGE", f"{label} focus_id {focus} is not an occurrence")
    rel_ids: list[str] = []
    for index, raw in enumerate(rels):
        item = require_mapping(raw, f"{label}.relations[{index}]")
        require_closed_keys(item, RECORDS_RELATION_KEYS, f"{label}.relations[{index}]")
        rid = require_str(item.get("id"), f"{label}.relations[{index}].id")
        if rid in rel_ids:
            raise ExperimentError("MALFORMED_REF", f"{label} duplicate relation id {rid}")
        rel_ids.append(rid)
        require_str(item.get("rel"), f"{label}.{rid}.rel")
        frm = require_str(item.get("from"), f"{label}.{rid}.from")
        to = require_str(item.get("to"), f"{label}.{rid}.to")
        if frm not in id_set or to not in id_set:
            raise ExperimentError(
                "DANGLING_EDGE",
                f"{label}.{rid} endpoints ({frm}, {to}) are not both occurrences",
            )
    return dict(body)


def utf8_span_ok(raw: bytes, start: int, end: int) -> bool:
    if start < 0 or end < start or end > len(raw):
        return False
    if start != 0 and start < len(raw) and (raw[start] & 0xC0) == 0x80:
        return False
    if end != len(raw) and end < len(raw) and (raw[end] & 0xC0) == 0x80:
        return False
    try:
        raw[start:end].decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def records_report(
    *,
    status: str,
    origin: str | None,
    source_validation: str | None,
    documents: int,
    fragments: int,
    bundles: int,
    diagnostics: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    return {
        "status": status,
        "marker": RECORDS_MARKER if status == "ok" else None,
        "schema": RECORDS_SCHEMA,
        "schema_version": RECORDS_SCHEMA_VERSION,
        "provenance_origin": origin,
        "source_validation": source_validation,
        "documents": documents,
        "fragments": fragments,
        "bundles": bundles,
        "diagnostics": [dict(row) for row in diagnostics],
    }


def invalid_records_report(error: ExperimentError) -> dict[str, Any]:
    return records_report(
        status="invalid",
        origin=None,
        source_validation=None,
        documents=0,
        fragments=0,
        bundles=0,
        diagnostics=({"code": error.diagnostic, "detail": error.detail},),
    )


def protected_path_reason(root: Path, path: Path) -> str | None:
    raw = Path(path)
    bases = []
    for base in (root, ROOT):
        resolved_base = Path(base).resolve()
        if resolved_base not in bases:
            bases.append(resolved_base)
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append(raw)
        for base in bases:
            candidates.append(base / raw)
    resolved: list[Path] = []
    for item in candidates:
        resolved.append(item.resolve())
    posix_names = {item.as_posix() for item in candidates}
    posix_names.update(item.as_posix() for item in resolved)
    for rel in PROTECTED_RELS:
        if rel in posix_names or any(name.endswith("/" + rel) for name in posix_names):
            return rel
        for base in bases:
            if (base / rel).resolve() in resolved:
                return rel
    for prefix in PROTECTED_PREFIXES:
        for name in posix_names:
            if name == prefix.rstrip("/") or name.endswith("/" + prefix.rstrip("/")):
                return prefix
            if prefix in name.replace("\\", "/"):
                return prefix
        for base in bases:
            for item in resolved:
                try:
                    relative = item.relative_to(base).as_posix()
                except ValueError:
                    continue
                if relative == prefix.rstrip("/") or relative.startswith(prefix):
                    return prefix
    return None


def fragment_text(fragment_id: str) -> str:
    mapping = {
        HEAD_FRAG: "SYN-HEAD",
        M1_FRAG: "SYN-MEMBER-A",
        M2_FRAG: "SYN-MEMBER-B",
        AG_FRAG: "SYN-AGREEMENT",
        CT_FRAG: "SYN-CONTRACT",
        AX_FRAG: "SYN-ANNEX",
        AP_FRAG: "SYN-APPROVER",
        TH_FRAG: "SYN-THIS",
        AL_FRAG: "SYN-ALIAS",
    }
    if fragment_id not in mapping:
        raise ExperimentError("MALFORMED_REF", f"unknown synthetic fragment {fragment_id}")
    return mapping[fragment_id]


def fragment_entry(fragment_id: str, *, with_bytes: bool = True) -> dict[str, Any]:
    text = fragment_text(fragment_id)
    encoded = text.encode("utf-8")
    row: dict[str, Any] = {
        "fragment_id": fragment_id,
        "byte_length": len(encoded),
    }
    if with_bytes:
        row["source_utf8"] = text
    return row


def example_hybrid_records(
    *,
    origin: str = "synthetic",
    with_bytes: bool = True,
    include_alias: bool = True,
) -> dict[str, Any]:
    documents = [
        {
            "document_id": "doc-series",
            "fragments": [
                fragment_entry(HEAD_FRAG, with_bytes=with_bytes),
                fragment_entry(M1_FRAG, with_bytes=with_bytes),
                fragment_entry(M2_FRAG, with_bytes=with_bytes),
            ],
        },
        {
            "document_id": "doc-agreement",
            "fragments": [
                fragment_entry(AG_FRAG, with_bytes=with_bytes),
                fragment_entry(CT_FRAG, with_bytes=with_bytes),
            ],
        },
        {
            "document_id": "doc-annex",
            "fragments": [
                fragment_entry(AX_FRAG, with_bytes=with_bytes),
                fragment_entry(AP_FRAG, with_bytes=with_bytes),
            ],
        },
    ]
    bundles = [series_expected(), agreement_expected(), annex_expected()]
    if include_alias:
        documents.append(
            {
                "document_id": "doc-alias",
                "fragments": [
                    fragment_entry(TH_FRAG, with_bytes=with_bytes),
                    fragment_entry(AL_FRAG, with_bytes=with_bytes),
                ],
            }
        )
        bundles.append(alias_expected())
    derived = "bytes-present" if with_bytes else "metadata-only"
    return {
        "schema": RECORDS_SCHEMA,
        "schema_version": RECORDS_SCHEMA_VERSION,
        "lifecycle": ["proposed"],
        "authoritative": False,
        "is_gold": False,
        "not_human": True,
        "not_s03_metrics": True,
        "provenance_origin": origin,
        "source_validation": derived,
        "alignment_policy": "local-anchor-identity-v1",
        "documents": documents,
        "bundles": bundles,
        "limits": [
            "synthetic expected labels only" if origin == "synthetic" else "rust-runtime export",
            "not human, not gold, not S03 metrics",
            "stdlib JSON wire; no serde",
        ],
        "non_claims": [
            "Does not measure legal correctness",
            "Does not adopt TYPE vocabulary",
            "Does not rewrite frozen S01-S04 stores",
        ],
    }


def cited_anchors(bundle: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in bundle["occurrences"]:
        for anchor_row in item["anchors"]:
            rows.append(dict(anchor_row))
        fields = item["fields"]
        for slot in SLOTS:
            source = fields[slot]["source"]
            if source is not None:
                rows.append(dict(source))
    return rows


def cited_fragment_ids(bundle: Mapping[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("declared_region", "context_only"):
        for item in bundle[key]:
            ids.append(str(item))
    for row in cited_anchors(bundle):
        ids.append(str(row["fragment_id"]))
    return ids


def load_hybrid_records_bytes(raw: bytes, label: str) -> dict[str, Any]:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ExperimentError("MALFORMED_REF", f"{label} carries a UTF-8 BOM")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExperimentError("MALFORMED_REF", f"{label} is not UTF-8: {exc}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExperimentError("MALFORMED_REF", f"{label} is not valid JSON: {exc}") from exc
    return require_mapping(payload, label)


def validate_hybrid_records(payload: Mapping[str, Any], label: str = "records") -> dict[str, Any]:
    body = require_mapping(payload, label)
    require_closed_keys(body, RECORDS_ENVELOPE_KEYS, label)
    validate_honesty_keys(body, label)
    for key in ("schema", "schema_version", "provenance_origin", "documents", "bundles"):
        if key not in body:
            raise ExperimentError("MALFORMED_REF", f"{label} missing {key}")
    schema = body["schema"]
    version = body["schema_version"]
    if not isinstance(schema, str) or not schema:
        raise ExperimentError("MALFORMED_REF", f"{label}.schema must be a non-empty string")
    if isinstance(version, bool) or not isinstance(version, int):
        raise ExperimentError("MALFORMED_REF", f"{label}.schema_version must be an integer")
    if schema != RECORDS_SCHEMA or version != RECORDS_SCHEMA_VERSION:
        raise ExperimentError(
            "UNSUPPORTED_VERSION",
            f"{label} schema {schema!r} version {version} is not {RECORDS_SCHEMA}/"
            f"{RECORDS_SCHEMA_VERSION}",
        )
    origin = require_str(body.get("provenance_origin"), f"{label}.provenance_origin")
    if origin not in RECORDS_ORIGINS:
        raise ExperimentError(
            "PROVENANCE_FORBIDDEN",
            f"{label}.provenance_origin {origin!r} is not one of {list(RECORDS_ORIGINS)}",
        )
    documents = require_list(body["documents"], f"{label}.documents")
    bundles_raw = require_list(body["bundles"], f"{label}.bundles")
    if not documents:
        raise ExperimentError("MALFORMED_REF", f"{label}.documents must be non-empty")
    doc_ids: list[str] = []
    frag_doc: dict[str, str] = {}
    frag_meta: dict[str, dict[str, Any]] = {}
    for d_index, raw_doc in enumerate(documents):
        doc = require_mapping(raw_doc, f"{label}.documents[{d_index}]")
        require_closed_keys(doc, RECORDS_DOCUMENT_KEYS, f"{label}.documents[{d_index}]")
        document_id = require_str(
            doc.get("document_id"), f"{label}.documents[{d_index}].document_id"
        )
        if document_id in doc_ids:
            raise ExperimentError("MALFORMED_REF", f"{label} duplicate document_id {document_id}")
        doc_ids.append(document_id)
        fragments = require_list(doc.get("fragments"), f"{label}.{document_id}.fragments")
        if not fragments:
            raise ExperimentError(
                "MALFORMED_REF", f"{label}.{document_id}.fragments must be non-empty"
            )
        for f_index, raw_frag in enumerate(fragments):
            frag = require_mapping(raw_frag, f"{label}.{document_id}.fragments[{f_index}]")
            require_closed_keys(
                frag, RECORDS_FRAGMENT_KEYS, f"{label}.{document_id}.fragments[{f_index}]"
            )
            fragment_id = require_str(
                frag.get("fragment_id"),
                f"{label}.{document_id}.fragments[{f_index}].fragment_id",
            )
            if fragment_id in frag_meta:
                raise ExperimentError(
                    "MALFORMED_REF", f"{label} duplicate fragment_id {fragment_id}"
                )
            byte_length = require_int(
                frag.get("byte_length"),
                f"{label}.{fragment_id}.byte_length",
            )
            if byte_length < 0:
                raise ExperimentError(
                    "MALFORMED_REF",
                    f"{label}.{fragment_id}.byte_length must be >= 0",
                )
            source_bytes: bytes | None = None
            if "source_utf8" in frag and frag["source_utf8"] is not None:
                text = frag["source_utf8"]
                if not isinstance(text, str):
                    raise ExperimentError(
                        "MALFORMED_REF",
                        f"{label}.{fragment_id}.source_utf8 must be a string",
                    )
                source_bytes = text.encode("utf-8")
                if len(source_bytes) != byte_length:
                    raise ExperimentError(
                        "MALFORMED_REF",
                        f"{label}.{fragment_id} source_utf8 is {len(source_bytes)} bytes, "
                        f"byte_length={byte_length}",
                    )
            frag_doc[fragment_id] = document_id
            frag_meta[fragment_id] = {
                "byte_length": byte_length,
                "source_bytes": source_bytes,
            }
    validated_bundles: list[dict[str, Any]] = []
    referenced: set[str] = set()
    for b_index, raw_bundle in enumerate(bundles_raw):
        bundle_label = f"{label}.bundles[{b_index}]"
        bundle = validate_bundle(raw_bundle, bundle_label)
        ids = cited_fragment_ids(bundle)
        doc_for_bundle: str | None = None
        for fragment_id in ids:
            if fragment_id not in frag_meta:
                raise ExperimentError(
                    "DANGLING_EDGE",
                    f"{bundle_label} cites unknown fragment {fragment_id}",
                )
            document_id = frag_doc[fragment_id]
            if doc_for_bundle is None:
                doc_for_bundle = document_id
            elif document_id != doc_for_bundle:
                raise ExperimentError(
                    "CROSS_DOC_REF",
                    f"{bundle_label} mixes {doc_for_bundle} and {document_id}",
                )
            referenced.add(fragment_id)
        for a_index, row in enumerate(cited_anchors(bundle)):
            fragment_id = str(row["fragment_id"])
            start = int(row["start"])
            end = int(row["end"])
            meta = frag_meta[fragment_id]
            length = int(meta["byte_length"])
            if end > length:
                raise ExperimentError(
                    "INVALID_BOUNDS",
                    f"{bundle_label} anchor[{a_index}] [{start}, {end}) exceeds "
                    f"{fragment_id} byte_length={length}",
                )
            source_bytes = meta["source_bytes"]
            if source_bytes is not None and not utf8_span_ok(source_bytes, start, end):
                raise ExperimentError(
                    "INVALID_BOUNDS",
                    f"{bundle_label} anchor[{a_index}] [{start}, {end}) is not a UTF-8 "
                    f"boundary span in {fragment_id}",
                )
        occs = list(bundle["occurrences"])
        seen_keys: dict[tuple[tuple[str, int, int], ...], list[str]] = defaultdict(list)
        for item in occs:
            seen_keys[anchor_key(item)].append(str(item["id"]))
        for key, occ_ids in seen_keys.items():
            if len(occ_ids) > 1:
                raise ExperimentError(
                    "AMBIGUOUS_DUPLICATE",
                    f"{bundle_label} duplicate anchor {key_json(key)} for {occ_ids}",
                )
        validated_bundles.append(bundle)
    bytes_n = 0
    meta_n = 0
    for fragment_id in referenced:
        if frag_meta[fragment_id]["source_bytes"] is None:
            meta_n += 1
        else:
            bytes_n += 1
    if not referenced:
        derived = "metadata-only"
    elif meta_n == 0:
        derived = "bytes-present"
    elif bytes_n == 0:
        derived = "metadata-only"
    else:
        derived = "mixed"
    declared = body.get("source_validation")
    if declared is not None:
        declared_s = require_str(declared, f"{label}.source_validation")
        if declared_s != derived:
            if declared_s == "bytes-present" and derived != "bytes-present":
                raise ExperimentError(
                    "SOURCE_CLAIM_WITHOUT_BYTES",
                    f"{label} claims bytes-present but derived source_validation={derived}",
                )
            raise ExperimentError(
                "MALFORMED_REF",
                f"{label}.source_validation {declared_s!r} does not match derived {derived!r}",
            )
    return records_report(
        status="ok",
        origin=origin,
        source_validation=derived,
        documents=len(doc_ids),
        fragments=len(frag_meta),
        bundles=len(validated_bundles),
        diagnostics=(),
    )


def validate_records_file(root: Path, path: Path) -> dict[str, Any]:
    reason = protected_path_reason(root, path)
    if reason is not None:
        raise ExperimentError(
            "PROTECTED_PATH",
            f"records CLI cannot read protected path {reason}",
        )
    candidate = path if path.is_absolute() else root / path
    if not candidate.is_file():
        raise ExperimentError("MISSING_INPUT", f"records file is missing: {path}")
    payload = load_hybrid_records_bytes(candidate.read_bytes(), str(path))
    return validate_hybrid_records(payload, "records")


def emit_records_result(report: Mapping[str, Any], error: ExperimentError | None) -> int:
    sys.stdout.write(canonical_json_bytes(report).decode("utf-8"))
    if error is None:
        print(
            f"{RECORDS_MARKER} status={report['status']} "
            f"origin={report['provenance_origin']} "
            f"source_validation={report['source_validation']} "
            f"documents={report['documents']} bundles={report['bundles']}",
            file=sys.stderr,
        )
        return 0
    print(f"FAIL {error.diagnostic}: {error.detail}", file=sys.stderr)
    return 2 if error.diagnostic == "USAGE" else 1


def measured_ratio(correct: int, denominator: int) -> dict[str, Any]:
    if denominator == 0:
        return {
            "correct": 0,
            "denominator": 0,
            "value": None,
            "status": "not-measured",
        }
    return {
        "correct": correct,
        "denominator": denominator,
        "value": f"{correct}/{denominator}",
        "status": "measured",
    }


def e2e_block(tp: int, fp: int, fn: int, expected_n: int, predicted_n: int) -> dict[str, Any]:
    if expected_n == 0 and predicted_n == 0:
        return {
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "expected_n": 0,
            "predicted_n": 0,
            "value": None,
            "status": "not-measured",
        }
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "expected_n": expected_n,
        "predicted_n": predicted_n,
        "value": f"{tp}/{expected_n}",
        "status": "measured",
    }


def anchor_key(item: Mapping[str, Any]) -> tuple[tuple[str, int, int], ...]:
    anchors = item["anchors"]
    return tuple(
        sorted((str(row["fragment_id"]), int(row["start"]), int(row["end"])) for row in anchors)
    )


def key_json(key: tuple[tuple[str, int, int], ...]) -> list[list[Any]]:
    return [[fragment_id, start, end] for fragment_id, start, end in key]


def align(
    expected: Sequence[Mapping[str, Any]], predicted: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    exp_by: dict[tuple[tuple[str, int, int], ...], list[Mapping[str, Any]]] = defaultdict(list)
    pred_by: dict[tuple[tuple[str, int, int], ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in expected:
        exp_by[anchor_key(row)].append(row)
    for row in predicted:
        pred_by[anchor_key(row)].append(row)
    unique: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    unmatched_expected: list[str] = []
    unmatched_predicted: list[str] = []
    ambiguous: list[dict[str, Any]] = []
    for key in sorted(set(exp_by) | set(pred_by)):
        exp_rows = exp_by.get(key, [])
        pred_rows = pred_by.get(key, [])
        if len(exp_rows) == 1 and len(pred_rows) == 1:
            unique.append((exp_rows[0], pred_rows[0]))
            continue
        if not exp_rows:
            unmatched_predicted.extend(str(row["id"]) for row in pred_rows)
            continue
        if not pred_rows:
            unmatched_expected.extend(str(row["id"]) for row in exp_rows)
            continue
        ambiguous.append(
            {
                "key": key_json(key),
                "expected_ids": [str(row["id"]) for row in exp_rows],
                "predicted_ids": [str(row["id"]) for row in pred_rows],
            }
        )
    unique.sort(key=lambda pair: str(pair[0]["id"]))
    return {
        "unique": unique,
        "unmatched_expected": unmatched_expected,
        "unmatched_predicted": unmatched_predicted,
        "ambiguous": ambiguous,
    }


def slot_match(expected: Mapping[str, Any], predicted: Mapping[str, Any], slot: str) -> bool:
    return expected["fields"][slot]["value"] == predicted["fields"][slot]["value"]


def source_match(expected: Mapping[str, Any], predicted: Mapping[str, Any], slot: str) -> bool:
    return expected["fields"][slot]["source"] == predicted["fields"][slot]["source"]


def score_fields(
    expected_occs: Sequence[Mapping[str, Any]],
    unique: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
    comparer,
    slots: Sequence[str] = SLOTS,
) -> dict[str, Any]:
    by_id = {str(pair[0]["id"]): pair[1] for pair in unique}
    correct = 0
    denominator = len(expected_occs) * len(slots)
    for item in expected_occs:
        predicted = by_id.get(str(item["id"]))
        for slot in slots:
            if predicted is not None and comparer(item, predicted, slot):
                correct += 1
    return measured_ratio(correct, denominator)


def score_relations(
    expected: Mapping[str, Any],
    predicted: Mapping[str, Any],
    unique: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    id_map = {str(exp["id"]): str(pred["id"]) for exp, pred in unique}
    reverse = {pred: exp for exp, pred in id_map.items()}
    expected_rels = list(expected["relations"])
    predicted_rels = list(predicted["relations"])
    pred_keys: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in predicted_rels:
        pred_keys[(str(row["rel"]), str(row["from"]), str(row["to"]))] += 1
    tp = 0
    fn = 0
    eligible = 0
    eligible_correct = 0
    for row in expected_rels:
        frm = str(row["from"])
        to = str(row["to"])
        mapped = frm in id_map and to in id_map
        if mapped:
            eligible += 1
            key = (str(row["rel"]), id_map[frm], id_map[to])
            if pred_keys.get(key, 0) > 0:
                pred_keys[key] -= 1
                tp += 1
                eligible_correct += 1
            else:
                fn += 1
        else:
            fn += 1
    fp = sum(pred_keys.values())
    extra_aligned = 0
    for (_name, frm, to), count in pred_keys.items():
        if count and frm in reverse and to in reverse:
            extra_aligned += count
    conditional = measured_ratio(eligible_correct, eligible)
    conditional["extra_among_aligned"] = extra_aligned
    return e2e_block(tp, fp, fn, len(expected_rels), len(predicted_rels)), conditional


def bundle_exact(
    detection: Mapping[str, int],
    fields: Mapping[str, Any],
    provenance: Mapping[str, Any],
    unresolved: Mapping[str, Any],
    e2e: Mapping[str, Any],
    ambiguity: Mapping[str, Any],
) -> bool:
    if detection["fp"] or detection["fn"]:
        return False
    if ambiguity["groups"]:
        return False
    if fields["status"] == "measured" and fields["correct"] != fields["denominator"]:
        return False
    if provenance["status"] == "measured" and provenance["correct"] != provenance["denominator"]:
        return False
    if unresolved["status"] == "measured" and unresolved["correct"] != unresolved["denominator"]:
        return False
    if e2e["status"] == "measured" and (e2e["fp"] or e2e["fn"]):
        return False
    return True


def score_pair(expected_raw: Mapping[str, Any], predicted_raw: Mapping[str, Any]) -> dict[str, Any]:
    expected = validate_bundle(expected_raw, "expected")
    predicted = validate_bundle(predicted_raw, "predicted")
    aligned = align(expected["occurrences"], predicted["occurrences"])
    unique = aligned["unique"]
    detection = {
        "tp": len(unique),
        "fp": len(aligned["unmatched_predicted"]),
        "fn": len(aligned["unmatched_expected"]),
    }
    fields = score_fields(expected["occurrences"], unique, slot_match, SLOTS)
    provenance = score_fields(expected["occurrences"], unique, source_match, SOURCE_SLOTS)
    e2e, conditional = score_relations(expected, predicted, unique)
    unresolved_correct = 0
    for exp, pred in unique:
        if bool(exp["unresolved"]) == bool(pred["unresolved"]):
            unresolved_correct += 1
    unresolved = measured_ratio(unresolved_correct, len(unique))
    unresolved["predicted_resolved_when_expected_unresolved"] = sum(
        1 for exp, pred in unique if exp["unresolved"] and not pred["unresolved"]
    )
    ambiguity = {
        "groups": len(aligned["ambiguous"]),
        "expected_occurrences": sum(len(row["expected_ids"]) for row in aligned["ambiguous"]),
        "predicted_occurrences": sum(len(row["predicted_ids"]) for row in aligned["ambiguous"]),
        "items": aligned["ambiguous"],
    }
    exact = bundle_exact(detection, fields, provenance, unresolved, e2e, ambiguity)
    return {
        "detection": detection,
        "field_value": fields,
        "provenance": provenance,
        "relation_e2e": e2e,
        "relation_conditional": conditional,
        "ambiguity": ambiguity,
        "unresolved": unresolved,
        "bundle_exact": exact,
        "alignment": {
            "unique_pairs": [[str(a["id"]), str(b["id"])] for a, b in unique],
            "unmatched_expected": list(aligned["unmatched_expected"]),
            "unmatched_predicted": list(aligned["unmatched_predicted"]),
        },
    }


def local_focus_views(
    expected: Mapping[str, Any], predicted: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    focus_id = expected["focus_id"]
    focus = next(row for row in expected["occurrences"] if row["id"] == focus_id)
    key = anchor_key(focus)
    pred_rows = [row for row in predicted["occurrences"] if anchor_key(row) == key]
    exp_view = clone(expected)
    pred_view = clone(predicted)
    exp_view["occurrences"] = [clone(focus)]
    exp_view["relations"] = []
    pred_view["occurrences"] = clone(pred_rows)
    pred_view["relations"] = []
    if pred_rows:
        ids = {row["id"] for row in pred_rows}
        if pred_view["focus_id"] not in ids:
            pred_view["focus_id"] = pred_rows[0]["id"]
    return exp_view, pred_view


def score_scenario(scenario: Mapping[str, Any]) -> dict[str, Any]:
    expected = scenario["expected"]
    predicted = scenario["predicted"]
    hybrid = score_pair(expected, predicted)
    focus_exp, focus_pred = local_focus_views(expected, predicted)
    local = score_pair(focus_exp, focus_pred)
    return {
        "id": scenario["id"],
        "construction": scenario["construction"],
        "injected": scenario["injected"],
        "hybrid": hybrid,
        "local_focus": {
            "detection": local["detection"],
            "field_value": local["field_value"],
            "provenance": local["provenance"],
            "unresolved": local["unresolved"],
            "ambiguity": {
                "groups": local["ambiguity"]["groups"],
                "expected_occurrences": local["ambiguity"]["expected_occurrences"],
                "predicted_occurrences": local["ambiguity"]["predicted_occurrences"],
            },
            "bundle_exact": local["bundle_exact"],
            "alignment": local["alignment"],
        },
        "expected": expected,
        "predicted": predicted,
    }


def add_detection(total: dict[str, int], block: Mapping[str, int]) -> None:
    total["tp"] += block["tp"]
    total["fp"] += block["fp"]
    total["fn"] += block["fn"]


def add_ratio(total: dict[str, int], block: Mapping[str, Any]) -> None:
    if block["status"] == "measured":
        total["correct"] += int(block["correct"])
        total["denominator"] += int(block["denominator"])


def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    det = {"tp": 0, "fp": 0, "fn": 0}
    lf_det = {"tp": 0, "fp": 0, "fn": 0}
    fields = {"correct": 0, "denominator": 0}
    provenance = {"correct": 0, "denominator": 0}
    lf_fields = {"correct": 0, "denominator": 0}
    lf_prov = {"correct": 0, "denominator": 0}
    unresolved = {"correct": 0, "denominator": 0}
    e2e = {"tp": 0, "fp": 0, "fn": 0, "expected": 0, "predicted": 0}
    cond = {"correct": 0, "denominator": 0}
    amb_groups = 0
    exact = 0
    lf_exact = 0
    for row in rows:
        hybrid = row["hybrid"]
        local = row["local_focus"]
        add_detection(det, hybrid["detection"])
        add_detection(lf_det, local["detection"])
        add_ratio(fields, hybrid["field_value"])
        add_ratio(provenance, hybrid["provenance"])
        add_ratio(lf_fields, local["field_value"])
        add_ratio(lf_prov, local["provenance"])
        add_ratio(unresolved, hybrid["unresolved"])
        e2e_block_row = hybrid["relation_e2e"]
        e2e["tp"] += e2e_block_row["tp"]
        e2e["fp"] += e2e_block_row["fp"]
        e2e["fn"] += e2e_block_row["fn"]
        e2e["expected"] += int(e2e_block_row["expected_n"])
        e2e["predicted"] += int(e2e_block_row["predicted_n"])
        add_ratio(cond, hybrid["relation_conditional"])
        amb_groups += hybrid["ambiguity"]["groups"]
        exact += int(hybrid["bundle_exact"])
        lf_exact += int(local["bundle_exact"])
    bundles = len(rows)
    e2e_out = e2e_block(e2e["tp"], e2e["fp"], e2e["fn"], e2e["expected"], e2e["predicted"])
    hybrid_summary = {
        "detection": det,
        "field_value": measured_ratio(fields["correct"], fields["denominator"]),
        "provenance": measured_ratio(provenance["correct"], provenance["denominator"]),
        "relation_e2e": e2e_out,
        "relation_conditional": measured_ratio(cond["correct"], cond["denominator"]),
        "unresolved": measured_ratio(unresolved["correct"], unresolved["denominator"]),
        "ambiguity_groups": amb_groups,
        "bundle_exact": measured_ratio(exact, bundles),
        "occurrence_expected": fields["denominator"] // len(SLOTS) if SLOTS else 0,
        "bundles": bundles,
    }
    local_summary = {
        "detection": lf_det,
        "field_value": measured_ratio(lf_fields["correct"], lf_fields["denominator"]),
        "provenance": measured_ratio(lf_prov["correct"], lf_prov["denominator"]),
        "bundle_exact": measured_ratio(lf_exact, bundles),
        "bundles": bundles,
    }
    return {
        "hybrid": hybrid_summary,
        "local_focus": local_summary,
        "exact_bundle": hybrid_summary["bundle_exact"],
    }


def pred_missing_member() -> dict[str, Any]:
    return drop_occ(series_expected(), "occ-b")


def pred_extra_head_as_act() -> dict[str, Any]:
    out = clone(series_expected())
    src = head_src()
    out["occurrences"].append(
        occ(
            "occ-extra",
            [anchor(HEAD_FRAG, HEAD_SPAN)],
            kind=KIND_MEMBER,
            date=DATE_SERIES,
            number=NUM_SERIES,
            date_src=src,
            number_src=src,
        )
    )
    return out


def pred_wrong_field() -> dict[str, Any]:
    out = clone(agreement_expected())
    for row in out["occurrences"]:
        if row["id"] == "occ-b":
            row["fields"]["date"]["value"] = "1900-01-01"
    return out


def pred_wrong_relation() -> dict[str, Any]:
    out = clone(annex_expected())
    out["relations"][0]["rel"] = REL_REFERS
    return out


def pred_wrong_provenance() -> dict[str, Any]:
    out = clone(series_expected())
    for row in out["occurrences"]:
        own = clone(row["anchors"][0])
        row["fields"]["date"]["source"] = own
        row["fields"]["number"]["source"] = own
    return out


def pred_unavailable() -> dict[str, Any]:
    out = clone(series_expected())
    src = head_src()
    for row in out["occurrences"]:
        row["unresolved"] = False
        row["unresolved_reason"] = None
        row["fields"]["date"] = field(DATE_SERIES, src)
        row["fields"]["number"] = field(NUM_SERIES, src)
    out["relations"] = []
    return out


def expected_unavailable() -> dict[str, Any]:
    out = clone(series_expected())
    out["context_status"] = "unavailable"
    out["relations"] = []
    for row in out["occurrences"]:
        row["unresolved"] = True
        row["unresolved_reason"] = "unavailable-context"
        row["fields"]["date"] = field(None, None)
        row["fields"]["number"] = field(None, None)
    return out


def pred_swapped_kinds() -> dict[str, Any]:
    out = clone(repeat_expected())
    kinds = {row["id"]: row["fields"]["kind"]["value"] for row in out["occurrences"]}
    for row in out["occurrences"]:
        other = "occ-b" if row["id"] == "occ-a" else "occ-a"
        row["fields"]["kind"]["value"] = kinds[other]
    return out


def pred_duplicate_anchor() -> dict[str, Any]:
    base = agreement_expected()
    focus = clone(base["occurrences"][0])
    twin = clone(focus)
    twin["id"] = "occ-dup"
    twin["fields"]["kind"]["value"] = KIND_CONTRACT
    return bundle(
        bid="dup-pred",
        construction=base["construction"],
        focus_id="occ-a",
        context_status="available",
        declared_region=base["declared_region"],
        context_only=(),
        occs=(focus, twin),
        rels=(),
    )


def expected_single_focus() -> dict[str, Any]:
    base = agreement_expected()
    focus = clone(base["occurrences"][0])
    return bundle(
        bid="dup-exp",
        construction=base["construction"],
        focus_id="occ-a",
        context_status="available",
        declared_region=(AG_FRAG,),
        context_only=(),
        occs=(focus,),
        rels=(),
    )


def pred_missed_endpoint() -> dict[str, Any]:
    return drop_occ(agreement_expected(), "occ-b")


def scenarios() -> list[dict[str, Any]]:
    return [
        {
            "id": "series-correct",
            "construction": "shared-head-series",
            "injected": "none",
            "expected": series_expected(),
            "predicted": series_expected(),
        },
        {
            "id": "agreement-correct",
            "construction": "agreement-refers-to-contract",
            "injected": "none",
            "expected": agreement_expected(),
            "predicted": agreement_expected(),
        },
        {
            "id": "annex-correct",
            "construction": "annex-approved-by",
            "injected": "none",
            "expected": annex_expected(),
            "predicted": annex_expected(),
        },
        {
            "id": "alias-unresolved",
            "construction": "alias-this-ref-ambiguity",
            "injected": "none",
            "expected": alias_expected(),
            "predicted": alias_expected(),
        },
        {
            "id": "series-missing-member",
            "construction": "shared-head-series",
            "injected": "missing_occurrence",
            "expected": series_expected(),
            "predicted": pred_missing_member(),
        },
        {
            "id": "series-extra-head-as-act",
            "construction": "shared-head-series",
            "injected": "extra_occurrence",
            "expected": series_expected(),
            "predicted": pred_extra_head_as_act(),
        },
        {
            "id": "agreement-wrong-field",
            "construction": "agreement-refers-to-contract",
            "injected": "wrong_field",
            "expected": agreement_expected(),
            "predicted": pred_wrong_field(),
        },
        {
            "id": "annex-wrong-relation",
            "construction": "annex-approved-by",
            "injected": "wrong_relation",
            "expected": annex_expected(),
            "predicted": pred_wrong_relation(),
        },
        {
            "id": "series-wrong-provenance",
            "construction": "shared-head-series",
            "injected": "wrong_provenance",
            "expected": series_expected(),
            "predicted": pred_wrong_provenance(),
        },
        {
            "id": "series-unavailable-context",
            "construction": "shared-head-series",
            "injected": "unavailable_context",
            "expected": expected_unavailable(),
            "predicted": pred_unavailable(),
        },
        {
            "id": "repeat-values-distinct-spans",
            "construction": "agreement-refers-to-contract",
            "injected": "repeated_values",
            "expected": repeat_expected(),
            "predicted": pred_swapped_kinds(),
        },
        {
            "id": "duplicate-anchor-ambiguous",
            "construction": "agreement-refers-to-contract",
            "injected": "duplicate_anchor",
            "expected": expected_single_focus(),
            "predicted": pred_duplicate_anchor(),
        },
        {
            "id": "agreement-missed-endpoint",
            "construction": "agreement-refers-to-contract",
            "injected": "missed_endpoint",
            "expected": agreement_expected(),
            "predicted": pred_missed_endpoint(),
        },
    ]


def build_record() -> dict[str, Any]:
    rows = [score_scenario(item) for item in scenarios()]
    summary = summarize(rows)
    compact_rows = []
    for row in rows:
        compact_rows.append(
            {
                "id": row["id"],
                "construction": row["construction"],
                "injected": row["injected"],
                "hybrid": {
                    "detection": row["hybrid"]["detection"],
                    "field_value": row["hybrid"]["field_value"],
                    "provenance": row["hybrid"]["provenance"],
                    "relation_e2e": row["hybrid"]["relation_e2e"],
                    "relation_conditional": row["hybrid"]["relation_conditional"],
                    "ambiguity": {
                        "groups": row["hybrid"]["ambiguity"]["groups"],
                        "expected_occurrences": row["hybrid"]["ambiguity"]["expected_occurrences"],
                        "predicted_occurrences": row["hybrid"]["ambiguity"][
                            "predicted_occurrences"
                        ],
                    },
                    "unresolved": row["hybrid"]["unresolved"],
                    "bundle_exact": row["hybrid"]["bundle_exact"],
                    "alignment": row["hybrid"]["alignment"],
                },
                "local_focus": row["local_focus"],
                "expected": row["expected"],
                "predicted": row["predicted"],
            }
        )
    return {
        "schema": SCHEMA,
        "schema_version": 1,
        "lifecycle": "[proposed]",
        "authoritative": False,
        "human_adoption": "pending",
        "promotion": "none",
        "is_gold": False,
        "provenance": "synthetic",
        "not_human": True,
        "not_s03_metrics": True,
        "parser_implementation": "out-of-scope-M211",
        "frozen_pilot_untouched": True,
        "working_kind_field": (
            "kind is a synthetic working label, not adopted legal TYPE vocabulary"
        ),
        "alignment_policy": "local-anchor-identity-v1",
        "constructions": list(CONSTRUCTIONS),
        "scenario_count": len(compact_rows),
        "scenarios": compact_rows,
        "summary": summary,
        "comparison": {
            "disclaimer": (
                "Successor experiment measures for local-focus vs exact-bundle vs hybrid. "
                "Not S03 metrics."
            ),
            "local_focus": summary["local_focus"],
            "exact_bundle": summary["exact_bundle"],
            "hybrid": summary["hybrid"],
        },
        "limits": [
            "synthetic expected labels only",
            "provenance=synthetic",
            "not human, not gold, promotion=none",
            "shared head is a context source, not necessarily an act",
            "alignment by local anchor identity, independent of kind and values",
            "unmatched and duplicate-anchor ambiguity are explicit, not best-match-to-label",
            "empty denominator is not-measured, not perfect accuracy",
            "missed relation endpoints count as end-to-end FN",
            "conditional-on-correct-endpoints is a distinct plane",
            "correct kind with wrong inheritance is a provenance error",
            "unavailable context is not a human abstention",
            "not S03 metrics",
            "parser implementation remains M211",
            "no frozen M207 gate or pin is discharged",
            "no human stores or raw legal corpus",
        ],
        "non_claims": [
            "Does not measure legal correctness",
            "Does not adopt a successor schema or label inventory",
            "Does not release a human pilot or presentation",
            "Does not read or rewrite frozen S01/S02/S03 stores",
            "Does not reuse the frozen human-pass evaluation rates",
        ],
    }


def render(record: Mapping[str, Any]) -> bytes:
    return (json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_record(target: Path, payload: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_bytes(payload)
    tmp.replace(target)


def check_record(target: Path, payload: bytes) -> None:
    if not target.is_file():
        raise ExperimentError("MISSING_ARTIFACT", f"tracked experiment missing: {RECORD_REL}")
    if target.read_bytes() != payload:
        raise ExperimentError(
            "STALE_ARTIFACT",
            "tracked JSON is not the deterministic synthetic experiment projection",
        )


def summary_line(record: Mapping[str, Any]) -> str:
    hybrid = record["summary"]["hybrid"]
    det = hybrid["detection"]
    return (
        f"{MARKER} constructions={len(record['constructions'])} "
        f"scenarios={record['scenario_count']} "
        f"detection_tp={det['tp']} detection_fp={det['fp']} detection_fn={det['fn']} "
        f"field={hybrid['field_value']['value']} "
        f"provenance={hybrid['provenance']['value']} "
        f"rel_e2e={hybrid['relation_e2e']['value']} "
        f"rel_cond={hybrid['relation_conditional']['value']} "
        f"bundle_exact={hybrid['bundle_exact']['value']} "
        f"ambiguity_groups={hybrid['ambiguity_groups']}"
    )


def eval_protected_path_reason(root: Path, path: Path) -> str | None:
    """protected_path_reason plus the eval-only S03 report path.

    PROTECTED_RELS and protected_path_reason stay untouched so that
    --validate-records keeps its exact S05 behavior.
    """
    reason = protected_path_reason(root, path)
    if reason is not None:
        return reason
    raw = Path(path)
    bases: list[Path] = []
    for base in (root, ROOT):
        resolved_base = Path(base).resolve()
        if resolved_base not in bases:
            bases.append(resolved_base)
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append(raw)
        for base in bases:
            candidates.append(base / raw)
    resolved = [item.resolve() for item in candidates]
    names = {item.as_posix() for item in candidates}
    names.update(item.as_posix() for item in resolved)
    for rel in EVAL_EXTRA_PROTECTED_RELS:
        if rel in names or any(name.endswith("/" + rel) for name in names):
            return rel
        for base in bases:
            if (base / rel).resolve() in resolved:
                return rel
    return None


def bundles_by_id(doc: Mapping[str, Any], side: str) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(doc["bundles"]):
        bundle_id = str(raw["bundle_id"])
        if bundle_id in by_id:
            raise ExperimentError(
                "DUPLICATE_BUNDLE_ID",
                f"{side} bundles[{index}] repeats bundle_id {bundle_id}",
            )
        by_id[bundle_id] = dict(raw)
    return by_id


def pair_bundles(
    expected_doc: Mapping[str, Any], predicted_doc: Mapping[str, Any]
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], dict[str, Any]]:
    """Pair bundles by bundle_id only; unmatched ids never reach score_pair."""
    expected_by = bundles_by_id(expected_doc, "expected")
    predicted_by = bundles_by_id(predicted_doc, "predicted")
    matched_ids = sorted(set(expected_by) & set(predicted_by))
    matched = [(expected_by[bundle_id], predicted_by[bundle_id]) for bundle_id in matched_ids]
    alignment = {
        "matched": matched_ids,
        "expected_only": sorted(set(expected_by) - set(predicted_by)),
        "predicted_only": sorted(set(predicted_by) - set(expected_by)),
        "expected_bundles": len(expected_by),
        "predicted_bundles": len(predicted_by),
    }
    return matched, alignment


def local_focus_block(expected: Mapping[str, Any], predicted: Mapping[str, Any]) -> dict[str, Any]:
    """score_pair-compatible local-focus view, guarded for an empty bundle.

    The records validator accepts a bundle with zero occurrences, and
    local_focus_views would then raise StopIteration. Such a bundle is
    not-measured rather than an exception.
    """
    if not expected["occurrences"]:
        return {
            "status": "not-measured",
            "detection": {"tp": 0, "fp": 0, "fn": 0},
            "field_value": measured_ratio(0, 0),
            "provenance": measured_ratio(0, 0),
            "relation_e2e": e2e_block(0, 0, 0, 0, 0),
            "relation_conditional": measured_ratio(0, 0),
            "unresolved": measured_ratio(0, 0),
            "ambiguity": {
                "groups": 0,
                "expected_occurrences": 0,
                "predicted_occurrences": 0,
                "items": [],
            },
            "bundle_exact": False,
            "alignment": {
                "unique_pairs": [],
                "unmatched_expected": [],
                "unmatched_predicted": [],
            },
        }
    focus_expected, focus_predicted = local_focus_views(expected, predicted)
    pair = score_pair(focus_expected, focus_predicted)
    return {
        "status": "measured",
        "detection": pair["detection"],
        "field_value": pair["field_value"],
        "provenance": pair["provenance"],
        "relation_e2e": pair["relation_e2e"],
        "relation_conditional": pair["relation_conditional"],
        "unresolved": pair["unresolved"],
        "ambiguity": pair["ambiguity"],
        "bundle_exact": pair["bundle_exact"],
        "alignment": pair["alignment"],
    }


def metamorphic_container() -> dict[str, Any]:
    """Sibling evidence object; properties are wired in M207 S06 T02."""
    return {
        "evidence_class": "metamorphic",
        "properties": [],
        "properties_executed": 0,
        "properties_passed": 0,
        "verdict": measured_ratio(0, 0),
        "rules": ["properties are reserved here and populated in M207 S06 T02"],
    }


def invalid_metamorphic_container() -> dict[str, Any]:
    """Shape-only container: an invalid input executes no property and no metric."""
    return {
        "evidence_class": "metamorphic",
        "properties": [],
        "not_executed": "no property was executed because the input did not validate",
    }


def eval_status(metamorphic: Mapping[str, Any]) -> str:
    for row in metamorphic.get("properties", ()):  # pragma: no branch - empty in T01
        if row.get("status") == "failed":
            return "unstable"
    return "ok"


def eval_report(
    *,
    status: str,
    expected_origin: str | None,
    predicted_origin: str | None,
    differential: Mapping[str, Any] | None,
    metamorphic: Mapping[str, Any],
    diagnostics: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    return {
        "schema": EVAL_SCHEMA,
        "schema_version": EVAL_SCHEMA_VERSION,
        "status": status,
        "marker": EVAL_MARKER if status == "ok" else None,
        "lifecycle": ["proposed"],
        "authoritative": False,
        "is_gold": False,
        "not_human": True,
        "not_s03_metrics": True,
        "alignment_policy": "local-anchor-identity-v1",
        "reference_role": "harness-expected",
        "evidence_classes": ["differential", "metamorphic"],
        "expected_provenance_origin": expected_origin,
        "predicted_provenance_origin": predicted_origin,
        "differential": differential,
        "metamorphic": dict(metamorphic),
        "not_measured_policy": EVAL_NOT_MEASURED_POLICY,
        "limits": list(EVAL_LIMITS),
        "non_claims": list(EVAL_NON_CLAIMS),
        "diagnostics": [dict(row) for row in diagnostics],
    }


def invalid_eval_report(error: ExperimentError) -> dict[str, Any]:
    return eval_report(
        status="invalid",
        expected_origin=None,
        predicted_origin=None,
        differential=None,
        metamorphic=invalid_metamorphic_container(),
        diagnostics=(({"code": error.diagnostic, "detail": error.detail}),),
    )


def load_eval_records(root: Path, path: Path, side: str) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate = path if path.is_absolute() else root / path
    if not candidate.is_file():
        raise ExperimentError("MISSING_INPUT", f"eval {side} file is missing: {path}")
    payload = load_hybrid_records_bytes(candidate.read_bytes(), f"{side} {path}")
    return payload, validate_hybrid_records(payload, f"{side} {path}")


def evaluate_records(root: Path, expected_path: Path, predicted_path: Path) -> dict[str, Any]:
    """Read-only differential evaluation of two validated records files."""
    for side, path in (("expected", expected_path), ("predicted", predicted_path)):
        reason = eval_protected_path_reason(root, Path(path))
        if reason is not None:
            raise ExperimentError(
                "PROTECTED_PATH",
                f"eval CLI cannot read protected {side} path {reason}",
            )
    expected_doc, expected_meta = load_eval_records(root, Path(expected_path), "expected")
    predicted_doc, predicted_meta = load_eval_records(root, Path(predicted_path), "predicted")
    matched, alignment = pair_bundles(expected_doc, predicted_doc)
    rows = [
        {
            "hybrid": score_pair(exp_bundle, pred_bundle),
            "local_focus": local_focus_block(exp_bundle, pred_bundle),
        }
        for exp_bundle, pred_bundle in matched
    ]
    metamorphic = metamorphic_container()
    differential = {
        "evidence_class": "differential",
        "planes": summarize(rows),
        "bundle_alignment": alignment,
    }
    return eval_report(
        status=eval_status(metamorphic),
        expected_origin=expected_meta["provenance_origin"],
        predicted_origin=predicted_meta["provenance_origin"],
        differential=differential,
        metamorphic=metamorphic,
        diagnostics=(),
    )


def eval_summary_line(report: Mapping[str, Any]) -> str:
    differential = report["differential"]
    hybrid = differential["planes"]["hybrid"]
    alignment = differential["bundle_alignment"]
    return (
        f"{EVAL_MARKER} status={report['status']} "
        f"matched={len(alignment['matched'])} "
        f"expected_only={len(alignment['expected_only'])} "
        f"predicted_only={len(alignment['predicted_only'])} "
        f"bundle_exact={hybrid['bundle_exact']['value']} "
        f"field={hybrid['field_value']['value']} "
        f"provenance={hybrid['provenance']['value']} "
        f"rel_e2e={hybrid['relation_e2e']['value']} "
        f"rel_cond={hybrid['relation_conditional']['value']} "
        f"unresolved={hybrid['unresolved']['value']} "
        f"ambiguity_groups={hybrid['ambiguity_groups']}"
    )


def emit_eval_result(report: Mapping[str, Any], error: ExperimentError | None) -> int:
    sys.stdout.write(canonical_json_bytes(report).decode("utf-8"))
    if error is not None:
        print(f"FAIL {error.diagnostic}: {error.detail}", file=sys.stderr)
        return 2 if error.diagnostic == "USAGE" else 1
    if report["status"] == "unstable":
        print(
            "FAIL UNSTABLE: metamorphic property failed; differential planes are "
            "still printed on stdout",
            file=sys.stderr,
        )
        return 1
    print(eval_summary_line(report), file=sys.stderr)
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    parser.add_argument(
        "--check",
        action="store_true",
        help="read-only compare against the tracked artifact (default)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the tracked artifact; refused unless explicitly passed",
    )
    parser.add_argument(
        "--validate-records",
        metavar="PATH",
        default=None,
        help="read-only validate m207-hybrid-records/v1 JSON; never writes",
    )
    parser.add_argument(
        "--evaluate-records",
        nargs=2,
        metavar=("EXPECTED", "PREDICTED"),
        default=None,
        help="read-only evaluate two m207-hybrid-records/v1 files; never writes",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    if args.evaluate_records is not None:
        if args.write or args.check or args.validate_records is not None:
            error = ExperimentError(
                "USAGE",
                "eval CLI is read-only; do not combine --evaluate-records with "
                "--write, --check or --validate-records",
            )
            return emit_eval_result(invalid_eval_report(error), error)
        expected_path, predicted_path = args.evaluate_records
        try:
            report = evaluate_records(root, Path(expected_path), Path(predicted_path))
        except ExperimentError as exc:
            return emit_eval_result(invalid_eval_report(exc), exc)
        except Exception as exc:  # noqa: BLE001 - fail closed, never traceback
            error = ExperimentError(
                "MALFORMED_REF",
                f"eval input raised unexpected {type(exc).__name__}: {exc}",
            )
            return emit_eval_result(invalid_eval_report(error), error)
        return emit_eval_result(report, None)
    if args.validate_records is not None:
        if args.write:
            error = ExperimentError(
                "USAGE",
                "records CLI is read-only; do not pass --write with --validate-records",
            )
            return emit_records_result(invalid_records_report(error), error)
        try:
            report = validate_records_file(root, Path(args.validate_records))
        except ExperimentError as exc:
            return emit_records_result(invalid_records_report(exc), exc)
        except Exception as exc:  # noqa: BLE001 - fail closed, never traceback
            error = ExperimentError(
                "MALFORMED_REF",
                f"records input raised unexpected {type(exc).__name__}: {exc}",
            )
            return emit_records_result(invalid_records_report(error), error)
        return emit_records_result(report, None)
    if args.write and args.check:
        print("FAIL USAGE: pass only one of --check or --write", file=sys.stderr)
        return 2
    try:
        record = build_record()
        payload = render(record)
    except ExperimentError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        return 1
    target = root / RECORD_REL
    if args.write:
        write_record(target, payload)
        print(f"{summary_line(record)} wrote={RECORD_REL}")
        return 0
    try:
        check_record(target, payload)
    except ExperimentError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        return 1
    print(f"{summary_line(record)} drift=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

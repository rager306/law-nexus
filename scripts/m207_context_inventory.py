#!/usr/bin/env python3
"""Operator-only context inventory for the frozen M207 40-case draw.

This is **not** a coder kit, not gold, not a human-acceptance mint, and not a
rewrite of the frozen seed, S01 codebook, unit diagnosis, or closed kit schema.

It projects each pilot case's original fragment-local half-open BYTE span
together with ordered, same-document context references for diagnosed edition
series. Orphan heads stay unresolved. Other truncation flags stay
requires-review. Nothing else is declared human-ready.

Modes:
  --check  (default)  re-derive and compare the tracked JSON; missing/stale
                      fails closed; never writes
  --write             write prd/migration/rust-evidence/m207-context-inventory.json

Marker: M207_CONTEXT_INVENTORY_OK
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
MARKER = "M207_CONTEXT_INVENTORY_OK"
SCHEMA = "m207-context-inventory/v1"
RECORD_REL = "prd/migration/rust-evidence/m207-context-inventory.json"
SEED_REL = "prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json"
PILOT_REL = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"
DIAG_REL = "prd/migration/rust-evidence/m207-unit-diagnosis.json"
FIX_REL = "crates/ln-decode/tests/fixtures/npa-lawref"

SEED_SCHEMA = "npa-lawref-sample/v1"
PILOT_SCHEMA = "m207-s01-pilot-cases/v1"
DIAG_SCHEMA = "m207-unit-diagnosis/v1"

ELIG_SERIES = "diagnosed-series-context-only"
ELIG_ORPHAN = "unavailable-for-coding"
ELIG_REVIEW = "requires-review"
ELIG_INVENTORY = "operator-inventory-only"

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "text",
        "joined_preview",
        "preview",
        "raw",
        "genre",
        "coding_verdict",
        "type",
        "TYPE",
        "type_label",
        "answer",
        "model_answer",
        "predicted_type",
        "legal_label",
    }
)


class InventoryError(Exception):
    def __init__(self, diagnostic: str, detail: str) -> None:
        super().__init__(f"{diagnostic}: {detail}")
        self.diagnostic = diagnostic
        self.detail = detail


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InventoryError("SOURCE_SHAPE", f"{label} must be a JSON object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise InventoryError("SOURCE_SHAPE", f"{label} must be a JSON array")
    return value


def _require_keys(payload: Mapping[str, Any], keys: Sequence[str], label: str) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise InventoryError("SOURCE_SHAPE", f"{label} missing keys {missing}")


def _require_str(payload: Mapping[str, Any], key: str, label: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value:
        raise InventoryError("SOURCE_SHAPE", f"{label}.{key} must be a non-empty string")
    return value


def _require_int(payload: Mapping[str, Any], key: str, label: str) -> int:
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise InventoryError("SOURCE_SHAPE", f"{label}.{key} must be an integer")
    return value


def load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise InventoryError("MISSING_SOURCE", f"{label} is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InventoryError("SOURCE_SHAPE", f"{label} is not valid JSON: {exc}") from exc
    return _require_dict(payload, label)


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


def load_seed(root: Path) -> dict[str, Any]:
    payload = load_json(root / SEED_REL, "M199 seed manifest")
    _require_keys(payload, ("schema", "documents", "fragments"), "seed")
    if payload["schema"] != SEED_SCHEMA:
        raise InventoryError("SOURCE_SHAPE", f"seed schema must be {SEED_SCHEMA}")
    documents = _require_list(payload["documents"], "seed.documents")
    fragments = _require_list(payload["fragments"], "seed.fragments")
    if not documents or not fragments:
        raise InventoryError("SOURCE_SHAPE", "seed documents/fragments must be non-empty")
    doc_by_id: dict[str, dict[str, Any]] = {}
    for index, document in enumerate(documents):
        rec = _require_dict(document, f"seed.documents[{index}]")
        _require_keys(
            rec,
            ("doc_id", "source_path", "source_sha256", "fragment_ids"),
            f"seed.documents[{index}]",
        )
        doc_id = _require_str(rec, "doc_id", f"seed.documents[{index}]")
        if doc_id in doc_by_id:
            raise InventoryError("SOURCE_SHAPE", f"duplicate seed doc_id {doc_id}")
        _require_list(rec["fragment_ids"], f"seed.documents[{index}].fragment_ids")
        doc_by_id[doc_id] = rec
    frag_by_id: dict[str, dict[str, Any]] = {}
    for index, fragment in enumerate(fragments):
        rec = _require_dict(fragment, f"seed.fragments[{index}]")
        _require_keys(
            rec,
            ("id", "file", "doc_id", "byte_len", "source_block_index"),
            f"seed.fragments[{index}]",
        )
        frag_id = _require_str(rec, "id", f"seed.fragments[{index}]")
        if frag_id in frag_by_id:
            raise InventoryError("SOURCE_SHAPE", f"duplicate seed fragment id {frag_id}")
        if rec["doc_id"] not in doc_by_id:
            raise InventoryError("SOURCE_SHAPE", f"seed fragment {frag_id} has unknown doc_id")
        _require_int(rec, "byte_len", f"seed.fragments[{index}]")
        _require_int(rec, "source_block_index", f"seed.fragments[{index}]")
        frag_by_id[frag_id] = rec
    payload["_doc_by_id"] = doc_by_id
    payload["_frag_by_id"] = frag_by_id
    return payload


def load_pilot(root: Path) -> dict[str, Any]:
    payload = load_json(root / PILOT_REL, "M207 pilot cases")
    _require_keys(payload, ("schema", "cases"), "pilot")
    if payload["schema"] != PILOT_SCHEMA:
        raise InventoryError("SOURCE_SHAPE", f"pilot schema must be {PILOT_SCHEMA}")
    cases = _require_list(payload["cases"], "pilot.cases")
    if not cases:
        raise InventoryError("SOURCE_SHAPE", "pilot.cases must be non-empty")
    seen: set[str] = set()
    for index, case in enumerate(cases):
        rec = _require_dict(case, f"pilot.cases[{index}]")
        _require_keys(
            rec,
            (
                "case_id",
                "fragment_id",
                "doc_id",
                "start",
                "end",
                "byte_len",
                "source_sha256",
                "source_block_index",
            ),
            f"pilot.cases[{index}]",
        )
        case_id = _require_str(rec, "case_id", f"pilot.cases[{index}]")
        if case_id in seen:
            raise InventoryError("DUPLICATE_CASE", f"case_id {case_id} occurs more than once")
        seen.add(case_id)
        _require_int(rec, "start", f"pilot.cases[{index}]")
        _require_int(rec, "end", f"pilot.cases[{index}]")
        _require_int(rec, "byte_len", f"pilot.cases[{index}]")
        _require_int(rec, "source_block_index", f"pilot.cases[{index}]")
    if "case_count" in payload:
        declared = _require_int(payload, "case_count", "pilot")
        if declared != len(cases):
            raise InventoryError(
                "CASE_COUNT",
                f"pilot.case_count={declared} does not match len(cases)={len(cases)}",
            )
    payload["_case_ids"] = seen
    return payload


def load_diagnosis(root: Path) -> dict[str, Any]:
    payload = load_json(root / DIAG_REL, "M207 unit diagnosis")
    _require_keys(payload, ("schema", "fragments", "edition_series"), "diagnosis")
    if payload["schema"] != DIAG_SCHEMA:
        raise InventoryError("SOURCE_SHAPE", f"diagnosis schema must be {DIAG_SCHEMA}")
    fragments = _require_list(payload["fragments"], "diagnosis.fragments")
    series_rows = _require_list(payload["edition_series"], "diagnosis.edition_series")
    if not fragments:
        raise InventoryError("SOURCE_SHAPE", "diagnosis.fragments must be non-empty")
    frag_by_id: dict[str, dict[str, Any]] = {}
    for index, fragment in enumerate(fragments):
        rec = _require_dict(fragment, f"diagnosis.fragments[{index}]")
        _require_keys(
            rec,
            (
                "fragment_id",
                "doc_id",
                "byte_len",
                "text_sha256",
                "trunc_flags",
                "source_block_index",
            ),
            f"diagnosis.fragments[{index}]",
        )
        frag_id = _require_str(rec, "fragment_id", f"diagnosis.fragments[{index}]")
        if frag_id in frag_by_id:
            raise InventoryError("SOURCE_SHAPE", f"duplicate diagnosis fragment {frag_id}")
        flags = rec["trunc_flags"]
        if not isinstance(flags, list) or any(not isinstance(flag, str) for flag in flags):
            raise InventoryError(
                "SOURCE_SHAPE",
                f"diagnosis.fragments[{index}].trunc_flags must be a string array",
            )
        frag_by_id[frag_id] = rec
    series_by_frag: dict[str, dict[str, Any]] = {}
    for index, series in enumerate(series_rows):
        rec = _require_dict(series, f"diagnosis.edition_series[{index}]")
        _require_keys(
            rec,
            ("doc_id", "fragment_ids", "block_indices", "cross_block_text_anchor"),
            f"diagnosis.edition_series[{index}]",
        )
        if rec["cross_block_text_anchor"] is not False:
            raise InventoryError(
                "CROSS_BLOCK_TEXT_ANCHOR",
                f"diagnosis series {index} claims a cross-block TextAnchor",
            )
        ids = _require_list(rec["fragment_ids"], f"diagnosis.edition_series[{index}].fragment_ids")
        if len(ids) < 2 or any(not isinstance(item, str) or not item for item in ids):
            raise InventoryError(
                "SOURCE_SHAPE",
                f"diagnosis.edition_series[{index}].fragment_ids must name >=2 members",
            )
        blocks = _require_list(
            rec["block_indices"], f"diagnosis.edition_series[{index}].block_indices"
        )
        if len(blocks) != len(ids):
            raise InventoryError(
                "SOURCE_SHAPE",
                f"diagnosis.edition_series[{index}] block_indices length mismatch",
            )
        for frag_id in ids:
            if frag_id in series_by_frag:
                raise InventoryError(
                    "SOURCE_SHAPE",
                    f"fragment {frag_id} belongs to more than one diagnosed series",
                )
            series_by_frag[frag_id] = rec
    payload["_frag_by_id"] = frag_by_id
    payload["_series_by_frag"] = series_by_frag
    return payload


def fragment_bytes(root: Path, seed_frag: Mapping[str, Any]) -> bytes:
    rel = Path(FIX_REL) / seed_frag["file"]
    path = root / rel
    if not path.is_file():
        raise InventoryError("MISSING_FRAGMENT", f"fixture missing: {rel.as_posix()}")
    return path.read_bytes()


def local_ref(
    *,
    fragment_id: str,
    doc_id: str,
    seed_frag: Mapping[str, Any],
    raw: bytes,
    digest: str,
    start: int,
    end: int,
    role: str | None = None,
) -> dict[str, Any]:
    if not utf8_span_ok(raw, start, end):
        raise InventoryError(
            "SPAN_INVALID",
            f"{fragment_id} span [{start},{end}) is not a fragment-local UTF-8 BYTE range",
        )
    if end - start != len(raw[start:end]):
        raise InventoryError("SPAN_INVALID", f"{fragment_id} span length drifted")
    rec: dict[str, Any] = {
        "fragment_id": fragment_id,
        "doc_id": doc_id,
        "fixture_rel": f"{FIX_REL}/{seed_frag['file']}",
        "text_sha256": digest,
        "byte_len": len(raw),
        "source_block_index": seed_frag["source_block_index"],
        "span": {
            "end": end,
            "half_open": True,
            "start": start,
            "unit": "byte",
        },
    }
    if role is not None:
        rec["role"] = role
    return rec


def classify(
    *,
    series: Mapping[str, Any] | None,
    trunc_flags: Sequence[str],
) -> tuple[str, dict[str, Any] | None]:
    if series is not None:
        return ELIG_SERIES, None
    if "starts-ot-date" in trunc_flags:
        return ELIG_ORPHAN, {
            "reason": "orphan-tail-head-not-proven-by-harvested-seed",
            "status": "unresolved",
        }
    if trunc_flags:
        return ELIG_REVIEW, None
    return ELIG_INVENTORY, None


def walk_forbidden_keys(value: Any, trail: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_PAYLOAD_KEYS:
                raise InventoryError(
                    "LABEL_LEAK",
                    f"operator inventory must not carry {key!r} at {trail}",
                )
            walk_forbidden_keys(child, f"{trail}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            walk_forbidden_keys(child, f"{trail}[{index}]")


def assert_no_raw_text(record: Mapping[str, Any], texts: Sequence[bytes]) -> None:
    blob = json.dumps(record, ensure_ascii=False, sort_keys=True)
    for raw in texts:
        sample = raw.decode("utf-8")
        if sample and sample in blob:
            raise InventoryError(
                "RAW_TEXT_LEAK",
                "operator inventory must not embed fixture text",
            )


def build(root: Path) -> dict[str, Any]:
    seed = load_seed(root)
    pilot = load_pilot(root)
    diagnosis = load_diagnosis(root)
    seed_docs: dict[str, dict[str, Any]] = seed["_doc_by_id"]
    seed_frags: dict[str, dict[str, Any]] = seed["_frag_by_id"]
    diag_frags: dict[str, dict[str, Any]] = diagnosis["_frag_by_id"]
    series_by_frag: dict[str, dict[str, Any]] = diagnosis["_series_by_frag"]

    cases_out: list[dict[str, Any]] = []
    referenced_raw: dict[str, bytes] = {}
    text_groups: dict[str, list[str]] = defaultdict(list)

    for case in pilot["cases"]:
        case_id = case["case_id"]
        frag_id = _require_str(case, "fragment_id", case_id)
        if frag_id not in seed_frags:
            raise InventoryError("MISSING_FRAGMENT", f"{case_id} fragment {frag_id} not in seed")
        if frag_id not in diag_frags:
            raise InventoryError(
                "MISSING_FRAGMENT",
                f"{case_id} fragment {frag_id} not in diagnosis",
            )
        seed_frag = seed_frags[frag_id]
        diag_frag = diag_frags[frag_id]
        doc_id = _require_str(case, "doc_id", case_id)
        if doc_id != seed_frag["doc_id"] or doc_id != diag_frag["doc_id"]:
            raise InventoryError("DOC_MISMATCH", f"{case_id} doc_id does not match seed/diagnosis")
        document = seed_docs[doc_id]
        if case["source_sha256"] != document["source_sha256"]:
            raise InventoryError(
                "WRONG_HASH",
                f"{case_id} source_sha256 does not match seed document",
            )
        if case["source_block_index"] != seed_frag["source_block_index"]:
            raise InventoryError(
                "SOURCE_SHAPE",
                f"{case_id} source_block_index does not match seed",
            )
        if seed_frag["source_block_index"] != diag_frag["source_block_index"]:
            raise InventoryError(
                "SOURCE_SHAPE",
                f"{frag_id} source_block_index seed/diagnosis mismatch",
            )
        raw = fragment_bytes(root, seed_frag)
        digest = sha256_bytes(raw)
        if digest != diag_frag["text_sha256"]:
            raise InventoryError("WRONG_HASH", f"{frag_id} fixture hash does not match diagnosis")
        if len(raw) != case["byte_len"] or len(raw) != seed_frag["byte_len"]:
            raise InventoryError("BYTE_LEN_MISMATCH", f"{case_id} byte_len does not match fixture")
        if len(raw) != diag_frag["byte_len"]:
            raise InventoryError(
                "BYTE_LEN_MISMATCH",
                f"{frag_id} diagnosis byte_len does not match fixture",
            )
        start = case["start"]
        end = case["end"]
        if start != 0 or end != len(raw):
            # Preserve the original case span; still reject anything outside the file.
            if start < 0 or end > len(raw) or start >= end:
                raise InventoryError(
                    "SPAN_INVALID",
                    f"{case_id} original span [{start},{end}) is not inside the fixture",
                )
        referenced_raw[frag_id] = raw
        text_groups[digest].append(case_id)
        cases_out.append(
            {
                "_case": case,
                "_seed_frag": seed_frag,
                "_diag_frag": diag_frag,
                "_raw": raw,
                "_digest": digest,
                "case_id": case_id,
                "focus": local_ref(
                    fragment_id=frag_id,
                    doc_id=doc_id,
                    seed_frag=seed_frag,
                    raw=raw,
                    digest=digest,
                    start=start,
                    end=end,
                ),
            }
        )

    duplicate_map: dict[str, list[str]] = {}
    for _digest, ids in text_groups.items():
        if len(ids) > 1:
            for case_id in ids:
                duplicate_map[case_id] = [other for other in ids if other != case_id]

    public_cases: list[dict[str, Any]] = []
    for item in cases_out:
        case_id = item["case_id"]
        focus = item["focus"]
        frag_id = focus["fragment_id"]
        diag_frag = item["_diag_frag"]
        series = series_by_frag.get(frag_id)
        trunc_flags = list(diag_frag["trunc_flags"])
        eligibility, unresolved = classify(series=series, trunc_flags=trunc_flags)
        context_refs: list[dict[str, Any]] = []
        series_out: dict[str, Any] | None = None
        if series is not None:
            member_ids = list(series["fragment_ids"])
            member_docs: set[str] = set()
            ordered_blocks: list[int] = []
            for member_id in member_ids:
                if member_id not in seed_frags or member_id not in diag_frags:
                    raise InventoryError(
                        "MISSING_FRAGMENT",
                        f"series member {member_id} is not in seed/diagnosis",
                    )
                member_seed = seed_frags[member_id]
                member_diag = diag_frags[member_id]
                member_doc = member_seed["doc_id"]
                member_docs.add(member_doc)
                if member_doc != series["doc_id"] or member_doc != member_diag["doc_id"]:
                    raise InventoryError(
                        "CROSS_DOCUMENT_SERIES",
                        f"series member {member_id} is not same-document as {series['doc_id']}",
                    )
                if member_id in referenced_raw:
                    member_raw = referenced_raw[member_id]
                else:
                    member_raw = fragment_bytes(root, member_seed)
                    referenced_raw[member_id] = member_raw
                member_digest = sha256_bytes(member_raw)
                if member_digest != member_diag["text_sha256"]:
                    raise InventoryError(
                        "WRONG_HASH",
                        f"series member {member_id} fixture hash does not match diagnosis",
                    )
                if (
                    len(member_raw) != member_seed["byte_len"]
                    or len(member_raw) != member_diag["byte_len"]
                ):
                    raise InventoryError(
                        "BYTE_LEN_MISMATCH",
                        f"series member {member_id} byte_len does not match fixture",
                    )
                if member_seed["source_block_index"] != member_diag["source_block_index"]:
                    raise InventoryError(
                        "SOURCE_SHAPE",
                        f"series member {member_id} source_block_index mismatch",
                    )
                ordered_blocks.append(member_seed["source_block_index"])
                if member_id == frag_id:
                    continue
                context_refs.append(
                    local_ref(
                        fragment_id=member_id,
                        doc_id=member_doc,
                        seed_frag=member_seed,
                        raw=member_raw,
                        digest=member_digest,
                        start=0,
                        end=len(member_raw),
                        role="series-member",
                    )
                )
            if len(member_docs) != 1:
                raise InventoryError(
                    "CROSS_DOCUMENT_SERIES",
                    f"series for {frag_id} spans documents {sorted(member_docs)}",
                )
            if ordered_blocks != list(series["block_indices"]):
                raise InventoryError(
                    "SOURCE_SHAPE",
                    f"series {member_ids} block_indices do not match seed order",
                )
            series_out = {
                "block_indices": list(series["block_indices"]),
                "cross_block_text_anchor": False,
                "display_join_only": True,
                "doc_id": series["doc_id"],
                "fragment_ids": member_ids,
                "kind": "diagnosed-same-document",
                "member_count": len(member_ids),
            }

        public_cases.append(
            {
                "case_id": case_id,
                "context_refs": context_refs,
                "duplicate_text_case_ids": duplicate_map.get(case_id, []),
                "eligibility": eligibility,
                "focus": focus,
                "series": series_out,
                "truncation_flags": trunc_flags,
                "unresolved_head": unresolved,
            }
        )

    unique_texts = len(text_groups)
    duplicate_groups = sum(1 for ids in text_groups.values() if len(ids) > 1)
    duplicate_cases = sum(len(ids) for ids in text_groups.values() if len(ids) > 1)
    series_cases = sum(1 for rec in public_cases if rec["eligibility"] == ELIG_SERIES)
    orphan_cases = sum(1 for rec in public_cases if rec["eligibility"] == ELIG_ORPHAN)
    review_cases = sum(1 for rec in public_cases if rec["eligibility"] == ELIG_REVIEW)
    inventory_only = sum(1 for rec in public_cases if rec["eligibility"] == ELIG_INVENTORY)
    context_ref_count = sum(len(rec["context_refs"]) for rec in public_cases)

    record = {
        "adaptation": {
            "coding_unit": (
                "one complete reference occurrence, or one complete edition-list "
                "series diagnosed across adjacent same-document blocks"
            ),
            "context": "ordered fragment-local refs; display join only; never a merged span",
            "do_not_mutate_frozen_kit_schema": True,
            "do_not_rewrite_m207_codebook": True,
            "keep_frozen_seed": True,
            "not_coder_facing": True,
            "not_gold": True,
            "not_human_acceptance": True,
        },
        "audience": "operator",
        "authoritative": False,
        "cases": public_cases,
        "coder_facing": False,
        "counts": {
            "cases": len(public_cases),
            "coder_facing_cases": 0,
            "context_refs": context_ref_count,
            "cross_block_text_anchor": 0,
            "diagnosed_series_cases": series_cases,
            "duplicate_text_cases": duplicate_cases,
            "duplicate_text_groups": duplicate_groups,
            "human_ready_cases": 0,
            "operator_inventory_only_cases": inventory_only,
            "orphan_unresolved_cases": orphan_cases,
            "referenced_fragments": len(referenced_raw),
            "truncation_requires_review_cases": review_cases,
            "unique_case_ids": len(public_cases),
            "unique_focus_fragments": len({rec["focus"]["fragment_id"] for rec in public_cases}),
            "unique_focus_texts": unique_texts,
        },
        "frozen_pins": {
            "m199_manifest": {"path": SEED_REL, "sha256": sha256_file(root / SEED_REL)},
            "m207_pilot_cases": {"path": PILOT_REL, "sha256": sha256_file(root / PILOT_REL)},
            "m207_unit_diagnosis": {"path": DIAG_REL, "sha256": sha256_file(root / DIAG_REL)},
        },
        "human_adoption": "pending",
        "human_ready": False,
        "lifecycle": "[bounded]",
        "non_claims": [
            "not gold",
            "not a human pilot",
            "not coder-facing",
            "not human acceptance",
            "not a rewrite of the frozen 180-fragment seed",
            "not a mutation of the closed kit schema",
            "not a cross-block TextAnchor",
            "not predicted TYPE or legal labels",
            "not raw fixture text",
            "not every remaining case is human-ready",
        ],
        "operator_only": True,
        "runtime_stop_active": True,
        "schema": SCHEMA,
        "schema_version": 1,
    }
    walk_forbidden_keys(record, "inventory")
    assert_no_raw_text(record, list(referenced_raw.values()))
    if record["counts"]["unique_case_ids"] != len(public_cases):
        raise InventoryError("DUPLICATE_CASE", "case_id set drifted during projection")
    if "case_count" in pilot and pilot["case_count"] != len(public_cases):
        raise InventoryError(
            "CASE_COUNT",
            f"projected {len(public_cases)} cases, pilot.case_count={pilot['case_count']}",
        )
    return record


def render(record: dict[str, Any]) -> bytes:
    return (json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_record(target: Path, payload: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_bytes(payload)
    tmp.replace(target)


def check_record(target: Path, payload: bytes) -> None:
    if not target.is_file():
        raise InventoryError("MISSING_ARTIFACT", f"tracked inventory missing: {RECORD_REL}")
    if target.read_bytes() != payload:
        raise InventoryError(
            "STALE_ARTIFACT",
            "tracked JSON is not the deterministic operator inventory projection",
        )


def summary_line(record: dict[str, Any]) -> str:
    counts = record["counts"]
    return (
        f"{MARKER} cases={counts['cases']} unique_ids={counts['unique_case_ids']} "
        f"unique_texts={counts['unique_focus_texts']} series={counts['diagnosed_series_cases']} "
        f"orphan={counts['orphan_unresolved_cases']} review={counts['truncation_requires_review_cases']} "
        f"inventory_only={counts['operator_inventory_only_cases']} "
        f"dup_groups={counts['duplicate_text_groups']} context_refs={counts['context_refs']} "
        f"human_ready={counts['human_ready_cases']}"
    )


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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.write and args.check:
        print("FAIL USAGE: pass only one of --check or --write", file=sys.stderr)
        return 2
    root = Path(args.root).resolve()
    try:
        record = build(root)
        payload = render(record)
    except InventoryError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        return 1
    target = root / RECORD_REL
    if args.write:
        write_record(target, payload)
        print(f"{summary_line(record)} wrote={RECORD_REL}")
        return 0
    try:
        check_record(target, payload)
    except InventoryError as exc:
        print(f"FAIL {exc.diagnostic}: {exc.detail}", file=sys.stderr)
        return 1
    print(f"{summary_line(record)} drift=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

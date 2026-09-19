#!/usr/bin/env python3
"""Offline unit diagnosis for the frozen M199 npa-lawref seed (M207 overlay).

This is **not** a coder, not gold, not a Pullenti port, and not a rewrite of
the frozen 180-fragment seed or the M207 S01/S02 codebook.

It classifies each tracked fixture as a coding-unit candidate and records
WordML-block continuity inside one document version. Adjacent blocks may be
*diagnosed* as one edition-list series; they are never concatenated into a
cross-block TextAnchor (D385).

Modes:
  check  — re-derive the tracked JSON byte-for-byte
  run    — write prd/migration/rust-evidence/m207-unit-diagnosis.json
  report — print a short human table to stdout (no write)

Marker: M207_UNIT_DIAGNOSIS_OK
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MARKER = "M207_UNIT_DIAGNOSIS_OK"
SCHEMA = "m207-unit-diagnosis/v1"
RECORD_REL = "prd/migration/rust-evidence/m207-unit-diagnosis.json"
MANIFEST_REL = "prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json"
PILOT_REL = "prd/migration/rust-evidence/m207-s01-pilot-cases.json"
FIX_REL = "crates/ln-decode/tests/fixtures/npa-lawref"

OT_DATE = re.compile(r"^от\s+\d{2}\.\d{2}\.\d{4}")
ED_OPEN = re.compile(r"^\(в\s+ред\.", re.I)
TITLE_HEAD = re.compile(r"^(Указ|Постановление|Распоряжение|Приказ|Закон)\b")
POWER = re.compile(r"доверенност", re.I)
AMEND_OP = re.compile(r"дополнить\s+(пунктами|частями|статьями)", re.I)
INTRA = re.compile(r"статьями|части\s+\d|пункта\s+\d|настоящ", re.I)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trunc_flags(text: str) -> list[str]:
    s = text.rstrip()
    flags: list[str] = []
    if s.endswith(","):
        flags.append("ends-comma")
    if s.endswith("..."):
        flags.append("ellipsis")
    if s.count("(") > s.count(")"):
        flags.append("unclosed-paren")
    if OT_DATE.match(s):
        flags.append("starts-ot-date")
    if ED_OPEN.match(s) and not s.endswith(")"):
        flags.append("ed-note-open")
    return flags


def genres(text: str) -> list[str]:
    s = text.strip()
    out: list[str] = []
    if ED_OPEN.match(s) or "введен Федеральн" in s:
        out.append("consultant-ed-note")
    if TITLE_HEAD.match(s):
        out.append("full-title")
    if POWER.search(s):
        out.append("power-of-attorney")
    if AMEND_OP.search(s):
        out.append("amending-operative")
    if OT_DATE.match(s) or (s.endswith(",") and ED_OPEN.match(s)):
        out.append("truncated-list")
    if OT_DATE.match(s) and len(s) < 80:
        out.append("orphan-tail")
    if INTRA.search(s):
        out.append("intra-or-anaphora")
    if not out:
        out.append("other")
    return out


def coding_verdict(text: str, flags: list[str], genre: list[str]) -> str:
    """One closed label for whether this fragment is a sane coding unit."""
    if "ed-note-open" in flags or ("starts-ot-date" in flags and "ends-comma" in flags):
        return "incomplete-series-member"
    if "starts-ot-date" in flags and "orphan-tail" in genre:
        return "orphan-tail"
    if "power-of-attorney" in genre:
        return "not-norm-reference"
    if "amending-operative" in genre and "intra-or-anaphora" not in genre:
        return "operative-text-not-cite"
    if "consultant-ed-note" in genre and "ed-note-open" not in flags:
        return "complete-ed-note"
    if "full-title" in genre:
        return "document-title"
    if "intra-or-anaphora" in genre:
        return "in-text-cite"
    return "other-needs-coder"


def glue_candidate(a_text: str, b_text: str, gap: int) -> bool:
    if gap > 2:
        return False
    af, bf = trunc_flags(a_text), trunc_flags(b_text)
    a_open = "ends-comma" in af or "unclosed-paren" in af or "ed-note-open" in af
    b_tail = "starts-ot-date" in bf
    return a_open and b_tail


def build(root: Path) -> dict[str, Any]:
    manifest_path = root / MANIFEST_REL
    pilot_path = root / PILOT_REL
    fix = root / FIX_REL
    man = json.loads(manifest_path.read_text(encoding="utf-8"))
    pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
    fragments = man["fragments"]
    docs = {d["doc_id"]: d for d in man["documents"]}
    pilot_ids = {c["fragment_id"] for c in pilot["cases"]}

    rows: list[dict[str, Any]] = []
    by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for frag in fragments:
        path = fix / frag["file"]
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        flags = trunc_flags(text)
        gen = genres(text)
        rec = {
            "fragment_id": frag["id"],
            "doc_id": frag["doc_id"],
            "source_block_index": frag["source_block_index"],
            "note_kind": frag["note_kind"],
            "byte_len": len(raw),
            "in_m207_pilot": frag["id"] in pilot_ids,
            "trunc_flags": flags,
            "genre": gen,
            "coding_verdict": coding_verdict(text, flags, gen),
            "text_sha256": hashlib.sha256(raw).hexdigest(),
        }
        rec["_text"] = text
        rows.append(rec)
        by_doc[frag["doc_id"]].append(rec)

    for items in by_doc.values():
        items.sort(key=lambda r: r["source_block_index"])

    series: list[dict[str, Any]] = []
    used: set[str] = set()
    for doc_id, items in by_doc.items():
        i = 0
        while i < len(items):
            chain = [items[i]]
            j = i
            while j + 1 < len(items):
                a, b = items[j], items[j + 1]
                gap = b["source_block_index"] - a["source_block_index"]
                if glue_candidate(a["_text"], b["_text"], gap):
                    chain.append(b)
                    j += 1
                    continue
                break
            if len(chain) >= 2:
                ids = [c["fragment_id"] for c in chain]
                used.update(ids)
                joined = "".join(c["_text"] for c in chain)
                series.append(
                    {
                        "doc_id": doc_id,
                        "family": docs[doc_id]["family"],
                        "doc_type": docs[doc_id]["doc_type"],
                        "fragment_ids": ids,
                        "block_indices": [c["source_block_index"] for c in chain],
                        "member_count": len(chain),
                        "joined_byte_len": len(joined.encode("utf-8")),
                        "in_m207_pilot": any(c["in_m207_pilot"] for c in chain),
                        "kind": "consultant-edition-list",
                        "display_join_only": True,
                        "cross_block_text_anchor": False,
                        "joined_preview": joined[:180],
                    }
                )
                i = j + 1
                continue
            i += 1

    by_text: dict[str, list[str]] = defaultdict(list)
    for rec in rows:
        by_text[rec["_text"]].append(rec["fragment_id"])
    duplicates = [
        {"fragment_ids": ids, "byte_len": len(text.encode("utf-8"))}
        for text, ids in by_text.items()
        if len(ids) > 1
    ]

    verdicts = Counter(r["coding_verdict"] for r in rows)
    genres_c = Counter(g for r in rows for g in r["genre"])
    notes = Counter(r["note_kind"] for r in rows)

    public_rows = [{k: v for k, v in r.items() if k != "_text"} for r in rows]

    record = {
        "schema": SCHEMA,
        "schema_version": 1,
        "lifecycle": "[bounded]",
        "authoritative": False,
        "human_adoption": "pending",
        "runtime_stop_active": True,
        "frozen_pins": {
            "m199_manifest": {"path": MANIFEST_REL, "sha256": sha256_file(manifest_path)},
            "m207_pilot_cases": {"path": PILOT_REL, "sha256": sha256_file(pilot_path)},
        },
        "prior_art": {
            "pullenti": {
                "path": "/root/vendor-source/pullenti",
                "role": "development-stage orientation only (D380)",
                "observed": [
                    "AnalysisKit+Sofa keeps one token chain over the whole document",
                    "DecreeToken.ItemType.Edition parses '(в ред. …)' including bracketed lists",
                    "elliptical 'от DATE N' members inherit TYPE from the list head",
                    "IsNewlineBefore is a layout cue, not a document cut",
                ],
                "not_adopted": [
                    "no vendor code, dictionary, threshold, or runtime port",
                    "agreement with Pullenti is not gold and not a second coder",
                ],
                "evaluation_orientation": {
                    "role": "diagnostic third extractor, optional, license-gated",
                    "authority": "D380; ident40 bake-off (D383); RC28-F14",
                    "when": "after owner confirmation, on complete coding units only",
                    "compare": [
                        "edition-list membership and TYPE inheritance on elliptical «от DATE N» tails",
                        "Decree vs Part vs ThisDecree slot alphabet",
                        "series reconstructed by adjacent_blocks vs Sofa token chain",
                    ],
                    "never": [
                        "gold",
                        "second human coder",
                        "independent-measured S03 rate",
                        "product lex()/CI call",
                    ],
                    "s03_machinery": "Pullenti-differential was not scheduled inside execute-task; that does not cancel D380",
                    "other_extractors_ident40": [
                        "sol",
                        "spark",
                        "Agnes",
                    ],
                    "other_extractors_role": "disagreement map only; not a coding-unit design and not M207 gold",
                },
            },
            "law_nexus_own": {
                "d385": "prd/architecture/npa-document-context.yaml",
                "observed": [
                    "adjacent_blocks query is allowed; concatenating the document into parser input is forbidden",
                    "cross-block TextAnchor is forbidden",
                    "harvest selected shaped WordML w:p blocks independently",
                ],
            },
        },
        "counts": {
            "fragments": len(rows),
            "unique_texts": len(by_text),
            "duplicate_groups": len(duplicates),
            "series": len(series),
            "series_members": sum(s["member_count"] for s in series),
            "pilot_cases": len(pilot_ids),
            "pilot_unique_texts": len({r["_text"] for r in rows if r["in_m207_pilot"]}),
            "note_kind": dict(notes),
            "coding_verdict": dict(verdicts),
            "genre": dict(genres_c),
        },
        "duplicates": sorted(duplicates, key=lambda d: d["fragment_ids"][0]),
        "edition_series": series,
        "fragments": public_rows,
        "adaptation": {
            "keep_frozen_seed": True,
            "do_not_rewrite_m207_codebook": True,
            "coding_unit": "one complete reference occurrence, or one complete edition-list series diagnosed across adjacent same-document blocks",
            "context": "typed adjacent_blocks / open_series_head (D385), never a merged span",
            "human_pilot": "do not run two-pass coding on incomplete-series-member or orphan-tail units",
            "not_gold": True,
        },
        "non_claims": [
            "not gold",
            "not a human pilot",
            "not a Pullenti port or license grant",
            "not a rewrite of the frozen 180-fragment seed",
            "not a cross-block TextAnchor",
            "not RC28-F13 / Change-family adoption",
            "not official-publication provenance (R070 stays open)",
        ],
    }
    return record


def render(record: dict[str, Any]) -> bytes:
    return (json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("check", "run", "report"))
    args = parser.parse_args()
    record = build(ROOT)
    payload = render(record)
    target = ROOT / RECORD_REL
    if args.mode == "report":
        c = record["counts"]
        print(
            f"fragments={c['fragments']} unique={c['unique_texts']} "
            f"dup_groups={c['duplicate_groups']} series={c['series']} "
            f"series_members={c['series_members']} "
            f"pilot_unique={c['pilot_unique_texts']}/40"
        )
        print("verdicts", json.dumps(c["coding_verdict"], ensure_ascii=False))
        print("series:")
        for s in record["edition_series"]:
            print(f"  {s['doc_id']} {s['fragment_ids']} preview={s['joined_preview'][:90]!r}")
        print(MARKER)
        return 0
    if args.mode == "run":
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_bytes(payload)
        tmp.replace(target)
        print(
            f"{MARKER} fragments={record['counts']['fragments']} "
            f"series={record['counts']['series']} wrote={RECORD_REL}"
        )
        return 0
    if not target.is_file():
        print(f"FAIL MISSING_RECORD: {RECORD_REL}", file=sys.stderr)
        return 1
    if target.read_bytes() != payload:
        print(
            "FAIL DIAGNOSIS_DRIFT: tracked JSON is not the deterministic projection",
            file=sys.stderr,
        )
        return 1
    print(
        f"{MARKER} fragments={record['counts']['fragments']} "
        f"series={record['counts']['series']} drift=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

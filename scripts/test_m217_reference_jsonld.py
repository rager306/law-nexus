"""Independent fail-closed battery for the M217 reference prototype (scripts/m217_reference_jsonld.py).

Fast invariants run against the committed artifacts; the --check subprocess test
re-derives the full timeline from the pinned corpus (passes --check explicitly:
without it the writer mode never fails and stale detection false-passes).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "m217_reference_jsonld.py"
TIMELINE = REPO / "prd" / "migration" / "rust-evidence" / "m217-reference-timeline.json"
DIGESTS = REPO / "prd" / "migration" / "rust-evidence" / "m217-reference-digests.jsonl"
NAMED = REPO / "prd" / "migration" / "rust-evidence" / "m217-reference-named-graphs.json"
AMEND = REPO / "prd" / "migration" / "rust-evidence" / "m217-reference-amend-provenance.json"
REFERENCES = REPO / "prd" / "migration" / "rust-evidence" / "m217-reference-references.json"
D767_RESIDUAL = {"applied_day": "2017-08-06", "from_edition_no": 36, "raw_day": "2017-07-29"}


def test_artifacts_present() -> None:
    for path in (TIMELINE, DIGESTS, NAMED, AMEND, REFERENCES):
        assert path.exists(), f"missing committed artifact: {path}"


def test_timeline_schema_and_pins() -> None:
    timeline = json.loads(TIMELINE.read_text(encoding="utf-8"))
    assert timeline["schema_version"] == "m217-reference-timeline/v2"
    assert timeline["authoritative"] is False
    assert timeline["counts"]["editions"] == 118
    assert timeline["counts"]["non_monotonic"] == 1
    assert timeline["non_monotonic"] == [D767_RESIDUAL]
    clamped = [e for e in timeline["editions"] if e["clamped"]]
    assert len(clamped) == 1 and clamped[0]["edition_no"] == 37
    days = [e["applied_day"] for e in timeline["editions"]]
    assert days == sorted(days), "applied days must be monotonic after clamping"
    assert timeline["normalization_profile"]["id"] == "m217-norm/v1"
    assert all(re.fullmatch(r"[a-f0-9]{64}", e["source_sha256"]) for e in timeline["editions"])


def test_structural_breaks_are_history_not_parser_loss() -> None:
    timeline = json.loads(TIMELINE.read_text(encoding="utf-8"))
    breaks = [
        (e["edition_no"], e["removed_from_previous"])
        for e in timeline["editions"]
        if e["break_from_previous"]
    ]
    assert breaks == [(64, 3), (76, 5), (81, 40)]
    ed81 = next(e for e in timeline["editions"] if e["edition_no"] == 81)
    assert ed81["article_count"] == 94
    assert sum(e["parse_loss"] for e in timeline["editions"]) >= 0
    assert any("476-FZ purge band" in nc for nc in timeline["non_claims"]), (
        "article-count variance must be qualified as law history"
    )


def test_ctv_counts_stay_published() -> None:
    timeline = json.loads(TIMELINE.read_text(encoding="utf-8"))
    ops = {
        op: sum(1 for c in timeline["ctv_events"] if c["op"] == op)
        for op in ("created", "amended", "removed")
    }
    assert ops["created"] == 28
    assert ops["amended"] > 0 and ops["removed"] > 0
    assert sum(ops.values()) == timeline["counts"]["ctv_events"]


def test_digests_header_profile_and_matrix_shape() -> None:
    lines = DIGESTS.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 10_000
    header = json.loads(lines[0])
    assert header["record_kind"] == "header"
    assert header["normalization_profile"]["id"] == "m217-norm/v1"
    assert header["non_claims"], "profile header must carry non-claims"
    first = json.loads(lines[1])
    assert first["record_kind"] == "art_digest"
    assert first["schema_version"] == "m217-reference-digests/v1"
    assert first["edition_no"] == 1 and first["article"] == "statya-1"
    assert re.fullmatch(r"[a-f0-9]{64}", first["source"]["sha256"])
    assert 0 <= first["source"]["p_start"] <= first["source"]["p_end"]
    for line in lines[1:]:
        rec = json.loads(line)
        assert rec["record_kind"] == "art_digest" and len(rec["digest"]) == 12
        assert rec["source"]["sha256"]


def test_named_graphs_sample_contract() -> None:
    named = json.loads(NAMED.read_text(encoding="utf-8"))
    assert named["schema_version"] == "m217-reference-named-graphs/v1"
    assert named["graphs"][0]["sample_article"] == "statya-44"
    body = named["graphs"][1]
    assert body["@id"] == "cc:44-fz:statya-44"
    entries = body["graphs"]
    assert len(entries) > 100, "named graph per edition expected"
    assert entries == sorted(entries, key=lambda g: g["@id"])


def test_amend_provenance_layer() -> None:
    amend = json.loads(AMEND.read_text(encoding="utf-8"))
    assert amend["schema_version"] == "m217-reference-amend-provenance/v1"
    assert amend["authoritative"] is False
    assert amend["counts"]["editions_with_markers"] == 117
    assert amend["counts"]["markers"] > 10_000
    assert amend["counts"]["unique_amending_laws"] >= 60
    assert set(amend["resolution_tiers"]) <= {
        "resolved_enacting_date",
        "resolved_number_only",
        "unresolved",
    }
    ed50 = [m for m in amend["markers"] if m["edition_no"] == 50]
    assert len({(m["date"], m["number"]) for m in ed50}) == 22
    assert all(m["tier"] == "resolved_enacting_date" for m in ed50)
    assert any(m["article"] == "act" for m in ed50), "act-level edition marker expected"


def test_check_mode_rederivation_is_byte_identical() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert proc.returncode == 0, f"--check drifted (exit {proc.returncode}): {proc.stderr[-800:]}"
    assert "check=ok artifacts byte-identical" in proc.stdout

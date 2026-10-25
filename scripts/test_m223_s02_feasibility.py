#!/usr/bin/env python3
"""Contracts for the M223/S02 full-run feasibility decision helper.

Two layers of coverage:

* the committed evidence is re-derived from the two tracked S02 artifacts and
  must match byte-for-byte (closed decision vocabulary, export+read-back+overhead
  projection, stop thresholds that are *not* upper bounds, conditional-attempt
  authorization, explicit resume semantics, mandatory preflight, R1000 left
  active/unclosed, no raw decoded text);
* the projection/decision functions are exercised on hermetic inline fixtures
  (tempdir manifests and probes) so every failure path and every decision branch
  is asserted without touching the pinned corpus, the real binary or the
  committed evidence.

The rework finding ``M223-S02-end-to-end-budget`` requires: read-back cost must
affect the decision, thresholds must be labelled stop thresholds rather than
measured proof, and partial passes must never be reported as full.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FEASIBILITY_PATH = ROOT / "scripts/m223_s02_feasibility.py"
MANIFEST_PATH = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl"
PROBE_PATH = ROOT / "prd/migration/rust-evidence/m223-s02-clean-path-probe.json"
EVIDENCE_PATH = ROOT / "prd/migration/rust-evidence/m223-s02-corpus-feasibility.json"
CONTRACT_PATH = ROOT / "prd/architecture/intermediate-source-acceptance-contract.md"


def load_feasibility():
    spec = importlib.util.spec_from_file_location("m223_s02_feasibility", FEASIBILITY_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


feasibility = load_feasibility()


# ------------------------------------------------------------ fixtures #


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def write_manifest(path: Path, entries: list[tuple[str, int]]) -> dict:
    """Write a small deterministic inventory manifest (T01 format)."""
    total_bytes = sum(size for _, size in entries)
    header = {
        "schema": "m223-s02-corpus-inventory/v1",
        "version": 1,
        "root": "fixtures/exports",
        "counts": {
            "entries": len(entries),
            "total_bytes": total_bytes,
            "max_bytes": max((size for _, size in entries), default=0),
        },
        "subdirs": {},
        "pins": {
            "count": len(entries),
            "total_bytes": total_bytes,
            "max_bytes": max((size for _, size in entries), default=0),
            "match": True,
            "drift": [],
        },
        "inventory_digest": _sha("inventory"),
    }
    lines = [json.dumps(header)]
    for relative_path, size in entries:
        lines.append(
            json.dumps(
                {
                    "relative_path": relative_path,
                    "sha256": _sha(relative_path),
                    "bytes": size,
                }
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return header


def make_record(
    relative_path: str,
    size: int,
    *,
    strata: list[str],
    wall_s: float,
    rss_kb: int,
    output_bytes: int,
    readback_wall_s: float = 0.1,
) -> dict:
    return {
        "relative_path": relative_path,
        "input_bytes": size,
        "strata": strata,
        "outcome": "accepted",
        "export": {"wall_s": wall_s, "peak_rss_kb": rss_kb},
        "readback": {"outcome": "readback_ok", "wall_s": readback_wall_s},
        "output_bytes": output_bytes,
        "output_input_ratio": output_bytes / size if size else None,
    }


def write_probe(
    path: Path,
    records: list[dict],
    *,
    free_bytes: int = 10**12,
    total_bytes: int = 10**12,
    seed: int = 1,
) -> dict:
    payload = {
        "schema": "m223-s02-clean-path-probe/v1",
        "version": 1,
        "manifest": {"sha256": _sha("manifest"), "inventory_digest": _sha("inventory")},
        "sample": {"seed": seed, "count": len(records)},
        "aggregates": {"sampled": len(records), "accepted": len(records)},
        "run": {
            "status": "complete",
            "disk_before": {"free_bytes": free_bytes, "total_bytes": total_bytes},
        },
        "records": records,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def small_corpus_fixture(
    tmp_path: Path, *, free_bytes: int = 10**12, base_size: int = 1000, readback_wall_s: float = 0.1
) -> tuple[Path, Path]:
    """Two files per decile (20 files); one measured sample per decile, no tail."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    entries = [(f"npa/doc-{index:03d}.xml", base_size + index * 100) for index in range(20)]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, entries)
    ordered = sorted(entries, key=lambda item: (item[1], item[0]))
    records = []
    for index, (relative_path, size) in enumerate(ordered):
        decile = min(9, index * 10 // len(ordered))
        records.append(
            make_record(
                relative_path,
                size,
                strata=[f"decile_{decile}"],
                wall_s=0.5,
                rss_kb=32000,
                output_bytes=size * 8,
                readback_wall_s=readback_wall_s,
            )
        )
    probe = tmp_path / "probe.json"
    write_probe(probe, records, free_bytes=free_bytes)
    return manifest, probe


# ------------------------------------------------- committed evidence #


def committed_evidence() -> dict:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


def test_committed_decision_in_closed_vocabulary():
    evidence = committed_evidence()
    assert evidence["schema"] == "m223-s02-corpus-feasibility/v1"
    assert evidence["decision"]["verdict"] in feasibility.DECISIONS
    assert set(evidence["decision"]["vocabulary"]) == set(feasibility.DECISIONS)


def test_committed_projections_recompute_exactly():
    expected = feasibility.build_feasibility(MANIFEST_PATH, PROBE_PATH)
    assert committed_evidence() == expected


def test_committed_inputs_bind_to_artifacts():
    evidence = committed_evidence()
    manifest = evidence["inputs"]["manifest"]
    probe = evidence["inputs"]["probe"]
    assert manifest["sha256"] == feasibility.sha256_file(MANIFEST_PATH)
    assert probe["sha256"] == feasibility.sha256_file(PROBE_PATH)
    assert probe["manifest_sha256"] == manifest["sha256"]
    assert probe["inventory_digest"] == manifest["inventory_digest"]
    assert manifest["counts"]["entries"] == 43785
    assert manifest["counts"]["total_bytes"] == 3789431364
    assert manifest["counts"]["max_bytes"] == 29372660


def test_committed_manifest_pins_match():
    evidence = committed_evidence()
    pins = evidence["inputs"]["manifest"]["pins"]
    assert pins["match"] is True
    assert pins["drift"] == []
    assert pins["count"] == 43785
    assert pins["total_bytes"] == 3789431364
    assert pins["max_bytes"] == 29372660


def test_committed_wall_is_export_plus_readback_plus_stated_overhead():
    wall = committed_evidence()["projections"]["wall_s"]
    assert wall["export"]["total"] > 0
    assert wall["readback"]["total"] > 0
    assert pytest.approx(wall["combined_s"], rel=1e-6) == (
        wall["export"]["total"] + wall["readback"]["total"]
    )
    assert pytest.approx(wall["reconciliation_overhead_s"], rel=1e-6) == (
        wall["combined_s"] * feasibility.RECONCILIATION_OVERHEAD_FRACTION
    )
    assert pytest.approx(wall["subtotal_s"], rel=1e-6) == (
        wall["combined_s"] + wall["reconciliation_overhead_s"]
    )
    assert pytest.approx(wall["uncertainty_s"], rel=1e-6) == (
        wall["subtotal_s"] * feasibility.UNCERTAINTY_FRACTION
    )
    assert pytest.approx(wall["projected_total_s"], rel=1e-6) == (
        wall["subtotal_s"] + wall["uncertainty_s"]
    )
    assert wall["projected_total_s"] > wall["combined_s"]
    assert wall["reconciliation_overhead_fraction"] == feasibility.RECONCILIATION_OVERHEAD_FRACTION
    assert wall["uncertainty_fraction"] == feasibility.UNCERTAINTY_FRACTION


def test_committed_layer_and_rss_shape():
    projections = committed_evidence()["projections"]
    layer = projections["cleaned_layer_bytes"]
    assert layer["conservative_bytes"] >= layer["total_bytes"]
    assert layer["conservative_bytes"] >= layer["aggregate_ratio_bytes"]
    assert layer["ratio"]["max"] >= layer["ratio"]["p95"] >= layer["ratio"]["median"]
    rss = projections["peak_rss_kb"]
    assert rss["max"] >= rss["p95"] >= rss["median"] >= rss["min"]
    assert rss["stop_threshold_kb"] == feasibility.RSS_STOP_THRESHOLD_KB
    disk = projections["disk"]
    assert disk["persist_required_bytes"] == (
        disk["conservative_layer_bytes"] + disk["persist_safety_bytes"]
    )
    assert disk["headroom_bytes"] == disk["free_bytes"] - disk["conservative_layer_bytes"]
    for split in ("export", "readback"):
        assert len(projections["wall_s"][split]["per_decile"]) == feasibility.DECILE_COUNT


def test_committed_layer_tail_bytes_match_probe_output():
    # Independent recompute straight from the probe artifact: the layer's measured
    # tail must be the sum of actual output_bytes, never a sum of ratios.
    probe = json.loads(PROBE_PATH.read_text(encoding="utf-8"))
    tail_bytes = sum(
        record["output_bytes"]
        for record in probe["records"]
        if "tail_largest" in (record.get("strata") or [])
        and record.get("outcome") == "accepted"
        and record.get("output_bytes") is not None
    )
    layer = committed_evidence()["projections"]["cleaned_layer_bytes"]
    assert layer["tail_measured_bytes"] == tail_bytes
    assert layer["tail_measured_bytes"] > 1_000_000_000  # bytes, not a ratio sum
    assert layer["total_bytes"] == layer["tail_measured_bytes"] + layer["body_projected_bytes"]


def test_committed_stop_thresholds_are_not_upper_bounds():
    thresholds = committed_evidence()["decision"]["stop_thresholds"]
    assert thresholds["kind"] == "stop_threshold"
    assert thresholds["not_an_upper_bound"] is True
    assert thresholds["overshoot_note"]
    assert thresholds["wall_s"] == feasibility.WALL_STOP_THRESHOLD_S
    assert thresholds["peak_rss_kb"] == feasibility.RSS_STOP_THRESHOLD_KB
    assert thresholds["single_artifact_bytes"] == feasibility.SINGLE_ARTIFACT_STOP_THRESHOLD_BYTES
    # The declared stop thresholds are configuration, not measured maxima.
    measured_max_rss = committed_evidence()["projections"]["peak_rss_kb"]["max"]
    assert thresholds["peak_rss_kb"] != measured_max_rss


def test_committed_preflight_requirements_cover_memory_and_disk():
    preflight = committed_evidence()["decision"]["preflight_requirements"]
    assert preflight
    checks = " ".join(entry["check"] for entry in preflight)
    assert "available_memory_bytes" in checks
    assert "free_disk_bytes" in checks
    assert all(entry.get("threshold_bytes") or entry.get("threshold_s") for entry in preflight)


def test_committed_authorization_is_conditional_and_forbids_partial_as_full():
    authorization = committed_evidence()["decision"]["authorization"]
    assert authorization["kind"] == "conditional_attempt_authorization"
    assert authorization["partial_is_not_full"] is True
    assert "manifest entry" in authorization["scope"]
    assert authorization["on_stop"]
    assert authorization["granted_when"]


def test_committed_resume_semantics_bound_to_three_hash_families():
    resume = committed_evidence()["decision"]["resume_semantics"]
    assert len(resume["bound_to"]) == 3
    assert "§8.6" in resume["resume_requires"]
    assert "not full" in resume["partial_run_label"]


def test_committed_condition_names_full_persist_threshold():
    decision = committed_evidence()["decision"]
    condition = decision["condition_that_changes_decision"]
    assert condition["to"] == "full-persist"
    conservative = decision["decided_from"]["projected_layer_bytes"]
    assert condition["requires_free_disk_bytes"] > conservative
    assert str(condition["requires_free_disk_bytes"]) in condition["statement"]


def test_committed_evidence_pointers_resolve():
    evidence = committed_evidence()
    pointers = evidence["evidence_pointers"]
    assert pointers
    for relative in pointers:
        assert (ROOT / relative).is_file(), relative
    assert "prd/migration/rust-evidence/m223-s02-corpus-feasibility.json" not in pointers


def test_committed_verdict_follows_headroom():
    evidence = committed_evidence()
    disk = evidence["projections"]["disk"]
    verdict = evidence["decision"]["verdict"]
    if disk["free_bytes"] >= disk["persist_required_bytes"]:
        assert verdict == "full-persist"
    else:
        assert verdict in {"full-stream-discard", "requires-disk-expansion"}
        assert verdict != "full-persist"


def test_committed_blind_spots_recorded():
    evidence = committed_evidence()
    assert set(evidence["blind_spots"]) == set(feasibility.UNMEASURED_CLASSES)


# ------------------------------------------------------- R1000 identity #


def test_r1000_status_not_changed_by_decision():
    evidence = committed_evidence()
    assert evidence["r1000_status"] == "active/unclosed"
    joined = " ".join(evidence["non_claims"])
    assert "R1000 stays active/unclosed" in joined


def test_contract_preserves_r1000_nonclosure():
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    assert "R1000 stays active/unclosed" in text
    assert "no M223 slice closes R1000" in text


def test_script_has_no_requirement_mutation_surface():
    source = FEASIBILITY_PATH.read_text(encoding="utf-8")
    for forbidden in ("REQUIREMENTS.md", "gsd.db", "sqlite3", "better-sqlite3", "import sqlite"):
        assert forbidden not in source, forbidden


# ------------------------------------------------------------ redaction #


def test_evidence_carries_no_raw_decoded_text():
    evidence = committed_evidence()
    assert "records" not in evidence
    serialized = json.dumps(evidence)
    assert '"text_chars"' not in serialized
    assert '"inline_chars"' not in serialized
    for pointer in evidence["evidence_pointers"]:
        assert not Path(pointer).is_absolute()


# ---------------------------------------------------------------- solver #


def test_build_is_deterministic():
    first = feasibility.build_feasibility(MANIFEST_PATH, PROBE_PATH)
    second = feasibility.build_feasibility(MANIFEST_PATH, PROBE_PATH)
    assert first == second


def test_full_persist_when_disk_is_abundant(tmp_path):
    manifest, probe = small_corpus_fixture(tmp_path, free_bytes=10**14)
    payload = feasibility.build_feasibility(manifest, probe)
    assert payload["decision"]["verdict"] == "full-persist"


def test_stream_discard_when_layer_exceeds_disk(tmp_path):
    # Large corpus (~2 GB) with an ~8x ratio projects a ~16 GB layer; a 5 GB disk
    # covers one artifact plus safety but not the whole projected layer.
    manifest, probe = small_corpus_fixture(tmp_path, free_bytes=5 * 10**9, base_size=100_000_000)
    payload = feasibility.build_feasibility(manifest, probe)
    disk = payload["projections"]["disk"]
    assert disk["free_bytes"] < disk["persist_required_bytes"]
    assert payload["decision"]["verdict"] == "full-stream-discard"


def test_requires_disk_expansion_without_artifact_headroom(tmp_path):
    manifest, probe = small_corpus_fixture(tmp_path, free_bytes=10**4)
    payload = feasibility.build_feasibility(manifest, probe)
    assert payload["decision"]["verdict"] == "requires-disk-expansion"


def test_layer_tail_is_sum_of_output_bytes_not_ratios(tmp_path):
    # Tail file output (9,000,000) is deliberately far from its ratio (450), so a
    # ratio-or-time substitution would be caught instead of passing silently.
    entries = [(f"npa/doc-{index:03d}.xml", 1000 * (index + 1)) for index in range(20)]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, entries)
    ordered = sorted(entries, key=lambda item: (item[1], item[0]))
    tail_path, tail_size = ordered[-1]
    records = []
    for index, (relative_path, size) in enumerate(ordered):
        if relative_path == tail_path:
            records.append(
                make_record(
                    relative_path,
                    size,
                    strata=["tail_largest"],
                    wall_s=1.0,
                    rss_kb=1,
                    output_bytes=9_000_000,
                )
            )
        else:
            records.append(
                make_record(
                    relative_path,
                    size,
                    strata=[f"decile_{min(9, index * 10 // len(ordered))}"],
                    wall_s=1.0,
                    rss_kb=1,
                    output_bytes=size * 2,
                )
            )
    probe = tmp_path / "probe.json"
    write_probe(probe, records)
    payload = feasibility.build_feasibility(manifest, probe)
    layer = payload["projections"]["cleaned_layer_bytes"]
    assert layer["tail_measured_bytes"] == 9_000_000
    assert layer["total_bytes"] == layer["tail_measured_bytes"] + layer["body_projected_bytes"]


def test_readback_cost_changes_the_verdict(tmp_path):
    # Same corpus and disk, but a large read-back cost pushes the projected total
    # over the wall stop threshold, flipping full-stream-discard to a stop.
    small_rb = small_corpus_fixture(
        tmp_path / "small", free_bytes=5 * 10**9, base_size=100_000_000, readback_wall_s=0.1
    )
    big_rb = small_corpus_fixture(
        tmp_path / "big", free_bytes=5 * 10**9, base_size=100_000_000, readback_wall_s=5000.0
    )
    fast = feasibility.build_feasibility(*small_rb)
    slow = feasibility.build_feasibility(*big_rb)
    assert fast["decision"]["verdict"] == "full-stream-discard"
    assert (
        slow["projections"]["wall_s"]["projected_total_s"]
        > fast["projections"]["wall_s"]["projected_total_s"]
    )
    assert slow["projections"]["wall_s"]["projected_total_s"] > feasibility.WALL_STOP_THRESHOLD_S
    assert slow["decision"]["verdict"] != "full-stream-discard"


def test_readback_is_a_separate_projection_component(tmp_path):
    manifest, probe = small_corpus_fixture(tmp_path)
    wall = feasibility.build_feasibility(manifest, probe)["projections"]["wall_s"]
    assert wall["readback"]["total"] > 0
    assert wall["combined_s"] == pytest.approx(
        wall["export"]["total"] + wall["readback"]["total"], rel=1e-9
    )


# --------------------------------------------------------- failure paths #


def test_missing_manifest_is_typed_error(tmp_path):
    probe = tmp_path / "probe.json"
    write_probe(probe, [])
    code = feasibility.main(
        [
            "--manifest",
            str(tmp_path / "nope.jsonl"),
            "--probe",
            str(probe),
            "--out",
            str(tmp_path / "out.json"),
        ]
    )
    assert code == feasibility.EXIT_MISSING_INPUT


def test_missing_probe_is_typed_error(tmp_path):
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, [("npa/a.xml", 10)])
    code = feasibility.main(
        [
            "--manifest",
            str(manifest),
            "--probe",
            str(tmp_path / "nope.json"),
            "--out",
            str(tmp_path / "out.json"),
        ]
    )
    assert code == feasibility.EXIT_MISSING_INPUT


def test_manifest_schema_mismatch_refused(tmp_path):
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps({"schema": "wrong/v0"}) + "\n", encoding="utf-8")
    probe = tmp_path / "probe.json"
    write_probe(
        probe, [make_record("a.xml", 10, strata=["decile_0"], wall_s=1, rss_kb=1, output_bytes=10)]
    )
    code = feasibility.main(
        [
            "--manifest",
            str(manifest),
            "--probe",
            str(probe),
            "--out",
            str(tmp_path / "out.json"),
        ]
    )
    assert code == feasibility.EXIT_BAD_INPUT


def test_probe_schema_mismatch_refused(tmp_path):
    manifest, probe = small_corpus_fixture(tmp_path)
    payload = json.loads(probe.read_text())
    payload["schema"] = "wrong/v0"
    probe.write_text(json.dumps(payload), encoding="utf-8")
    code = feasibility.main(
        [
            "--manifest",
            str(manifest),
            "--probe",
            str(probe),
            "--out",
            str(tmp_path / "out.json"),
        ]
    )
    assert code == feasibility.EXIT_BAD_INPUT


def test_incomplete_probe_refused(tmp_path):
    manifest, probe = small_corpus_fixture(tmp_path)
    payload = json.loads(probe.read_text())
    payload["run"]["status"] = "interrupted"
    probe.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(feasibility.FeasibilityError):
        feasibility.build_feasibility(manifest, probe)


def test_probe_without_records_refused(tmp_path):
    manifest, probe = small_corpus_fixture(tmp_path)
    payload = json.loads(probe.read_text())
    payload["records"] = []
    probe.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(feasibility.FeasibilityError):
        feasibility.build_feasibility(manifest, probe)


def test_probe_missing_required_section_refused(tmp_path):
    manifest, probe = small_corpus_fixture(tmp_path)
    payload = json.loads(probe.read_text())
    del payload["aggregates"]
    probe.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(feasibility.FeasibilityError):
        feasibility.build_feasibility(manifest, probe)


def test_zero_free_disk_refused(tmp_path):
    manifest, probe = small_corpus_fixture(tmp_path, free_bytes=0)
    with pytest.raises(feasibility.FeasibilityError):
        feasibility.build_feasibility(manifest, probe)


def test_no_accepted_records_refused(tmp_path):
    manifest, probe = small_corpus_fixture(tmp_path)
    payload = json.loads(probe.read_text())
    for record in payload["records"]:
        record["outcome"] = "typed_refusal"
    probe.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(feasibility.FeasibilityError):
        feasibility.build_feasibility(manifest, probe)


def test_empty_manifest_refused(tmp_path):
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, [])
    probe = tmp_path / "probe.json"
    write_probe(
        probe, [make_record("a.xml", 10, strata=["decile_0"], wall_s=1, rss_kb=1, output_bytes=10)]
    )
    with pytest.raises(feasibility.FeasibilityError):
        feasibility.build_feasibility(manifest, probe)


def test_unreadable_probe_refused(tmp_path):
    manifest, probe = small_corpus_fixture(tmp_path)
    probe.write_text("{not json", encoding="utf-8")
    with pytest.raises(feasibility.FeasibilityError):
        feasibility.build_feasibility(manifest, probe)


def test_unwritable_out_returns_error(tmp_path, capsys):
    manifest, probe = small_corpus_fixture(tmp_path)
    out_dir = tmp_path / "as-directory"
    out_dir.mkdir()
    code = feasibility.main(
        ["--manifest", str(manifest), "--probe", str(probe), "--out", str(out_dir)]
    )
    assert code == feasibility.EXIT_OUT_UNWRITABLE
    assert "cannot write evidence" in capsys.readouterr().err


def test_decile_fallback_is_flagged(tmp_path):
    entries = [(f"npa/doc-{index:03d}.xml", 1000 + index * 100) for index in range(20)]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, entries)
    ordered = sorted(entries, key=lambda item: (item[1], item[0]))
    # Sample only decile 0; the other deciles must fall back to the global mean.
    records = [
        make_record(
            ordered[0][0],
            ordered[0][1],
            strata=["decile_0"],
            wall_s=1.0,
            rss_kb=1,
            output_bytes=ordered[0][1] * 8,
        )
    ]
    probe = tmp_path / "probe.json"
    write_probe(probe, records)
    payload = feasibility.build_feasibility(manifest, probe)
    deciles = payload["projections"]["wall_s"]["export"]["per_decile"]
    flagged = [row for row in deciles if row["fallback"]]
    assert flagged
    assert all(row["fallback"].get("value") == "global_body_mean" for row in flagged)


def test_tail_missing_is_recorded_when_tail_file_refused(tmp_path):
    entries = [(f"npa/doc-{index:03d}.xml", 1000 + index * 100) for index in range(20)]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, entries)
    ordered = sorted(entries, key=lambda item: (item[1], item[0]))
    biggest = ordered[-1][0]
    refused = make_record(
        biggest, ordered[-1][1], strata=["tail_largest"], wall_s=1, rss_kb=1, output_bytes=10
    )
    refused["outcome"] = "typed_refusal"
    records = [
        refused,
        make_record(
            ordered[0][0],
            ordered[0][1],
            strata=["decile_0"],
            wall_s=1.0,
            rss_kb=1,
            output_bytes=ordered[0][1] * 8,
        ),
    ]
    probe = tmp_path / "probe.json"
    write_probe(probe, records)
    payload = feasibility.build_feasibility(manifest, probe)
    sample = payload["projections"]["sample"]
    assert sample["tail_missing"] == [biggest]


# ----------------------------------------------------------- contract #


def test_contract_section_8_3_has_s02_authoritative_values():
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    assert "Value at S02 (authoritative)" in text
    assert "Value at S01" in text  # S01 history preserved
    assert "sha256:aa7e14e31059c906f291423a2e8151f8bf0f857e9fd7370545d7e3b5800766dd" in text


def test_contract_section_9_records_s02_verdict():
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    section = text.split("## 9. Slice feasibility reassessment", 1)[1].split("## 10.", 1)[0]
    s02_row = next(line for line in section.splitlines() if "S02" in line)
    assert "full-stream-discard" in s02_row
    assert "m223-s02-corpus-feasibility.json" in s02_row

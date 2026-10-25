#!/usr/bin/env python3
"""Contracts for the M223/S02 cleaned-path resource probe harness.

The suite exercises the probe as a process harness with a hermetic stub
``cleaned-project`` executable and inline fixture manifests; it never touches
the pinned corpus, the real binary, or any tracked evidence path.  Coverage:
all size strata, exactly one outcome per sampled file, the closed outcome
vocabulary, typed-refusal vs harness-timeout separation, live resource
enforcement (RSS/output/disk) in both export and read-back phases, read-back as
its own outcome, temp-artifact cleanup, percentile presence, disk/budget guards,
and interruption preserving completed records and the signal-derived exit code.
"""

from __future__ import annotations

import importlib.util
import json
import signal
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = ROOT / "scripts/m223_s02_probe.py"


def load_probe():
    spec = importlib.util.spec_from_file_location("m223_s02_probe", PROBE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


probe = load_probe()

# Stub executable: emulates the product's argv surface and exit-code contract.
# Export writes a small artifact; read prints the counts-only summary.  Behavior
# is keyed off the source file name (or artifact marker) so tests can drive every
# outcome, including live RSS/output breaches that require a child to stay alive.
STUB = """#!/usr/bin/env python3
import os
import signal
import sys
import time


def value(flag):
    args = sys.argv
    return args[args.index(flag) + 1] if flag in args else None


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "export":
        src = value("--from-xml") or ""
        out = value("--out")
        name = os.path.basename(src)
        sys.stdout.write("export-diagnostic-marker\\n")
        if "refuse" in name:
            sys.stderr.write("cleaned-project: source refused: unsupported_source\\n")
            return 5
        if "unwritable" in name:
            return 3
        if "verifyfail" in name:
            return 4
        if "usagebad" in name:
            return 2
        if "killme" in name:
            os.kill(os.getpid(), signal.SIGTERM)
            return 0
        if "slow" in name:
            time.sleep(30)
            return 0
        if "bigrss" in name:
            blob = bytearray(200 * 1024 * 1024)
            blob[0] = 1
            time.sleep(1)
        if "fastbigout" in name:
            with open(out + ".tmp", "wb") as handle:
                handle.write(b"o" * (2 * 1024 * 1024))
            os.replace(out + ".tmp", out)
            return 0
        if "bigout" in name:
            with open(out + ".tmp", "wb") as handle:
                handle.write(b"o" * (2 * 1024 * 1024))
            time.sleep(3)
            os.replace(out + ".tmp", out)
            return 0
        if "badread" in name:
            payload = b"BADREAD"
        elif "bigread" in name:
            payload = b"BIGREAD"
        else:
            payload = b"x" * 128
        with open(out, "wb") as handle:
            handle.write(payload)
        return 0
    if cmd == "read":
        artifact = value("--artifact") or ""
        with open(artifact, "rb") as handle:
            head = handle.read(7)
        if head == b"BADREAD":
            sys.stderr.write("cleaned-project: artifact unreadable: bad schema\\n")
            return 4
        if head == b"BIGREAD":
            blob = bytearray(200 * 1024 * 1024)
            blob[0] = 1
            time.sleep(1)
        sys.stdout.write(
            "contract_version=1\\n"
            "completion=complete\\n"
            "completion_basis=bounded_projection_complete\\n"
            "incomplete_reasons=\\n"
            "views=1\\n"
            "segments=2\\n"
            "references=3\\n"
            "source_segments=2\\n"
            "derived_segments=0\\n"
            "records=5\\n"
            "text_chars=100\\n"
            "text_bytes=150\\n"
            "inline_chars=100\\n"
            "inline_bytes=150\\n"
            "raw_decoded=SECRET_RAW_MARKER\\n"
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
"""


def write_stub(tmp_path: Path) -> Path:
    path = tmp_path / "cleaned-project"
    path.write_text(STUB, encoding="utf-8")
    path.chmod(0o755)
    return path


def make_entries(count: int, *, size_base: int = 1000, step: int = 10) -> list[dict]:
    return [
        {
            "relative_path": f"sample/doc-{index:04d}-normal.xml",
            "sha256": "sha256:" + f"{index:064x}",
            "bytes": size_base + index * step,
        }
        for index in range(count)
    ]


def write_manifest(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "manifest.jsonl"
    total = sum(entry["bytes"] for entry in entries)
    mx = max((entry["bytes"] for entry in entries), default=0)
    header = {
        "schema": "m223-s02-corpus-inventory/v1",
        "version": 1,
        "root": "fixture",
        "counts": {"entries": len(entries), "total_bytes": total, "max_bytes": mx},
        "subdirs": {},
        "pins": {
            "count": len(entries),
            "total_bytes": total,
            "max_bytes": mx,
            "match": True,
            "drift": [],
        },
        "inventory_digest": "sha256:" + "a" * 64,
    }
    with path.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(header) + "\n")
        for entry in entries:
            stream.write(json.dumps(entry) + "\n")
    return path


def entries_for(names: list[str]) -> list[dict]:
    return [
        {"relative_path": name, "sha256": "sha256:" + f"{index:064x}", "bytes": 2000 + index * 10}
        for index, name in enumerate(names)
    ]


def sample_from(entries: list[dict]) -> list:
    return [probe.SampleItem(e["relative_path"], e["bytes"], ["test"]) for e in entries]


def measured_result(**overrides) -> dict:
    """A full ``measure_subprocess`` result shape for classification unit tests."""
    base = {
        "wall_s": 0.01,
        "peak_rss_kb": 1000,
        "rc": 0,
        "signal": None,
        "timed_out": False,
        "exec_error": False,
        "rss_exceeded": False,
        "output_exceeded": False,
        "disk_exceeded": False,
        "rss_enforced": True,
        "observed_output_bytes": 128,
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------- manifest #


def test_manifest_roundtrip(tmp_path):
    path = write_manifest(tmp_path, make_entries(3))
    header, entries = probe.parse_manifest(path)
    assert header["counts"]["entries"] == 3
    assert [e.relative_path for e in entries] == [
        f"sample/doc-{i:04d}-normal.xml" for i in range(3)
    ]
    assert entries[0].bytes == 1000


def test_manifest_rejects_wrong_schema(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"schema":"other/v1"}\n', encoding="utf-8")
    with pytest.raises(ValueError):
        probe.parse_manifest(path)


# ----------------------------------------------------------------- strata #


def test_build_sample_covers_all_deciles():
    entries = [
        probe.Entry(f"doc-{i:04d}.xml", "sha256:" + f"{i:064x}", 1000 + i * 10) for i in range(100)
    ]
    sample, strata = probe.build_sample(entries, seed=7, per_decile=3, tail_n=5)
    assert set(strata["deciles"]) == {f"decile_{i}" for i in range(10)}
    assert all(count >= 1 for count in strata["deciles"].values())
    assert strata["tail_included"] >= 1
    assert strata["union_count"] == len(sample)
    assert all(item.strata for item in sample)
    # every sampled path is unique and deterministic for a fixed seed
    again, _ = probe.build_sample(entries, seed=7, per_decile=3, tail_n=5)
    assert [i.relative_path for i in again] == [i.relative_path for i in sample]


# --------------------------------------------------------------- run loop #


def test_run_probe_one_outcome_per_file_and_readback_separate(tmp_path):
    entries = make_entries(12)
    sample = sample_from(entries)
    run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(),
        tmp_dir=tmp_path,
    )
    records = run["records"]
    assert len(records) == len(sample)
    assert {r["outcome"] for r in records} == {"accepted"}
    for record in records:
        assert record["outcome"] in probe.EXPORT_OUTCOMES
        assert record["output_bytes"] == 128
        assert record["output_input_ratio"] == pytest.approx(round(128 / record["input_bytes"], 6))
        # read-back is its own outcome with its own timing
        assert record["readback"]["outcome"] == "readback_ok"
        assert record["readback"]["wall_s"] is not None
        assert record["readback"]["counts"]["text_chars"] == 100
        assert record["readback"]["counts"]["records"] == 5
    assert run["run_status"] == "complete"


def test_closed_failure_classification(tmp_path):
    names = [
        "a-refuse.xml",
        "b-unwritable.xml",
        "c-verifyfail.xml",
        "d-usagebad.xml",
        "e-killme.xml",
        "f-slow.xml",
        "g-normal.xml",
    ]
    sample = sample_from(entries_for(names))
    run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(export_wall_s=0.4),
        tmp_dir=tmp_path,
    )
    by_name = {r["relative_path"]: r["outcome"] for r in run["records"]}
    assert by_name["a-refuse.xml"] == "typed_refusal"
    assert by_name["b-unwritable.xml"] == "out_unwritable"
    assert by_name["c-verifyfail.xml"] == "artifact_verify_failed"
    assert by_name["d-usagebad.xml"] == "usage_error"
    assert by_name["e-killme.xml"] == "signaled"
    assert by_name["f-slow.xml"] == "timeout"
    assert by_name["g-normal.xml"] == "accepted"
    assert set(by_name.values()) <= set(probe.EXPORT_OUTCOMES)


def test_typed_refusal_is_not_timeout(tmp_path):
    sample = sample_from(entries_for(["a-refuse.xml", "b-slow.xml"]))
    run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(export_wall_s=0.4),
        tmp_dir=tmp_path,
    )
    by_name = {r["relative_path"]: r["outcome"] for r in run["records"]}
    assert by_name["a-refuse.xml"] == "typed_refusal"
    assert by_name["b-slow.xml"] == "timeout"
    assert by_name["a-refuse.xml"] != by_name["b-slow.xml"]
    aggregates = probe.aggregate(run["records"])
    assert aggregates["outcome_counts"] == {"timeout": 1, "typed_refusal": 1}
    assert aggregates["accepted"] == 0


# ------------------------------------------------- live resource breach #


def test_rss_limit_breach_enforced_in_export_phase(tmp_path):
    sample = sample_from(entries_for(["a-bigrss.xml"]))
    run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(peak_rss_kb=50_000),
        tmp_dir=tmp_path,
    )
    record = run["records"][0]
    assert record["outcome"] == "rss_limit_exceeded"
    assert record["export"]["rss_exceeded"] is True
    # live /proc sampling was available and is reported as enforced
    assert record["export"]["rss_enforced"] is True


def test_readback_rss_breach_preserves_export_outcome(tmp_path):
    sample = sample_from(entries_for(["a-bigread.xml"]))
    run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(peak_rss_kb=50_000),
        tmp_dir=tmp_path,
    )
    record = run["records"][0]
    # the export phase succeeded and its original outcome is preserved
    assert record["outcome"] == "accepted"
    assert record["readback"]["outcome"] == "readback_rss_exceeded"
    assert record["readback"]["rss_exceeded"] is True
    assert record["readback"]["rss_enforced"] is True


def test_output_budget_enforced_live_atomic_tmp(tmp_path):
    # The stub mimics the real publisher: it grows <out>.tmp, then renames.  The
    # live guard must catch the growing sibling before the rename.
    sample = sample_from(entries_for(["a-bigout.xml"]))
    run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(max_single_artifact_bytes=1000),
        tmp_dir=tmp_path,
    )
    record = run["records"][0]
    assert record["outcome"] == "output_limit_exceeded"
    assert record["export"]["output_exceeded"] is True
    assert record["tmp_removed"] is True
    assert not any(p.name.endswith(".tmp") for p in tmp_path.iterdir())


def test_atomic_output_post_exit_check_preserves_rc(tmp_path):
    # A fast atomic publish (write .tmp, rename, exit 0) can finish before the
    # wait loop samples.  Call measure_subprocess directly with a long poll
    # interval so the child exits first; the post-exit size check must refuse it
    # while keeping the child's original rc separate from the budget verdict.
    stub = write_stub(tmp_path)
    out = tmp_path / "artifact.jsonl"
    result = probe.measure_subprocess(
        [
            str(stub),
            "export",
            "--from-xml",
            str(tmp_path / "a-fastbigout.xml"),
            "--out",
            str(out),
        ],
        timeout_s=5.0,
        output_path=out,
        max_output_bytes=1000,
        poll_s=0.2,
    )
    assert result["output_exceeded"] is True
    assert result["rc"] == 0
    assert result["signal"] is None
    assert out.exists() and out.stat().st_size == 2 * 1024 * 1024
    assert not Path(str(out) + ".tmp").exists()


def test_atomic_output_fast_run_integration(tmp_path):
    # Same atomic fast publish through run_probe: whichever path catches it
    # (live poll or post-exit check), the outcome is the budget refusal and no
    # artifact/.tmp is left behind.
    sample = sample_from(entries_for(["a-fastbigout.xml"]))
    run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(max_single_artifact_bytes=1000),
        tmp_dir=tmp_path,
    )
    record = run["records"][0]
    assert record["outcome"] == "output_limit_exceeded"
    assert record["export"]["output_exceeded"] is True
    assert record["output_bytes"] is None
    assert record["readback"] is None
    assert record["tmp_removed"] is True
    assert not any(p.name.endswith(".tmp") for p in tmp_path.iterdir())


def test_classify_enforcement_outcomes():
    limits = probe.Limits()
    assert probe.classify_export(measured_result(rss_exceeded=True), limits) == "rss_limit_exceeded"
    assert probe.classify_export(measured_result(output_exceeded=True), limits) == (
        "output_limit_exceeded"
    )
    assert probe.classify_export(measured_result(disk_exceeded=True), limits) == (
        "disk_limit_exceeded"
    )
    assert probe.classify_readback(measured_result(rss_exceeded=True)) == "readback_rss_exceeded"
    assert probe.classify_readback(measured_result(disk_exceeded=True)) == "readback_disk_exceeded"


def test_disk_budget_enforced_in_flight(tmp_path):
    slow = tmp_path / "slow.sh"
    slow.write_text("#!/bin/sh\nsleep 5\n", encoding="utf-8")
    slow.chmod(0o755)
    state = {"n": 0}

    def fake_free() -> int:
        state["n"] += 1
        return 10**18 if state["n"] <= 2 else 0

    started = time.monotonic()
    result = probe.measure_subprocess(
        [str(slow)],
        timeout_s=10.0,
        disk_free_probe=fake_free,
        disk_floor_bytes=1,
        poll_s=0.02,
    )
    assert result["disk_exceeded"] is True
    assert time.monotonic() - started < 4.0
    assert probe.classify_export(result, probe.Limits()) == "disk_limit_exceeded"


def test_readback_failure_is_a_separate_outcome(tmp_path):
    sample = sample_from(entries_for(["a-badread.xml", "b-normal.xml"]))
    run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(),
        tmp_dir=tmp_path,
    )
    by_name = {r["relative_path"]: r for r in run["records"]}
    assert by_name["a-badread.xml"]["outcome"] == "accepted"
    assert by_name["a-badread.xml"]["readback"]["outcome"] == "readback_failed"
    assert by_name["a-badread.xml"]["readback"]["counts"] == {}
    assert by_name["b-normal.xml"]["readback"]["outcome"] == "readback_ok"


def test_temp_artifacts_removed(tmp_path):
    sample = sample_from(make_entries(6))
    work = tmp_path / "work"
    work.mkdir()
    run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(),
        tmp_dir=work,
    )
    assert all(r["tmp_removed"] for r in run["records"])
    leftovers = [p.name for p in work.iterdir()]
    assert leftovers == [], leftovers


def test_budget_and_disk_guards(tmp_path):
    sample = sample_from(make_entries(4))
    budget_run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(total_budget_wall_s=0.0),
        tmp_dir=tmp_path,
    )
    assert budget_run["run_status"] == "budget_exhausted"
    assert all(r["outcome"] == "not_run" for r in budget_run["records"])

    disk_run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(min_free_disk_bytes=10**18, abort_free_disk_bytes=1),
        tmp_dir=tmp_path,
    )
    assert all(r["outcome"] == "not_run" for r in disk_run["records"])

    abort_run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(abort_free_disk_bytes=10**18),
        tmp_dir=tmp_path,
    )
    assert abort_run["run_status"] == "disk_guard_stopped"
    assert all(r["outcome"] == "not_run" for r in abort_run["records"])


# ------------------------------------------------------------------ stats #


def test_percentiles_defined_and_ordered(tmp_path):
    sample = sample_from(make_entries(20))
    run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(),
        tmp_dir=tmp_path,
    )
    aggregates = probe.aggregate(run["records"])
    for key in ("export_wall_s", "export_peak_rss_kb", "output_bytes", "output_input_ratio"):
        stats = aggregates[key]
        assert stats["median"] is not None
        assert stats["p95"] is not None
        assert stats["max"] is not None
        assert stats["min"] <= stats["median"] <= stats["p95"] <= stats["max"]
    assert aggregates["readback_wall_s"]["median"] is not None
    assert aggregates["accept_rate"] == 1.0


def test_complex_classes_from_ready_metadata(tmp_path):
    entries = entries_for(["a-small.xml", "b-large.xml", "c-mid.xml"])
    sample = sample_from(entries)
    run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(),
        tmp_dir=tmp_path,
    )
    classes = probe.complex_classes(run["records"])
    for key in (
        "slowest_export",
        "peak_rss",
        "largest_output",
        "largest_text",
        "densest_records_per_kib",
    ):
        assert isinstance(classes[key], list)
    assert classes["largest_input"][0]["relative_path"] == "c-mid.xml"


# ---------------------------------------------------------------- payload #


def test_payload_contains_no_raw_text(tmp_path):
    sample = sample_from(entries_for(["a-normal.xml"]))
    run = probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(),
        tmp_dir=tmp_path,
    )
    payload = probe.build_payload(
        header={"counts": {}, "pins": {}, "inventory_digest": "sha256:" + "a" * 64},
        manifest_path=write_manifest(tmp_path, entries_for(["a-normal.xml"])),
        sample=sample,
        strata={"deciles": {}},
        limits=probe.Limits(),
        run=run,
        seed=1,
        bin_path=tmp_path / "cleaned-project",
        corpus_root=tmp_path / "corpus",
    )
    dump = json.dumps(payload)
    assert "SECRET_RAW_MARKER" not in dump
    assert "export-diagnostic-marker" not in dump
    assert payload["run"]["persistent_layer_bytes"] == 0
    assert payload["run"]["disk_before"]["free_bytes"] > 0
    assert payload["readback_disclaimer"]
    assert payload["enforcement"]["mode"] == "live"
    assert "per-document nesting depth" in payload["structural_coverage"]["not_measured"]


def test_evidence_written_atomically(tmp_path):
    out = tmp_path / "evidence.json"
    probe.write_evidence({"schema": probe.SCHEMA, "records": [1, 2]}, out)
    assert json.loads(out.read_text(encoding="utf-8"))["records"] == [1, 2]
    assert not out.with_suffix(out.suffix + ".tmp").exists()


# ------------------------------------------------------------ interruption #


def test_main_interruption_preserves_records_and_exit_code(tmp_path, monkeypatch):
    manifest = write_manifest(tmp_path, entries_for(["a.xml", "b.xml"]))
    stub = write_stub(tmp_path)
    out = tmp_path / "probe.json"

    items = [
        probe.SampleItem("a.xml", 1000, ["test"]),
        probe.SampleItem("b.xml", 2000, ["test"]),
    ]
    monkeypatch.setattr(probe, "build_sample", lambda entries, **kwargs: (items, {"deciles": {}}))

    calls = {"export": 0}

    def fake_measure(argv, **kwargs):
        if argv[1] == "export":
            calls["export"] += 1
            if calls["export"] == 1:
                Path(argv[argv.index("--out") + 1]).write_bytes(b"x" * 64)
                return measured_result()
            raise probe.Interrupted(signal.SIGTERM)
        kwargs["stdout_path"].write_text("text_chars=5\nrecords=2\n", encoding="utf-8")
        return measured_result()

    monkeypatch.setattr(probe, "measure_subprocess", fake_measure)

    exit_code = probe.main(
        [
            "--manifest",
            str(manifest),
            "--bin",
            str(stub),
            "--out",
            str(out),
            "--corpus-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 128 + signal.SIGTERM
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["run"]["status"] == "interrupted"
    assert len(payload["records"]) == 1
    assert payload["records"][0]["outcome"] == "accepted"


def test_run_probe_emits_incremental_callback(tmp_path):
    sample = sample_from(make_entries(5))
    seen: list[int] = []
    probe.run_probe(
        manifest_path=tmp_path / "manifest.jsonl",
        corpus_root=tmp_path / "corpus",
        bin_path=write_stub(tmp_path),
        sample=sample,
        limits=probe.Limits(),
        tmp_dir=tmp_path,
        on_record=lambda records: seen.append(len(records)),
    )
    assert seen == [1, 2, 3, 4, 5]


def test_percentile_interpolates():
    assert probe.percentile([], 50) is None
    assert probe.percentile([4.0], 95) == 4.0
    assert probe.percentile([0.0, 10.0], 50) == pytest.approx(5.0)
    assert probe.percentile([0.0, 10.0], 100) == pytest.approx(10.0)


def test_measure_subprocess_timeout_kills_child(tmp_path):
    slow = tmp_path / "slow.sh"
    slow.write_text("#!/bin/sh\nsleep 5\n", encoding="utf-8")
    slow.chmod(0o755)
    result = probe.measure_subprocess([str(slow)], timeout_s=0.3)
    assert result["timed_out"] is True
    assert result["wall_s"] < 3.0


def test_measure_subprocess_reports_signal(tmp_path):
    killer = tmp_path / "killer.sh"
    killer.write_text("#!/bin/sh\nkill -TERM $$\n", encoding="utf-8")
    killer.chmod(0o755)
    start = time.monotonic()
    result = probe.measure_subprocess([str(killer)], timeout_s=5.0)
    assert time.monotonic() - start < 4.0
    assert result["signal"] == "SIGTERM"
    assert result["rc"] is None

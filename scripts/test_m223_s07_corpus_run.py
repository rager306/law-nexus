#!/usr/bin/env python3
"""Contracts for the M223/S07 consumer acceptance corpus harness (T04).

Coverage:

* the closed consumer outcome/reason vocabulary and the four-pin binding;
* exactly one terminal outcome per manifest entry, with ``accepted`` /
  ``refused`` / ``incomplete`` reported separately and a refusal never counted
  as a success;
* the counts-document accounting/redaction check (schema
  ``m223-s07-consumer-counts/v1``, idempotent repeat import, identity pin, no
  decoded text);
* resume that skips current receipts and recomputes a stale binding;
* crash-safe receipts with an explicit ``incomplete`` on interruption;
* the ``run`` / ``status`` / ``verify-ledger`` / ``preflight`` / ``publish`` /
  ``prove-resume`` / ``prove-repeat-import`` surfaces;
* a real-binary end-to-end run over git-tracked fixtures (no corpus, no network)
  and a stub-driven SIGTERM + same-ledger resume proof.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts/m223_s07_corpus_run.py"
FIXED_REVISION = "sha256:" + "a" * 64


def load_harness():
    spec = importlib.util.spec_from_file_location("m223_s07_corpus_run", HARNESS_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mod = load_harness()


def real_binary() -> Path:
    for candidate in (
        ROOT / "target/release/consumer-run",
        ROOT / "target/debug/consumer-run",
    ):
        if candidate.is_file():
            return candidate
    subprocess.run(
        ["cargo", "build", "-p", "ln-decode", "--offline", "--bin", "consumer-run"],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    return ROOT / "target/debug/consumer-run"


# --------------------------------------------------------------- fixtures #

VALID_FIXTURES = (
    "crates/ln-decode/tests/fixtures/reader/diverse/text-only.xml",
    "crates/ln-decode/tests/fixtures/reader/diverse/controls.xml",
    "crates/ln-decode/tests/fixtures/reader/diverse/fields-revisions.xml",
)
REFUSAL_FIXTURES = (
    "crates/ln-decode/tests/fixtures/reader/diverse/negative-not-wordml.xml",
    "crates/ln-decode/tests/fixtures/reader/diverse/negative-namespace-absent.xml",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


def write_manifest(
    path: Path, entries: list[dict], *, inventory_digest: str = "sha256:" + "b" * 64
):
    total = sum(int(entry["bytes"]) for entry in entries)
    maximum = max((int(entry["bytes"]) for entry in entries), default=0)
    header = {
        "schema": mod.MANIFEST_SCHEMA,
        "version": 1,
        "root": "fixtures",
        "counts": {"entries": len(entries), "total_bytes": total, "max_bytes": maximum},
        "inventory_digest": inventory_digest,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(header, sort_keys=True) + "\n")
        for entry in entries:
            stream.write(json.dumps(entry, sort_keys=True) + "\n")


def manifest_entry(
    relative_path: str, *, override_sha: str | None = None, override_bytes: int | None = None
):
    source = ROOT / relative_path
    return {
        "relative_path": relative_path,
        "sha256": override_sha or sha256_file(source),
        "bytes": override_bytes if override_bytes is not None else source.stat().st_size,
    }


def run_cli(*args: str, expect: int | None = None) -> subprocess.CompletedProcess:
    completed = subprocess.run(
        [sys.executable, str(HARNESS_PATH), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if expect is not None:
        assert completed.returncode == expect, completed.stderr[-2000:]
    return completed


def cli_json(completed: subprocess.CompletedProcess) -> dict:
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert lines, completed.stderr[-2000:]
    return json.loads(lines[-1])


def base_run_args(
    tmp: Path, manifest: Path, binary: Path, *, corpus_root: Path = ROOT
) -> list[str]:
    return [
        "run",
        "--manifest",
        str(manifest),
        "--corpus-root",
        str(corpus_root),
        "--bin",
        str(binary),
        "--scratch",
        str(tmp / "scratch"),
        "--receipts",
        str(tmp / "receipts.jsonl"),
        "--report",
        str(tmp / "run.json"),
        "--resume",
        "--skip-preflight",
        "--code-revision",
        FIXED_REVISION,
    ]


# ----------------------------------------------------------- unit: closed #


def _result(rc=0, **overrides):
    base = {
        "timed_out": False,
        "rss_exceeded": False,
        "output_exceeded": False,
        "disk_exceeded": False,
        "signal": None,
        "rc": rc,
        "peak_rss_kb": 1000,
    }
    base.update(overrides)
    return base


LIMITS = None


def _limits():
    global LIMITS
    if LIMITS is None:
        LIMITS = mod.probe.Limits(peak_rss_kb=10_000)
    return LIMITS


@pytest.mark.parametrize(
    "result,expected",
    [
        (_result(rc=0), "accepted"),
        (_result(rc=5), "source_refusal"),
        (_result(rc=6), "consumer_refusal"),
        (_result(rc=2), "usage_error"),
        (_result(rc=3), "out_unwritable"),
        (_result(rc=4), "input_unreadable"),
        (_result(rc=127), "exec_error"),
        (_result(rc=9), "unknown_exit"),
        (_result(rc=0, timed_out=True), "timeout"),
        (_result(rc=0, rss_exceeded=True), "rss_limit_exceeded"),
        (_result(rc=0, output_exceeded=True), "output_limit_exceeded"),
        (_result(rc=0, disk_exceeded=True), "disk_limit_exceeded"),
        (_result(rc=None, signal="SIGTERM"), "signaled"),
        (_result(rc=0, peak_rss_kb=10_001), "rss_limit_exceeded"),
    ],
)
def test_classify_consumer_is_closed(result, expected):
    assert mod.classify_consumer(result, _limits()) == expected


def test_parse_refusal_accepts_known_tokens():
    assert mod.parse_refusal("consumer-run: source refused: source_not_wordml\n") == (
        "source:source_not_wordml",
        "source",
        "source_not_wordml",
    )
    assert mod.parse_refusal("consumer-run: consumer failed: span_invalid\n") == (
        "consumer:span_invalid",
        "consumer",
        "span_invalid",
    )
    assert mod.parse_refusal(
        "consumer-run: capture failed: source package error: malformed_xml: x\n"
    ) == ("package:malformed_xml", "package", "malformed_xml")


def test_parse_refusal_rejects_unknown_tokens():
    assert mod.parse_refusal("consumer-run: source refused: bogus_class\n") is None
    assert mod.parse_refusal("consumer-run: consumer failed: bogus_kind\n") is None
    assert mod.parse_refusal("nothing to see here\n") is None


def test_refusal_vocabularies_are_disjoint_and_closed():
    # A refusal is never a success class.
    assert "accepted" not in mod.READER_SOURCE_REFUSALS
    assert "accepted" not in mod.CONSUMER_REFUSAL_TOKENS
    # The graph refusals are part of the closed consumer vocabulary.
    assert mod.GRAPH_ERROR_KINDS.issubset(mod.CONSUMER_REFUSAL_TOKENS)
    assert mod.WIRE_ERROR_KINDS.issubset(mod.CONSUMER_REFUSAL_TOKENS)


# ------------------------------------------------------- unit: counts doc #


def _valid_counts(source_hex: str = "c" * 64) -> dict:
    return {
        "schema": mod.COUNTS_SCHEMA,
        "docs": 1,
        "tokens_total": 3,
        "tokens_source": 2,
        "tokens_derived": 1,
        "tokens_composite": 0,
        "tokens_by_class": {"word": 1, "whitespace": 1},
        "derived_by_kind": {"tab": 1},
        "graph": {"nodes": 2, "fragments": 1, "members": 1, "classifications": 0, "relations": 0},
        "repeat_import": {
            "already_present": True,
            "added_nodes": 0,
            "added_edges": 0,
            "counts_identical": True,
        },
        "identity": {
            "source_sha256": source_hex,
            "source_bytes": 12,
            "parent_schema": "law-nexus/cleaned-projection/v1",
            "document_version_ref": "m223-s07-corpus/v1",
            "source_revision": source_hex,
            "decoder_profile": "source_package_decoded_text/v1",
        },
        "profiles": {"tokenizer": "reader_tokenizer/v1", "graph": "npa_graph_projection/v1"},
    }


def test_validate_counts_doc_accepts_valid():
    doc, error = mod.validate_counts_doc(
        json.dumps(_valid_counts()), input_sha256="sha256:" + "c" * 64
    )
    assert error is None
    assert doc["schema"] == mod.COUNTS_SCHEMA


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update({"schema": "wrong"}),
        lambda d: d.update({"tokens_total": 9}),
        lambda d: d.update({"tokens_by_class": {"word": 1}}),
        lambda d: d.update({"derived_by_kind": {}}),
        lambda d: d.update(
            {
                "graph": {
                    "nodes": 5,
                    "fragments": 1,
                    "members": 1,
                    "classifications": 0,
                    "relations": 0,
                }
            }
        ),
        lambda d: d["repeat_import"].update({"added_nodes": 1}),
        lambda d: d["repeat_import"].update({"already_present": False}),
        lambda d: d["identity"].update({"source_sha256": "d" * 64}),
        lambda d: d.pop("profiles"),
    ],
)
def test_validate_counts_doc_rejects_broken(mutate):
    doc = _valid_counts()
    mutate(doc)
    _, error = mod.validate_counts_doc(json.dumps(doc), input_sha256="sha256:" + "c" * 64)
    assert error is not None


def test_validate_counts_doc_rejects_raw_text():
    doc = _valid_counts()
    doc["identity"]["document_version_ref"] = "Дело № 123"
    _, error = mod.validate_counts_doc(json.dumps(doc), input_sha256="sha256:" + "c" * 64)
    assert error is not None


def test_assert_no_raw_text_allows_tokens_and_rejects_cyrillic():
    mod.assert_no_raw_text({"a": "sha256:" + "a" * 64, "b": ["x", 1, True, None]})
    with pytest.raises(mod.HarnessError):
        mod.assert_no_raw_text({"leak": "приговор"})
    with pytest.raises(mod.HarnessError):
        mod.assert_no_raw_text({"nested": {"deep": ["ok", "ЖЖ"]}})
    with pytest.raises(mod.HarnessError):
        mod.assert_no_raw_text({"long": "x" * 5000})


# ----------------------------------------------------------- unit: ledger #


def test_receipt_log_roundtrip_and_torn_line(tmp_path):
    log = mod.ReceiptLog(tmp_path / "r.jsonl")
    entry = mod.probe.Entry("a/b.xml", "sha256:" + "a" * 64, 5)
    binding = mod.Binding(FIXED_REVISION, mod.rules_digest(), "sha256:" + "b" * 64, "bin")
    receipt = mod._base_receipt(entry, binding, 1, 0.0)
    receipt = mod._finish(receipt, "accepted", "accepted")
    log.append(receipt)
    log.append(receipt)
    assert len(log.read()) == 2

    # A torn final line is dropped; a corrupt interior line is fatal.
    with log.path.open("a", encoding="utf-8") as stream:
        stream.write('{"schema": "m223-s07-consumer-receipt/v1", "oops"')
    assert len(log.read()) == 2

    log2 = mod.ReceiptLog(tmp_path / "bad.jsonl")
    log2.append(receipt)
    with log2.path.open("a", encoding="utf-8") as stream:
        stream.write("not json\n")
    log2.append(receipt)
    with pytest.raises(mod.HarnessError):
        log2.read()


def test_receipt_is_current_requires_all_four_pins():
    entry = mod.probe.Entry("a/b.xml", "sha256:" + "a" * 64, 5)
    binding = mod.Binding(FIXED_REVISION, mod.rules_digest(), "sha256:" + "b" * 64, "bin")
    receipt = mod._finish(mod._base_receipt(entry, binding, 1, 0.0), "accepted", "accepted")
    assert mod.receipt_is_current(receipt, entry, binding, entry.sha256, entry.bytes)
    # code drift
    other = mod.Binding("sha256:" + "0" * 64, binding.rules_digest, binding.binary_sha256, "bin")
    assert not mod.receipt_is_current(receipt, entry, other, entry.sha256, entry.bytes)
    # input drift
    assert not mod.receipt_is_current(receipt, entry, binding, "sha256:" + "9" * 64, entry.bytes)
    # rules drift
    assert not mod.receipt_is_current(
        receipt,
        entry,
        mod.Binding(FIXED_REVISION, "sha256:" + "1" * 64, binding.binary_sha256, "bin"),
        entry.sha256,
        entry.bytes,
    )
    # binary drift
    assert not mod.receipt_is_current(
        receipt,
        entry,
        mod.Binding(FIXED_REVISION, binding.rules_digest, "sha256:" + "2" * 64, "bin"),
        entry.sha256,
        entry.bytes,
    )


def test_verify_ledger_ok_missing_and_multiple_bindings():
    entry = mod.probe.Entry("a/b.xml", "sha256:" + "a" * 64, 5)
    binding = mod.Binding(FIXED_REVISION, mod.rules_digest(), "sha256:" + "b" * 64, "bin")
    good = mod._finish(mod._base_receipt(entry, binding, 1, 0.0), "accepted", "accepted")

    ok = mod.verify_ledger(entries=[entry], receipts=[good], live_binding=binding)
    assert ok["ok"] and ok["terminal"] == 1 and ok["distinct_bindings"] == 1

    missing = mod.verify_ledger(entries=[entry], receipts=[], live_binding=binding)
    assert not missing["ok"]
    assert any(error["code"] == "missing_receipt" for error in missing["errors"])

    other_entry = mod.probe.Entry("a/c.xml", "sha256:" + "c" * 64, 6)
    other = mod._finish(
        mod._base_receipt(
            other_entry,
            mod.Binding("sha256:" + "0" * 64, binding.rules_digest, binding.binary_sha256, "bin"),
            2,
            0.0,
        ),
        "accepted",
        "accepted",
    )
    multi = mod.verify_ledger(
        entries=[entry, other_entry], receipts=[good, other], live_binding=binding
    )
    assert not multi["ok"]
    assert multi["distinct_bindings"] == 2
    assert any(error["code"] == "multiple_bindings" for error in multi["errors"])
    assert multi["live_drift"] is None


def test_rules_digest_is_stable_and_closed():
    assert mod.rules_digest() == mod.rules_digest()
    assert mod.rules_digest().startswith("sha256:")


def test_load_manifest_rejects_unsafe_and_duplicate(tmp_path):
    entries = [manifest_entry(VALID_FIXTURES[0])]
    path = tmp_path / "m.jsonl"
    write_manifest(path, entries)
    header, loaded = mod.load_manifest(path)
    assert len(loaded) == 1

    bad = tmp_path / "bad.jsonl"
    write_manifest(
        bad, [{"relative_path": "../escape.xml", "sha256": "sha256:" + "a" * 64, "bytes": 1}]
    )
    with pytest.raises(mod.HarnessError):
        mod.load_manifest(bad)


def test_select_proof_subset_is_deterministic():
    entries = [
        mod.probe.Entry(f"courts/{index:05d}.xml", "sha256:" + f"{index:064x}", 100 + index)
        for index in range(40)
    ]
    first = mod.select_proof_subset(entries, seed=7, per_subdir=3)
    second = mod.select_proof_subset(entries, seed=7, per_subdir=3)
    assert first.digest == second.digest
    assert [entry.relative_path for entry in first.entries] == [
        entry.relative_path for entry in second.entries
    ]
    assert len(first.entries) == 3


# ----------------------------------------------- integration: real binary #


def test_end_to_end_outcome_partition(tmp_path):
    binary = real_binary()
    entries = [manifest_entry(path) for path in VALID_FIXTURES + REFUSAL_FIXTURES]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, entries)

    run_cli(*base_run_args(tmp_path, manifest, binary), expect=0)
    report = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    summary = report["counts"]
    assert summary["entries"] == len(entries)
    assert summary["accepted"] == len(VALID_FIXTURES)
    assert summary["refused"] == len(REFUSAL_FIXTURES)
    assert summary["incomplete"] == 0
    assert summary["terminal"] == len(entries)
    assert summary["remaining"] == 0
    assert report["status"] == "complete"
    assert report["partial_is_not_full"] is True
    assert report["r1000_status"] == "active/unclosed"

    # Every refused entry carries a closed reason token, never a success class.
    receipts = mod.ReceiptLog(tmp_path / "receipts.jsonl").read()
    latest = mod.latest_by_path(receipts)
    assert len(latest) == len(entries)
    for receipt in latest.values():
        assert receipt["outcome"] in mod.TERMINAL_OUTCOMES
        if receipt["outcome"] == "refused":
            assert receipt["reason_token"] in mod.READER_SOURCE_REFUSALS
            assert receipt["counts"] is None
        else:
            assert receipt["counts"]["schema"] == mod.COUNTS_SCHEMA

    # The S03 reconciliation is carried, never re-derived.
    s03 = report["s03_baseline_reconciled"]
    assert s03["entries"] == 43785 and s03["accepted"] == 43785
    assert s03["refused"] == 0 and s03["incomplete"] == 0
    assert s03["r1000_status"] == "active/unclosed"

    # Redaction holds over the report and every receipt.
    mod.assert_no_raw_text(report)
    for receipt in receipts:
        mod.assert_no_raw_text(receipt)


def test_incomplete_outcomes_are_not_accepted(tmp_path):
    binary = real_binary()
    entries = [
        manifest_entry(VALID_FIXTURES[0]),
        # A missing file is an explicit incomplete, never a success.
        {
            "relative_path": "crates/ln-decode/tests/fixtures/reader/diverse/does-not-exist.xml",
            "sha256": "sha256:" + "a" * 64,
            "bytes": 10,
        },
        # A drifted sha is an explicit incomplete.
        manifest_entry(VALID_FIXTURES[1], override_sha="sha256:" + "0" * 64),
    ]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, entries)

    completed = run_cli(*base_run_args(tmp_path, manifest, binary), expect=mod.EXIT_INCOMPLETE)
    assert completed.returncode == mod.EXIT_INCOMPLETE
    report = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    assert report["status"] == "incomplete"
    assert report["counts"]["accepted"] == 1
    assert report["counts"]["incomplete"] == 2
    assert report["counts"]["refused"] == 0
    assert "input_drift" in report["incomplete_by_class"]
    assert report["partial_is_not_full"] is True


def test_resume_skips_current_receipts(tmp_path):
    binary = real_binary()
    entries = [manifest_entry(path) for path in VALID_FIXTURES]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, entries)

    run_cli(*base_run_args(tmp_path, manifest, binary), expect=0)
    first = mod.ReceiptLog(tmp_path / "receipts.jsonl").read()
    assert len(first) == len(entries)

    # A second resume adds no new receipt: every entry is current.
    run_cli(*base_run_args(tmp_path, manifest, binary), expect=0)
    second = mod.ReceiptLog(tmp_path / "receipts.jsonl").read()
    assert len(second) == len(first)


def test_status_and_verify_ledger_subcommands(tmp_path):
    binary = real_binary()
    entries = [manifest_entry(path) for path in VALID_FIXTURES]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, entries)
    run_cli(*base_run_args(tmp_path, manifest, binary), expect=0)

    common = [
        "--manifest",
        str(manifest),
        "--corpus-root",
        str(ROOT),
        "--bin",
        str(binary),
        "--scratch",
        str(tmp_path / "scratch"),
        "--receipts",
        str(tmp_path / "receipts.jsonl"),
        "--report",
        str(tmp_path / "run.json"),
        "--code-revision",
        FIXED_REVISION,
    ]
    status = cli_json(run_cli("status", *common, expect=0))
    assert status["summary"]["terminal"] == len(entries)
    assert status["partial_is_not_full"] is False

    verified = cli_json(run_cli("verify-ledger", *common, expect=0))
    assert verified["ok"] is True
    assert verified["distinct_bindings"] == 1
    assert verified["terminal"] == len(entries)

    # An empty ledger is not ok.
    empty = cli_json(
        run_cli(
            "verify-ledger",
            "--manifest",
            str(manifest),
            "--corpus-root",
            str(ROOT),
            "--bin",
            str(binary),
            "--scratch",
            str(tmp_path / "scratch"),
            "--receipts",
            str(tmp_path / "absent.jsonl"),
            "--code-revision",
            FIXED_REVISION,
            expect=mod.EXIT_VERIFY_FAILED,
        )
    )
    assert empty["ok"] is False


def test_preflight_subcommand(tmp_path):
    binary = real_binary()
    result = cli_json(
        run_cli(
            "preflight",
            "--bin",
            str(binary),
            "--scratch",
            str(tmp_path / "scratch"),
            expect=0,
        )
    )
    assert result["ok"] is True
    assert {check["id"] for check in result["checks"]} == {
        "free_disk_bytes",
        "available_memory_bytes",
        "binary_present",
    }


def test_publish_artifacts_are_redacted_and_schema(tmp_path):
    binary = real_binary()
    entries = [manifest_entry(path) for path in VALID_FIXTURES]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, entries)
    run_cli(*base_run_args(tmp_path, manifest, binary), expect=0)

    run_out = tmp_path / "published-run.json"
    receipts_out = tmp_path / "published-receipts.jsonl"
    cli_json(
        run_cli(
            "publish",
            "--manifest",
            str(manifest),
            "--corpus-root",
            str(ROOT),
            "--bin",
            str(binary),
            "--scratch",
            str(tmp_path / "scratch"),
            "--receipts",
            str(tmp_path / "receipts.jsonl"),
            "--report",
            str(tmp_path / "run.json"),
            "--run-out",
            str(run_out),
            "--receipts-out",
            str(receipts_out),
            "--code-revision",
            FIXED_REVISION,
            expect=0,
        )
    )
    report = json.loads(run_out.read_text(encoding="utf-8"))
    assert report["schema"] == mod.RUN_SCHEMA
    mod.assert_no_raw_text(report)
    receipts = mod.ReceiptLog(receipts_out).read()
    assert len(receipts) == len(entries)
    for receipt in receipts:
        assert receipt["schema"] == mod.RECEIPT_SCHEMA
        mod.assert_no_raw_text(receipt)


def test_real_binary_counts_doc_is_redacted(tmp_path):
    binary = real_binary()
    out = tmp_path / "counts.json"
    completed = subprocess.run(
        [str(binary), "--from-xml", str(ROOT / VALID_FIXTURES[1]), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == mod.COUNTS_SCHEMA
    assert doc["repeat_import"]["counts_identical"] is True
    assert doc["repeat_import"]["added_nodes"] == 0
    mod.assert_no_raw_text(doc)


def test_real_binary_refusal_exit_codes(tmp_path):
    binary = real_binary()
    refusal = ROOT / REFUSAL_FIXTURES[0]
    completed = subprocess.run(
        [str(binary), "--from-xml", str(refusal)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 5
    assert "source refused" in completed.stderr
    assert completed.stdout == ""

    missing = subprocess.run(
        [str(binary), "--from-xml", str(tmp_path / "nope.xml")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode == 4

    usage = subprocess.run(
        [str(binary), "--bogus"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert usage.returncode == 2


def test_prove_repeat_import_real_binary(tmp_path):
    binary = real_binary()
    entries = [manifest_entry(path) for path in VALID_FIXTURES]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, entries)
    out = tmp_path / "repeat.json"
    result = cli_json(
        run_cli(
            "prove-repeat-import",
            "--manifest",
            str(manifest),
            "--corpus-root",
            str(ROOT),
            "--bin",
            str(binary),
            "--scratch",
            str(tmp_path / "scratch"),
            "--out",
            str(out),
            "--per-subdir",
            "3",
            "--code-revision",
            FIXED_REVISION,
            expect=0,
        )
    )
    assert result["ok"] is True
    assert result["counts_byte_identical"] is True
    proof = json.loads(out.read_text(encoding="utf-8"))
    assert proof["schema"] == mod.REPEAT_PROOF_SCHEMA
    assert all(entry["counts_identical"] for entry in proof["entries"])
    mod.assert_no_raw_text(proof)


# ------------------------------------------------- stub-driven machinery #

STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import hashlib, json, os, sys, time
    args = sys.argv
    def value(flag):
        return args[args.index(flag) + 1] if flag in args else None
    src = value("--from-xml") or ""
    out = value("--out")
    name = os.path.basename(src)
    data = open(src, "rb").read()
    sha = hashlib.sha256(data).hexdigest()
    if "refuse" in name:
        sys.stderr.write("consumer-run: source refused: source_not_wordml\\n")
        sys.exit(5)
    if "timeout" in name:
        time.sleep(30)
        sys.exit(0)
    if "sleepy" in name:
        time.sleep(float(os.environ.get("M223_STUB_SLEEP", "0.4")))
    doc = {
        "schema": "m223-s07-consumer-counts/v1",
        "docs": 1,
        "tokens_total": 0,
        "tokens_source": 0,
        "tokens_derived": 0,
        "tokens_composite": 0,
        "tokens_by_class": {},
        "derived_by_kind": {},
        "graph": {"nodes": 0, "fragments": 0, "members": 0, "classifications": 0, "relations": 0},
        "repeat_import": {"already_present": True, "added_nodes": 0, "added_edges": 0, "counts_identical": True},
        "identity": {
            "source_sha256": sha,
            "source_bytes": len(data),
            "parent_schema": "law-nexus/cleaned-projection/v1",
            "document_version_ref": "m223-s07-corpus/v1",
            "source_revision": sha,
            "decoder_profile": "source_package_decoded_text/v1",
        },
        "profiles": {"tokenizer": "reader_tokenizer/v1", "graph": "npa_graph_projection/v1"},
    }
    with open(out, "w") as handle:
        json.dump(doc, handle)
    sys.exit(0)
    """
)


def write_stub(tmp_path: Path) -> Path:
    stub = tmp_path / "stub-consumer-run"
    stub.write_text(STUB, encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return stub


def test_timeout_is_incomplete_not_accepted(tmp_path):
    stub = write_stub(tmp_path)
    source = tmp_path / "timeout.xml"
    source.write_text("<x/>", encoding="utf-8")
    entries = [
        {
            "relative_path": "timeout.xml",
            "sha256": sha256_file(source),
            "bytes": source.stat().st_size,
        }
    ]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, entries)

    args = base_run_args(tmp_path, manifest, stub, corpus_root=tmp_path)
    args += ["--consumer-wall-s", "0.5"]
    run_cli(*args, expect=mod.EXIT_INCOMPLETE)
    report = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    assert report["counts"]["incomplete"] == 1
    assert report["counts"]["accepted"] == 0
    assert "timeout" in report["incomplete_by_class"]


def test_resume_proof_sigterm_same_ledger(tmp_path):
    stub = write_stub(tmp_path)
    sources = []
    for index in range(6):
        path = tmp_path / f"sleepy-{index}.xml"
        path.write_text("<x/>", encoding="utf-8")
        sources.append(
            {"relative_path": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size}
        )
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, sources)

    out = tmp_path / "resume-proof.json"
    env_backup = os.environ.get("M223_STUB_SLEEP")
    os.environ["M223_STUB_SLEEP"] = "0.3"
    try:
        cli_json(
            run_cli(
                "prove-resume",
                "--manifest",
                str(manifest),
                "--corpus-root",
                str(tmp_path),
                "--bin",
                str(stub),
                "--scratch",
                str(tmp_path / "scratch"),
                "--receipts",
                str(tmp_path / "proof-receipts.jsonl"),
                "--out",
                str(out),
                "--per-subdir",
                "6",
                "--code-revision",
                FIXED_REVISION,
                expect=0,
            )
        )
    finally:
        if env_backup is None:
            os.environ.pop("M223_STUB_SLEEP", None)
        else:
            os.environ["M223_STUB_SLEEP"] = env_backup

    proof = json.loads(out.read_text(encoding="utf-8"))
    assert proof["schema"] == mod.PROOF_SCHEMA
    assert proof["interruption"]["status"] == "interrupted"
    assert proof["interruption"]["signalled"] is True
    assert proof["preserved_current_receipts"] >= 1
    assert proof["final"]["terminal"] == len(sources)
    assert proof["final"]["remaining"] == 0
    assert proof["verification"]["ok"] is True
    assert proof["stale_recompute"]["stale_recomputed"] is True
    assert proof["r1000_status"] == "active/unclosed"
    mod.assert_no_raw_text(proof)


def test_prove_resume_rejects_unknown_refusal_token(tmp_path):
    # A stub that emits an unknown refusal token must fail closed to incomplete.
    stub = tmp_path / "stub-consumer-run"
    stub.write_text(
        "#!/usr/bin/env python3\nimport sys\n"
        "sys.stderr.write('consumer-run: source refused: bogus_class\\n')\nsys.exit(5)\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    source = tmp_path / "x.xml"
    source.write_text("<x/>", encoding="utf-8")
    entries = [
        {"relative_path": "x.xml", "sha256": sha256_file(source), "bytes": source.stat().st_size}
    ]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(manifest, entries)
    run_cli(
        *base_run_args(tmp_path, manifest, stub, corpus_root=tmp_path), expect=mod.EXIT_INCOMPLETE
    )
    report = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    assert report["counts"]["refused"] == 0
    assert report["counts"]["incomplete"] == 1

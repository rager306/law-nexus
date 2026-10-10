#!/usr/bin/env python3
"""Contracts for the M223/S03 resumable corpus baseline runner.

The suite exercises the runner as a process harness with a hermetic stub
``cleaned-project`` executable, fixture manifests and a fixture S02 decision; it
never touches the pinned corpus, the real binary, node, or any tracked evidence
path.  Coverage: the closed outcome/reason vocabulary, exactly one terminal
outcome per entry, separate accepted/refused/incomplete accounting, resume skip
of current receipts, stale recompute for each of the four binding pins
(input / code / rules / binary), crash-safe receipts with an explicit incomplete
on interruption, budget-chunk resume reaching complete, fail-closed preflight,
live stop-threshold classification, no-silent-skip, partial-is-not-full,
redaction, and the CLI ``run`` / ``status`` / ``verify-ledger`` / ``preflight``
surfaces.
"""

from __future__ import annotations

import importlib.util
import json
import signal
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "scripts/m223_s03_baseline.py"


def load_baseline():
    spec = importlib.util.spec_from_file_location("m223_s03_baseline", BASELINE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mod = load_baseline()

# --------------------------------------------------------------- fixtures #

#: Hermetic stub obeying the product argv/exit contract.  Behavior is keyed off
#: the source file name so tests can drive every outcome, including live RSS and
#: output breaches that need a child to stay alive.
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
        if "refuse" in name:
            sys.stderr.write("cleaned-project: source refused: source_not_wordml\\n")
            return 5
        if "capturefail" in name:
            sys.stderr.write(
                "cleaned-project: capture failed: source package error: malformed_xml\\n"
            )
            return 5
        if "unknownref" in name:
            sys.stderr.write("cleaned-project: source refused: bogus_class\\n")
            return 5
        if "wirefail" in name:
            sys.stderr.write("cleaned-project: projection failed: text_loss\\n")
            return 5
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
        if "bigout" in name:
            with open(out + ".tmp", "wb") as handle:
                handle.write(b"o" * (2 * 1024 * 1024))
            time.sleep(1.5)
            os.replace(out + ".tmp", out)
            return 0
        with open(out, "wb") as handle:
            handle.write(b"x" * 64)
        return 0
    if cmd == "read":
        artifact = value("--artifact") or ""
        with open(artifact, "rb") as handle:
            head = handle.read(7)
        if head == b"BADREAD":
            sys.stderr.write("cleaned-project: artifact unreadable: hash_mismatch\\n")
            return 4
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


def write_stub(tmp_path: Path, *, name: str = "cleaned-project", marker: str = "") -> Path:
    path = tmp_path / name
    body = STUB if not marker else STUB.replace("SECRET_RAW_MARKER", marker)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def make_corpus(tmp_path: Path, names: list[str]) -> tuple[Path, list[dict]]:
    """Write fixture corpus files and return their true sha256/bytes entries."""
    root = tmp_path / "corpus"
    entries = []
    for index, name in enumerate(names):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = f"<doc name={name!r} index={index}/>".encode()
        path.write_bytes(data)
        entries.append(
            {
                "relative_path": name,
                "sha256": mod.probe.sha256_file(path),
                "bytes": len(data),
            }
        )
    return root, entries


def write_manifest(tmp_path: Path, entries: list[dict], *, name: str = "manifest.jsonl") -> Path:
    path = tmp_path / name
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


def write_decision(
    tmp_path: Path,
    manifest_path: Path,
    *,
    disk_threshold: int = 1,
    mem_threshold: int = 1,
    verdict: str = "full-stream-discard",
    wall_s: int = 14400,
    peak_rss_kb: int = 6291456,
    single_artifact_bytes: int = 2147483648,
    name: str = "decision.json",
) -> Path:
    payload = json.loads(manifest_path.read_text(encoding="utf-8").splitlines()[0])
    decision = {
        "schema": "m223-s02-corpus-feasibility/v1",
        "version": 2,
        "inputs": {
            "manifest": {
                "path": str(manifest_path),
                "sha256": mod.probe.sha256_file(manifest_path),
                "inventory_digest": payload["inventory_digest"],
                "counts": payload["counts"],
            }
        },
        "decision": {
            "verdict": verdict,
            "stop_thresholds": {
                "kind": "stop_threshold",
                "enforcement": "polled",
                "not_an_upper_bound": True,
                "wall_s": wall_s,
                "peak_rss_kb": peak_rss_kb,
                "single_artifact_bytes": single_artifact_bytes,
            },
            "preflight_requirements": [
                {
                    "check": "free_disk_bytes >= single_artifact_stop_threshold_bytes + safety",
                    "threshold_bytes": disk_threshold,
                },
                {
                    "check": "available_memory_bytes >= peak_rss_stop_threshold_kb * 1024",
                    "threshold_bytes": mem_threshold,
                },
            ],
            "authorization": {
                "kind": "conditional_attempt_authorization",
                "partial_is_not_full": True,
            },
        },
    }
    path = tmp_path / name
    path.write_text(json.dumps(decision), encoding="utf-8")
    return path


def binding_for(bin_path: Path, code_revision: str = "sha256:" + "1" * 64) -> "mod.Binding":
    return mod.compute_binding(bin_path, code_revision=code_revision)


def measured_result(**overrides):
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
        "observed_output_bytes": 64,
    }
    base.update(overrides)
    return base


def run(
    tmp_path,
    *,
    names,
    bin_path=None,
    decision=None,
    binding=None,
    limits=None,
    attempt_wall_s=0.0,
    resume=True,
    scratch=None,
    receipts=None,
    max_entries=None,
    clock=None,
    measure=None,
):
    corpus_root, entries = make_corpus(tmp_path, names)
    manifest_path = write_manifest(tmp_path, entries)
    decision_path = decision or write_decision(tmp_path, manifest_path)
    if bin_path is None:
        bin_path = write_stub(tmp_path)
    scratch = scratch or (tmp_path / "scratch")
    receipts = receipts or (scratch / "receipts.jsonl")
    if binding is None:
        binding = binding_for(bin_path)
    kwargs = {}
    if clock is not None:
        kwargs["clock"] = clock
    if measure is not None:
        kwargs["measure"] = measure
    state = mod.run_baseline(
        entries=[mod.probe.Entry(**entry) for entry in entries],
        corpus_root=corpus_root,
        bin_path=bin_path,
        binding=binding,
        limits=limits or mod.probe.Limits(),
        scratch_dir=scratch,
        receipts_path=receipts,
        attempt_wall_s=attempt_wall_s,
        resume=resume,
        max_entries=max_entries,
        **kwargs,
    )
    return {
        "entries": [mod.probe.Entry(**entry) for entry in entries],
        "corpus_root": corpus_root,
        "manifest_path": manifest_path,
        "decision_path": decision_path,
        "bin_path": bin_path,
        "binding": binding,
        "scratch": scratch,
        "receipts": receipts,
        "state": state,
    }


# ------------------------------------------------------------- vocabulary #


def test_rules_digest_is_closed_and_stable():
    digest = mod.rules_digest()
    assert digest == mod.rules_digest()
    assert digest.startswith("sha256:")
    assert len(digest) == len("sha256:") + 64


def test_closed_vocabularies_are_disjoint_and_named():
    assert set(mod.ALL_OUTCOMES) == {"accepted", "refused", "incomplete"}
    assert set(mod.TERMINAL_OUTCOMES) <= set(mod.ALL_OUTCOMES)
    assert "input_drift" in mod.INCOMPLETE_CLASSES
    assert "binary_drift" in mod.INCOMPLETE_CLASSES
    assert mod.RULES_PROFILE == "cleaned_projection_wordml/v1"
    assert mod.RULES_CONTRACT_VERSION == 1
    assert mod.RULES_COMPLETION == "complete"


def test_parse_refusal_recognises_every_family():
    assert mod.parse_refusal("cleaned-project: source refused: source_not_wordml\n") == (
        "source:source_not_wordml",
        "source",
        "source_not_wordml",
    )
    assert (
        mod.parse_refusal("cleaned-project: projection failed: text_loss\n")[0] == "wire:text_loss"
    )
    assert (
        mod.parse_refusal("cleaned-project: export failed: hash_mismatch\n")[0]
        == "wire:hash_mismatch"
    )
    assert (
        mod.parse_refusal(
            "cleaned-project: capture failed: source package error: malformed_xml: detail\n"
        )[0]
        == "package:malformed_xml"
    )
    assert (
        mod.parse_refusal("cleaned-project: cannot read --from-xml: not_found\n")[0]
        == "io:not_found"
    )


def test_parse_refusal_unknown_token_is_none():
    assert mod.parse_refusal("cleaned-project: source refused: bogus\n") is None
    assert mod.parse_refusal("cleaned-project: projection failed: made_up\n") is None
    assert mod.parse_refusal("cleaned-project: something else\n") is None


# -------------------------------------------------------------- pin load #


def test_load_decision_fail_closed(tmp_path):
    manifest = write_manifest(tmp_path, [])
    good = write_decision(tmp_path, manifest)
    mod.load_decision(good)

    with pytest.raises(mod.HarnessError):
        mod.load_decision(
            write_decision(tmp_path, manifest, verdict="bounded-partial", name="d2.json")
        )

    bad = json.loads(good.read_text(encoding="utf-8"))
    del bad["decision"]["stop_thresholds"]
    p3 = tmp_path / "d3.json"
    p3.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(mod.HarnessError):
        mod.load_decision(p3)

    bad2 = json.loads(good.read_text(encoding="utf-8"))
    bad2["decision"]["authorization"]["partial_is_not_full"] = False
    p4 = tmp_path / "d4.json"
    p4.write_text(json.dumps(bad2), encoding="utf-8")
    with pytest.raises(mod.HarnessError):
        mod.load_decision(p4)


def test_load_manifest_rejects_unsafe_duplicate_and_pin_mismatch(tmp_path):
    unsafe = write_manifest(
        tmp_path, [{"relative_path": "../escape.xml", "sha256": "sha256:" + "a" * 64, "bytes": 1}]
    )
    with pytest.raises(mod.HarnessError):
        mod.load_manifest(unsafe)

    absolute = write_manifest(
        tmp_path, [{"relative_path": "/etc/passwd", "sha256": "sha256:" + "a" * 64, "bytes": 1}]
    )
    with pytest.raises(mod.HarnessError):
        mod.load_manifest(absolute)

    duplicate = write_manifest(
        tmp_path,
        [
            {"relative_path": "a.xml", "sha256": "sha256:" + "a" * 64, "bytes": 1},
            {"relative_path": "a.xml", "sha256": "sha256:" + "b" * 64, "bytes": 2},
        ],
    )
    with pytest.raises(mod.HarnessError):
        mod.load_manifest(duplicate)

    corpus_root, entries = make_corpus(tmp_path, ["a.xml"])
    manifest = write_manifest(tmp_path, entries)
    decision = write_decision(tmp_path, manifest)
    decision_payload = json.loads(decision.read_text(encoding="utf-8"))
    decision_payload["inputs"]["manifest"]["sha256"] = "sha256:" + "0" * 64
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(decision_payload), encoding="utf-8")
    with pytest.raises(mod.HarnessError):
        mod.load_manifest(manifest, decision=json.loads(tampered.read_text(encoding="utf-8")))


# --------------------------------------------------------------- receipts #


def test_receipt_log_torn_line_tolerated_and_interior_corrupt_rejected(tmp_path):
    path = tmp_path / "receipts.jsonl"
    log = mod.ReceiptLog(path)
    receipt = {"schema": mod.RECEIPT_SCHEMA, "relative_path": "a.xml", "attempt": 1}
    log.append(receipt)
    with path.open("a", encoding="utf-8") as stream:
        stream.write('{"schema": "m223-s03-baseline-receipt/v1", "relati')
    assert len(log.read()) == 1

    path.write_text(
        json.dumps(receipt) + "\nnot-json\n" + json.dumps(receipt) + "\n", encoding="utf-8"
    )
    with pytest.raises(mod.HarnessError):
        mod.ReceiptLog(path).read()


def test_latest_by_path_last_wins():
    receipts = [
        {"relative_path": "a.xml", "attempt": 1},
        {"relative_path": "b.xml", "attempt": 1},
        {"relative_path": "a.xml", "attempt": 2},
    ]
    latest = mod.latest_by_path(receipts)
    assert latest["a.xml"]["attempt"] == 2
    assert latest["b.xml"]["attempt"] == 1


# --------------------------------------------------------------- process #


def test_process_entry_accepted_records_artifact_identity(tmp_path):
    corpus_root, entries = make_corpus(tmp_path, ["a-normal.xml"])
    stub = write_stub(tmp_path)
    binding = binding_for(stub)
    receipt = mod.process_entry(
        mod.probe.Entry(**entries[0]),
        corpus_root=corpus_root,
        bin_path=stub,
        binding=binding,
        limits=mod.probe.Limits(),
        scratch_dir=tmp_path / "scratch",
        attempt=1,
    )
    assert receipt["outcome"] == "accepted"
    assert receipt["outcome_class"] == "accepted"
    assert receipt["artifact_sha256"].startswith("sha256:")
    assert receipt["readback"]["counts"]["text_chars"] == 100
    assert receipt["readback"]["is_substrate_verify"] is False
    assert receipt["input_verified_after"] is True
    assert receipt["tmp_removed"] is True
    assert not any(p.name.endswith(".tmp") for p in (tmp_path / "scratch").iterdir())


def test_process_entry_typed_refusal_and_unknown_token(tmp_path):
    corpus_root, entries = make_corpus(tmp_path, ["a-refuse.xml", "b-unknownref.xml"])
    stub = write_stub(tmp_path)
    binding = binding_for(stub)
    scratch = tmp_path / "scratch"
    refused = mod.process_entry(
        mod.probe.Entry(**entries[0]),
        corpus_root=corpus_root,
        bin_path=stub,
        binding=binding,
        limits=mod.probe.Limits(),
        scratch_dir=scratch,
        attempt=1,
    )
    assert refused["outcome"] == "refused"
    assert refused["outcome_class"] == "source:source_not_wordml"
    assert refused["reason_family"] == "source"
    assert refused["reason_token"] == "source_not_wordml"

    unknown = mod.process_entry(
        mod.probe.Entry(**entries[1]),
        corpus_root=corpus_root,
        bin_path=stub,
        binding=binding,
        limits=mod.probe.Limits(),
        scratch_dir=scratch,
        attempt=1,
    )
    assert unknown["outcome"] == "incomplete"
    assert unknown["outcome_class"] == "harness_error"
    assert unknown["outcome"] != "accepted"


def test_process_entry_input_drift(tmp_path):
    corpus_root, entries = make_corpus(tmp_path, ["a-normal.xml"])
    stub = write_stub(tmp_path)
    binding = binding_for(stub)
    drifted = dict(entries[0])
    drifted["sha256"] = "sha256:" + "f" * 64  # manifest pin that the file does not match
    receipt = mod.process_entry(
        mod.probe.Entry(**drifted),
        corpus_root=corpus_root,
        bin_path=stub,
        binding=binding,
        limits=mod.probe.Limits(),
        scratch_dir=tmp_path / "scratch",
        attempt=1,
    )
    assert receipt["outcome"] == "incomplete"
    assert receipt["outcome_class"] == "input_drift"


def test_readback_failure_is_not_accepted(tmp_path):
    corpus_root, entries = make_corpus(tmp_path, ["a-normal.xml"])
    # no a-badread path here: drive the read-back branch directly via a stub that
    # reports artifact unreadable using a marker artifact is awkward; instead we
    # assert a normal accepted run and a separate harness-level failure class.
    stub = write_stub(tmp_path)
    binding = binding_for(stub)

    def failing_read(argv, **kwargs):
        if argv[1] == "export":
            Path(kwargs["output_path"]).write_bytes(b"BADREAD")
            return measured_result()
        return measured_result(rc=4)

    receipt = mod.process_entry(
        mod.probe.Entry(**entries[0]),
        corpus_root=corpus_root,
        bin_path=stub,
        binding=binding,
        limits=mod.probe.Limits(),
        scratch_dir=tmp_path / "scratch",
        attempt=1,
        measure=failing_read,
    )
    assert receipt["outcome"] == "incomplete"
    assert receipt["outcome_class"] == "artifact_verify_failed"
    assert receipt["artifact_sha256"] is None


# ------------------------------------------------------------- run + resume #


def test_run_baseline_terminal_outcome_per_entry_and_accounting(tmp_path):
    result = run(tmp_path, names=["a-normal.xml", "b-refuse.xml", "c-wirefail.xml"])
    state = result["state"]
    receipts = mod.ReceiptLog(result["receipts"]).read()
    assert [r["relative_path"] for r in receipts] == [
        "a-normal.xml",
        "b-refuse.xml",
        "c-wirefail.xml",
    ]
    assert state["status"] == "complete"
    assert state["summary"]["accepted"] == 1
    assert state["summary"]["refused"] == 2
    assert state["summary"]["incomplete"] == 0
    assert state["summary"]["terminal"] == 3
    assert state["summary"]["refused_by_class"] == {
        "source:source_not_wordml": 1,
        "wire:text_loss": 1,
    }


def test_resume_skips_current_receipts(tmp_path):
    first = run(tmp_path, names=["a-normal.xml", "b-refuse.xml"])
    assert first["state"]["written_receipts"] == 2
    second = run(
        tmp_path,
        names=["a-normal.xml", "b-refuse.xml"],
        receipts=first["receipts"],
        scratch=first["scratch"],
        binding=first["binding"],
    )
    assert second["state"]["skipped"] == 2
    assert second["state"]["written_receipts"] == 0
    assert second["state"]["status"] == "complete"


def test_resume_recomputes_stale_input(tmp_path):
    """Blocker: modifying the XML while keeping the manifest/receipt must not skip/accepted."""
    result = run(tmp_path, names=["a-normal.xml"])
    assert result["state"]["summary"]["accepted"] == 1
    # mutate the corpus file, leaving the manifest and the receipt untouched
    (result["corpus_root"] / "a-normal.xml").write_bytes(b"<changed/>")
    state = mod.run_baseline(
        entries=result["entries"],
        corpus_root=result["corpus_root"],
        bin_path=result["bin_path"],
        binding=result["binding"],
        limits=mod.probe.Limits(),
        scratch_dir=result["scratch"],
        receipts_path=result["receipts"],
        attempt_wall_s=0.0,
    )
    latest = mod.latest_by_path(mod.ReceiptLog(result["receipts"]).read())
    receipt = latest["a-normal.xml"]
    assert state["skipped"] == 0
    assert receipt["outcome"] == "incomplete"
    assert receipt["outcome_class"] == "input_drift"
    assert receipt["outcome"] != "accepted"


def test_resume_recomputes_stale_code_revision(tmp_path):
    result = run(tmp_path, names=["a-normal.xml"])
    other = binding_for(result["bin_path"], code_revision="sha256:" + "2" * 64)
    second = run(
        tmp_path,
        names=["a-normal.xml"],
        receipts=result["receipts"],
        scratch=result["scratch"],
        binding=other,
    )
    assert second["state"]["skipped"] == 0
    assert second["state"]["written_receipts"] == 1
    latest = mod.latest_by_path(mod.ReceiptLog(result["receipts"]).read())
    assert latest["a-normal.xml"]["code_revision"] == "sha256:" + "2" * 64


def test_resume_recomputes_stale_rules_digest(tmp_path):
    result = run(tmp_path, names=["a-normal.xml"])
    stale_rules = mod.Binding(
        code_revision=result["binding"].code_revision,
        rules_digest="sha256:" + "3" * 64,
        binary_sha256=result["binding"].binary_sha256,
        binary_path=result["binding"].binary_path,
    )
    second = run(
        tmp_path,
        names=["a-normal.xml"],
        receipts=result["receipts"],
        scratch=result["scratch"],
        binding=stale_rules,
    )
    assert second["state"]["skipped"] == 0
    assert second["state"]["written_receipts"] == 1
    latest = mod.latest_by_path(mod.ReceiptLog(result["receipts"]).read())
    assert latest["a-normal.xml"]["rules_digest"] == "sha256:" + "3" * 64


def test_resume_recomputes_on_binary_change_same_source_revision(tmp_path):
    """Blocker: a changed binary at the same code revision must not reuse old receipts."""
    stub_one = write_stub(tmp_path, name="bin-one", marker="MARKER_ONE")
    result = run(tmp_path, names=["a-normal.xml"], bin_path=stub_one)
    assert result["state"]["summary"]["accepted"] == 1

    stub_two = write_stub(tmp_path, name="bin-two", marker="MARKER_TWO")
    assert mod.probe.sha256_file(stub_one) != mod.probe.sha256_file(stub_two)
    new_binding = binding_for(stub_two, code_revision=result["binding"].code_revision)
    second = run(
        tmp_path,
        names=["a-normal.xml"],
        bin_path=stub_two,
        receipts=result["receipts"],
        scratch=result["scratch"],
        binding=new_binding,  # same code revision, different binary sha
    )
    # the runner recomputes with the *new* binary binding
    assert second["state"]["skipped"] == 0
    latest = mod.latest_by_path(mod.ReceiptLog(result["receipts"]).read())
    assert latest["a-normal.xml"]["binary_sha256"] == mod.probe.sha256_file(stub_two)


def test_no_silent_skip_when_receipt_not_current(tmp_path):
    result = run(tmp_path, names=["a-normal.xml"])
    receipts_path = result["receipts"]
    records = mod.ReceiptLog(receipts_path).read()
    records[0]["input_sha256"] = "sha256:" + "9" * 64
    with receipts_path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record) + "\n")
    second = run(
        tmp_path,
        names=["a-normal.xml"],
        receipts=receipts_path,
        scratch=result["scratch"],
        binding=result["binding"],
    )
    assert second["state"]["skipped"] == 0
    assert second["state"]["written_receipts"] == 1


# ------------------------------------------------------------ budget/resume #


class FakeClock:
    def __init__(self, step: float = 0.6) -> None:
        self.value = 0.0
        self.step = step

    def __call__(self) -> float:
        result = self.value
        self.value += self.step
        return result


def test_budget_chunk_resume_reaches_complete(tmp_path):
    names = ["a-normal.xml", "b-normal.xml", "c-normal.xml"]
    first = run(tmp_path, names=names, attempt_wall_s=1.0, clock=FakeClock())
    assert first["state"]["status"] == "budget_exhausted"
    assert first["state"]["written_receipts"] == 1
    assert first["state"]["summary"]["terminal"] < 3

    second = run(
        tmp_path,
        names=names,
        receipts=first["receipts"],
        scratch=first["scratch"],
        binding=first["binding"],
        attempt_wall_s=0.0,
    )
    assert second["state"]["status"] == "complete"
    assert second["state"]["skipped"] == 1
    assert second["state"]["summary"]["terminal"] == 3


# ------------------------------------------------------------ interruption #


def test_interruption_preserves_receipts_and_marks_not_run(tmp_path):
    corpus_root, entries = make_corpus(tmp_path, ["a-normal.xml", "b-normal.xml"])
    stub = write_stub(tmp_path)
    binding = binding_for(stub)
    scratch = tmp_path / "scratch"
    calls = {"export": 0}

    def flaky_measure(argv, **kwargs):
        if argv[1] == "export":
            calls["export"] += 1
            if calls["export"] == 1:
                Path(kwargs["output_path"]).write_bytes(b"x" * 64)
                return measured_result()
            raise mod.probe.Interrupted(signal.SIGTERM)
        kwargs["stdout_path"].write_text(
            "contract_version=1\ncompletion=complete\ntext_chars=5\n", encoding="utf-8"
        )
        return measured_result()

    with pytest.raises(mod.probe.Interrupted):
        mod.run_baseline(
            entries=[mod.probe.Entry(**entry) for entry in entries],
            corpus_root=corpus_root,
            bin_path=stub,
            binding=binding,
            limits=mod.probe.Limits(),
            scratch_dir=scratch,
            receipts_path=scratch / "receipts.jsonl",
            attempt_wall_s=0.0,
            measure=flaky_measure,
        )
    receipts = mod.ReceiptLog(scratch / "receipts.jsonl").read()
    assert [r["relative_path"] for r in receipts] == ["a-normal.xml", "b-normal.xml"]
    assert receipts[0]["outcome"] == "accepted"
    assert receipts[1]["outcome"] == "incomplete"
    assert receipts[1]["outcome_class"] == "not_run"


def test_main_interruption_returns_signal_exit(tmp_path, monkeypatch):
    corpus_root, entries = make_corpus(tmp_path, ["a-normal.xml"])
    manifest = write_manifest(tmp_path, entries)
    decision = write_decision(tmp_path, manifest)
    stub = write_stub(tmp_path)
    scratch = tmp_path / "scratch"

    def boom(**kwargs):
        raise mod.probe.Interrupted(signal.SIGTERM)

    monkeypatch.setattr(mod, "run_baseline", boom)
    exit_code = mod.main(
        [
            "run",
            "--manifest",
            str(manifest),
            "--corpus-root",
            str(corpus_root),
            "--bin",
            str(stub),
            "--decision",
            str(decision),
            "--scratch",
            str(scratch),
            "--receipts",
            str(scratch / "receipts.jsonl"),
            "--report",
            str(scratch / "run.json"),
            "--code-revision",
            "sha256:" + "1" * 64,
        ]
    )
    assert exit_code == 128 + signal.SIGTERM
    report = json.loads((scratch / "run.json").read_text(encoding="utf-8"))
    assert report["status"] == "interrupted"
    assert report["partial_is_not_full"] is True


def test_binary_drift_within_attempt_fails_closed(tmp_path):
    """Blocker: an executable swapped mid-attempt must not be reported full."""
    corpus_root, entries = make_corpus(tmp_path, ["a-normal.xml"])
    stub = write_stub(tmp_path, name="bin", marker="MARKER")
    binding = binding_for(stub)
    scratch = tmp_path / "scratch"
    real_measure = mod.probe.measure_subprocess
    swapped = {"done": False}

    def swapping_measure(argv, **kwargs):
        result = real_measure(argv, **kwargs)
        if not swapped["done"]:
            stub.write_text(STUB.replace("SECRET_RAW_MARKER", "SWAPPED"), encoding="utf-8")
            stub.chmod(0o755)
            swapped["done"] = True
        return result

    run_state = mod.run_baseline(
        entries=[mod.probe.Entry(**entry) for entry in entries],
        corpus_root=corpus_root,
        bin_path=stub,
        binding=binding,
        limits=mod.probe.Limits(),
        scratch_dir=scratch,
        receipts_path=scratch / "receipts.jsonl",
        attempt_wall_s=0.0,
        measure=swapping_measure,
    )
    assert swapped["done"] is True
    assert run_state["binary_drift"] is True
    assert run_state["status"] == "incomplete"


# ---------------------------------------------------------------- preflight #


def test_preflight_fail_closed_disk_and_memory(tmp_path):
    corpus_root, entries = make_corpus(tmp_path, ["a-normal.xml"])
    manifest = write_manifest(tmp_path, entries)
    stub = write_stub(tmp_path)
    scratch = tmp_path / "scratch"
    scratch.mkdir()

    huge = json.loads(write_decision(tmp_path, manifest).read_text(encoding="utf-8"))
    huge["decision"]["preflight_requirements"][0]["threshold_bytes"] = 10**18
    huge["decision"]["preflight_requirements"][1]["threshold_bytes"] = 10**18
    result = mod.preflight(decision=huge, bin_path=stub, scratch_dir=scratch, mem_probe=lambda: 1)
    assert result["ok"] is False
    assert "free_disk_bytes" in result["failures"]
    assert "available_memory_bytes" in result["failures"]

    ok = mod.preflight(
        decision=json.loads(write_decision(tmp_path, manifest).read_text(encoding="utf-8")),
        bin_path=stub,
        scratch_dir=scratch,
        mem_probe=lambda: 10**18,
    )
    assert ok["ok"] is True


def test_preflight_missing_binary_fails(tmp_path):
    corpus_root, entries = make_corpus(tmp_path, ["a-normal.xml"])
    manifest = write_manifest(tmp_path, entries)
    decision = json.loads(write_decision(tmp_path, manifest).read_text(encoding="utf-8"))
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    result = mod.preflight(
        decision=decision,
        bin_path=tmp_path / "nope",
        scratch_dir=scratch,
        mem_probe=lambda: 10**18,
    )
    assert result["ok"] is False
    assert "binary_present" in result["failures"]


# ------------------------------------------------------------ stop thresholds #


def test_stop_threshold_rss_breach(tmp_path):
    result = run(
        tmp_path,
        names=["a-bigrss.xml"],
        limits=mod.probe.Limits(peak_rss_kb=50_000),
    )
    latest = mod.latest_by_path(mod.ReceiptLog(result["receipts"]).read())
    assert latest["a-bigrss.xml"]["outcome_class"] == "rss_limit_exceeded"


def test_stop_threshold_output_breach(tmp_path):
    result = run(
        tmp_path,
        names=["a-bigout.xml"],
        limits=mod.probe.Limits(max_single_artifact_bytes=1000),
    )
    latest = mod.latest_by_path(mod.ReceiptLog(result["receipts"]).read())
    assert latest["a-bigout.xml"]["outcome_class"] == "output_limit_exceeded"


def test_stop_threshold_wall_breach(tmp_path):
    result = run(
        tmp_path,
        names=["a-slow.xml"],
        limits=mod.probe.Limits(export_wall_s=0.4),
    )
    latest = mod.latest_by_path(mod.ReceiptLog(result["receipts"]).read())
    assert latest["a-slow.xml"]["outcome_class"] == "timeout"


# ------------------------------------------------------------- verify ledger #


def test_verify_ledger_ok_and_rejects_incomplete(tmp_path):
    result = run(tmp_path, names=["a-normal.xml", "b-refuse.xml"])
    entries = result["entries"]
    receipts = mod.ReceiptLog(result["receipts"]).read()
    verdict = mod.verify_ledger(entries=entries, receipts=receipts, live_binding=result["binding"])
    assert verdict["ok"] is True
    assert verdict["terminal"] == 2
    assert verdict["distinct_bindings"] == 1
    assert verdict["live_drift"] is False

    # mark one receipt non-terminal -> not ok
    records = [dict(record) for record in receipts]
    records[1]["outcome"] = "incomplete"
    records[1]["outcome_class"] = "not_run"
    bad = mod.verify_ledger(entries=entries, receipts=records)
    assert bad["ok"] is False
    assert any(error["code"] == "non_terminal" for error in bad["errors"])

    # drop a receipt -> missing
    missing = mod.verify_ledger(entries=entries, receipts=receipts[:1])
    assert missing["ok"] is False
    assert any(error["code"] == "missing_receipt" for error in missing["errors"])


def test_verify_ledger_reports_live_drift_without_failing(tmp_path):
    result = run(tmp_path, names=["a-normal.xml"])
    receipts = mod.ReceiptLog(result["receipts"]).read()
    other = mod.Binding(
        code_revision="sha256:" + "5" * 64,
        rules_digest=result["binding"].rules_digest,
        binary_sha256=result["binding"].binary_sha256,
        binary_path=result["binding"].binary_path,
    )
    verdict = mod.verify_ledger(entries=result["entries"], receipts=receipts, live_binding=other)
    assert verdict["ok"] is True
    assert verdict["live_drift"] is True


# ------------------------------------------------------------ report/redact #


def test_partial_is_not_full(tmp_path):
    result = run(tmp_path, names=["a-normal.xml", "b-normal.xml", "c-normal.xml"], max_entries=1)
    assert result["state"]["status"] == "budget_exhausted"
    state = result["state"]
    report = mod.build_run_report(
        state=state,
        header={"inventory_digest": "sha256:" + "a" * 64, "counts": {}},
        manifest_path=result["manifest_path"],
        decision=json.loads(result["decision_path"].read_text(encoding="utf-8")),
        attempts=[],
        preflight_result=None,
        manifest_sha256="sha256:" + "a" * 64,
    )
    assert report["partial_is_not_full"] is True
    assert report["status"] == "budget_exhausted"
    verdict = mod.verify_ledger(
        entries=result["entries"], receipts=mod.ReceiptLog(result["receipts"]).read()
    )
    assert verdict["ok"] is False


def test_no_raw_decoded_text_in_receipts_or_report(tmp_path):
    result = run(tmp_path, names=["a-normal.xml"])
    dump_receipts = result["receipts"].read_text(encoding="utf-8")
    assert "SECRET_RAW_MARKER" not in dump_receipts
    report = mod.build_run_report(
        state=result["state"],
        header={"inventory_digest": "sha256:" + "a" * 64, "counts": {}},
        manifest_path=result["manifest_path"],
        decision=json.loads(result["decision_path"].read_text(encoding="utf-8")),
        attempts=[],
        preflight_result=None,
        manifest_sha256="sha256:" + "a" * 64,
    )
    assert "SECRET_RAW_MARKER" not in json.dumps(report)


# -------------------------------------------------------------------- cli #


def test_cli_run_status_verify_preflight(tmp_path, capsys):
    corpus_root, entries = make_corpus(tmp_path, ["a-normal.xml", "b-refuse.xml"])
    manifest = write_manifest(tmp_path, entries)
    decision = write_decision(tmp_path, manifest)
    stub = write_stub(tmp_path)
    scratch = tmp_path / "scratch"
    receipts = scratch / "receipts.jsonl"
    report = scratch / "run.json"
    revision = "sha256:" + "1" * 64

    run_code = mod.main(
        [
            "run",
            "--manifest",
            str(manifest),
            "--corpus-root",
            str(corpus_root),
            "--bin",
            str(stub),
            "--decision",
            str(decision),
            "--scratch",
            str(scratch),
            "--receipts",
            str(receipts),
            "--report",
            str(report),
            "--code-revision",
            revision,
            "--resume",
        ]
    )
    assert run_code == mod.EXIT_OK
    assert report.exists()
    assert len(mod.ReceiptLog(receipts).read()) == 2

    status_code = mod.main(
        [
            "status",
            "--manifest",
            str(manifest),
            "--bin",
            str(stub),
            "--decision",
            str(decision),
            "--scratch",
            str(scratch),
            "--receipts",
            str(receipts),
            "--code-revision",
            revision,
        ]
    )
    assert status_code == mod.EXIT_OK
    snapshot = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert snapshot["summary"]["terminal"] == 2

    verify_code = mod.main(
        [
            "verify-ledger",
            "--manifest",
            str(manifest),
            "--bin",
            str(stub),
            "--decision",
            str(decision),
            "--scratch",
            str(scratch),
            "--receipts",
            str(receipts),
            "--code-revision",
            revision,
        ]
    )
    assert verify_code == mod.EXIT_OK

    preflight_code = mod.main(
        [
            "preflight",
            "--manifest",
            str(manifest),
            "--bin",
            str(stub),
            "--decision",
            str(decision),
            "--scratch",
            str(scratch),
        ]
    )
    assert preflight_code == mod.EXIT_OK


def test_cli_preflight_failed_exit(tmp_path, capsys):
    corpus_root, entries = make_corpus(tmp_path, ["a-normal.xml"])
    manifest = write_manifest(tmp_path, entries)
    decision_payload = json.loads(write_decision(tmp_path, manifest).read_text(encoding="utf-8"))
    decision_payload["decision"]["preflight_requirements"][0]["threshold_bytes"] = 10**18
    decision_payload["decision"]["preflight_requirements"][1]["threshold_bytes"] = 10**18
    decision = tmp_path / "huge.json"
    decision.write_text(json.dumps(decision_payload), encoding="utf-8")
    stub = write_stub(tmp_path)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    code = mod.main(
        [
            "preflight",
            "--manifest",
            str(manifest),
            "--bin",
            str(stub),
            "--decision",
            str(decision),
            "--scratch",
            str(scratch),
        ]
    )
    assert code == mod.EXIT_PREFLIGHT
    assert "preflight failed" in capsys.readouterr().err


def test_cli_verify_ledger_fails_on_missing(tmp_path, capsys):
    corpus_root, entries = make_corpus(tmp_path, ["a-normal.xml"])
    manifest = write_manifest(tmp_path, entries)
    decision = write_decision(tmp_path, manifest)
    stub = write_stub(tmp_path)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    code = mod.main(
        [
            "verify-ledger",
            "--manifest",
            str(manifest),
            "--bin",
            str(stub),
            "--decision",
            str(decision),
            "--scratch",
            str(scratch),
            "--receipts",
            str(scratch / "receipts.jsonl"),
            "--code-revision",
            "sha256:" + "1" * 64,
        ]
    )
    assert code == mod.EXIT_VERIFY_FAILED


# ------------------------------------------------------------- resume proof #


def proof_fixture(tmp_path, names, *, scratch_name="proof"):
    """Fixture bundle for the resume-proof surfaces (stub binary, pinned pairs)."""
    corpus_root, entries = make_corpus(tmp_path, names)
    manifest = write_manifest(tmp_path, entries, name="proof-manifest.jsonl")
    decision = write_decision(tmp_path, manifest, name="proof-decision.json")
    stub = write_stub(tmp_path, name="proof-bin")
    binding = binding_for(stub, code_revision="sha256:" + "1" * 64)
    scratch = tmp_path / scratch_name
    receipts = scratch / "receipts.jsonl"
    return {
        "entries": [mod.probe.Entry(**entry) for entry in entries],
        "corpus_root": corpus_root,
        "manifest_path": manifest,
        "decision_path": decision,
        "bin_path": stub,
        "binding": binding,
        "scratch": scratch,
        "receipts": receipts,
    }


def test_select_proof_subset_is_deterministic_and_covers_subdirs():
    entries = [
        mod.probe.Entry(f"{sub}/f{index:03d}.xml", "sha256:" + "a" * 64, 100 + index)
        for sub in ("courts", "fas", "npa", "xml")
        for index in range(20)
    ]
    first = mod.select_proof_subset(entries, seed=7, per_subdir=5)
    second = mod.select_proof_subset(entries, seed=7, per_subdir=5)
    assert first.digest == second.digest
    assert [e.relative_path for e in first.entries] == [e.relative_path for e in second.entries]
    assert len(first.entries) == 20
    assert set(first.subdir_counts) == {"courts", "fas", "npa", "xml"}
    assert all(count == 5 for count in first.subdir_counts.values())
    assert first.digest.startswith("sha256:")
    # the seed genuinely drives the draw
    other = mod.select_proof_subset(entries, seed=8, per_subdir=5)
    assert other.digest != first.digest


def test_prove_resume_records_skip_stale_incomplete_and_final(tmp_path):
    fix = proof_fixture(
        tmp_path,
        [
            "courts/a-normal.xml",
            "courts/b-refuse.xml",
            "fas/c-normal.xml",
            "fas/d-wirefail.xml",
        ],
    )
    proof = mod.prove_resume(
        manifest_path=fix["manifest_path"],
        corpus_root=fix["corpus_root"],
        bin_path=fix["bin_path"],
        decision_path=fix["decision_path"],
        binding=fix["binding"],
        limits=mod.probe.Limits(),
        scratch_dir=fix["scratch"],
        receipts_path=fix["receipts"],
        entries=fix["entries"],
        seed=1,
        per_subdir=2,
        bounded_wall_s=0.0,
        enable_interrupt=False,
        enable_refusal_probe=False,
    )
    assert proof["schema"] == mod.PROOF_SCHEMA
    labels = [attempt["label"] for attempt in proof["attempts"]]
    assert labels == [
        "bounded-budget",
        "resume-skip",
        "stale-recompute",
        "incomplete-reattempt",
    ]
    assert proof["attempts"][0]["status"] == "budget_exhausted"
    assert proof["attempts"][0]["receipts_after"] == 3
    assert proof["attempts"][1]["status"] == "complete"
    assert proof["attempts"][1]["skipped_current"] == 3
    assert proof["attempts"][1]["resumed_without_reexport"] is True
    assert proof["attempts"][1]["exports"] == 1
    assert proof["attempts"][2]["recomputed_stale"] == 1
    assert proof["attempts"][2]["skipped_current"] == 3
    assert proof["attempts"][3]["reattempted_incomplete"] == 1
    assert proof["stale_probe"]["recomputed"] is True
    assert proof["subset"]["size"] == 4
    assert proof["subset"]["non_wordml_subdir_present"] is False
    assert proof["final"]["verify_ledger_ok"] is True
    assert proof["final"]["entries"] == 4
    assert proof["final"]["incomplete"] == 0
    assert proof["final"]["terminal"] == 4
    assert proof["partial_is_not_full"] is True
    assert proof["refusal_probe"] is None
    assert proof["interruption"] is None


def test_verify_proof_recomputes_and_rejects_tamper(tmp_path):
    fix = proof_fixture(tmp_path, ["courts/a-normal.xml", "fas/c-normal.xml"])
    proof = mod.prove_resume(
        manifest_path=fix["manifest_path"],
        corpus_root=fix["corpus_root"],
        bin_path=fix["bin_path"],
        decision_path=fix["decision_path"],
        binding=fix["binding"],
        limits=mod.probe.Limits(),
        scratch_dir=fix["scratch"],
        receipts_path=fix["receipts"],
        entries=fix["entries"],
        seed=3,
        per_subdir=1,
        bounded_wall_s=0.0,
        enable_interrupt=False,
        enable_refusal_probe=False,
    )
    receipts = mod.ReceiptLog(fix["receipts"]).read()
    ok = mod.verify_proof(
        proof=proof, entries=fix["entries"], receipts=receipts, live_binding=fix["binding"]
    )
    assert ok["ok"] is True
    assert ok["errors"] == []

    tampered = json.loads(json.dumps(proof))
    tampered["subset"]["digest"] = "sha256:" + "0" * 64
    bad = mod.verify_proof(
        proof=tampered, entries=fix["entries"], receipts=receipts, live_binding=fix["binding"]
    )
    assert bad["ok"] is False
    assert "subset_digest_mismatch" in bad["errors"]


def test_prove_resume_refusal_probe_validates_closed_dictionary(tmp_path):
    real_bin = ROOT / "target/release/cleaned-project"
    if not real_bin.is_file():
        pytest.skip("real cleaned-project binary is absent")
    binding = binding_for(real_bin, code_revision="sha256:" + "1" * 64)
    probe_result = mod.run_refusal_probe(
        bin_path=real_bin,
        binding=binding,
        limits=mod.probe.Limits(),
        scratch_dir=tmp_path / "scratch",
        attempt=1,
    )
    assert probe_result["available"] is True
    assert probe_result["all_refused_typed"] is True
    assert "source:source_not_wordml" in probe_result["observed_classes"]
    assert "source:namespace_absent" in probe_result["observed_classes"]
    assert "source:unsupported_schema" in probe_result["observed_classes"]


def test_interrupt_attempt_via_timeout_preserves_receipts(tmp_path):
    names = [f"courts/f{index:03d}-normal.xml" for index in range(120)]
    fix = proof_fixture(tmp_path, names, scratch_name="interrupt-proof")
    result = mod.interrupt_attempt(
        manifest_path=fix["manifest_path"],
        corpus_root=fix["corpus_root"],
        bin_path=fix["bin_path"],
        decision_path=fix["decision_path"],
        scratch_dir=fix["scratch"],
        code_revision=fix["binding"].code_revision,
        processing_window_s=0.4,
    )
    assert result["mechanism"] == "timeout -s TERM"
    assert result["status"] == "interrupted"
    assert result["exit_code"] in (124, 128 + signal.SIGTERM)
    assert result["completed_preserved"] is True
    assert result["receipts_before"] == 0
    assert result["receipts_after"] >= 1
    assert result["in_flight_not_run"] is True
    assert result["in_flight_relative_path"] is not None


def test_cli_prove_resume_and_verify_proof(tmp_path, capsys):
    fix = proof_fixture(
        tmp_path,
        [
            "courts/a-normal.xml",
            "courts/b-refuse.xml",
            "fas/c-normal.xml",
            "fas/d-wirefail.xml",
        ],
    )
    out = tmp_path / "proof.json"
    code = mod.main(
        [
            "prove-resume",
            "--manifest",
            str(fix["manifest_path"]),
            "--corpus-root",
            str(fix["corpus_root"]),
            "--bin",
            str(fix["bin_path"]),
            "--decision",
            str(fix["decision_path"]),
            "--scratch",
            str(fix["scratch"]),
            "--receipts",
            str(fix["receipts"]),
            "--out",
            str(out),
            "--code-revision",
            fix["binding"].code_revision,
            "--seed",
            "1",
            "--per-subdir",
            "2",
            "--bounded-wall-s",
            "0",
            "--skip-interrupt",
            "--skip-refusal-probe",
        ]
    )
    assert code == mod.EXIT_OK
    capsys.readouterr()
    proof = json.loads(out.read_text(encoding="utf-8"))
    assert proof["final"]["verify_ledger_ok"] is True
    assert proof["subset"]["size"] == 4

    verify_code = mod.main(
        [
            "verify-proof",
            "--manifest",
            str(fix["manifest_path"]),
            "--bin",
            str(fix["bin_path"]),
            "--decision",
            str(fix["decision_path"]),
            "--scratch",
            str(fix["scratch"]),
            "--receipts",
            str(fix["receipts"]),
            "--proof",
            str(out),
            "--code-revision",
            fix["binding"].code_revision,
        ]
    )
    assert verify_code == mod.EXIT_OK
    verdict = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert verdict["ok"] is True


def test_measure_subprocess_does_not_orphan_child_on_interrupt(tmp_path):
    """Blocker M223-S03-no-orphan-after-interrupt: a SIGTERM unwinding the poll
    loop must SIGKILL and reap the running export child, never orphan it.

    The interrupt is delivered in a throwaway subprocess so the SIGTERM hits the
    harness frame (not the pytest runner); the child publishes its own pid, which
    is checked to be gone after the Interrupted unwinds.
    """
    child = (
        "import os,sys,time; sys.stdout.write(str(os.getpid())+'\\n'); "
        "sys.stdout.flush(); time.sleep(60)"
    )
    out = tmp_path / "child.pid"
    snippet = (
        "import signal, sys, threading, time\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(mod._SCRIPTS_DIR)!r})\n"
        "import m223_s02_probe as probe\n"
        f"out = Path({str(out)!r})\n"
        "def handler(sig, frame):\n"
        "    raise probe.Interrupted(sig)\n"
        "signal.signal(signal.SIGTERM, handler)\n"
        "def fire():\n"
        "    time.sleep(0.5)\n"
        "    import os\n"
        "    os.kill(os.getpid(), signal.SIGTERM)\n"
        "threading.Thread(target=fire, daemon=True).start()\n"
        "try:\n"
        f"    probe.measure_subprocess([{sys.executable!r}, '-c', {child!r}], "
        "timeout_s=30, stdout_path=out)\n"
        "    print('NO_INTERRUPT')\n"
        "except probe.Interrupted:\n"
        "    pid = int(out.read_text().split()[0])\n"
        "    time.sleep(0.3)\n"
        "    import os\n"
        "    try:\n"
        "        os.kill(pid, 0)\n"
        "        print('ORPHAN')\n"
        "    except ProcessLookupError:\n"
        "        print('REAPED')\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", snippet], capture_output=True, text=True, timeout=90
    )
    assert "REAPED" in completed.stdout, completed.stdout + completed.stderr
    assert "ORPHAN" not in completed.stdout

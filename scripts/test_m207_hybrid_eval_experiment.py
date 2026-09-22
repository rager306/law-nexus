#!/usr/bin/env python3
"""Offline suite for the M207 hybrid evaluator and records validator.

Uses throw-away roots for CLI drift and records tests. Does not mutate frozen
M207 pins, human stores, or the legal corpus.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "m207_hybrid_eval_experiment.py"
MARKER = "M207_HYBRID_SYNTHETIC_EXPERIMENT_OK"
RECORDS_MARKER = "M207_HYBRID_RECORDS_OK"
RECORD_REL = "prd/migration/rust-evidence/m207-hybrid-synthetic-experiment.json"
EVAL_MARKER = "M207_HYBRID_EVAL_OK"
EVAL_SCHEMA = "m207-hybrid-eval-report/v1"
S03_REPORT_REL = "prd/migration/rust-evidence/m207-s03-evaluation-report.json"
S03_BATTERY_REL = "prd/migration/rust-evidence/m207-s03-battery.json"
# Contract documents that must not drift while the evaluator is exercised.
RECORDS_CONTRACT_REL = "prd/annotation/m207-hybrid-records-contract.md"
EVAL_CONTRACT_REL = "prd/annotation/m207-hybrid-eval-contract.md"
# Pinned `--check` summary: the synthetic regression baseline. Score values are
# pinned exactly so a scorer edit cannot silently move the drift baseline.
PINNED_CHECK_SUMMARY = (
    "constructions=4 scenarios=13 detection_tp=22 detection_fp=1 detection_fn=2 "
    "field=59/75 provenance=36/50 rel_e2e=7/10 rel_cond=7/8 bundle_exact=4/13 "
    "ambiguity_groups=1"
)
# The eval contract must stay harness-local (R064): no Rust surface consumes it.
RUST_SURFACE_NEEDLES = ("m207-hybrid-eval-report", "M207_HYBRID_EVAL_OK", "--evaluate-records")
TIMEOUT = 30

FROZEN_PATHS = (
    "prd/annotation/m207-s01-codebook.md",
    "prd/annotation/m207-s01-schemas.json",
    "prd/annotation/m207-s02-coder-protocol.md",
    "prd/annotation/m207-s02-schemas.json",
    "prd/annotation/m207-s03-eval-protocol.md",
    "prd/annotation/m207-s03-schemas.json",
    "prd/migration/rust-evidence/m207-s01-pilot-cases.json",
    "prd/migration/rust-evidence/m207-s03-eval-manifest.json",
    "prd/annotation/m207-context-presentation-contract.md",
    "prd/annotation/m207-hybrid-records-contract.md",
    "prd/annotation/m207-hybrid-eval-contract.md",
    "prd/migration/rust-evidence/m207-context-inventory.json",
    "scripts/m207_context_inventory.py",
    "scripts/test_m207_context_inventory.py",
)

S03_METRIC_KEYS = (
    '"false_authority"',
    '"span_rate"',
    '"slot_rate"',
    '"scope_rate"',
    '"binding_rate"',
    '"abstention_rate"',
    '"aspect_rates"',
)

sys.path.insert(0, str(ROOT / "scripts"))
import m207_hybrid_eval_experiment as exp  # noqa: E402


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def frozen_fingerprint() -> dict[str, str]:
    out: dict[str, str] = {}
    for relative in FROZEN_PATHS:
        path = ROOT / relative
        if path.is_file():
            out[relative] = sha256_bytes(path.read_bytes())
        else:
            out[relative] = "absent"
    return out


EVAL_DIAGNOSTICS_BEGIN = "<!-- eval-diagnostics:begin -->"
EVAL_DIAGNOSTICS_END = "<!-- eval-diagnostics:end -->"
_DIAGNOSTIC_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def parse_eval_diagnostic_codes(text: str) -> set[str]:
    """Extract the closed eval-diagnostic set from a contract document.

    Exactly one marker block is expected, with one upper-case code per line.
    A missing or duplicated marker, an out-of-order block, an empty block, a
    duplicate code, or a non-code line is a hard error -- never a silent skip.
    """
    lines = text.splitlines()
    begins = [index for index, line in enumerate(lines) if line.strip() == EVAL_DIAGNOSTICS_BEGIN]
    ends = [index for index, line in enumerate(lines) if line.strip() == EVAL_DIAGNOSTICS_END]
    if len(begins) != 1 or len(ends) != 1:
        raise AssertionError(
            f"expected exactly one diagnostic block, begin={len(begins)} end={len(ends)}"
        )
    if begins[0] >= ends[0]:
        raise AssertionError("diagnostic block markers are out of order")
    codes: list[str] = []
    for line in lines[begins[0] + 1 : ends[0]]:
        stripped = line.strip()
        if not stripped:
            continue
        if not _DIAGNOSTIC_CODE_RE.match(stripped):
            raise AssertionError(f"non-code line in diagnostic block: {stripped!r}")
        codes.append(stripped)
    if not codes:
        raise AssertionError("diagnostic block is empty")
    if len(codes) != len(set(codes)):
        raise AssertionError("diagnostic block contains duplicate codes")
    return set(codes)


class HybridEvalExperimentTests(unittest.TestCase):
    def make_root(self) -> Path:
        directory = Path(tempfile.mkdtemp(prefix="m207-hybrid-eval-"))
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        return directory

    def run_cli(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPT), "--root", str(root), *extra]
        return subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=TIMEOUT
        )

    def assert_ok(self, result: subprocess.CompletedProcess[str], *needles: str) -> None:
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        blob = result.stdout + result.stderr
        self.assertIn(MARKER, blob)
        for needle in needles:
            self.assertIn(needle, blob)

    def assert_fail_closed(self, result: subprocess.CompletedProcess[str], diagnostic: str) -> None:
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(f"FAIL {diagnostic}", result.stderr)

    def write_artifact(self, root: Path) -> dict[str, Any]:
        self.assert_ok(self.run_cli(root, "--write"), "wrote=")
        return json.loads((root / RECORD_REL).read_text(encoding="utf-8"))

    def empty_bundle(self) -> dict[str, Any]:
        return exp.bundle(
            bid="empty",
            construction="shared-head-series",
            focus_id="none",
            context_status="available",
            declared_region=(),
            context_only=(),
            occs=(),
            rels=(),
        )

    def test_four_constructions_and_synthetic_limits(self) -> None:
        record = exp.build_record()
        self.assertEqual(record["constructions"], list(exp.CONSTRUCTIONS))
        self.assertEqual(record["schema"], exp.SCHEMA)
        self.assertEqual(record["lifecycle"], "[proposed]")
        self.assertIs(record["is_gold"], False)
        self.assertEqual(record["promotion"], "none")
        self.assertEqual(record["provenance"], "synthetic")
        self.assertIs(record["not_human"], True)
        self.assertIs(record["not_s03_metrics"], True)
        self.assertEqual(record["scenario_count"], 13)
        blob = json.dumps(record)
        for name in S03_METRIC_KEYS:
            self.assertNotIn(name, blob)
        series = next(row for row in record["scenarios"] if row["id"] == "series-correct")
        occ_ids = {item["id"] for item in series["expected"]["occurrences"]}
        self.assertEqual(occ_ids, {"occ-a", "occ-b"})
        self.assertEqual(series["expected"]["context_only"], ["syn-head"])
        for item in series["expected"]["occurrences"]:
            self.assertNotEqual(item["anchors"][0]["fragment_id"], "syn-head")

    def test_correct_kind_wrong_inheritance_is_provenance_error(self) -> None:
        record = exp.build_record()
        row = next(item for item in record["scenarios"] if item["id"] == "series-wrong-provenance")
        hybrid = row["hybrid"]
        self.assertEqual(hybrid["detection"], {"tp": 2, "fp": 0, "fn": 0})
        self.assertEqual(hybrid["field_value"]["value"], "6/6")
        self.assertEqual(hybrid["provenance"]["value"], "0/4")
        self.assertIs(hybrid["bundle_exact"], False)
        self.assertEqual(hybrid["relation_e2e"]["tp"], 1)
        self.assertEqual(hybrid["relation_e2e"]["fn"], 0)

    def test_missing_extra_wrong_field_relation_and_unavailable(self) -> None:
        record = exp.build_record()
        by_id = {row["id"]: row["hybrid"] for row in record["scenarios"]}
        missing = by_id["series-missing-member"]
        self.assertEqual(missing["detection"], {"tp": 1, "fp": 0, "fn": 1})
        extra = by_id["series-extra-head-as-act"]
        self.assertEqual(extra["detection"], {"tp": 2, "fp": 1, "fn": 0})
        field = by_id["agreement-wrong-field"]
        self.assertEqual(field["detection"], {"tp": 2, "fp": 0, "fn": 0})
        self.assertEqual(field["field_value"]["value"], "5/6")
        self.assertEqual(field["provenance"]["value"], "4/4")
        rel = by_id["annex-wrong-relation"]
        self.assertEqual(rel["field_value"]["value"], "6/6")
        self.assertEqual(rel["relation_e2e"]["tp"], 0)
        self.assertEqual(rel["relation_e2e"]["fp"], 1)
        self.assertEqual(rel["relation_e2e"]["fn"], 1)
        self.assertEqual(rel["relation_conditional"]["value"], "0/1")
        unavailable = by_id["series-unavailable-context"]
        self.assertEqual(unavailable["unresolved"]["value"], "0/2")
        self.assertEqual(
            unavailable["unresolved"]["predicted_resolved_when_expected_unresolved"], 2
        )
        missed = by_id["agreement-missed-endpoint"]
        self.assertEqual(missed["relation_e2e"]["fn"], 1)
        self.assertEqual(missed["relation_conditional"]["status"], "not-measured")

    def test_duplicate_anchor_is_explicit_not_best_match(self) -> None:
        record = exp.build_record()
        row = next(
            item for item in record["scenarios"] if item["id"] == "duplicate-anchor-ambiguous"
        )
        hybrid = row["hybrid"]
        self.assertEqual(hybrid["detection"], {"tp": 0, "fp": 0, "fn": 0})
        self.assertEqual(hybrid["ambiguity"]["groups"], 1)
        self.assertEqual(hybrid["alignment"]["unique_pairs"], [])
        self.assertEqual(hybrid["field_value"]["value"], "0/3")
        self.assertIs(hybrid["bundle_exact"], False)

    def test_repeated_values_do_not_rematch_by_date_or_number(self) -> None:
        record = exp.build_record()
        row = next(
            item for item in record["scenarios"] if item["id"] == "repeat-values-distinct-spans"
        )
        hybrid = row["hybrid"]
        self.assertEqual(
            hybrid["alignment"]["unique_pairs"], [["occ-a", "occ-a"], ["occ-b", "occ-b"]]
        )
        self.assertEqual(hybrid["field_value"]["value"], "4/6")
        self.assertEqual(hybrid["detection"], {"tp": 2, "fp": 0, "fn": 0})

    def test_local_focus_conceals_missing_member_hybrid_does_not(self) -> None:
        record = exp.build_record()
        row = next(item for item in record["scenarios"] if item["id"] == "series-missing-member")
        self.assertEqual(row["local_focus"]["detection"], {"tp": 1, "fp": 0, "fn": 0})
        self.assertIs(row["local_focus"]["bundle_exact"], True)
        self.assertEqual(row["hybrid"]["detection"]["fn"], 1)
        self.assertIs(row["hybrid"]["bundle_exact"], False)
        comparison = record["comparison"]
        self.assertIn("Not S03 metrics", comparison["disclaimer"])
        self.assertIn("detection", comparison["local_focus"])
        self.assertIn("value", comparison["exact_bundle"])
        self.assertIn("detection", comparison["hybrid"])

    def test_empty_denominator_is_not_measured(self) -> None:
        empty = self.empty_bundle()
        scores = exp.score_pair(empty, empty)
        self.assertEqual(scores["field_value"]["status"], "not-measured")
        self.assertIsNone(scores["field_value"]["value"])
        self.assertEqual(scores["provenance"]["status"], "not-measured")
        self.assertEqual(scores["relation_e2e"]["status"], "not-measured")
        self.assertEqual(scores["unresolved"]["status"], "not-measured")
        predicted = exp.clone(empty)
        predicted["occurrences"] = [
            exp.occ(
                "occ-x",
                [exp.anchor(exp.AG_FRAG, exp.AG_SPAN)],
                kind=exp.KIND_AGREEMENT,
                date=exp.DATE_AG,
                number=exp.NUM_AG,
                date_src=exp.own_src(exp.AG_FRAG, exp.AG_SPAN),
                number_src=exp.own_src(exp.AG_FRAG, exp.AG_SPAN),
            )
        ]
        predicted["focus_id"] = "occ-x"
        extra = exp.score_pair(empty, predicted)
        self.assertEqual(extra["detection"], {"tp": 0, "fp": 1, "fn": 0})
        self.assertEqual(extra["field_value"]["status"], "not-measured")

    def test_malformed_refs_fail_closed(self) -> None:
        base = exp.agreement_expected()
        broken = exp.clone(base)
        broken["occurrences"][0]["anchors"] = []
        with self.assertRaises(exp.ExperimentError) as ctx:
            exp.validate_bundle(broken, "expected")
        self.assertEqual(ctx.exception.diagnostic, "MALFORMED_REF")
        span = exp.clone(base)
        span["occurrences"][0]["anchors"][0]["end"] = 0
        with self.assertRaises(exp.ExperimentError) as ctx:
            exp.validate_bundle(span, "expected")
        self.assertEqual(ctx.exception.diagnostic, "MALFORMED_REF")
        fields = exp.clone(base)
        del fields["occurrences"][0]["fields"]["date"]
        with self.assertRaises(exp.ExperimentError) as ctx:
            exp.validate_bundle(fields, "predicted")
        self.assertEqual(ctx.exception.diagnostic, "MALFORMED_REF")

    def test_dangling_edges_fail_closed(self) -> None:
        base = exp.agreement_expected()
        dangling = exp.clone(base)
        dangling["relations"][0]["to"] = "missing-occ"
        with self.assertRaises(exp.ExperimentError) as ctx:
            exp.validate_bundle(dangling, "predicted")
        self.assertEqual(ctx.exception.diagnostic, "DANGLING_EDGE")
        focus = exp.clone(base)
        focus["focus_id"] = "missing-focus"
        with self.assertRaises(exp.ExperimentError) as ctx:
            exp.validate_bundle(focus, "expected")
        self.assertEqual(ctx.exception.diagnostic, "DANGLING_EDGE")

    def test_alignment_invariant_to_record_order(self) -> None:
        expected = exp.agreement_expected()
        predicted = exp.agreement_expected()
        predicted["occurrences"] = list(reversed(predicted["occurrences"]))
        predicted["relations"] = list(reversed(predicted["relations"]))
        scores = exp.score_pair(expected, predicted)
        self.assertEqual(
            scores["alignment"]["unique_pairs"], [["occ-a", "occ-a"], ["occ-b", "occ-b"]]
        )
        self.assertEqual(scores["detection"], {"tp": 2, "fp": 0, "fn": 0})
        self.assertIs(scores["bundle_exact"], True)

    def test_changed_labels_do_not_rematch(self) -> None:
        expected = exp.repeat_expected()
        predicted = exp.pred_swapped_kinds()
        predicted["occurrences"][0]["id"] = "renamed-a"
        predicted["occurrences"][1]["id"] = "renamed-b"
        predicted["relations"][0]["from"] = "renamed-a"
        predicted["relations"][0]["to"] = "renamed-b"
        predicted["focus_id"] = "renamed-a"
        scores = exp.score_pair(expected, predicted)
        self.assertEqual(
            scores["alignment"]["unique_pairs"],
            [["occ-a", "renamed-a"], ["occ-b", "renamed-b"]],
        )
        self.assertEqual(scores["field_value"]["value"], "4/6")
        self.assertEqual(scores["relation_e2e"]["tp"], 1)

    def test_default_is_check_and_does_not_write(self) -> None:
        root = self.make_root()
        target = root / RECORD_REL
        self.assertFalse(target.exists())
        self.assert_fail_closed(self.run_cli(root), "MISSING_ARTIFACT")
        self.assertFalse(target.exists())
        self.assert_fail_closed(self.run_cli(root, "--check"), "MISSING_ARTIFACT")
        self.assertFalse(target.exists())

    def test_stale_check_does_not_rewrite(self) -> None:
        root = self.make_root()
        payload = self.write_artifact(root)
        target = root / RECORD_REL
        original = target.read_bytes()
        stale = json.loads(original.decode("utf-8"))
        stale["summary"]["hybrid"]["detection"]["tp"] = 99
        mutated = (json.dumps(stale, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
        target.write_bytes(mutated)
        self.assert_fail_closed(self.run_cli(root, "--check"), "STALE_ARTIFACT")
        self.assertEqual(target.read_bytes(), mutated)
        self.assert_fail_closed(self.run_cli(root), "STALE_ARTIFACT")
        self.assertEqual(target.read_bytes(), mutated)
        self.assertNotEqual(mutated, original)
        self.assertEqual(payload["schema"], exp.SCHEMA)

    def test_check_and_write_together_is_usage_error(self) -> None:
        root = self.make_root()
        result = self.run_cli(root, "--check", "--write")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("FAIL USAGE", result.stderr)
        self.assertFalse((root / RECORD_REL).exists())

    def test_write_then_check_is_stable(self) -> None:
        root = self.make_root()
        self.write_artifact(root)
        self.assert_ok(self.run_cli(root, "--check"), "drift=0")
        self.assert_ok(self.run_cli(root), "drift=0")

    def test_no_frozen_side_effects(self) -> None:
        before = frozen_fingerprint()
        root = self.make_root()
        self.write_artifact(root)
        self.assert_ok(self.run_cli(root, "--check"), "drift=0")
        after = frozen_fingerprint()
        self.assertEqual(before, after)
        self.assertFalse((ROOT / RECORD_REL).exists() and root == ROOT)


class HybridRecordsContractTests(unittest.TestCase):
    def make_root(self) -> Path:
        directory = Path(tempfile.mkdtemp(prefix="m207-hybrid-records-"))
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        return directory

    def run_cli(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPT), "--root", str(root), *extra]
        return subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=TIMEOUT
        )

    def write_records(
        self, root: Path, payload: dict[str, Any], name: str = "records.json"
    ) -> Path:
        path = root / name
        path.write_bytes(exp.canonical_json_bytes(payload))
        return path

    def report_from(self, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        return json.loads(result.stdout)

    def assert_records_ok(self, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn(RECORDS_MARKER, result.stderr)
        report = self.report_from(result)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["marker"], RECORDS_MARKER)
        self.assertEqual(report["diagnostics"], [])
        return report

    def assert_records_fail(
        self, result: subprocess.CompletedProcess[str], diagnostic: str
    ) -> dict[str, Any]:
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(f"FAIL {diagnostic}", result.stderr)
        report = self.report_from(result)
        self.assertEqual(report["status"], "invalid")
        self.assertIsNone(report["marker"])
        codes = [row["code"] for row in report["diagnostics"]]
        self.assertIn(diagnostic, codes)
        return report

    def test_external_happy_series_bytes_present(self) -> None:
        root = self.make_root()
        payload = exp.example_hybrid_records(origin="synthetic", with_bytes=True)
        path = self.write_records(root, payload)
        result = self.run_cli(root, "--validate-records", str(path))
        report = self.assert_records_ok(result)
        self.assertEqual(report["provenance_origin"], "synthetic")
        self.assertEqual(report["source_validation"], "bytes-present")
        self.assertEqual(report["bundles"], 4)
        self.assertEqual(report["documents"], 4)

    def test_rust_runtime_origin_is_accepted(self) -> None:
        root = self.make_root()
        payload = exp.example_hybrid_records(origin="rust-runtime", with_bytes=True)
        path = self.write_records(root, payload, "rust-series.json")
        result = self.run_cli(root, "--validate-records", str(path))
        report = self.assert_records_ok(result)
        self.assertEqual(report["provenance_origin"], "rust-runtime")

    def test_metadata_only_does_not_claim_bytes(self) -> None:
        root = self.make_root()
        payload = exp.example_hybrid_records(origin="synthetic", with_bytes=False)
        path = self.write_records(root, payload, "meta.json")
        report = self.assert_records_ok(self.run_cli(root, "--validate-records", str(path)))
        self.assertEqual(report["source_validation"], "metadata-only")
        claimed = exp.clone(payload)
        claimed["source_validation"] = "bytes-present"
        bad = self.write_records(root, claimed, "claimed.json")
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(bad)),
            "SOURCE_CLAIM_WITHOUT_BYTES",
        )

    def test_unsupported_version_fails(self) -> None:
        root = self.make_root()
        payload = exp.example_hybrid_records()
        payload["schema_version"] = 2
        path = self.write_records(root, payload, "v2.json")
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(path)), "UNSUPPORTED_VERSION"
        )
        payload["schema_version"] = 1
        payload["schema"] = exp.SCHEMA
        other = self.write_records(root, payload, "synthetic-schema.json")
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(other)), "UNSUPPORTED_VERSION"
        )

    def test_invalid_bounds_and_utf8_split(self) -> None:
        root = self.make_root()
        payload = exp.example_hybrid_records()
        series = next(row for row in payload["bundles"] if row["bundle_id"] == "series")
        series["occurrences"][0]["anchors"][0]["end"] = 99
        path = self.write_records(root, payload, "bounds.json")
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(path)), "INVALID_BOUNDS"
        )
        split = {
            "schema": exp.RECORDS_SCHEMA,
            "schema_version": 1,
            "provenance_origin": "synthetic",
            "source_validation": "bytes-present",
            "documents": [
                {
                    "document_id": "doc-utf8",
                    "fragments": [
                        {
                            "fragment_id": "frag-e",
                            "byte_length": 2,
                            "source_utf8": "é",
                        }
                    ],
                }
            ],
            "bundles": [
                exp.bundle(
                    bid="utf8",
                    construction="agreement-refers-to-contract",
                    focus_id="occ-a",
                    context_status="available",
                    declared_region=("frag-e",),
                    context_only=(),
                    occs=(
                        exp.occ(
                            "occ-a",
                            [{"fragment_id": "frag-e", "start": 1, "end": 2}],
                            kind=exp.KIND_AGREEMENT,
                            date=None,
                            number=None,
                            date_src=None,
                            number_src=None,
                        ),
                    ),
                    rels=(),
                )
            ],
        }
        split_path = self.write_records(root, split, "split.json")
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(split_path)), "INVALID_BOUNDS"
        )

    def test_cross_doc_refs_fail(self) -> None:
        root = self.make_root()
        payload = exp.example_hybrid_records(include_alias=False)
        docs = payload["documents"]
        series_doc = next(row for row in docs if row["document_id"] == "doc-series")
        moved = next(row for row in series_doc["fragments"] if row["fragment_id"] == exp.M2_FRAG)
        series_doc["fragments"] = [
            row for row in series_doc["fragments"] if row["fragment_id"] != exp.M2_FRAG
        ]
        docs.append({"document_id": "doc-other", "fragments": [moved]})
        path = self.write_records(root, payload, "cross.json")
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(path)), "CROSS_DOC_REF"
        )

    def test_dangling_endpoints_fail(self) -> None:
        root = self.make_root()
        payload = exp.example_hybrid_records(include_alias=False)
        payload["bundles"][0]["relations"][0]["to"] = "missing-occ"
        path = self.write_records(root, payload, "dangling-rel.json")
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(path)), "DANGLING_EDGE"
        )
        payload = exp.example_hybrid_records(include_alias=False)
        payload["bundles"][0]["occurrences"][0]["anchors"][0]["fragment_id"] = "missing-frag"
        missing = self.write_records(root, payload, "dangling-frag.json")
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(missing)), "DANGLING_EDGE"
        )

    def test_missing_and_malformed_input(self) -> None:
        root = self.make_root()
        missing = root / "absent.json"
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(missing)), "MISSING_INPUT"
        )
        broken = root / "broken.json"
        broken.write_text("{not-json", encoding="utf-8")
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(broken)), "MALFORMED_REF"
        )
        empty = self.write_records(root, {"schema": exp.RECORDS_SCHEMA}, "empty.json")
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(empty)), "MALFORMED_REF"
        )
        human = exp.example_hybrid_records()
        human["provenance_origin"] = "human-reviewed"
        human_path = self.write_records(root, human, "human.json")
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(human_path)),
            "PROVENANCE_FORBIDDEN",
        )

    def test_hostile_encodings_and_object_shape_fail_closed(self) -> None:
        root = self.make_root()
        cases = (
            ("zero-byte.json", b""),
            ("bom.json", b"\xef\xbb\xbf{}"),
            ("array.json", b"[1, 2, 3]"),
            ("null.json", b"null"),
            ("string.json", b'"records"'),
            ("trailing.json", b'{"schema": "m207-hybrid-records/v1"} trailing'),
            ("invalid-utf8.json", b'{"schema": "\xff\xfe"}'),
        )
        for name, raw in cases:
            with self.subTest(name=name):
                path = root / name
                path.write_bytes(raw)
                self.assert_records_fail(
                    self.run_cli(root, "--validate-records", str(path)), "MALFORMED_REF"
                )
                self.assertEqual(path.read_bytes(), raw)

    def test_directory_and_protected_symlink_fail_closed(self) -> None:
        root = self.make_root()
        directory = root / "as-directory"
        directory.mkdir()
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(directory)), "MISSING_INPUT"
        )
        real = self.write_records(root, exp.example_hybrid_records(), "ok.json")
        self.assert_records_ok(self.run_cli(root, "--validate-records", str(real)))
        for relative in (
            "prd/annotation/m207-s01-codebook.md",
            RECORD_REL,
        ):
            with self.subTest(protected=relative):
                target = ROOT / relative
                if not target.is_file():
                    continue
                before = target.read_bytes()
                link = root / ("link-" + Path(relative).name)
                link.symlink_to(target)
                self.assert_records_fail(
                    self.run_cli(root, "--validate-records", str(link)), "PROTECTED_PATH"
                )
                self.assertEqual(target.read_bytes(), before)

    def test_duplicate_anchor_is_explicit(self) -> None:
        root = self.make_root()
        payload = exp.example_hybrid_records(include_alias=False)
        focus = exp.clone(payload["bundles"][1]["occurrences"][0])
        twin = exp.clone(focus)
        twin["id"] = "occ-dup"
        payload["bundles"][1]["occurrences"].append(twin)
        path = self.write_records(root, payload, "dup.json")
        self.assert_records_fail(
            self.run_cli(root, "--validate-records", str(path)), "AMBIGUOUS_DUPLICATE"
        )

    def test_deterministic_roundtrip(self) -> None:
        payload = exp.example_hybrid_records(origin="rust-runtime")
        first = exp.canonical_json_bytes(payload)
        loaded = json.loads(first.decode("utf-8"))
        second = exp.canonical_json_bytes(loaded)
        self.assertEqual(first, second)
        report_a = exp.validate_hybrid_records(loaded, "records")
        report_b = exp.validate_hybrid_records(json.loads(second.decode("utf-8")), "records")
        self.assertEqual(report_a, report_b)
        self.assertEqual(report_a["status"], "ok")
        root = self.make_root()
        path = self.write_records(root, loaded, "roundtrip.json")
        original = path.read_bytes()
        self.assert_records_ok(self.run_cli(root, "--validate-records", str(path)))
        self.assertEqual(path.read_bytes(), original)

    def test_records_cli_is_read_only_and_refuses_protected_paths(self) -> None:
        root = self.make_root()
        payload = exp.example_hybrid_records()
        path = self.write_records(root, payload, "ok.json")
        original = path.read_bytes()
        usage = self.run_cli(root, "--validate-records", str(path), "--write")
        self.assertEqual(usage.returncode, 2, usage.stderr)
        self.assert_records_fail(usage, "USAGE")
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse((root / RECORD_REL).exists())
        protected = root / RECORD_REL
        protected.parent.mkdir(parents=True, exist_ok=True)
        protected.write_bytes(original)
        relative = self.run_cli(root, "--validate-records", RECORD_REL)
        self.assert_records_fail(relative, "PROTECTED_PATH")
        self.assertEqual(protected.read_bytes(), original)
        frozen = ROOT / "prd/annotation/m207-s01-codebook.md"
        if frozen.is_file():
            before = frozen.read_bytes()
            abs_fail = self.run_cli(root, "--validate-records", str(frozen))
            self.assert_records_fail(abs_fail, "PROTECTED_PATH")
            self.assertEqual(frozen.read_bytes(), before)

    def test_records_cli_does_not_touch_frozen_or_synthetic_store(self) -> None:
        before = frozen_fingerprint()
        root = self.make_root()
        path = self.write_records(root, exp.example_hybrid_records())
        self.assert_records_ok(self.run_cli(root, "--validate-records", str(path)))
        self.assertEqual(frozen_fingerprint(), before)
        self.assertFalse((root / RECORD_REL).exists())


class HybridRecordsRejectionTests(unittest.TestCase):
    """Regression coverage for the closed, honest, fail-closed envelope.

    Every case here previously validated as ``status=ok`` with the success
    marker, which made the executable gate weaker than its own contract.
    """

    def make_root(self) -> Path:
        directory = Path(tempfile.mkdtemp(prefix="m207-hybrid-reject-"))
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        return directory

    def run_cli(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPT), "--root", str(root), *extra]
        return subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=TIMEOUT
        )

    def write_records(self, root: Path, payload: dict[str, Any], name: str) -> Path:
        path = root / name
        path.write_bytes(exp.canonical_json_bytes(payload))
        return path

    def assert_rejected(self, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn(RECORDS_MARKER, result.stdout)
        self.assertNotIn(RECORDS_MARKER, result.stderr)
        self.assertIn("FAIL MALFORMED_REF", result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "invalid")
        self.assertIsNone(report["marker"])
        codes = [row["code"] for row in report["diagnostics"]]
        self.assertIn("MALFORMED_REF", codes)
        return report

    def assert_accepted(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn(RECORDS_MARKER, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "ok")

    def test_dishonest_honesty_keys_fail_closed(self) -> None:
        root = self.make_root()
        cases: tuple[tuple[str, Any], ...] = (
            ("is_gold", True),
            ("authoritative", True),
            ("not_human", False),
            ("not_s03_metrics", False),
            ("lifecycle", ["validated"]),
            ("lifecycle", ["proposed", "validated"]),
            ("lifecycle", "[proposed]"),
            ("alignment_policy", "best-match"),
            ("alignment_policy", ""),
            ("authoritative", 0),
            ("not_human", 1),
        )
        for index, (key, value) in enumerate(cases):
            with self.subTest(key=key, value=value):
                payload = exp.example_hybrid_records(origin="rust-runtime")
                payload[key] = value
                path = self.write_records(root, payload, f"dishonest-{index}.json")
                self.assert_rejected(self.run_cli(root, "--validate-records", str(path)))

    def test_synthetic_bytes_cannot_be_relabelled_as_gold(self) -> None:
        root = self.make_root()
        payload = exp.example_hybrid_records(origin="rust-runtime")
        payload.update(
            {
                "is_gold": True,
                "authoritative": True,
                "not_human": False,
                "not_s03_metrics": False,
                "lifecycle": ["validated"],
                "alignment_policy": "best-match",
            }
        )
        path = self.write_records(root, payload, "relabelled-gold.json")
        report = self.assert_rejected(self.run_cli(root, "--validate-records", str(path)))
        self.assertIn("honesty key", report["diagnostics"][0]["detail"])

    def test_honest_and_absent_honesty_keys_are_accepted(self) -> None:
        root = self.make_root()
        honest = exp.example_hybrid_records(origin="synthetic")
        self.assert_accepted(
            self.run_cli(
                root,
                "--validate-records",
                str(self.write_records(root, honest, "honest.json")),
            )
        )
        bare = exp.clone(honest)
        for key, _ in exp.RECORDS_HONESTY_VALUES:
            bare.pop(key)
        self.assert_accepted(
            self.run_cli(
                root,
                "--validate-records",
                str(self.write_records(root, bare, "bare.json")),
            )
        )

    def test_bundle_and_list_types_fail_closed_with_json_diagnostics(self) -> None:
        root = self.make_root()

        def declared_region_int(payload: dict[str, Any]) -> None:
            payload["bundles"][0]["declared_region"] = 1

        def declared_region_str(payload: dict[str, Any]) -> None:
            payload["bundles"][0]["declared_region"] = "syn-head"

        def declared_region_element_int(payload: dict[str, Any]) -> None:
            payload["bundles"][0]["declared_region"] = [1]

        def declared_region_element_empty(payload: dict[str, Any]) -> None:
            payload["bundles"][0]["declared_region"] = [""]

        def context_only_str(payload: dict[str, Any]) -> None:
            payload["bundles"][0]["context_only"] = "syn-head"

        def context_only_int(payload: dict[str, Any]) -> None:
            payload["bundles"][0]["context_only"] = 5

        def bundle_id_int(payload: dict[str, Any]) -> None:
            payload["bundles"][0]["bundle_id"] = 123

        def construction_int(payload: dict[str, Any]) -> None:
            payload["bundles"][0]["construction"] = 7

        def construction_empty(payload: dict[str, Any]) -> None:
            payload["bundles"][0]["construction"] = ""

        def context_status_int(payload: dict[str, Any]) -> None:
            payload["bundles"][0]["context_status"] = 9

        cases = (
            ("declared-region-int", declared_region_int),
            ("declared-region-str", declared_region_str),
            ("declared-region-element-int", declared_region_element_int),
            ("declared-region-element-empty", declared_region_element_empty),
            ("context-only-str", context_only_str),
            ("context-only-int", context_only_int),
            ("bundle-id-int", bundle_id_int),
            ("construction-int", construction_int),
            ("construction-empty", construction_empty),
            ("context-status-int", context_status_int),
        )
        for name, mutate in cases:
            with self.subTest(name=name):
                payload = exp.example_hybrid_records(include_alias=False)
                mutate(payload)
                path = self.write_records(root, payload, f"shape-{name}.json")
                self.assert_rejected(self.run_cli(root, "--validate-records", str(path)))

    def test_closed_allow_list_rejects_unknown_and_forbidden_keys(self) -> None:
        root = self.make_root()

        def top(key: str) -> Any:
            def mutate(payload: dict[str, Any]) -> None:
                payload[key] = "injected"

            return mutate

        def on_occurrence(key: str, value: Any) -> Any:
            def mutate(payload: dict[str, Any]) -> None:
                payload["bundles"][0]["occurrences"][0][key] = value

            return mutate

        def on_relation(key: str, value: Any) -> Any:
            def mutate(payload: dict[str, Any]) -> None:
                payload["bundles"][0]["relations"][0][key] = value

            return mutate

        def on_field_slot(key: str, value: Any) -> Any:
            def mutate(payload: dict[str, Any]) -> None:
                payload["bundles"][0]["occurrences"][0]["fields"]["kind"][key] = value

            return mutate

        def on_fields_container(key: str, value: Any) -> Any:
            def mutate(payload: dict[str, Any]) -> None:
                payload["bundles"][0]["occurrences"][0]["fields"][key] = value

            return mutate

        def on_anchor(key: str, value: Any) -> Any:
            def mutate(payload: dict[str, Any]) -> None:
                payload["bundles"][0]["occurrences"][0]["anchors"][0][key] = value

            return mutate

        def on_document(key: str) -> Any:
            def mutate(payload: dict[str, Any]) -> None:
                payload["documents"][0][key] = "injected"

            return mutate

        def on_fragment(key: str) -> Any:
            def mutate(payload: dict[str, Any]) -> None:
                payload["documents"][0]["fragments"][0][key] = "injected"

            return mutate

        cases = (
            ("envelope-s03-rate", top("span_rate")),
            ("envelope-s03-rate-false-authority", top("false_authority")),
            ("envelope-s03-aspect-rates", top("aspect_rates")),
            ("envelope-raw-corpus", top("corpus_excerpt")),
            ("envelope-raw-legal-text", top("raw_legal_text")),
            ("envelope-coder-submission", top("submissions")),
            ("envelope-coder-id", top("coder_id")),
            ("envelope-unknown", top("future_field")),
            ("document-unknown", on_document("hash")),
            ("fragment-unknown", on_fragment("encoding")),
            ("bundle-unknown", top("nothing")),
            ("occurrence-unknown", on_occurrence("legal_type", "договор")),
            ("occurrence-rate", on_occurrence("slot_rate", 0.9)),
            ("relation-unknown", on_relation("weight", 1)),
            ("field-slot-unknown", on_field_slot("confidence", 0.9)),
            ("fields-container-unknown", on_fields_container("confidence", 0.9)),
            ("anchor-unknown", on_anchor("confidence", 1)),
        )
        for index, (name, mutate) in enumerate(cases):
            with self.subTest(name=name):
                payload = exp.example_hybrid_records(include_alias=False)
                if name == "bundle-unknown":
                    payload["bundles"][0]["future_key"] = 1
                elif name == "envelope-unknown":
                    payload["future_field"] = 1
                else:
                    mutate(payload)
                path = self.write_records(root, payload, f"closed-{index}.json")
                self.assert_rejected(self.run_cli(root, "--validate-records", str(path)))


class HybridEvalReportTests(unittest.TestCase):
    """Read-only differential evaluator (--evaluate-records) contract."""

    def make_root(self) -> Path:
        directory = Path(tempfile.mkdtemp(prefix="m207-hybrid-eval-report-"))
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        return directory

    def run_cli(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPT), "--root", str(root), *extra]
        return subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=TIMEOUT
        )

    def write_records(
        self, root: Path, payload: dict[str, Any], name: str = "records.json"
    ) -> Path:
        path = root / name
        path.write_bytes(exp.canonical_json_bytes(payload))
        return path

    def eval_cli(
        self, root: Path, expected: Any, predicted: Any
    ) -> subprocess.CompletedProcess[str]:
        return self.run_cli(root, "--evaluate-records", str(expected), str(predicted))

    def report_from(self, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        return json.loads(result.stdout)

    def assert_eval_ok(self, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn(EVAL_MARKER, result.stderr)
        self.assertNotIn(RECORDS_MARKER, result.stderr)
        report = self.report_from(result)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["marker"], EVAL_MARKER)
        self.assertEqual(report["diagnostics"], [])
        return report

    def assert_eval_fail(
        self,
        result: subprocess.CompletedProcess[str],
        diagnostic: str,
        *,
        exit_code: int = 1,
    ) -> dict[str, Any]:
        self.assertEqual(result.returncode, exit_code, result.stderr + result.stdout)
        self.assertIn(f"FAIL {diagnostic}", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn(EVAL_MARKER, result.stderr)
        report = self.report_from(result)
        self.assertEqual(report["status"], "invalid")
        self.assertIsNone(report["marker"])
        codes = [row["code"] for row in report["diagnostics"]]
        self.assertIn(diagnostic, codes)
        return report

    def write_pair(self, root: Path) -> tuple[Path, Path]:
        payload = exp.example_hybrid_records()
        expected = self.write_records(root, payload, "expected.json")
        predicted = self.write_records(root, payload, "predicted.json")
        return expected, predicted

    def test_identical_records_are_differential_not_gold(self) -> None:
        root = self.make_root()
        expected, predicted = self.write_pair(root)
        report = self.assert_eval_ok(self.eval_cli(root, expected, predicted))
        self.assertEqual(report["schema"], EVAL_SCHEMA)
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["expected_provenance_origin"], "synthetic")
        self.assertEqual(report["predicted_provenance_origin"], "synthetic")
        self.assertEqual(report["lifecycle"], ["proposed"])
        self.assertEqual(report["evidence_classes"], ["differential", "metamorphic"])
        self.assertEqual(report["reference_role"], "harness-expected")
        self.assertEqual(report["alignment_policy"], "local-anchor-identity-v1")
        self.assertIs(report["authoritative"], False)
        self.assertIs(report["is_gold"], False)
        self.assertIs(report["not_human"], True)
        self.assertIs(report["not_s03_metrics"], True)
        self.assertIn("not-measured", report["not_measured_policy"])
        hybrid = report["differential"]["planes"]["hybrid"]
        self.assertEqual(hybrid["detection"], {"tp": 8, "fp": 0, "fn": 0})
        for key in (
            "field_value",
            "provenance",
            "relation_e2e",
            "relation_conditional",
            "unresolved",
            "bundle_exact",
        ):
            self.assertEqual(hybrid[key]["status"], "measured", key)
        self.assertEqual(hybrid["field_value"]["value"], "24/24")
        self.assertEqual(hybrid["provenance"]["value"], "16/16")
        self.assertEqual(hybrid["relation_e2e"]["value"], "3/3")
        self.assertEqual(hybrid["relation_conditional"]["value"], "3/3")
        self.assertEqual(hybrid["unresolved"]["value"], "8/8")
        self.assertEqual(hybrid["bundle_exact"]["value"], "4/4")
        self.assertEqual(hybrid["ambiguity_groups"], 0)
        local = report["differential"]["planes"]["local_focus"]
        for key in ("field_value", "provenance", "bundle_exact"):
            self.assertEqual(local[key]["status"], "measured", key)
        alignment = report["differential"]["bundle_alignment"]
        self.assertEqual(alignment["matched"], ["agreement", "alias", "annex", "series"])
        self.assertEqual(alignment["expected_only"], [])
        self.assertEqual(alignment["predicted_only"], [])
        self.assertEqual(alignment["expected_bundles"], 4)
        self.assertEqual(alignment["predicted_bundles"], 4)
        metamorphic = report["metamorphic"]
        self.assertEqual(metamorphic["evidence_class"], "metamorphic")
        self.assertEqual(
            [row["name"] for row in metamorphic["properties"]],
            [name for name, _ in exp.METAMORPHIC_PROPERTIES],
        )
        for row in metamorphic["properties"]:
            self.assertEqual(row["status"], "passed", row["name"])
            self.assertTrue(row["detail"], row["name"])
        self.assertEqual(metamorphic["properties_executed"], 4)
        self.assertEqual(metamorphic["properties_passed"], 4)
        self.assertEqual(metamorphic["verdict"]["value"], "4/4")

    def test_eval_marker_is_distinct_from_records_marker(self) -> None:
        self.assertNotEqual(EVAL_MARKER, RECORDS_MARKER)
        self.assertNotEqual(EVAL_MARKER, exp.MARKER)
        root = self.make_root()
        expected, predicted = self.write_pair(root)
        result = self.eval_cli(root, expected, predicted)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(EVAL_MARKER, result.stderr)
        self.assertNotIn(RECORDS_MARKER, result.stderr)
        self.assertNotIn(exp.MARKER, result.stderr)

    def test_usage_guards_reject_forbidden_combinations(self) -> None:
        root = self.make_root()
        expected, predicted = self.write_pair(root)
        for extra in (
            ("--write",),
            ("--check",),
            ("--validate-records", str(expected)),
        ):
            with self.subTest(extra=extra):
                result = self.run_cli(
                    root, "--evaluate-records", str(expected), str(predicted), *extra
                )
                report = self.assert_eval_fail(result, "USAGE", exit_code=2)
                self.assertIsNone(report["differential"])
                self.assertFalse((root / RECORD_REL).exists())

    def test_protected_paths_are_refused_on_both_sides(self) -> None:
        root = self.make_root()
        safe = self.write_records(root, exp.example_hybrid_records(), "ok.json")
        for relative in (RECORD_REL, S03_REPORT_REL):
            with self.subTest(protected=relative, side="expected"):
                report = self.assert_eval_fail(
                    self.eval_cli(root, relative, safe), "PROTECTED_PATH"
                )
                self.assertIn("expected", report["diagnostics"][0]["detail"])
            with self.subTest(protected=relative, side="predicted"):
                report = self.assert_eval_fail(
                    self.eval_cli(root, safe, relative), "PROTECTED_PATH"
                )
                self.assertIn("predicted", report["diagnostics"][0]["detail"])
        self.assertFalse((ROOT / S03_REPORT_REL).exists())

    def test_missing_input_is_fail_closed(self) -> None:
        root = self.make_root()
        safe = self.write_records(root, exp.example_hybrid_records(), "ok.json")
        absent = root / "absent.json"
        report = self.assert_eval_fail(self.eval_cli(root, absent, safe), "MISSING_INPUT")
        self.assertIn("expected", report["diagnostics"][0]["detail"])
        report = self.assert_eval_fail(self.eval_cli(root, safe, absent), "MISSING_INPUT")
        self.assertIn("predicted", report["diagnostics"][0]["detail"])

    def test_duplicate_bundle_id_is_refused_on_either_side(self) -> None:
        root = self.make_root()
        payload = exp.example_hybrid_records()
        safe = self.write_records(root, payload, "ok.json")
        doubled = exp.clone(payload)
        doubled["bundles"].append(exp.clone(doubled["bundles"][0]))
        dup = self.write_records(root, doubled, "dup.json")
        report = self.assert_eval_fail(self.eval_cli(root, dup, safe), "DUPLICATE_BUNDLE_ID")
        self.assertIn("expected", report["diagnostics"][0]["detail"])
        report = self.assert_eval_fail(self.eval_cli(root, safe, dup), "DUPLICATE_BUNDLE_ID")
        self.assertIn("predicted", report["diagnostics"][0]["detail"])

    def test_unmatched_bundle_is_alignment_not_a_synthetic_pair(self) -> None:
        root = self.make_root()
        expected_payload = exp.example_hybrid_records()
        predicted_payload = exp.clone(expected_payload)
        predicted_payload["bundles"] = [
            row for row in predicted_payload["bundles"] if row["bundle_id"] != "alias"
        ]
        expected = self.write_records(root, expected_payload, "expected.json")
        predicted = self.write_records(root, predicted_payload, "predicted.json")
        report = self.assert_eval_ok(self.eval_cli(root, expected, predicted))
        alignment = report["differential"]["bundle_alignment"]
        self.assertEqual(alignment["expected_only"], ["alias"])
        self.assertEqual(alignment["predicted_only"], [])
        self.assertEqual(alignment["matched"], ["agreement", "annex", "series"])
        self.assertEqual(alignment["expected_bundles"], 4)
        self.assertEqual(alignment["predicted_bundles"], 3)
        hybrid = report["differential"]["planes"]["hybrid"]
        self.assertEqual(hybrid["bundles"], 3)
        self.assertEqual(hybrid["bundle_exact"]["value"], "3/3")
        self.assertEqual(hybrid["detection"], {"tp": 6, "fp": 0, "fn": 0})

    def test_invalid_records_are_diagnostics_with_side_and_no_metrics(self) -> None:
        root = self.make_root()
        bad = exp.example_hybrid_records()
        bad["is_gold"] = True
        bad_path = self.write_records(root, bad, "bad.json")
        safe = self.write_records(root, exp.example_hybrid_records(), "ok.json")
        report = self.assert_eval_fail(self.eval_cli(root, bad_path, safe), "MALFORMED_REF")
        self.assertIn("expected", report["diagnostics"][0]["detail"])
        report = self.assert_eval_fail(self.eval_cli(root, safe, bad_path), "MALFORMED_REF")
        self.assertIn("predicted", report["diagnostics"][0]["detail"])
        blob = json.dumps(report)
        self.assertIsNone(report["differential"])
        self.assertNotIn('"value":', blob)
        for key in S03_METRIC_KEYS:
            self.assertNotIn(key, blob, key)

    def test_eval_stdout_has_no_s03_metric_keys(self) -> None:
        root = self.make_root()
        expected, predicted = self.write_pair(root)
        result = self.eval_cli(root, expected, predicted)
        self.assertEqual(result.returncode, 0, result.stderr)
        for key in S03_METRIC_KEYS:
            self.assertNotIn(key, result.stdout, key)

    def test_eval_is_read_only_and_leaves_frozen_stores_alone(self) -> None:
        before = frozen_fingerprint()
        synthetic = ROOT / RECORD_REL
        synthetic_before = synthetic.read_bytes() if synthetic.is_file() else None
        root = self.make_root()
        expected, predicted = self.write_pair(root)
        expected_before = expected.read_bytes()
        predicted_before = predicted.read_bytes()
        self.assert_eval_ok(self.eval_cli(root, expected, predicted))
        self.assertEqual(expected.read_bytes(), expected_before)
        self.assertEqual(predicted.read_bytes(), predicted_before)
        self.assertFalse((root / RECORD_REL).exists())
        self.assertEqual(frozen_fingerprint(), before)
        if synthetic_before is None:
            self.assertFalse(synthetic.exists())
        else:
            self.assertEqual(synthetic.read_bytes(), synthetic_before)
        self.assertFalse((ROOT / S03_REPORT_REL).exists())

    def eval_in_process(
        self, root: Path, expected: Path, predicted: Path, **patches: Any
    ) -> tuple[int, str, str]:
        """Run the eval CLI in-process so module-level properties can be patched."""
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with contextlib.ExitStack() as stack:
                for target, replacement in patches.items():
                    stack.enter_context(mock.patch.object(exp, target, replacement))
                code = exp.main(
                    ["--root", str(root), "--evaluate-records", str(expected), str(predicted)]
                )
        return code, stdout.getvalue(), stderr.getvalue()

    def test_metamorphic_property_denominators_are_explicit(self) -> None:
        root = self.make_root()
        expected, predicted = self.write_pair(root)
        report = self.assert_eval_ok(self.eval_cli(root, expected, predicted))
        metamorphic = report["metamorphic"]
        self.assertEqual(metamorphic["rules"], list(exp.METAMORPHIC_RULES))
        by_name = {row["name"]: row for row in metamorphic["properties"]}
        self.assertEqual(sorted(by_name), sorted(name for name, _ in exp.METAMORPHIC_PROPERTIES))
        order = by_name["alignment_invariant_to_record_order"]
        self.assertEqual((order["denominator"], order["value"]), (4, "4/4"))
        labels = by_name["labels_do_not_drive_matching"]
        self.assertEqual((labels["denominator"], labels["value"]), (4, "4/4"))
        self.assertIn("anchor pairs unchanged", labels["detail"])
        empty = by_name["empty_denominator_is_not_measured"]
        self.assertEqual((empty["denominator"], empty["value"]), (1, "1/1"))
        self.assertIn("not-measured", empty["detail"])
        duplicate = by_name["duplicate_anchor_key_is_rejected"]
        self.assertEqual((duplicate["denominator"], duplicate["value"]), (1, "1/1"))
        self.assertIn("AMBIGUOUS_DUPLICATE", duplicate["detail"])

    def test_forced_property_failure_is_unstable_and_keeps_differential(self) -> None:
        root = self.make_root()
        expected, predicted = self.write_pair(root)
        baseline = self.assert_eval_ok(self.eval_cli(root, expected, predicted))
        target = "metamorphic_empty_denominator_is_not_measured"
        real = getattr(exp, target)

        def broken(context: Any) -> dict[str, Any]:
            row = real(context)
            row["status"] = "failed"
            row["correct"] = 0
            row["detail"] = "forced failure for the independence test"
            return row

        code, stdout, stderr = self.eval_in_process(root, expected, predicted, **{target: broken})
        self.assertEqual(code, 1)
        self.assertIn("FAIL UNSTABLE", stderr)
        self.assertNotIn(EVAL_MARKER, stderr)
        self.assertNotIn("Traceback", stderr)
        report = json.loads(stdout)
        self.assertEqual(report["status"], "unstable")
        self.assertIsNone(report["marker"])
        self.assertEqual(report["metamorphic"]["properties_executed"], 4)
        self.assertEqual(report["metamorphic"]["properties_passed"], 3)
        self.assertEqual(report["metamorphic"]["verdict"]["value"], "3/4")
        self.assertEqual(report["differential"]["planes"], baseline["differential"]["planes"])
        self.assertEqual(
            report["differential"]["planes"]["hybrid"]["bundle_exact"],
            baseline["differential"]["planes"]["hybrid"]["bundle_exact"],
        )
        self.assertEqual(
            report["differential"]["bundle_alignment"],
            baseline["differential"]["bundle_alignment"],
        )

    def test_raising_property_is_failed_not_a_traceback(self) -> None:
        root = self.make_root()
        expected, predicted = self.write_pair(root)
        target_func = "metamorphic_duplicate_anchor_key_is_rejected"
        target_name = "duplicate_anchor_key_is_rejected"

        def boom(context: Any) -> dict[str, Any]:
            raise RuntimeError("metamorphic boom")

        code, stdout, stderr = self.eval_in_process(
            root, expected, predicted, **{target_func: boom}
        )
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", stderr)
        report = json.loads(stdout)
        rows = {row["name"]: row for row in report["metamorphic"]["properties"]}
        self.assertEqual(rows[target_name]["status"], "failed")
        self.assertIn("RuntimeError", rows[target_name]["detail"])
        self.assertIn("metamorphic boom", rows[target_name]["detail"])
        self.assertEqual(report["status"], "unstable")
        self.assertIsNone(report["marker"])

    def test_green_metamorphic_keeps_ok_while_differential_degrades(self) -> None:
        root = self.make_root()
        expected_payload = exp.example_hybrid_records()
        predicted_payload = exp.clone(expected_payload)
        predicted_payload["bundles"] = [
            row for row in predicted_payload["bundles"] if row["bundle_id"] != "alias"
        ]
        series = next(row for row in predicted_payload["bundles"] if row["bundle_id"] == "series")
        series["occurrences"][0]["fields"]["kind"]["value"] = "wrong-kind"
        expected = self.write_records(root, expected_payload, "expected.json")
        predicted = self.write_records(root, predicted_payload, "predicted.json")
        report = self.assert_eval_ok(self.eval_cli(root, expected, predicted))
        alignment = report["differential"]["bundle_alignment"]
        self.assertEqual(alignment["expected_only"], ["alias"])
        hybrid = report["differential"]["planes"]["hybrid"]
        self.assertEqual(hybrid["bundles"], 3)
        self.assertEqual(hybrid["bundle_exact"]["value"], "2/3")
        self.assertEqual(hybrid["field_value"]["value"], "17/18")
        metamorphic = report["metamorphic"]
        self.assertEqual(metamorphic["properties_executed"], 4)
        self.assertEqual(metamorphic["properties_passed"], 4)
        self.assertEqual(metamorphic["verdict"]["value"], "4/4")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["marker"], EVAL_MARKER)

    def test_labels_property_fails_when_align_becomes_label_sensitive(self) -> None:
        root = self.make_root()
        expected, predicted = self.write_pair(root)
        real_align = exp.align

        def label_sensitive_align(exp_occs: Any, pred_occs: Any) -> dict[str, Any]:
            aligned = real_align(exp_occs, pred_occs)
            if any(row["fields"]["kind"]["value"] == exp.METAMORPHIC_SENTINEL for row in pred_occs):
                changed = dict(aligned)
                changed["unique"] = []
                return changed
            return aligned

        code, stdout, stderr = self.eval_in_process(
            root, expected, predicted, align=label_sensitive_align
        )
        self.assertEqual(code, 1)
        self.assertIn("FAIL UNSTABLE", stderr)
        report = json.loads(stdout)
        rows = {row["name"]: row for row in report["metamorphic"]["properties"]}
        self.assertEqual(rows["labels_do_not_drive_matching"]["status"], "failed")
        self.assertEqual(rows["alignment_invariant_to_record_order"]["status"], "passed")
        self.assertEqual(report["metamorphic"]["properties_passed"], 3)
        self.assertEqual(report["metamorphic"]["verdict"]["value"], "3/4")

    def test_no_executed_property_is_not_measured_and_not_unstable(self) -> None:
        root = self.make_root()
        expected, predicted = self.write_pair(root)
        patches: dict[str, Any] = {}
        for name, func_name in exp.METAMORPHIC_PROPERTIES:

            def skipped(context: Any, _name: str = name) -> dict[str, Any]:
                return exp.metamorphic_row(_name, 0, 0, "skipped by test")

            patches[func_name] = skipped
        code, stdout, stderr = self.eval_in_process(root, expected, predicted, **patches)
        self.assertEqual(code, 0)
        self.assertIn(EVAL_MARKER, stderr)
        report = json.loads(stdout)
        metamorphic = report["metamorphic"]
        self.assertEqual(metamorphic["properties_executed"], 0)
        self.assertEqual(metamorphic["properties_passed"], 0)
        self.assertEqual(
            metamorphic["verdict"],
            {"correct": 0, "denominator": 0, "value": None, "status": "not-measured"},
        )
        for row in metamorphic["properties"]:
            self.assertEqual(row["status"], "not-measured", row["name"])
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["marker"], EVAL_MARKER)

    def test_metamorphic_run_writes_nothing_and_keeps_bytes(self) -> None:
        root = self.make_root()
        before = frozen_fingerprint()
        expected, predicted = self.write_pair(root)
        expected_before = expected.read_bytes()
        predicted_before = predicted.read_bytes()
        self.assert_eval_ok(self.eval_cli(root, expected, predicted))
        self.assertEqual(expected.read_bytes(), expected_before)
        self.assertEqual(predicted.read_bytes(), predicted_before)
        self.assertEqual(
            sorted(path.name for path in root.iterdir()),
            ["expected.json", "predicted.json"],
        )
        self.assertEqual(frozen_fingerprint(), before)
        self.assertFalse((ROOT / S03_REPORT_REL).exists())

    def records_with_bundle(self, bundle: dict[str, Any]) -> dict[str, Any]:
        """Full example payload with one bundle swapped for a mutated copy."""
        payload = exp.example_hybrid_records()
        replacement = exp.clone(bundle)
        for index, row in enumerate(payload["bundles"]):
            if row["bundle_id"] == replacement["bundle_id"]:
                payload["bundles"][index] = replacement
                return payload
        self.fail(f"example_hybrid_records() has no bundle {replacement['bundle_id']}")

    def run_bundle_pair(
        self, root: Path, expected_bundle: dict[str, Any], predicted_bundle: dict[str, Any]
    ) -> dict[str, Any]:
        expected = self.write_records(
            root, self.records_with_bundle(expected_bundle), "expected.json"
        )
        predicted = self.write_records(
            root, self.records_with_bundle(predicted_bundle), "predicted.json"
        )
        return self.assert_eval_ok(self.eval_cli(root, expected, predicted))

    def test_differential_plane_mutations_are_exact_and_isolated(self) -> None:
        """Each single-plane mutation moves one block and leaves the others pinned."""
        root = self.make_root()
        cases = (
            (
                "occurrence_fn",
                exp.series_expected(),
                exp.drop_occ(exp.series_expected(), "occ-b"),
                {
                    "detection": {"tp": 7, "fp": 0, "fn": 1},
                    "field_value": "21/24",
                    "provenance": "14/16",
                    "relation_e2e": "2/3",
                    "relation_conditional": "2/2",
                    "unresolved": "7/7",
                    "bundle_exact": "3/4",
                },
            ),
            (
                "wrong_field_moves_only_field_value",
                exp.agreement_expected(),
                exp.pred_wrong_field(),
                {
                    "detection": {"tp": 8, "fp": 0, "fn": 0},
                    "field_value": "23/24",
                    "provenance": "16/16",
                    "relation_e2e": "3/3",
                    "unresolved": "8/8",
                    "bundle_exact": "3/4",
                },
            ),
            (
                "wrong_provenance_moves_only_provenance",
                exp.series_expected(),
                exp.pred_wrong_provenance(),
                {
                    "detection": {"tp": 8, "fp": 0, "fn": 0},
                    "field_value": "24/24",
                    "provenance": "12/16",
                    "relation_e2e": "3/3",
                    "unresolved": "8/8",
                    "bundle_exact": "3/4",
                },
            ),
            (
                "wrong_relation_moves_only_relation_e2e",
                exp.annex_expected(),
                exp.pred_wrong_relation(),
                {
                    "detection": {"tp": 8, "fp": 0, "fn": 0},
                    "field_value": "24/24",
                    "provenance": "16/16",
                    "relation_e2e": "2/3",
                    "relation_conditional": "2/3",
                    "unresolved": "8/8",
                    "bundle_exact": "3/4",
                },
            ),
            (
                "extra_occurrence_fp",
                exp.series_expected(),
                exp.pred_extra_head_as_act(),
                {
                    "detection": {"tp": 8, "fp": 1, "fn": 0},
                    "field_value": "24/24",
                    "provenance": "16/16",
                    "relation_e2e": "3/3",
                    "unresolved": "8/8",
                    "bundle_exact": "3/4",
                },
            ),
        )
        for name, expected_bundle, predicted_bundle, wanted in cases:
            with self.subTest(case=name):
                report = self.run_bundle_pair(root, expected_bundle, predicted_bundle)
                hybrid = report["differential"]["planes"]["hybrid"]
                self.assertEqual(hybrid["detection"], wanted["detection"], name)
                self.assertEqual(hybrid["occurrence_expected"], 8, name)
                for key in (
                    "field_value",
                    "provenance",
                    "relation_e2e",
                    "relation_conditional",
                    "unresolved",
                    "bundle_exact",
                ):
                    if key in wanted:
                        self.assertEqual(hybrid[key]["value"], wanted[key], f"{name}.{key}")
                # exact numerator and denominator, not merely "it got worse"
                for key in ("field_value", "provenance", "unresolved", "bundle_exact"):
                    correct, denominator = (int(part) for part in wanted[key].split("/"))
                    self.assertEqual(hybrid[key]["correct"], correct, f"{name}.{key}.correct")
                    self.assertEqual(
                        hybrid[key]["denominator"], denominator, f"{name}.{key}.denominator"
                    )
                alignment = report["differential"]["bundle_alignment"]
                self.assertEqual(
                    alignment["matched"], ["agreement", "alias", "annex", "series"], name
                )
                self.assertEqual(alignment["expected_only"], [], name)
                self.assertEqual(alignment["predicted_only"], [], name)
                self.assertEqual(alignment["expected_bundles"], 4, name)
                self.assertEqual(alignment["predicted_bundles"], 4, name)
        # The dropped endpoint is an end-to-end relation FN for the series pair
        # itself (0/1); the aggregate plane reports 2/3 because agreement and
        # annex still match, which is exactly the plane separation under test.
        pair = exp.score_pair(exp.series_expected(), exp.drop_occ(exp.series_expected(), "occ-b"))
        self.assertEqual(pair["relation_e2e"]["value"], "0/1")
        self.assertEqual(pair["relation_e2e"]["fn"], 1)
        self.assertEqual(pair["detection"], {"tp": 1, "fp": 0, "fn": 1})
        self.assertFalse(pair["bundle_exact"])

    def test_whole_bundle_removal_is_alignment_not_a_scored_pair(self) -> None:
        root = self.make_root()
        expected_payload = exp.example_hybrid_records()
        dropped_id = str(expected_payload["bundles"][-1]["bundle_id"])
        predicted_payload = exp.clone(expected_payload)
        predicted_payload["bundles"] = predicted_payload["bundles"][:-1]
        expected = self.write_records(root, expected_payload, "expected.json")
        predicted = self.write_records(root, predicted_payload, "predicted.json")
        report = self.assert_eval_ok(self.eval_cli(root, expected, predicted))
        alignment = report["differential"]["bundle_alignment"]
        self.assertEqual(alignment["expected_only"], [dropped_id])
        self.assertEqual(alignment["predicted_only"], [])
        self.assertNotIn(dropped_id, alignment["matched"])
        self.assertEqual(alignment["expected_bundles"], 4)
        self.assertEqual(alignment["predicted_bundles"], 3)
        hybrid = report["differential"]["planes"]["hybrid"]
        self.assertEqual(hybrid["detection"], {"tp": 6, "fp": 0, "fn": 0})
        self.assertEqual(hybrid["field_value"]["value"], "18/18")
        self.assertEqual(hybrid["unresolved"]["value"], "6/6")
        # bundle_exact is the matched-pair count, never the expected-bundle count
        self.assertEqual(hybrid["bundle_exact"]["value"], "3/3")
        self.assertEqual(hybrid["bundle_exact"]["denominator"], len(alignment["matched"]))
        self.assertEqual(hybrid["bundles"], len(alignment["matched"]))
        self.assertNotEqual(hybrid["bundle_exact"]["denominator"], alignment["expected_bundles"])

    def test_extra_bundle_is_predicted_only_and_not_scored(self) -> None:
        root = self.make_root()
        expected_payload = exp.example_hybrid_records()
        predicted_payload = exp.clone(expected_payload)
        extra = exp.clone(predicted_payload["bundles"][0])
        extra["bundle_id"] = "series-extra"
        predicted_payload["bundles"].append(extra)
        expected = self.write_records(root, expected_payload, "expected.json")
        predicted = self.write_records(root, predicted_payload, "predicted.json")
        report = self.assert_eval_ok(self.eval_cli(root, expected, predicted))
        alignment = report["differential"]["bundle_alignment"]
        self.assertEqual(alignment["predicted_only"], ["series-extra"])
        self.assertEqual(alignment["expected_only"], [])
        self.assertNotIn("series-extra", alignment["matched"])
        self.assertEqual(alignment["expected_bundles"], 4)
        self.assertEqual(alignment["predicted_bundles"], 5)
        hybrid = report["differential"]["planes"]["hybrid"]
        self.assertEqual(hybrid["bundles"], 4)
        self.assertEqual(hybrid["detection"], {"tp": 8, "fp": 0, "fn": 0})
        self.assertEqual(hybrid["bundle_exact"]["value"], "4/4")
        self.assertEqual(hybrid["bundle_exact"]["denominator"], len(alignment["matched"]))

    def test_not_measured_pair_does_not_move_the_denominator(self) -> None:
        root = self.make_root()
        expected, predicted = self.write_pair(root)
        report = self.assert_eval_ok(self.eval_cli(root, expected, predicted))
        hybrid = report["differential"]["planes"]["hybrid"]
        e2e = hybrid["relation_e2e"]
        self.assertEqual(e2e["status"], "measured")
        self.assertEqual(e2e["expected_n"], 3)
        self.assertEqual(e2e["tp"], 3)
        self.assertEqual(e2e["value"], "3/3")
        self.assertNotEqual(e2e["value"], "3/4")
        self.assertEqual(hybrid["unresolved"]["value"], "8/8")
        self.assertEqual(hybrid["bundle_exact"]["value"], "4/4")
        # the alias bundle has no relations on either side: not-measured, not 0/0
        alias_pair = exp.score_pair(exp.alias_expected(), exp.alias_expected())
        self.assertEqual(alias_pair["relation_e2e"]["status"], "not-measured")
        self.assertIsNone(alias_pair["relation_e2e"]["value"])

    def test_differential_planes_are_independent_of_record_order(self) -> None:
        root = self.make_root()
        payload = exp.example_hybrid_records()
        expected = self.write_records(root, payload, "expected.json")
        baseline = self.assert_eval_ok(self.eval_cli(root, expected, expected))
        shuffled = exp.clone(payload)
        for bundle in shuffled["bundles"]:
            bundle["occurrences"].reverse()
            bundle["relations"].reverse()
        self.assertNotEqual(
            [row["id"] for row in shuffled["bundles"][0]["occurrences"]],
            [row["id"] for row in payload["bundles"][0]["occurrences"]],
        )
        shuffled_path = self.write_records(root, shuffled, "shuffled.json")
        report = self.assert_eval_ok(self.eval_cli(root, expected, shuffled_path))
        self.assertEqual(report["differential"]["planes"], baseline["differential"]["planes"])
        self.assertEqual(
            report["differential"]["bundle_alignment"],
            baseline["differential"]["bundle_alignment"],
        )
        self.assertEqual(report["metamorphic"]["properties_passed"], 4)

    def invalid_input_cases(self) -> tuple[tuple[str, str, dict[str, Any] | None], ...]:
        def duplicate_anchor() -> dict[str, Any]:
            payload = exp.example_hybrid_records()
            bundle = payload["bundles"][1]
            twin = exp.clone(bundle["occurrences"][0])
            twin["id"] = f"{twin['id']}-dup"
            bundle["occurrences"].append(twin)
            return payload

        def cross_doc() -> dict[str, Any]:
            payload = exp.example_hybrid_records(include_alias=False)
            docs = payload["documents"]
            series_doc = next(row for row in docs if row["document_id"] == "doc-series")
            moved = next(
                row for row in series_doc["fragments"] if row["fragment_id"] == exp.M2_FRAG
            )
            series_doc["fragments"] = [
                row for row in series_doc["fragments"] if row["fragment_id"] != exp.M2_FRAG
            ]
            docs.append({"document_id": "doc-other", "fragments": [moved]})
            return payload

        def forbidden_origin() -> dict[str, Any]:
            payload = exp.example_hybrid_records()
            payload["provenance_origin"] = "human-reviewed"
            return payload

        def gold_claim() -> dict[str, Any]:
            payload = exp.example_hybrid_records()
            payload["is_gold"] = True
            return payload

        def s03_rate_key() -> dict[str, Any]:
            payload = exp.example_hybrid_records()
            payload["span_rate"] = 0.5
            return payload

        def schema_version_two() -> dict[str, Any]:
            payload = exp.example_hybrid_records()
            payload["schema_version"] = 2
            return payload

        def synthetic_schema() -> dict[str, Any]:
            payload = exp.example_hybrid_records()
            payload["schema"] = exp.SCHEMA
            return payload

        def dangling_edge() -> dict[str, Any]:
            payload = exp.example_hybrid_records()
            payload["bundles"][0]["relations"][0]["to"] = "missing-occ"
            return payload

        def invalid_bounds() -> dict[str, Any]:
            payload = exp.example_hybrid_records()
            payload["bundles"][0]["occurrences"][0]["anchors"][0]["end"] = 99
            return payload

        def duplicate_bundle_id() -> dict[str, Any]:
            payload = exp.example_hybrid_records()
            payload["bundles"].append(exp.clone(payload["bundles"][0]))
            return payload

        return (
            ("ambiguous_duplicate", "AMBIGUOUS_DUPLICATE", duplicate_anchor()),
            ("cross_doc_ref", "CROSS_DOC_REF", cross_doc()),
            ("provenance_forbidden", "PROVENANCE_FORBIDDEN", forbidden_origin()),
            ("is_gold", "MALFORMED_REF", gold_claim()),
            ("s03_rate_key", "MALFORMED_REF", s03_rate_key()),
            ("schema_version_2", "UNSUPPORTED_VERSION", schema_version_two()),
            ("synthetic_schema", "UNSUPPORTED_VERSION", synthetic_schema()),
            ("dangling_edge", "DANGLING_EDGE", dangling_edge()),
            ("invalid_bounds", "INVALID_BOUNDS", invalid_bounds()),
            ("duplicate_bundle_id", "DUPLICATE_BUNDLE_ID", duplicate_bundle_id()),
            ("missing_input", "MISSING_INPUT", None),
        )

    def assert_invalid_side(self, report: dict[str, Any], side: str) -> None:
        self.assertIn(side, report["diagnostics"][0]["detail"])
        self.assertIsNone(report["differential"])
        blob = json.dumps(report)
        self.assertNotIn("bundle_exact", blob)
        self.assertNotIn('"planes"', blob)
        self.assertNotIn('"value":', blob)
        for key in S03_METRIC_KEYS:
            self.assertNotIn(key, blob, key)

    def test_invalid_inputs_carry_side_and_never_publish_metrics(self) -> None:
        root = self.make_root()
        safe = self.write_records(root, exp.example_hybrid_records(), "safe.json")
        absent = root / "absent.json"
        for name, code, payload in self.invalid_input_cases():
            with self.subTest(case=name):
                self.assertIn(code, exp.EVAL_DIAGNOSTICS)
                bad = absent if payload is None else self.write_records(root, payload, "bad.json")
                details: dict[str, str] = {}
                for side in ("expected", "predicted"):
                    args = (bad, safe) if side == "expected" else (safe, bad)
                    report = self.assert_eval_fail(self.eval_cli(root, *args), code)
                    self.assert_invalid_side(report, side)
                    self.assertEqual(report["diagnostics"][0]["code"], code)
                    details[side] = report["diagnostics"][0]["detail"]
                # same code, opposite side: the diagnostic names the side it saw
                self.assertNotEqual(details["expected"], details["predicted"], name)


class HybridEvalContractTests(unittest.TestCase):
    """Doc-code conformance and byte-stability regression for the S06 evaluator."""

    def make_root(self) -> Path:
        directory = Path(tempfile.mkdtemp(prefix="m207-hybrid-eval-contract-"))
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        return directory

    def run_cli(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPT), "--root", str(root), *extra]
        return subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False, timeout=TIMEOUT
        )

    def write_records(self, root: Path, payload: Any, name: str) -> Path:
        path = root / name
        path.write_bytes(exp.canonical_json_bytes(payload))
        return path

    def eval_cli(
        self, root: Path, expected: Any, predicted: Any
    ) -> subprocess.CompletedProcess[str]:
        return self.run_cli(root, "--evaluate-records", str(expected), str(predicted))

    def assert_eval_ok_cli(self, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn(EVAL_MARKER, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "ok")
        return report

    def assert_eval_fail_cli(
        self, result: subprocess.CompletedProcess[str], diagnostic: str
    ) -> dict[str, Any]:
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        self.assertIn(f"FAIL {diagnostic}", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "invalid")
        self.assertIsNone(report["marker"])
        return report

    def eval_in_process(
        self, root: Path, expected: Path, predicted: Path, **patches: Any
    ) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with contextlib.ExitStack() as stack:
                for target, replacement in patches.items():
                    stack.enter_context(mock.patch.object(exp, target, replacement))
                code = exp.main(
                    ["--root", str(root), "--evaluate-records", str(expected), str(predicted)]
                )
        return code, stdout.getvalue(), stderr.getvalue()

    def test_contract_document_matches_the_closed_diagnostic_set(self) -> None:
        document = (ROOT / EVAL_CONTRACT_REL).read_text(encoding="utf-8")
        self.assertEqual(parse_eval_diagnostic_codes(document), set(exp.EVAL_DIAGNOSTICS))

    def test_diagnostic_extraction_fails_in_both_directions(self) -> None:
        document = (ROOT / EVAL_CONTRACT_REL).read_text(encoding="utf-8")
        expected = set(exp.EVAL_DIAGNOSTICS)
        # Removing any single documented code must be detectable.
        for code in exp.EVAL_DIAGNOSTICS:
            pruned = "\n".join(line for line in document.splitlines() if line.strip() != code)
            self.assertNotEqual(parse_eval_diagnostic_codes(pruned), expected, code)
        # Adding an undocumented code must be detectable.
        injected: list[str] = []
        for line in document.splitlines():
            injected.append(line)
            if line.strip() == EVAL_DIAGNOSTICS_BEGIN:
                injected.append("UNDOCUMENTED_CODE")
        with_extra = parse_eval_diagnostic_codes("\n".join(injected))
        self.assertNotEqual(with_extra, expected)
        self.assertEqual(with_extra - expected, {"UNDOCUMENTED_CODE"})
        # Malformed blocks are hard errors, never silent skips.
        with self.assertRaises(AssertionError):
            parse_eval_diagnostic_codes("no markers here")
        with self.assertRaises(AssertionError):
            parse_eval_diagnostic_codes(document.replace(EVAL_DIAGNOSTICS_END, ""))
        with self.assertRaises(AssertionError):
            parse_eval_diagnostic_codes(
                document.replace(EVAL_DIAGNOSTICS_BEGIN, EVAL_DIAGNOSTICS_BEGIN + "\nlowercase")
            )
        with self.assertRaises(AssertionError):
            parse_eval_diagnostic_codes(
                document.replace(EVAL_DIAGNOSTICS_BEGIN, EVAL_DIAGNOSTICS_BEGIN + "\nUSAGE")
            )

    def test_pinned_check_summary_is_stable(self) -> None:
        root = self.make_root()
        written = self.run_cli(root, "--write")
        self.assertEqual(written.returncode, 0, written.stderr + written.stdout)
        check = self.run_cli(root, "--check")
        self.assertEqual(check.returncode, 0, check.stderr + check.stdout)
        self.assertIn(PINNED_CHECK_SUMMARY, check.stdout)
        self.assertIn("drift=0", check.stdout)
        default = self.run_cli(root)
        self.assertEqual(default.returncode, 0, default.stderr + default.stdout)
        self.assertIn(PINNED_CHECK_SUMMARY, default.stdout)

    def test_validate_records_summary_is_unchanged(self) -> None:
        root = self.make_root()
        path = self.write_records(root, exp.example_hybrid_records(), "records.json")
        result = self.run_cli(root, "--validate-records", str(path))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn(RECORDS_MARKER, result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["documents"], 4)
        self.assertEqual(report["bundles"], 4)
        self.assertEqual(report["diagnostics"], [])

    def test_eval_runs_leave_frozen_stores_and_inputs_untouched(self) -> None:
        self.assertIn(RECORDS_CONTRACT_REL, FROZEN_PATHS)
        self.assertIn(EVAL_CONTRACT_REL, FROZEN_PATHS)
        before = frozen_fingerprint()
        watched = {
            relative: ((ROOT / relative).read_bytes() if (ROOT / relative).is_file() else None)
            for relative in (RECORD_REL, S03_REPORT_REL, S03_BATTERY_REL)
        }
        root = self.make_root()
        payload = exp.example_hybrid_records()
        expected = self.write_records(root, payload, "expected.json")
        predicted = self.write_records(root, payload, "predicted.json")
        expected_before = expected.read_bytes()
        predicted_before = predicted.read_bytes()
        # 1. successful eval
        self.assert_eval_ok_cli(self.eval_cli(root, expected, predicted))
        # 2. invalid input eval (dishonest honesty key)
        dishonest = exp.clone(payload)
        dishonest["is_gold"] = True
        bad = self.write_records(root, dishonest, "bad.json")
        self.assert_eval_fail_cli(self.eval_cli(root, bad, predicted), "MALFORMED_REF")
        # 3. forced metamorphic property failure
        target = "metamorphic_empty_denominator_is_not_measured"
        real = getattr(exp, target)

        def broken(context: Any) -> dict[str, Any]:
            row = real(context)
            row["status"] = "failed"
            row["correct"] = 0
            row["detail"] = "forced failure for the byte-stability regression"
            return row

        code, stdout, stderr = self.eval_in_process(root, expected, predicted, **{target: broken})
        self.assertEqual(code, 1, stderr + stdout)
        unstable = json.loads(stdout)
        self.assertEqual(unstable["status"], "unstable")
        self.assertIsNone(unstable["marker"])
        # No frozen byte moved, no artifact appeared or was rewritten, inputs intact.
        self.assertEqual(frozen_fingerprint(), before)
        for relative, snapshot in watched.items():
            actual = (ROOT / relative).read_bytes() if (ROOT / relative).is_file() else None
            self.assertEqual(actual, snapshot, relative)
        self.assertEqual(expected.read_bytes(), expected_before)
        self.assertEqual(predicted.read_bytes(), predicted_before)
        self.assertEqual(
            sorted(path.name for path in root.iterdir()),
            ["bad.json", "expected.json", "predicted.json"],
        )

    def test_eval_contract_stays_out_of_the_rust_surface(self) -> None:
        offenders: list[str] = []
        for path in sorted((ROOT / "crates").rglob("*")):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for needle in RUST_SURFACE_NEEDLES:
                if needle in text:
                    offenders.append(f"{path.relative_to(ROOT)}:{needle}")
        self.assertEqual(offenders, [])


def main() -> int:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(HybridEvalExperimentTests))
    suite.addTests(loader.loadTestsFromTestCase(HybridRecordsContractTests))
    suite.addTests(loader.loadTestsFromTestCase(HybridRecordsRejectionTests))
    suite.addTests(loader.loadTestsFromTestCase(HybridEvalReportTests))
    suite.addTests(loader.loadTestsFromTestCase(HybridEvalContractTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

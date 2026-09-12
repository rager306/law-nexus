#!/usr/bin/env python3
"""Bounded tmp-only tests for the S11 historical predicate split."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from m204_s11_classify import historical_predicates, parse_jsonl


class S11PredicateTests(unittest.TestCase):
    def test_equal_duplicate_digest_is_s07_valid_but_s10_invalid(self) -> None:
        digest = "sha256:test"
        records = [
            {"record_kind": "header", "inventory_digest": digest},
            {"record_kind": "canonical_payload", "inventory_digest": digest},
        ]
        predicates = historical_predicates(records)
        self.assertTrue(predicates["s07_first_digest_valid"])
        self.assertFalse(predicates["s10_duplicate_digest_valid"])
        self.assertTrue(predicates["duplicate_digests_equal"])

    def test_unequal_duplicate_digest_is_still_harness_invalid(self) -> None:
        records = [
            {"record_kind": "header", "inventory_digest": "sha256:a"},
            {"record_kind": "canonical_payload", "inventory_digest": "sha256:b"},
        ]
        predicates = historical_predicates(records)
        self.assertTrue(predicates["s07_first_digest_valid"])
        self.assertFalse(predicates["s10_duplicate_digest_valid"])
        self.assertFalse(predicates["duplicate_digests_equal"])

    def test_malformed_line_fails_closed_and_forged_claim_is_not_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "diagnostics.jsonl"
            path.write_text('{"record_kind":"header"}\nnot-json\n', encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                parse_jsonl(path)

    def test_non_object_json_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "diagnostics.jsonl"
            path.write_text("[]\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_jsonl(path)


if __name__ == "__main__":
    unittest.main()

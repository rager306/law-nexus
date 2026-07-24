"""Tests for Consultant NormStatement candidate extraction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JSONL_PATH = ROOT / "prd" / "parser" / "consultant_norm_candidates.jsonl"


def load_candidates() -> list[dict[str, object]]:
    if not JSONL_PATH.exists():
        pytest.skip("norm candidates artifact not present")
    return [
        json.loads(line)
        for line in JSONL_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_candidates_exist_and_have_required_fields() -> None:
    candidates = load_candidates()
    assert len(candidates) > 0
    for c in candidates:
        assert c["record_kind"] == "norm_candidate"
        assert c["modality"] in ("obligation", "permission", "prohibition")
        assert c["extraction_method"] == "deterministic"
        assert c["verification_status"] == "unverified"
        assert c["source_unit_id"]
        assert c["evidence_excerpt"]
        assert c["evidence_sha256"]
        assert c["non_authoritative"] is True


def test_modality_breakdown_is_present() -> None:
    candidates = load_candidates()
    modalities = {c["modality"] for c in candidates}
    assert modalities <= {"obligation", "permission", "prohibition"}


def test_all_candidates_are_non_authoritative() -> None:
    candidates = load_candidates()
    for c in candidates:
        assert c["non_authoritative"] is True
        assert any("unverified" in nc for nc in c["non_claims"])


def test_candidate_ids_are_unique() -> None:
    candidates = load_candidates()
    ids = [c["id"] for c in candidates]
    assert len(ids) == len(set(ids))

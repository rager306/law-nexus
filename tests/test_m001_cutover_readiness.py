"""Mechanical pins for the M001 cutover readiness assessment (M001 task T009).

SC8, corrected contract (owner ruling «(a)», INTENT.md ## Corrections): the
assessment must exist, carry exactly one law-nexus/cutover-readiness/v1
machine block, keep cutover false (N2) and corpus_honesty true, record every
ci_runs entry in its pending-ship form (final null, reruns 0,
advisory_documented true — E8's rerun budget not consumed before ship), and
cite every SC1-SC10 verdict plus the held-out edges E1/E3/E5/E8/E9 and the
judgment prohibitions N4/N7, so gutting the per-criterion content fails.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "docs" / "agent-stack" / "CUTOVER-READINESS-M001.md"
BLOCK_INFO = "law-nexus/cutover-readiness/v1"

CITED_IDS = [f"SC{n}" for n in range(1, 11)] + ["E1", "E3", "E5", "E8", "E9", "N4", "N7"]


def _document() -> str:
    assert DOC.exists(), f"cutover readiness assessment is missing: {DOC}"
    return DOC.read_text(encoding="utf-8")


def _machine_block(doc: str) -> dict:
    fence = re.compile(r"```" + re.escape(BLOCK_INFO) + r"[ \t]*\n(.*?)```", re.DOTALL)
    blocks = fence.findall(doc)
    assert len(blocks) == 1, f"expected exactly one {BLOCK_INFO} fenced block, found {len(blocks)}"
    return json.loads(blocks[0])


def test_assessment_exists_with_exactly_one_machine_block() -> None:
    block = _machine_block(_document())
    assert block["schema"] == BLOCK_INFO


def test_cutover_remains_false() -> None:
    block = _machine_block(_document())
    assert block["cutover"] is False, "cutover must stay false inside M001 (N2)"


def test_corpus_honesty_flag_is_true() -> None:
    block = _machine_block(_document())
    assert block["corpus_honesty"] is True


def test_every_ci_run_is_recorded_as_pending_ship() -> None:
    block = _machine_block(_document())
    runs = block["ci_runs"]
    assert isinstance(runs, list) and runs, "ci_runs must be a non-empty array"
    for run in runs:
        assert run["status"] == "pending-ship", (
            "every ci_runs entry records the pending-ship form of the E8 ruling"
        )
        assert run["final"] is None
        assert run["reruns"] == 0, "the one-rerun budget is not consumed before ship"
        assert run["advisory_documented"] is True
        assert isinstance(run.get("surface"), str) and run["surface"]


def test_document_cites_every_sc_and_pinned_edges() -> None:
    doc = _document()
    missing = [id_ for id_ in CITED_IDS if not re.search(rf"\b{re.escape(id_)}\b", doc)]
    assert not missing, f"gutted citations, missing ids: {missing}"

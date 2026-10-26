"""Mechanical pins for the closed M225 validation residual (M001 task T004).

SC3 with E3 and N1: the battery pin must be the full 40-hex SHA of the exact
HEAD the native re-validation ran at (never the placeholder again), the rerun
record must account for every battery check id with a disposition from the
fixed set, both records must carry the same revision, and the rerun verdict
must state its measurement class: a corpus-absent hermetic run is
observability, never a byte-parity PASS.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BATTERY = REPO / "prd" / "migration" / "rust-evidence" / "m225-validation-battery-2026-10-18.json"
RERUN = REPO / "prd" / "migration" / "rust-evidence" / "m225-validation-rerun-m001.json"

PLACEHOLDER = "pending-fill-by-validate-unit"
DISPOSITIONS = {"re-run-passed-hermetic", "skipped-corpus-absent", "not-rerun-environment-gated"}


def test_battery_pin_is_full_40_hex_sha_and_placeholder_is_gone() -> None:
    raw = BATTERY.read_text(encoding="utf-8")
    battery = json.loads(raw)
    rev = battery["tested_source_revision"]
    assert re.fullmatch(r"[0-9a-f]{40}", rev), f"pin is not a full 40-hex SHA: {rev!r}"
    assert PLACEHOLDER not in raw, "the placeholder string must be gone from the battery"


def test_battery_role_text_states_the_40_hex_head_semantics() -> None:
    battery = json.loads(BATTERY.read_text(encoding="utf-8"))
    role = battery["tested_source_revision_role"]
    assert "40-hex" in role, "role text must state the 40-hex SHA semantics (E3)"
    assert "exact HEAD" in role, "role text must bind the pin to the exact HEAD (E3)"


def test_battery_and_rerun_record_carry_the_same_revision() -> None:
    battery = json.loads(BATTERY.read_text(encoding="utf-8"))
    rerun = json.loads(RERUN.read_text(encoding="utf-8"))
    assert rerun["tested_source_revision"] == battery["tested_source_revision"]
    rerun_env = battery["environment"]["native_rerun_m001"]["git_state"]
    assert battery["tested_source_revision"] in rerun_env


def test_rerun_record_covers_every_battery_check_id_with_fixed_disposition() -> None:
    battery = json.loads(BATTERY.read_text(encoding="utf-8"))
    rerun = json.loads(RERUN.read_text(encoding="utf-8"))
    battery_ids = [c["check_id"] for c in battery["checks"]]
    dispositions = {d["check_id"]: d["disposition"] for d in rerun["check_dispositions"]}
    assert set(dispositions) == set(battery_ids), (
        "every battery check id needs exactly one disposition"
    )
    assert len(rerun["check_dispositions"]) == len(battery_ids)
    bad = {k: v for k, v in dispositions.items() if v not in DISPOSITIONS}
    assert not bad, f"dispositions outside the fixed set: {bad}"


def test_rerun_verdict_states_its_measurement_class_not_byte_parity() -> None:
    rerun = json.loads(RERUN.read_text(encoding="utf-8"))
    verdict = rerun["verdict"]
    assert "hermetic" in verdict["measurement_class"], (
        "measurement class must name the hermetic run"
    )
    assert "not a byte-parity PASS" in verdict["statement"], (
        "the verdict must disclaim byte parity (N1)"
    )
    assert "do not prove corpus scenarios ran" in verdict["statement"]
    assert "2026-10-18" in verdict["statement"], (
        "corpus-bound parity evidence remains the pinned 2026-10-18 corpus-present run"
    )

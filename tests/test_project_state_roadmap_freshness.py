#!/usr/bin/env python3
"""Freshness guard for the derived project-state roadmap.

The project-state roadmap (`prd/project-state/roadmap.md` +
`prd/project-state/data/roadmap.json`) is a hand-maintained cold-reader summary.
GSD state (milestones) moves independently under `.gsd/`. Without a check, the
roadmap drifts — historically it named M047 as current long after M068/M069
landed, and even recommended the (D098-frozen) ACP track as next.

This test is the anti-drift guard: it parses the GSD milestone registry
(`.gsd/STATE.md`) as the source of truth and asserts the roadmap's
`current_milestone` actually reflects GSD state. It is read-only and asserts
only structural/freshness facts — it does not validate product readiness.

If this test fails, update `prd/project-state/data/roadmap.json` (and
`prd/project-state/roadmap.md`) to match the current GSD state, then re-run.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".gsd/STATE.md"
ROADMAP_JSON_PATH = ROOT / "prd/project-state/data/roadmap.json"

# Matches a Milestone Registry row, in either form:
#   "- ✅ **M069-sl591m:** Title"
#   "- 🔄 **M068-xi4034:** Title"
# (the random suffix is optional; some legacy rows are bare "M047:").
_REGISTRY_ROW_RE = re.compile(
    r"^\s*-\s*(?P<marker>✅|🔄|⏸|🟡|⚪)\s*\*\*M(?P<seq>\d+)(?:-[a-z0-9]+)?:\*\*\s*(?P<title>.+?)\s*$"
)

# Matches the "Active Milestone:" header line in STATE.md.
_ACTIVE_MILESTONE_RE = re.compile(
    r"^\*\*Active Milestone:\*\*\s*M(?P<seq>\d+)(?:-(?P<rand>[a-z0-9]+))?",
    re.IGNORECASE,
)

# Extract the sequence number from a milestone id like "M069-sl591m".
_MSEQ_RE = re.compile(r"^M(\d+)(?:-[a-z0-9]+)?$")


def _registry_milestones(state_text: str) -> list[tuple[int, str, str]]:
    """Return ``(seq, marker, title)`` for every Milestone Registry row.

    The marker is the emoji status glyph (✅ = complete, 🔄/🟡 = active/blocked).
    """
    rows: list[tuple[int, str, str]] = []
    in_registry = False
    for line in state_text.splitlines():
        if line.strip().startswith("## Milestone Registry"):
            in_registry = True
            continue
        if in_registry and line.startswith("## "):
            break
        if not in_registry:
            continue
        match = _REGISTRY_ROW_RE.match(line)
        if match:
            rows.append((int(match.group("seq")), match.group("marker"), match.group("title")))
    return rows


def _active_milestone_seq(state_text: str) -> int | None:
    for line in state_text.splitlines():
        match = _ACTIVE_MILESTONE_RE.match(line.strip())
        if match:
            return int(match.group("seq"))
    return None


def _load_state() -> str:
    assert STATE_PATH.exists(), f"GSD state not found at {STATE_PATH}"
    return STATE_PATH.read_text(encoding="utf-8")


def _load_roadmap() -> dict:
    assert ROADMAP_JSON_PATH.exists(), f"roadmap.json not found at {ROADMAP_JSON_PATH}"
    return json.loads(ROADMAP_JSON_PATH.read_text(encoding="utf-8"))


def test_state_md_has_a_parseable_milestone_registry() -> None:
    """Guard the guard: STATE.md must expose a registry we can parse."""
    state = _load_state()
    rows = _registry_milestones(state)
    assert rows, "no milestone rows parsed from .gsd/STATE.md registry — parser broken?"
    seqs = [seq for seq, _, _ in rows]
    assert seqs == sorted(seqs), "registry rows are not in ascending sequence order"


def test_roadmap_current_milestone_exists_in_gsd_state() -> None:
    """The roadmap's current_milestone must name a real milestone in GSD state."""
    state = _load_state()
    roadmap = _load_roadmap()
    registry_seqs = {seq for seq, _, _ in _registry_milestones(state)}

    current_id = roadmap["current_milestone"]["id"]
    seq_match = _MSEQ_RE.match(current_id)
    assert seq_match, f"roadmap current_milestone.id is not a milestone id: {current_id!r}"
    current_seq = int(seq_match.group(1))
    assert current_seq in registry_seqs, (
        f"roadmap current_milestone {current_id} (M{current_seq}) is not present in the "
        f"GSD milestone registry — roadmap is stale or names a non-existent milestone."
    )


def test_roadmap_current_milestone_tracks_latest_gsd_milestone() -> None:
    """The roadmap current_milestone must track the latest GSD milestone.

    This is the core anti-drift assertion. The roadmap's current_milestone
    sequence must equal the maximum sequence in the GSD registry (the latest
    milestone, completed or active). When a new milestone completes, the roadmap
    MUST be updated; otherwise this test fails. Tolerance is zero by design —
    a roadmap that lags the latest milestone is exactly the drift we prevent.

    Accepted if the roadmap current is EITHER the latest milestone OR the active
    (blocked) milestone, since a blocked-but-active milestone can legitimately
    be the thing the roadmap points at.
    """
    state = _load_state()
    roadmap = _load_roadmap()
    rows = _registry_milestones(state)
    max_seq = max(seq for seq, _, _ in rows)
    active_seq = _active_milestone_seq(state)

    current_id = roadmap["current_milestone"]["id"]
    current_seq = int(_MSEQ_RE.match(current_id).group(1))

    accepted = {max_seq}
    if active_seq is not None:
        accepted.add(active_seq)
    assert current_seq in accepted, (
        f"roadmap current_milestone is M{current_seq} but the latest GSD milestone is "
        f"M{max_seq} (active: M{active_seq}). The project-state roadmap is stale — "
        f"refresh prd/project-state/data/roadmap.json (+ roadmap.md) to the current "
        f"GSD state."
    )


def test_roadmap_current_milestone_status_matches_gsd_state() -> None:
    """The status the roadmap claims for current_milestone must match GSD state.

    Maps the GSD registry marker to a coarse status: ✅ -> complete; any active
    marker (🔄/🟡/⏸) -> active. The roadmap's claimed status must agree.
    """
    state = _load_state()
    roadmap = _load_roadmap()
    rows = _registry_milestones(state)
    by_seq = {seq: marker for seq, marker, _ in rows}

    current_id = roadmap["current_milestone"]["id"]
    current_seq = int(_MSEQ_RE.match(current_id).group(1))
    claimed_status = roadmap["current_milestone"]["status"]

    marker = by_seq.get(current_seq)
    if marker == "✅":
        actual = "complete"
    else:
        actual = "active"

    assert claimed_status == actual, (
        f"roadmap claims current_milestone {current_id} status={claimed_status!r} but "
        f"GSD state marker is {marker!r} (={actual}). Update the roadmap status to match."
    )


def test_roadmap_completed_groups_cover_through_latest_milestone() -> None:
    """The roadmap's completed_milestone_groups ranges must cover the latest milestone.

    Prevents the roadmap from silently dropping a milestone range after it lands.
    The upper bound of the highest range must be >= the latest completed GSD
    milestone sequence.
    """
    state = _load_state()
    roadmap = _load_roadmap()
    rows = _registry_milestones(state)

    completed_seqs = [seq for seq, marker, _ in rows if marker == "✅"]
    if not completed_seqs:
        pytest.skip("no completed milestones in GSD state to check coverage against")
    latest_completed = max(completed_seqs)

    range_re = re.compile(r"M(\d+)\s*[-–]\s*M(\d+)")
    max_upper = 0
    for group in roadmap.get("completed_milestone_groups", []):
        rng = group.get("range", "")
        match = range_re.search(rng)
        if match:
            max_upper = max(max_upper, int(match.group(2)))

    assert max_upper >= latest_completed, (
        f"roadmap completed_milestone_groups top out at M{max_upper} but GSD state has "
        f"completed milestones through M{latest_completed}. Add/extend a range to cover it."
    )


if __name__ == "__main__":
    # Manual run: print a freshness summary instead of raising.
    state = _load_state()
    roadmap = _load_roadmap()
    rows = _registry_milestones(state)
    max_seq = max(seq for seq, _, _ in rows)
    active_seq = _active_milestone_seq(state)
    current_seq = int(_MSEQ_RE.match(roadmap["current_milestone"]["id"]).group(1))
    print(
        json.dumps(
            {
                "latest_gsd_milestone": f"M{max_seq}",
                "active_gsd_milestone": f"M{active_seq}" if active_seq else None,
                "roadmap_current": f"M{current_seq}",
                "fresh": current_seq in {max_seq, *(active_seq is not None and [active_seq] or [])},
            },
            sort_keys=True,
        )
    )

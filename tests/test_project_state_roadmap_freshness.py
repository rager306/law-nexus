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

The suite also pins the migration job's CI diagnostics contract
(`.github/workflows/repository-quality.yml`): the governor-diagnostics
artifact must publish on any job failure without masking the non-zero exit
(M003 SC3).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from law_nexus_harness.workflow_state import WorkflowStateKind, read_workflow_state

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".gsd/STATE.md"
ROADMAP_JSON_PATH = ROOT / "prd/project-state/data/roadmap.json"

# Matches a Milestone Registry row, in either form:
#   "- ✅ **M069-sl591m:** Title"
#   "- 🔄 **M068-xi4034:** Title"
#   "- ⬜ **M166-iyy4ak:** Title"  (planned; white large square)
# (the random suffix is optional; some legacy rows are bare "M047:").
# Keep marker set in sync with src/law_nexus_harness/governor.py.
_REGISTRY_ROW_RE = re.compile(
    r"^\s*-\s*(?P<marker>✅|🔄|⏸|🟡|⚪|⬜)\s*\*\*M(?P<seq>\d+)(?:-[a-z0-9]+)?:\*\*\s*(?P<title>.+?)\s*$"
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


def _load_state() -> str | None:
    """Return the milestone-registry text, or None when no operational state exists.

    MIGRATION.md §4.2 requires this guard to follow the typed adapter
    (`workflow_state.read_workflow_state`) instead of assuming a GSD-Pi tree on
    disk. The adapter classifies the surface; only a *historical legacy* or a
    *native Path* surface can carry milestone rows, and a missing state is a
    first-class outcome rather than an assertion failure. Tests that need rows
    skip on None; the anti-drift assertions run whenever rows exist.
    """
    report = read_workflow_state(ROOT)
    if report.kind is WorkflowStateKind.HISTORICAL_LEGACY:
        # The frozen snapshot is still the only milestone ledger until native
        # Path state exists; read it directly rather than inventing rows.
        if STATE_PATH.exists():
            return STATE_PATH.read_text(encoding="utf-8")
        return None
    if report.kind is WorkflowStateKind.BOOTSTRAP_NOT_CUT_OVER:
        # Bootstrap mode: the legacy projection is explicitly still described
        # by .gsd (docs/agent-stack/MIGRATION.md), so the ledger is readable but
        # the test must not treat it as operational Path state.
        if STATE_PATH.exists():
            return STATE_PATH.read_text(encoding="utf-8")
        return None
    # Operational native Path state has its own freshness owner; this guard
    # covers the legacy projection only.
    return None


def _load_roadmap() -> dict:
    assert ROADMAP_JSON_PATH.exists(), f"roadmap.json not found at {ROADMAP_JSON_PATH}"
    return json.loads(ROADMAP_JSON_PATH.read_text(encoding="utf-8"))


def test_state_md_has_a_parseable_milestone_registry() -> None:
    """Guard the guard: STATE.md must expose a registry we can parse."""
    state = _load_state()
    if state is None:
        pytest.skip("no workflow state surface on this checkout (bootstrap without .gsd)")
    rows = _registry_milestones(state)
    assert rows, "no milestone rows parsed from .gsd/STATE.md registry — parser broken?"
    seqs = [seq for seq, _, _ in rows]
    assert seqs == sorted(seqs), "registry rows are not in ascending sequence order"


def test_roadmap_current_milestone_exists_in_gsd_state() -> None:
    """The roadmap's current_milestone must name a real milestone in GSD state."""
    state = _load_state()
    if state is None:
        pytest.skip("no workflow state surface on this checkout (bootstrap without .gsd)")
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
    """The roadmap current_milestone must track the latest COMPLETED GSD milestone.

    This is the core anti-drift assertion. The roadmap's current_milestone must
    point at the latest milestone that is actually DONE (✅), because the roadmap
    describes what has landed — not what is merely in flight. The drift this
    prevents is concrete: historically the roadmap named M047 long after M068/
    M069 had completed.

    Target = the latest COMPLETED milestone (highest ✅ seq). An active-but-
    incomplete milestone (🔄, e.g. one just planned) is explicitly tolerated: the
    roadmap legitimately stays on the last completed milestone until the active
    one lands. When the active milestone completes, the roadmap MUST advance, or
    this test fails.

    Accepted if roadmap current == latest completed seq, OR (for a blocked-
    but-active milestone that the roadmap deliberately foregrounds) == active seq.
    """
    state = _load_state()
    if state is None:
        pytest.skip("no workflow state surface on this checkout (bootstrap without .gsd)")
    roadmap = _load_roadmap()
    rows = _registry_milestones(state)
    completed_seqs = [seq for seq, marker, _ in rows if marker == "✅"]
    assert completed_seqs, "no completed milestones in GSD registry"
    latest_completed_seq = max(completed_seqs)
    active_seq = _active_milestone_seq(state)

    current_id = roadmap["current_milestone"]["id"]
    current_seq = int(_MSEQ_RE.match(current_id).group(1))

    accepted = {latest_completed_seq}
    if active_seq is not None:
        accepted.add(active_seq)
    assert current_seq in accepted, (
        f"roadmap current_milestone is M{current_seq} but the latest COMPLETED GSD "
        f"milestone is M{latest_completed_seq} (active: M{active_seq}). The "
        f"project-state roadmap is stale — refresh prd/project-state/data/roadmap.json "
        f"(+ roadmap.md) to the current GSD state."
    )


def test_roadmap_current_milestone_status_matches_gsd_state() -> None:
    """The status the roadmap claims for current_milestone must match GSD state.

    Maps the GSD registry marker to a coarse status: ✅ -> complete; any active
    marker (🔄/🟡/⏸) -> active. The roadmap's claimed status must agree.
    """
    state = _load_state()
    if state is None:
        pytest.skip("no workflow state surface on this checkout (bootstrap without .gsd)")
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
    if state is None:
        pytest.skip("no workflow state surface on this checkout (bootstrap without .gsd)")
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


# Matches the live workflow-marker bullet in the roadmap front and captures
# the milestone slug that immediately follows the label. The superseded
# historical bullet carries extra text inside its bold label ("... marker
# (superseded 2026-10-16):**"), so requiring ":**" directly after "marker"
# selects only the live bullet; duplicates of the live bullet stay visible so
# the exact-one assertion below can fail closed on them.
_MARKER_BULLET_RE = re.compile(
    r"^- \*\*Local GSD workflow marker:\*\*\s*(?P<slug>\S+)", re.MULTILINE
)

# Native milestone line in the tracked .project/STATE.md frontmatter.
_NATIVE_MILESTONE_RE = re.compile(r"^milestone:\s*(?P<slug>\S+)\s*$", re.MULTILINE)

ROADMAP_MD_PATH = ROOT / "prd/project-state/roadmap.md"
NATIVE_STATE_PATH = ROOT / ".project/STATE.md"

# STATE.md frontmatter phase fields. The phase/status pair decides which
# documented roadmap contract applies: a milestone in flight leaves the
# roadmap tracking the last landed milestone — the mismatch the governor
# reports as the honest roadmap-current-tracks-path finding — while a
# shipped/done state must agree with the projection exactly.
_STATE_PHASE_RE = re.compile(r"^phase:\s*(?P<value>[^\s#]+)", re.MULTILINE)
_STATE_STATUS_RE = re.compile(r"^status:\s*(?P<value>[^\s#]+)", re.MULTILINE)
_LANDED_PHASE = ("shipped", "done")

# Archive directories are named "<NNN>-<milestone-slug>"; the highest NNN is
# the most recently landed milestone.
_ARCHIVE_DIR_RE = re.compile(r"^(?P<seq>\d{3})-(?P<slug>.+)$")


def _latest_archived_milestone_slug() -> str | None:
    """Return the slug of the most recently archived milestone, or None."""
    archive_dir = ROOT / ".project" / "archive"
    if not archive_dir.is_dir():
        return None
    ranked: list[tuple[int, str]] = []
    for entry in archive_dir.iterdir():
        match = _ARCHIVE_DIR_RE.match(entry.name)
        if entry.is_dir() and match:
            ranked.append((int(match.group("seq")), match.group("slug")))
    if not ranked:
        return None
    return max(ranked)[1]


def test_native_marker_names_the_operational_milestone() -> None:
    """Three-way roadmap identity, keyed on the native STATE phase (SC4/E5).

    The projection must name exactly one milestone, consistently across
    roadmap.json and the live roadmap.md marker, and that milestone must be
    the one the STATE phase semantics demand:

    - shipped/done (nothing in flight): exact three-way identity — STATE.md
      milestone = roadmap.json id = live marker slug.
    - any in-flight phase (e.g. build/active): STATE.md is deliberately ahead
      of the projection; the roadmap keeps tracking the last landed milestone
      (the M002 continuation on this checkout), which is exactly the honest
      roadmap-current-tracks-path mismatch the governor reports on integrated
      main. The three-way anchor here is archive = roadmap.json = marker.

    A marker that disagrees with roadmap.json, a duplicated live bullet, or a
    projection pointing at an unrelated milestone fails closed in both
    phases. Skips only when this checkout carries no native STATE.md
    milestone at all.
    """
    if not NATIVE_STATE_PATH.exists():
        pytest.skip("no .project/STATE.md on this checkout (native state absent)")
    state_text = NATIVE_STATE_PATH.read_text(encoding="utf-8")
    native_match = _NATIVE_MILESTONE_RE.search(state_text)
    if native_match is None:
        pytest.skip(".project/STATE.md carries no milestone (native state absent)")
    phase_match = _STATE_PHASE_RE.search(state_text)
    status_match = _STATE_STATUS_RE.search(state_text)
    assert phase_match is not None and status_match is not None, (
        "native STATE.md names a milestone but carries no phase/status pair — "
        "the phase semantics that key the roadmap contract are unreadable"
    )
    native_slug = native_match.group("slug")
    landed = (phase_match.group("value"), status_match.group("value")) == _LANDED_PHASE

    roadmap = _load_roadmap()
    current = roadmap["current_milestone"]
    assert current["status"] == "active", (
        "roadmap.json current_milestone.status must be 'active' while the "
        "native milestone is the operational one"
    )

    roadmap_md = ROADMAP_MD_PATH.read_text(encoding="utf-8")
    marker_slugs = _MARKER_BULLET_RE.findall(roadmap_md)
    assert len(marker_slugs) == 1, (
        "expected exactly one live 'Local GSD workflow marker:' bullet in "
        f"prd/project-state/roadmap.md, found {len(marker_slugs)}"
    )
    marker_slug = marker_slugs[0]
    assert marker_slug == current["id"], (
        f"roadmap.md live marker names {marker_slug!r} but roadmap.json "
        f"current_milestone.id is {current['id']!r} — the projection must be "
        "one consistent view (E5); a prefix/suffix variant or reworded slug "
        "is a blocking mismatch."
    )

    if landed:
        assert current["id"] == native_slug, (
            f"roadmap.json current_milestone.id {current['id']!r} != shipped "
            f"STATE.md milestone {native_slug!r} — nothing is in flight, so "
            "the projection must agree with STATE.md exactly; refresh "
            "prd/project-state/data/roadmap.json (+ roadmap.md)."
        )
    else:
        landed_slug = _latest_archived_milestone_slug()
        assert landed_slug is not None, (
            "no archived milestone under .project/archive/ while STATE.md is "
            "in flight — the roadmap has no landed milestone to track"
        )
        assert current["id"] == landed_slug, (
            f"roadmap.json current_milestone.id {current['id']!r} does not "
            f"match the last landed (archived) milestone {landed_slug!r} "
            f"while STATE.md is in flight on {native_slug!r} — the projection "
            "must track the landed milestone, not an unrelated one."
        )


# The dated superseded bullet that records M001 shipped/archived/integrated
# (post-ship pointers, M002 task T004). It must stay a historical record: one
# bullet, dated, carrying both ship and integration commits.
_SUPERSEDED_M001_BULLET_RE = re.compile(
    r"^- \*\*Local GSD workflow marker \(superseded 2026-10-27\):\*\*"
    r"(?P<body>.*?)^(?=^- |[^ ])",
    re.MULTILINE | re.DOTALL,
)


def test_every_archived_milestone_has_a_dated_history_bullet() -> None:
    """The superseded history must record every shipment (M010 SC3, E3, N2).

    The live marker names the current milestone; the history below it records
    the shipments a fresh reader cannot otherwise reconstruct. Bullets are
    appended, never deleted (N2), and every archive under `.project/archive/`
    must have one, with its ship commit, tag and archive path.
    """
    if not NATIVE_STATE_PATH.exists():
        pytest.skip("no .project/STATE.md on this checkout (native state absent)")
    roadmap_md = ROADMAP_MD_PATH.read_text(encoding="utf-8")
    archive_dir = ROOT / ".project" / "archive"
    archives = (
        sorted(
            entry.name
            for entry in archive_dir.iterdir()
            if entry.is_dir() and _ARCHIVE_DIR_RE.match(entry.name)
        )
        if archive_dir.is_dir()
        else []
    )
    if not archives:
        pytest.skip("no archived milestones on this checkout")
    live_slugs = _MARKER_BULLET_RE.findall(roadmap_md)
    assert len(live_slugs) == 1, "expected exactly one live marker bullet"
    live_slug = live_slugs[0]
    recorded = 0
    for name in archives:
        slug = _ARCHIVE_DIR_RE.match(name).group("slug")
        if slug == live_slug:
            # The current milestone's shipment is the live marker itself; it
            # moves into the history when the next milestone ships.
            continue
        assert f".project/archive/{name}" in roadmap_md, (
            f"the roadmap history must record archive {name}"
        )
        assert f"milestone/{name}" in roadmap_md, (
            f"the roadmap history must name tag milestone/{name}"
        )
        recorded += 1
    assert recorded >= 1, "no shipment is recorded in the roadmap history"


def test_native_marker_has_one_dated_m001_superseded_bullet() -> None:
    """Exactly one dated superseded bullet records the shipped M001 (T004, AC1).

    The live marker moved to `post-ship-hardening`; the retired M001 marker
    becomes a dated historical record carrying the ship and integration
    commits, so a fresh agent reads the shipped state instead of re-planning
    finished work. Runs under the same guard as the three-way identity test:
    whenever a native STATE.md milestone exists.
    """
    if not NATIVE_STATE_PATH.exists():
        pytest.skip("no .project/STATE.md on this checkout (native state absent)")
    state_text = NATIVE_STATE_PATH.read_text(encoding="utf-8")
    if _NATIVE_MILESTONE_RE.search(state_text) is None:
        pytest.skip(".project/STATE.md carries no milestone (native state absent)")

    roadmap_md = ROADMAP_MD_PATH.read_text(encoding="utf-8")
    bullets = _SUPERSEDED_M001_BULLET_RE.findall(roadmap_md)
    assert len(bullets) == 1, (
        "expected exactly one dated M001 superseded marker bullet "
        f"(superseded 2026-10-27) in prd/project-state/roadmap.md, found {len(bullets)}"
    )
    body = bullets[0]
    assert "001-native-workflow-acceptance" in body
    assert "shipped/archived/integrated" in body, (
        "the dated superseded bullet must record M001 shipped/archived/integrated"
    )
    assert "886a36a8" in body, "the superseded bullet must record the ship commit"
    assert "4e0cd4db" in body, "the superseded bullet must record the integration merge"


# --- CI diagnostics publication (SC3) ---------------------------------------
# The migration job's governor-diagnostics artifact must publish on ANY job
# failure without masking the non-zero exit. Pins for
# .github/workflows/repository-quality.yml.

WORKFLOW_PATH = ROOT / ".github/workflows/repository-quality.yml"
MIGRATION_JOB_NAME = "migration-layer-quality"
GOVERNOR_STEP_NAME = "Governor report is honest about bootstrap mode"
DIAGNOSTICS_STEP_NAME = "Publish governor diagnostics on failure"


def _migration_job_steps() -> list[dict]:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    return workflow["jobs"][MIGRATION_JOB_NAME]["steps"]


def _named_job_step(steps: list[dict], name: str) -> dict:
    matches = [step for step in steps if step.get("name") == name]
    assert len(matches) == 1, name
    return matches[0]


def test_diagnostics_artifact_is_job_failure_scoped() -> None:
    """SC3/E4: the artifact publishes when any step of the migration job fails.

    The upload carries `if: failure()`, which GitHub evaluates against the
    job's failure status — so any earlier failed step (pytest, governor,
    restore) triggers it — and it stays the job's last step so no failure can
    fall after it.
    """
    steps = _migration_job_steps()
    diagnostics = _named_job_step(steps, DIAGNOSTICS_STEP_NAME)
    assert diagnostics.get("if") == "failure()"
    assert str(diagnostics.get("uses", "")).startswith("actions/upload-artifact@")
    assert diagnostics["with"]["name"] == "governor-diagnostics"
    assert diagnostics["with"]["path"] == "governor.json"
    assert steps[-1] is diagnostics, (
        "the diagnostics upload must be the migration job's last step so a "
        "failure in any earlier step is covered"
    )


def test_governor_payload_exists_on_any_failure_path() -> None:
    """The governor step runs `if: always()`, so governor.json exists even when
    an earlier step (pytest, restore) failed — otherwise the upload would find
    no file and publish nothing (the CI 40533158703 blind spot)."""
    steps = _migration_job_steps()
    governor = _named_job_step(steps, GOVERNOR_STEP_NAME)
    assert governor.get("if") == "always()"
    assert steps.index(governor) < steps.index(_named_job_step(steps, DIAGNOSTICS_STEP_NAME))


def test_diagnostics_publication_never_masks_the_job_exit() -> None:
    """N3: publishing diagnostics must not absorb the non-zero job exit."""
    steps = _migration_job_steps()
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    job = workflow["jobs"][MIGRATION_JOB_NAME]
    assert job.get("continue-on-error") is not True
    diagnostics = _named_job_step(steps, DIAGNOSTICS_STEP_NAME)
    governor = _named_job_step(steps, GOVERNOR_STEP_NAME)
    assert "continue-on-error" not in diagnostics
    assert "continue-on-error" not in governor
    assert "run" not in diagnostics, (
        "the diagnostics step must stay a pure upload action; it must not run "
        "shell that could absorb a failure"
    )
    assert "|| true" not in str(governor.get("run", ""))


if __name__ == "__main__":
    # Manual run: print a freshness summary instead of raising. "fresh" uses
    # the same semantics as the test: roadmap current should equal the latest
    # COMPLETED milestone, OR the active milestone (an active-but-incomplete
    # milestone is tolerated).
    state = _load_state()
    if state is None:
        pytest.skip("no workflow state surface on this checkout (bootstrap without .gsd)")
    roadmap = _load_roadmap()
    rows = _registry_milestones(state)
    completed_seqs = [seq for seq, marker, _ in rows if marker == "✅"]
    latest_completed = max(completed_seqs) if completed_seqs else None
    active_seq = _active_milestone_seq(state)
    max_seq = max(seq for seq, _, _ in rows)
    current_seq = int(_MSEQ_RE.match(roadmap["current_milestone"]["id"]).group(1))
    accepted = set()
    if latest_completed is not None:
        accepted.add(latest_completed)
    if active_seq is not None:
        accepted.add(active_seq)
    print(
        json.dumps(
            {
                "latest_completed_gsd_milestone": f"M{latest_completed}"
                if latest_completed
                else None,
                "active_gsd_milestone": f"M{active_seq}" if active_seq else None,
                "max_gsd_milestone": f"M{max_seq}",
                "roadmap_current": f"M{current_seq}",
                "fresh": current_seq in accepted,
            },
            sort_keys=True,
        )
    )

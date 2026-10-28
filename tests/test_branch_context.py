"""Contracts for the shared branch-context predicate and the scenario matrix.

Pins five things (T003 acceptance 1 and 2; M003 T001 acceptance 3–5):

- the classification: five mutually exclusive contexts, fail-closed on an
  unreadable binding (E4), plus the STATE.md phase pairing they are keyed on
  (M003 E2: five contexts × both phases, pinned as a pure function);
- the four non-bound scenario contracts, each driven through the real governor
  and preflight surface checks against a fixture checkout whose runtime stack
  prints the pinned helper's recorded payload for that scenario: foreign,
  detached, and verify sidecar pin ``kind=conflicting-ownership`` with the
  runtime resolved and the scenario's own discriminator; shipped main pins
  Contract A — never collapsed into one broad expectation (E3); a main
  checkout with an in-flight build/active STATE blocks on branch ownership
  and never reports a phantom roadmap verdict (E1);
- the source scan: the two live suites hold no branch-detection logic outside
  :mod:`branch_context`, no broad ``startswith("kind=")`` pinning (N3), and
  no milestone-branch literals outside explicitly whitelisted fixture
  payloads (M003 SC2);
- the STATE.md phase reader: exactly the two documented pairings key the
  operational expectations, everything else fails closed to ``UNREADABLE``.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import branch_context
from branch_context import BranchContext, Classification, StateBinding, StatePhase
from law_nexus_harness.governor import check_roadmap_freshness, check_workflow_state_surface
from law_nexus_harness.preflight import _workflow_state_surface_check
from law_nexus_harness.workflow_state import (
    WorkflowStateKind,
    read_workflow_state,
    workflow_readiness,
)
from test_harness_workflow_state import (
    NATIVE_STATUS_VALID,
    PINNED_RUNTIME_DIGEST,
    PINNED_RUNTIME_VERSION,
    write_cutover_marker,
    write_operational_surface_files,
    write_project_state,
    write_runtime_declaration,
    write_shipped_main_real_stack,
)

BOUND_BRANCH = "gsd-path/M002"
FOREIGN_BRANCH = "gsd-path/M009"
SIDECAR_BRANCH = "gsd-path-verify/task-t003-verify"
MAIN_BRANCH = "main"

# The STATE.md frontmatter of an integrated main checkout with a milestone in
# flight (M003 SC1's named context): build/active, owned by the bound branch,
# while the checkout sits on the default branch. Fixture payload, so the
# milestone identity here is fixture data, not a suite expectation.
MAIN_BUILD_STATE_TEXT = f"""---
pipeline: gsd-path/v2
project: law-nexus
milestone: 001-native-workflow-acceptance
phase: build
status: active
branch: {BOUND_BRANCH}
default_branch: main # origin default branch; initialization records it once
---

# Project State
"""

SUITE_NAMES = ("test_harness_governor.py", "test_harness_preflight.py")

# Every way the M001 patch let a suite detect its branch or pin the surface
# finding broadly. After T003 the suites route through branch_context, so any
# of these tokens reappearing means branch logic leaked back into a suite.
FORBIDDEN_BRANCH_LOGIC = (
    "abbrev-ref",
    "symbolic-ref",
    "_current_branch",
    "_on_bound_branch",
    "BOUND_BRANCH",
    'startswith("kind=")',
    "gsd-path/M001",
    "gsd-path/M002",
)


def _active_milestone_block_payload(current_branch: str | None) -> dict[str, Any]:
    """The pinned helper's block payload for one non-operational scenario.

    Built on the recorded verbatim helper payload (``NATIVE_STATUS_VALID``);
    only the branch-ownership facts carry the scenario. The reason comes from
    the shared :func:`branch_context.block_reason`, so the fixture and the
    live pins cannot drift.
    """
    payload = copy.deepcopy(NATIVE_STATUS_VALID)
    payload["route"] = {
        "action": "block",
        "reason": branch_context.block_reason(current_branch, BOUND_BRANCH),
    }
    payload["completion"] = {"status": "not-shipped"}
    payload["git"]["branch"] = current_branch
    payload["state"]["branch"] = BOUND_BRANCH
    return payload


def _write_block_stack(root: Path, current_branch: str | None) -> None:
    """Fixture checkout whose real shim+helper stack reports one block scenario.

    Same discipline as ``write_shipped_main_real_stack``: the tracked
    declaration and marker are real, the shim resolves a runtime-cache
    directory whose ``pipeline_state.py`` prints one fixed status payload. No
    network and no real runtime store are involved.
    """
    write_operational_surface_files(root)
    _write_block_runtime_stack(root, current_branch)


def _write_block_runtime_stack(root: Path, current_branch: str | None) -> None:
    """Write the fake runtime cache + shim printing one block payload."""
    runtime_dir = root / "runtime-cache" / PINNED_RUNTIME_DIGEST
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "manifest.json").write_text(
        json.dumps({"version": PINNED_RUNTIME_VERSION, "files": {"pipeline_state.py": "0" * 64}}),
        encoding="utf-8",
    )
    payload_text = json.dumps(_active_milestone_block_payload(current_branch), sort_keys=True)
    (runtime_dir / "pipeline_state.py").write_text(
        f"import sys\nsys.stdout.write({payload_text!r})\n",
        encoding="utf-8",
    )
    shim = root / ".gsd-path" / "status_runtime.py"
    shim.parent.mkdir(parents=True, exist_ok=True)
    shim.write_text(f"print({runtime_dir.as_posix()!r})\n", encoding="utf-8")


def _write_main_build_stack(root: Path) -> None:
    """Fixture checkout of integrated main with an in-flight build/active STATE.

    The tracked cutover marker still says false on integrated main (the C7
    flip has not happened), so the marker is written false here — unlike the
    operational fixtures. The helper payload is the same recorded block
    payload the fail-closed fixtures use: while a milestone is in flight the
    pinned helper owns main away from the bound branch.
    """
    write_cutover_marker(root, cutover=False)
    write_project_state(root, MAIN_BUILD_STATE_TEXT)
    write_runtime_declaration(root)
    _write_block_runtime_stack(root, MAIN_BRANCH)


class TestClassification:
    """One checkout, exactly one of the five documented contexts (E4)."""

    def test_the_contexts_are_exactly_the_five_documented_scenarios(self) -> None:
        assert {context.value for context in BranchContext} == {
            "bound",
            "foreign",
            "detached",
            "verify-sidecar",
            "shipped-main",
        }

    def test_bound_branch_and_authorized_task_worktree_classify_bound(self) -> None:
        binding = StateBinding(bound_branch=BOUND_BRANCH)
        assert branch_context.classify_branch(BOUND_BRANCH, binding) is BranchContext.BOUND
        # An authorized gsd-path-task/* build worktree routes run-phase like
        # the bound branch (live-verified 2026-10-27), so it is an operational
        # BOUND site, never a fail-closed one.
        assert branch_context.classify_branch("gsd-path-task/T003", binding) is BranchContext.BOUND

    def test_foreign_branches_classify_foreign(self) -> None:
        binding = StateBinding(bound_branch=BOUND_BRANCH)
        assert branch_context.classify_branch(FOREIGN_BRANCH, binding) is BranchContext.FOREIGN
        assert (
            branch_context.classify_branch("gsd-path-task-notes", binding) is BranchContext.FOREIGN
        )

    def test_detached_head_classifies_detached(self) -> None:
        assert (
            branch_context.classify_branch(None, StateBinding(bound_branch=BOUND_BRANCH))
            is BranchContext.DETACHED
        )

    def test_verify_sidecar_classifies_verify_sidecar(self) -> None:
        binding = StateBinding(bound_branch=BOUND_BRANCH)
        assert (
            branch_context.classify_branch(SIDECAR_BRANCH, binding) is BranchContext.VERIFY_SIDECAR
        )

    def test_integrated_default_branch_classifies_shipped_main(self) -> None:
        binding = StateBinding(bound_branch=BOUND_BRANCH, default_branch="main")
        assert branch_context.classify_branch(MAIN_BRANCH, binding) is BranchContext.SHIPPED_MAIN
        assert (
            branch_context.classify_branch(MAIN_BRANCH, StateBinding(bound_branch=BOUND_BRANCH))
            is BranchContext.SHIPPED_MAIN
        )

    def test_classification_matrix_all_contexts_both_phases(self) -> None:
        """E2 (held-out): five contexts x both STATE phases, pinned exactly.

        The classification is a pure function of the live branch and the
        STATE.md binding (which carries the phase), so the full matrix is
        pinned without touching a filesystem.
        """
        contexts_by_branch = (
            (BOUND_BRANCH, BranchContext.BOUND),
            ("gsd-path-task/T003", BranchContext.BOUND),
            (FOREIGN_BRANCH, BranchContext.FOREIGN),
            (None, BranchContext.DETACHED),
            (SIDECAR_BRANCH, BranchContext.VERIFY_SIDECAR),
            (MAIN_BRANCH, BranchContext.SHIPPED_MAIN),
        )
        for phase in (StatePhase.BUILD_ACTIVE, StatePhase.SHIPPED_DONE):
            binding = StateBinding(
                bound_branch=BOUND_BRANCH, default_branch=MAIN_BRANCH, state_phase=phase
            )
            for branch, context in contexts_by_branch:
                classified = branch_context.classify_checkout(branch, binding)
                assert classified == Classification(context=context, phase=phase), (branch, phase)
        # An unreadable binding still fails closed, whatever the phase says.
        for phase in (StatePhase.BUILD_ACTIVE, StatePhase.SHIPPED_DONE):
            binding = StateBinding(bound_branch=None, state_phase=phase)
            assert branch_context.classify_checkout(BOUND_BRANCH, binding) == Classification(
                context=BranchContext.FOREIGN, phase=phase
            )

    def test_unreadable_binding_never_classifies_bound(self) -> None:
        # Fail closed: without a readable binding no checkout may reach the
        # full-assertion path.
        assert (
            branch_context.classify_branch(BOUND_BRANCH, StateBinding(bound_branch=None))
            is BranchContext.FOREIGN
        )

    def test_pins_fail_closed_covers_exactly_the_three_blocking_contexts(self) -> None:
        assert branch_context.pins_fail_closed(BranchContext.FOREIGN)
        assert branch_context.pins_fail_closed(BranchContext.DETACHED)
        assert branch_context.pins_fail_closed(BranchContext.VERIFY_SIDECAR)
        assert not branch_context.pins_fail_closed(BranchContext.BOUND)
        assert not branch_context.pins_fail_closed(BranchContext.SHIPPED_MAIN)

    def test_block_reason_is_the_helper_verbatim_mismatch_shape(self) -> None:
        assert branch_context.block_reason("gsd-path/M009", BOUND_BRANCH) == (
            "current branch gsd-path/M009 != STATE.branch gsd-path/M002"
        )
        # Detached HEAD renders as <detached>, the helper's own rendering.
        assert branch_context.block_reason(None, BOUND_BRANCH) == (
            "current branch <detached> != STATE.branch gsd-path/M002"
        )


class TestStatePhaseReading:
    """The STATE.md phase pairing: the two documented pairs, else unreadable."""

    @staticmethod
    def _write_state(root: Path, text: str) -> None:
        project = root / ".project"
        project.mkdir(parents=True, exist_ok=True)
        (project / "STATE.md").write_text(text, encoding="utf-8")

    def test_documented_pairs_read_build_active_and_shipped_done(self, tmp_path: Path) -> None:
        active = f"---\nbranch: {BOUND_BRANCH}\nphase: build\nstatus: active\n---\n"
        self._write_state(tmp_path / "active", active)
        shipped = f"---\nbranch: {BOUND_BRANCH}\nphase: shipped\nstatus: done\n---\n"
        self._write_state(tmp_path / "shipped", shipped)

        assert branch_context.state_binding(tmp_path / "active").state_phase is (
            StatePhase.BUILD_ACTIVE
        )
        assert branch_context.state_binding(tmp_path / "shipped").state_phase is (
            StatePhase.SHIPPED_DONE
        )

    def test_comments_between_fields_do_not_break_the_pair(self, tmp_path: Path) -> None:
        # The real STATE.md carries comment lines between the frontmatter
        # fields and trailing comments on a value line; both must be skipped.
        self._write_state(
            tmp_path,
            "---\n"
            "phase: build\n"
            "                    # inspect only for brownfield\n"
            "status: active\n"
            f"branch: {BOUND_BRANCH}\n"
            "                    # the router rebinds before any next-milestone file change\n"
            f"default_branch: {MAIN_BRANCH} # origin default branch\n"
            "---\n",
        )
        binding = branch_context.state_binding(tmp_path)
        assert binding.state_phase is StatePhase.BUILD_ACTIVE
        assert binding.bound_branch == BOUND_BRANCH
        assert binding.default_branch == MAIN_BRANCH

    def test_missing_or_mixed_pairs_fail_closed_unreadable(self, tmp_path: Path) -> None:
        cases = (
            "---\nphase: build\n---\n",  # status missing
            "---\nstatus: done\n---\n",  # phase missing
            "---\nphase: build\nstatus: done\n---\n",  # mixed pairing
            "---\nphase: inspect\nstatus: active\n---\n",  # undocumented pair
            "# GSD Path State\n",  # no frontmatter
        )
        for case in cases:
            self._write_state(tmp_path, case)
            binding = branch_context.state_binding(tmp_path)
            assert binding.state_phase is StatePhase.UNREADABLE, case

    def test_absent_state_file_reads_unreadable(self, tmp_path: Path) -> None:
        assert branch_context.state_binding(tmp_path).state_phase is StatePhase.UNREADABLE


class TestFailClosedScenarioContracts:
    """foreign / detached / verify sidecar: the fail-closed pin, per scenario."""

    def _assert_conflicting_ownership_surface(self, root: Path, current_branch: str | None) -> None:
        report = read_workflow_state(root)
        assert report.kind is WorkflowStateKind.CONFLICTING_OWNERSHIP
        assert workflow_readiness(report) == "blocked"
        assert report.remediation
        # The runtime resolved: a runtime-unavailable failure must never
        # satisfy the branch-ownership pin (the M001 startswith defect).
        assert report.runtime.version == PINNED_RUNTIME_VERSION
        reason = branch_context.block_reason(current_branch, BOUND_BRANCH)

        finding = check_workflow_state_surface(root)[0]
        assert finding.check_id == "workflow-state-surface"
        assert finding.status == "fail"
        assert finding.severity == "error"
        assert finding.rule_id == "workflow-state-surface.blocking"
        assert finding.observed.startswith("kind=conflicting-ownership;")
        assert re.search(branch_context.RESOLVED_RUNTIME_PATTERN, finding.observed)
        assert reason in finding.observed
        assert finding.remediation

        check = _workflow_state_surface_check(root)
        assert check.check_id == "workflow-state-surface"
        assert check.status == "fail"
        assert check.severity == "error"
        assert check.observed.startswith("kind=conflicting-ownership;")
        assert reason in check.observed
        assert check.remediation

    def test_foreign_branch_scenario_pins_its_own_discriminator(self, tmp_path: Path) -> None:
        # E3: a foreign bound branch (gsd-path/M009 while M002 rules) is its
        # own scenario with its own mismatch reason — never the shipped pin.
        _write_block_stack(tmp_path, FOREIGN_BRANCH)
        self._assert_conflicting_ownership_surface(tmp_path, FOREIGN_BRANCH)

    def test_detached_checkout_scenario_renders_detached(self, tmp_path: Path) -> None:
        # CI PR merge refs: the discriminator is the <detached> rendering.
        _write_block_stack(tmp_path, None)
        self._assert_conflicting_ownership_surface(tmp_path, None)

    def test_verify_sidecar_scenario_names_the_sidecar_branch(self, tmp_path: Path) -> None:
        _write_block_stack(tmp_path, SIDECAR_BRANCH)
        self._assert_conflicting_ownership_surface(tmp_path, SIDECAR_BRANCH)


class TestShippedMainScenarioContract:
    """Contract A on the integrated default branch: honest, non-blocking pass."""

    def test_shipped_main_surface_pins_contract_a(self, tmp_path: Path) -> None:
        write_shipped_main_real_stack(tmp_path)
        report = read_workflow_state(tmp_path)
        assert report.kind is WorkflowStateKind.SHIPPED_INTEGRATED
        assert report.remediation == "none"
        # The archive proof is part of the observed fact; WHICH milestone's
        # archive it names is not pinned (M003 SC2).
        assert "outcome shipped/done; archive .project/archive/" in report.observed
        assert workflow_readiness(report) == "operational"

        finding = check_workflow_state_surface(tmp_path)[0]
        assert finding.status == "pass"
        assert finding.severity == "ok"
        assert finding.rule_id == "workflow-state-surface.shipped"
        assert finding.observed.startswith("kind=shipped-integrated;")
        # The archive proof is required; WHICH milestone's archive it names is
        # not (M003 SC2): the archive path moves every milestone.
        assert "outcome shipped/done; archive .project/archive/" in finding.observed

        check = _workflow_state_surface_check(tmp_path)
        assert check.status == "pass"
        assert "state=shipped-integrated" in check.observed
        assert "outcome shipped/done; archive .project/archive/" in check.observed

    def test_shipped_main_and_foreign_branch_stay_distinct(self, tmp_path: Path) -> None:
        # E3: the two expectations can never collapse into one broad pin.
        write_shipped_main_real_stack(tmp_path / "shipped")
        shipped = check_workflow_state_surface(tmp_path / "shipped")[0]
        assert shipped.status == "pass"
        assert shipped.rule_id == "workflow-state-surface.shipped"

        _write_block_stack(tmp_path / "foreign", FOREIGN_BRANCH)
        foreign = check_workflow_state_surface(tmp_path / "foreign")[0]
        assert foreign.status == "fail"
        assert foreign.observed.startswith("kind=conflicting-ownership;")


class TestMainBuildActiveScenarioContract:
    """main with an in-flight build/active STATE: the block, never Contract A.

    On integrated main the pinned helper owns the checkout away from the
    bound branch while a milestone is in flight, so the honest surface is
    the same branch-ownership block the fail-closed contexts pin — and the
    roadmap claim is explicitly not asserted there (the native state is not
    operational on main), never passed or failed by inference (E1).
    """

    def test_surface_blocks_on_branch_ownership_and_roadmap_is_not_asserted(
        self, tmp_path: Path
    ) -> None:
        _write_main_build_stack(tmp_path)
        roadmap_dir = tmp_path / "prd" / "project-state" / "data"
        roadmap_dir.mkdir(parents=True)
        (roadmap_dir / "roadmap.json").write_text(
            json.dumps({"current_milestone": {"id": "post-ship-hardening", "status": "active"}}),
            encoding="utf-8",
        )

        binding = branch_context.state_binding(tmp_path)
        assert binding.bound_branch == BOUND_BRANCH
        assert binding.state_phase is StatePhase.BUILD_ACTIVE
        assert branch_context.classify_checkout(MAIN_BRANCH, binding) == Classification(
            context=BranchContext.SHIPPED_MAIN, phase=StatePhase.BUILD_ACTIVE
        )

        finding = check_workflow_state_surface(tmp_path)[0]
        assert finding.status == "fail"
        assert finding.severity == "error"
        assert finding.rule_id == "workflow-state-surface.blocking"
        assert finding.observed.startswith("kind=conflicting-ownership;")
        assert re.search(branch_context.RESOLVED_RUNTIME_PATTERN, finding.observed)
        assert branch_context.block_reason(MAIN_BRANCH, BOUND_BRANCH) in finding.observed

        roadmap = check_roadmap_freshness(tmp_path)
        assert len(roadmap) == 1
        assert roadmap[0].check_id == "roadmap-freshness"
        assert roadmap[0].status == "pass"
        assert roadmap[0].severity == "ok"
        assert "comparison=not-performed" in roadmap[0].observed


class TestSuiteSourceScan:
    """The two suites route every scenario through the one predicate (E4)."""

    def test_suites_hold_no_other_branch_detection_logic(self) -> None:
        for name in SUITE_NAMES:
            source = (Path(__file__).resolve().parent / name).read_text(encoding="utf-8")
            for forbidden in FORBIDDEN_BRANCH_LOGIC:
                assert forbidden not in source, (
                    f"{name} carries branch logic outside branch_context: {forbidden!r}"
                )
            assert "branch_context" in source, f"{name} must import branch_context"
            assert "pins_fail_closed" in source, f"{name} must route its scenario through it"


# SC2: no milestone-branch literal may key a live-suite expectation. The
# scanner flags any ``gsd-path/M0NN`` literal; a fixture payload region that
# genuinely needs one must be whitelisted here explicitly, by file and exact
# source line. Empty by contract today: the suites key every expectation on
# the STATE.md phase (branch_context.StatePhase), never on a literal.
MILESTONE_LITERAL_RE = re.compile(r"gsd-path/M0\d")
MILESTONE_LITERAL_WHITELIST: dict[str, frozenset[str]] = {}


def _milestone_literal_violations(name: str, source: str, allowed: frozenset[str]) -> list[str]:
    return [
        line
        for line in source.splitlines()
        if MILESTONE_LITERAL_RE.search(line) and line not in allowed
    ]


class TestMilestoneLiteralPin:
    """M003 SC2/E3: the literal ban is mechanical and its scanner is pinned."""

    def test_no_milestone_literals_in_expectations(self) -> None:
        for name in SUITE_NAMES:
            source = (Path(__file__).resolve().parent / name).read_text(encoding="utf-8")
            violations = _milestone_literal_violations(
                name, source, MILESTONE_LITERAL_WHITELIST.get(name, frozenset())
            )
            assert violations == [], (
                f"{name} carries milestone-branch literals outside whitelisted "
                f"fixture payloads: {violations!r}; key the expectation on the "
                "STATE.md phase (branch_context.StatePhase) instead"
            )

    def test_milestone_literal_scanner_flags_and_honors_whitelist(self) -> None:
        canary = '    assert finding.observed == "gsd-path/M004"'
        assert MILESTONE_LITERAL_RE.search(canary)
        assert _milestone_literal_violations("test_harness_governor.py", canary, frozenset()) == [
            canary
        ]
        assert (
            _milestone_literal_violations("test_harness_governor.py", canary, frozenset({canary}))
            == []
        )

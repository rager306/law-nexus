"""Contracts for the shared branch-context predicate and the scenario matrix.

Pins three things (T003 acceptance 1 and 2):

- the classification: five mutually exclusive contexts, fail-closed on an
  unreadable binding (E4);
- the four non-bound scenario contracts, each driven through the real governor
  and preflight surface checks against a fixture checkout whose runtime stack
  prints the pinned helper's recorded payload for that scenario: foreign,
  detached, and verify sidecar pin ``kind=conflicting-ownership`` with the
  runtime resolved and the scenario's own discriminator; shipped main pins
  Contract A — never collapsed into one broad expectation (E3);
- the source scan: the two live suites hold no branch-detection logic outside
  :mod:`branch_context` and no broad ``startswith("kind=")`` pinning (N3).
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import branch_context
from branch_context import BranchContext, StateBinding
from law_nexus_harness.governor import check_workflow_state_surface
from law_nexus_harness.preflight import _workflow_state_surface_check
from law_nexus_harness.workflow_state import (
    WorkflowStateKind,
    read_workflow_state,
    workflow_readiness,
)
from test_harness_workflow_state import (
    M001_ARCHIVE,
    NATIVE_STATUS_VALID,
    PINNED_RUNTIME_DIGEST,
    PINNED_RUNTIME_VERSION,
    write_operational_surface_files,
    write_shipped_main_real_stack,
)

BOUND_BRANCH = "gsd-path/M002"
FOREIGN_BRANCH = "gsd-path/M009"
SIDECAR_BRANCH = "gsd-path-verify/task-t003-verify"

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
        assert branch_context.classify_branch("main", binding) is BranchContext.SHIPPED_MAIN
        assert (
            branch_context.classify_branch("main", StateBinding(bound_branch=BOUND_BRANCH))
            is BranchContext.SHIPPED_MAIN
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
        assert M001_ARCHIVE in report.observed
        assert workflow_readiness(report) == "operational"

        finding = check_workflow_state_surface(tmp_path)[0]
        assert finding.status == "pass"
        assert finding.severity == "ok"
        assert finding.rule_id == "workflow-state-surface.shipped"
        assert finding.observed.startswith("kind=shipped-integrated;")
        assert M001_ARCHIVE in finding.observed

        check = _workflow_state_surface_check(tmp_path)
        assert check.status == "pass"
        assert "state=shipped-integrated" in check.observed
        assert M001_ARCHIVE in check.observed

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

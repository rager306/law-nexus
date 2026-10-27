"""The single shared checkout-context predicate for the live harness suites.

M002 SC2 pins the governor and preflight suites to five documented checkout
scenarios, each with its own contract:

- ``BOUND`` — the active milestone's operational build sites: the bound branch
  itself (``STATE.branch``) and the authorized ``gsd-path-task/*`` build
  worktrees. The pinned helper routes both ``run-phase`` during build (an
  authorized task worktree is a legitimate build site; live-verified
  2026-10-27), so the suites run their full substantive assertions there.
- ``FOREIGN`` — a named branch away from the bound branch while the milestone
  rules (E3's "``gsd-path/M002`` while M001 rules"): the helper blocks on
  branch ownership and the suites pin ``kind=conflicting-ownership``.
- ``DETACHED`` — a detached HEAD (CI PR merge refs): same fail-closed pin,
  with the checkout rendered as ``<detached>`` in the mismatch reason.
- ``VERIFY_SIDECAR`` — a ``gsd-path-verify/*`` verify worktree: same
  fail-closed pin, with the sidecar branch named in the mismatch reason.
- ``SHIPPED_MAIN`` — the integrated default branch: Contract A. The verified
  shipped/done state passes honestly (``kind=shipped-integrated`` with the
  archive proof), so the suites run their full substantive assertions there.

The predicate reads only two identity fields — the live branch and the
``branch:``/``default_branch:`` binding recorded in the tracked
``.project/STATE.md`` — to decide WHICH documented contract to assert. It
makes no workflow-validity claim: the typed adapter
(:mod:`law_nexus_harness.workflow_state`) stays the only validator of the
workflow state, and every scenario assertion pins the adapter's real output.
An unreadable binding can never yield ``BOUND``, so the predicate fails closed
towards the pinned contracts instead of the full assertions.
"""

from __future__ import annotations

import enum
import subprocess
from dataclasses import dataclass
from pathlib import Path

STATE_RELATIVE_PATH = ".project/STATE.md"
VERIFY_SIDECAR_PREFIX = "gsd-path-verify/"
TASK_BRANCH_PREFIX = "gsd-path-task/"
DEFAULT_BRANCH_FALLBACK = "main"

# A resolved pinned runtime renders as "runtime=<version>@<digest12>" in the
# governor finding's observed fact; "unresolved" means the runtime never
# resolved. A runtime-unavailable failure must never satisfy a branch-ownership
# pin — that is exactly what the M001 startswith("kind=") defect allowed.
RESOLVED_RUNTIME_PATTERN = r"runtime=\d+\.\d+\.\d+@[0-9a-f]{12}"


class BranchContext(enum.Enum):
    """The five documented checkout scenarios (M002 SC2)."""

    BOUND = "bound"
    FOREIGN = "foreign"
    DETACHED = "detached"
    VERIFY_SIDECAR = "verify-sidecar"
    SHIPPED_MAIN = "shipped-main"


@dataclass(frozen=True)
class StateBinding:
    """The STATE.md identity fields the predicate reads; nothing more.

    ``bound_branch`` is None when STATE.md is absent or carries no readable
    ``branch:`` value: no branch can match it, so no checkout classifies as
    ``BOUND`` and the suites stay on the pinned contracts.
    """

    bound_branch: str | None
    default_branch: str = DEFAULT_BRANCH_FALLBACK


def live_branch(root: Path) -> str | None:
    """Return the checkout's live branch, or None on a detached HEAD.

    Mirrors the pinned helper's own detection (``git symbolic-ref --quiet
    --short HEAD``), so the predicate and the helper cannot disagree about
    what detached means.
    """
    completed = subprocess.run(
        ["git", "-C", str(root), "symbolic-ref", "--quiet", "--short", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return completed.stdout.strip()
    if completed.returncode == 1:
        return None
    detail = completed.stderr.strip() or completed.stdout.strip()
    raise RuntimeError(f"could not inspect the live branch of {root}: {detail}")


def state_binding(root: Path) -> StateBinding:
    """Read the STATE.md identity fields; absent fields fail closed to None."""
    try:
        text = (root / STATE_RELATIVE_PATH).read_text(encoding="utf-8")
    except OSError:
        return StateBinding(bound_branch=None)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return StateBinding(bound_branch=None)
    bound_branch: str | None = None
    default_branch: str | None = None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        bound_branch = _identity_value(line, "branch") or bound_branch
        default_branch = _identity_value(line, "default_branch") or default_branch
    return StateBinding(
        bound_branch=bound_branch,
        default_branch=default_branch or DEFAULT_BRANCH_FALLBACK,
    )


def _identity_value(line: str, field: str) -> str | None:
    prefix = f"{field}:"
    if not line.startswith(prefix):
        return None
    value = line[len(prefix) :].split("#", 1)[0].strip()
    return value or None


def classify_branch(branch: str | None, binding: StateBinding) -> BranchContext:
    """Classify one branch against one binding into exactly one context.

    The branch shapes are mutually exclusive, so the checks can never compete;
    any named branch that is none of the special shapes is ``FOREIGN`` — away
    from the bound branch, the fail-closed branch-ownership contract applies.
    """
    if branch is None:
        return BranchContext.DETACHED
    if branch.startswith(VERIFY_SIDECAR_PREFIX):
        return BranchContext.VERIFY_SIDECAR
    if binding.bound_branch is not None and branch == binding.bound_branch:
        return BranchContext.BOUND
    if branch.startswith(TASK_BRANCH_PREFIX):
        return BranchContext.BOUND
    if branch == binding.default_branch:
        return BranchContext.SHIPPED_MAIN
    return BranchContext.FOREIGN


def classify(root: Path) -> BranchContext:
    """Classify the live checkout; the single entry point both suites call."""
    return classify_branch(live_branch(root), state_binding(root))


_FAIL_CLOSED_CONTEXTS = frozenset(
    {BranchContext.FOREIGN, BranchContext.DETACHED, BranchContext.VERIFY_SIDECAR}
)


def pins_fail_closed(context: BranchContext) -> bool:
    """Whether the context pins the fail-closed branch-ownership contract."""
    return context in _FAIL_CLOSED_CONTEXTS


def block_reason(branch: str | None, bound_branch: str) -> str:
    """Return the pinned helper's verbatim branch-ownership block reason.

    Single source for the scenario discriminators: the fixture payloads assert
    it and the live pins demand it, so they cannot drift apart.
    """
    current = branch if branch else "<detached>"
    return f"current branch {current} != STATE.branch {bound_branch}"

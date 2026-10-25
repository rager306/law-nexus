"""Typed read-only adapter between repository checks and GSD Path workflow state.

This module is ADR-0007 repository control-plane logic only. It classifies the
delivery-workflow state surface (the GSD Path ``.project/`` state, the tracked
cutover marker, and the pinned runtime declaration) into typed diagnostics for
humans and auto-mode. Contract source: docs/agent-stack/MIGRATION.md section 4.1.

The adapter is strictly read-only: it never writes or repairs workflow state,
never completes tasks, and never emits review events. The frozen GSD-Pi
snapshot is exposed as clearly marked historical evidence only; it is never a
runtime fallback. Operational Path decisions never parse STATE.md frontmatter;
the only sanctioned plain-text STATE.md surface is the legacy snapshot reader.

Every consumer of the legacy surface asks :func:`read_legacy_surface` what it
may claim, so an absent surface, a frozen surface, and a live pre-cutover
surface cannot be confused with one another.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal

WORKFLOW_STATE_SCHEMA_VERSION = "law-nexus-workflow-state-report/v1"

CUTOVER_MARKER_RELATIVE_PATH = "prd/project-state/workflow-backend.json"
CUTOVER_MARKER_SCHEMA = 1
WORKFLOW_BACKEND = "gsd-path"
RUNTIME_DECLARATION_RELATIVE_PATH = ".gsd-path/runtime.json"
RUNTIME_DECLARATION_SCHEMA = "gsd-path/runtime/v1"
STATUS_RUNTIME_SHIM_RELATIVE_PATH = ".gsd-path/status_runtime.py"
NATIVE_STATUS_SCHEMA = "gsd-path/status/v1"
PROJECT_RELATIVE_PATH = ".project"
PROJECT_STATE_RELATIVE_PATH = ".project/STATE.md"
LEGACY_GSD_RELATIVE_PATH = ".gsd"
LEGACY_GSD_STATE_RELATIVE_PATH = ".gsd/STATE.md"

RUNTIME_RESOLUTION_TIMEOUT_SECONDS = 30
_DETAIL_LIMIT = 240
_LEGACY_VALUE_LIMIT = 80
_LEGACY_HEADER_SCAN_LIMIT = 100

# Route actions of the pinned helper (`pipeline_state.py status`, Path 1.6.2).
# `run-phase` and `wait` mean the workflow needs no native recovery: the router
# either runs the current phase or waits for a promotion. The recovery actions
# mean a native helper step must happen first, which is never an operational
# verdict. An action outside both sets is contract drift and yields no verdict
# at all rather than a guess.
_NATIVE_ROUTE_ACTIONS_OPERATIONAL = frozenset({"run-phase", "wait"})
_NATIVE_ROUTE_ACTIONS_RECOVERY = frozenset(
    {
        "bind-initial",
        "block",
        "resume-checkpoint",
        "resume-next-handoff",
        "resume-promotion",
        "resume-shipment",
        "resume-undo",
        "validate-integrated",
    }
)


class WorkflowStateKind(Enum):
    """Typed classification of the delivery-workflow state surface."""

    BOOTSTRAP_NOT_CUT_OVER = "bootstrap-not-cut-over"
    OPERATIONAL_VALID = "operational-valid"
    STATE_UNVERIFIED = "state-unverified"
    MISSING_STATE = "missing-state"
    INVALID_SCHEMA = "invalid-schema"
    RUNTIME_UNAVAILABLE = "runtime-unavailable"
    RUNTIME_MISMATCH = "runtime-mismatch"
    CONFLICTING_OWNERSHIP = "conflicting-ownership"
    HISTORICAL_LEGACY = "historical-legacy"


WorkflowReadiness = Literal["operational", "bootstrap-not-cut-over", "blocked"]


class LegacySurface(Enum):
    """What the checkout holds where the frozen legacy GSD-Pi surface belongs."""

    ABSENT = "absent"
    FROZEN_HISTORICAL = "frozen-historical"
    OPERATIONAL_NOT_CUT_OVER = "operational-not-cut-over"


LegacyPolicy = Literal["applies", "historical-only", "not-applicable"]

# The governor checks whose only current-state input lives on the legacy
# surface, one per legacy artifact: the milestone registry (.gsd/STATE.md),
# the requirements register (.gsd/REQUIREMENTS.md), the flow journal
# (.gsd/journal/*.jsonl), and the projection marker (.gsd/.compat.json).
#
# An independent review showed two of these still treated frozen Pi data as the
# current truth: at cutover=true, `.gsd/STATE.md` produced a BLOCKING error from
# a 2026-10-18 backlog, and `.gsd/REQUIREMENTS.md` was read as live
# requirements. A retained archive may be history; it must not decide current
# readiness, so they now go through the same policy as the other four.
LEGACY_SURFACE_CHECKS: tuple[str, ...] = (
    "active-requirement-contradictions",
    "compat-marker-hygiene",
    "gsd-residual-debt",
    "gsd-review-dual-truth",
    "journal-retry-loops",
    "roadmap-freshness",
)

_LEGACY_SURFACE_POLICY: Mapping[LegacySurface, LegacyPolicy] = {
    LegacySurface.ABSENT: "not-applicable",
    LegacySurface.FROZEN_HISTORICAL: "historical-only",
    LegacySurface.OPERATIONAL_NOT_CUT_OVER: "applies",
}

# The one claim whose only comparison source is the legacy registry. Once
# cutover lands and the registry is gone, nobody can compare the tracked
# roadmap against anything, so the claim becomes unverifiable instead of true.
# The other three lose coverage rather than correctness and stay
# not-applicable.
_LEGACY_SURFACE_BLOCKING_CHECKS: frozenset[str] = frozenset({"roadmap-freshness"})


@dataclass(frozen=True)
class WorkflowRuntimeInfo:
    """Best-known pinned runtime identity behind a workflow-state report."""

    version: str | None
    digest: str | None
    path: str | None


NO_RUNTIME_INFO = WorkflowRuntimeInfo(version=None, digest=None, path=None)


@dataclass(frozen=True)
class CutoverMarker:
    """Parsed tracked cutover marker (prd/project-state/workflow-backend.json)."""

    cutover: bool


@dataclass(frozen=True)
class RuntimeDeclaration:
    """Pinned runtime identity declared in .gsd-path/runtime.json."""

    version: str
    digest: str


@dataclass(frozen=True)
class RuntimeDeclarationRead:
    """Outcome of reading the tracked runtime declaration."""

    status: Literal["valid", "missing", "invalid"]
    declaration: RuntimeDeclaration | None = None
    detail: str = ""


@dataclass(frozen=True)
class RuntimeResolution:
    """Outcome of resolving the pinned runtime cache through the launcher shim."""

    available: bool
    runtime_path: Path | None
    version: str | None
    digest: str | None
    detail: str


RuntimeResolver = Callable[[Path], RuntimeResolution]
NativeStatusRunner = Callable[[Path, Path], dict[str, Any]]


def run_pinned_native_status(root: Path, runtime_path: Path) -> dict[str, Any]:
    """Read the pinned Path helper's own status verdict (the only real proof).

    ``pipeline_state.py status --repo <abs>`` prints exactly one sorted JSON
    object on success and exits non-zero with ``error: ...`` on stderr when it
    cannot prove the state. Anything other than one clean JSON object raises:
    a payload we could not read is not evidence that the state is valid.

    This is the production runner. It is deliberately the default in
    :func:`read_workflow_state` callers so that "no runner wired" cannot read as
    operational; passing ``None`` explicitly now yields ``state-unverified``.
    """

    helper = runtime_path / "pipeline_state.py"
    if not helper.is_file():
        raise RuntimeError(f"pinned runtime has no pipeline_state.py at {runtime_path}")
    completed = subprocess.run(
        [sys.executable, "-B", str(helper), "status", "--repo", str(root)],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        raise RuntimeError(
            f"exit {completed.returncode}: {detail[0] if detail else 'no diagnostic'}"
        )
    try:
        payload = json.loads(completed.stdout)
    except ValueError as error:
        raise RuntimeError(f"status output is not JSON: {error}") from error
    if not isinstance(payload, dict):
        raise RuntimeError("status output must be a JSON object")
    return payload


@dataclass(frozen=True)
class WorkflowStateReport:
    """Stable, read-only workflow-state diagnostic for humans and auto-mode."""

    schema_version: str
    kind: WorkflowStateKind
    observed: str
    remediation: str
    detail: str
    evidence: tuple[str, ...]
    runtime: WorkflowRuntimeInfo
    legacy_gsd_present: bool

    def to_dict(self) -> dict[str, Any]:
        """Return the stable JSON-compatible result mapping."""

        payload: dict[str, Any] = asdict(self)
        payload["kind"] = self.kind.value
        return payload

    def to_json(self) -> str:
        """Return deterministic JSON with a trailing newline."""

        return (
            json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        )


def _head(value: bytes | str | None, limit: int = _DETAIL_LIMIT) -> str:
    """Return the bounded head of a subprocess output or error message."""

    if value is None:
        return ""
    text = value if isinstance(value, str) else value.decode("utf-8", errors="replace")
    return text.strip()[:limit]


def _bounded_value(value: str, limit: int = _LEGACY_VALUE_LIMIT) -> str:
    """Bound one human-readable legacy header value."""

    return value if len(value) <= limit else value[: limit - 3] + "..."


def _legacy_gsd_present(root: Path) -> bool:
    """Whether the frozen legacy GSD-Pi surface is present (dangling links count)."""

    legacy = root / ".gsd"
    return legacy.exists() or legacy.is_symlink()


def _report(
    kind: WorkflowStateKind,
    *,
    observed: str,
    remediation: str,
    legacy_gsd_present: bool,
    detail: str = "",
    evidence: tuple[str, ...] = (),
    runtime: WorkflowRuntimeInfo = NO_RUNTIME_INFO,
) -> WorkflowStateReport:
    return WorkflowStateReport(
        schema_version=WORKFLOW_STATE_SCHEMA_VERSION,
        kind=kind,
        observed=observed,
        remediation=remediation,
        detail=detail,
        evidence=evidence,
        runtime=runtime,
        legacy_gsd_present=legacy_gsd_present,
    )


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


@dataclass(frozen=True)
class LegacySurfaceDecision:
    """The single decision point for reads of the frozen legacy GSD surface.

    ``surface`` states what the checkout holds; :meth:`policy` states what a
    legacy-surface check may claim about it. ``cutover`` is the tracked marker
    value, and False whenever the marker is missing or unreadable: a cutover
    nobody proved has not happened, so it can never turn into a blocker.
    """

    surface: LegacySurface
    cutover: bool
    detail: str = ""

    def policy(self, check_id: str) -> LegacyPolicy:
        """Return the policy that governs ``check_id`` on this surface."""

        self._require_legacy_check(check_id)
        return _LEGACY_SURFACE_POLICY[self.surface]

    def blocks(self, check_id: str) -> bool:
        """Whether this surface makes ``check_id``'s claim unverifiable.

        Only a check whose sole comparison source is the legacy registry can
        lose its whole claim with that registry (``roadmap-freshness``), and
        only after cutover: before cutover the missing projection is a state
        the bootstrap path already owns.
        """

        return (
            self._require_legacy_check(check_id) in _LEGACY_SURFACE_BLOCKING_CHECKS
            and self.surface is LegacySurface.ABSENT
            and self.cutover
        )

    def observed(self, check_id: str) -> str:
        """Stable observed tokens naming the surface, its policy, and cutover."""

        return f"{self.surface_tokens()}; policy={self.policy(check_id)}"

    def surface_tokens(self) -> str:
        """Stable observed tokens naming the surface and the cutover marker."""

        return f"legacy_surface={self.surface.value}; cutover={'true' if self.cutover else 'false'}"

    @staticmethod
    def _require_legacy_check(check_id: str) -> str:
        if check_id not in LEGACY_SURFACE_CHECKS:
            raise ValueError(f"not a legacy-surface check: {check_id}")
        return check_id


def read_legacy_surface(root: Path) -> LegacySurfaceDecision:
    """Classify the legacy surface and its authority in one read-only call.

    A surface that exists counts even as a dangling symlink: a checkout
    pointing at a vanished snapshot has not stopped carrying the surface, and
    the checks must say the registry is unreadable rather than absent.
    """

    resolved_root = root.resolve()
    marker, marker_detail = _read_cutover_marker(resolved_root)
    cutover = marker is not None and marker.cutover
    if not _legacy_gsd_present(resolved_root):
        detail = f"{LEGACY_GSD_RELATIVE_PATH} is absent"
        if marker_detail:
            detail = f"{detail}; {marker_detail}"
        return LegacySurfaceDecision(surface=LegacySurface.ABSENT, cutover=cutover, detail=detail)
    surface = LegacySurface.FROZEN_HISTORICAL if cutover else LegacySurface.OPERATIONAL_NOT_CUT_OVER
    return LegacySurfaceDecision(surface=surface, cutover=cutover, detail=marker_detail)


def _read_cutover_marker(root: Path) -> tuple[CutoverMarker | None, str]:
    """Read the tracked cutover marker; missing or invalid payloads fail closed."""

    path = root / CUTOVER_MARKER_RELATIVE_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return None, "cutover marker missing"
    except json.JSONDecodeError as error:
        return None, f"cutover marker is not valid JSON: {_head(str(error))}"
    if not isinstance(payload, dict) or set(payload) != {"schema", "backend", "cutover"}:
        return None, "cutover marker must be an object with exactly schema, backend, cutover"
    if payload["schema"] != CUTOVER_MARKER_SCHEMA or isinstance(payload["schema"], bool):
        return None, f"cutover marker schema must be the integer {CUTOVER_MARKER_SCHEMA}"
    if payload["backend"] != WORKFLOW_BACKEND:
        return None, f"cutover marker backend must be {WORKFLOW_BACKEND!r}"
    if not isinstance(payload["cutover"], bool):
        return None, "cutover marker cutover must be a boolean"
    return CutoverMarker(cutover=payload["cutover"]), ""


def _read_runtime_declaration(root: Path) -> RuntimeDeclarationRead:
    """Read the tracked runtime declaration without running the launcher shim."""

    path = root / RUNTIME_DECLARATION_RELATIVE_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return RuntimeDeclarationRead(status="missing", detail="declaration missing")
    except json.JSONDecodeError as error:
        return RuntimeDeclarationRead(
            status="invalid", detail=f"runtime declaration is not valid JSON: {_head(str(error))}"
        )
    if not isinstance(payload, dict) or payload.get("schema") != RUNTIME_DECLARATION_SCHEMA:
        return RuntimeDeclarationRead(
            status="invalid",
            detail=f"runtime declaration schema must be {RUNTIME_DECLARATION_SCHEMA!r}",
        )
    version = payload.get("version")
    digest = payload.get("digest")
    if not isinstance(version, str) or not version:
        return RuntimeDeclarationRead(
            status="invalid", detail="runtime declaration version must be a non-empty string"
        )
    if not isinstance(digest, str) or not _is_sha256_hex(digest):
        return RuntimeDeclarationRead(
            status="invalid",
            detail="runtime declaration digest must be a 64-character lowercase hex string",
        )
    return RuntimeDeclarationRead(
        status="valid", declaration=RuntimeDeclaration(version=version, digest=digest)
    )


def _runtime_manifest_version(runtime_path: Path) -> str | None:
    """Read the version the resolved runtime cache carries in its manifest."""

    try:
        payload = json.loads((runtime_path / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    version = payload.get("version") if isinstance(payload, dict) else None
    if not isinstance(version, str) or not version:
        return None
    return version


def resolve_pinned_runtime(root: Path) -> RuntimeResolution:
    """Resolve the pinned GSD Path runtime cache through the launcher shim.

    The subprocess runs only when the tracked shim exists; the shim itself
    validates the cache against the tracked declaration and prints the
    absolute runtime directory path.
    """

    shim = root / STATUS_RUNTIME_SHIM_RELATIVE_PATH
    if not shim.is_file():
        return RuntimeResolution(
            available=False,
            runtime_path=None,
            version=None,
            digest=None,
            detail="launcher shim missing",
        )
    command = [
        sys.executable,
        "-B",
        str(shim),
        "--repo",
        str(root),
        "--runtime-path",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            check=False,
            capture_output=True,
            timeout=RUNTIME_RESOLUTION_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return RuntimeResolution(
            available=False,
            runtime_path=None,
            version=None,
            digest=None,
            detail="launcher shim timed out",
        )
    except OSError as error:
        return RuntimeResolution(
            available=False,
            runtime_path=None,
            version=None,
            digest=None,
            detail=f"launcher shim failed to start: {_head(str(error))}",
        )
    if completed.returncode != 0:
        return RuntimeResolution(
            available=False,
            runtime_path=None,
            version=None,
            digest=None,
            detail=(
                f"launcher shim failed with exit {completed.returncode}: {_head(completed.stderr)}"
            ),
        )
    stdout = completed.stdout.decode("utf-8", errors="replace") if completed.stdout else ""
    runtime_path = Path(stdout.strip())
    if not runtime_path.is_absolute() or not runtime_path.is_dir():
        return RuntimeResolution(
            available=False,
            runtime_path=None,
            version=None,
            digest=None,
            detail="launcher shim did not return an absolute runtime directory",
        )
    version = _runtime_manifest_version(runtime_path)
    if version is None:
        return RuntimeResolution(
            available=False,
            runtime_path=None,
            version=None,
            digest=None,
            detail=f"resolved runtime carries no readable manifest version: {runtime_path}",
        )
    return RuntimeResolution(
        available=True,
        runtime_path=runtime_path,
        version=version,
        digest=runtime_path.name,
        detail="",
    )


def _declared_runtime_info(declaration: RuntimeDeclaration) -> WorkflowRuntimeInfo:
    return WorkflowRuntimeInfo(version=declaration.version, digest=declaration.digest, path=None)


def _resolved_runtime_info(resolution: RuntimeResolution) -> WorkflowRuntimeInfo:
    return WorkflowRuntimeInfo(
        version=resolution.version,
        digest=resolution.digest,
        path=str(resolution.runtime_path) if resolution.runtime_path is not None else None,
    )


class _NativeStatusError(Exception):
    """The native status helper produced no usable verdict."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True)
class _NativeStatusVerdict:
    """The single positive signal the adapter accepts from the native helper."""

    action: str
    reason: str

    @property
    def operational(self) -> bool:
        return self.action in _NATIVE_ROUTE_ACTIONS_OPERATIONAL


def _native_status_verdict(
    runner: NativeStatusRunner,
    root: Path,
    runtime_path: Path,
) -> _NativeStatusVerdict:
    """Translate one pinned-helper status payload into a verdict.

    The pinned helper (``pipeline_state.py status``, Path 1.6.2) prints exactly
    one JSON object with ``sort_keys=True`` and exits 1 with ``error: ...`` on
    stderr when it cannot prove the state, so a parsed payload is itself the
    proof that STATE.md passed native validation. Three keys are read:
    ``schema`` (must be ``gsd-path/status/v1``), ``state`` (the parsed STATE.md
    fields), and ``route`` (``action`` plus ``reason``). Anything else is
    refused rather than guessed at.
    """

    try:
        payload = runner(root, runtime_path)
    except Exception as error:  # a helper that did not print a payload proved nothing
        raise _NativeStatusError(f"native status helper failed: {_head(str(error))}") from error
    if not isinstance(payload, dict):
        raise _NativeStatusError(
            f"native status payload must be a JSON object, got {type(payload).__name__}"
        )
    if payload.get("schema") != NATIVE_STATUS_SCHEMA:
        raise _NativeStatusError(f"native status schema must be {NATIVE_STATUS_SCHEMA!r}")
    state = payload.get("state")
    if not isinstance(state, dict) or not isinstance(state.get("phase"), str):
        raise _NativeStatusError("native status payload must carry the parsed state fields")
    route = payload.get("route")
    if not isinstance(route, dict):
        raise _NativeStatusError("native status payload must carry a route object")
    action = route.get("action")
    if not isinstance(action, str) or not action:
        raise _NativeStatusError("native status payload must carry a route action")
    if action not in _NATIVE_ROUTE_ACTIONS_OPERATIONAL | _NATIVE_ROUTE_ACTIONS_RECOVERY:
        raise _NativeStatusError(f"native status route action is unknown: {action!r}")
    reason = route.get("reason")
    return _NativeStatusVerdict(
        action=action,
        reason=reason if isinstance(reason, str) and reason else "<missing>",
    )


def read_workflow_state(
    root: Path,
    *,
    runtime_resolver: RuntimeResolver = resolve_pinned_runtime,
    native_status_runner: NativeStatusRunner | None = run_pinned_native_status,
) -> WorkflowStateReport:
    """Classify the GSD Path workflow state surface without mutating anything."""

    resolved_root = root.resolve()
    legacy_gsd_present = _legacy_gsd_present(resolved_root)

    marker, marker_detail = _read_cutover_marker(resolved_root)
    if marker is None:
        return _report(
            WorkflowStateKind.INVALID_SCHEMA,
            observed="The workflow backend cutover marker is missing or invalid.",
            remediation=(
                "Restore prd/project-state/workflow-backend.json to the tracked contract: "
                "schema 1, backend gsd-path, and an explicit cutover boolean."
            ),
            detail=marker_detail,
            evidence=(CUTOVER_MARKER_RELATIVE_PATH,),
            legacy_gsd_present=legacy_gsd_present,
        )

    project = resolved_root / PROJECT_RELATIVE_PATH
    state = project / "STATE.md"
    if not project.exists() and not project.is_symlink():
        if marker.cutover:
            return _report(
                WorkflowStateKind.MISSING_STATE,
                observed="Operational mode: the GSD Path project state is missing.",
                remediation=(
                    "Run native Path initialization on the clean origin baseline; "
                    "do not hand-create .project/STATE.md."
                ),
                evidence=(CUTOVER_MARKER_RELATIVE_PATH, PROJECT_RELATIVE_PATH),
                legacy_gsd_present=legacy_gsd_present,
            )
        return _report(
            WorkflowStateKind.BOOTSTRAP_NOT_CUT_OVER,
            observed=(
                "Bootstrap mode: the GSD Path project is not initialized yet and the "
                "tracked cutover marker is still false."
            ),
            remediation=(
                "Continue the migration bootstrap; native Path initialization happens at C4 "
                "and the owner flips the cutover marker at C7."
            ),
            evidence=(CUTOVER_MARKER_RELATIVE_PATH,),
            legacy_gsd_present=legacy_gsd_present,
        )

    if project.is_symlink():
        return _report(
            WorkflowStateKind.INVALID_SCHEMA,
            observed="The .project directory is a symlink instead of owned Path state.",
            remediation=(
                "Classify the unowned .project surface with the native helper "
                "(detect_project.py classify); do not treat it as an empty project."
            ),
            detail="symlinked .project",
            evidence=(PROJECT_RELATIVE_PATH,),
            legacy_gsd_present=legacy_gsd_present,
        )
    if state.is_symlink() or not state.is_file():
        return _report(
            WorkflowStateKind.INVALID_SCHEMA,
            observed=(
                "The .project directory exists without an owned STATE.md (orphan artifacts)."
            ),
            remediation=(
                "Classify the orphan .project artifacts with the native helper "
                "(detect_project.py classify); do not treat them as an empty project."
            ),
            detail="symlinked STATE.md"
            if state.is_symlink()
            else "no owned STATE.md under .project",
            evidence=(PROJECT_RELATIVE_PATH,),
            legacy_gsd_present=legacy_gsd_present,
        )

    declaration_read = _read_runtime_declaration(resolved_root)
    if declaration_read.status == "missing":
        return _report(
            WorkflowStateKind.RUNTIME_UNAVAILABLE,
            observed="The pinned GSD Path runtime declaration is missing.",
            remediation=(
                "Run the pinned bootstrap stage that installs the tracked "
                ".gsd-path/runtime.json declaration."
            ),
            detail=declaration_read.detail,
            evidence=(RUNTIME_DECLARATION_RELATIVE_PATH,),
            legacy_gsd_present=legacy_gsd_present,
        )
    if declaration_read.status == "invalid" or declaration_read.declaration is None:
        return _report(
            WorkflowStateKind.INVALID_SCHEMA,
            observed="The pinned GSD Path runtime declaration is unparseable or unsupported.",
            remediation=(
                "Reinstall the pinned Path runtime through the native bootstrap; "
                "do not hand-edit .gsd-path/runtime.json."
            ),
            detail=declaration_read.detail,
            evidence=(RUNTIME_DECLARATION_RELATIVE_PATH,),
            legacy_gsd_present=legacy_gsd_present,
        )
    declaration = declaration_read.declaration

    resolution = runtime_resolver(resolved_root)
    if not resolution.available or resolution.runtime_path is None:
        return _report(
            WorkflowStateKind.RUNTIME_UNAVAILABLE,
            observed="The pinned GSD Path runtime could not be resolved.",
            remediation=(
                "Restore the exact pinned runtime with the native --runtime-restore flow; "
                "do not substitute a different version."
            ),
            detail=resolution.detail,
            evidence=(RUNTIME_DECLARATION_RELATIVE_PATH, STATUS_RUNTIME_SHIM_RELATIVE_PATH),
            runtime=_declared_runtime_info(declaration),
            legacy_gsd_present=legacy_gsd_present,
        )
    if resolution.digest != declaration.digest or resolution.version != declaration.version:
        return _report(
            WorkflowStateKind.RUNTIME_MISMATCH,
            observed="The resolved GSD Path runtime does not match the tracked declaration.",
            remediation=(
                "Restore the exact runtime declared in .gsd-path/runtime.json; "
                "do not edit the declaration to match a different cache."
            ),
            detail=(
                f"declared version={declaration.version} digest={declaration.digest}; "
                f"resolved version={resolution.version} digest={resolution.digest}"
            ),
            evidence=(RUNTIME_DECLARATION_RELATIVE_PATH,),
            runtime=_resolved_runtime_info(resolution),
            legacy_gsd_present=legacy_gsd_present,
        )

    runtime_info = _resolved_runtime_info(resolution)
    if native_status_runner is None:
        return _report(
            WorkflowStateKind.STATE_UNVERIFIED,
            observed=(
                "GSD Path workflow state is present and the pinned runtime is resolved, "
                "but the state is unverified: the native status helper is not wired, "
                "so STATE.md itself was never validated."
            ),
            remediation=(
                "Wire the native status helper (pipeline_state.py status) into the "
                "caller; until it runs, this project is not operational."
            ),
            detail="unverified: native status helper not wired",
            evidence=(PROJECT_STATE_RELATIVE_PATH, RUNTIME_DECLARATION_RELATIVE_PATH),
            runtime=runtime_info,
            legacy_gsd_present=legacy_gsd_present,
        )
    try:
        verdict = _native_status_verdict(
            native_status_runner, resolved_root, resolution.runtime_path
        )
    except _NativeStatusError as error:
        return _report(
            WorkflowStateKind.INVALID_SCHEMA,
            observed=(
                "The native status helper produced no usable verdict, so STATE.md "
                "is not proven valid."
            ),
            remediation=(
                "Make the native status helper emit its typed gsd-path/status/v1 "
                "payload and exit non-zero on failure; do not guess the workflow "
                "state from STATE.md text."
            ),
            detail=error.detail,
            evidence=(PROJECT_STATE_RELATIVE_PATH,),
            runtime=runtime_info,
            legacy_gsd_present=legacy_gsd_present,
        )
    if verdict.operational:
        return _report(
            WorkflowStateKind.OPERATIONAL_VALID,
            observed=(
                "GSD Path workflow state is valid; native status validated STATE.md "
                f"and routes {verdict.action}."
            ),
            remediation="none",
            detail=f"native status route={verdict.action}: {verdict.reason}",
            evidence=(PROJECT_STATE_RELATIVE_PATH, RUNTIME_DECLARATION_RELATIVE_PATH),
            runtime=runtime_info,
            legacy_gsd_present=legacy_gsd_present,
        )
    return _report(
        WorkflowStateKind.CONFLICTING_OWNERSHIP,
        observed=(
            "Native status validated STATE.md but routes a native recovery step "
            f"first (route: {verdict.action}; reason: {verdict.reason})."
        ),
        remediation=(
            "Follow the native Path recovery flow for the reported route; "
            "do not repair STATE.md by hand."
        ),
        detail=f"native status route={verdict.action}: {verdict.reason}",
        evidence=(PROJECT_STATE_RELATIVE_PATH,),
        runtime=runtime_info,
        legacy_gsd_present=legacy_gsd_present,
    )


def read_legacy_gsd_snapshot(root: Path) -> WorkflowStateReport:
    """Read the frozen GSD-Pi snapshot header as historical, non-authoritative evidence.

    This is the only sanctioned plain-text STATE.md surface in the harness.
    The report is historical evidence, never an operational workflow state or
    a runtime fallback; ``workflow_readiness`` classifies it as blocked.
    """

    resolved_root = root.resolve()
    legacy_gsd_present = _legacy_gsd_present(resolved_root)
    state = resolved_root / LEGACY_GSD_STATE_RELATIVE_PATH
    if not state.is_file():
        return _report(
            WorkflowStateKind.HISTORICAL_LEGACY,
            observed=(
                "Frozen GSD-Pi snapshot is not available; no legacy header evidence "
                "(historical, non-authoritative)."
            ),
            remediation="none (historical evidence only)",
            legacy_gsd_present=legacy_gsd_present,
        )
    milestone: str | None = None
    phase: str | None = None
    lines = state.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[:_LEGACY_HEADER_SCAN_LIMIT]:
        if line.startswith("## "):
            break
        if milestone is None and line.startswith("**Active Milestone:** "):
            milestone = line[len("**Active Milestone:** ") :].strip()
        elif phase is None and line.startswith("**Phase:** "):
            phase = line[len("**Phase:** ") :].strip()
    parts: list[str] = []
    if milestone is not None:
        parts.append(f"Active Milestone {_bounded_value(milestone)}")
    if phase is not None:
        parts.append(f"Phase {_bounded_value(phase)}")
    if not parts:
        return _report(
            WorkflowStateKind.HISTORICAL_LEGACY,
            observed=(
                "Frozen GSD-Pi STATE.md carries no recognizable header fields "
                "(historical, non-authoritative)."
            ),
            remediation="none (historical evidence only)",
            evidence=(LEGACY_GSD_STATE_RELATIVE_PATH,),
            legacy_gsd_present=legacy_gsd_present,
        )
    return _report(
        WorkflowStateKind.HISTORICAL_LEGACY,
        observed=(
            "Frozen GSD-Pi snapshot (historical, non-authoritative): " + "; ".join(parts) + "."
        ),
        remediation="none (historical evidence only)",
        evidence=(LEGACY_GSD_STATE_RELATIVE_PATH,),
        legacy_gsd_present=legacy_gsd_present,
    )


def workflow_readiness(report: WorkflowStateReport) -> WorkflowReadiness:
    """Map one workflow-state report to the coarse harness readiness verdict.

    Only a state the native helper actually validated is operational. Everything
    else blocks, including ``STATE_UNVERIFIED`` (present but never validated),
    ``MISSING_STATE``, ``INVALID_SCHEMA``, and ``CONFLICTING_OWNERSHIP``; the
    fallthrough keeps a future kind fail-closed by default.
    """

    if report.kind is WorkflowStateKind.OPERATIONAL_VALID:
        return "operational"
    if report.kind is WorkflowStateKind.BOOTSTRAP_NOT_CUT_OVER:
        return "bootstrap-not-cut-over"
    return "blocked"

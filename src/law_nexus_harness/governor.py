"""Trajectory governor for repository control-plane checks.

Read-only anti-drift checks that catch the debt patterns observed after
hostile-case milestones: GSD complete while roadmap lags, missing completed
ranges, and hostile-proof aggregate mismatch.

This module is repository metadata policy only. It does not implement product
or legal-domain behavior (ADR-0007).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

GOVERNOR_SCHEMA_VERSION = "law-nexus-governor-report/v1"

Severity = Literal["error", "warn", "ok"]
CheckStatus = Literal["pass", "fail"]

_REGISTRY_ROW_RE = re.compile(
    r"^\s*-\s*(?P<marker>✅|🔄|⏸|🟡|⚪)\s*\*\*M(?P<seq>\d+)(?:-[a-z0-9]+)?:\*\*\s*(?P<title>.+?)\s*$"
)
_ACTIVE_MILESTONE_RE = re.compile(
    r"^\*\*Active Milestone:\*\*\s*M(?P<seq>\d+)(?:-(?P<rand>[a-z0-9]+))?",
    re.IGNORECASE,
)
_LAST_COMPLETED_RE = re.compile(
    r"^\*\*Last Completed Milestone:\*\*\s*M(?P<seq>\d+)(?:-(?P<rand>[a-z0-9]+))?",
    re.IGNORECASE,
)
_MSEQ_RE = re.compile(r"^M(\d+)(?:-[a-z0-9]+)?$")
_RANGE_RE = re.compile(r"M(\d+)\s*[-–]\s*M(\d+)")
_HC_PROOF_RE = re.compile(r"^hc(\d{2})-.*-runtime\.json$")
_BASELINE_AGG_RE = re.compile(
    r"PASS\s+(\d+)/20;\s*FAIL\s+(\d+)/20;\s*`?unsupported-case`?\s+(\d+)/20",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GovernorFinding:
    check_id: str
    status: CheckStatus
    severity: Severity
    message: str
    observed: str
    remediation: str


@dataclass(frozen=True)
class GovernorReport:
    schema_version: str
    status: Literal["ok", "failure"]
    root: str
    findings: tuple[GovernorFinding, ...]
    error_count: int
    warn_count: int
    pass_count: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [asdict(item) for item in self.findings]
        return payload

    def to_json(self) -> str:
        return (
            json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        )


def _registry_milestones(state_text: str) -> list[tuple[int, str, str]]:
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


def _last_completed_seq(state_text: str) -> int | None:
    for line in state_text.splitlines():
        match = _LAST_COMPLETED_RE.match(line.strip())
        if match:
            return int(match.group("seq"))
    return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_roadmap_freshness(root: Path) -> list[GovernorFinding]:
    """Mirror the project-state roadmap freshness invariants."""

    findings: list[GovernorFinding] = []
    state_path = root / ".gsd" / "STATE.md"
    roadmap_path = root / "prd" / "project-state" / "data" / "roadmap.json"
    if not state_path.is_file():
        return [
            GovernorFinding(
                check_id="roadmap-state-present",
                status="fail",
                severity="error",
                message="GSD STATE.md is missing",
                observed=str(state_path),
                remediation="Restore .gsd/STATE.md from GSD engine state",
            )
        ]
    if not roadmap_path.is_file():
        return [
            GovernorFinding(
                check_id="roadmap-json-present",
                status="fail",
                severity="error",
                message="roadmap.json is missing",
                observed=str(roadmap_path),
                remediation="Restore prd/project-state/data/roadmap.json",
            )
        ]

    state_text = state_path.read_text(encoding="utf-8")
    roadmap = _load_json(roadmap_path)
    rows = _registry_milestones(state_text)
    completed_seqs = [seq for seq, marker, _ in rows if marker == "✅"]
    latest_completed = max(completed_seqs) if completed_seqs else None
    active_seq = _active_milestone_seq(state_text)
    current_id = str(roadmap.get("current_milestone", {}).get("id", ""))
    current_match = _MSEQ_RE.match(current_id)
    current_seq = int(current_match.group(1)) if current_match else None
    claimed_status = str(roadmap.get("current_milestone", {}).get("status", ""))

    if latest_completed is None:
        findings.append(
            GovernorFinding(
                check_id="roadmap-completed-exists",
                status="fail",
                severity="error",
                message="No completed milestones found in GSD registry",
                observed="completed_seqs=[]",
                remediation="Complete at least one milestone before relying on roadmap freshness",
            )
        )
        return findings

    accepted = {latest_completed}
    if active_seq is not None:
        accepted.add(active_seq)
    if current_seq in accepted:
        findings.append(
            GovernorFinding(
                check_id="roadmap-current-tracks-gsd",
                status="pass",
                severity="ok",
                message="roadmap current_milestone tracks latest completed or active GSD milestone",
                observed=f"current=M{current_seq}; latest_completed=M{latest_completed}; active={active_seq}",
                remediation="none",
            )
        )
    else:
        findings.append(
            GovernorFinding(
                check_id="roadmap-current-tracks-gsd",
                status="fail",
                severity="error",
                message="roadmap current_milestone lags GSD completed state",
                observed=f"current={current_id!r}; latest_completed=M{latest_completed}; active={active_seq}",
                remediation=(
                    "Refresh prd/project-state/data/roadmap.json and roadmap.md so "
                    f"current_milestone is M{latest_completed} (or the active milestone)"
                ),
            )
        )

    by_seq = {seq: marker for seq, marker, _ in rows}
    marker = by_seq.get(current_seq) if current_seq is not None else None
    expected_status = "complete" if marker == "✅" else "active"
    if claimed_status == expected_status:
        findings.append(
            GovernorFinding(
                check_id="roadmap-current-status",
                status="pass",
                severity="ok",
                message="roadmap current_milestone status matches GSD marker",
                observed=f"status={claimed_status}; marker={marker}",
                remediation="none",
            )
        )
    else:
        findings.append(
            GovernorFinding(
                check_id="roadmap-current-status",
                status="fail",
                severity="error",
                message="roadmap current_milestone status disagrees with GSD marker",
                observed=f"claimed={claimed_status!r}; expected={expected_status!r}; marker={marker!r}",
                remediation="Set current_milestone.status to match GSD complete/active marker",
            )
        )

    max_upper = 0
    for group in roadmap.get("completed_milestone_groups", []):
        if not isinstance(group, dict):
            continue
        match = _RANGE_RE.search(str(group.get("range", "")))
        if match:
            max_upper = max(max_upper, int(match.group(2)))
    if max_upper >= latest_completed:
        findings.append(
            GovernorFinding(
                check_id="roadmap-range-coverage",
                status="pass",
                severity="ok",
                message="completed_milestone_groups cover through latest completed GSD milestone",
                observed=f"max_upper=M{max_upper}; latest_completed=M{latest_completed}",
                remediation="none",
            )
        )
    else:
        findings.append(
            GovernorFinding(
                check_id="roadmap-range-coverage",
                status="fail",
                severity="error",
                message="completed_milestone_groups do not cover latest completed GSD milestone",
                observed=f"max_upper=M{max_upper}; latest_completed=M{latest_completed}",
                remediation=(
                    f"Add completed range M{latest_completed}-M{latest_completed} "
                    "(or extend an existing range) in roadmap.json"
                ),
            )
        )

    return findings


def check_hostile_proof_chain(root: Path) -> list[GovernorFinding]:
    """Ensure tracked hostile runtime proofs form a contiguous PASS prefix."""

    findings: list[GovernorFinding] = []
    probes = root / "prd" / "migration" / "rust-evidence" / "probes"
    if not probes.is_dir():
        return [
            GovernorFinding(
                check_id="hostile-probes-dir",
                status="fail",
                severity="error",
                message="hostile proof probe directory is missing",
                observed=str(probes),
                remediation="Restore prd/migration/rust-evidence/probes/",
            )
        ]

    by_case: dict[int, dict[str, Any]] = {}
    for path in sorted(probes.glob("hc*-runtime.json")):
        match = _HC_PROOF_RE.match(path.name)
        if not match:
            continue
        case_num = int(match.group(1))
        payload = _load_json(path)
        by_case[case_num] = payload
        evidence_id = str(payload.get("evidence_id", ""))
        expected_evidence = f"S10-HC-{case_num:02d}-RT"
        verdict = str(payload.get("verdict", ""))
        remaining = payload.get("remaining_unsupported_cases")
        expected_remaining = 20 - case_num
        if (
            evidence_id == expected_evidence
            and verdict == "PASS"
            and remaining == expected_remaining
        ):
            findings.append(
                GovernorFinding(
                    check_id=f"hostile-proof-hc{case_num:02d}",
                    status="pass",
                    severity="ok",
                    message=f"HC-{case_num:02d} tracked proof is coherent",
                    observed=f"{path.name}: verdict={verdict}; remaining={remaining}",
                    remediation="none",
                )
            )
        else:
            findings.append(
                GovernorFinding(
                    check_id=f"hostile-proof-hc{case_num:02d}",
                    status="fail",
                    severity="error",
                    message=f"HC-{case_num:02d} tracked proof is incoherent",
                    observed=(
                        f"{path.name}: evidence_id={evidence_id!r}; verdict={verdict!r}; "
                        f"remaining={remaining!r}; expected remaining={expected_remaining}"
                    ),
                    remediation=(
                        "Rewrite the tracked proof package so evidence_id, verdict and "
                        "remaining_unsupported_cases match the contiguous PASS prefix"
                    ),
                )
            )

    if not by_case:
        findings.append(
            GovernorFinding(
                check_id="hostile-proof-present",
                status="fail",
                severity="warn",
                message="no hostile runtime proof packages found",
                observed="probes empty of hcNN-*-runtime.json",
                remediation="Produce S10-HC-NN-RT packages as hostile cases land",
            )
        )
        return findings

    # Contiguous prefix: if HC-N exists as PASS, HC-1..HC-(N-1) must also exist as PASS.
    max_case = max(by_case)
    missing = [n for n in range(1, max_case + 1) if n not in by_case]
    if not missing:
        findings.append(
            GovernorFinding(
                check_id="hostile-proof-contiguous",
                status="pass",
                severity="ok",
                message="hostile proof packages form a contiguous case prefix",
                observed=f"cases={sorted(by_case)}",
                remediation="none",
            )
        )
    else:
        findings.append(
            GovernorFinding(
                check_id="hostile-proof-contiguous",
                status="fail",
                severity="error",
                message="hostile proof packages skip earlier cases",
                observed=f"present={sorted(by_case)}; missing={missing}",
                remediation="Do not admit a later HC proof while earlier HC proofs are absent",
            )
        )

    baseline_path = root / "prd" / "architecture" / "m111-final-architecture-baseline.md"
    if baseline_path.is_file():
        text = baseline_path.read_text(encoding="utf-8")
        match = _BASELINE_AGG_RE.search(text)
        expected_pass = max_case
        expected_fail = 0
        expected_unsupported = 20 - max_case
        if match and (
            int(match.group(1)) == expected_pass
            and int(match.group(2)) == expected_fail
            and int(match.group(3)) == expected_unsupported
        ):
            findings.append(
                GovernorFinding(
                    check_id="hostile-baseline-aggregate",
                    status="pass",
                    severity="ok",
                    message="baseline runtime aggregate matches tracked hostile PASS prefix",
                    observed=match.group(0),
                    remediation="none",
                )
            )
        else:
            observed = match.group(0) if match else "aggregate row not found"
            findings.append(
                GovernorFinding(
                    check_id="hostile-baseline-aggregate",
                    status="fail",
                    severity="error",
                    message="baseline runtime aggregate does not match tracked hostile PASS prefix",
                    observed=(
                        f"{observed}; expected PASS {expected_pass}/20; FAIL {expected_fail}/20; "
                        f"unsupported-case {expected_unsupported}/20"
                    ),
                    remediation=(
                        "Update current-state aggregate rows in "
                        "prd/architecture/m111-final-architecture-baseline.md after each HC PASS"
                    ),
                )
            )
    else:
        findings.append(
            GovernorFinding(
                check_id="hostile-baseline-present",
                status="fail",
                severity="error",
                message="architecture baseline is missing",
                observed=str(baseline_path),
                remediation="Restore prd/architecture/m111-final-architecture-baseline.md",
            )
        )

    return findings


def check_gsd_residual_debt(root: Path) -> list[GovernorFinding]:
    """Detect residual incomplete GSD milestones that are true debt.

    One open milestone is allowed when it is exactly the next sequence after the
    latest completed milestone (the currently planned/active wave). Residual debt
    is: multiple open milestones, an open milestone at or behind last completed,
    or a gap ahead of last_completed+1.
    """

    findings: list[GovernorFinding] = []
    state_path = root / ".gsd" / "STATE.md"
    if not state_path.is_file():
        return [
            GovernorFinding(
                check_id="gsd-state-present",
                status="fail",
                severity="error",
                message="GSD STATE.md is missing",
                observed=str(state_path),
                remediation="Restore .gsd/STATE.md",
            )
        ]

    state_text = state_path.read_text(encoding="utf-8")
    rows = _registry_milestones(state_text)
    incomplete = [(seq, title) for seq, marker, title in rows if marker != "✅"]
    completed_seqs = [seq for seq, marker, _ in rows if marker == "✅"]
    latest_completed = max(completed_seqs) if completed_seqs else _last_completed_seq(state_text)
    active = _active_milestone_seq(state_text)

    if not incomplete:
        findings.append(
            GovernorFinding(
                check_id="gsd-no-open-registry-debt",
                status="pass",
                severity="ok",
                message="GSD registry has no open non-complete milestones",
                observed=f"last_completed={latest_completed}; active={active}",
                remediation="none",
            )
        )
    elif (
        len(incomplete) == 1
        and latest_completed is not None
        and incomplete[0][0] == latest_completed + 1
    ):
        findings.append(
            GovernorFinding(
                check_id="gsd-no-open-registry-debt",
                status="pass",
                severity="ok",
                message=("Exactly one open next-wave milestone is allowed after last completed"),
                observed=(
                    f"open={incomplete}; last_completed=M{latest_completed}; active={active}"
                ),
                remediation="none",
            )
        )
    else:
        findings.append(
            GovernorFinding(
                check_id="gsd-no-open-registry-debt",
                status="fail",
                severity="error",
                message="GSD registry has residual open-milestone debt",
                observed=(f"open={incomplete}; last_completed={latest_completed}; active={active}"),
                remediation=(
                    "Close leftover incomplete milestones at or behind the last completed "
                    "wave, or collapse multiple open milestones to a single next-wave "
                    "active milestone before product work continues"
                ),
            )
        )

    phase_line = next(
        (line for line in state_text.splitlines() if line.startswith("**Phase:**")),
        "",
    )
    if latest_completed is not None and active is not None and active <= latest_completed:
        findings.append(
            GovernorFinding(
                check_id="gsd-phase-complete-consistent",
                status="fail",
                severity="error",
                message="Active milestone is not ahead of last completed milestone",
                observed=f"active=M{active}; last_completed=M{latest_completed}; {phase_line}",
                remediation="Close residual slices on the active milestone or advance active pointer",
            )
        )
    elif latest_completed is not None and active is not None and active == latest_completed + 1:
        findings.append(
            GovernorFinding(
                check_id="gsd-phase-complete-consistent",
                status="pass",
                severity="ok",
                message="Active milestone is exactly the next wave after last completed",
                observed=f"active=M{active}; last_completed=M{latest_completed}; {phase_line}",
                remediation="none",
            )
        )
    elif latest_completed is not None and active is None:
        findings.append(
            GovernorFinding(
                check_id="gsd-phase-complete-consistent",
                status="pass",
                severity="ok",
                message="No active milestone; last completed stands alone",
                observed=f"last_completed=M{latest_completed}; {phase_line}",
                remediation="none",
            )
        )
    else:
        findings.append(
            GovernorFinding(
                check_id="gsd-phase-complete-consistent",
                status="pass",
                severity="ok",
                message="GSD active/last-completed relationship is coherent",
                observed=f"active={active}; last_completed={latest_completed}; {phase_line}",
                remediation="none",
            )
        )

    return findings


def run_governor(root: Path | None = None) -> GovernorReport:
    """Run all governor checks and return a machine-readable report."""

    resolved = (root or Path.cwd()).resolve()
    findings = (
        check_roadmap_freshness(resolved)
        + check_hostile_proof_chain(resolved)
        + check_gsd_residual_debt(resolved)
    )
    error_count = sum(1 for item in findings if item.status == "fail" and item.severity == "error")
    warn_count = sum(1 for item in findings if item.status == "fail" and item.severity == "warn")
    pass_count = sum(1 for item in findings if item.status == "pass")
    status: Literal["ok", "failure"] = "ok" if error_count == 0 else "failure"
    return GovernorReport(
        schema_version=GOVERNOR_SCHEMA_VERSION,
        status=status,
        root=str(resolved),
        findings=tuple(findings),
        error_count=error_count,
        warn_count=warn_count,
        pass_count=pass_count,
    )

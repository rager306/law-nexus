"""Trajectory governor for repository control-plane checks.

Read-only anti-drift checks that catch the debt patterns observed after
hostile-case milestones: GSD complete while roadmap lags, missing completed
ranges, and hostile-proof aggregate mismatch.

This module is repository metadata policy only. It does not implement product
or legal-domain behavior (ADR-0007).
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
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
_FORWARD_MILESTONE_RE = re.compile(r"^M(?P<seq>\d+):\s+.+$", re.MULTILINE)
_EXPECTED_FORWARD_MILESTONES = tuple(range(131, 141))
_BASELINE_AGG_RE = re.compile(
    r"PASS\s+(\d+)/20;\s*FAIL\s+(\d+)/20;\s*`?unsupported-case`?\s+(\d+)/20",
    re.IGNORECASE,
)
_DIRECTION_BLOCK_RE = re.compile(
    r"^## Active Direction Contract\s*$.*?^```text\s*$\n(?P<body>.*?)^```\s*$",
    re.MULTILINE | re.DOTALL,
)
_DIRECTION_ROW_RE = re.compile(r"^(?P<key>[a-z_]+)=(?P<value>[a-z0-9-]+)$")
_DIRECTION_PATHS = (
    "prd/ARCHITECTURE.md",
    "prd/project-state/roadmap.md",
)
_LEGACY_ACTIVE_REQUIREMENT_IDS = {
    "R037",
    "R041",
    "R042",
    "R043",
    "R046",
    "R047",
    "R048",
    "R055",
    "R056",
    "R057",
}
_REQUIREMENT_HEADING_RE = re.compile(r"^### (?P<id>R\d+) (?:—|–|-) (?P<title>.+)$", re.MULTILINE)
_REQUIREMENT_LIKE_HEADING_RE = re.compile(r"^### R\d+\b.*$", re.MULTILINE)
_REQUIREMENT_DESCRIPTION_RE = re.compile(r"^- Description:\s*(?P<value>.+)$", re.MULTILINE)
_ACTIVE_REQUIREMENT_POLICY = {
    "R065": {
        "required": ("prior art", "bounded comparison"),
        "forbidden": ("behavioral reference", "source of truth", "normative specification"),
    }
}
_EXPECTED_DIRECTION = {
    "runtime": "rust-only",
    "python": "repository-control-only",
    "graph_vector": "ruvector",
    "infrastructure_lifecycle": "proposed",
    "embedding": "tei-user-bge-m3-1024d",
    "acp_git_lex": "archive-only",
    "falkordb": "historical-only",
}


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


def _last_completed_id(state_text: str, expected_seq: int) -> str:
    for line in state_text.splitlines():
        match = _LAST_COMPLETED_RE.match(line.strip())
        if match and int(match.group("seq")) == expected_seq:
            suffix = match.group("rand")
            return f"M{expected_seq}" + (f"-{suffix}" if suffix else "")
    return f"M{expected_seq}"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_direction_contract(
    text: str,
) -> tuple[dict[str, str], list[str], list[str], int]:
    matches = list(_DIRECTION_BLOCK_RE.finditer(text))
    if not matches:
        return {}, [], [], 0

    values: dict[str, str] = {}
    duplicates: list[str] = []
    unknown: list[str] = []
    for raw_line in matches[0].group("body").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        row = _DIRECTION_ROW_RE.fullmatch(line)
        if row is None:
            unknown.append(line)
            continue
        key = row.group("key")
        if key not in _EXPECTED_DIRECTION:
            unknown.append(key)
        elif key in values:
            duplicates.append(key)
        else:
            values[key] = row.group("value")
    return values, duplicates, unknown, len(matches)


def check_architecture_direction(root: Path) -> list[GovernorFinding]:
    """Require one coherent active-direction contract across living surfaces."""

    errors: list[str] = []
    for rel_path in _DIRECTION_PATHS:
        path = root / rel_path
        if not path.is_file():
            errors.append(f"{rel_path}: missing-surface")
            continue
        values, duplicates, unknown, block_count = _parse_direction_contract(
            path.read_text(encoding="utf-8")
        )
        missing = sorted(set(_EXPECTED_DIRECTION) - set(values))
        mismatches = sorted(
            key
            for key, expected in _EXPECTED_DIRECTION.items()
            if key in values and values[key] != expected
        )
        details: list[str] = []
        if block_count == 0:
            details.append("missing-contract")
        elif block_count != 1:
            details.append(f"contract_blocks={block_count}")
        else:
            if missing:
                details.append(f"missing={','.join(missing)}")
            if duplicates:
                details.append(f"duplicate={','.join(sorted(set(duplicates)))}")
            if unknown:
                details.append(f"unknown={','.join(sorted(set(unknown)))}")
            if mismatches:
                details.append(f"mismatch={','.join(mismatches)}")
        if details:
            errors.append(f"{rel_path}: {'; '.join(details)}")

    if errors:
        return [
            GovernorFinding(
                check_id="architecture-direction-contract",
                status="fail",
                severity="error",
                message="Living architecture direction is missing, stale, or inconsistent",
                observed=" | ".join(errors),
                remediation=(
                    "Update _EXPECTED_DIRECTION, tests ACTIVE_DIRECTION, and the tracked "
                    "Active Direction Contract blocks in prd/ARCHITECTURE.md and "
                    "prd/project-state/roadmap.md together; do not rewrite historical "
                    "evidence or raise lifecycle proof ceilings"
                ),
            )
        ]
    return [
        GovernorFinding(
            check_id="architecture-direction-contract",
            status="pass",
            severity="ok",
            message="Living architecture direction is coherent across all required surfaces",
            observed="; ".join(f"{key}={value}" for key, value in _EXPECTED_DIRECTION.items()),
            remediation="none",
        )
    ]


def check_active_requirement_contradictions(root: Path) -> list[GovernorFinding]:
    """Inspect the local GSD requirements projection without making CI depend on it."""

    path = root / ".gsd" / "REQUIREMENTS.md"
    if not path.is_file():
        return [
            GovernorFinding(
                check_id="active-requirement-contradictions",
                status="pass",
                severity="ok",
                message="Local GSD requirements projection is unavailable",
                observed="unavailable-local-projection; portable tracked checks still apply",
                remediation="none",
            )
        ]

    text = path.read_text(encoding="utf-8")
    active_match = re.search(
        r"^## Active\s*$\n(?P<body>.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL
    )
    if active_match is None:
        return [
            GovernorFinding(
                check_id="active-requirement-contradictions",
                status="fail",
                severity="error",
                message="Local GSD requirements projection is malformed",
                observed="missing-active-section",
                remediation="Regenerate the GSD requirements projection from the requirements DB",
            )
        ]
    active = active_match.group("body")
    if not active.strip():
        return [
            GovernorFinding(
                check_id="active-requirement-contradictions",
                status="fail",
                severity="error",
                message="Local GSD requirements projection has no active requirements",
                observed="empty-active-section",
                remediation="Regenerate and inspect the GSD requirements projection",
            )
        ]

    headings = list(_REQUIREMENT_HEADING_RE.finditer(active))
    requirement_like_headings = list(_REQUIREMENT_LIKE_HEADING_RE.finditer(active))
    malformed_headings = [
        match.group(0)
        for match in requirement_like_headings
        if _REQUIREMENT_HEADING_RE.fullmatch(match.group(0)) is None
    ]
    if malformed_headings:
        return [
            GovernorFinding(
                check_id="active-requirement-contradictions",
                status="fail",
                severity="error",
                message="Local GSD requirements projection has malformed requirement headings",
                observed=f"malformed-headings={malformed_headings}",
                remediation="Regenerate the GSD requirements projection from the requirements DB",
            )
        ]

    conflicts: list[str] = []
    for index, heading in enumerate(headings):
        requirement_id = heading.group("id")
        block_end = headings[index + 1].start() if index + 1 < len(headings) else len(active)
        block = active[heading.start() : block_end]
        if requirement_id in _LEGACY_ACTIVE_REQUIREMENT_IDS:
            conflicts.append(requirement_id)
        policy = _ACTIVE_REQUIREMENT_POLICY.get(requirement_id)
        if policy is not None:
            description_match = _REQUIREMENT_DESCRIPTION_RE.search(block)
            description = description_match.group("value").lower() if description_match else ""
            required = policy["required"]
            forbidden = policy["forbidden"]
            if any(term not in description for term in required) or any(
                term in description for term in forbidden
            ):
                conflicts.append(requirement_id)

    unique_conflicts = sorted(set(conflicts))
    if unique_conflicts:
        return [
            GovernorFinding(
                check_id="active-requirement-contradictions",
                status="fail",
                severity="error",
                message="Active requirement contract contradicts the current architecture direction",
                observed=f"active_conflicts={unique_conflicts}",
                remediation=(
                    "Use GSD requirement tools to move legacy ACP/git-lex/FalkorDB "
                    "obligations out of active scope and keep R065 as prior-art comparison "
                    "plus controlled cutover, not a normative Python specification"
                ),
            )
        ]
    return [
        GovernorFinding(
            check_id="active-requirement-contradictions",
            status="pass",
            severity="ok",
            message="Active requirement contract matches the current architecture direction",
            observed="active_conflicts=[]",
            remediation="none",
        )
    ]


def check_forward_roadmap_sequence(root: Path) -> list[GovernorFinding]:
    """Require the non-conflicting post-M130 product milestone sequence."""

    path = root / "prd" / "migration" / "forward-roadmap.md"
    if not path.is_file():
        return [
            GovernorFinding(
                check_id="forward-roadmap-sequence",
                status="fail",
                severity="error",
                message="Forward product roadmap is missing",
                observed="missing-surface=prd/migration/forward-roadmap.md",
                remediation="Restore the tracked M131-M140 forward roadmap",
            )
        ]
    sequences = [
        int(match.group("seq"))
        for match in _FORWARD_MILESTONE_RE.finditer(path.read_text(encoding="utf-8"))
    ]
    expected = set(_EXPECTED_FORWARD_MILESTONES)
    counts = {seq: sequences.count(seq) for seq in set(sequences)}
    missing = sorted(expected - set(sequences))
    duplicate = sorted(seq for seq, count in counts.items() if count > 1)
    unexpected = sorted(set(sequences) - expected)
    details: list[str] = []
    if missing:
        details.append(f"missing={','.join(f'M{seq}' for seq in missing)}")
    if duplicate:
        details.append(f"duplicate={','.join(f'M{seq}' for seq in duplicate)}")
    if unexpected:
        details.append(f"unexpected={','.join(f'M{seq}' for seq in unexpected)}")
    if details:
        return [
            GovernorFinding(
                check_id="forward-roadmap-sequence",
                status="fail",
                severity="error",
                message="Forward product roadmap numbering conflicts with M130 debt milestone",
                observed="; ".join(details),
                remediation="Keep M130 for repository-control debt and product milestones exactly M131-M140",
            )
        ]
    return [
        GovernorFinding(
            check_id="forward-roadmap-sequence",
            status="pass",
            severity="ok",
            message="Forward product roadmap has a unique post-M130 sequence",
            observed="product_sequence=M131-M140",
            remediation="none",
        )
    ]


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

    latest_completed_id = _last_completed_id(state_text, latest_completed)
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
                    "Set prd/project-state/data/roadmap.json "
                    f"current_milestone.id={latest_completed_id} and status=complete "
                    "(or use the active milestone with status=active); update roadmap.md current prose"
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
                    "Set prd/project-state/data/roadmap.json "
                    f"completed_milestone_groups[].range=M{latest_completed}-M{latest_completed} "
                    "(or extend an existing completed range)"
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


def _load_port_contract_coverage_module(root: Path):
    # Prefer the checked-out repository script under the target root; fall back to
    # the harness package's repository so fixture roots can reuse inventory code.
    candidates = (
        root / "scripts" / "verify-port-contract-coverage.py",
        Path(__file__).resolve().parents[2] / "scripts" / "verify-port-contract-coverage.py",
    )
    script = next((path for path in candidates if path.is_file()), None)
    if script is None:
        raise FileNotFoundError(
            "missing coverage inventory script under target root or harness repository"
        )
    module_name = f"verify_port_contract_coverage_{abs(hash(str(script)))}"
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load coverage inventory script: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def check_port_contract_coverage(root: Path) -> list[GovernorFinding]:
    """Inventory InMemory adapters vs ln-testkit shared port-contract coverage.

    Debt is non-blocking (fail + warn). Inventory script/load failures are
    fail-closed (fail + error). Full coverage pass is bounded port-suite
    evidence only and must not be read as TEI/RuVector validation.
    """
    check_id = "port-contract-coverage"
    remediation = (
        "Expand ln-testkit shared port contracts for uncovered InMemory adapters "
        "(ADR-0015) or inspect `uv run python scripts/verify-port-contract-coverage.py`. "
        "Do not claim real TEI/RuVector validation or product readiness from inventory alone."
    )
    try:
        module = _load_port_contract_coverage_module(root)
        crates_root = root / "crates"
        discovered = module.discover_inmemory_adapters(crates_root, repo_root=root)
        report = module.build_report(discovered)
    except Exception as error:  # noqa: BLE001 - fail-closed process surface
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="error",
                message="port-contract coverage inventory failed",
                observed=str(error),
                remediation=remediation,
            )
        ]

    covered = int(report.get("covered_count") or 0)
    uncovered = int(report.get("uncovered_count") or 0)
    discovered_count = int(report.get("discovered_count") or 0)
    status = str(report.get("status") or "")
    identity_model = str(report.get("identity_model") or "unknown")
    missing_declared = report.get("missing_declared_covered") or []

    if uncovered > 0 or status == "debt" or missing_declared:
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="InMemory port-contract coverage debt remains",
                observed=(
                    f"covered={covered}, uncovered={uncovered}, discovered={discovered_count}, "
                    f"identity_model={identity_model}, missing_declared={len(missing_declared)} "
                    f"(lifecycle [bounded]; not real TEI/RuVector validation)."
                ),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="InMemory adapters are covered by ln-testkit shared port contracts",
            observed=(
                f"covered={covered}, uncovered={uncovered}, discovered={discovered_count}, "
                f"identity_model={identity_model} "
                f"(lifecycle [bounded]; not real TEI/RuVector validation or product readiness)."
            ),
            remediation="none",
        )
    ]


def _load_hostile_negative_suite_module(root: Path):
    candidates = (
        root / "scripts" / "verify-hostile-negative-suite-coverage.py",
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "verify-hostile-negative-suite-coverage.py",
    )
    script = next((path for path in candidates if path.is_file()), None)
    if script is None:
        raise FileNotFoundError(
            "missing hostile-negative inventory script under target root or harness repository"
        )
    module_name = f"verify_hostile_negative_suite_coverage_{abs(hash(str(script)))}"
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load hostile-negative inventory script: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def check_hostile_negative_suite_coverage(root: Path) -> list[GovernorFinding]:
    """Inventory hostile adapters vs shared ln-testkit negative-suite mentions.

    Debt is non-blocking (fail + warn). Inventory script/load failures are
    fail-closed (fail + error). Classification is mention-based and does not
    prove negative-suite semantic completeness or real infrastructure readiness.
    """
    check_id = "hostile-negative-suite-coverage"
    remediation = (
        "Add shared negative suites in crates/ln-testkit for hostile adapters "
        "missing mentions, or inspect "
        "`uv run python scripts/verify-hostile-negative-suite-coverage.py`. "
        "Crate-local HC hostile tests are not shared suites. Do not claim "
        "product readiness from inventory alone."
    )
    try:
        module = _load_hostile_negative_suite_module(root)
        crates_root = root / "crates"
        discovered = module.discover_hostile_adapters(crates_root, repo_root=root)
        testkit_text = module.load_testkit_text(crates_root / "ln-testkit")
        report = module.build_report(discovered, testkit_text=testkit_text)
    except Exception as error:  # noqa: BLE001 - fail-closed process surface
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="error",
                message="hostile-negative suite inventory failed",
                observed=str(error),
                remediation=remediation,
            )
        ]

    discovered_count = int(report.get("discovered_count") or 0)
    with_shared = int(report.get("with_shared_negative_count") or 0)
    missing = int(report.get("missing_shared_negative_count") or 0)
    status = str(report.get("status") or "")
    missing_ids = [
        item.get("identity", "?") for item in (report.get("missing_shared_negative") or [])
    ]
    missing_preview = ",".join(missing_ids[:6])
    if len(missing_ids) > 6:
        missing_preview += f",+{len(missing_ids) - 6}"

    if missing > 0 or status == "debt":
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="hostile adapters lack shared negative-suite mentions",
                observed=(
                    f"discovered={discovered_count}, with_shared_negative={with_shared}, "
                    f"missing_shared_negative={missing}, missing=[{missing_preview}] "
                    f"(lifecycle [bounded]; mention-based; not product readiness)."
                ),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="hostile adapters have shared negative-suite mentions",
            observed=(
                f"discovered={discovered_count}, with_shared_negative={with_shared}, "
                f"missing_shared_negative={missing} "
                f"(lifecycle [bounded]; mention-based; not product readiness)."
            ),
            remediation="none",
        )
    ]


def _load_multi_adapter_port_coverage_module(root: Path):
    candidates = (
        root / "scripts" / "verify-multi-adapter-port-coverage.py",
        Path(__file__).resolve().parents[2] / "scripts" / "verify-multi-adapter-port-coverage.py",
    )
    script = next((path for path in candidates if path.is_file()), None)
    if script is None:
        raise FileNotFoundError(
            "missing multi-adapter port inventory script under target root or harness repository"
        )
    module_name = f"verify_multi_adapter_port_coverage_{abs(hash(str(script)))}"
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load multi-adapter port inventory script: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def check_multi_adapter_port_coverage(root: Path) -> list[GovernorFinding]:
    """Inventory multi-adapter real ports vs shared ln-testkit suite mentions.

    Debt is non-blocking (fail + warn). Inventory script/load failures are
    fail-closed (fail + error). Classification is mention-based and does not
    prove suite semantic completeness or live TEI/RuVector readiness.
    """
    check_id = "multi-adapter-port-coverage"
    remediation = (
        "Add shared suites in crates/ln-testkit for real adapters on multi-adapter "
        "ports missing mentions, or inspect "
        "`uv run python scripts/verify-multi-adapter-port-coverage.py`. "
        "Fake/hostile fixtures are excluded from residual debt. Do not claim "
        "product readiness from inventory alone."
    )
    try:
        module = _load_multi_adapter_port_coverage_module(root)
        crates_root = root / "crates"
        ports = module.discover_port_impls(crates_root, repo_root=root)
        testkit_text = module.load_testkit_text(crates_root / "ln-testkit")
        report = module.build_report(ports, testkit_text=testkit_text)
    except Exception as error:  # noqa: BLE001 - fail-closed process surface
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="error",
                message="multi-adapter port inventory failed",
                observed=str(error),
                remediation=remediation,
            )
        ]

    multi_ports = int(report.get("multi_adapter_port_count") or 0)
    real_count = int(report.get("real_adapter_count") or 0)
    with_shared = int(report.get("with_shared_suite_count") or 0)
    missing = int(report.get("missing_shared_suite_count") or 0)
    status = str(report.get("status") or "")
    missing_ids = [item.get("identity", "?") for item in (report.get("missing_shared_suite") or [])]
    missing_preview = ",".join(missing_ids[:6])
    if len(missing_ids) > 6:
        missing_preview += f",+{len(missing_ids) - 6}"

    if missing > 0 or status == "debt":
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="real multi-adapter ports lack shared suite mentions",
                observed=(
                    f"multi_adapter_ports={multi_ports}, real_adapters={real_count}, "
                    f"with_shared_suite={with_shared}, missing_shared_suite={missing}, "
                    f"missing=[{missing_preview}] "
                    f"(lifecycle [bounded]; mention-based; not product readiness)."
                ),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="real multi-adapter ports have shared suite mentions",
            observed=(
                f"multi_adapter_ports={multi_ports}, real_adapters={real_count}, "
                f"with_shared_suite={with_shared}, missing_shared_suite={missing} "
                f"(lifecycle [bounded]; mention-based; not product readiness)."
            ),
            remediation="none",
        )
    ]


def run_governor(root: Path | None = None) -> GovernorReport:
    """Run all governor checks and return a machine-readable report."""

    resolved = (root or Path.cwd()).resolve()
    findings = (
        check_architecture_direction(resolved)
        + check_active_requirement_contradictions(resolved)
        + check_forward_roadmap_sequence(resolved)
        + check_roadmap_freshness(resolved)
        + check_hostile_proof_chain(resolved)
        + check_gsd_residual_debt(resolved)
        + check_port_contract_coverage(resolved)
        + check_hostile_negative_suite_coverage(resolved)
        + check_multi_adapter_port_coverage(resolved)
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

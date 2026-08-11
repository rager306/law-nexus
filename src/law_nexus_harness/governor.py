"""Trajectory governor for repository control-plane checks.

Read-only anti-drift checks that catch the debt patterns observed after
hostile-case milestones: GSD complete while roadmap lags, missing completed
ranges, and hostile-proof aggregate mismatch.

This module is repository metadata policy only. It does not implement product
or legal-domain behavior (ADR-0007).
"""

from __future__ import annotations

import fnmatch
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Literal

from law_nexus_harness.adr_matrix import (
    DEFAULT_ADR_MATRIX_PATH,
    check_adr_matrix_output,
)

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
class GovernorEvidence:
    path: str
    line: int | None = None


@dataclass(frozen=True)
class GovernorFinding:
    check_id: str
    status: CheckStatus
    severity: Severity
    message: str
    observed: str
    remediation: str
    rule_id: str = ""
    expected: str = ""
    evidence: tuple[GovernorEvidence, ...] = ()


CheckRunner = Callable[[Path], list[GovernorFinding]]
CheckKind = Literal["deterministic", "heuristic"]


@dataclass(frozen=True)
class CheckSpec:
    check_id: str
    group: str
    kind: CheckKind
    runner: CheckRunner
    purpose: str
    authority_inputs: tuple[str, ...]
    default_severity: Severity
    non_claim: str

    def to_explanation(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "group": self.group,
            "kind": self.kind,
            "purpose": self.purpose,
            "authority_inputs": list(self.authority_inputs),
            "default_severity": self.default_severity,
            "non_claim": self.non_claim,
        }


class GovernorSelectionError(ValueError):
    def __init__(self, error: str, value: str) -> None:
        super().__init__(f"{error}: {value}")
        self.error = error
        self.value = value


@dataclass(frozen=True)
class GovernorReport:
    schema_version: str
    status: Literal["ok", "failure"]
    root: str
    findings: tuple[GovernorFinding, ...]
    error_count: int
    warn_count: int
    pass_count: int
    tool_error_count: int = 0

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


def _load_live_adapter_readiness_module(root: Path):
    candidates = (
        root / "scripts" / "verify-live-adapter-readiness.py",
        Path(__file__).resolve().parents[2] / "scripts" / "verify-live-adapter-readiness.py",
    )
    script = next((path for path in candidates if path.is_file()), None)
    if script is None:
        raise FileNotFoundError(
            "missing live-adapter readiness inventory script under target root or harness repository"
        )
    module_name = f"verify_live_adapter_readiness_{abs(hash(str(script)))}"
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load live-adapter readiness inventory script: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def check_live_adapter_readiness(root: Path) -> list[GovernorFinding]:
    """Inventory TEI/RuVector live-adapter readiness from repository evidence.

    Overclaim debt is non-blocking (fail + warn). Inventory script/load failures
    are fail-closed (fail + error). Stub/proposed classifications are process
    honesty only and do not validate live TEI/RuVector adapters.
    """
    check_id = "live-adapter-readiness"
    remediation = (
        "Inspect `uv run python scripts/verify-live-adapter-readiness.py`. "
        "Remove overclaim markers or restore TEI stub-transport / RuVector "
        "proposed evidence ceilings. Do not claim live TEI/RuVector validation "
        "or product readiness from inventory alone."
    )
    try:
        module = _load_live_adapter_readiness_module(root)
        report = module.build_report(root)
    except Exception as error:  # noqa: BLE001 - fail-closed process surface
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="error",
                message="live-adapter readiness inventory failed",
                observed=str(error),
                remediation=remediation,
            )
        ]

    status = str(report.get("status") or "")
    overclaim_count = int(report.get("overclaim_count") or 0)
    tei = report.get("tei") or {}
    ruvector = report.get("ruvector") or {}
    tei_status = str(tei.get("status") or "unknown")
    ruvector_status = str(ruvector.get("status") or "unknown")

    if overclaim_count > 0 or status == "debt":
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="live-adapter readiness inventory reports overclaims",
                observed=(
                    f"status={status}, tei={tei_status}, ruvector={ruvector_status}, "
                    f"overclaim_count={overclaim_count} "
                    f"(lifecycle [bounded]; repository-evidence only; not live "
                    f"TEI/RuVector validation or product readiness)."
                ),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="live-adapter readiness inventory within evidence ceiling",
            observed=(
                f"status={status}, tei={tei_status}, ruvector={ruvector_status}, "
                f"overclaim_count={overclaim_count} "
                f"(lifecycle [bounded]; repository-evidence only; not live "
                f"TEI/RuVector validation or product readiness)."
            ),
            remediation="none",
        )
    ]


def _extract_pre_commit_hook_ids(root: Path) -> set[str]:
    """Extract local hook IDs from .pre-commit-config.yaml without yaml dependency."""
    config = root / ".pre-commit-config.yaml"
    if not config.is_file():
        return set()
    text = config.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"-\s+id:\s+(\S+)", text))


def _extract_ci_content(root: Path) -> str:
    """Read the CI workflow file content for drift detection."""
    ci = root / ".github" / "workflows" / "repository-quality.yml"
    if not ci.is_file():
        return ""
    return ci.read_text(encoding="utf-8", errors="replace")


def check_ci_quality_gate_drift(root: Path) -> list[GovernorFinding]:
    """Detect drift between pre-commit hooks, CI workflow, and quality-gate inventory.

    Debt is non-blocking (fail + warn). Missing inventory file is fail-closed
    (fail + error). This check enforces that process surfaces stay synchronized
    so CI cannot silently drop inventory scripts or pre-commit hooks.
    """
    check_id = "ci-quality-gate-drift"
    remediation = (
        "Synchronize .pre-commit-config.yaml hook IDs, "
        ".github/workflows/repository-quality.yml process suite/inventory scripts, "
        "and prd/migration/decommission/repository-quality-gate.json. "
        "Do not claim process readiness from a drifted inventory."
    )

    inventory_path = root / "prd" / "migration" / "decommission" / "repository-quality-gate.json"
    try:
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001 - fail-closed process surface
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="error",
                message="quality-gate inventory load failed",
                observed=str(error),
                remediation=remediation,
            )
        ]

    qg_check_ids = {check["id"] for check in payload.get("checks", [])}
    qg_process_suite = set(payload.get("ci_process_suite", []))
    qg_inventory_scripts = set(payload.get("ci_inventory_scripts", []))

    pre_commit_ids = _extract_pre_commit_hook_ids(root)
    ci_text = _extract_ci_content(root)

    drift_details: list[str] = []

    pre_vs_qg_hooks = pre_commit_ids.symmetric_difference(qg_check_ids)
    if pre_vs_qg_hooks:
        drift_details.append(f"pre_commit_vs_qg_checks={sorted(pre_vs_qg_hooks)}")

    suite_missing_from_ci = {t for t in qg_process_suite if t not in ci_text}
    if suite_missing_from_ci:
        drift_details.append(f"process_suite_missing_from_ci={sorted(suite_missing_from_ci)}")

    scripts_missing_from_ci = {t for t in qg_inventory_scripts if t not in ci_text}
    if scripts_missing_from_ci:
        drift_details.append(f"inventory_scripts_missing_from_ci={sorted(scripts_missing_from_ci)}")

    if drift_details:
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="CI/pre-commit/quality-gate inventory drift detected",
                observed=(
                    f"{'; '.join(drift_details)} "
                    f"(lifecycle [bounded]; process anti-drift; not product readiness)."
                ),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="pre-commit hooks, CI process suite, and inventory scripts synchronized",
            observed=(
                f"hooks={len(pre_commit_ids)}, process_suite={len(qg_process_suite)}, "
                f"inventory_scripts={len(qg_inventory_scripts)} "
                f"(lifecycle [bounded]; process anti-drift; not product readiness)."
            ),
            remediation="none",
        )
    ]


def check_verify_test_coverage_drift(root: Path) -> list[GovernorFinding]:
    """Detect tests for active verify scripts that are missing from CI process suite.

    Scans test_verify_*.py for references to scripts in active CI/pre-commit/quality-gate
    inventory surfaces. Any such test must be in ci_process_suite. Debt is non-blocking
    (fail + warn). Quality-gate inventory load failure is fail-closed (error).
    """
    check_id = "verify-test-coverage-drift"
    remediation = (
        "Add the missing test to the quality-gate ci_process_suite and CI workflow, "
        "or remove the script from active CI/pre-commit surfaces. "
        "Do not claim process readiness from a drifted test suite."
    )

    inventory_path = root / "prd" / "migration" / "decommission" / "repository-quality-gate.json"
    try:
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001 - fail-closed process surface
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="error",
                message="quality-gate inventory load failed",
                observed=str(error),
                remediation=remediation,
            )
        ]

    ci_suite = set(payload.get("ci_process_suite", []))
    ci_inventory_scripts = set(payload.get("ci_inventory_scripts", []))
    pre_commit_ids_text = _extract_pre_commit_hook_ids_with_entries(root)
    ci_text = _extract_ci_content(root)

    # Build set of active verify script names from pre-commit entries and CI inventory
    active_scripts: set[str] = set()
    for script in ci_inventory_scripts:
        active_scripts.add(Path(script).name)
    for script in re.findall(r"scripts/(verify-[a-z0-9_-]+\.py)", ci_text):
        active_scripts.add(script)
    for script in re.findall(r"verify-[a-z0-9_-]+\.py", pre_commit_ids_text):
        active_scripts.add(script)

    # Scan test_verify_*.py for references to active scripts
    tests_dir = root / "tests"
    missing: list[str] = []
    if tests_dir.is_dir():
        for test_path in sorted(tests_dir.glob("test_verify_*.py")):
            rel = f"tests/{test_path.name}"
            if rel in ci_suite:
                continue
            text = test_path.read_text(encoding="utf-8", errors="replace")
            referenced = {s for s in active_scripts if s in text}
            if referenced:
                missing.append(f"{rel}->{sorted(referenced)[0]}")

    if missing:
        preview = ",".join(missing[:8])
        if len(missing) > 8:
            preview += f",+{len(missing) - 8}"
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="verify tests for active scripts missing from CI process suite",
                observed=(
                    f"missing_count={len(missing)}, missing=[{preview}] "
                    f"(lifecycle [bounded]; process anti-drift; not product readiness)."
                ),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="verify tests for active scripts are in CI process suite",
            observed=(
                f"active_scripts={len(active_scripts)}, ci_suite={len(ci_suite)} "
                f"(lifecycle [bounded]; process anti-drift; not product readiness)."
            ),
            remediation="none",
        )
    ]


def check_semantic_stub_in_product_code(root: Path) -> list[GovernorFinding]:
    """Detect semantic stub/fake markers in active product Rust source.

    Scans crates/*/src/**/*.rs (excluding */tests/* and the ln-testkit crate, which
    are test infrastructure) for stub/fake/dummy/placeholder/hardcoded comment
    markers and todo!()/unimplemented!()/panic!('not implemented') macros. This is
    the advisory anti-drift probe (MEM676) for the class of fabricated-semantics
    bug that passed every green process gate in M161. Debt is non-blocking
    (fail + warn). Lifecycle [bounded]; process anti-drift, not product readiness.
    """
    check_id = "semantic-stub-in-product-code"
    remediation = (
        "Replace the flagged semantic stub/fake with functional, semantically verified "
        "code, or reword the comment if it only documents historical behavior. "
        "Do not ship fabricated product semantics under green process gates."
    )

    pattern = re.compile(
        r"(?i)"
        r"//\s*(stub|fake|dummy|placeholder|hardcoded)"  # comment markers
        r"|todo!\s*\("  # rust unimplemented markers
        r"|unimplemented!\s*\("
        r"|panic!\s*\(\s*\"(not implemented|unimplemented|todo|stub)"
    )

    matches: list[str] = []
    crates_dir = root / "crates"
    if crates_dir.is_dir():
        for src_file in crates_dir.glob("*/src/**/*.rs"):
            rel = str(src_file.relative_to(root)).replace("\\", "/")
            # Exclude test files and the shared ln-testkit crate (test infra).
            if "/tests/" in rel or rel.startswith("crates/ln-testkit/"):
                continue
            try:
                text = src_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line):
                    matches.append(f"{rel}:{lineno}")

    if matches:
        preview = ",".join(matches[:12])
        if len(matches) > 12:
            preview += f",+{len(matches) - 12}"
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="semantic stub/fake markers found in active product Rust source",
                observed=(
                    f"stub_count={len(matches)}, matches=[{preview}] "
                    f"(lifecycle [bounded]; process anti-drift; not product readiness)."
                ),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="no semantic stub/fake markers in active product Rust source",
            observed=(
                "stub_count=0 (lifecycle [bounded]; process anti-drift; not product readiness)."
            ),
            remediation="none",
        )
    ]


def check_historical_test_debt_visibility(root: Path) -> list[GovernorFinding]:
    """Inventory non-CI tests referencing decommissioned eras.

    Surfaces tests/test_*.py that reference decommissioned-era technologies
    (ACP/git-lex, the legacy graph store, PyO3, MiniMax) as an advisory inventory
    so the silently-carried historical test debt is triage-visible (AGENTS.md
    anti-silently-keep). Non-destructive: nothing is deleted or moved. Files whose
    name marks them as active decommission-policy controls
    (decommission/no_acp/no_forbidden/archive/verify_) are EXCLUDED so active
    guards are not false-flagged. Lifecycle [bounded]; process visibility, not
    product readiness.
    """
    check_id = "historical-test-debt-visibility"
    remediation = (
        "Triage the flagged historical tests: active regression coverage -> add to "
        "CI_PROCESS_SUITE; pure historical/archival evidence -> document as such; "
        "hard-dependency on archived product code -> retire/archive. Do not silently "
        "keep residual tests that hard-depend on archived product code."
    )

    era_keywords = re.compile(r"(?i)falkordb|git[\-_]lex|\bacp\b|minimax|pyo3")
    # File-name markers that indicate an ACTIVE decommission-policy control,
    # not residual historical evidence.
    active_control = re.compile(r"decommission|no_acp|no_forbidden|archive|verify_")

    matches: list[str] = []
    tests_dir = root / "tests"
    if tests_dir.is_dir():
        for test_file in tests_dir.glob("test_*.py"):
            name = test_file.name
            if active_control.search(name):
                continue
            try:
                text = test_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if era_keywords.search(text):
                matches.append(name)

    if matches:
        preview = ",".join(sorted(matches)[:12])
        if len(matches) > 12:
            preview += f",+{len(matches) - 12}"
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="non-CI tests reference decommissioned eras",
                observed=(
                    f"historical_test_count={len(matches)}, files=[{preview}] "
                    f"(lifecycle [bounded]; process visibility, not product readiness; "
                    f"advisory, not a hard gate)."
                ),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="no non-CI tests reference decommissioned eras",
            observed=(
                "historical_test_count=0 "
                "(lifecycle [bounded]; process visibility, not product readiness)."
            ),
            remediation="none",
        )
    ]


# Historical vaults that must not be active product truth / index surfaces.
_HISTORICAL_ACTIVE_ALIASES: tuple[str, ...] = (
    "prd/architecture/acp",
    "scripts/s02-cold-path-install-proof.sh",
    "scripts/s02-first-proof.sh",
    "scripts/s02-self-check.sh",
    "scripts/s03-install-rehearsal-workflow-proof.sh",
    "scripts/s03-validate-reject-proof.sh",
    "tests/test_consultant_parser_proof.py",
    "tests/test_hierarchy_metadata_completeness.py",
    "tests/test_local_retrieval_runtime_check_cli.py",
    "tests/test_source_structuring_protocol.py",
)

_HISTORICAL_VAULT_PATHS: tuple[str, ...] = (
    ".lex",
    "python_archive",
    "Old_project",
    "prd/archive/acp-git-lex",
    "prd/archive/pre-rust-prd",
    "prd/archive/milestone-proofs-era",
    "prd/archive/research-era",
    "prd/archive/project-state-era",
    "prd/archive/architecture-era",
    "prd/archive/parser-dumps-era",
    "prd/archive/retrieval-era",
    "prd/archive/migration-era",
    "archive",
    "probes",
    ".commandcode",
)

# Ontology ADRs that must be cited in REQUIREMENTS + PROJECT after M165 weave.
_ONTOLOGY_DOC_MATRIX_ADRS: tuple[str, ...] = tuple(f"{n:04d}" for n in range(16, 23))
_ONTOLOGY_DOC_MATRIX_SURFACES: tuple[str, ...] = (
    ".gsd/REQUIREMENTS.md",
    ".gsd/PROJECT.md",
)

# ADR IDs that must appear in prd/ARCHITECTURE.md with a matching lifecycle tag
# on the same line or an adjacent line (truth-oracle sync, D098).
_ADR_TRUTH_ORACLE_EXPECTATIONS: dict[str, str] = {
    "0004": "bounded",
    "0005": "bounded",
    "0007": "validated",
    "0008": "bounded",
    "0009": "bounded",
    "0010": "bounded",
    "0011": "bounded",
    "0012": "bounded",
    "0013": "bounded",
    "0014": "proposed",
    "0015": "bounded",
    "0016": "proposed",
    "0017": "proposed",
    "0018": "proposed",
    "0019": "proposed",
    "0020": "proposed",
    "0021": "proposed",
    "0022": "proposed",
    "0023": "proposed",
}

# Surfaces that must cite every present ADR file (cross-surface matrix).
_ADR_CROSS_SURFACE_PATHS: tuple[str, ...] = (
    "prd/ARCHITECTURE.md",
    "README.md",
    "doc/adr/README.md",
)

# Required MADR section headings for every ADR file (hygiene).
_ADR_REQUIRED_SECTIONS: tuple[str, ...] = (
    "Status",
    "Context",
    "Decision",
    "Consequences",
    "Non-claims",
)

_LIFECYCLE_TAG_RE = re.compile(r"\[(proposed|bounded|smoke|validated|deferred)\]", re.IGNORECASE)
_ADR_ID_RE = re.compile(r"\bADR-(?P<id>\d{4})\b", re.IGNORECASE)


def _gitignore_covers(gitignore_text: str, path: str) -> bool:
    """Return True if a simple gitignore entry covers ``path``.

    Accepts exact path, trailing-slash directory form, or a leading-slash form.
    Does not implement full gitignore semantics — sufficient for vault policy.
    """
    candidates = {
        path,
        f"{path}/",
        f"/{path}",
        f"/{path}/",
    }
    for raw in gitignore_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line in candidates:
            return True
    return False


def _git_tracked_paths(root: Path, path: str) -> list[str]:
    """List git-tracked files under ``path`` (empty if not a git worktree)."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", path],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line.strip()]


def _active_symlinks_into_vaults(root: Path) -> list[str]:
    """Find active-tree symlinks whose resolved target is inside a historical vault."""

    root = root.resolve()
    vaults = tuple((root / path).resolve() for path in _HISTORICAL_VAULT_PATHS)
    excluded_roots = {".git", ".gitnexus", ".venv", "target"}
    hits: list[str] = []

    def is_vault_path(path: Path) -> bool:
        return any(path == vault or vault in path.parents for vault in vaults)

    def inspect(path: Path) -> None:
        if not path.is_symlink():
            return
        target = path.resolve(strict=False)
        if not is_vault_path(target):
            return
        rel = path.relative_to(root).as_posix()
        try:
            target_label = target.relative_to(root).as_posix()
        except ValueError:
            target_label = "external-vault-target"
        hits.append(f"{rel}->{target_label}")

    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        retained_dirs: list[str] = []
        for name in dirnames:
            candidate = current_path / name
            rel_parts = candidate.relative_to(root).parts
            if rel_parts and rel_parts[0] in excluded_roots:
                continue
            inspect(candidate)
            if is_vault_path(candidate.resolve(strict=False)):
                continue
            retained_dirs.append(name)
        dirnames[:] = retained_dirs
        for name in filenames:
            inspect(current_path / name)

    return sorted(hits)


def check_archive_path_policy(root: Path) -> list[GovernorFinding]:
    """Ensure historical vaults are gitignored and not git-tracked.

    Enforces the archive-only boundary for ACP/git-lex residue (``.lex``),
    Python product prior art (``python_archive``), and ``Old_project`` so they
    do not re-enter active index/governor surfaces. Trees may remain on disk.
    Lifecycle [bounded]; process anti-drift, not product readiness.
    """
    check_id = "archive-path-policy"
    remediation = (
        "Add vault paths to .gitignore (.lex/, python_archive/, Old_project/), "
        "then `git rm -r --cached <path>` to untrack while keeping on-disk history. "
        "Do not delete vaults without an explicit archive decision."
    )

    gitignore_path = root / ".gitignore"
    gitignore_text = (
        gitignore_path.read_text(encoding="utf-8", errors="replace")
        if gitignore_path.is_file()
        else ""
    )

    missing_ignore: list[str] = []
    still_tracked: list[str] = []
    active_aliases = [
        path
        for path in _HISTORICAL_ACTIVE_ALIASES
        if (root / path).exists() or (root / path).is_symlink()
    ]
    known_aliases = set(active_aliases)
    active_aliases.extend(
        item
        for item in _active_symlinks_into_vaults(root)
        if item.split("->", 1)[0] not in known_aliases
    )
    active_aliases = sorted(set(active_aliases))
    for vault in _HISTORICAL_VAULT_PATHS:
        if not _gitignore_covers(gitignore_text, vault):
            missing_ignore.append(vault)
        tracked = _git_tracked_paths(root, vault)
        if tracked:
            still_tracked.append(f"{vault}:{len(tracked)}")

    if missing_ignore or still_tracked or active_aliases:
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="historical vaults not fully ignored/untracked",
                observed=(
                    f"missing_gitignore={missing_ignore or '[]'}, "
                    f"tracked={still_tracked or '[]'}, "
                    f"active_aliases={active_aliases or '[]'} "
                    f"(lifecycle [bounded]; process anti-drift; advisory until "
                    f"untrack wave lands)."
                ),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="historical vaults are gitignored and untracked",
            observed=(
                f"vaults={list(_HISTORICAL_VAULT_PATHS)} ignored+untracked "
                f"(lifecycle [bounded]; process anti-drift)."
            ),
            remediation="none",
        )
    ]


def _line_lifecycle_tags(line: str) -> set[str]:
    return {m.group(1).lower() for m in _LIFECYCLE_TAG_RE.finditer(line)}


def _adr_truth_expectations(root: Path) -> dict[str, str | None]:
    """Derive every present ADR lifecycle from its own Status, fail-closed."""
    adr_dir = root / "doc" / "adr"
    expectations: dict[str, str | None] = {}
    if adr_dir.is_dir():
        for path in sorted(adr_dir.glob("0*.md")):
            adr_id_match = re.match(r"(?P<id>\d{4})-", path.name)
            if adr_id_match is None:
                continue
            lifecycle = _adr_status_lifecycle(path.read_text(encoding="utf-8", errors="replace"))
            expectations[adr_id_match.group("id")] = lifecycle
    return expectations or dict(_ADR_TRUTH_ORACLE_EXPECTATIONS)


def _adr_lifecycle_evidence(
    root: Path, adr_ids: set[str], lines: list[str]
) -> tuple[GovernorEvidence, ...]:
    evidence: list[GovernorEvidence] = []
    adr_dir = root / "doc" / "adr"
    for adr_id in sorted(adr_ids):
        path = next(iter(sorted(adr_dir.glob(f"{adr_id}-*.md"))), None)
        if path is not None:
            adr_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            status_line = next(
                (
                    index
                    for index, line in enumerate(adr_lines, start=1)
                    if line.strip() == "## Status"
                ),
                1,
            )
            evidence.append(
                GovernorEvidence(path=path.relative_to(root).as_posix(), line=status_line)
            )
        oracle_line = next(
            (index for index, line in enumerate(lines, start=1) if f"ADR-{adr_id}" in line),
            1,
        )
        evidence.append(GovernorEvidence(path="prd/ARCHITECTURE.md", line=oracle_line))
    return tuple(evidence)


def check_adr_truth_oracle_sync(root: Path) -> list[GovernorFinding]:
    """Require key ADRs in ARCHITECTURE with matching lifecycle tags.

    Prevents D098 smoothing where the living truth oracle cites an ADR under a
    stronger lifecycle than the ADR Status/frontmatter (e.g. ADR-0004 as
    [validated] while the ADR is [bounded]). Also requires ontology L1-L7 IDs
    to appear in ARCHITECTURE. Lifecycle [bounded]; process anti-drift.
    """
    check_id = "adr-truth-oracle-sync"
    remediation = (
        "Cite each required ADR in prd/ARCHITECTURE.md with the ADR's real "
        "lifecycle tag on the same line (or keep a foundation ADR map table). "
        "Never upgrade [bounded]/[proposed] ADR direction to [validated] in the "
        "oracle without promoting the ADR itself."
    )

    arch_path = root / "prd" / "ARCHITECTURE.md"
    if not arch_path.is_file():
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="error",
                message="prd/ARCHITECTURE.md missing",
                observed="ARCHITECTURE.md not found",
                remediation="restore the living truth oracle at prd/ARCHITECTURE.md",
            )
        ]

    lines = arch_path.read_text(encoding="utf-8", errors="replace").splitlines()
    missing: list[str] = []
    mismatched: list[str] = []

    expectations = _adr_truth_expectations(root)
    for adr_id, expected_lc in expectations.items():
        needle = f"ADR-{adr_id}"
        if expected_lc is None:
            mismatched.append(f"{needle}:expected=status-lifecycle:seen=none")
            continue
        hit_indexes = [i for i, line in enumerate(lines) if needle in line]
        if not hit_indexes:
            missing.append(needle)
            continue

        # Prefer lifecycle tags on the citation line. When the line cites one
        # ADR only, reject dual or conflicting tags instead of accepting the
        # expected tag beside an overclaim. Multi-ADR summary rows may carry
        # distinct tags for different IDs, so they retain presence semantics.
        found_expected = False
        found_wrong: set[str] = set()
        for i in hit_indexes:
            line_tags = _line_lifecycle_tags(lines[i])
            cited_ids = {match.group("id") for match in _ADR_ID_RE.finditer(lines[i])}
            if line_tags:
                if len(cited_ids) == 1 and cited_ids == {adr_id}:
                    if line_tags == {expected_lc}:
                        found_expected = True
                    else:
                        found_wrong |= line_tags
                    continue
                if expected_lc in line_tags:
                    found_expected = True
                else:
                    found_wrong |= line_tags
                continue

            adjacent_tags: set[str] = set()
            for adjacent in lines[max(0, i - 1) : min(len(lines), i + 2)]:
                adjacent_tags |= _line_lifecycle_tags(adjacent)
            if adjacent_tags == {expected_lc}:
                found_expected = True
            else:
                found_wrong |= adjacent_tags

        if not found_expected:
            wrong = ",".join(sorted(found_wrong)) if found_wrong else "none"
            mismatched.append(f"{needle}:expected={expected_lc}:seen={wrong}")

    if missing or mismatched:
        affected_ids = {
            match.group("id")
            for value in (*missing, *mismatched)
            if (match := _ADR_ID_RE.search(value)) is not None
        }
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="error",
                message="ARCHITECTURE ADR lifecycle sync failed",
                observed=(
                    f"missing={missing or '[]'}, mismatched={mismatched or '[]'} "
                    f"(lifecycle [bounded]; truth-oracle anti-drift)."
                ),
                remediation=remediation,
                rule_id="truth-oracle.lifecycle-mismatch",
                expected="Each ADR citation carries exactly its Status lifecycle without promotion.",
                evidence=_adr_lifecycle_evidence(root, affected_ids, lines),
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="ARCHITECTURE cites required ADRs with matching lifecycle",
            observed=(
                f"adr_checked={len(expectations)} (lifecycle [bounded]; truth-oracle anti-drift)."
            ),
            remediation="none",
        )
    ]


_CONSEQUENTIAL_TRACE_CHAINS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("PC-001", "RQ-001", ("0004", "0005", "0007", "0011")),
    ("PC-002", "RQ-002", ("0013", "0015")),
    ("PC-003", "RQ-003", ("0010", "0011", "0015")),
    ("PC-007", "RQ-007", ("0009", "0011")),
    ("PC-008", "RQ-008", ("0016", "0022")),
    ("PC-009", "RQ-009", ("0017", "0022", "0023")),
    ("PC-010", "RQ-010", ("0015", "0022", "0023")),
    ("PC-014", "RQ-014", ("0012", "0015")),
    ("PC-016", "RQ-016", ()),
    ("PC-019", "RQ-019", ("0014", "0015")),
    ("PC-020", "RQ-020", ("0015",)),
)


def _table_line(
    text: str, item_id: str, *, must_contain: str | None = None
) -> tuple[int, str] | None:
    prefix = f"| {item_id} |"
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.startswith(prefix) and (must_contain is None or must_contain in line):
            return line_number, line
    return None


_DOCUMENT_FRESHNESS_CATALOG = "prd/architecture/document-freshness-triggers.json"


def _working_tree_paths(root: Path) -> set[str]:
    commands = (
        ("git", "-C", str(root), "diff", "--name-only", "HEAD"),
        ("git", "-C", str(root), "ls-files", "--others", "--exclude-standard"),
    )
    changed: set[str] = set()
    for command in commands:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode != 0:
            raise RuntimeError("git working-tree inventory failed")
        changed.update(line.strip() for line in completed.stdout.splitlines() if line.strip())
    return changed


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _freshness_trigger_gaps(catalog: dict[str, Any], changed_paths: set[str]) -> list[str]:
    if catalog.get("schema_version") != "law-nexus-document-freshness-triggers/v1":
        raise ValueError("unsupported document freshness trigger schema")
    if catalog.get("authoritative") is not False:
        raise ValueError("document freshness trigger catalog must be non-authoritative")
    triggers = catalog.get("triggers")
    if not isinstance(triggers, list) or not triggers:
        raise ValueError("document freshness trigger catalog has no triggers")

    gaps: list[str] = []
    seen_ids: set[str] = set()
    for trigger in triggers:
        if not isinstance(trigger, dict):
            raise ValueError("document freshness trigger must be an object")
        trigger_id = str(trigger.get("id") or "")
        sources = trigger.get("sources")
        required_any = trigger.get("required_any")
        review = str(trigger.get("review") or "")
        if (
            not trigger_id
            or trigger_id in seen_ids
            or not isinstance(sources, list)
            or not sources
            or not isinstance(required_any, list)
            or not required_any
            or not review
        ):
            raise ValueError("invalid or duplicate document freshness trigger")
        if not all(isinstance(item, str) and item for item in (*sources, *required_any)):
            raise ValueError("document freshness patterns must be non-empty strings")
        seen_ids.add(trigger_id)

        source_matches = {path for path in changed_paths if _matches_any(path, sources)}
        if not source_matches:
            continue
        companion_matches = {
            path for path in changed_paths - source_matches if _matches_any(path, required_any)
        }
        if not companion_matches:
            gaps.append(trigger_id)
    return gaps


def check_document_freshness_triggers(root: Path) -> list[GovernorFinding]:
    """Warn when consequential document changes omit a catalogued companion refresh."""

    path = root / _DOCUMENT_FRESHNESS_CATALOG
    catalog = _load_json(path)
    changed_paths = _working_tree_paths(root)
    gaps = _freshness_trigger_gaps(catalog, changed_paths)
    if gaps:
        return [
            GovernorFinding(
                check_id="document-freshness-triggers",
                status="fail",
                severity="warn",
                message="changed consequential surfaces lack a catalogued companion refresh",
                observed=f"trigger_gaps={gaps}",
                remediation=(
                    "Refresh or review at least one required companion surface for each trigger, "
                    "then rerun; do not treat a companion edit as semantic validation."
                ),
                rule_id="document-freshness.companion-gap",
                expected="Every matched source change has a distinct changed companion surface.",
                evidence=(GovernorEvidence(path=_DOCUMENT_FRESHNESS_CATALOG),),
            )
        ]
    return [
        GovernorFinding(
            check_id="document-freshness-triggers",
            status="pass",
            severity="ok",
            message="working-tree changes satisfy the bounded freshness trigger catalog",
            observed=(
                f"changed_paths={len(changed_paths)}, trigger_gaps=0 "
                "(change-impact diagnostics only; not semantic validation)."
            ),
            remediation="none",
        )
    ]


def check_published_trace_contract(root: Path) -> list[GovernorFinding]:
    """Verify consequential published PC→RQ→ADR trace structure.

    This is a bounded publication consistency check. It verifies stable IDs,
    declared links, proof/lifecycle/non-claim cells and assessment role
    separation; it does not validate the meaning or implementation of a claim.
    """

    check_id = "published-trace-contract"
    paths = {
        "product": root / "prd" / "PRODUCT.md",
        "requirements": root / "prd" / "REQUIREMENTS.md",
        "architecture": root / "prd" / "ARCHITECTURE.md",
        "assessment": root / "assessment" / "01-authority-map.md",
    }
    missing_files = [
        path.relative_to(root).as_posix() for path in paths.values() if not path.is_file()
    ]
    if missing_files:
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="published trace contract surfaces are incomplete",
                observed=f"missing_files={missing_files}",
                remediation="Restore the tracked Product, Requirements, oracle and authority-map surfaces.",
                rule_id="published-trace.missing-surface",
                expected="All tracked publication trace surfaces exist.",
                evidence=tuple(GovernorEvidence(path=path) for path in missing_files),
            )
        ]

    texts = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    gaps: list[str] = []
    evidence: list[GovernorEvidence] = []
    for pc_id, rq_id, adr_ids in _CONSEQUENTIAL_TRACE_CHAINS:
        product_row = _table_line(texts["product"], pc_id, must_contain=rq_id)
        requirement_row = _table_line(texts["requirements"], rq_id, must_contain=pc_id)
        if product_row is None or rq_id not in product_row[1]:
            gaps.append(f"{pc_id}/{rq_id}:product-link")
            evidence.append(GovernorEvidence(path="prd/PRODUCT.md"))
        elif len(product_row[1].split("|")) < 6:
            gaps.append(f"{pc_id}/{rq_id}:product-proof-cells")
            evidence.append(GovernorEvidence(path="prd/PRODUCT.md", line=product_row[0]))
        if requirement_row is None or pc_id not in requirement_row[1]:
            gaps.append(f"{pc_id}/{rq_id}:requirements-link")
            evidence.append(GovernorEvidence(path="prd/REQUIREMENTS.md"))
        elif len(requirement_row[1].split("|")) < 9:
            gaps.append(f"{pc_id}/{rq_id}:requirements-proof-cells")
            evidence.append(GovernorEvidence(path="prd/REQUIREMENTS.md", line=requirement_row[0]))
        for adr_id in adr_ids:
            if f"ADR-{adr_id}" not in texts["architecture"]:
                gaps.append(f"{pc_id}/{rq_id}:oracle-ADR-{adr_id}")
                evidence.append(GovernorEvidence(path="prd/ARCHITECTURE.md"))

    assessment_lower = texts["assessment"].lower()
    if not (
        "assessmentpacket" in assessment_lower
        and "process evidence" in assessment_lower
        and ("не является product" in assessment_lower or "not product" in assessment_lower)
    ):
        gaps.append("assessment-process-only-boundary")
        evidence.append(GovernorEvidence(path="assessment/01-authority-map.md"))

    if gaps:
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="published consequential trace contract is incomplete",
                observed=f"gaps={sorted(set(gaps))}",
                remediation=(
                    "Repair the tracked PC/RQ/ADR links, proof cells or assessment role boundary; "
                    "do not use local GSD, registry or assessment output as product proof."
                ),
                rule_id="published-trace.chain-gap",
                expected="Consequential PC/RQ rows resolve to oracle ADRs with process-only assessment.",
                evidence=tuple(dict.fromkeys(evidence)),
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="published consequential trace contract is structurally complete",
            observed=(
                f"chains={len(_CONSEQUENTIAL_TRACE_CHAINS)} "
                "(lifecycle [bounded]; publication structure only; not product validation)."
            ),
            remediation="none",
        )
    ]


def check_adr_doc_matrix_coverage(root: Path) -> list[GovernorFinding]:
    """Require ontology ADR-0016..0022 cites in REQUIREMENTS and PROJECT.

    Closes the post-M165 coverage hole where the living ontology spine existed
    only in ARCHITECTURE/adr README. Lifecycle [bounded]; process anti-drift.
    """
    check_id = "adr-doc-matrix-coverage"
    remediation = (
        "Cite each ADR-0016..0022 in .gsd/REQUIREMENTS.md (e.g. R074 / R068 / R070 "
        "notes) and .gsd/PROJECT.md ontology section so the requirement/project "
        "contract tracks the design spine."
    )

    missing: list[str] = []
    for rel in _ONTOLOGY_DOC_MATRIX_SURFACES:
        path = root / rel
        if not path.is_file():
            missing.append(f"{rel}:missing_file")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for adr_id in _ONTOLOGY_DOC_MATRIX_ADRS:
            if f"ADR-{adr_id}" not in text:
                missing.append(f"{rel}:ADR-{adr_id}")

    if missing:
        preview = missing[:16]
        extra = len(missing) - len(preview)
        observed = f"missing={preview}"
        if extra > 0:
            observed += f" +{extra}"
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="ontology ADR×doc matrix coverage incomplete",
                observed=(f"{observed} (lifecycle [bounded]; process anti-drift; advisory)."),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="ontology ADR-0016..0022 cited in REQUIREMENTS and PROJECT",
            observed=(
                f"surfaces={list(_ONTOLOGY_DOC_MATRIX_SURFACES)} "
                f"adrs={list(_ONTOLOGY_DOC_MATRIX_ADRS)} "
                f"(lifecycle [bounded]; process anti-drift)."
            ),
            remediation="none",
        )
    ]


def check_adr_index_completeness(root: Path) -> list[GovernorFinding]:
    """Every doc/adr/0*.md (except README) must be listed in doc/adr/README.md."""
    check_id = "adr-index-completeness"
    remediation = (
        "Add the missing ADR file name or ADR-NNNN id to doc/adr/README.md so the "
        "index remains the navigable catalog of architectural decisions."
    )
    adr_dir = root / "doc" / "adr"
    readme = adr_dir / "README.md"
    if not adr_dir.is_dir() or not readme.is_file():
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="error",
                message="doc/adr index surface missing",
                observed=f"adr_dir={adr_dir.is_dir()}, readme={readme.is_file()}",
                remediation="restore doc/adr/ and doc/adr/README.md",
            )
        ]

    readme_text = readme.read_text(encoding="utf-8", errors="replace")
    readme_lines = readme_text.splitlines()
    missing: list[str] = []
    lifecycle_missing: list[str] = []
    for path in sorted(adr_dir.glob("0*.md")):
        adr_id_match = re.search(r"(\d{4})", path.name)
        if not adr_id_match:
            continue
        adr_id = adr_id_match.group(1)
        needle = f"ADR-{adr_id}"
        matching_lines = [line for line in readme_lines if needle in line or path.name in line]
        if not matching_lines:
            missing.append(path.name)
            continue
        lifecycle = _adr_status_lifecycle(path.read_text(encoding="utf-8", errors="replace"))
        if lifecycle is not None and not any(
            lifecycle in _line_lifecycle_tags(line) for line in matching_lines
        ):
            lifecycle_missing.append(f"{needle}:expected={lifecycle}")

    if missing or lifecycle_missing:
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="ADR index is missing files or per-entry lifecycle tags",
                observed=(
                    f"missing={missing or '[]'}, lifecycle_missing={lifecycle_missing or '[]'} "
                    f"(lifecycle [bounded]; index anti-drift; advisory)."
                ),
                remediation=(
                    remediation
                    + " Include the ADR Status lifecycle tag on that ADR's own index line."
                ),
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="all ADR files are listed in doc/adr/README.md",
            observed="adr_index_complete=true (lifecycle [bounded]; index anti-drift).",
            remediation="none",
        )
    ]


def _adr_status_lifecycle(text: str) -> str | None:
    """Extract the primary lifecycle tag from an ADR Status section first line."""
    match = re.search(r"(?ims)^##\s*Status\s*\n+(.+)$", text)
    if not match:
        return None
    first = match.group(1).splitlines()[0]
    tags = _LIFECYCLE_TAG_RE.findall(first)
    return tags[0].lower() if tags else None


def check_adr_structure_hygiene(root: Path) -> list[GovernorFinding]:
    """Require MADR sections + Status lifecycle on every ADR file.

    Makes ADRs machine-verifiable: Status must carry a D098 lifecycle tag on the
    first Status line; required section headings must exist. Gaps are advisory
    (warn) so historical ADR prose can be repaired without blocking the tree.
    Lifecycle [bounded]; process anti-drift.
    """
    check_id = "adr-structure-hygiene"
    remediation = (
        "For each ADR under doc/adr/0*.md: put a D098 lifecycle tag on the first "
        "Status line (Accepted [proposed|bounded|smoke|validated|deferred]) and "
        "ensure ## Status/Context/Decision/Consequences/Non-claims headings exist."
    )

    adr_dir = root / "doc" / "adr"
    if not adr_dir.is_dir():
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="error",
                message="doc/adr directory missing",
                observed="doc/adr not found",
                remediation="restore doc/adr with MADR ADR files",
            )
        ]

    missing_status_lc: list[str] = []
    missing_sections: list[str] = []
    for path in sorted(adr_dir.glob("0*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if _adr_status_lifecycle(text) is None:
            missing_status_lc.append(path.name)
        for section in _ADR_REQUIRED_SECTIONS:
            if not re.search(rf"(?im)^##\s*{re.escape(section)}\s*$", text):
                missing_sections.append(f"{path.name}:##{section}")

    if missing_status_lc or missing_sections:
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="ADR structure or Status lifecycle incomplete",
                observed=(
                    f"missing_status_lifecycle={missing_status_lc or '[]'}, "
                    f"missing_sections={missing_sections[:20] or '[]'} "
                    f"(lifecycle [bounded]; ADR hygiene; advisory)."
                ),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="all ADRs have Status lifecycle and required MADR sections",
            observed=("adr_structure_complete=true (lifecycle [bounded]; ADR hygiene)."),
            remediation="none",
        )
    ]


_MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\((?P<target>[^)]+)\)")
_ADR_SUPERSESSION_REF_RE = re.compile(
    r"\bADR-(?P<id>\d{4})(?:#(?P<scope>[a-z0-9][a-z0-9-]*))?\b",
    re.IGNORECASE,
)


def _markdown_heading_slugs(text: str) -> set[str]:
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match is None:
            continue
        slug = match.group(1).strip().lower()
        slug = re.sub(r"[^\w\- ]", "", slug, flags=re.UNICODE)
        slug = re.sub(r"\s+", "-", slug).strip("-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        slugs.add(slug if count == 0 else f"{slug}-{count}")
    return slugs


def check_adr_link_integrity(root: Path) -> list[GovernorFinding]:
    """Resolve relative Markdown links and local heading fragments in active ADRs."""
    check_id = "adr-link-integrity"
    adr_dir = root / "doc" / "adr"
    if not adr_dir.is_dir():
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="error",
                message="doc/adr directory missing",
                observed="doc/adr not found",
                remediation="restore doc/adr before checking ADR links",
            )
        ]

    gaps: list[str] = []
    evidence: list[GovernorEvidence] = []
    for source in sorted(adr_dir.glob("0*.md")):
        for line_number, line in enumerate(
            source.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            for match in _MARKDOWN_LINK_RE.finditer(line):
                raw_target = match.group("target").strip().strip("<>")
                if not raw_target or re.match(r"^[a-z][a-z0-9+.-]*:", raw_target, re.I):
                    continue
                path_part, separator, fragment = raw_target.partition("#")
                if not path_part:
                    target = source
                else:
                    target = (source.parent / path_part).resolve()
                    try:
                        target.relative_to(root.resolve())
                    except ValueError:
                        gaps.append(f"outside-root:{source.name}:{line_number}")
                        evidence.append(
                            GovernorEvidence(
                                path=source.relative_to(root).as_posix(), line=line_number
                            )
                        )
                        continue
                if not target.is_file():
                    gaps.append(f"missing-target:{source.name}:{line_number}")
                    evidence.append(
                        GovernorEvidence(path=source.relative_to(root).as_posix(), line=line_number)
                    )
                    continue
                if separator and fragment:
                    headings = _markdown_heading_slugs(
                        target.read_text(encoding="utf-8", errors="replace")
                    )
                    if fragment.lower() not in headings:
                        gaps.append(f"missing-fragment:{source.name}:{line_number}")
                        evidence.append(
                            GovernorEvidence(
                                path=source.relative_to(root).as_posix(), line=line_number
                            )
                        )

    if gaps:
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="ADR relative Markdown links are unresolved",
                observed=f"gaps={gaps[:40]} (repository-link diagnostics only).",
                remediation=(
                    "Repair each relative target or heading fragment in doc/adr; do not "
                    "replace a missing authority link with unlinked prose."
                ),
                rule_id="adr-links.relative-target",
                expected="Every relative ADR Markdown link resolves inside the repository.",
                evidence=tuple(dict.fromkeys(evidence)),
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="ADR relative Markdown links resolve",
            observed="relative_link_gaps=0 (repository-link diagnostics only).",
            remediation="none",
        )
    ]


def _adr_frontmatter(text: str) -> tuple[dict[str, tuple[str, int]], int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fields: dict[str, tuple[str, int]] = {}
    for line_number, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return fields, line_number
        match = re.match(r"^(?P<key>[a-z_]+):\s*(?P<value>.*)$", line, re.I)
        if match is not None:
            fields[match.group("key").lower()] = (
                match.group("value").split(" #", 1)[0].strip(),
                line_number,
            )
    return {}, 0


def _supersession_refs(value: str) -> set[tuple[str, str]]:
    return {
        (match.group("id"), (match.group("scope") or "").lower())
        for match in _ADR_SUPERSESSION_REF_RE.finditer(value)
    }


def check_adr_supersession_graph(root: Path) -> list[GovernorFinding]:
    """Validate metadata-owned ADR supersession targets, reciprocity and acyclicity."""
    check_id = "adr-supersession-graph"
    adr_dir = root / "doc" / "adr"
    if not adr_dir.is_dir():
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="error",
                message="doc/adr directory missing",
                observed="doc/adr not found",
                remediation="restore doc/adr before checking supersession metadata",
            )
        ]

    records: dict[str, tuple[Path, dict[str, tuple[str, int]]]] = {}
    duplicate_ids: set[str] = set()
    for path in sorted(adr_dir.glob("0*.md")):
        fields, _ = _adr_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        id_value = fields.get("id", ("", 1))[0]
        match = re.fullmatch(r"ADR-(\d{4})", id_value, re.I)
        if match is None:
            continue
        adr_id = match.group(1)
        if adr_id in records:
            duplicate_ids.add(adr_id)
        records[adr_id] = (path, fields)

    outgoing: dict[str, set[tuple[str, str]]] = {}
    incoming: dict[str, set[tuple[str, str]]] = {}
    source_lines: dict[tuple[str, str], int] = {}
    for adr_id, (_, fields) in records.items():
        supersedes_field = fields.get("supersedes") or fields.get("superseds")
        superseded_by_field = fields.get("superseded_by")
        outgoing[adr_id] = _supersession_refs(supersedes_field[0]) if supersedes_field else set()
        incoming[adr_id] = (
            _supersession_refs(superseded_by_field[0]) if superseded_by_field else set()
        )
        if supersedes_field:
            source_lines[(adr_id, "supersedes")] = supersedes_field[1]
        if superseded_by_field:
            source_lines[(adr_id, "superseded_by")] = superseded_by_field[1]

    gaps: list[str] = [f"duplicate-id:ADR-{adr_id}" for adr_id in sorted(duplicate_ids)]
    affected: set[tuple[str, str]] = set()
    for new_id, old_refs in outgoing.items():
        for old_id, scope in old_refs:
            edge = f"ADR-{new_id}->ADR-{old_id}" + (f"#{scope}" if scope else "")
            if old_id not in records:
                gaps.append(f"missing-target:{edge}")
                affected.add((new_id, "supersedes"))
                continue
            if (new_id, scope) not in incoming.get(old_id, set()):
                gaps.append(f"non-reciprocal:{edge}")
                affected.update(((new_id, "supersedes"), (old_id, "superseded_by")))

    for old_id, new_refs in incoming.items():
        for new_id, scope in new_refs:
            edge = f"ADR-{old_id}<-ADR-{new_id}" + (f"#{scope}" if scope else "")
            if new_id not in records:
                gaps.append(f"missing-target:{edge}")
                affected.add((old_id, "superseded_by"))
                continue
            if (old_id, scope) not in outgoing.get(new_id, set()):
                gaps.append(f"non-reciprocal:{edge}")
                affected.update(((old_id, "superseded_by"), (new_id, "supersedes")))

    adjacency = {
        adr_id: {target for target, _ in refs if target in records}
        for adr_id, refs in outgoing.items()
    }
    visiting: set[str] = set()
    visited: set[str] = set()
    cycle_nodes: set[str] = set()

    def visit(adr_id: str, path: tuple[str, ...]) -> None:
        if adr_id in visiting:
            cycle_nodes.update(path[path.index(adr_id) :])
            return
        if adr_id in visited:
            return
        visiting.add(adr_id)
        for target in adjacency.get(adr_id, set()):
            visit(target, (*path, target))
        visiting.remove(adr_id)
        visited.add(adr_id)

    for adr_id in sorted(records):
        visit(adr_id, (adr_id,))
    if cycle_nodes:
        gaps.append("cycle:" + "->".join(f"ADR-{item}" for item in sorted(cycle_nodes)))
        affected.update((item, "supersedes") for item in cycle_nodes)

    if gaps:
        evidence: list[GovernorEvidence] = []
        for adr_id, field in sorted(affected):
            record = records.get(adr_id)
            if record is None:
                continue
            path, _ = record
            evidence.append(
                GovernorEvidence(
                    path=path.relative_to(root).as_posix(),
                    line=source_lines.get((adr_id, field), 1),
                )
            )
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="ADR supersession metadata graph is inconsistent",
                observed=f"gaps={gaps[:40]} (metadata graph diagnostics only).",
                remediation=(
                    "Repair supersedes/superseded_by ADR metadata with matching optional "
                    "#scope references; remove missing targets and cycles."
                ),
                rule_id="adr-supersession.graph-integrity",
                expected="Supersession targets exist, are reciprocal by scope, and form a DAG.",
                evidence=tuple(dict.fromkeys(evidence)),
            )
        ]

    edge_count = sum(len(refs) for refs in outgoing.values())
    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="ADR supersession metadata graph is coherent",
            observed=(
                f"adr_nodes={len(records)}, supersession_edges={edge_count}, cycles=0 "
                "(metadata graph diagnostics only)."
            ),
            remediation="none",
        )
    ]


def check_adr_matrix_freshness(root: Path) -> list[GovernorFinding]:
    """Require the tracked non-authoritative ADR matrix to match current inputs."""
    check_id = "adr-matrix-freshness"
    result = check_adr_matrix_output(root, root / DEFAULT_ADR_MATRIX_PATH)
    if result["status"] != "ok":
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="derived ADR matrix is missing or stale",
                observed=(
                    f"output={result['output']}, reason={result['reason']} "
                    "(derived diagnostics only)."
                ),
                remediation=(
                    "Regenerate with `uv run python -m law_nexus_harness adr-verify "
                    "--matrix generate --stdout > prd/architecture/adr-matrix.json`, "
                    "then review the diff; never treat the matrix as authority."
                ),
                rule_id="adr-matrix.derived-freshness",
                expected="Tracked non-authoritative ADR matrix matches active ADR inputs.",
                evidence=(GovernorEvidence(path=DEFAULT_ADR_MATRIX_PATH.as_posix()),),
            )
        ]
    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="derived ADR matrix matches current inputs",
            observed=(
                f"output={result['output']}, authoritative=false (derived diagnostics only)."
            ),
            remediation="none",
        )
    ]


def check_adr_cross_surface_matrix(root: Path) -> list[GovernorFinding]:
    """Require every present ADR to be cited on core living surfaces.

    Cross-surface matrix: each doc/adr/0*.md ID must appear in
    ARCHITECTURE + root README + doc/adr/README. Ontology ADRs (0016-0022)
    additionally remain covered by adr-doc-matrix-coverage (REQ/PROJECT).
    Advisory until gaps are closed. Lifecycle [bounded]; process anti-drift.
    """
    check_id = "adr-cross-surface-matrix"
    remediation = (
        "Cite every ADR-NNNN present under doc/adr/ in prd/ARCHITECTURE.md, "
        "README.md, and doc/adr/README.md. Prefer the foundation ADR table in "
        "ARCHITECTURE with matching lifecycle tags (see adr-truth-oracle-sync)."
    )

    adr_dir = root / "doc" / "adr"
    if not adr_dir.is_dir():
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="error",
                message="doc/adr directory missing",
                observed="doc/adr not found",
                remediation="restore doc/adr",
            )
        ]

    adr_ids: list[str] = []
    for path in sorted(adr_dir.glob("0*.md")):
        match = re.search(r"(\d{4})", path.name)
        if match:
            adr_ids.append(match.group(1))

    surface_text: dict[str, str] = {}
    missing_surface: list[str] = []
    for rel in _ADR_CROSS_SURFACE_PATHS:
        path = root / rel
        if not path.is_file():
            missing_surface.append(rel)
            surface_text[rel] = ""
        else:
            surface_text[rel] = path.read_text(encoding="utf-8", errors="replace")

    gaps: list[str] = []
    for adr_id in adr_ids:
        needle = f"ADR-{adr_id}"
        for rel, text in surface_text.items():
            if needle not in text and f"{adr_id}-" not in text:
                gaps.append(f"{needle}@{rel}")

    if missing_surface or gaps:
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="ADR cross-surface citation matrix incomplete",
                observed=(
                    f"missing_surfaces={missing_surface or '[]'}, "
                    f"gaps={gaps[:24] or '[]'} "
                    f"(lifecycle [bounded]; matrix anti-drift; advisory)."
                ),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="every ADR is cited on core living surfaces",
            observed=(
                f"adrs={adr_ids} surfaces={list(_ADR_CROSS_SURFACE_PATHS)} "
                f"(lifecycle [bounded]; matrix anti-drift)."
            ),
            remediation="none",
        )
    ]


# Retired Python-era ADR IDs (files absent). Living entrypoints may mention them
# only with an explicit retirement qualifier on the same line.
_RETIRED_ADR_IDS: tuple[str, ...] = ("0001", "0002", "0003", "0006")
_RETIRED_ADR_LINE_RE = re.compile(r"\bADR[-\s]?0*([1236])\b", re.IGNORECASE)
_RETIRED_ADR_QUALIFIER_RE = re.compile(
    r"(?i)\b(historical|retired|rejected|superseded|prior[- ]art|archive-only|"
    r"archived|not present|not active|python[- ]era|python-specific)\b"
)
_RETIRED_ADR_SCAN_PATHS: tuple[str, ...] = (
    "prd/ARCHITECTURE.md",
    "README.md",
    "doc/adr/README.md",
    "prd/project-state/roadmap.md",
)

# Entrypoint surfaces for residual era-token noise (historical-only backends).
# Mentions are allowed only with historical/non-claim qualifiers nearby.
_ERA_NOISE_SCAN_PATHS: tuple[str, ...] = (
    "prd/ARCHITECTURE.md",
    "README.md",
    "doc/adr/README.md",
    "prd/architecture/README.md",
    "prd/parser/README.md",
    "prd/project-state/roadmap.md",
)
# Detection keyword set: falkordb|git-lex|acp|pyo3|minimax (historical-only ban).
_ERA_NOISE_TOKEN_RE = re.compile(r"(?i)\b(falkordb(?:lite)?|git[-_]lex|\bacp\b|pyo3|minimax)\b")
_ERA_NOISE_QUALIFIER_RE = re.compile(
    r"(?i)\b(historical|history|archived|archive-only|prior[- ]art|decommission|"
    r"decommissioned|rejected|superseded|not active|non-claim|non-claims|"
    r"does not|do not|must not|never|forbidden|no production|production-scale "
    r"claim|replacing|replaced|→|ruvector)\b"
)


def check_adr_retired_id_ban(root: Path) -> list[GovernorFinding]:
    """Ban unqualified live cites of retired ADR-0001/0002/0003/0006.

    Those IDs have no files under doc/adr/ (Python-onion / PyO3-bridge era).
    Living entrypoints may mention them only with an explicit retirement
    qualifier on the same line (historical/retired/rejected/superseded/...)."""
    check_id = "adr-retired-id-ban"
    remediation = (
        "Rewrite living entrypoints so ADR-0001/0002/0003/0006 appear only with "
        "historical/retired/rejected/superseded qualifiers on the same line, or "
        "remove the cite and point at the current ADR (0004+)."
    )

    hits: list[str] = []
    for rel in _RETIRED_ADR_SCAN_PATHS:
        path = root / rel
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, line in enumerate(lines):
            if not _RETIRED_ADR_LINE_RE.search(line):
                continue
            window = " ".join(lines[j] for j in (idx - 1, idx, idx + 1) if 0 <= j < len(lines))
            if _RETIRED_ADR_QUALIFIER_RE.search(window):
                continue
            ids = sorted({f"000{m.group(1)}" for m in _RETIRED_ADR_LINE_RE.finditer(line)})
            hits.append(f"{rel}:{idx + 1}:ADR-{','.join(ids)}")

    if hits:
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="unqualified retired ADR IDs cited on living entrypoints",
                observed=(f"hits={hits[:20]} (lifecycle [bounded]; retired-id ban; advisory)."),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="no unqualified retired ADR IDs on living entrypoints",
            observed=(
                f"scanned={list(_RETIRED_ADR_SCAN_PATHS)} retired={list(_RETIRED_ADR_IDS)} "
                f"(lifecycle [bounded]; retired-id ban)."
            ),
            remediation="none",
        )
    ]


def check_active_surface_era_noise(root: Path) -> list[GovernorFinding]:
    """Warn on unqualified historical-only era tokens on living entrypoints.

    Living entrypoints may mention era tokens (falkordb|git-lex|acp|pyo3|minimax)
    only with historical/non-claim qualifiers nearby. Dense derived registry/CI
    views are out of scope (still non-authoritative). Advisory only."""
    check_id = "active-surface-era-noise"
    remediation = (
        "On living entrypoints (ARCHITECTURE, README, adr/README, architecture/parser "
        "README, project-state roadmap), qualify every historical-only era token "
        "(falkordb/acp/git-lex/pyo3/minimax) as historical/archive-only/non-claim, "
        "or remove the token."
    )

    hits: list[str] = []
    for rel in _ERA_NOISE_SCAN_PATHS:
        path = root / rel
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, line in enumerate(lines):
            tokens = _ERA_NOISE_TOKEN_RE.findall(line)
            if not tokens:
                continue
            # Require the historical/non-claim polarity on the token line.
            # Adjacent infrastructure or heading vocabulary must not launder
            # an active production assertion for a historical-only backend.
            if _ERA_NOISE_QUALIFIER_RE.search(line):
                continue
            uniq = sorted({t.lower() for t in tokens})
            hits.append(f"{rel}:{idx + 1}:{','.join(uniq)}")

    if hits:
        return [
            GovernorFinding(
                check_id=check_id,
                status="fail",
                severity="warn",
                message="unqualified era tokens on living entrypoints",
                observed=(
                    f"hit_count={len(hits)}, hits={hits[:24]} "
                    f"(lifecycle [bounded]; era-noise ban; advisory)."
                ),
                remediation=remediation,
            )
        ]

    return [
        GovernorFinding(
            check_id=check_id,
            status="pass",
            severity="ok",
            message="living entrypoints qualify era tokens",
            observed=(
                f"scanned={list(_ERA_NOISE_SCAN_PATHS)} (lifecycle [bounded]; era-noise ban)."
            ),
            remediation="none",
        )
    ]


def _extract_pre_commit_hook_ids_with_entries(root: Path) -> str:
    """Return pre-commit config text for script reference scanning."""
    config = root / ".pre-commit-config.yaml"
    if not config.is_file():
        return ""
    return config.read_text(encoding="utf-8", errors="replace")


_PROCESS_NON_CLAIM = (
    "Repository-control evidence only; no product, runtime, legal, requirement or "
    "lifecycle validation."
)


def _check_spec(
    check_id: str,
    group: str,
    kind: CheckKind,
    runner: CheckRunner,
    purpose: str,
    authority_inputs: tuple[str, ...],
    default_severity: Severity,
) -> CheckSpec:
    return CheckSpec(
        check_id=check_id,
        group=group,
        kind=kind,
        runner=runner,
        purpose=purpose,
        authority_inputs=authority_inputs,
        default_severity=default_severity,
        non_claim=_PROCESS_NON_CLAIM,
    )


GOVERNOR_CHECK_SPECS: tuple[CheckSpec, ...] = (
    _check_spec(
        "architecture-direction-contract",
        "docs",
        "deterministic",
        check_architecture_direction,
        "Keep the active direction contract coherent across living projections.",
        _DIRECTION_PATHS,
        "error",
    ),
    _check_spec(
        "active-requirement-contradictions",
        "docs",
        "deterministic",
        check_active_requirement_contradictions,
        "Reject active local requirement text that contradicts the Rust-only direction.",
        (".gsd/REQUIREMENTS.md",),
        "error",
    ),
    _check_spec(
        "forward-roadmap-sequence",
        "docs",
        "deterministic",
        check_forward_roadmap_sequence,
        "Keep the tracked forward roadmap sequence unique and complete.",
        ("prd/migration/forward-roadmap.md",),
        "error",
    ),
    _check_spec(
        "roadmap-freshness",
        "docs",
        "deterministic",
        check_roadmap_freshness,
        "Keep tracked roadmap state aligned with local GSD workflow state.",
        (".gsd/STATE.md", "prd/project-state/data/roadmap.json"),
        "error",
    ),
    _check_spec(
        "hostile-proof-chain",
        "proof",
        "deterministic",
        check_hostile_proof_chain,
        "Keep hostile proof packages contiguous and baseline aggregates coherent.",
        (
            "prd/migration/rust-evidence/probes/",
            "prd/architecture/m111-final-architecture-baseline.md",
        ),
        "error",
    ),
    _check_spec(
        "gsd-residual-debt",
        "docs",
        "deterministic",
        check_gsd_residual_debt,
        "Expose stale or contradictory local GSD milestone state.",
        (".gsd/STATE.md",),
        "error",
    ),
    _check_spec(
        "port-contract-coverage",
        "verification",
        "deterministic",
        check_port_contract_coverage,
        "Inventory bounded shared port-contract coverage.",
        ("crates/", "crates/ln-testkit/"),
        "warn",
    ),
    _check_spec(
        "hostile-negative-suite-coverage",
        "verification",
        "deterministic",
        check_hostile_negative_suite_coverage,
        "Inventory bounded shared hostile-negative coverage.",
        ("crates/", "crates/ln-testkit/"),
        "warn",
    ),
    _check_spec(
        "multi-adapter-port-coverage",
        "verification",
        "deterministic",
        check_multi_adapter_port_coverage,
        "Inventory shared suites for real adapters on multi-adapter ports.",
        ("crates/", "crates/ln-testkit/"),
        "warn",
    ),
    _check_spec(
        "live-adapter-readiness",
        "verification",
        "deterministic",
        check_live_adapter_readiness,
        "Keep TEI and RuVector repository claims within their evidence ceiling.",
        ("crates/", "doc/adr/0014-ruvector-primary-infrastructure.md"),
        "warn",
    ),
    _check_spec(
        "ci-quality-gate-drift",
        "verification",
        "deterministic",
        check_ci_quality_gate_drift,
        "Keep quality-gate inventory, pre-commit and CI synchronized.",
        (".pre-commit-config.yaml", ".github/workflows/repository-quality.yml"),
        "warn",
    ),
    _check_spec(
        "verify-test-coverage-drift",
        "verification",
        "deterministic",
        check_verify_test_coverage_drift,
        "Keep tests for active verification scripts in the CI process suite.",
        ("scripts/verify-*.py", "tests/test_verify_*.py"),
        "warn",
    ),
    _check_spec(
        "semantic-stub-in-product-code",
        "semantic",
        "heuristic",
        check_semantic_stub_in_product_code,
        "Surface explicit semantic stub markers in active Rust product source.",
        ("crates/*/src/**/*.rs",),
        "warn",
    ),
    _check_spec(
        "historical-test-debt-visibility",
        "semantic",
        "heuristic",
        check_historical_test_debt_visibility,
        "Surface tests that still reference decommissioned eras.",
        ("tests/test_*.py",),
        "warn",
    ),
    _check_spec(
        "archive-path-policy",
        "adr",
        "deterministic",
        check_archive_path_policy,
        "Keep historical vaults ignored, untracked and unreachable from active symlinks.",
        (".gitignore", "python_archive/", "archive/", "prd/archive/"),
        "warn",
    ),
    _check_spec(
        "adr-truth-oracle-sync",
        "adr",
        "deterministic",
        check_adr_truth_oracle_sync,
        "Require every active ADR lifecycle to match its living-oracle citation.",
        ("doc/adr/0*.md", "prd/ARCHITECTURE.md"),
        "error",
    ),
    _check_spec(
        "adr-index-completeness",
        "adr",
        "deterministic",
        check_adr_index_completeness,
        "Require every active ADR and lifecycle in the ADR index.",
        ("doc/adr/0*.md", "doc/adr/README.md"),
        "warn",
    ),
    _check_spec(
        "document-freshness-triggers",
        "docs",
        "deterministic",
        check_document_freshness_triggers,
        "Require a distinct companion refresh for consequential working-tree document changes.",
        (_DOCUMENT_FRESHNESS_CATALOG,),
        "warn",
    ),
    _check_spec(
        "published-trace-contract",
        "docs",
        "deterministic",
        check_published_trace_contract,
        "Keep consequential Product, Requirement, ADR and assessment-role traces connected.",
        (
            "prd/PRODUCT.md",
            "prd/REQUIREMENTS.md",
            "prd/ARCHITECTURE.md",
            "assessment/01-authority-map.md",
        ),
        "warn",
    ),
    _check_spec(
        "adr-doc-matrix-coverage",
        "adr",
        "deterministic",
        check_adr_doc_matrix_coverage,
        "Keep the bounded ontology ADR workflow weave visible.",
        _ONTOLOGY_DOC_MATRIX_SURFACES,
        "warn",
    ),
    _check_spec(
        "adr-structure-hygiene",
        "adr",
        "deterministic",
        check_adr_structure_hygiene,
        "Require lifecycle Status and core MADR sections.",
        ("doc/adr/0*.md",),
        "warn",
    ),
    _check_spec(
        "adr-link-integrity",
        "adr",
        "deterministic",
        check_adr_link_integrity,
        "Resolve relative Markdown links and local heading fragments in active ADRs.",
        ("doc/adr/0*.md",),
        "warn",
    ),
    _check_spec(
        "adr-supersession-graph",
        "adr",
        "deterministic",
        check_adr_supersession_graph,
        "Validate metadata-owned supersession targets, reciprocity and acyclicity.",
        ("doc/adr/0*.md",),
        "warn",
    ),
    _check_spec(
        "adr-matrix-freshness",
        "adr",
        "deterministic",
        check_adr_matrix_freshness,
        "Keep the tracked non-authoritative ADR matrix synchronized with active inputs.",
        ("doc/adr/0*.md", "prd/ARCHITECTURE.md", DEFAULT_ADR_MATRIX_PATH.as_posix()),
        "warn",
    ),
    _check_spec(
        "adr-cross-surface-matrix",
        "adr",
        "deterministic",
        check_adr_cross_surface_matrix,
        "Require active ADR citations on core living entrypoints.",
        _ADR_CROSS_SURFACE_PATHS,
        "warn",
    ),
    _check_spec(
        "adr-retired-id-ban",
        "adr",
        "heuristic",
        check_adr_retired_id_ban,
        "Surface unqualified retired ADR IDs on living entrypoints.",
        _RETIRED_ADR_SCAN_PATHS,
        "warn",
    ),
    _check_spec(
        "active-surface-era-noise",
        "semantic",
        "heuristic",
        check_active_surface_era_noise,
        "Surface unqualified decommissioned-era vocabulary on living entrypoints.",
        _ERA_NOISE_SCAN_PATHS,
        "warn",
    ),
)


def get_governor_check_spec(check_id: str) -> CheckSpec:
    for spec in GOVERNOR_CHECK_SPECS:
        if spec.check_id == check_id:
            return spec
    raise GovernorSelectionError("unknown-check", check_id)


def governor_groups() -> tuple[str, ...]:
    return tuple(sorted({spec.group for spec in GOVERNOR_CHECK_SPECS}))


def _selected_specs(only: str | None, check: str | None) -> tuple[CheckSpec, ...]:
    if only is not None and check is not None:
        raise GovernorSelectionError("conflicting-selectors", f"only={only},check={check}")
    if check is not None:
        return (get_governor_check_spec(check),)
    if only is None:
        return GOVERNOR_CHECK_SPECS
    selected = tuple(spec for spec in GOVERNOR_CHECK_SPECS if spec.group == only)
    if not selected:
        raise GovernorSelectionError("unknown-group", only)
    return selected


def _enrich_finding(finding: GovernorFinding, spec: CheckSpec) -> GovernorFinding:
    evidence = finding.evidence or tuple(
        GovernorEvidence(path=path) for path in spec.authority_inputs
    )
    return replace(
        finding,
        rule_id=finding.rule_id or f"{finding.check_id}.contract",
        expected=finding.expected or spec.purpose,
        evidence=evidence,
    )


def format_governor_report_text(report: GovernorReport) -> str:
    lines = [
        f"governor status={report.status} pass={report.pass_count} "
        f"warn={report.warn_count} error={report.error_count} tool_error={report.tool_error_count}"
    ]
    for finding in report.findings:
        lines.append(
            f"[{finding.status.upper()}/{finding.severity}] {finding.check_id}: {finding.message}"
        )
        if finding.status == "fail":
            lines.append(f"  observed: {finding.observed}")
            lines.append(f"  remediation: {finding.remediation}")
    return "\n".join(lines) + "\n"


def run_governor(
    root: Path | None = None,
    *,
    only: str | None = None,
    check: str | None = None,
) -> GovernorReport:
    """Run selected governor checks and return a machine-readable report."""

    resolved = (root or Path.cwd()).resolve()
    findings: list[GovernorFinding] = []
    for spec in _selected_specs(only, check):
        try:
            findings.extend(_enrich_finding(item, spec) for item in spec.runner(resolved))
        except Exception as error:  # noqa: BLE001 - bounded tool-error report
            findings.append(
                GovernorFinding(
                    check_id=spec.check_id,
                    status="fail",
                    severity="error",
                    message="governor check could not read or parse its required inputs",
                    observed=f"tool_error={type(error).__name__}",
                    remediation="Repair the required repository inputs or tool environment and rerun.",
                    rule_id="tool-error",
                    expected="The check runner reads and parses every required input.",
                    evidence=tuple(GovernorEvidence(path=path) for path in spec.authority_inputs),
                )
            )
    error_count = sum(1 for item in findings if item.status == "fail" and item.severity == "error")
    warn_count = sum(1 for item in findings if item.status == "fail" and item.severity == "warn")
    pass_count = sum(1 for item in findings if item.status == "pass")
    tool_error_count = sum(1 for item in findings if item.rule_id == "tool-error")
    status: Literal["ok", "failure"] = "ok" if error_count == 0 else "failure"
    return GovernorReport(
        schema_version=GOVERNOR_SCHEMA_VERSION,
        status=status,
        root=str(resolved),
        findings=tuple(findings),
        error_count=error_count,
        warn_count=warn_count,
        pass_count=pass_count,
        tool_error_count=tool_error_count,
    )

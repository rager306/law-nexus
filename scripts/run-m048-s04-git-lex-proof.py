#!/usr/bin/env python3
"""Run the M048/S04 isolated git-lex mechanics proof harness.

This script is intentionally main-repo safe:
- it must be launched from the law-nexus checkout;
- it never initializes git-lex in the main checkout;
- it creates transient workspaces with tempfile.TemporaryDirectory;
- it copies only prd/architecture/acp/fixtures/git-lex-isolated-proof into the
  transient workspace;
- it checks before and after execution that main-repo .lex does not exist.

Safe acquisition/build stance:
- the harness probes for an existing `git lex` subcommand and `git-lex` binary;
- when neither exists, acquisition is reported as `blocked`;
- it does not clone, install, download, write cargo caches, or persist vendor
  sources from this repository. Future adoption work must add a separately
  accepted acquisition decision and proof gate.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "prd/architecture/acp/fixtures/git-lex-isolated-proof"
MAIN_REPO_LEX_DIR = ROOT / ".lex"

REQUIRED_KINDS = {
    "requirement_binding": "RB-ACP-0001",
    "architecture_decision": "AD-ACP-0001",
    "architecture_prompt_record": "APR-ACP-0001",
    "architecture_proposal": "AP-ACP-0001",
    "decision_candidate": "DC-ACP-0001",
    "proof_gate": "PG-ACP-0001",
    "evidence_anchor": "EA-ACP-0001",
    "architecture_health_finding": "AHF-ACP-0001",
    "derived_projection_reference": "DPR-ACP-0001",
    "profile_constraint": "PC-LN-0001",
    "blocked_action": "BA-ACP-0001",
}
FIXTURE_RECORD_IDS = set(REQUIRED_KINDS.values())
NON_CLAIM_FLAGS = [
    "claims_product_readiness",
    "claims_parser_completeness",
    "claims_falkordb_ingestion",
    "claims_legal_correctness",
    "claims_r035_validated",
    "claims_r037_validated",
    "claims_r038_validated",
]
UNSAFE_ANCHOR_PATTERNS = [
    r"^/",
    r"\.gsd/exec/",
    r"\.lex(?:/|$)",
    r"provider_payload",
    r"raw_vectors?",
    r"secret",
]
PROJECT_SPECIFIC_TERMS = {
    "law-nexus",
    "Russian legal evidence",
    "FalkorDB",
    "parser completeness",
    "LLM authority",
    "GSD operational quirks",
    "R035",
    "R037",
    "R038",
}


@dataclass
class Phase:
    name: str
    status: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0


def monotonic_ms() -> int:
    return int(time.monotonic() * 1000)


def phase(name: str, status: str, summary: str, details: dict[str, Any] | None = None, started: int | None = None) -> Phase:
    return Phase(
        name=name,
        status=status,
        summary=summary,
        details=details or {},
        duration_ms=monotonic_ms() - started if started is not None else 0,
    )


def run_probe(command: list[str], cwd: Path) -> dict[str, Any]:
    started = monotonic_ms()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout_preview": completed.stdout[:500],
            "stderr_preview": completed.stderr[:500],
            "duration_ms": monotonic_ms() - started,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "exit_code": None,
            "stdout_preview": (exc.stdout or "")[:500] if isinstance(exc.stdout, str) else "",
            "stderr_preview": (exc.stderr or "")[:500] if isinstance(exc.stderr, str) else "",
            "duration_ms": monotonic_ms() - started,
            "timed_out": True,
        }
    except OSError as exc:
        return {
            "command": command,
            "exit_code": None,
            "stdout_preview": "",
            "stderr_preview": str(exc),
            "duration_ms": monotonic_ms() - started,
            "timed_out": False,
        }


def read_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n([\s\S]*?)\n---\n", text)
    if not match:
        raise ValueError(f"missing YAML frontmatter: {path.name}")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise ValueError(f"frontmatter is not a mapping: {path.name}")
    return data


def flatten(value: Any) -> list[Any]:
    if isinstance(value, dict):
        out: list[Any] = []
        for item in value.values():
            out.extend(flatten(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(flatten(item))
        return out
    return [value]


def referenced_fixture_ids(record: dict[str, Any]) -> set[str]:
    return {
        value
        for value in flatten(record)
        if isinstance(value, str) and value in FIXTURE_RECORD_IDS and value != record.get("id")
    }


def assert_repo_relative_path(path: str) -> None:
    candidate = Path(path)
    if candidate.is_absolute():
        raise ValueError(f"anchor path must be repository-relative: {path!r}")
    if ".." in candidate.parts:
        raise ValueError(f"anchor path must not escape the repository: {path!r}")
    if any(re.search(pattern, path, flags=re.IGNORECASE) for pattern in UNSAFE_ANCHOR_PATTERNS):
        raise ValueError(f"unsafe durable anchor path: {path!r}")


def load_records(copied_fixture_dir: Path) -> dict[str, dict[str, Any]]:
    files = sorted(copied_fixture_dir.glob("*.md"))
    if not files:
        raise ValueError("no fixture Markdown files copied into isolated workspace")
    records: dict[str, dict[str, Any]] = {}
    for path in files:
        record = read_frontmatter(path)
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise ValueError(f"record id missing in {path.name}")
        if record_id in records:
            raise ValueError(f"duplicate record id: {record_id}")
        records[record_id] = record
    return records


def validate_records(records: dict[str, dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    ids_by_kind = {record.get("record_kind"): record_id for record_id, record in records.items()}
    if ids_by_kind != REQUIRED_KINDS:
        failures.append(f"required taxonomy mismatch: expected {REQUIRED_KINDS}, got {ids_by_kind}")
    if set(records) != set(REQUIRED_KINDS.values()):
        failures.append(f"record id mismatch: expected {sorted(REQUIRED_KINDS.values())}, got {sorted(records)}")

    for record_id, record in records.items():
        safety = record.get("safety")
        if not isinstance(safety, dict):
            failures.append(f"{record_id}: missing safety mapping")
            continue
        for flag in NON_CLAIM_FLAGS:
            if safety.get(flag) is not False:
                failures.append(f"{record_id}: safety flag must be false: {flag}")

    unresolved = sorted(
        ref for record in records.values() for ref in referenced_fixture_ids(record) if ref not in records
    )
    if unresolved:
        failures.append(f"unresolved fixture references: {unresolved}")

    anchor = records.get("EA-ACP-0001")
    if not anchor:
        failures.append("EA-ACP-0001 evidence anchor missing")
    else:
        for key in ["repo_relative_path"]:
            try:
                assert_repo_relative_path(str(anchor[key]))
                if not (ROOT / str(anchor[key])).exists():
                    failures.append(f"primary evidence anchor path is missing: {anchor[key]}")
            except (KeyError, ValueError) as exc:
                failures.append(str(exc))
        for item in anchor.get("secondary_repo_relative_paths", []):
            try:
                assert_repo_relative_path(str(item))
                if not (ROOT / str(item)).exists():
                    failures.append(f"secondary evidence anchor path is missing: {item}")
            except ValueError as exc:
                failures.append(str(exc))
    return failures


def acp_projection(records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    edges = {
        record_id: sorted(referenced_fixture_ids(record))
        for record_id, record in records.items()
    }
    return {
        "projection_kind": "deterministic-acp-fixture-projection",
        "authority_status": "non_authoritative",
        "record_count": len(records),
        "records": [
            {
                "id": record_id,
                "record_kind": record.get("record_kind"),
                "status": record.get("status"),
                "title": record.get("title"),
            }
            for record_id, record in sorted(records.items())
        ],
        "edges": edges,
    }


def validate_lifecycle(records: dict[str, dict[str, Any]]) -> list[str]:
    expected = {
        "APR-ACP-0001": "linked",
        "AP-ACP-0001": "candidate_extracted",
        "DC-ACP-0001": "requires_proof",
        "AD-ACP-0001": "requires_proof",
        "PG-ACP-0001": "pending_evidence",
        "AHF-ACP-0001": "blocked",
        "BA-ACP-0001": "active",
    }
    failures = []
    for record_id, status in expected.items():
        actual = records.get(record_id, {}).get("status")
        if actual != status:
            failures.append(f"{record_id}: expected status {status!r}, got {actual!r}")
    gate_text = " ".join(str(records.get("PG-ACP-0001", {}).get("claim_or_requirement", "")).casefold().split())
    for term in [
        "typed records",
        "validation",
        "extraction/projection",
        "query/recovery",
        "lifecycle/proof-gate",
        "source/projection boundary",
        "blocked-action mechanics",
    ]:
        if term not in gate_text:
            failures.append(f"PG-ACP-0001 claim missing mechanic term: {term}")
    return failures


def validate_profile_boundary(records: dict[str, dict[str, Any]]) -> list[str]:
    failures = []
    profile = records.get("PC-LN-0001")
    if profile is None:
        return ["PC-LN-0001 profile constraint missing"]
    if profile.get("profile_id") != "law-nexus":
        failures.append("PC-LN-0001 must own law-nexus profile-specific constraints")
    profile_text = yaml.safe_dump(profile, sort_keys=True)
    for term in PROJECT_SPECIFIC_TERMS:
        if term not in profile_text:
            failures.append(f"profile constraint missing project-specific term: {term}")
    for record_id, record in records.items():
        if record_id == "PC-LN-0001":
            continue
        record_text = yaml.safe_dump(record, sort_keys=True)
        leaked = sorted(term for term in PROJECT_SPECIFIC_TERMS if term in record_text)
        if leaked:
            failures.append(f"project terms leaked into reusable core record {record_id}: {leaked}")
    return failures


def validate_blocked_actions(records: dict[str, dict[str, Any]]) -> list[str]:
    blocked = records.get("BA-ACP-0001")
    if blocked is None:
        return ["BA-ACP-0001 blocked action missing"]
    failures = []
    if "git lex init" not in str(blocked.get("action", "")):
        failures.append("BA-ACP-0001 must explicitly block main-repo git lex init")
    if blocked.get("severity") != "critical":
        failures.append("BA-ACP-0001 severity must be critical")
    if "PG-ACP-0001" not in "\n".join(map(str, blocked.get("required_unblock_evidence", []))):
        failures.append("BA-ACP-0001 must name PG-ACP-0001 as unblock evidence")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Return non-zero when fail-closed checks fail.")
    args = parser.parse_args()

    started_all = monotonic_ms()
    phases: list[Phase] = []
    fatal_failures: list[str] = []
    blocked_or_deferred: list[str] = []

    if Path.cwd().resolve() != ROOT:
        fatal_failures.append(f"must be run from {ROOT}, got {Path.cwd().resolve()}")

    main_lex_before = MAIN_REPO_LEX_DIR.exists()
    if main_lex_before:
        fatal_failures.append("main repository .lex exists before proof harness execution")

    start = monotonic_ms()
    probes = [
        run_probe(["git", "lex", "--help"], ROOT),
        run_probe(["git-lex", "--help"], ROOT),
    ]
    available = [probe for probe in probes if probe["exit_code"] == 0 and not probe["timed_out"]]
    if available:
        phases.append(phase("acquisition", "pass", "Existing git-lex command responds to a help probe; no acquisition attempted.", {"probes": probes}, start))
    else:
        blocked_or_deferred.append("git-lex executable unavailable; runtime git-lex mechanics are blocked, deterministic fixture checks still ran")
        phases.append(phase("acquisition", "blocked", "No existing git-lex executable was found; safe acquisition/build is intentionally not attempted from the main checkout.", {"probes": probes, "safe_acquisition_policy": "no clone/install/download/durable build from law-nexus"}, start))

    records: dict[str, dict[str, Any]] = {}
    projection: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="m048-s04-git-lex-proof-") as tmp:
        tmp_root = Path(tmp)
        isolated_fixture_dir = tmp_root / "git-lex-isolated-proof"

        start = monotonic_ms()
        try:
            if not FIXTURE_DIR.exists():
                raise FileNotFoundError(f"missing fixture directory: {FIXTURE_DIR.relative_to(ROOT)}")
            shutil.copytree(FIXTURE_DIR, isolated_fixture_dir)
            copied_files = sorted(path.name for path in isolated_fixture_dir.glob("*.md"))
            if (isolated_fixture_dir / ".lex").exists():
                raise RuntimeError("copied fixture unexpectedly contains .lex state")
            phases.append(phase("fixture_copy", "pass", "Copied only the S04 fixture pack into a Python temporary workspace.", {"temporary_workspace": str(tmp_root), "copied_files": copied_files}, start))
        except Exception as exc:  # noqa: BLE001 - harness must emit diagnostics rather than traceback-only output.
            fatal_failures.append(f"fixture_copy: {exc}")
            phases.append(phase("fixture_copy", "fail", "Could not copy fixture pack into isolated workspace.", {"error": str(exc)}, start))

        start = monotonic_ms()
        try:
            records = load_records(isolated_fixture_dir)
            failures = validate_records(records)
            if failures:
                fatal_failures.extend(f"validation: {failure}" for failure in failures)
                phases.append(phase("validation", "fail", "Fixture source-record validation failed.", {"failures": failures}, start))
            else:
                phases.append(phase("validation", "pass", "Typed source records, required taxonomy, relationships, safety flags, and anchors validated.", {"record_count": len(records), "record_ids": sorted(records)}, start))
        except Exception as exc:  # noqa: BLE001
            fatal_failures.append(f"validation: {exc}")
            phases.append(phase("validation", "fail", "Fixture validation crashed safely and emitted diagnostics.", {"error": str(exc)}, start))

        start = monotonic_ms()
        try:
            if not records:
                raise RuntimeError("records unavailable after validation")
            projection = acp_projection(records)
            projection_path = tmp_root / "derived-projection.json"
            projection_path.write_text(json.dumps(projection, indent=2, sort_keys=True), encoding="utf-8")
            if projection["authority_status"] != "non_authoritative":
                raise RuntimeError("derived projection must remain non_authoritative")
            phases.append(phase("extraction_projection", "pass", "Built a deterministic non-authoritative projection in the temporary workspace only.", {"projection_path": str(projection_path), "authority_status": projection["authority_status"], "record_count": projection["record_count"]}, start))
        except Exception as exc:  # noqa: BLE001
            fatal_failures.append(f"extraction_projection: {exc}")
            phases.append(phase("extraction_projection", "fail", "Could not build or validate temporary projection.", {"error": str(exc)}, start))

        start = monotonic_ms()
        try:
            if not projection:
                raise RuntimeError("projection unavailable")
            by_kind = {item["record_kind"]: item["id"] for item in projection["records"]}
            recovered_decision = by_kind.get("architecture_decision")
            recovered_gate_edges = projection["edges"].get("PG-ACP-0001", [])
            if recovered_decision != "AD-ACP-0001":
                raise RuntimeError("query recovery did not recover AD-ACP-0001 decision")
            if "EA-ACP-0001" not in recovered_gate_edges:
                raise RuntimeError("query recovery did not recover proof gate evidence edge")
            phases.append(phase("query_recovery", "pass", "Recovered typed records and proof-gate relationships from the temporary projection.", {"architecture_decision": recovered_decision, "proof_gate_edges": recovered_gate_edges}, start))
        except Exception as exc:  # noqa: BLE001
            fatal_failures.append(f"query_recovery: {exc}")
            phases.append(phase("query_recovery", "fail", "Could not recover expected records from temporary projection.", {"error": str(exc)}, start))

        start = monotonic_ms()
        failures = validate_lifecycle(records) if records else ["records unavailable"]
        if failures:
            fatal_failures.extend(f"lifecycle_proof_gate: {failure}" for failure in failures)
            phases.append(phase("lifecycle_proof_gate", "fail", "Lifecycle/proof-gate semantics failed.", {"failures": failures}, start))
        else:
            phases.append(phase("lifecycle_proof_gate", "pass", "Lifecycle and proof-gate records expose pending/blocked states without claiming proof satisfaction.", {"checked_records": ["APR-ACP-0001", "AP-ACP-0001", "DC-ACP-0001", "AD-ACP-0001", "PG-ACP-0001", "AHF-ACP-0001", "BA-ACP-0001"]}, start))

        start = monotonic_ms()
        failures = validate_profile_boundary(records) if records else ["records unavailable"]
        if failures:
            fatal_failures.extend(f"profile_boundary: {failure}" for failure in failures)
            phases.append(phase("profile_boundary", "fail", "Reusable core/profile boundary failed.", {"failures": failures}, start))
        else:
            phases.append(phase("profile_boundary", "pass", "law-nexus-specific proof boundaries are confined to ProfileConstraint.", {"profile_record": "PC-LN-0001"}, start))

        start = monotonic_ms()
        failures = validate_blocked_actions(records) if records else ["records unavailable"]
        if failures:
            fatal_failures.extend(f"blocked_actions: {failure}" for failure in failures)
            phases.append(phase("blocked_actions", "fail", "Blocked action semantics failed.", {"failures": failures}, start))
        else:
            phases.append(phase("blocked_actions", "pass", "Main-repo git-lex initialization remains explicitly blocked until separate proof and decision evidence exist.", {"blocked_record": "BA-ACP-0001", "blocked_surface": records["BA-ACP-0001"].get("surface")}, start))

    start = monotonic_ms()
    main_lex_after = MAIN_REPO_LEX_DIR.exists()
    if main_lex_after:
        fatal_failures.append("main repository .lex exists after proof harness execution")
        phases.append(phase("main_repo_mutation_guard", "fail", "Main repository .lex state exists; proof failed closed.", {"main_lex_before": main_lex_before, "main_lex_after": main_lex_after}, start))
    else:
        phases.append(phase("main_repo_mutation_guard", "pass", "No .lex state exists in the main repository before or after the harness run.", {"main_lex_before": main_lex_before, "main_lex_after": main_lex_after}, start))

    status = "fail" if fatal_failures else ("blocked" if blocked_or_deferred else "pass")
    result = {
        "harness": "m048-s04-git-lex-proof",
        "status": status,
        "check_mode": args.check,
        "root": str(ROOT),
        "duration_ms": monotonic_ms() - started_all,
        "phases": [phase_item.__dict__ for phase_item in phases],
        "fatal_failures": fatal_failures,
        "blocked_or_deferred": blocked_or_deferred,
        "observability": {
            "phase_statuses": [phase_item.name for phase_item in phases],
            "main_repo_mutation_checked": True,
            "runtime_telemetry_introduced": False,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.check and fatal_failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

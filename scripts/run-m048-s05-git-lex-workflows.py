#!/usr/bin/env python3
"""Run M048/S05 ACP git-lex workflow diagnostics.

The S05 harness is intentionally diagnostic-only. It consumes the S04 isolated
proof harness and fixture pack to report ACP workflow readiness without cloning,
installing, downloading, running `git lex init`, or creating durable git-lex
state in the main repository.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
S04_HARNESS_PATH = ROOT / "scripts/run-m048-s04-git-lex-proof.py"
MAIN_REPO_LEX_DIR = ROOT / ".lex"

WORKFLOW_IDS = [
    "runtime_acquisition_and_adoption",
    "typed_source_record_validation",
    "extraction_projection_query_recovery",
    "lifecycle_proof_gate_profile_boundary",
    "main_repo_mutation_guard",
]

NON_CLAIMS = [
    "does_not_claim_runtime_git_lex_available_when_help_probe_fails",
    "does_not_claim_full_acp_git_lex_adoption",
    "does_not_claim_product_readiness",
    "does_not_claim_parser_completeness",
    "does_not_claim_falkordb_ingestion",
    "does_not_claim_legal_correctness",
    "does_not_validate_R035",
    "does_not_validate_R037",
    "does_not_validate_R038",
    "does_not_promote_derived_projections_to_source_truth",
]

ALLOWED_ACTIONS_WHEN_BLOCKED = [
    "inspect_json_contract",
    "reuse_s04_deterministic_fixture_validators",
    "read_tracked_s04_fixture_records",
    "produce_non_authoritative_temporary_projection_diagnostics",
    "defer_runtime_git_lex_adoption_decision_until_acquisition_is_proven",
]

BLOCKED_ACTIONS = [
    "clone_git_lex_from_this_harness",
    "install_or_download_git_lex_from_this_harness",
    "run_git_lex_init_in_main_repository",
    "create_or_mutate_main_repository_dot_lex_state",
    "claim_full_acp_runtime_adoption_from_fixture_only_evidence",
    "validate_R035_R037_R038_from_git_lex_projection_diagnostics",
    "treat_derived_projection_as_source_truth",
]


class ContractError(RuntimeError):
    """Raised when the S05 JSON contract itself is malformed."""


def monotonic_ms() -> int:
    return int(time.monotonic() * 1000)


def load_s04_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("m048_s04_git_lex_proof", S04_HARNESS_PATH)
    if spec is None or spec.loader is None:
        raise ContractError(f"could not load S04 harness from {S04_HARNESS_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def phase(name: str, status: str, summary: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "summary": summary,
        "details": details or {},
    }


def workflow(
    workflow_id: str,
    title: str,
    status: str,
    phases: list[dict[str, Any]],
    *,
    blocked_or_deferred_reason: str | None = None,
    allowed_actions: list[str] | None = None,
    blocked_actions: list[str] | None = None,
    non_claims: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": workflow_id,
        "title": title,
        "status": status,
        "phases": phases,
        "blocked_or_deferred_reason": blocked_or_deferred_reason,
        "allowed_actions": allowed_actions or [],
        "blocked_actions": blocked_actions or [],
        "non_claims": non_claims or [],
    }


def probe_runtime(s04: ModuleType) -> tuple[bool, list[dict[str, Any]]]:
    probes = [
        s04.run_probe(["git", "lex", "--help"], ROOT),
        s04.run_probe(["git-lex", "--help"], ROOT),
    ]
    available = any(probe.get("exit_code") == 0 and not probe.get("timed_out") for probe in probes)
    return available, probes


def deterministic_mechanics(s04: ModuleType) -> tuple[dict[str, Any], list[str]]:
    records = s04.load_records(s04.FIXTURE_DIR)
    failures: list[str] = []
    failures.extend(f"validation: {failure}" for failure in s04.validate_records(records))

    projection = s04.acp_projection(records)
    if projection.get("authority_status") != "non_authoritative":
        failures.append("projection: derived projection must remain non_authoritative")

    by_kind = {item["record_kind"]: item["id"] for item in projection.get("records", [])}
    if by_kind.get("architecture_decision") != "AD-ACP-0001":
        failures.append("query_recovery: architecture decision AD-ACP-0001 was not recovered")
    if "EA-ACP-0001" not in projection.get("edges", {}).get("PG-ACP-0001", []):
        failures.append("query_recovery: proof gate evidence edge EA-ACP-0001 was not recovered")

    failures.extend(f"lifecycle_proof_gate: {failure}" for failure in s04.validate_lifecycle(records))
    failures.extend(f"profile_boundary: {failure}" for failure in s04.validate_profile_boundary(records))
    failures.extend(f"blocked_actions: {failure}" for failure in s04.validate_blocked_actions(records))

    diagnostics = {
        "record_count": len(records),
        "record_ids": sorted(records),
        "projection_kind": projection.get("projection_kind"),
        "projection_authority_status": projection.get("authority_status"),
        "recovered_architecture_decision": by_kind.get("architecture_decision"),
        "proof_gate_edges": projection.get("edges", {}).get("PG-ACP-0001", []),
        "proof_gate_status": records.get("PG-ACP-0001", {}).get("status"),
        "profile_record": "PC-LN-0001" if "PC-LN-0001" in records else None,
        "blocked_record": "BA-ACP-0001" if "BA-ACP-0001" in records else None,
    }
    return diagnostics, failures


def build_contract() -> dict[str, Any]:
    started = monotonic_ms()
    fatal_failures: list[str] = []
    blocked_or_deferred: list[str] = []
    workflows: list[dict[str, Any]] = []

    main_repo_lex_before = MAIN_REPO_LEX_DIR.exists()
    if main_repo_lex_before:
        fatal_failures.append("main repository .lex exists before S05 workflow diagnostics")

    try:
        s04 = load_s04_harness()
    except Exception as exc:  # noqa: BLE001 - diagnostics must be machine-readable.
        s04 = None
        fatal_failures.append(f"s04_harness_load: {exc}")

    runtime_available = False
    runtime_probes: list[dict[str, Any]] = []
    if s04 is not None:
        try:
            runtime_available, runtime_probes = probe_runtime(s04)
        except Exception as exc:  # noqa: BLE001
            fatal_failures.append(f"runtime_probe: {exc}")

    runtime_reason = None
    runtime_status = "pass" if runtime_available else "blocked"
    if not runtime_available:
        runtime_reason = "git-lex executable unavailable; runtime acquisition and adoption are deferred while deterministic ACP mechanics remain inspectable"
        blocked_or_deferred.append(runtime_reason)

    workflows.append(workflow(
        "runtime_acquisition_and_adoption",
        "Runtime acquisition and adoption",
        runtime_status,
        [phase(
            "runtime_help_probe",
            runtime_status,
            "Existing git-lex command responded to a help probe." if runtime_available else "No existing git-lex executable responded; acquisition is intentionally not attempted.",
            {
                "probes": runtime_probes,
                "safe_acquisition_policy": "no clone/install/download/durable build/git-lex-init from law-nexus",
            },
        )],
        blocked_or_deferred_reason=runtime_reason,
        allowed_actions=ALLOWED_ACTIONS_WHEN_BLOCKED,
        blocked_actions=BLOCKED_ACTIONS,
        non_claims=[
            "does_not_claim_runtime_git_lex_available_when_help_probe_fails",
            "does_not_claim_full_acp_git_lex_adoption",
        ],
    ))

    deterministic: dict[str, Any] = {}
    mechanics_failures: list[str] = []
    if s04 is not None:
        try:
            deterministic, mechanics_failures = deterministic_mechanics(s04)
        except Exception as exc:  # noqa: BLE001
            mechanics_failures = [f"deterministic_mechanics: {exc}"]
    else:
        mechanics_failures = ["deterministic_mechanics: S04 harness unavailable"]

    if mechanics_failures:
        fatal_failures.extend(mechanics_failures)

    mechanics_status = "fail" if mechanics_failures else "pass"
    workflows.extend([
        workflow(
            "typed_source_record_validation",
            "Typed source-record validation",
            mechanics_status,
            [phase(
                "s04_validate_records",
                mechanics_status,
                "S04 source-record taxonomy, relationship, safety flag, and anchor checks passed." if not mechanics_failures else "S04 source-record validation or related deterministic mechanics failed.",
                {"record_count": deterministic.get("record_count"), "record_ids": deterministic.get("record_ids"), "failures": mechanics_failures},
            )],
            non_claims=["does_not_validate_R035", "does_not_validate_R037", "does_not_validate_R038"],
        ),
        workflow(
            "extraction_projection_query_recovery",
            "Extraction projection and query recovery",
            mechanics_status,
            [
                phase(
                    "s04_acp_projection",
                    mechanics_status,
                    "S04 projection remains deterministic and non-authoritative." if not mechanics_failures else "Projection diagnostics failed with S04 deterministic mechanics.",
                    {
                        "projection_kind": deterministic.get("projection_kind"),
                        "authority_status": deterministic.get("projection_authority_status"),
                        "failures": mechanics_failures,
                    },
                ),
                phase(
                    "s04_query_recovery",
                    mechanics_status,
                    "Recovered architecture decision and proof-gate evidence edge from the derived projection." if not mechanics_failures else "Query recovery failed with S04 deterministic mechanics.",
                    {
                        "architecture_decision": deterministic.get("recovered_architecture_decision"),
                        "proof_gate_edges": deterministic.get("proof_gate_edges"),
                        "failures": mechanics_failures,
                    },
                ),
            ],
            non_claims=["does_not_promote_derived_projections_to_source_truth"],
        ),
        workflow(
            "lifecycle_proof_gate_profile_boundary",
            "Lifecycle proof-gate and profile boundary",
            mechanics_status,
            [phase(
                "s04_lifecycle_profile_blocked_actions",
                mechanics_status,
                "S04 lifecycle, pending proof-gate, law-nexus profile boundary, and blocked action checks passed." if not mechanics_failures else "Lifecycle/profile/blocked-action diagnostics failed.",
                {
                    "proof_gate_status": deterministic.get("proof_gate_status"),
                    "profile_record": deterministic.get("profile_record"),
                    "blocked_record": deterministic.get("blocked_record"),
                    "failures": mechanics_failures,
                },
            )],
            non_claims=["does_not_claim_product_readiness", "does_not_claim_full_acp_git_lex_adoption"],
        ),
    ])

    main_repo_lex_after = MAIN_REPO_LEX_DIR.exists()
    if main_repo_lex_after:
        fatal_failures.append("main repository .lex exists after S05 workflow diagnostics")
    guard_status = "fail" if main_repo_lex_before or main_repo_lex_after else "pass"
    workflows.append(workflow(
        "main_repo_mutation_guard",
        "Main-repo mutation guard",
        guard_status,
        [phase(
            "main_repo_dot_lex_guard",
            guard_status,
            "No main-repo .lex state exists before or after S05 workflow diagnostics." if guard_status == "pass" else "Main-repo .lex state exists; S05 fails closed.",
            {"main_lex_before": main_repo_lex_before, "main_lex_after": main_repo_lex_after},
        )],
        blocked_actions=["run_git_lex_init_in_main_repository", "create_or_mutate_main_repository_dot_lex_state"],
    ))

    phase_statuses = {
        phase_item["name"]: phase_item["status"]
        for workflow_item in workflows
        for phase_item in workflow_item["phases"]
    }
    workflow_statuses = {workflow_item["id"]: workflow_item["status"] for workflow_item in workflows}
    status = "fail" if fatal_failures else ("blocked" if blocked_or_deferred else "pass")
    adoption_recommendation = (
        "defer_runtime_adoption_keep_deterministic_acp_mechanics_only"
        if blocked_or_deferred
        else "partial_adoption_requires_separate_runtime_git_lex_proof_before_full_adoption"
    )

    contract = {
        "harness": "m048-s05-git-lex-workflows",
        "status": status,
        "duration_ms": monotonic_ms() - started,
        "workflow_ids": WORKFLOW_IDS,
        "workflow_statuses": workflow_statuses,
        "phase_statuses": phase_statuses,
        "workflows": workflows,
        "blocked_or_deferred": blocked_or_deferred,
        "blocked_or_deferred_reason": "; ".join(blocked_or_deferred) if blocked_or_deferred else None,
        "adoption_recommendation": adoption_recommendation,
        "allowed_actions": ALLOWED_ACTIONS_WHEN_BLOCKED,
        "blocked_actions": BLOCKED_ACTIONS,
        "non_claims": NON_CLAIMS,
        "source_projection_boundary": {
            "source_truth": "tracked S04 fixture source records and evidence anchors",
            "derived_projection": "temporary deterministic non-authoritative diagnostic projection",
            "projection_may_validate_requirements": False,
            "projection_may_override_source_records": False,
        },
        "requirement_boundary": {
            "R035": "not_validated_by_s05_git_lex_workflow_diagnostics",
            "R037": "not_validated_by_s05_git_lex_workflow_diagnostics",
            "R038": "not_validated_by_s05_git_lex_workflow_diagnostics",
        },
        "main_repo_lex_exists": main_repo_lex_after,
        "mutation_guard": {
            "checked": True,
            "main_lex_before": main_repo_lex_before,
            "main_lex_after": main_repo_lex_after,
            "safe": guard_status == "pass",
        },
        "fatal_failures": fatal_failures,
    }
    validate_contract(contract)
    return contract


def validate_contract(contract: dict[str, Any]) -> None:
    missing_workflows = sorted(set(WORKFLOW_IDS) - set(contract.get("workflow_statuses", {})))
    if missing_workflows:
        raise ContractError(f"missing workflow diagnostics: {missing_workflows}")
    if contract.get("source_projection_boundary", {}).get("projection_may_validate_requirements") is not False:
        raise ContractError("derived projection must not validate requirements")
    if contract.get("source_projection_boundary", {}).get("projection_may_override_source_records") is not False:
        raise ContractError("derived projection must not override source records")
    requirement_boundary = contract.get("requirement_boundary", {})
    for requirement_id in ["R035", "R037", "R038"]:
        if requirement_boundary.get(requirement_id) != "not_validated_by_s05_git_lex_workflow_diagnostics":
            raise ContractError(f"{requirement_id} must remain not validated by S05")
    if "does_not_claim_full_acp_git_lex_adoption" not in contract.get("non_claims", []):
        raise ContractError("contract must include full-adoption non-claim")
    if "treat_derived_projection_as_source_truth" not in contract.get("blocked_actions", []):
        raise ContractError("contract must block source/projection confusion")
    if contract.get("main_repo_lex_exists") is True and not contract.get("fatal_failures"):
        raise ContractError("main-repo .lex must be fatal when present")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Return non-zero only for unsafe mutation or malformed deterministic contract.")
    args = parser.parse_args()

    try:
        contract = build_contract()
    except ContractError as exc:
        contract = {
            "harness": "m048-s05-git-lex-workflows",
            "status": "fail",
            "fatal_failures": [f"contract: {exc}"],
            "main_repo_lex_exists": MAIN_REPO_LEX_DIR.exists(),
        }
    print(json.dumps(contract, indent=2, sort_keys=True))
    if args.check and contract.get("fatal_failures"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

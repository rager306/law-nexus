#!/usr/bin/env python3
"""Detect GSD sync drift for the R035 active/unmapped contradiction class.

This check is intentionally read-only. It compares the S02 drift contract and
R035 evidence audit against current derived architecture registry/view artifacts
and verifier policy text. It does not validate, repair, synchronize, or update
R035 lifecycle state.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "prd/research/ontology_architecture_requirements/06-r035-evidence-audit.md"
CONTRACT_PATH = ROOT / "prd/research/ontology_architecture_requirements/07-gsd-sync-drift-contract.md"
INTEGRATION_PLAN_PATH = ROOT / "prd/research/ontology_architecture_requirements/05-registry-integration-plan.md"
ARCHITECTURE_ITEMS_PATH = ROOT / "prd/architecture/architecture_items.jsonl"
CLAIMS_LEDGER_PATH = ROOT / "prd/architecture/claims_ledger.md"
VERIFIER_PATH = ROOT / "scripts/verify-architecture-graph.py"

PLANNED_R035_CANDIDATE_IDS = (
    "EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO",
    "DATA-LEGAL-DOCUMENT-IDENTITY-FRBR",
    "DATA-LKIF-DEONTIC-MAPPING",
    "DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY",
    "DATA-LEGAL-SOURCE-HIERARCHY",
    "GATE-AKOMA-FRBR-NORMALIZATION",
    "GATE-DEONTIC-MAPPING-PROOF",
    "GATE-RUSLEGALCORE-SCOPE",
    "GATE-BFO-GOST-ALIGNMENT",
    "GATE-LEGAL-COLLISION-POLICY",
    "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION",
    "GATE-1000-DOC-PILOT",
)

KNOWN_GATE_ID_DRIFT_PAIRS = (
    ("GATE-DEONTIC-MAPPING-PROOF", "GATE-LKIF-DEONTIC-BENCHMARK"),
    ("GATE-1000-DOC-PILOT", "GATE-PILOT-SCALE-READINESS"),
)

CANONICAL_R035_CANDIDATE_ID_BY_ALIAS = dict(KNOWN_GATE_ID_DRIFT_PAIRS)
PLANNED_R035_CANONICAL_CANDIDATE_IDS = tuple(
    CANONICAL_R035_CANDIDATE_ID_BY_ALIAS.get(candidate_id, candidate_id)
    for candidate_id in PLANNED_R035_CANDIDATE_IDS
)

Status = Literal["ERROR", "OK"]


@dataclass(frozen=True)
class DiagnosticResult:
    diagnostic_id: str
    status: Status
    severity: str
    evidence_path: str
    remediation_owner: str
    remediation_hint: str
    message: str
    observed: str
    non_claim_boundary: str

    @property
    def failed(self) -> bool:
        return self.status == "ERROR"


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"unable to read {display_path(path)}: {exc}") from exc


def load_jsonl_records(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SystemExit(f"unable to read {display_path(path)}: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"malformed JSONL in {display_path(path)}:{line_number}: {exc}") from exc
        record_id = record.get("id")
        if isinstance(record_id, str) and record_id:
            records[record_id] = record
    return records


def load_jsonl_ids(path: Path) -> set[str]:
    return set(load_jsonl_records(path))


def has_alias_reconciliation_evidence(record: dict[str, Any] | None, planning_alias: str) -> bool:
    if not record:
        return False
    alias_tag = f"alias-{planning_alias}"
    tags = record.get("tags")
    if isinstance(tags, list) and alias_tag in tags:
        return True
    non_claims = record.get("non_claims")
    if isinstance(non_claims, list) and any(planning_alias in str(non_claim) for non_claim in non_claims):
        return True
    return False


def unresolved_candidate_ids(registry_records: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    missing_candidates: list[str] = []
    missing_alias_evidence: list[str] = []
    for candidate_id in PLANNED_R035_CANDIDATE_IDS:
        canonical_id = CANONICAL_R035_CANDIDATE_ID_BY_ALIAS.get(candidate_id, candidate_id)
        record = registry_records.get(canonical_id)
        if record is None:
            missing_candidates.append(candidate_id if canonical_id == candidate_id else f"{candidate_id}->{canonical_id}")
        elif canonical_id != candidate_id and not has_alias_reconciliation_evidence(record, candidate_id):
            missing_alias_evidence.append(f"{candidate_id}->{canonical_id}")
    return missing_candidates, missing_alias_evidence


def extract_required_gate_ids_from_verifier(verifier_text: str) -> set[str]:
    """Extract gate IDs from ONTOLOGY_PROMOTION_RULES without importing the verifier."""

    match = re.search(r"ONTOLOGY_PROMOTION_RULES:\s*tuple\[dict\[str, Any\], \.\.\.\]\s*=\s*(\(.*?\n\))\n\n", verifier_text, re.DOTALL)
    if not match:
        return set(re.findall(r'"(GATE-[A-Z0-9-]+)"', verifier_text))
    try:
        rules = ast.literal_eval(match.group(1))
    except (SyntaxError, ValueError):
        return set(re.findall(r'"(GATE-[A-Z0-9-]+)"', match.group(1)))
    gate_ids: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        required_gate_ids = rule.get("required_gate_ids")
        if not isinstance(required_gate_ids, tuple):
            continue
        gate_ids.update(gate_id for gate_id in required_gate_ids if isinstance(gate_id, str))
    return gate_ids


def r035_gate_status_section(claims_ledger_text: str) -> str:
    match = re.search(r"^## R035 Gate Status\n(?P<section>.*?)(?=^##\s|\Z)", claims_ledger_text, re.DOTALL | re.MULTILINE)
    return match.group("section") if match else ""


def unsafe_lifecycle_lines(paths_and_text: Iterable[tuple[Path, str]]) -> list[str]:
    unsafe_patterns = (
        re.compile(r"\bR035\b[^\n]*(?:validated|closed|satisfied)[^\n]*(?:because|from|by|after|due to)[^\n]*(?:M017|M018|milestone completion|completed milestone)", re.IGNORECASE),
        re.compile(r"(?:M017|M018|milestone completion|completed milestone)[^\n]*(?:validates|validated|closes|closed|satisfies|satisfied)[^\n]*\bR035\b", re.IGNORECASE),
    )
    safe_markers = (
        "does not claim",
        "does not validate",
        "does not prove",
        "not validated",
        "must stay active",
        "must not",
        "non-claim",
        "non_claim",
        "not evidence",
        "incomplete",
        "missing",
        "planned",
        "not represented",
        "drift visible",
    )
    findings: list[str] = []
    for path, text in paths_and_text:
        for line_number, line in enumerate(text.splitlines(), start=1):
            lower = line.lower()
            if any(marker in lower for marker in safe_markers):
                continue
            if any(pattern.search(line) for pattern in unsafe_patterns):
                findings.append(f"{display_path(path)}:{line_number}: {line.strip()}")
    return findings


def make_result(
    diagnostic_id: str,
    failed: bool,
    evidence_path: Path,
    remediation_owner: str,
    remediation_hint: str,
    failure_message: str,
    ok_message: str,
    observed: str,
    non_claim_boundary: str,
) -> DiagnosticResult:
    return DiagnosticResult(
        diagnostic_id=diagnostic_id,
        status="ERROR" if failed else "OK",
        severity="error" if failed else "none",
        evidence_path=display_path(evidence_path),
        remediation_owner=remediation_owner,
        remediation_hint=remediation_hint,
        message=failure_message if failed else ok_message,
        observed=observed,
        non_claim_boundary=non_claim_boundary,
    )


def build_diagnostics() -> list[DiagnosticResult]:
    audit_text = read_text(AUDIT_PATH)
    contract_text = read_text(CONTRACT_PATH)
    integration_plan_text = read_text(INTEGRATION_PLAN_PATH)
    claims_ledger_text = read_text(CLAIMS_LEDGER_PATH)
    verifier_text = read_text(VERIFIER_PATH)
    registry_records = load_jsonl_records(ARCHITECTURE_ITEMS_PATH)
    registry_ids = set(registry_records)
    verifier_gate_ids = extract_required_gate_ids_from_verifier(verifier_text)

    missing_candidates, missing_alias_evidence = unresolved_candidate_ids(registry_records)
    alias_reconciliations = [
        f"{planned}->{policy}"
        for planned, policy in KNOWN_GATE_ID_DRIFT_PAIRS
        if has_alias_reconciliation_evidence(registry_records.get(policy), planned)
    ]
    gate_status_section = r035_gate_status_section(claims_ledger_text)
    gate_view_missing = [
        candidate_id
        for candidate_id in PLANNED_R035_CANDIDATE_IDS
        if CANONICAL_R035_CANDIDATE_ID_BY_ALIAS.get(candidate_id, candidate_id) not in gate_status_section
    ]
    r035_verifier_gate_ids = verifier_gate_ids.intersection(PLANNED_R035_CANONICAL_CANDIDATE_IDS)
    missing_verifier_gates = sorted(gate_id for gate_id in r035_verifier_gate_ids if gate_id not in registry_ids)
    drift_pairs = [
        f"{planned} vs {policy}"
        for planned, policy in KNOWN_GATE_ID_DRIFT_PAIRS
        if (
            planned in integration_plan_text
            and policy in verifier_text
            and planned not in verifier_text
            and not has_alias_reconciliation_evidence(registry_records.get(policy), planned)
        )
    ]
    unsafe_lines = unsafe_lifecycle_lines(
        (
            (AUDIT_PATH, audit_text),
            (CONTRACT_PATH, contract_text),
            (CLAIMS_LEDGER_PATH, claims_ledger_text),
        )
    )

    audit_says_active = bool(re.search(r"R035 remains \*\*Active / not validated\*\*", audit_text))
    audit_says_completed_prior_milestones = "M017 and M018" in audit_text and "do **not** prove" in audit_text
    explicit_followup_owner = bool(re.search(r"R035[^\n]*(?:owned by|owner:)\s*(?:M019|S03|in-progress)", audit_text, re.IGNORECASE))

    return [
        make_result(
            "DRIFT-R035-ACTIVE-UNOWNED",
            audit_says_active and audit_says_completed_prior_milestones and not explicit_followup_owner,
            AUDIT_PATH,
            "GSD planning / requirement lifecycle owner",
            "Assign explicit in-progress milestone/follow-up ownership or keep this drift visible until lifecycle state is reconciled.",
            "DRIFT-R035-ACTIVE-UNOWNED: R035 remains Active but is not visibly owned by an in-progress milestone or explicit follow-up owner.",
            "R035 active ownership is visibly reconciled.",
            "audit states R035 remains Active/not validated while M017/M018 completion is non-validation evidence; no explicit in-progress owner marker found",
            "Does not claim M017/M018 failed; only flags lifecycle ownership drift.",
        ),
        make_result(
            "DRIFT-R035-REGISTRY-MAPPING-ABSENT",
            bool(missing_candidates or missing_alias_evidence),
            ARCHITECTURE_ITEMS_PATH,
            "Extractor / registry integration owner",
            "Implement the deferred extractor mapping and regenerate derived registry artifacts; do not hand-edit JSONL.",
            "DRIFT-R035-REGISTRY-MAPPING-ABSENT: planned R035 ontology candidate IDs are absent from architecture_items.jsonl or lack explicit alias reconciliation evidence.",
            "All planned R035 ontology candidate IDs resolve to current registry items, including canonical verifier-policy aliases.",
            f"missing {len(missing_candidates)}/12 canonicalized candidates: {', '.join(missing_candidates) or 'none'}; missing alias evidence: {', '.join(missing_alias_evidence) or 'none'}; reconciled aliases: {', '.join(alias_reconciliations) or 'none'}",
            "Does not assert which mappings are correct; only detects absence of planned candidates in current derived registry.",
        ),
        make_result(
            "DRIFT-R035-MISSING-PROOF-GATE",
            "GATE-AKOMA-FRBR-NORMALIZATION" not in registry_ids,
            ARCHITECTURE_ITEMS_PATH,
            "Extractor / ontology proof-gate owner",
            "Generate GATE-AKOMA-FRBR-NORMALIZATION through the extractor before treating policy/source mentions as registry-backed proof.",
            "DRIFT-R035-MISSING-PROOF-GATE: required gate GATE-AKOMA-FRBR-NORMALIZATION is referenced by source/policy evidence but missing from architecture_items.jsonl.",
            "GATE-AKOMA-FRBR-NORMALIZATION resolves to a current registry item.",
            "GATE-AKOMA-FRBR-NORMALIZATION absent from current registry IDs",
            "Verifier-policy mentions are not proof that the gate exists or is satisfied.",
        ),
        make_result(
            "DRIFT-R035-STALE-GATE-VIEW",
            not gate_status_section or bool(gate_view_missing),
            CLAIMS_LEDGER_PATH,
            "Architecture view / claims-ledger regeneration owner",
            "Regenerate claims-ledger/view artifacts from registry outputs after extractor integration emits the planned candidates.",
            "DRIFT-R035-STALE-GATE-VIEW: claims_ledger.md has an R035 Gate Status section but does not enumerate the planned M017 ontology candidate set.",
            "R035 Gate Status enumerates the planned M017 ontology candidate set.",
            f"R035 Gate Status present={bool(gate_status_section)}; missing from view {len(gate_view_missing)}/12 canonicalized candidates: {', '.join(gate_view_missing)}",
            "Does not treat claims ledger as authoritative source evidence; it only checks view freshness against tracked source expectations.",
        ),
        make_result(
            "DRIFT-R035-POLICY-ENDPOINT-MISSING",
            bool(missing_verifier_gates),
            VERIFIER_PATH,
            "Verifier / registry integration owner",
            "Ensure verifier-policy gate IDs resolve to generated registry items or keep policy references classified as policy-only evidence.",
            "DRIFT-R035-POLICY-ENDPOINT-MISSING: ontology verifier policy names required gates that do not resolve to current registry items.",
            "All ontology verifier policy gate IDs resolve to current registry items.",
            f"missing verifier-policy gates: {', '.join(missing_verifier_gates)}",
            "Does not claim verifier policy is wrong; it prevents policy text from being counted as generated registry proof.",
        ),
        make_result(
            "DRIFT-R035-CANDIDATE-CURRENT-MISMATCH",
            bool(missing_candidates or missing_alias_evidence),
            INTEGRATION_PLAN_PATH,
            "Extractor / architecture registry owner",
            "Resolve the source-plan/current-registry mismatch by extractor implementation and regeneration, or keep R035 Active/unmapped.",
            "DRIFT-R035-CANDIDATE-CURRENT-MISMATCH: source plan lists 12 candidate items and 9 edge mapping classes, but current derived registry outputs do not contain the canonicalized candidate set with alias reconciliation evidence.",
            "Current derived registry contains the planned candidate set from the source plan using verifier-policy canonical IDs where aliases are explicitly reconciled.",
            f"source plan candidate count=12 edge mapping class count=9; canonical candidate count=12; current registry missing candidate count={len(missing_candidates)}; missing alias evidence count={len(missing_alias_evidence)}",
            "Does not validate candidate correctness, edge endpoints, source anchors, or proof levels.",
        ),
        make_result(
            "DRIFT-R035-GATE-ID-DRIFT",
            bool(drift_pairs),
            VERIFIER_PATH,
            "Ontology architecture / verifier owner",
            "Reconcile aliases or choose canonical gate IDs in source evidence before registry emission.",
            "DRIFT-R035-GATE-ID-DRIFT: planned gate IDs and verifier-policy gate IDs disagree and have not been reconciled as registry aliases or chosen canonical IDs.",
            "Known planned gate IDs and verifier-policy gate IDs are reconciled.",
            f"unreconciled pairs: {', '.join(drift_pairs) or 'none'}; alias reconciliation evidence present: {', '.join(alias_reconciliations) or 'none'}",
            "Does not choose canonical IDs; it only reports unresolved naming drift.",
        ),
        make_result(
            "DRIFT-R035-UNSAFE-LIFECYCLE-LANGUAGE",
            bool(unsafe_lines),
            AUDIT_PATH,
            "Requirement lifecycle / documentation owner",
            "Downgrade lifecycle wording so milestone completion is not presented as R035 validation without regenerated registry and verifier/view coverage.",
            "DRIFT-R035-UNSAFE-LIFECYCLE-LANGUAGE: lifecycle wording implies R035 validation from milestone completion without regenerated registry presence and verifier/view coverage.",
            "No unsafe lifecycle language was found in checked R035 audit/contract/view artifacts.",
            "; ".join(unsafe_lines) if unsafe_lines else "safe wording only in checked artifacts",
            "Does not block safe wording such as Active, not validated, planned, proposed, bounded evidence, or deferred proof.",
        ),
    ]


def emit_text(diagnostics: list[DiagnosticResult]) -> None:
    failed_count = sum(1 for diagnostic in diagnostics if diagnostic.failed)
    print("GSD sync drift check: R035 active/unmapped contradiction class")
    print(f"status={'DRIFT' if failed_count else 'OK'} diagnostics={len(diagnostics)} failed={failed_count}")
    print("non_claim=This check does not validate, synchronize, repair, or update R035 lifecycle state.")
    for diagnostic in diagnostics:
        print(
            f"{diagnostic.diagnostic_id} status={diagnostic.status} severity={diagnostic.severity} "
            f"evidence={diagnostic.evidence_path} owner={diagnostic.remediation_owner} "
            f"message={diagnostic.message} observed={diagnostic.observed} "
            f"remediation_hint={diagnostic.remediation_hint} non_claim_boundary={diagnostic.non_claim_boundary}"
        )


def emit_json(diagnostics: list[DiagnosticResult]) -> None:
    failed_count = sum(1 for diagnostic in diagnostics if diagnostic.failed)
    payload = {
        "check": "gsd-sync-drift-r035",
        "status": "DRIFT" if failed_count else "OK",
        "failed_count": failed_count,
        "non_claim": "This check does not validate, synchronize, repair, or update R035 lifecycle state.",
        "diagnostics": [diagnostic.__dict__ for diagnostic in diagnostics],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect R035 GSD sync drift without changing requirement state.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    parser.add_argument(
        "--strict-exit-code",
        action="store_true",
        help="Return exit code 1 when drift diagnostics fail; default keeps drift visible without failing the command.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    diagnostics = build_diagnostics()
    if args.format == "json":
        emit_json(diagnostics)
    else:
        emit_text(diagnostics)
    return 1 if args.strict_exit_code and any(diagnostic.failed for diagnostic in diagnostics) else 0


if __name__ == "__main__":
    raise SystemExit(main())

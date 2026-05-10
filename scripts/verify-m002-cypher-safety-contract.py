#!/usr/bin/env python3
"""Proof-only generated-Cypher safety validator for M002/S03.

This script intentionally performs local string/JSON checks only. It does not call
providers, FalkorDB, Graph.query, or Graph.ro_query; the contract reserves
Graph.ro_query for execute_validated after deterministic validation succeeds.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SUPPORTED_SCHEMA_VERSION = "m002-legalgraph-cypher-safety-contract/v1"
CONTRACT_REQUIRED_TERMS = (
    "Graph.ro_query",
    "read-only",
    "EvidenceSpan",
    "SourceBlock",
    "schema_version",
    "generate_only",
    "validate",
    "execute_validated",
    "LLM non-authoritative",
    "cypher_only",
    "text_to_cypher",
)
READBACK_UNSAFE_CASES: tuple[tuple[str, str], ...] = (
    ("E_CONTRACT_MALFORMED", "contract-readback"),
    ("E_SCHEMA_VERSION_UNKNOWN", "contract-readback"),
    ("E_CANDIDATE_FORMAT", "validation"),
    ("E_WRITE_OPERATION", "validation"),
    ("E_UNSUPPORTED_PROCEDURE", "validation"),
    ("E_UNKNOWN_LABEL", "validation"),
    ("E_UNKNOWN_RELATIONSHIP", "validation"),
    ("E_UNKNOWN_PROPERTY", "validation"),
    ("E_BAD_RELATIONSHIP_ENDPOINT", "validation"),
    ("E_UNBOUNDED_TRAVERSAL", "validation"),
    ("E_LIMIT_REQUIRED", "validation"),
    ("E_LIMIT_EXCEEDED", "validation"),
    ("E_EVIDENCE_REQUIRED", "validation"),
    ("E_TEMPORAL_REQUIRED", "validation"),
    ("E_NEO4J_ONLY_CARRYOVER", "validation"),
)
ACCEPTED_CASES: tuple[tuple[str, str], ...] = (
    (
        "accepted_article_evidence",
        """MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article)-[:SUPPORTED_BY]->(block:SourceBlock),
                  (span)-[:IN_BLOCK]->(block)
           WHERE article.id = $article_id
           RETURN article.id, span.id, block.id, block.source_id, span.start_offset, span.end_offset
           LIMIT 5""",
    ),
    (
        "accepted_citation_evidence",
        """MATCH (:Article {id:$source_article_id})-[:CITES]->(target:Article)<-[:HAS_ARTICLE]-(act:Act),
                  (span:EvidenceSpan)-[:SUPPORTS]->(target)-[:SUPPORTED_BY]->(block:SourceBlock),
                  (span)-[:IN_BLOCK]->(block)
           RETURN act.id, target.id, span.id, block.id
           LIMIT 5""",
    ),
    (
        "accepted_fulltext_sourceblock_evidence",
        """CALL db.idx.fulltext.queryNodes('SourceBlock', $search_terms) YIELD node, score
           MATCH (span:EvidenceSpan)-[:IN_BLOCK]->(node)<-[:SUPPORTED_BY]-(article:Article),
                 (span)-[:SUPPORTS]->(article)
           RETURN article.id, node.id, span.id, score
           LIMIT 5""",
    ),
)


@dataclass(frozen=True)
class ValidationDiagnostic:
    query_case: str
    schema_version: str
    failure_class: str
    rejection_code: str
    schema_policy_field: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    query_case: str
    accepted: bool
    normalized_query: str
    schema_version: str
    required_evidence_returns: list[str]
    max_limit: int
    rejection_codes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diagnostics: list[ValidationDiagnostic] = field(default_factory=list)


def normalize_query(candidate: str) -> str:
    """Collapse query whitespace for deterministic diagnostics and artifacts."""
    return re.sub(r"\s+", " ", candidate.strip())


def _diagnostic(
    contract: dict[str, Any],
    query_case: str,
    rejection_code: str,
    message: str,
) -> ValidationDiagnostic:
    codes = contract.get("rejection_codes", {}) if isinstance(contract, dict) else {}
    code_contract = codes.get(rejection_code, {}) if isinstance(codes, dict) else {}
    return ValidationDiagnostic(
        query_case=query_case,
        schema_version=str(contract.get("schema_version", "unknown")),
        failure_class=str(code_contract.get("failure_class", "validation")),
        rejection_code=rejection_code,
        schema_policy_field=str(code_contract.get("schema_policy_field", "unknown")),
        message=message,
    )


def reject(
    contract: dict[str, Any],
    query_case: str,
    candidate: object,
    rejection_code: str,
    message: str,
) -> ValidationReport:
    normalized = normalize_query(candidate) if isinstance(candidate, str) else ""
    diagnostic = _diagnostic(contract, query_case, rejection_code, message)
    return ValidationReport(
        query_case=query_case,
        accepted=False,
        normalized_query=normalized,
        schema_version=str(contract.get("schema_version", "unknown")),
        required_evidence_returns=required_evidence_returns(contract),
        max_limit=max_limit(contract),
        rejection_codes=[rejection_code],
        diagnostics=[diagnostic],
    )


def required_evidence_returns(contract: dict[str, Any]) -> list[str]:
    returns: list[str] = []
    for path in contract.get("required_evidence_paths", []):
        for field_name in path.get("required_return_fields", []):
            if field_name not in returns:
                returns.append(field_name)
    return returns


def max_limit(contract: dict[str, Any]) -> int:
    policy = contract.get("cypher_policy", {})
    value = policy.get("max_limit", 0)
    return int(value) if isinstance(value, int | float | str) and str(value).isdigit() else 0


def load_schema_contract(path: Path) -> dict[str, Any]:
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("E_CONTRACT_MALFORMED: schema/policy JSON cannot be read") from exc
    validate_schema_contract(contract)
    return contract


def validate_schema_contract(contract: dict[str, Any]) -> None:
    required_top_level = {
        "schema_version",
        "allowed_schema",
        "required_evidence_paths",
        "cypher_policy",
        "diagnostics_contract",
        "rejection_codes",
    }
    missing = sorted(required_top_level - contract.keys())
    if missing:
        raise ValueError(f"E_CONTRACT_MALFORMED: missing top-level keys {missing}")
    if contract.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise ValueError("E_SCHEMA_VERSION_UNKNOWN: unsupported schema_version")
    for code, failure_class in READBACK_UNSAFE_CASES:
        code_contract = contract.get("rejection_codes", {}).get(code)
        if not code_contract or code_contract.get("failure_class") != failure_class:
            raise ValueError(f"E_CONTRACT_MALFORMED: rejection code {code} is missing or malformed")


def contract_readback(contract_path: Path, schema_path: Path) -> dict[str, Any]:
    contract_text = contract_path.read_text(encoding="utf-8")
    missing_terms = [term for term in CONTRACT_REQUIRED_TERMS if term not in contract_text]
    schema = load_schema_contract(schema_path)
    return {
        "accepted": not missing_terms,
        "schema_version": schema["schema_version"],
        "missing_terms": missing_terms,
        "required_terms": list(CONTRACT_REQUIRED_TERMS),
        "failure_class": "contract-readback" if missing_terms else "none",
        "rejection_code": "E_CONTRACT_MALFORMED" if missing_terms else "none",
    }


def _word_pattern(term: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Z_]){re.escape(term)}(?![A-Z_])", re.IGNORECASE)


def _extract_variable_labels(query: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for match in re.finditer(r"\(\s*([A-Za-z_][A-Za-z0-9_]*)?\s*:\s*([A-Za-z_][A-Za-z0-9_]*)", query):
        variable = match.group(1)
        label = match.group(2)
        if variable:
            labels[variable] = label
    for match in re.finditer(r"CALL\s+db\.idx\.fulltext\.queryNodes\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]", query, re.IGNORECASE):
        labels.setdefault("node", match.group(1))
    return labels


def _extract_labels(query: str) -> set[str]:
    return set(_extract_variable_labels(query).values()) | {
        match.group(1)
        for match in re.finditer(r"\(\s*:\s*([A-Za-z_][A-Za-z0-9_]*)", query)
    }


def _extract_relationships(
    query: str, variable_labels: dict[str, str] | None = None
) -> list[tuple[str | None, str, str | None, str]]:
    labels_by_variable = variable_labels or {}
    relationships: list[tuple[str | None, str, str | None, str]] = []
    forward = re.compile(
        r"\(\s*(?P<left_var>[A-Za-z_][A-Za-z0-9_]*)?\s*(?::\s*(?P<left_label>[A-Za-z_][A-Za-z0-9_]*))?[^)]*\)\s*"
        r"-\s*\[:\s*(?P<rel>[A-Za-z_][A-Za-z0-9_]*)(?P<depth>\*[^\]]*)?\]\s*->\s*"
        r"\(\s*(?P<right_var>[A-Za-z_][A-Za-z0-9_]*)?\s*(?::\s*(?P<right_label>[A-Za-z_][A-Za-z0-9_]*))?[^)]*\)",
        re.DOTALL,
    )
    reverse = re.compile(
        r"\(\s*(?P<left_var>[A-Za-z_][A-Za-z0-9_]*)?\s*(?::\s*(?P<left_label>[A-Za-z_][A-Za-z0-9_]*))?[^)]*\)\s*"
        r"<-\s*\[:\s*(?P<rel>[A-Za-z_][A-Za-z0-9_]*)(?P<depth>\*[^\]]*)?\]\s*-\s*"
        r"\(\s*(?P<right_var>[A-Za-z_][A-Za-z0-9_]*)?\s*(?::\s*(?P<right_label>[A-Za-z_][A-Za-z0-9_]*))?[^)]*\)",
        re.DOTALL,
    )
    for pattern, direction in ((forward, "forward"), (reverse, "reverse")):
        for match in pattern.finditer(query):
            left_label = match.group("left_label") or labels_by_variable.get(match.group("left_var") or "")
            right_label = match.group("right_label") or labels_by_variable.get(match.group("right_var") or "")
            if direction == "forward":
                relationships.append((left_label, match.group("rel"), right_label, match.group("depth") or ""))
            else:
                relationships.append((right_label, match.group("rel"), left_label, match.group("depth") or ""))
    return relationships


def _extract_relationship_types(query: str) -> set[str]:
    return set(re.findall(r"\[:\s*([A-Za-z_][A-Za-z0-9_]*)", query))


def _extract_properties(query: str) -> list[tuple[str, str]]:
    properties: list[tuple[str, str]] = []
    for variable, property_name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b", query):
        if variable.upper() not in {"DB"}:
            properties.append((variable, property_name))
    return properties


def _limit_values(query: str) -> list[int]:
    return [int(value) for value in re.findall(r"\bLIMIT\s+(\d+)\b", query, re.IGNORECASE)]


def _procedure_names(query: str) -> list[str]:
    return re.findall(r"\bCALL\s+([A-Za-z_][A-Za-z0-9_.]*)", query, re.IGNORECASE)


def _has_unbounded_scan(query: str, variable_labels: dict[str, str]) -> bool:
    for variable in re.findall(r"MATCH\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", query, re.IGNORECASE):
        if variable not in variable_labels:
            return True
    return bool(re.search(r"RETURN\s+\*", query, re.IGNORECASE))


def _has_excessive_traversal(depth_expression: str, policy: dict[str, Any]) -> bool:
    if not depth_expression:
        return False
    max_depth = int(policy.get("max_traversal_depth", 0))
    if depth_expression == "*":
        return True
    numbers = [int(value) for value in re.findall(r"\d+", depth_expression)]
    return not numbers or max(numbers) > max_depth


def _relationship_endpoint_allowed(
    allowed_relationship: dict[str, Any],
    from_label: str | None,
    to_label: str | None,
) -> bool:
    if from_label is None or to_label is None:
        return True
    endpoints = allowed_relationship.get("allowed_endpoints", [])
    return any(item.get("from") == from_label and item.get("to") == to_label for item in endpoints)


def _query_returns_required_evidence(query: str, variable_labels: dict[str, str]) -> bool:
    required_labels = {"Article", "EvidenceSpan", "SourceBlock"}
    if not required_labels.issubset(set(variable_labels.values())):
        return False
    relationships = _extract_relationship_types(query)
    if not {"SUPPORTS", "SUPPORTED_BY", "IN_BLOCK"}.issubset(relationships):
        return False
    return_clause_match = re.search(r"\bRETURN\b(?P<return>.+?)\bLIMIT\b", query, re.IGNORECASE | re.DOTALL)
    if return_clause_match is None:
        return False
    return_clause = return_clause_match.group("return")
    labels_returned = set()
    for variable, property_name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\.(id)\b", return_clause):
        label = variable_labels.get(variable)
        if property_name == "id" and label in required_labels:
            labels_returned.add(label)
    return required_labels.issubset(labels_returned)


def _requires_temporal_filter(query: str, request_context: dict[str, Any] | None) -> bool:
    return bool(request_context and request_context.get("as_of") and "Article" in _extract_labels(query))


def _has_temporal_filter(query: str) -> bool:
    normalized = normalize_query(query).lower().replace(" ", "")
    return "valid_from<=$as_of" in normalized and "$as_of<" in normalized and "valid_to" in normalized


def validate_candidate(
    candidate: object,
    contract: dict[str, Any],
    *,
    query_case: str = "candidate",
    request_context: dict[str, Any] | None = None,
) -> ValidationReport:
    """Validate generated Cypher text against the local proof-only contract."""
    try:
        validate_schema_contract(contract)
    except ValueError as exc:
        code = str(exc).split(":", maxsplit=1)[0]
        return reject(contract, query_case, candidate, code, str(exc))

    if not isinstance(candidate, str) or not candidate.strip():
        return reject(contract, query_case, candidate, "E_CANDIDATE_FORMAT", "candidate is empty or not a string")

    query = candidate.strip()
    normalized = normalize_query(query)
    policy = contract["cypher_policy"]

    for clause in policy.get("forbidden_clauses", []):
        if _word_pattern(clause).search(normalized):
            return reject(contract, query_case, query, "E_WRITE_OPERATION", f"forbidden clause {clause} is not read-only")

    forbidden_tokens = policy.get("forbidden_tokens", [])
    if any(token in query for token in forbidden_tokens):
        return reject(contract, query_case, query, "E_CANDIDATE_FORMAT", "candidate contains forbidden formatting, comments, or multi-statement token")
    if not re.match(r"^(MATCH|CALL)\b", normalized, re.IGNORECASE):
        return reject(contract, query_case, query, "E_CANDIDATE_FORMAT", "candidate must start with MATCH or CALL")

    procedures = _procedure_names(normalized)
    allowed_procedures = set(policy.get("allowed_procedures", []))
    for procedure in procedures:
        if procedure in allowed_procedures:
            continue
        if procedure.startswith(("gds.", "apoc.")) or procedure in set(policy.get("forbidden_procedures", [])):
            return reject(contract, query_case, query, "E_NEO4J_ONLY_CARRYOVER", f"procedure {procedure} is Neo4j/APOC/GDS carryover")
        return reject(contract, query_case, query, "E_UNSUPPORTED_PROCEDURE", f"procedure {procedure} is not allowlisted")

    allowed_schema = contract["allowed_schema"]
    allowed_labels = set(allowed_schema["labels"])
    variable_labels = _extract_variable_labels(query)
    for label in _extract_labels(query):
        if label not in allowed_labels:
            return reject(contract, query_case, query, "E_UNKNOWN_LABEL", f"label {label} is not in allowed_schema.labels")

    allowed_relationships = allowed_schema["relationships"]
    for from_label, relationship, to_label, depth_expression in _extract_relationships(query, variable_labels):
        if relationship not in allowed_relationships:
            return reject(contract, query_case, query, "E_UNKNOWN_RELATIONSHIP", f"relationship {relationship} is not in allowed_schema.relationships")
        if _has_excessive_traversal(depth_expression, policy):
            return reject(contract, query_case, query, "E_UNBOUNDED_TRAVERSAL", f"relationship {relationship}{depth_expression} exceeds max traversal depth")
        if not _relationship_endpoint_allowed(allowed_relationships[relationship], from_label, to_label):
            return reject(contract, query_case, query, "E_BAD_RELATIONSHIP_ENDPOINT", f"relationship {relationship} endpoint {from_label}->{to_label} is not allowed")

    if _has_unbounded_scan(query, variable_labels):
        return reject(contract, query_case, query, "E_UNBOUNDED_TRAVERSAL", "query performs an unbounded node scan or RETURN *")

    for variable, property_name in _extract_properties(query):
        label = variable_labels.get(variable)
        if label is None:
            continue
        if label not in allowed_schema["labels"]:
            return reject(contract, query_case, query, "E_UNKNOWN_LABEL", f"label {label} is not in allowed_schema.labels")
        properties = set(allowed_schema["labels"][label].get("properties", []))
        if property_name not in properties:
            return reject(contract, query_case, query, "E_UNKNOWN_PROPERTY", f"property {label}.{property_name} is not allowed")
        returnable = set(allowed_schema["labels"][label].get("returnable_properties", []))
        non_returnable = set(allowed_schema["labels"][label].get("non_returnable_properties", []))
        if property_name in non_returnable or (property_name in properties and property_name not in returnable):
            return reject(contract, query_case, query, "E_UNKNOWN_PROPERTY", f"property {label}.{property_name} is not returnable under redaction policy")

    limits = _limit_values(query)
    if policy.get("requires_limit") and not limits:
        return reject(contract, query_case, query, "E_LIMIT_REQUIRED", "query omits required LIMIT")
    policy_max_limit = max_limit(contract)
    if any(limit > policy_max_limit for limit in limits):
        return reject(contract, query_case, query, "E_LIMIT_EXCEEDED", f"LIMIT exceeds max_limit {policy_max_limit}")

    if _requires_temporal_filter(query, request_context) and not _has_temporal_filter(query):
        return reject(contract, query_case, query, "E_TEMPORAL_REQUIRED", "as_of context requires Article valid_from/valid_to predicates")

    labels_in_query = set(variable_labels.values())
    if labels_in_query & {"Article", "EvidenceSpan", "SourceBlock"} and not _query_returns_required_evidence(query, variable_labels):
        return reject(contract, query_case, query, "E_EVIDENCE_REQUIRED", "answer query omits required EvidenceSpan/SourceBlock path or returns")

    warnings: list[str] = []
    if procedures:
        warnings.append("procedure allowlist used: read-only full-text proof shape only")
    return ValidationReport(
        query_case=query_case,
        accepted=True,
        normalized_query=normalized,
        schema_version=str(contract["schema_version"]),
        required_evidence_returns=required_evidence_returns(contract),
        max_limit=policy_max_limit,
        warnings=warnings,
    )


def evaluate_contract(contract_path: Path, schema_path: Path) -> dict[str, Any]:
    schema = load_schema_contract(schema_path)
    readback = contract_readback(contract_path, schema_path)
    accepted_reports = [
        validate_candidate(query, schema, query_case=query_case) for query_case, query in ACCEPTED_CASES
    ]
    unsafe_reports = [
        validate_candidate(item["cypher"], schema, query_case=item["name"])
        for item in schema.get("unsafe_examples", [])
    ]
    unsafe_expectations = [
        {
            "query_case": item["name"],
            "expected_rejection_code": item["expected_rejection_code"],
            "observed_rejection_codes": report.rejection_codes,
            "accepted": report.accepted,
            "passed": (not report.accepted)
            and item["expected_rejection_code"] in report.rejection_codes,
        }
        for item, report in zip(schema.get("unsafe_examples", []), unsafe_reports, strict=True)
    ]
    status = "pass" if readback["accepted"] and all(r.accepted for r in accepted_reports) and all(e["passed"] for e in unsafe_expectations) else "fail"
    return {
        "schema_version": schema["schema_version"],
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "execution_boundary": "No provider calls, FalkorDB network calls, Graph.query, or Graph.ro_query execution. Graph.ro_query is named only as the execute_validated read-only backstop.",
        "contract_readback": readback,
        "accepted_reports": [asdict(report) for report in accepted_reports],
        "unsafe_expectations": unsafe_expectations,
        "unsafe_reports": [asdict(report) for report in unsafe_reports],
        "required_evidence_returns": required_evidence_returns(schema),
        "max_limit": max_limit(schema),
        "redaction": "Artifacts contain normalized synthetic Cypher diagnostics only; no credentials, provider metadata values, or raw legal text.",
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# M002 Cypher Safety Verification",
        "",
        f"- status: `{payload['status']}`",
        f"- schema_version: `{payload['schema_version']}`",
        f"- max_limit: `{payload['max_limit']}`",
        "- execution: proof-only local validation; no Graph.query, no provider calls, no FalkorDB network calls; `Graph.ro_query` remains the `execute_validated` read-only backstop.",
        "- LLM non-authoritative: generated Cypher is candidate text only until deterministic validation and evidence verification pass.",
        "",
        "## Contract readback",
        "",
        f"- accepted: `{payload['contract_readback']['accepted']}`",
        f"- missing terms: `{payload['contract_readback']['missing_terms']}`",
        "",
        "## Accepted cases",
        "",
    ]
    for report in payload["accepted_reports"]:
        lines.append(f"- `{report['query_case']}` accepted={report['accepted']} warnings={report['warnings']}")
    lines.extend(["", "## Rejected unsafe cases", ""])
    for expectation in payload["unsafe_expectations"]:
        lines.append(
            f"- `{expectation['query_case']}` expected={expectation['expected_rejection_code']} "
            f"observed={expectation['observed_rejection_codes']} passed={expectation['passed']}"
        )
    lines.extend(["", "## Required evidence returns", ""])
    for field_name in payload["required_evidence_returns"]:
        lines.append(f"- `{field_name}`")
    lines.extend(["", "## Redaction", "", payload["redaction"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--write-artifact", type=Path)
    parser.add_argument("--write-markdown", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = evaluate_contract(args.contract, args.schema)
    if args.write_artifact:
        write_json(args.write_artifact, payload)
    if args.write_markdown:
        write_markdown(args.write_markdown, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

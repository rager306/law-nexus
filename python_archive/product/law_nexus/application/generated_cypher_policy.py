"""Generated-Cypher safety policy.

[bounded] M076 S16 package policy for deterministic pre-execution checks. The
policy validates candidate Cypher text against a local schema contract only; it
does not call providers, FalkorDB, Graph.query, Graph.ro_query, or prove query
correctness/runtime safety.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from law_nexus.ports.graph_store import GraphStoreQuery

SUPPORTED_SCHEMA_VERSION = "m002-legalgraph-cypher-safety-contract/v1"

GENERATED_CYPHER_POLICY_NON_CLAIMS: tuple[str, ...] = (
    "Does not prove FalkorDB runtime safety.",
    "Does not prove OpenCypher completeness.",
    "Does not prove generated query correctness.",
    "Does not prove legal-answer correctness.",
    "Does not prove parser completeness.",
    "Does not prove retrieval quality.",
    "Does not execute Graph.query or Graph.ro_query.",
    "Does not make LLM output authoritative.",
)

_FORBIDDEN_CONTEXT_KEYS = frozenset(
    {
        "raw_legal_text",
        "raw_text",
        "source_excerpt",
        "source_excerpts",
        "prompt",
        "user_prompt",
        "provider_payload",
        "provider_response_body",
        "generated_answer_prose",
        "secret",
        "token",
    }
)


@dataclass(frozen=True)
class GeneratedCypherDiagnostic:
    """Safe policy diagnostic."""

    code: str
    message: str
    query_case: str
    schema_policy_field: str = "cypher_policy"
    failure_class: str = "validation"

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "query_case": self.query_case,
            "schema_policy_field": self.schema_policy_field,
            "failure_class": self.failure_class,
        }


@dataclass(frozen=True)
class GeneratedCypherValidationRequest:
    """Input for generated-Cypher policy validation."""

    query: object
    schema_contract: Mapping[str, Any]
    query_case: str = "candidate"
    generated: bool = False
    request_context: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class GeneratedCypherValidationResult:
    """Bounded validation result."""

    query_case: str
    accepted: bool
    normalized_query: str
    schema_version: str
    required_evidence_returns: tuple[str, ...]
    max_limit: int
    rejection_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    diagnostics: tuple[GeneratedCypherDiagnostic, ...] = ()
    generated: bool = True
    non_authoritative: bool = True
    non_claims: tuple[str, ...] = GENERATED_CYPHER_POLICY_NON_CLAIMS

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_case": self.query_case,
            "accepted": self.accepted,
            "normalized_query": self.normalized_query,
            "schema_version": self.schema_version,
            "required_evidence_returns": list(self.required_evidence_returns),
            "max_limit": self.max_limit,
            "rejection_codes": list(self.rejection_codes),
            "warnings": list(self.warnings),
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "generated": self.generated,
            "non_authoritative": self.non_authoritative,
            "non_claims": list(self.non_claims),
        }

    def to_graph_store_query(self) -> GraphStoreQuery | None:
        """Return a GraphStoreQuery only when validation accepted the query."""

        if not self.accepted:
            return None
        return GraphStoreQuery(
            cypher=self.normalized_query,
            read_only=True,
            generated=self.generated,
            purpose="generated-cypher-policy-approved",
        )


class GeneratedCypherPolicy:
    """Validate candidate Cypher before any graph execution path."""

    def validate(
        self, request: GeneratedCypherValidationRequest
    ) -> GeneratedCypherValidationResult:
        contract = dict(request.schema_contract)
        try:
            _validate_contract(contract)
        except ValueError as exc:
            code = str(exc).split(":", maxsplit=1)[0]
            return _reject(contract, request, code, str(exc), "")

        if unsafe_key := _unsafe_context_key(request.request_context):
            return _reject(
                contract,
                request,
                "E_UNSAFE_CONTEXT_FIELD",
                f"unsafe request context key: {unsafe_key}",
                request.query,
            )
        if request.generated:
            return _reject(
                contract,
                request,
                "E_GENERATED_QUERY_UNAPPROVED",
                "generated Cypher is rejected until explicitly policy-approved",
                request.query,
            )
        if not isinstance(request.query, str) or not request.query.strip():
            return _reject(
                contract,
                request,
                "E_CANDIDATE_FORMAT",
                "candidate is empty or not a string",
                request.query,
            )

        query = request.query.strip()
        normalized = normalize_query(query)
        if _has_multiple_statements(normalized):
            return _reject(
                contract,
                request,
                "E_MULTIPLE_STATEMENTS",
                "multiple Cypher statements are not allowed",
                query,
            )

        policy = _policy(contract)
        for clause in policy.get("forbidden_clauses", []):
            if _word_pattern(str(clause)).search(normalized):
                return _reject(
                    contract,
                    request,
                    "E_WRITE_OPERATION",
                    f"forbidden clause {clause} is not read-only",
                    query,
                )
        for token in policy.get("forbidden_tokens", []):
            if str(token).lower() in normalized.lower():
                return _reject(
                    contract, request, "E_FORBIDDEN_TOKEN", f"forbidden token {token}", query
                )

        procedures = _procedure_names(normalized)
        allowed = {str(name) for name in policy.get("allowed_procedures", [])}
        for procedure in procedures:
            if procedure not in allowed:
                return _reject(
                    contract,
                    request,
                    "E_PROCEDURE_NOT_ALLOWLISTED",
                    f"procedure {procedure} is not allowlisted",
                    query,
                )

        if not normalized.upper().startswith(("MATCH ", "OPTIONAL MATCH ", "CALL ")):
            return _reject(
                contract,
                request,
                "E_CLAUSE_NOT_ALLOWED",
                "query must start with a read-only MATCH/OPTIONAL MATCH/CALL",
                query,
            )
        if policy.get("requires_limit", True) and not _limit_values(normalized):
            return _reject(contract, request, "E_LIMIT_REQUIRED", "query must include LIMIT", query)
        limit_values = _limit_values(normalized)
        max_allowed = max_limit(contract)
        if any(value > max_allowed for value in limit_values):
            return _reject(
                contract, request, "E_LIMIT_TOO_HIGH", "query LIMIT exceeds policy maximum", query
            )
        if not _query_returns_required_evidence(normalized, contract):
            return _reject(
                contract,
                request,
                "E_EVIDENCE_RETURN_REQUIRED",
                "query must return required evidence identifiers",
                query,
            )

        return GeneratedCypherValidationResult(
            query_case=request.query_case,
            accepted=True,
            normalized_query=normalized,
            schema_version=schema_version(contract),
            required_evidence_returns=tuple(required_evidence_returns(contract)),
            max_limit=max_allowed,
            generated=request.generated,
        )


def normalize_query(candidate: str) -> str:
    """Collapse query whitespace for deterministic diagnostics and artifacts."""

    return re.sub(r"\s+", " ", candidate.strip())


def schema_version(contract: Mapping[str, Any]) -> str:
    return str(contract.get("schema_version", ""))


def _policy(contract: Mapping[str, Any]) -> Mapping[str, Any]:
    policy = contract.get("cypher_policy")
    return policy if isinstance(policy, Mapping) else {}


def _validate_contract(contract: Mapping[str, Any]) -> None:
    if schema_version(contract) != SUPPORTED_SCHEMA_VERSION:
        raise ValueError("E_SCHEMA_VERSION: unsupported schema_version")
    if not isinstance(contract.get("cypher_policy"), Mapping):
        raise ValueError("E_SCHEMA_CONTRACT: missing cypher_policy")
    if not required_evidence_returns(contract):
        raise ValueError("E_SCHEMA_CONTRACT: missing required_evidence_paths.return_fields")


def required_evidence_returns(contract: Mapping[str, Any]) -> list[str]:
    paths = contract.get("required_evidence_paths")
    if isinstance(paths, Mapping):
        raw_fields = paths.get("return_fields")
        if isinstance(raw_fields, list):
            return [str(item) for item in raw_fields]
    if isinstance(paths, list):
        fields: list[str] = []
        for path in paths:
            if not isinstance(path, Mapping):
                continue
            raw_items = path.get("required_return_fields")
            if not isinstance(raw_items, list):
                continue
            for item in raw_items:
                value = str(item)
                if value not in fields:
                    fields.append(value)
        return fields
    return []


def max_limit(contract: Mapping[str, Any]) -> int:
    value = _policy(contract).get("max_limit", 25)
    return int(value) if isinstance(value, int) else 25


def _reject(
    contract: Mapping[str, Any],
    request: GeneratedCypherValidationRequest,
    code: str,
    message: str,
    candidate: object,
) -> GeneratedCypherValidationResult:
    diagnostic = GeneratedCypherDiagnostic(
        code=code,
        message=message,
        query_case=request.query_case,
        schema_policy_field=_schema_policy_field(contract, code),
        failure_class=_failure_class(contract, code),
    )
    return GeneratedCypherValidationResult(
        query_case=request.query_case,
        accepted=False,
        normalized_query=normalize_query(candidate)
        if isinstance(candidate, str)
        else "<non-string>",
        schema_version=schema_version(contract),
        required_evidence_returns=tuple(required_evidence_returns(contract)),
        max_limit=max_limit(contract),
        rejection_codes=(code,),
        diagnostics=(diagnostic,),
        generated=request.generated,
    )


def _schema_policy_field(contract: Mapping[str, Any], code: str) -> str:
    codes = contract.get("rejection_codes")
    if isinstance(codes, Mapping):
        details = codes.get(code)
        if isinstance(details, Mapping):
            return str(details.get("schema_policy_field", "cypher_policy"))
    return "cypher_policy"


def _failure_class(contract: Mapping[str, Any], code: str) -> str:
    codes = contract.get("rejection_codes")
    if isinstance(codes, Mapping):
        details = codes.get(code)
        if isinstance(details, Mapping):
            return str(details.get("failure_class", "validation"))
    return "validation"


def _word_pattern(word: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(word)}(?![A-Za-z0-9_])", re.IGNORECASE)


def _has_multiple_statements(query: str) -> bool:
    stripped = query.rstrip().rstrip(";")
    return ";" in stripped


def _limit_values(query: str) -> list[int]:
    return [int(value) for value in re.findall(r"\bLIMIT\s+(\d+)\b", query, flags=re.IGNORECASE)]


def _procedure_names(query: str) -> list[str]:
    return re.findall(r"\bCALL\s+([A-Za-z0-9_.]+)", query, flags=re.IGNORECASE)


def _query_returns_required_evidence(query: str, contract: Mapping[str, Any]) -> bool:
    return_values = _return_identifiers(query)
    required = required_evidence_returns(contract)
    return all(
        any(_field_matches(candidate, required_field) for candidate in return_values)
        for required_field in required
    )


def _return_identifiers(query: str) -> list[str]:
    match = re.search(r"\bRETURN\b(.+?)(?:\bORDER\s+BY\b|\bLIMIT\b|$)", query, flags=re.IGNORECASE)
    if not match:
        return []
    return [part.strip() for part in match.group(1).split(",") if part.strip()]


def _field_matches(candidate: str, required_field: str) -> bool:
    if "." not in required_field:
        return candidate.lower().endswith(required_field.lower())
    label, prop = required_field.split(".", maxsplit=1)
    label_token = label.lower()
    prop_token = f".{prop.lower()}"
    candidate_lower = candidate.lower()
    if label_token == "evidencespan":
        return candidate_lower.startswith("span") and prop_token in candidate_lower
    if label_token == "sourceblock":
        return candidate_lower.startswith("block") and prop_token in candidate_lower
    if label_token == "article":
        return candidate_lower.startswith("article") and prop_token in candidate_lower
    return prop_token in candidate_lower


def _unsafe_context_key(context: Mapping[str, Any] | None) -> str | None:
    if context is None:
        return None
    for key in context:
        if str(key) in _FORBIDDEN_CONTEXT_KEYS:
            return str(key)
    return None

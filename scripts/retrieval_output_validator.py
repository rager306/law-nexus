from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

RESULT_ACCEPTED = "accepted"
RESULT_ACCEPTED_SCOPED_NO_ANSWER = "accepted_scoped_no_answer"
RESULT_REJECTED = "rejected"

KNOWN_DIAGNOSTIC_CODES = frozenset(
    {
        "missing_required_field",
        "malformed_output_shape",
        "unknown_id_namespace",
        "unresolved_citation_key",
        "ambiguous_citation_key",
        "unresolved_evidence_span",
        "orphaned_source_path",
        "orphaned_legal_unit_path",
        "id_path_mismatch",
        "superseded_evidence",
        "wrong_edition",
        "answer_claim_without_evidence",
        "citation_without_evidence",
        "unsafe_no_answer_shape",
        "forbidden_payload_field",
        "scoped_no_answer",
    }
)

SAFE_DIAGNOSTIC_FIELDS = frozenset(
    {
        "code",
        "severity",
        "result",
        "field_path",
        "retrieval_output_id",
        "scope_id",
        "case_id",
        "safe_id_value",
        "expected_id",
        "resolved_id",
        "fixture_artifact",
    }
)

_ALLOWED_OUTPUT_KINDS = frozenset({"retrieval_candidate", "answer_claim", "scoped_no_answer"})
_REQUIRED_SCOPE_FIELDS = (
    "scope_id",
    "query_id",
    "retrieval_run_id",
    "as_of_date",
    "source_corpus_id",
    "validator_contract_version",
)
_REQUIRED_CITATION_FIELDS = (
    "retrieval_output_id",
    "citation_key",
    "evidence_span_id",
    "source_block_id",
    "source_document_id",
    "legal_unit_id",
    "act_edition_id",
)
_REQUIRED_ANSWER_CLAIM_FIELDS = (
    "answer_claim_id",
    "retrieval_output_id",
    "claim_kind",
    "scope_id",
    "supported_citation_keys",
)
_FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "raw_legal_text",
        "raw_text",
        "source_excerpt",
        "source_excerpts",
        "prompt",
        "user_prompt",
        "provider_payload",
        "provider_response_body",
        "secret",
        "secrets",
        "pii",
        "vector",
        "embedding_vector",
        "falkordb_row",
        "runtime_row",
        "generated_answer_prose",
        "legal_advice",
        "llm_reasoning",
    }
)
_ID_PREFIXES = {
    "retrieval_output_id": ("RET-M012-", "RET-M013-", "RET-M014-"),
    "scope_id": ("SCOPE-M012-", "SCOPE-M013-", "SCOPE-M014-"),
    "citation_key": ("CIT-M012-", "CIT-M013-", "CIT-M014-"),
    "evidence_span_id": ("EV-M012-", "EV-M013-", "EV-M014-"),
    "source_block_id": ("SB-M012-", "SB-M013-", "SB-M014-"),
    "source_document_id": ("SD-M012-", "SD-M013-", "SD-M014-"),
    "legal_unit_id": ("LU-M012-", "LU-M013-", "LU-M014-"),
    "act_edition_id": ("ED-M012-", "ED-M013-", "ED-M014-"),
    "answer_claim_id": ("AC-M012-", "AC-M013-", "AC-M014-"),
}


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    result: str
    field_path: str
    retrieval_output_id: str
    scope_id: str
    case_id: str
    safe_id_value: str | None = None
    expected_id: str | None = None
    resolved_id: str | None = None
    fixture_artifact: str | None = None

    def to_dict(self) -> dict[str, str]:
        payload = {
            "code": self.code,
            "severity": self.severity,
            "result": self.result,
            "field_path": self.field_path,
            "retrieval_output_id": self.retrieval_output_id,
            "scope_id": self.scope_id,
            "case_id": self.case_id,
        }
        for key in ("safe_id_value", "expected_id", "resolved_id", "fixture_artifact"):
            value = getattr(self, key)
            if value is not None:
                payload[key] = value
        return payload


@dataclass(frozen=True)
class ValidationResult:
    result: str
    diagnostics: tuple[Diagnostic, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"result": self.result, "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics]}


@dataclass(frozen=True)
class Fixture:
    data: Mapping[str, Any]
    fixture_artifact: str
    citation_bindings_by_scope_key: Mapping[tuple[str, str], tuple[Mapping[str, Any], ...]]
    evidence_spans_by_id: Mapping[str, Mapping[str, Any]]
    source_blocks_by_id: Mapping[str, Mapping[str, Any]]
    source_documents_by_id: Mapping[str, Mapping[str, Any]]
    legal_units_by_id: Mapping[str, Mapping[str, Any]]
    act_editions_by_id: Mapping[str, Mapping[str, Any]]
    legal_acts_by_id: Mapping[str, Mapping[str, Any]]


def load_fixture_file(path: str | Path) -> Fixture:
    fixture_path = Path(path)
    with fixture_path.open(encoding="utf-8") as fixture_file:
        data = json.load(fixture_file)
    if not isinstance(data, dict):
        raise ValueError("fixture root must be a JSON object")
    return build_fixture(data, fixture_artifact=data.get("fixture_artifact") or str(fixture_path))


def build_fixture(data: Mapping[str, Any], *, fixture_artifact: str = "<fixture>") -> Fixture:
    graph = data.get("fixture_graph")
    if not isinstance(graph, Mapping):
        raise ValueError("fixture_graph must be an object")

    def index(section: str, id_field: str) -> Mapping[str, Mapping[str, Any]]:
        records = graph.get(section)
        if not isinstance(records, list):
            raise ValueError(f"fixture_graph.{section} must be a list")
        indexed: dict[str, Mapping[str, Any]] = {}
        for record in records:
            if not isinstance(record, Mapping):
                raise ValueError(f"fixture_graph.{section} records must be objects")
            record_id = record.get(id_field)
            if not isinstance(record_id, str) or not record_id:
                raise ValueError(f"fixture_graph.{section} record missing {id_field}")
            indexed[record_id] = MappingProxyType(dict(record))
        return MappingProxyType(indexed)

    citation_index: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    bindings = graph.get("citation_bindings")
    if not isinstance(bindings, list):
        raise ValueError("fixture_graph.citation_bindings must be a list")
    for binding in bindings:
        if not isinstance(binding, Mapping):
            raise ValueError("fixture_graph.citation_bindings records must be objects")
        scope_id = binding.get("scope_id")
        citation_key = binding.get("citation_key")
        if not isinstance(scope_id, str) or not isinstance(citation_key, str):
            raise ValueError("citation binding missing scope_id or citation_key")
        citation_index.setdefault((scope_id, citation_key), []).append(MappingProxyType(dict(binding)))

    return Fixture(
        data=MappingProxyType(dict(data)),
        fixture_artifact=fixture_artifact,
        citation_bindings_by_scope_key=MappingProxyType(
            {key: tuple(value) for key, value in citation_index.items()}
        ),
        evidence_spans_by_id=index("evidence_spans", "evidence_span_id"),
        source_blocks_by_id=index("source_blocks", "source_block_id"),
        source_documents_by_id=index("source_documents", "source_document_id"),
        legal_units_by_id=index("legal_units", "legal_unit_id"),
        act_editions_by_id=index("act_editions", "act_edition_id"),
        legal_acts_by_id=index("legal_acts", "legal_act_id"),
    )


def validate_case(case: Mapping[str, Any], fixture: Fixture) -> ValidationResult:
    output = case.get("output") if isinstance(case, Mapping) else None
    case_id = case.get("case_id", "<missing>") if isinstance(case, Mapping) else "<missing>"
    return validate_output(output, fixture, case_id=case_id)


def validate_output(output: Any, fixture: Fixture, *, case_id: str = "<ad-hoc>") -> ValidationResult:
    diagnostics: list[Diagnostic] = []

    def add(
        code: str,
        field_path: str,
        *,
        severity: str = "error",
        safe_id_value: Any = None,
        expected_id: Any = None,
        resolved_id: Any = None,
    ) -> None:
        if code not in KNOWN_DIAGNOSTIC_CODES:
            raise ValueError(f"unknown diagnostic code: {code}")
        provisional_result = RESULT_ACCEPTED_SCOPED_NO_ANSWER if code == "scoped_no_answer" else RESULT_REJECTED
        diagnostics.append(
            Diagnostic(
                code=code,
                severity=severity,
                result=provisional_result,
                field_path=field_path,
                retrieval_output_id=_safe_id(output.get("retrieval_output_id") if isinstance(output, Mapping) else None),
                scope_id=_safe_id(_scope_id(output)),
                case_id=_safe_id(case_id),
                safe_id_value=_optional_safe_id(safe_id_value),
                expected_id=_optional_safe_id(expected_id),
                resolved_id=_optional_safe_id(resolved_id),
                fixture_artifact=fixture.fixture_artifact,
            )
        )

    if not isinstance(output, Mapping):
        add("malformed_output_shape", "$", safe_id_value=type(output).__name__)
        return _finalize(diagnostics)

    _check_forbidden_fields(output, add)
    _check_required_mapping(output, ("retrieval_output_id", "output_kind", "scope", "citations"), "", add)
    retrieval_output_id = output.get("retrieval_output_id")
    output_kind = output.get("output_kind")
    scope = output.get("scope")
    citations = output.get("citations")
    answer_claims = output.get("answer_claims", [])

    if isinstance(retrieval_output_id, str):
        _check_id_namespace("retrieval_output_id", retrieval_output_id, add)
    if output_kind not in _ALLOWED_OUTPUT_KINDS:
        add("malformed_output_shape", "output_kind", safe_id_value=output_kind)

    if not isinstance(scope, Mapping):
        add("malformed_output_shape", "scope", safe_id_value=type(scope).__name__)
        scope = {}
    else:
        _check_required_mapping(scope, _REQUIRED_SCOPE_FIELDS, "scope", add)
        _check_forbidden_fields(scope, add, path_prefix="scope")
        scope_id = scope.get("scope_id")
        if isinstance(scope_id, str):
            _check_id_namespace("scope.scope_id", scope_id, add, id_kind="scope_id")

    if not isinstance(citations, list):
        add("malformed_output_shape", "citations", safe_id_value=type(citations).__name__)
        citations = []
    if not isinstance(answer_claims, list):
        add("malformed_output_shape", "answer_claims", safe_id_value=type(answer_claims).__name__)
        answer_claims = []

    if output_kind == "scoped_no_answer":
        if citations or answer_claims:
            add("unsafe_no_answer_shape", "citations" if citations else "answer_claims")
        elif not _has_error(diagnostics):
            add("scoped_no_answer", "$", severity="info")
        return _finalize(diagnostics)

    citation_keys: set[str] = set()
    claim_ids_with_citation: set[str] = set()
    for index, citation in enumerate(citations):
        if not isinstance(citation, Mapping):
            add("malformed_output_shape", f"citations[{index}]", safe_id_value=type(citation).__name__)
            continue
        _validate_citation(
            citation,
            citation_index=index,
            fixture=fixture,
            output_id=retrieval_output_id,
            scope=scope,
            citation_keys=citation_keys,
            claim_ids_with_citation=claim_ids_with_citation,
            add=add,
        )

    if output_kind == "answer_claim" and not answer_claims:
        add("answer_claim_without_evidence", "answer_claims")
    for index, claim in enumerate(answer_claims):
        if not isinstance(claim, Mapping):
            add("malformed_output_shape", f"answer_claims[{index}]", safe_id_value=type(claim).__name__)
            continue
        _validate_answer_claim(
            claim,
            claim_index=index,
            output_id=retrieval_output_id,
            scope=scope,
            citation_keys=citation_keys,
            claim_ids_with_citation=claim_ids_with_citation,
            add=add,
        )

    return _finalize(diagnostics)


def _validate_citation(
    citation: Mapping[str, Any],
    *,
    citation_index: int,
    fixture: Fixture,
    output_id: Any,
    scope: Mapping[str, Any],
    citation_keys: set[str],
    claim_ids_with_citation: set[str],
    add: Any,
) -> None:
    prefix = f"citations[{citation_index}]"
    _check_forbidden_fields(citation, add, path_prefix=prefix)
    _check_required_mapping(citation, _REQUIRED_CITATION_FIELDS, prefix, add, citation_without_evidence=True)

    citation_output_id = citation.get("retrieval_output_id")
    if citation_output_id != output_id:
        add("id_path_mismatch", f"{prefix}.retrieval_output_id", expected_id=output_id, resolved_id=citation_output_id)
    if isinstance(citation_output_id, str):
        _check_id_namespace(f"{prefix}.retrieval_output_id", citation_output_id, add, id_kind="retrieval_output_id")

    for field in _REQUIRED_CITATION_FIELDS[1:]:
        value = citation.get(field)
        if isinstance(value, str):
            _check_id_namespace(f"{prefix}.{field}", value, add, id_kind=field)

    citation_key = citation.get("citation_key")
    evidence_span_id = citation.get("evidence_span_id")
    scope_id = scope.get("scope_id")
    if isinstance(citation_key, str):
        citation_keys.add(citation_key)
    answer_claim_id = citation.get("answer_claim_id")
    if isinstance(answer_claim_id, str):
        claim_ids_with_citation.add(answer_claim_id)
        _check_id_namespace(f"{prefix}.answer_claim_id", answer_claim_id, add, id_kind="answer_claim_id")

    if evidence_span_id is None:
        return
    if not isinstance(evidence_span_id, str) or not evidence_span_id:
        return
    if not _has_allowed_prefix("evidence_span_id", evidence_span_id):
        return

    bindings = fixture.citation_bindings_by_scope_key.get((scope_id, citation_key), ())
    if not bindings:
        add("unresolved_citation_key", f"{prefix}.citation_key", safe_id_value=citation_key)
    elif len(bindings) > 1:
        add("ambiguous_citation_key", f"{prefix}.citation_key", safe_id_value=citation_key)

    evidence = fixture.evidence_spans_by_id.get(evidence_span_id)
    if evidence is None:
        add("unresolved_evidence_span", f"{prefix}.evidence_span_id", safe_id_value=evidence_span_id)
        return

    if len(bindings) == 1 and bindings[0].get("evidence_span_id") != evidence_span_id:
        add(
            "id_path_mismatch",
            f"{prefix}.evidence_span_id",
            expected_id=bindings[0].get("evidence_span_id"),
            resolved_id=evidence_span_id,
        )

    if evidence.get("status") == "superseded":
        add("superseded_evidence", f"{prefix}.evidence_span_id", safe_id_value=evidence_span_id)
        return

    source_block = fixture.source_blocks_by_id.get(evidence.get("source_block_id"))
    source_document = fixture.source_documents_by_id.get(evidence.get("source_document_id"))
    if source_block is None or source_document is None or source_block.get("source_document_id") != evidence.get("source_document_id"):
        add(
            "orphaned_source_path",
            f"{prefix}.source_block_id",
            expected_id=evidence.get("source_document_id"),
            resolved_id=None if source_block is None else source_block.get("source_document_id"),
        )
        return

    legal_unit = fixture.legal_units_by_id.get(evidence.get("legal_unit_id"))
    act_edition = fixture.act_editions_by_id.get(evidence.get("act_edition_id"))
    legal_act = fixture.legal_acts_by_id.get(legal_unit.get("legal_act_id")) if legal_unit else None
    if (
        legal_unit is None
        or act_edition is None
        or legal_act is None
        or legal_unit.get("act_edition_id") != evidence.get("act_edition_id")
        or legal_unit.get("legal_act_id") != act_edition.get("legal_act_id")
    ):
        add(
            "orphaned_legal_unit_path",
            f"{prefix}.legal_unit_id",
            expected_id=evidence.get("legal_unit_id"),
            resolved_id=None if legal_unit is None else legal_unit.get("legal_unit_id"),
        )
        return

    as_of_date = scope.get("as_of_date")
    declared_edition_id = citation.get("act_edition_id")
    if declared_edition_id != evidence.get("act_edition_id") or not _edition_valid_for_date(act_edition, as_of_date):
        add(
            "wrong_edition",
            f"{prefix}.act_edition_id",
            expected_id=evidence.get("act_edition_id"),
            resolved_id=declared_edition_id,
        )
        return

    expected_paths = {
        "source_block_id": evidence.get("source_block_id"),
        "source_document_id": source_document.get("source_document_id"),
        "legal_unit_id": legal_unit.get("legal_unit_id"),
        "act_edition_id": act_edition.get("act_edition_id"),
    }
    for field, expected_id in expected_paths.items():
        if citation.get(field) != expected_id:
            add("id_path_mismatch", f"{prefix}.{field}", expected_id=expected_id, resolved_id=citation.get(field))
            return


def _validate_answer_claim(
    claim: Mapping[str, Any],
    *,
    claim_index: int,
    output_id: Any,
    scope: Mapping[str, Any],
    citation_keys: set[str],
    claim_ids_with_citation: set[str],
    add: Any,
) -> None:
    prefix = f"answer_claims[{claim_index}]"
    _check_forbidden_fields(claim, add, path_prefix=prefix)
    _check_required_mapping(claim, _REQUIRED_ANSWER_CLAIM_FIELDS, prefix, add)
    if claim.get("retrieval_output_id") != output_id:
        add("id_path_mismatch", f"{prefix}.retrieval_output_id", expected_id=output_id, resolved_id=claim.get("retrieval_output_id"))
    if claim.get("scope_id") != scope.get("scope_id"):
        add("id_path_mismatch", f"{prefix}.scope_id", expected_id=scope.get("scope_id"), resolved_id=claim.get("scope_id"))

    for field in ("answer_claim_id", "retrieval_output_id", "scope_id"):
        value = claim.get(field)
        if isinstance(value, str):
            _check_id_namespace(f"{prefix}.{field}", value, add, id_kind=field)

    supported = claim.get("supported_citation_keys")
    if not isinstance(supported, list):
        add("malformed_output_shape", f"{prefix}.supported_citation_keys", safe_id_value=type(supported).__name__)
        return
    if not supported:
        add("answer_claim_without_evidence", f"{prefix}.supported_citation_keys", safe_id_value=claim.get("answer_claim_id"))
        return
    missing = [key for key in supported if key not in citation_keys]
    if missing:
        add("answer_claim_without_evidence", f"{prefix}.supported_citation_keys", safe_id_value=missing[0])
    claim_id = claim.get("answer_claim_id")
    if isinstance(claim_id, str) and claim_id not in claim_ids_with_citation:
        add("answer_claim_without_evidence", f"{prefix}.answer_claim_id", safe_id_value=claim_id)


def _check_required_mapping(
    value: Mapping[str, Any],
    required_fields: tuple[str, ...],
    path_prefix: str,
    add: Any,
    *,
    citation_without_evidence: bool = False,
) -> None:
    for field in required_fields:
        if field not in value or value.get(field) in (None, ""):
            code = "citation_without_evidence" if citation_without_evidence and field == "evidence_span_id" and field in value else "missing_required_field"
            add(code, _join_path(path_prefix, field))


def _check_forbidden_fields(value: Any, add: Any, *, path_prefix: str = "") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            field_path = _join_path(path_prefix, str(key))
            if str(key).lower() in _FORBIDDEN_FIELD_NAMES:
                add("forbidden_payload_field", field_path, safe_id_value=key)
            _check_forbidden_fields(nested, add, path_prefix=field_path)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _check_forbidden_fields(nested, add, path_prefix=f"{path_prefix}[{index}]")


def _check_id_namespace(field_path: str, value: str, add: Any, *, id_kind: str | None = None) -> None:
    key = id_kind or field_path.rsplit(".", 1)[-1]
    if key in _ID_PREFIXES and not _has_allowed_prefix(key, value):
        add("unknown_id_namespace", field_path, safe_id_value=value)


def _has_allowed_prefix(id_kind: str, value: str) -> bool:
    return any(value.startswith(prefix) for prefix in _ID_PREFIXES[id_kind])


def _edition_valid_for_date(edition: Mapping[str, Any], as_of_date: Any) -> bool:
    if not isinstance(as_of_date, str) or not as_of_date:
        return False
    valid_from = edition.get("valid_from")
    valid_to = edition.get("valid_to")
    if isinstance(valid_from, str) and as_of_date < valid_from:
        return False
    if isinstance(valid_to, str) and as_of_date > valid_to:
        return False
    return edition.get("status") == "active"


def _scope_id(output: Any) -> Any:
    if isinstance(output, Mapping) and isinstance(output.get("scope"), Mapping):
        return output["scope"].get("scope_id")
    return None


def _finalize(diagnostics: list[Diagnostic]) -> ValidationResult:
    result = RESULT_REJECTED if _has_error(diagnostics) else RESULT_ACCEPTED
    if result == RESULT_ACCEPTED and any(diagnostic.code == "scoped_no_answer" for diagnostic in diagnostics):
        result = RESULT_ACCEPTED_SCOPED_NO_ANSWER
    normalized = tuple(
        Diagnostic(
            code=diagnostic.code,
            severity=diagnostic.severity,
            result=result if diagnostic.severity == "error" else diagnostic.result,
            field_path=diagnostic.field_path,
            retrieval_output_id=diagnostic.retrieval_output_id,
            scope_id=diagnostic.scope_id,
            case_id=diagnostic.case_id,
            safe_id_value=diagnostic.safe_id_value,
            expected_id=diagnostic.expected_id,
            resolved_id=diagnostic.resolved_id,
            fixture_artifact=diagnostic.fixture_artifact,
        )
        for diagnostic in diagnostics
    )
    return ValidationResult(result=result, diagnostics=normalized)


def _has_error(diagnostics: list[Diagnostic]) -> bool:
    return any(diagnostic.severity == "error" for diagnostic in diagnostics)


def _safe_id(value: Any) -> str:
    if isinstance(value, str) and value:
        return value[:128]
    return "<missing>"


def _optional_safe_id(value: Any) -> str | None:
    if value is None:
        return None
    return _safe_id(value)


def _join_path(prefix: str, field: str) -> str:
    return f"{prefix}.{field}" if prefix else field

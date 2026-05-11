#!/usr/bin/env python3
"""Build a derived, non-authoritative NetworkX parser staging graph.

The graph is a deterministic debug/staging shape over validated parser JSONL
artifacts. It does not reread raw legal sources, does not assert legal
correctness, and does not claim FalkorDB loading/runtime readiness.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, TypeVar

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.parser_records import (  # noqa: E402
    DocumentRecord,
    ParserRecord,
    RelationCandidateRecord,
    SourceBlockRecord,
    load_jsonl_records,
)

DEFAULT_DOCUMENT_RECORDS_PATH = ROOT / "prd/parser/odt_document_records.jsonl"
DEFAULT_SOURCE_BLOCK_RECORDS_PATH = ROOT / "prd/parser/odt_source_block_records.jsonl"
DEFAULT_RELATION_CANDIDATE_RECORDS_PATH = ROOT / "prd/parser/consultant_relation_candidates.jsonl"

NodeKind = Literal["document", "source_block", "unresolved_reference"]
EdgeKind = Literal["contains_source_block", "relation_candidate"]
DiagnosticSeverity = Literal["error", "warning", "info"]
GraphBuildStatus = Literal["pass", "fail"]


@dataclass(frozen=True)
class GraphBuildDiagnostic:
    """Compact, deterministic graph-build diagnostic for agent-visible failures."""

    path: Path
    line: int
    rule: str
    message: str
    severity: DiagnosticSeverity = "error"
    record_id: str | None = None
    record_kind: str | None = None
    field: str = "record"
    source_path: str | None = None

    @classmethod
    def from_loader_diagnostic(cls, diagnostic: dict[str, Any]) -> GraphBuildDiagnostic:
        return cls(
            path=Path(str(diagnostic.get("file", "<unknown>"))),
            line=int(diagnostic.get("line") or 0),
            rule=str(diagnostic.get("rule") or "validation_error"),
            message=str(diagnostic.get("message") or "validation error"),
            severity="error",
            record_id=_optional_string(diagnostic.get("record_id")),
            record_kind=_optional_string(diagnostic.get("record_kind")),
            field=str(diagnostic.get("field") or "record"),
            source_path=_optional_string(diagnostic.get("source_path")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": display_path(self.path),
            "line": self.line,
            "id": self.record_id,
            "record_id": self.record_id,
            "record_kind": self.record_kind,
            "field": self.field,
            "rule": self.rule,
            "severity": self.severity,
            "source_path": self.source_path,
            "message": self.message,
        }


@dataclass(frozen=True)
class LoadedParserRecords:
    """Validated parser records loaded from one JSONL artifact."""

    path: Path
    records: tuple[ParserRecord, ...]
    diagnostics: tuple[GraphBuildDiagnostic, ...]


@dataclass(frozen=True)
class ParserStagingGraphSummary:
    """Deterministic graph summary for tests and later CLI/report output."""

    node_counts: dict[str, int]
    edge_counts: dict[str, int]
    relation_candidate_edge_keys: list[str]
    unresolved_reference_ids: list[str]
    diagnostic_count: int
    error_count: int
    warning_count: int
    info_count: int
    status: GraphBuildStatus
    non_authoritative: bool = True
    parser_completeness_claimed: bool = False
    legal_correctness_claimed: bool = False
    product_etl_claimed: bool = False
    falkordb_loading_runtime_readiness_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_counts": dict(self.node_counts),
            "edge_counts": dict(self.edge_counts),
            "relation_candidate_edge_keys": list(self.relation_candidate_edge_keys),
            "unresolved_reference_ids": list(self.unresolved_reference_ids),
            "diagnostic_count": self.diagnostic_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "status": self.status,
            "non_authoritative": self.non_authoritative,
            "parser_completeness_claimed": self.parser_completeness_claimed,
            "legal_correctness_claimed": self.legal_correctness_claimed,
            "product_etl_claimed": self.product_etl_claimed,
            "falkordb_loading_runtime_readiness_claimed": self.falkordb_loading_runtime_readiness_claimed,
        }


@dataclass(frozen=True)
class ParserStagingGraphResult:
    """Built graph plus load/build diagnostics and summary."""

    graph: nx.MultiDiGraph
    diagnostics: list[GraphBuildDiagnostic] = field(default_factory=list)
    summary: ParserStagingGraphSummary = field(default_factory=lambda: summarize_graph(nx.MultiDiGraph(), []))


def build_default_staging_graph() -> ParserStagingGraphResult:
    """Build the parser staging graph from the tracked generated parser JSONL artifacts."""

    return build_staging_graph(
        document_records_path=DEFAULT_DOCUMENT_RECORDS_PATH,
        source_block_records_path=DEFAULT_SOURCE_BLOCK_RECORDS_PATH,
        relation_candidate_records_path=DEFAULT_RELATION_CANDIDATE_RECORDS_PATH,
    )


def build_staging_graph(
    *,
    document_records_path: Path,
    source_block_records_path: Path,
    relation_candidate_records_path: Path,
) -> ParserStagingGraphResult:
    """Load parser JSONL artifacts and assemble a non-authoritative MultiDiGraph."""

    document_load = load_records(document_records_path, expected_kind="document")
    source_block_load = load_records(source_block_records_path, expected_kind="source_block")
    relation_load = load_records(relation_candidate_records_path, expected_kind="relation_candidate")
    diagnostics = [
        *document_load.diagnostics,
        *source_block_load.diagnostics,
        *relation_load.diagnostics,
    ]

    graph = nx.MultiDiGraph(non_authoritative=True)
    if has_error_diagnostics(diagnostics):
        return ParserStagingGraphResult(
            graph=graph,
            diagnostics=diagnostics,
            summary=summarize_graph(graph, diagnostics),
        )

    documents = _typed_records(document_load.records, DocumentRecord)
    source_blocks = _typed_records(source_block_load.records, SourceBlockRecord)
    relation_candidates = _typed_records(relation_load.records, RelationCandidateRecord)

    invariant_diagnostics = validate_loaded_record_invariants(documents, source_blocks, relation_candidates)
    diagnostics.extend(invariant_diagnostics)
    if has_error_diagnostics(invariant_diagnostics):
        return ParserStagingGraphResult(
            graph=graph,
            diagnostics=diagnostics,
            summary=summarize_graph(graph, diagnostics),
        )

    build_diagnostics = populate_graph(graph, documents, source_blocks, relation_candidates)
    diagnostics.extend(build_diagnostics)
    diagnostics.append(
        GraphBuildDiagnostic(
            path=relation_candidate_records_path,
            line=0,
            rule="no_falkordb_load_executed",
            severity="info",
            message="NetworkX staging graph was built only; no FalkorDB loading/runtime readiness claim is made",
        )
    )
    return ParserStagingGraphResult(
        graph=graph,
        diagnostics=diagnostics,
        summary=summarize_graph(graph, diagnostics),
    )


def load_records(path: Path, *, expected_kind: str) -> LoadedParserRecords:
    """Load one JSONL parser artifact with missing-file and kind diagnostics."""

    if not path.exists():
        return LoadedParserRecords(
            path=path,
            records=(),
            diagnostics=(
                GraphBuildDiagnostic(
                    path=path,
                    line=0,
                    rule="missing_file",
                    severity="error",
                    message="required parser JSONL artifact is missing",
                    record_kind=expected_kind,
                ),
            ),
        )

    records, raw_diagnostics = load_jsonl_records(path)
    diagnostics = [GraphBuildDiagnostic.from_loader_diagnostic(diagnostic) for diagnostic in raw_diagnostics]
    for record in records:
        if record.record_kind != expected_kind:
            diagnostics.append(
                GraphBuildDiagnostic(
                    path=path,
                    line=0,
                    rule="unexpected_record_kind",
                    severity="error",
                    message=f"expected record_kind={expected_kind}",
                    record_id=record.id,
                    record_kind=record.record_kind,
                    field="record_kind",
                    source_path=record.source_path,
                )
            )
    if diagnostics:
        return LoadedParserRecords(path=path, records=(), diagnostics=tuple(diagnostics))
    return LoadedParserRecords(path=path, records=tuple(sorted(records, key=record_sort_key)), diagnostics=())


def validate_loaded_record_invariants(
    documents: list[DocumentRecord],
    source_blocks: list[SourceBlockRecord],
    relation_candidates: list[RelationCandidateRecord],
) -> list[GraphBuildDiagnostic]:
    """Validate loaded-record invariants that do not require graph traversal."""

    diagnostics: list[GraphBuildDiagnostic] = []
    seen_ids: dict[str, ParserRecord] = {}
    for record in sorted([*documents, *source_blocks, *relation_candidates], key=record_sort_key):
        prior_record = seen_ids.get(record.id)
        if prior_record is not None:
            diagnostics.append(
                _record_diagnostic(
                    record,
                    "duplicate_global_id",
                    f"record id duplicates {prior_record.record_kind} record id",
                    field="id",
                    severity="error",
                )
            )
            continue
        seen_ids[record.id] = record

    seen_document_identity: dict[tuple[str, str], DocumentRecord] = {}
    for document in sorted(documents, key=record_sort_key):
        identity = (document.source_kind, document.source_path)
        prior_document = seen_document_identity.get(identity)
        if prior_document is not None and prior_document.id != document.id:
            diagnostics.append(
                _record_diagnostic(
                    document,
                    "duplicate_document_identity",
                    f"document source identity duplicates document record {prior_document.id}",
                    field="source_path",
                    severity="error",
                )
            )
            continue
        seen_document_identity[identity] = document

    return diagnostics


def populate_graph(
    graph: nx.MultiDiGraph,
    documents: list[DocumentRecord],
    source_blocks: list[SourceBlockRecord],
    relation_candidates: list[RelationCandidateRecord],
) -> list[GraphBuildDiagnostic]:
    """Populate a MultiDiGraph with document/source-block nodes and keyed relation edges."""

    diagnostics: list[GraphBuildDiagnostic] = []
    document_ids: set[str] = set()
    source_block_ids: set[str] = {source_block.id for source_block in source_blocks}

    for document in sorted(documents, key=record_sort_key):
        document_ids.add(document.id)
        graph.add_node(document.id, node_kind="document", record=document, non_authoritative=True)

    for source_block in sorted(source_blocks, key=lambda record: (record.document_id, record.order_index, record.id)):
        graph.add_node(source_block.id, node_kind="source_block", record=source_block, non_authoritative=True)
        if source_block.document_id not in document_ids:
            diagnostics.append(
                _record_diagnostic(
                    source_block,
                    "missing_document_endpoint",
                    "source block references a document record that is absent",
                    field="document_id",
                    severity="error",
                )
            )
            continue
        graph.add_edge(
            source_block.document_id,
            source_block.id,
            key=f"contains:{source_block.id}",
            edge_kind="contains_source_block",
            record=source_block,
            non_authoritative=True,
        )

    for candidate in sorted(relation_candidates, key=record_sort_key):
        if candidate.source_block_id not in source_block_ids:
            diagnostics.append(
                _record_diagnostic(
                    candidate,
                    "missing_source_block_record",
                    "relation candidate source_block_id is not present in loaded source block records",
                    field="source_block_id",
                    severity="warning",
                )
            )
        if candidate.status == "candidate":
            diagnostics.append(
                _record_diagnostic(
                    candidate,
                    "candidate_only_relation",
                    "relation remains candidate-only and does not claim relation correctness",
                    field="status",
                    severity="info",
                )
            )

        subject_id = ensure_relation_endpoint_node(graph, candidate.subject_ref, candidate)
        if graph.nodes[subject_id].get("node_kind") == "unresolved_reference":
            diagnostics.append(
                _record_diagnostic(
                    candidate,
                    "unresolved_subject_ref",
                    "relation candidate subject_ref is not a loaded parser record id",
                    field="subject_ref",
                    severity="warning",
                )
            )
        object_id = ensure_relation_endpoint_node(graph, candidate.object_ref, candidate)
        if graph.nodes[object_id].get("node_kind") == "unresolved_reference":
            diagnostics.append(
                _record_diagnostic(
                    candidate,
                    "unresolved_object_ref",
                    "relation candidate object_ref is not a loaded parser record id",
                    field="object_ref",
                    severity="warning",
                )
            )
        graph.add_edge(
            subject_id,
            object_id,
            key=candidate.id,
            edge_kind="relation_candidate",
            record=candidate,
            source_block_id=candidate.source_block_id,
            relation_type=candidate.relation_type,
            status=candidate.status,
            non_authoritative=True,
        )

    return diagnostics


def ensure_relation_endpoint_node(graph: nx.MultiDiGraph, endpoint_ref: str, candidate: RelationCandidateRecord) -> str:
    """Ensure relation endpoints exist without rewriting non-DOC Consultant references."""

    if endpoint_ref in graph:
        return endpoint_ref
    if endpoint_ref.startswith("DOC-"):
        graph.add_node(
            endpoint_ref,
            node_kind="unresolved_reference",
            record=None,
            unresolved_ref=endpoint_ref,
            unresolved_ref_kind="document",
            relation_candidate_id=candidate.id,
            non_authoritative=True,
        )
        return endpoint_ref
    graph.add_node(
        endpoint_ref,
        node_kind="unresolved_reference",
        record=None,
        unresolved_ref=endpoint_ref,
        unresolved_ref_kind="external_or_parser_candidate",
        relation_candidate_id=candidate.id,
        non_authoritative=True,
    )
    return endpoint_ref


def summarize_graph(graph: nx.MultiDiGraph, diagnostics: Iterable[GraphBuildDiagnostic]) -> ParserStagingGraphSummary:
    """Compute deterministic counts and bounded graph health signals."""

    diagnostics_tuple = tuple(diagnostics)
    node_counts: dict[str, int] = {}
    for _, data in sorted(graph.nodes(data=True), key=lambda item: str(item[0])):
        kind = str(data.get("node_kind") or "unknown")
        node_counts[kind] = node_counts.get(kind, 0) + 1

    edge_counts: dict[str, int] = {}
    relation_candidate_edge_keys: list[str] = []
    edge_items = sorted(graph.edges(keys=True, data=True), key=lambda item: (str(item[0]), str(item[1]), str(item[2])))
    for _, _, key, data in edge_items:
        kind = str(data.get("edge_kind") or "unknown")
        edge_counts[kind] = edge_counts.get(kind, 0) + 1
        if kind == "relation_candidate":
            relation_candidate_edge_keys.append(str(key))

    unresolved_reference_ids = sorted(
        str(node_id)
        for node_id, data in graph.nodes(data=True)
        if data.get("node_kind") == "unresolved_reference"
    )
    error_count = sum(1 for diagnostic in diagnostics_tuple if diagnostic.severity == "error")
    warning_count = sum(1 for diagnostic in diagnostics_tuple if diagnostic.severity == "warning")
    info_count = sum(1 for diagnostic in diagnostics_tuple if diagnostic.severity == "info")
    return ParserStagingGraphSummary(
        node_counts=dict(sorted(node_counts.items())),
        edge_counts=dict(sorted(edge_counts.items())),
        relation_candidate_edge_keys=sorted(relation_candidate_edge_keys),
        unresolved_reference_ids=unresolved_reference_ids,
        diagnostic_count=len(diagnostics_tuple),
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        status="fail" if error_count else "pass",
    )


def has_error_diagnostics(diagnostics: Iterable[GraphBuildDiagnostic]) -> bool:
    """Return whether any diagnostic is a hard graph-build error."""

    return any(diagnostic.severity == "error" for diagnostic in diagnostics)


def record_sort_key(record: ParserRecord) -> tuple[str, int, str]:
    order = record.order_index if isinstance(record, SourceBlockRecord) else -1
    return (record.id, order, record.source_path)


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


T = TypeVar("T", DocumentRecord, SourceBlockRecord, RelationCandidateRecord)


def _typed_records(records: tuple[ParserRecord, ...], model_type: type[T]) -> list[T]:
    return [record for record in records if isinstance(record, model_type)]


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _record_diagnostic(
    record: ParserRecord,
    rule: str,
    message: str,
    *,
    severity: DiagnosticSeverity,
    field: str = "record",
) -> GraphBuildDiagnostic:
    return GraphBuildDiagnostic(
        path=ROOT / record.source_path,
        line=0,
        rule=rule,
        severity=severity,
        message=message,
        record_id=record.id,
        record_kind=record.record_kind,
        field=field,
        source_path=record.source_path,
    )

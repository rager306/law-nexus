from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import pytest

from law_nexus.domain.legal_unit import LegalUnit, LegalUnitType
from law_nexus.ports.graph_store import (
    GRAPH_STORE_NON_CLAIMS,
    GraphStoreCapability,
    GraphStoreDiagnostic,
    GraphStoreHealth,
    GraphStoreQuery,
    GraphStoreQueryResult,
    GraphWriteBatch,
    Relation,
)


@dataclass
class FakeGraphStore:
    legal_units: dict[str, LegalUnit] = field(default_factory=dict)
    relations: list[Relation] = field(default_factory=list)

    def write_legal_unit(self, unit: LegalUnit) -> None:
        self.legal_units[unit.unit_id] = unit

    def read_legal_unit(self, unit_id: str) -> LegalUnit | None:
        return self.legal_units.get(unit_id)

    def write_relation(self, relation: Relation) -> None:
        self.relations.append(relation)

    def write_batch(self, batch: GraphWriteBatch) -> GraphStoreQueryResult:
        for unit in batch.legal_units:
            self.write_legal_unit(unit)
        for relation in batch.relations:
            self.write_relation(relation)
        return GraphStoreQueryResult(
            rows=(),
            diagnostics=(
                GraphStoreDiagnostic(
                    code="write_batch_accepted",
                    severity="info",
                    message="accepted by fake graph store",
                    safe_context={
                        "legal_unit_count": len(batch.legal_units),
                        "relation_count": len(batch.relations),
                    },
                ),
            ),
        )

    def query(self, query: GraphStoreQuery) -> GraphStoreQueryResult:
        if (
            not query.read_only
            or query.generated
            or not query.cypher.strip().upper().startswith("MATCH")
        ):
            return GraphStoreQueryResult(
                rows=(),
                diagnostics=(
                    GraphStoreDiagnostic(
                        code="unsafe_query_rejected",
                        severity="error",
                        message="fake graph store accepts only explicit read-only MATCH queries",
                        safe_context={"generated": query.generated, "read_only": query.read_only},
                    ),
                ),
            )
        return GraphStoreQueryResult(
            rows=tuple({"unit_id": unit_id} for unit_id in sorted(self.legal_units)), diagnostics=()
        )

    def health(self) -> GraphStoreHealth:
        return GraphStoreHealth(
            status="fake",
            capabilities=(
                GraphStoreCapability(name="write_batch", supported=True, evidence="fake-contract"),
                GraphStoreCapability(
                    name="read_only_match_query", supported=True, evidence="fake-contract"
                ),
                GraphStoreCapability(
                    name="generated_cypher_execution", supported=False, evidence="S16-owned"
                ),
                GraphStoreCapability(
                    name="production_falkordb_runtime", supported=False, evidence="S15-owned"
                ),
            ),
            non_claims=GRAPH_STORE_NON_CLAIMS,
        )


def _unit(unit_id: str = "LU-M014-001") -> LegalUnit:
    return LegalUnit(
        unit_id=unit_id,
        legal_document_id="SD-M014-DOC-001",
        unit_type=LegalUnitType.article,
        parent_unit_id=None,
        edition_id="ED-M014-001",
    )


def test_graph_store_fake_contract_writes_units_and_relations() -> None:
    store = FakeGraphStore()
    relation = Relation(
        relation_type="CONTAINS",
        from_id="SD-M014-DOC-001",
        to_id="LU-M014-001",
        properties={"order": 1},
    )
    result = store.write_batch(GraphWriteBatch(legal_units=(_unit(),), relations=(relation,)))

    assert store.read_legal_unit("LU-M014-001") == _unit()
    assert store.relations == [relation]
    assert result.diagnostics[0].code == "write_batch_accepted"
    assert result.diagnostics[0].safe_context == {"legal_unit_count": 1, "relation_count": 1}


def test_graph_store_query_contract_rejects_generated_or_mutating_cypher() -> None:
    store = FakeGraphStore()

    generated = store.query(
        GraphStoreQuery(cypher="MATCH (n) RETURN n", read_only=True, generated=True)
    )
    mutating = store.query(
        GraphStoreQuery(cypher="CREATE (:LegalUnit)", read_only=False, generated=False)
    )

    assert [diagnostic.code for diagnostic in generated.diagnostics] == ["unsafe_query_rejected"]
    assert [diagnostic.code for diagnostic in mutating.diagnostics] == ["unsafe_query_rejected"]
    assert generated.rows == ()
    assert mutating.rows == ()


def test_graph_store_query_contract_returns_bounded_rows_for_read_only_match() -> None:
    store = FakeGraphStore()
    store.write_legal_unit(_unit("LU-M014-002"))

    result = store.query(
        GraphStoreQuery(
            cypher="MATCH (u:LegalUnit) RETURN u.unit_id", read_only=True, generated=False
        )
    )

    assert result.rows == ({"unit_id": "LU-M014-002"},)
    assert result.diagnostics == ()


def test_graph_store_health_declares_non_claims_and_unsupported_runtime_capabilities() -> None:
    health = FakeGraphStore().health()
    capability_map = {capability.name: capability.supported for capability in health.capabilities}

    assert health.status == "fake"
    assert capability_map["generated_cypher_execution"] is False
    assert capability_map["production_falkordb_runtime"] is False
    assert "Does not prove production FalkorDB runtime behavior." in health.non_claims
    assert "Does not prove legal-answer correctness." in health.non_claims


def test_graph_store_contract_exposes_structural_protocol_surface() -> None:
    # The fake intentionally implements the protocol by structure; this guards
    # the minimal adapter surface without depending on a FalkorDB client.
    required = {
        "write_legal_unit",
        "read_legal_unit",
        "write_relation",
        "write_batch",
        "query",
        "health",
    }

    assert required <= set(dir(FakeGraphStore()))
    assert isinstance(FakeGraphStore().health().capabilities, Iterable)


def test_graph_store_diagnostics_reject_raw_context_values() -> None:
    with pytest.raises(ValueError):
        GraphStoreDiagnostic(
            code="unsafe_query_rejected",
            severity="error",
            message="bad",
            safe_context={"raw_legal_text": "not allowed"},
        )

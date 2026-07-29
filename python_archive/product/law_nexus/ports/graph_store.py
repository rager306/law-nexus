"""GraphStore port — bounded graph write/query contract.

[proposed] port contract per D046 and hardened in M076 S14. Declares the
*shape* a graph backend adapter must satisfy for the LegalUnit + Relation
subset of the target model (prd/02_architecture.md §2), plus bounded batch,
read-only query, health, capability, and diagnostic DTOs.

This module is a port contract only. It imports no FalkorDB client, executes no
Cypher, validates no legal correctness, and proves no production graph runtime
behavior. S15/S16 own FalkorDB adapter and generated-Cypher policy work.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from law_nexus.domain.legal_unit import LegalUnit

#: Primitive scalar value allowed as relation/query/diagnostic metadata.
GraphPropertyValue = str | int | float | bool | None

GRAPH_STORE_NON_CLAIMS: tuple[str, ...] = (
    "Does not prove production FalkorDB runtime behavior.",
    "Does not prove production graph schema readiness.",
    "Does not prove generated Cypher safety.",
    "Does not execute generated Cypher.",
    "Does not prove legal-answer correctness.",
    "Does not prove parser completeness.",
    "Does not prove retrieval quality.",
    "Does not prove vector, full-text, GraphBLAS, or UDF support.",
)

_FORBIDDEN_DIAGNOSTIC_CONTEXT_KEYS = frozenset(
    {
        "raw_legal_text",
        "raw_text",
        "source_excerpt",
        "source_excerpts",
        "query_text",
        "raw_query_text",
        "prompt",
        "provider_payload",
        "raw_falkordb_row",
        "secret",
        "token",
    }
)


class Relation(BaseModel):
    """A directed graph edge between two nodes (port-local data shape).

    [proposed] port-local pending the D046 Relation domain form. ``from_id``
    and ``to_id`` reference node IDs (graph model). ``relation_type`` is one of
    the target-model relationship names (CONTAINS, SUPPORTED_BY, …,
    prd/02_architecture.md §2). ``properties`` carries scalar edge metadata.
    """

    model_config = ConfigDict(extra="forbid")

    relation_type: str = Field(min_length=1)
    from_id: str = Field(min_length=1)
    to_id: str = Field(min_length=1)
    properties: dict[str, GraphPropertyValue] = Field(default_factory=dict)


class GraphWriteBatch(BaseModel):
    """Bounded graph write batch for structural LegalUnit/Relation data."""

    model_config = ConfigDict(extra="forbid")

    legal_units: tuple[LegalUnit, ...] = ()
    relations: tuple[Relation, ...] = ()


class GraphStoreQuery(BaseModel):
    """Read-only graph query request.

    ``generated`` marks model-generated Cypher or policy-unreviewed query text.
    A conforming adapter must reject generated queries unless a later S16-owned
    policy explicitly allows them.
    """

    model_config = ConfigDict(extra="forbid")

    cypher: str = Field(min_length=1)
    parameters: dict[str, GraphPropertyValue] = Field(default_factory=dict)
    read_only: bool = True
    generated: bool = False
    purpose: str = "bounded-read"


class GraphStoreDiagnostic(BaseModel):
    """Safe diagnostic emitted by GraphStore adapters or fakes."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    severity: str = Field(pattern="^(info|warning|error)$")
    message: str = Field(min_length=1)
    safe_context: dict[str, GraphPropertyValue] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:  # noqa: ANN401 - Pydantic hook context is intentionally Any.
        forbidden = _FORBIDDEN_DIAGNOSTIC_CONTEXT_KEYS & set(self.safe_context)
        if forbidden:
            forbidden_keys = ", ".join(sorted(forbidden))
            raise ValueError(f"unsafe GraphStore diagnostic context keys: {forbidden_keys}")


class GraphStoreQueryResult(BaseModel):
    """Bounded graph query/write result."""

    model_config = ConfigDict(extra="forbid")

    rows: tuple[dict[str, GraphPropertyValue], ...] = ()
    diagnostics: tuple[GraphStoreDiagnostic, ...] = ()


class GraphStoreCapability(BaseModel):
    """Adapter capability metadata with an evidence label."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    supported: bool
    evidence: str = Field(min_length=1)


class GraphStoreHealth(BaseModel):
    """Health and capability boundary for a GraphStore implementation."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1)
    capabilities: tuple[GraphStoreCapability, ...] = ()
    diagnostics: tuple[GraphStoreDiagnostic, ...] = ()
    non_claims: tuple[str, ...] = GRAPH_STORE_NON_CLAIMS


@runtime_checkable
class GraphStore(Protocol):
    """Read/write LegalUnit nodes and Relation edges.

    Scope is deliberately narrow (LegalUnit + Relation) for the MVP port;
    extend as consuming use cases require. This port does NOT validate temporal
    applicability, lex superior, or evidence chains — those stay deterministic
    in downstream layers. Query execution is read-only by contract and
    generated-Cypher execution remains S16-owned.
    """

    def write_legal_unit(self, unit: LegalUnit) -> None:
        """Persist (upsert) a LegalUnit node keyed by ``unit.unit_id``."""
        ...

    def read_legal_unit(self, unit_id: str) -> LegalUnit | None:
        """Read a LegalUnit by ID, or ``None`` if absent."""
        ...

    def write_relation(self, relation: Relation) -> None:
        """Persist (upsert) a Relation edge between two nodes."""
        ...

    def read_relations(self, node_id: str) -> list[Relation]:
        """Read all Relation edges touching ``node_id`` (either endpoint)."""
        ...

    def write_batch(self, batch: GraphWriteBatch) -> GraphStoreQueryResult:
        """Persist a bounded batch and return safe diagnostics."""
        ...

    def query(self, query: GraphStoreQuery) -> GraphStoreQueryResult:
        """Execute a bounded read-only query or return a rejection diagnostic."""
        ...

    def health(self) -> GraphStoreHealth:
        """Return safe health/capability metadata and explicit non-claims."""
        ...

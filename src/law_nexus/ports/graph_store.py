"""GraphStore port — read/write LegalUnit nodes and Relation edges.

[proposed] port contract per D046. Declares the *shape* a graph backend
(FalkorDB) adapter must satisfy for the LegalUnit + Relation subset of the
target model (prd/02_architecture.md §2). Broader node kinds (SourceDocument,
ActEdition, NormStatement, TextChunk) are intentionally out of scope here;
they land as the consuming use cases demand them.

``Relation`` is a [proposed] port-local data shape pending a D046 Relation
domain form; it carries the edge type, endpoints, and a typed property bag.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from law_nexus.domain.legal_unit import LegalUnit

#: Primitive scalar value allowed as a relation/edge property.
GraphPropertyValue = str | int | float | bool | None


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


@runtime_checkable
class GraphStore(Protocol):
    """Read/write LegalUnit nodes and Relation edges.

    Scope is deliberately narrow (LegalUnit + Relation) for the MVP port;
    extend as consuming use cases require. This port does NOT validate temporal
    applicability, lex superior, or evidence chains — those stay deterministic
    in downstream layers.
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

"""law_nexus.ports — D046 port layer (typing.Protocol contracts).

[proposed] ports per D046. Each port is a pure ``typing.Protocol`` declaring
the *shape* adapters must satisfy, with zero implementation. The domain layer
is the only dependency; ports carry no infrastructure imports and no logic.

Ports:
- :class:`Parser`      — source path → SourceDocument + SourceBlock sequence.
- :class:`LLMClient`   — non-authoritative completion + provider embedding.
- :class:`GraphStore`  — read/write LegalUnit nodes and Relation edges.
- :class:`Embedder`    — corpus text → vector for retrieval indexing.

``runtime_checkable`` enables structural adapter-conformance checks; full
signature checking is done statically by basedpyright.
"""

from __future__ import annotations

from law_nexus.ports.embedder import Embedder
from law_nexus.ports.graph_store import GraphPropertyValue, GraphStore, Relation
from law_nexus.ports.llm_client import LLMClient
from law_nexus.ports.parser import Parser

__all__ = [
    "Embedder",
    "GraphStore",
    "GraphPropertyValue",
    "LLMClient",
    "Parser",
    "Relation",
]

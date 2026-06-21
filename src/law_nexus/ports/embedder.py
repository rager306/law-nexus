"""Embedder port — corpus text → vector for retrieval indexing.

[proposed] port contract per D046. Distinct from ``LLMClient.embed``: the
Embedder encodes retrieval chunks (the ``TextChunk`` corpus, legal-unit-aligned
per prd/02_architecture.md §8) and is expected to be backed by a dedicated
embedding model (e.g. the ``local-embeddings`` dependency group's
sentence-transformers). Vectors are non-authoritative retrieval signals, never
evidence or legal authority.

The port declares only the *shape* adapters must satisfy.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """Encode retrieval texts into vectors.

    Output vectors are non-authoritative retrieval signals only. Embeddings
    remain post-MVP / gated by FR-28b (prd/02_architecture.md §11); this port
    exists so retrieval code can depend on a stable shape, not so it can
    validate embedding-backed answers.
    """

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Batch-encode ``texts`` into one vector per text.

        Implementations SHOULD return vectors of a fixed, model-declared
        dimension and SHOULD NOT silently truncate or pad. Order is preserved:
        the i-th output vector corresponds to ``texts[i]``.
        """
        ...

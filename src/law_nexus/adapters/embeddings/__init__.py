"""Embedding infrastructure adapters."""

from __future__ import annotations

from law_nexus.adapters.embeddings.local_sentence_transformer import (
    LOCAL_SENTENCE_TRANSFORMER_NON_CLAIMS,
    LocalEmbeddingAdapterError,
    LocalEmbeddingDiagnostics,
    LocalSentenceTransformerEmbedder,
)

__all__ = [
    "LOCAL_SENTENCE_TRANSFORMER_NON_CLAIMS",
    "LocalEmbeddingAdapterError",
    "LocalEmbeddingDiagnostics",
    "LocalSentenceTransformerEmbedder",
]

"""Embedding infrastructure adapters."""

from __future__ import annotations

from law_nexus.adapters.embeddings.local_sentence_transformer import (
    LOCAL_SENTENCE_TRANSFORMER_NON_CLAIMS,
    LocalEmbeddingAdapterError,
    LocalEmbeddingDiagnostics,
    LocalSentenceTransformerEmbedder,
)
from law_nexus.adapters.embeddings.proof_environment import (
    EMBEDDING_PROOF_ENVIRONMENT_NON_CLAIMS,
    PackageAvailability,
    huggingface_cache_roots,
    import_name_for_requirement,
    model_cache_name,
    normalized_path,
    probe_package_availability,
    requirement_package_name,
    unique_paths,
    write_json_log,
)

__all__ = [
    "EMBEDDING_PROOF_ENVIRONMENT_NON_CLAIMS",
    "LOCAL_SENTENCE_TRANSFORMER_NON_CLAIMS",
    "LocalEmbeddingAdapterError",
    "LocalEmbeddingDiagnostics",
    "LocalSentenceTransformerEmbedder",
    "PackageAvailability",
    "huggingface_cache_roots",
    "import_name_for_requirement",
    "model_cache_name",
    "normalized_path",
    "probe_package_availability",
    "requirement_package_name",
    "unique_paths",
    "write_json_log",
]

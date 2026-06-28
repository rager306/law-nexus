"""Local sentence-transformers embedding adapter.

This adapter is a bounded infrastructure seam for local/open-weight embedding
models. It intentionally exposes diagnostics and non-claims because vectors are
retrieval signals, not legal evidence or answer authority.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast

from law_nexus.ports.embedder import Embedder

LOCAL_SENTENCE_TRANSFORMER_NON_CLAIMS = (
    "Does not use managed GigaChat or external embedding APIs.",
    "Does not prove legal correctness.",
    "Does not prove retrieval quality.",
    "Does not prove parser completeness.",
    "Does not prove production vector-index readiness.",
    "Does not persist raw vectors.",
    "Does not prove that a local model is installed or available.",
)


class LocalEmbeddingAdapterError(RuntimeError):
    """Raised when a local embedding adapter violates the port contract."""

    def __init__(self, code: str, message: str, *, failure_class: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.failure_class = failure_class


@dataclass(frozen=True)
class LocalEmbeddingDiagnostics:
    """Bounded diagnostics for local embedding adapter configuration/results."""

    model_id: str
    expected_vector_dimension: int | None
    observed_vector_dimension: int | None = None
    runtime_status: str = "configured"
    failure_class: str = "none"
    confirmed: bool = False
    managed_api_used: bool = False
    raw_vectors_persisted: bool = False
    network_used: bool = False
    diagnostic_codes: tuple[str, ...] = ()

    def to_report(self) -> dict[str, object]:
        """Return the stable diagnostic shape used by proof scripts."""

        return {
            "model_id": self.model_id,
            "runtime_status": self.runtime_status,
            "failure_class": self.failure_class,
            "expected_vector_dimension": self.expected_vector_dimension,
            "observed_vector_dimension": self.observed_vector_dimension,
            "confirmed": self.confirmed,
            "managed_api_used": self.managed_api_used,
            "raw_vectors_persisted": self.raw_vectors_persisted,
            "network_used": self.network_used,
            "diagnostic_codes": list(self.diagnostic_codes),
        }


class SentenceTransformerModel(Protocol):
    """Minimal model shape used by the local adapter."""

    def encode(self, texts: list[str], *, convert_to_numpy: bool = False) -> Sequence[Sequence[float]]:
        """Encode texts with order-preserving output."""
        ...


class SentenceTransformerLoader(Protocol):
    """Loader shape for dependency-injected tests and lazy runtime import."""

    def __call__(self, model_id: str, *, local_files_only: bool) -> SentenceTransformerModel:
        """Return a local sentence-transformers compatible model."""
        ...


def load_local_sentence_transformer(model_id: str, *, local_files_only: bool) -> SentenceTransformerModel:
    """Lazily import sentence-transformers in the adapter layer only."""

    sentence_transformers = __import__("sentence_transformers", fromlist=["SentenceTransformer"])
    model_cls = cast(Any, sentence_transformers).SentenceTransformer
    return cast(SentenceTransformerModel, model_cls(model_id, local_files_only=local_files_only))


class LocalSentenceTransformerEmbedder(Embedder):
    """Local sentence-transformers implementation of the Embedder port."""

    def __init__(
        self,
        *,
        model_id: str,
        expected_dimension: int | None,
        model_loader: SentenceTransformerLoader = load_local_sentence_transformer,
        local_files_only: bool = True,
    ) -> None:
        if expected_dimension is not None and expected_dimension <= 0:
            raise ValueError("expected_dimension must be positive when provided")
        self.model_id = model_id
        self.expected_dimension = expected_dimension
        self._model_loader = model_loader
        self._local_files_only = local_files_only
        self._model: SentenceTransformerModel | None = None
        self._observed_dimension: int | None = None

    def diagnostics(self) -> LocalEmbeddingDiagnostics:
        """Return bounded adapter diagnostics without exposing vector values."""

        return LocalEmbeddingDiagnostics(
            model_id=self.model_id,
            expected_vector_dimension=self.expected_dimension,
            observed_vector_dimension=self._observed_dimension,
        )

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts locally while enforcing count and dimension invariants."""

        if not texts:
            return []
        raw_vectors = self._load_model().encode(list(texts), convert_to_numpy=False)
        vectors = [[float(value) for value in vector] for vector in raw_vectors]
        if len(vectors) != len(texts):
            raise LocalEmbeddingAdapterError(
                "E_EMBEDDING_COUNT_MISMATCH",
                f"adapter returned {len(vectors)} vectors for {len(texts)} texts",
                failure_class="adapter_contract",
            )
        for index, vector in enumerate(vectors):
            self._validate_dimension(vector, index=index)
        return vectors

    def _load_model(self) -> SentenceTransformerModel:
        if self._model is None:
            self._model = self._model_loader(self.model_id, local_files_only=self._local_files_only)
        return self._model

    def _validate_dimension(self, vector: Sequence[float], *, index: int) -> None:
        observed = len(vector)
        if self._observed_dimension is None:
            self._observed_dimension = observed
        if self.expected_dimension is not None and observed != self.expected_dimension:
            raise LocalEmbeddingAdapterError(
                "E_EMBEDDING_DIMENSION_MISMATCH",
                f"vector {index} has dimension {observed}; expected {self.expected_dimension}",
                failure_class="adapter_contract",
            )
        if self._observed_dimension != observed:
            raise LocalEmbeddingAdapterError(
                "E_EMBEDDING_DIMENSION_MISMATCH",
                f"vector {index} has dimension {observed}; expected {self._observed_dimension}",
                failure_class="adapter_contract",
            )


__all__ = [
    "LOCAL_SENTENCE_TRANSFORMER_NON_CLAIMS",
    "LocalEmbeddingAdapterError",
    "LocalEmbeddingDiagnostics",
    "LocalSentenceTransformerEmbedder",
    "SentenceTransformerLoader",
    "SentenceTransformerModel",
    "load_local_sentence_transformer",
]

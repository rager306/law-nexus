from __future__ import annotations

from collections.abc import Sequence

import pytest

from law_nexus.adapters.embeddings.local_sentence_transformer import (
    LOCAL_SENTENCE_TRANSFORMER_NON_CLAIMS,
    LocalEmbeddingAdapterError,
    LocalSentenceTransformerEmbedder,
)
from law_nexus.ports.embedder import EMBEDDER_NON_CLAIMS, Embedder


class FakeModel:
    def __init__(self, vectors: Sequence[Sequence[float]]) -> None:
        self.vectors = vectors
        self.seen_texts: list[str] = []
        self.convert_to_numpy: bool | None = None

    def encode(self, texts: list[str], *, convert_to_numpy: bool = False) -> Sequence[Sequence[float]]:
        self.seen_texts = texts
        self.convert_to_numpy = convert_to_numpy
        return self.vectors[: len(texts)]


def test_embedder_port_declares_bounded_non_claims() -> None:
    assert "non-authoritative retrieval signal" in EMBEDDER_NON_CLAIMS
    assert "Does not prove legal correctness." in EMBEDDER_NON_CLAIMS
    assert "Does not persist raw vectors." in EMBEDDER_NON_CLAIMS


def test_local_sentence_transformer_adapter_preserves_order_and_metadata() -> None:
    model = FakeModel([[1, 0, 0.5], [0, 1, 0.25]])
    loader_calls: list[tuple[str, bool]] = []

    def loader(model_id: str, *, local_files_only: bool) -> FakeModel:
        loader_calls.append((model_id, local_files_only))
        return model

    embedder = LocalSentenceTransformerEmbedder(
        model_id="local/test-embedding",
        expected_dimension=3,
        model_loader=loader,
    )

    assert isinstance(embedder, Embedder)
    assert embedder.encode(["first", "second"]) == [[1.0, 0.0, 0.5], [0.0, 1.0, 0.25]]
    assert model.seen_texts == ["first", "second"]
    assert model.convert_to_numpy is False
    assert loader_calls == [("local/test-embedding", True)]

    diagnostics = embedder.diagnostics()
    assert diagnostics.to_report() == {
        "model_id": "local/test-embedding",
        "runtime_status": "configured",
        "failure_class": "none",
        "expected_vector_dimension": 3,
        "observed_vector_dimension": 3,
        "confirmed": False,
        "managed_api_used": False,
        "raw_vectors_persisted": False,
        "network_used": False,
        "diagnostic_codes": [],
    }


def test_local_sentence_transformer_adapter_rejects_wrong_vector_dimension() -> None:
    def loader(model_id: str, *, local_files_only: bool) -> FakeModel:
        return FakeModel([[1, 2]])

    embedder = LocalSentenceTransformerEmbedder(
        model_id="local/test-embedding",
        expected_dimension=3,
        model_loader=loader,
    )

    with pytest.raises(LocalEmbeddingAdapterError) as exc_info:
        embedder.encode(["bad dimension"])

    assert exc_info.value.code == "E_EMBEDDING_DIMENSION_MISMATCH"
    assert exc_info.value.failure_class == "adapter_contract"
    assert "expected 3" in str(exc_info.value)


def test_local_sentence_transformer_adapter_rejects_output_count_mismatch() -> None:
    def loader(model_id: str, *, local_files_only: bool) -> FakeModel:
        return FakeModel([[1, 2, 3]])

    embedder = LocalSentenceTransformerEmbedder(
        model_id="local/test-embedding",
        expected_dimension=3,
        model_loader=loader,
    )

    with pytest.raises(LocalEmbeddingAdapterError) as exc_info:
        embedder.encode(["one", "two"])

    assert exc_info.value.code == "E_EMBEDDING_COUNT_MISMATCH"
    assert exc_info.value.failure_class == "adapter_contract"


def test_local_adapter_non_claims_exclude_managed_api_and_raw_vectors() -> None:
    assert "Does not use managed GigaChat or external embedding APIs." in LOCAL_SENTENCE_TRANSFORMER_NON_CLAIMS
    assert "Does not persist raw vectors." in LOCAL_SENTENCE_TRANSFORMER_NON_CLAIMS
    assert "Does not prove retrieval quality." in LOCAL_SENTENCE_TRANSFORMER_NON_CLAIMS

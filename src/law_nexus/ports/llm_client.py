"""LLMClient port — non-authoritative generation + provider embedding.

[proposed] port contract per D046. LLM output is NON-AUTHORITATIVE per the LLM
Control Policy (prd/02_architecture.md §10): an LLMClient may only produce
candidate completions and candidate embeddings; nothing it returns is legal
authority. Structural lookup, temporal validity, citation resolution,
evidence verification, status checks, and source-existence checks MUST stay
deterministic and never route through this port.

The port declares only the *shape* providers must satisfy; real providers
(MiniMax / OpenAI-compatible) are wired in the adapter layer.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Candidate-only LLM surface (generation + provider embedding).

    Every method here returns NON-AUTHORITATIVE output: it is a candidate that
    downstream verification (prd/02_architecture.md §10) MUST check before use.
    Only these tasks may use this port: natural-language explanation,
    query-rewrite candidates, ambiguous-intent clarification, summarisation of
    already-verified evidence, and candidate semantic extraction pending
    verification.
    """

    def complete(self, prompt: str) -> str:
        """Generate a candidate completion for ``prompt``.

        The returned text is a non-authoritative candidate: it MUST be verified
        against EvidenceSpan / SourceBlock / ActEdition / temporal status
        before it may support an answer. It is never final authority.
        """
        ...

    def embed(self, text: str) -> list[float]:
        """Embed ``text`` into a vector via the provider's embedding model.

        The vector is a non-authoritative candidate signal for retrieval /
        similarity; it is not evidence and not legal authority. Use
        :class:`~law_nexus.ports.embedder.Embedder` for corpus indexing.
        """
        ...

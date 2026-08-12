"""Pure Review Case ports.

Outer adapters implement these Protocols. This module must not import
filesystem, codecs, CLI, Governor, GSD, or product-domain packages.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from law_nexus_harness.review_case.domain import EventLedgerEnvelope, ReviewEvent, ReviewPacket


class ReviewCasePortError(Exception):
    """Structured port failure without raw review bytes or secrets."""

    def __init__(self, *, code: str, operation: str, message: str) -> None:
        if not code or not operation or not message:
            raise ValueError("ReviewCasePortError requires code, operation, and message")
        self.code = code
        self.operation = operation
        self.message = message
        super().__init__(f"{operation}:{code}: {message}")


@runtime_checkable
class ReviewSourceReader(Protocol):
    def read_bytes(self, repo_relative_path: str) -> bytes:
        """Return immutable source bytes for a repository-relative path."""
        ...


@runtime_checkable
class ContentHasher(Protocol):
    def sha256(self, data: bytes) -> str:
        """Return lowercase hex SHA-256 for the given bytes."""
        ...


@runtime_checkable
class ReviewPacketStore(Protocol):
    def add(self, packet: ReviewPacket) -> None:
        """Persist a new ReviewPacket. Fail closed on duplicates."""
        ...

    def get(self, packet_id: str) -> ReviewPacket:
        """Load one ReviewPacket by id."""
        ...

    def list_all(self) -> tuple[ReviewPacket, ...]:
        """Return all stored packets in deterministic order."""
        ...


@runtime_checkable
class EventLedger(Protocol):
    def append(
        self,
        packet_id: str,
        event: ReviewEvent,
        *,
        source_revision: str,
    ) -> EventLedgerEnvelope:
        """Append one event envelope for a packet. Fail closed on races/forks."""
        ...

    def list_envelopes(self, packet_id: str) -> tuple[EventLedgerEnvelope, ...]:
        """Return ordered envelopes for a packet after integrity checks."""
        ...

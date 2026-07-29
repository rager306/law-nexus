"""Offline retrieval case builder port contracts.

[bounded] M076 S10 contracts for deterministic offline citation retrieval
case fixtures. Cases are proof fixtures, not retrieval-quality or legal
correctness claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

OFFLINE_RETRIEVAL_CASE_NON_CLAIMS: tuple[str, ...] = (
    "Offline retrieval cases are not product retrieval quality proof.",
    "Offline retrieval cases do not prove legal citation correctness.",
    "Offline retrieval cases do not validate parser extraction correctness.",
)


@dataclass(frozen=True)
class OfflineRetrievalSourceArtifact:
    """Portable source artifact digest supplied by a wrapper or adapter."""

    path: str
    sha256: str

    def as_dict(self) -> dict[str, str]:
        """Return the fixture JSON representation."""

        return {"path": self.path, "sha256": self.sha256}


@dataclass(frozen=True)
class OfflineRetrievalCaseBuildRequest:
    """Input data for deterministic offline retrieval case assembly."""

    real_cases: Mapping[str, Any]
    hierarchy_records: Sequence[Mapping[str, Any]]
    source_artifacts: Sequence[OfflineRetrievalSourceArtifact]

"""Real artifact retrieval case builder port contracts.

[bounded] M076 S11 contracts for deterministic real-artifact retrieval
fixture assembly. Cases are proof fixtures, not retrieval-quality, parser, or
legal-correctness claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

REAL_ARTIFACT_RETRIEVAL_CASE_NON_CLAIMS: tuple[str, ...] = (
    "Does not prove product retrieval quality.",
    "Does not prove parser completeness.",
    "Does not prove legal-answer correctness.",
    "Does not prove legal interpretation authority.",
    "Does not prove production FalkorDB runtime behavior.",
    "Does not prove production graph schema readiness.",
    "Does not prove local embedding quality.",
    "Does not close GATE-G008.",
    "Does not close GATE-G011.",
    "Does not make LLM output legal authority.",
    "Does not make proof-local IDs production IDs.",
)


@dataclass(frozen=True)
class RealArtifactSourceArtifact:
    """Portable source artifact digest supplied by a wrapper or adapter."""

    path: str
    sha256: str

    def as_dict(self) -> dict[str, str]:
        """Return the fixture JSON representation."""

        return {"path": self.path, "sha256": self.sha256}


@dataclass(frozen=True)
class RealArtifactRetrievalCaseBuildRequest:
    """Input data for deterministic real artifact retrieval case assembly."""

    hierarchy_summary: Mapping[str, Any]
    staging_graph: Mapping[str, Any]
    hierarchy_records: Sequence[Mapping[str, Any]]
    source_artifacts: Sequence[RealArtifactSourceArtifact]

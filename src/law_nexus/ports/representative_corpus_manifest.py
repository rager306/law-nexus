"""Representative corpus manifest port contracts.

[bounded] M076 S12 contracts for deterministic representative corpus manifest
assembly. The manifest is a proof-planning and handoff artifact only; it is
not retrieval-quality, parser-completeness, or legal-answer correctness proof.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

REPRESENTATIVE_CORPUS_MANIFEST_NON_CLAIMS: tuple[str, ...] = (
    "does not prove product retrieval quality",
    "does not prove parser completeness",
    "does not prove legal-answer correctness",
    "does not prove legal interpretation authority",
    "does not prove production FalkorDB runtime behavior",
    "does not prove production graph schema readiness",
    "does not prove local embedding quality",
    "does not compute runtime benchmark metrics",
    "does not allow managed GigaChat API fallback",
    "does not allow managed embedding API fallback",
    "does not persist raw legal text, raw query prompts, vectors, provider payloads, raw FalkorDB rows, or generated legal advice",
    "does not close GATE-G011",
    "does not close GATE-G008",
    "does not make LLM output legal authority",
    "does not make proof-local IDs production IDs",
)


@dataclass(frozen=True)
class RepresentativeCorpusSourceArtifact:
    """Portable digest for a manifest input artifact."""

    path: str
    sha256: str

    def as_dict(self) -> dict[str, str]:
        """Return the manifest JSON representation."""

        return {"path": self.path, "sha256": self.sha256}


@dataclass(frozen=True)
class RepresentativeCorpusManifestBuildRequest:
    """Inputs required by the representative corpus manifest builder.

    Wrappers/adapters own file IO and hashing. The application use case receives
    already loaded JSON objects plus repository-relative source artifact digests.
    """

    source_fixture_inventory: Mapping[str, Any]
    local_retrieval_quality_benchmark: Mapping[str, Any]
    offline_citation_retrieval_cases: Mapping[str, Any]
    real_artifact_retrieval_cases: Mapping[str, Any]
    source_artifacts: Sequence[RepresentativeCorpusSourceArtifact]

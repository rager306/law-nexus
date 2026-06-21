"""law_nexus.domain — D046 core domain models (Pydantic v2).

[proposed] lifecycle per D098: these are D046 *forms* (fields + basic
validation, no logic) that harden once real parser data arrives. They do NOT
validate R035/R037/R038 and carry zero infrastructure imports — the domain
knows only ``pydantic`` and ``typing`` (plus intra-domain references).

Evidence chain (prd/02_architecture.md §4):

    NormStatement → EvidenceSpan → LegalUnit → SourceBlock → SourceDocument
                                          └→ ActEdition
"""

from __future__ import annotations

from law_nexus.domain.act_edition import ActEdition, ActStatus, TemporalConfidence
from law_nexus.domain.citation import Citation
from law_nexus.domain.evidence_span import EvidenceLifecycle, EvidenceSpan
from law_nexus.domain.legal_unit import LegalUnit, LegalUnitType
from law_nexus.domain.norm_statement import (
    ExtractionMethod,
    NormModality,
    NormStatement,
    VerificationStatus,
)
from law_nexus.domain.source_block import SourceBlock, SourceBlockType
from law_nexus.domain.source_document import (
    SourceDocument,
    SourceProvenanceClass,
)
from law_nexus.domain.source_hierarchy import (
    SOURCE_HIERARCHY,
    SourceLevel,
    SourceTier,
)

__all__ = [
    # act_edition
    "ActEdition",
    "ActStatus",
    "TemporalConfidence",
    # citation
    "Citation",
    # evidence_span
    "EvidenceLifecycle",
    "EvidenceSpan",
    # legal_unit
    "LegalUnit",
    "LegalUnitType",
    # norm_statement
    "ExtractionMethod",
    "NormModality",
    "NormStatement",
    "VerificationStatus",
    # source_block
    "SourceBlock",
    "SourceBlockType",
    # source_document
    "SourceDocument",
    "SourceProvenanceClass",
    # source_hierarchy
    "SOURCE_HIERARCHY",
    "SourceLevel",
    "SourceTier",
]

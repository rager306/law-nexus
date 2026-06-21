"""T02 smoke check: instantiate every domain model from sample dicts.

Not a shipped test — ad-hoc verification that the [proposed] D046 forms can be
constructed from plain data. Run via ``PYTHONPATH=src python _smoke_t02.py``.
"""

from __future__ import annotations

from datetime import date

from law_nexus.domain import (
    ActEdition,
    ActStatus,
    Citation,
    EvidenceSpan,
    LegalUnit,
    LegalUnitType,
    NormModality,
    NormStatement,
    SourceBlock,
    SourceBlockType,
    SourceDocument,
    SourceLevel,
    SourceProvenanceClass,
    SourceTier,
)

sd = SourceDocument(
    source_id="sd-1",
    sha256="abc123",
    source_system="Гарант",
    source_provenance_class=SourceProvenanceClass.commercial_consolidated,
    act_number="44-ФЗ",
    edition_date=date(2026, 1, 1),
)
print("SourceDocument OK", sd.source_id)

sb = SourceBlock(
    block_id="sb-1",
    source_document_id="sd-1",
    block_type=SourceBlockType.article,
    order=0,
    text="Заказчик обязан...",
    char_start=0,
    char_end=20,
)
print("SourceBlock OK", sb.block_id)

cit = Citation(article="34", part="1", point="2")
print("Citation OK", cit.article)

ae = ActEdition(
    edition_id="ae-1",
    legal_document_id="act-44fz",
    source_document_id="sd-1",
    edition_date=date(2026, 1, 1),
    valid_from=date(2026, 1, 1),
    status=ActStatus.active,
)
print("ActEdition OK", ae.edition_id)

lu = LegalUnit(
    unit_id="lu-1",
    legal_document_id="act-44fz",
    unit_type=LegalUnitType.part,
    citation=cit,
    edition_id="ae-1",
)
print("LegalUnit OK", lu.unit_id)

ev = EvidenceSpan(
    span_id="ev-1",
    source_document_id="sd-1",
    source_block_id="sb-1",
    source_sha256="abc123",
    legal_unit_id="lu-1",
    act_edition_id="ae-1",
    char_start=0,
    char_end=20,
)
print("EvidenceSpan OK", ev.span_id)

ns = NormStatement(
    statement_id="ns-1",
    modality=NormModality.obligation,
    negated=False,
    source_unit_ids=["lu-1"],
    evidence_span_ids=["ev-1"],
)
print("NormStatement OK", ns.statement_id)

tier = SourceTier(level=SourceLevel.federal_law_or_code, rank=SourceLevel.federal_law_or_code)
print("SourceTier OK", tier.level.name, tier.rank)

print("ALL MODELS INSTANTIATED")

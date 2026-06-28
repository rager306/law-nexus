#!/usr/bin/env python3
"""Compatibility wrapper for parser record contracts.

Reusable parser record models and JSONL loading helpers live in
``law_nexus.adapters.sources.parser_records``. This script remains so existing
``scripts/`` imports keep working. These models validate record shape and
provenance only; they do not claim parser completeness, legal correctness,
product ETL readiness, or graph load/runtime readiness.
"""

from __future__ import annotations

from law_nexus.adapters.sources.parser_records import (
    MAX_DIAGNOSTICS_PER_FILE,
    MAX_EXCERPT_CHARS,
    PARSER_RECORD_ADAPTER,
    SCHEMA_VERSION,
    ConsultantHierarchyLevel,
    ConsultantHierarchyRecord,
    DocumentRecord,
    LocationRecord,
    MarkerMetadataRecord,
    ParserRecord,
    ParserRecordBase,
    RelationCandidateRecord,
    RelationCandidateStatus,
    Sha256,
    SourceBlockRecord,
    SourceKind,
    StrictRecordModel,
    dumps_jsonl_record,
    json_error_to_diagnostic,
    load_jsonl_records,
    parse_parser_record,
    validation_error_to_diagnostic,
)

__all__ = [
    "SCHEMA_VERSION",
    "MAX_EXCERPT_CHARS",
    "MAX_DIAGNOSTICS_PER_FILE",
    "SourceKind",
    "RelationCandidateStatus",
    "ConsultantHierarchyLevel",
    "Sha256",
    "StrictRecordModel",
    "LocationRecord",
    "ParserRecordBase",
    "DocumentRecord",
    "SourceBlockRecord",
    "MarkerMetadataRecord",
    "ConsultantHierarchyRecord",
    "RelationCandidateRecord",
    "ParserRecord",
    "PARSER_RECORD_ADAPTER",
    "parse_parser_record",
    "dumps_jsonl_record",
    "validation_error_to_diagnostic",
    "json_error_to_diagnostic",
    "load_jsonl_records",
]

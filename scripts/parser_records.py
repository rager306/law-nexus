#!/usr/bin/env python3
"""Strict parser record contracts for LegalGraph Nexus parser boundaries.

These models validate record shape and provenance only. They intentionally do not
claim parser completeness, legal correctness, product ETL readiness, or graph
load/runtime readiness.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "legalgraph-parser-record/v1"
MAX_EXCERPT_CHARS = 500
MAX_DIAGNOSTICS_PER_FILE = 100

SourceKind: TypeAlias = Literal["garant-odt", "consultant-wordml-xml"]
RelationCandidateStatus: TypeAlias = Literal["candidate", "needs-review", "rejected"]
Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class StrictRecordModel(BaseModel):
    """Base class that rejects coercion and unexpected boundary fields."""

    model_config = ConfigDict(extra="forbid", strict=True)


class LocationRecord(StrictRecordModel):
    """Bounded locator for a source block within a parser source."""

    selector: str = Field(min_length=1)
    label: str | None = Field(default=None, min_length=1)


class ParserRecordBase(StrictRecordModel):
    """Common provenance and non-claim fields shared by all parser records."""

    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    id: str = Field(min_length=1)
    source_kind: SourceKind
    source_path: str = Field(min_length=1)
    source_sha256: Sha256
    non_authoritative: Literal[True] = True
    non_claims: list[str] = Field(min_length=1)

    @field_validator("source_path")
    @classmethod
    def validate_repository_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if value.startswith("/") or path.is_absolute():
            raise ValueError("source_path must be repository-relative, not absolute")
        if any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError("source_path must not contain empty, current, or parent traversal parts")
        return value

    @field_validator("non_claims")
    @classmethod
    def validate_non_claims(cls, value: list[str]) -> list[str]:
        if any(not claim.strip() for claim in value):
            raise ValueError("non_claims must contain non-empty non-claim statements")
        return value


class DocumentRecord(ParserRecordBase):
    """Document-level parser boundary record."""

    record_kind: Literal["document"]
    id: str = Field(pattern=r"^DOC-.+")
    title: str = Field(min_length=1, max_length=240)


class SourceBlockRecord(ParserRecordBase):
    """Bounded source block extracted from a canonical parser fixture."""

    record_kind: Literal["source_block"]
    id: str = Field(pattern=r"^BLOCK-.+")
    document_id: str = Field(pattern=r"^DOC-.+")
    source_member: str | None = Field(default=None, min_length=1)
    order_index: int = Field(ge=0)
    location: LocationRecord
    excerpt: str = Field(min_length=1, max_length=MAX_EXCERPT_CHARS)
    excerpt_sha256: Sha256

    @model_validator(mode="after")
    def validate_source_member_for_source_kind(self) -> SourceBlockRecord:
        if self.source_kind == "garant-odt" and self.source_member != "content.xml":
            raise ValueError('garant-odt source blocks must use source_member="content.xml"')
        return self


class RelationCandidateRecord(ParserRecordBase):
    """Candidate-only relation record from bounded source evidence."""

    record_kind: Literal["relation_candidate"]
    id: str = Field(pattern=r"^REL-.+")
    source_member: str | None = Field(default=None, min_length=1)
    source_block_id: str = Field(pattern=r"^BLOCK-.+")
    subject_ref: str = Field(min_length=1)
    object_ref: str = Field(min_length=1)
    relation_type: str = Field(min_length=1)
    status: RelationCandidateStatus
    evidence_excerpt: str = Field(min_length=1, max_length=MAX_EXCERPT_CHARS)
    evidence_sha256: Sha256


ParserRecord: TypeAlias = Annotated[
    DocumentRecord | SourceBlockRecord | RelationCandidateRecord,
    Field(discriminator="record_kind"),
]
PARSER_RECORD_ADAPTER = TypeAdapter(ParserRecord)


def parse_parser_record(payload: dict[str, Any]) -> ParserRecord:
    """Validate one parser record through the discriminated union adapter."""

    return PARSER_RECORD_ADAPTER.validate_python(payload)


def dumps_jsonl_record(payload: dict[str, Any]) -> str:
    """Serialize a JSONL record deterministically for tests and fixtures."""

    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validation_error_to_diagnostic(
    *, file_path: Path, line_number: int, payload: dict[str, Any], error: dict[str, Any]
) -> dict[str, Any]:
    """Convert one Pydantic error into a compact deterministic diagnostic."""

    location = [str(part) for part in error.get("loc", ()) if str(part) not in {"tagged-union"}]
    if location and location[0] in {"document", "source_block", "relation_candidate"}:
        location = location[1:]
    field = ".".join(location) if location else "record"
    return {
        "file": str(file_path),
        "line": line_number,
        "record_id": payload.get("id"),
        "record_kind": payload.get("record_kind"),
        "field": field,
        "rule": error.get("type", "validation_error"),
        "source_path": payload.get("source_path"),
        "message": error.get("msg", "validation error"),
    }


def json_error_to_diagnostic(*, file_path: Path, line_number: int, message: str) -> dict[str, Any]:
    """Return a diagnostic for one malformed JSONL line."""

    return {
        "file": str(file_path),
        "line": line_number,
        "record_id": None,
        "record_kind": None,
        "field": "record",
        "rule": "json_invalid",
        "source_path": None,
        "message": message,
    }


def load_jsonl_records(path: Path, *, max_diagnostics: int = MAX_DIAGNOSTICS_PER_FILE) -> tuple[list[ParserRecord], list[dict[str, Any]]]:
    """Load parser records from JSONL with bounded deterministic diagnostics."""

    records: list[ParserRecord] = []
    diagnostics: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                diagnostics.append(
                    json_error_to_diagnostic(
                        file_path=path,
                        line_number=line_number,
                        message=exc.msg,
                    )
                )
                if len(diagnostics) >= max_diagnostics:
                    break
                continue
            if not isinstance(payload, dict):
                diagnostics.append(
                    {
                        "file": str(path),
                        "line": line_number,
                        "record_id": None,
                        "record_kind": None,
                        "field": "record",
                        "rule": "json_type",
                        "source_path": None,
                        "message": "JSONL line must decode to an object",
                    }
                )
                if len(diagnostics) >= max_diagnostics:
                    break
                continue
            try:
                records.append(parse_parser_record(payload))
            except ValidationError as exc:
                first_error = exc.errors(include_url=False)[0]
                diagnostics.append(
                    validation_error_to_diagnostic(
                        file_path=path,
                        line_number=line_number,
                        payload=payload,
                        error=first_error,
                    )
                )
                if len(diagnostics) >= max_diagnostics:
                    break
    return records, diagnostics

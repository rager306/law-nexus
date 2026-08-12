"""Pure Review Case domain values and construction invariants.

Process-control types only. No I/O, codecs, CLI, Governor, GSD, or product
domain semantics. Authority remains external: packets are always non-authoritative.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

SCHEMA_VERSION = "review-case/v1"

_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_GIT_REV_RE = re.compile(r"^[a-f0-9]{40}$")
_FORBIDDEN_PATH_PREFIXES = (
    ".gsd/",
    ".agents/",
    "old_project/",
    "python_archive/",
    "prd/archive/",
)


class SourceKind(StrEnum):
    HUMAN_EXTERNAL = "human_external"
    HUMAN_INTERNAL = "human_internal"
    MIXED = "mixed"
    TOOL_GENERATED = "tool_generated"


class NormalizationStatus(StrEnum):
    DRAFT_EXTRACTED = "draft_extracted"
    SOURCE_VERIFIED = "source_verified"
    HUMAN_REVIEWED = "human_reviewed"
    STALE = "stale"


class NormalizationMethod(StrEnum):
    MANUAL = "manual"
    SCRIPT_ASSISTED = "script_assisted"
    LLM_ASSISTED = "llm_assisted"


class FindingKind(StrEnum):
    STRENGTH = "strength"
    DEFECT = "defect"
    GAP = "gap"
    RISK = "risk"
    RECOMMENDATION = "recommendation"
    QUESTION = "question"
    RESEARCH_NEED = "research_need"
    DECISION_NEED = "decision_need"
    ROADMAP_PROPOSAL = "roadmap_proposal"


class ConcernClass(StrEnum):
    DOCS = "docs"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    EVIDENCE = "evidence"
    PROCESS = "process"


class ReviewerSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProofClass(StrEnum):
    DOCS = "docs"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    EVIDENCE = "evidence"
    PROCESS = "process"


class DispositionStatus(StrEnum):
    OPEN = "open"
    NEEDS_DISCUSSION = "needs_discussion"
    NEEDS_RESEARCH = "needs_research"
    ACCEPTED_AS_GAP = "accepted_as_gap"
    ACCEPTED_AS_REQUIREMENT_CANDIDATE = "accepted_as_requirement_candidate"
    ACCEPTED_AS_DECISION_CANDIDATE = "accepted_as_decision_candidate"
    ACCEPTED_AS_PROCESS_DEFECT = "accepted_as_process_defect"
    ALREADY_SATISFIED = "already_satisfied"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    DUPLICATE = "duplicate"
    SUPERSEDED = "superseded"
    NOT_APPLICABLE = "not_applicable"


class ExecutionStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    UNPLANNED = "unplanned"
    PLANNED = "planned"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    IMPLEMENTED = "implemented"
    CANCELLED = "cancelled"


class VerificationStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    UNVERIFIED = "unverified"
    INCONCLUSIVE = "inconclusive"
    FAILED = "failed"
    PASSED_BOUNDED = "passed_bounded"
    PASSED_SMOKE = "passed_smoke"
    PASSED_VALIDATED = "passed_validated"
    STALE = "stale"


class CandidateSurface(StrEnum):
    TSG = "tsg"
    ADR = "adr"
    PRODUCT = "product"
    REQUIREMENT = "requirement"
    ASSESSMENT = "assessment"
    CODE = "code"
    ROADMAP = "roadmap"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class ReviewCaseViolation:
    code: str
    field_path: str
    message: str
    value: object | None = None


class ReviewCaseValidationError(ValueError):
    """One or more pure construction invariants failed."""

    def __init__(self, violations: Sequence[ReviewCaseViolation]) -> None:
        if not violations:
            raise ValueError("ReviewCaseValidationError requires at least one violation")
        self.violations = tuple(violations)
        summary = "; ".join(
            f"{item.field_path}: {item.code} ({item.message})" for item in self.violations
        )
        super().__init__(summary)


def _collect(violations: list[ReviewCaseViolation], *items: ReviewCaseViolation | None) -> None:
    for item in items:
        if item is not None:
            violations.append(item)


def _raise_if(violations: Iterable[ReviewCaseViolation]) -> None:
    material = tuple(violations)
    if material:
        raise ReviewCaseValidationError(material)


def _require_nonempty_text(value: str, *, field_path: str, code: str) -> ReviewCaseViolation | None:
    if not isinstance(value, str) or not value.strip():
        return ReviewCaseViolation(code, field_path, "expected non-empty text", value)
    return None


def _require_id(value: str, *, field_path: str) -> ReviewCaseViolation | None:
    if not isinstance(value, str) or not value.strip():
        return ReviewCaseViolation("empty_id", field_path, "expected non-empty stable id", value)
    return None


def _validate_repo_relative_path(path: str, *, field_path: str) -> ReviewCaseViolation | None:
    if not isinstance(path, str) or not path.strip():
        return ReviewCaseViolation("invalid_path", field_path, "path must be non-empty", path)
    if (
        "\\" in path
        or ":" in path
        or any(character.isspace() for character in path)
        or path.startswith("/")
        or path.startswith("~")
    ):
        return ReviewCaseViolation(
            "invalid_path",
            field_path,
            "path must be repository-relative POSIX without absolute prefix",
            path,
        )
    if any(part in {"", ".", ".."} for part in path.split("/")):
        return ReviewCaseViolation(
            "invalid_path",
            field_path,
            "path must not contain empty, '.', or '..' segments",
            path,
        )
    lowered = path.lower()
    if any(
        lowered == prefix.rstrip("/") or lowered.startswith(prefix)
        for prefix in _FORBIDDEN_PATH_PREFIXES
    ):
        return ReviewCaseViolation(
            "invalid_path",
            field_path,
            "path targets a local-only or historical surface",
            path,
        )
    return None


def _validate_sha256(value: str, *, field_path: str) -> ReviewCaseViolation | None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        return ReviewCaseViolation(
            "invalid_sha256",
            field_path,
            "expected 64 lowercase hexadecimal characters",
            value,
        )
    return None


def _validate_git_revision(value: str, *, field_path: str) -> ReviewCaseViolation | None:
    if not isinstance(value, str) or _GIT_REV_RE.fullmatch(value) is None:
        return ReviewCaseViolation(
            "invalid_git_revision",
            field_path,
            "expected 40 lowercase hexadecimal characters",
            value,
        )
    return None


def _validate_timestamp(value: str, *, field_path: str) -> ReviewCaseViolation | None:
    if not isinstance(value, str) or "T" not in value:
        return ReviewCaseViolation(
            "invalid_timestamp",
            field_path,
            "expected ISO-8601 date-time with explicit timezone",
            value,
        )
    candidate = value
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return ReviewCaseViolation(
            "invalid_timestamp",
            field_path,
            "timestamp is not a valid ISO-8601 date-time",
            value,
        )
    if parsed.tzinfo is None:
        return ReviewCaseViolation(
            "invalid_timestamp",
            field_path,
            "timestamp must include an explicit timezone",
            value,
        )
    return None


def _validate_line_range(
    line_start: int,
    line_end: int,
    *,
    field_path: str,
) -> ReviewCaseViolation | None:
    if type(line_start) is not int or type(line_end) is not int:
        return ReviewCaseViolation(
            "invalid_line_range",
            field_path,
            "line bounds must be integers",
            (line_start, line_end),
        )
    if line_start < 1 or line_end < line_start:
        return ReviewCaseViolation(
            "invalid_line_range",
            field_path,
            "expected line_start >= 1 and line_end >= line_start",
            (line_start, line_end),
        )
    return None


def _validate_non_claims(
    non_claims: Sequence[str],
    *,
    field_path: str,
) -> list[ReviewCaseViolation]:
    violations: list[ReviewCaseViolation] = []
    if not non_claims:
        violations.append(
            ReviewCaseViolation(
                "missing_non_claims",
                field_path,
                "at least one non-claim is required",
                non_claims,
            )
        )
        return violations
    for index, item in enumerate(non_claims):
        _collect(
            violations,
            _require_nonempty_text(item, field_path=f"{field_path}[{index}]", code="empty_text"),
        )
    return violations


@dataclass(frozen=True, slots=True)
class ReviewSource:
    path: str
    content_sha256: str
    reviewed_git_revision: str
    received_at: str
    source_kind: SourceKind

    def __post_init__(self) -> None:
        violations: list[ReviewCaseViolation] = []
        _collect(
            violations,
            _validate_repo_relative_path(self.path, field_path="source.path"),
            _validate_sha256(self.content_sha256, field_path="source.content_sha256"),
            _validate_git_revision(
                self.reviewed_git_revision,
                field_path="source.reviewed_git_revision",
            ),
            _validate_timestamp(self.received_at, field_path="source.received_at"),
        )
        if not isinstance(self.source_kind, SourceKind):
            violations.append(
                ReviewCaseViolation(
                    "invalid_enum",
                    "source.source_kind",
                    "expected SourceKind",
                    self.source_kind,
                )
            )
        _raise_if(violations)


@dataclass(frozen=True, slots=True)
class NormalizationRecord:
    status: NormalizationStatus
    method: NormalizationMethod
    source_hash: str
    extractor_version: str | None = None

    def __post_init__(self) -> None:
        violations: list[ReviewCaseViolation] = []
        if not isinstance(self.status, NormalizationStatus):
            violations.append(
                ReviewCaseViolation(
                    "invalid_enum",
                    "normalization.status",
                    "expected NormalizationStatus",
                    self.status,
                )
            )
        if not isinstance(self.method, NormalizationMethod):
            violations.append(
                ReviewCaseViolation(
                    "invalid_enum",
                    "normalization.method",
                    "expected NormalizationMethod",
                    self.method,
                )
            )
        _collect(
            violations,
            _validate_sha256(self.source_hash, field_path="normalization.source_hash"),
        )
        if self.extractor_version is not None:
            _collect(
                violations,
                _require_nonempty_text(
                    self.extractor_version,
                    field_path="normalization.extractor_version",
                    code="empty_text",
                ),
            )
        _raise_if(violations)


@dataclass(frozen=True, slots=True)
class SourceSpan:
    path: str
    line_start: int
    line_end: int
    quote_sha256: str
    heading: str | None = None

    def __post_init__(self) -> None:
        violations: list[ReviewCaseViolation] = []
        _collect(
            violations,
            _validate_repo_relative_path(self.path, field_path="source_span.path"),
            _validate_line_range(
                self.line_start,
                self.line_end,
                field_path="source_span.line_range",
            ),
            _validate_sha256(self.quote_sha256, field_path="source_span.quote_sha256"),
        )
        if self.heading is not None:
            _collect(
                violations,
                _require_nonempty_text(
                    self.heading,
                    field_path="source_span.heading",
                    code="empty_text",
                ),
            )
        _raise_if(violations)


@dataclass(frozen=True, slots=True)
class CandidateTarget:
    surface: CandidateSurface
    id: str
    note: str | None = None

    def __post_init__(self) -> None:
        violations: list[ReviewCaseViolation] = []
        if not isinstance(self.surface, CandidateSurface):
            violations.append(
                ReviewCaseViolation(
                    "invalid_enum",
                    "candidate_target.surface",
                    "expected CandidateSurface",
                    self.surface,
                )
            )
        _collect(violations, _require_id(self.id, field_path="candidate_target.id"))
        if self.note is not None:
            _collect(
                violations,
                _require_nonempty_text(
                    self.note,
                    field_path="candidate_target.note",
                    code="empty_text",
                ),
            )
        _raise_if(violations)


@dataclass(frozen=True, slots=True)
class Finding:
    finding_id: str
    kind: FindingKind
    concern_class: ConcernClass
    reviewer_severity: ReviewerSeverity
    summary: str
    source_spans: tuple[SourceSpan, ...]
    candidate_targets: tuple[CandidateTarget, ...]
    required_proof_class: ProofClass
    normalization_status: NormalizationStatus
    disposition_status: DispositionStatus
    execution_status: ExecutionStatus
    verification_status: VerificationStatus
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        violations: list[ReviewCaseViolation] = []
        _collect(
            violations,
            _require_id(self.finding_id, field_path="finding.finding_id"),
            _require_nonempty_text(
                self.summary,
                field_path="finding.summary",
                code="empty_text",
            ),
        )
        enum_checks = (
            (self.kind, FindingKind, "finding.kind"),
            (self.concern_class, ConcernClass, "finding.concern_class"),
            (self.reviewer_severity, ReviewerSeverity, "finding.reviewer_severity"),
            (self.required_proof_class, ProofClass, "finding.required_proof_class"),
            (self.normalization_status, NormalizationStatus, "finding.normalization_status"),
            (self.disposition_status, DispositionStatus, "finding.disposition_status"),
            (self.execution_status, ExecutionStatus, "finding.execution_status"),
            (self.verification_status, VerificationStatus, "finding.verification_status"),
        )
        for value, enum_type, path in enum_checks:
            if not isinstance(value, enum_type):
                violations.append(
                    ReviewCaseViolation(
                        "invalid_enum",
                        path,
                        f"expected {enum_type.__name__}",
                        value,
                    )
                )
        collection_checks = (
            (self.source_spans, "finding.source_spans"),
            (self.candidate_targets, "finding.candidate_targets"),
            (self.non_claims, "finding.non_claims"),
        )
        for value, path in collection_checks:
            if not isinstance(value, tuple):
                violations.append(
                    ReviewCaseViolation(
                        "invalid_collection",
                        path,
                        "expected immutable tuple",
                        type(value).__name__,
                    )
                )
        if not self.source_spans:
            violations.append(
                ReviewCaseViolation(
                    "missing_source_spans",
                    "finding.source_spans",
                    "at least one source span is required",
                    self.source_spans,
                )
            )
        for index, span in enumerate(
            self.source_spans if isinstance(self.source_spans, tuple) else ()
        ):
            if not isinstance(span, SourceSpan):
                violations.append(
                    ReviewCaseViolation(
                        "invalid_type",
                        f"finding.source_spans[{index}]",
                        "expected SourceSpan",
                        span,
                    )
                )
        for index, target in enumerate(
            self.candidate_targets if isinstance(self.candidate_targets, tuple) else ()
        ):
            if not isinstance(target, CandidateTarget):
                violations.append(
                    ReviewCaseViolation(
                        "invalid_type",
                        f"finding.candidate_targets[{index}]",
                        "expected CandidateTarget",
                        target,
                    )
                )
        if isinstance(self.non_claims, tuple):
            violations.extend(
                _validate_non_claims(self.non_claims, field_path="finding.non_claims")
            )
        _raise_if(violations)


@dataclass(frozen=True, slots=True)
class ReviewPacket:
    packet_id: str
    source: ReviewSource
    normalization: NormalizationRecord
    non_claims: tuple[str, ...]
    findings: tuple[Finding, ...]
    schema_version: str = field(default=SCHEMA_VERSION, init=False)
    authoritative: bool = field(default=False, init=False)
    authority_required: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        violations: list[ReviewCaseViolation] = []
        _collect(violations, _require_id(self.packet_id, field_path="packet_id"))
        if not isinstance(self.source, ReviewSource):
            violations.append(
                ReviewCaseViolation(
                    "invalid_type",
                    "source",
                    "expected ReviewSource",
                    self.source,
                )
            )
        if not isinstance(self.normalization, NormalizationRecord):
            violations.append(
                ReviewCaseViolation(
                    "invalid_type",
                    "normalization",
                    "expected NormalizationRecord",
                    self.normalization,
                )
            )
        if (
            isinstance(self.source, ReviewSource)
            and isinstance(self.normalization, NormalizationRecord)
            and self.normalization.source_hash != self.source.content_sha256
        ):
            violations.append(
                ReviewCaseViolation(
                    "source_hash_mismatch",
                    "normalization.source_hash",
                    "normalization.source_hash must equal source.content_sha256",
                    self.normalization.source_hash,
                )
            )
        if not isinstance(self.non_claims, tuple):
            violations.append(
                ReviewCaseViolation(
                    "invalid_collection",
                    "non_claims",
                    "expected immutable tuple",
                    type(self.non_claims).__name__,
                )
            )
        else:
            violations.extend(_validate_non_claims(self.non_claims, field_path="non_claims"))
        if not isinstance(self.findings, tuple):
            violations.append(
                ReviewCaseViolation(
                    "invalid_collection",
                    "findings",
                    "expected immutable tuple",
                    type(self.findings).__name__,
                )
            )
        seen: set[str] = set()
        for index, finding in enumerate(self.findings if isinstance(self.findings, tuple) else ()):
            if not isinstance(finding, Finding):
                violations.append(
                    ReviewCaseViolation(
                        "invalid_type",
                        f"findings[{index}]",
                        "expected Finding",
                        finding,
                    )
                )
                continue
            if finding.finding_id in seen:
                violations.append(
                    ReviewCaseViolation(
                        "duplicate_finding_id",
                        f"findings[{index}].finding_id",
                        "finding ids must be unique within a packet",
                        finding.finding_id,
                    )
                )
            seen.add(finding.finding_id)
            for span_index, span in enumerate(finding.source_spans):
                if span.path != self.source.path:
                    violations.append(
                        ReviewCaseViolation(
                            "span_path_mismatch",
                            f"findings[{index}].source_spans[{span_index}].path",
                            "source span path must equal packet source path",
                            span.path,
                        )
                    )
        _raise_if(violations)

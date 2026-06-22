"""Minimal real Consultant WordML parser adapter (document-level seam).

[bounded] D046 adapter lifecycle tag. Reads **document-level metadata only**
from a ConsultantPlus Word 2003 WordML (``*.xml``) source via stdlib
``xml.etree.ElementTree`` and returns a
``(SourceDocument, list[SourceBlock])`` tuple matching the :class:`Parser`
port contract. Structural ``SourceBlock`` extraction is **not** done here
(see Scope), so the block list is empty for now.

Scope (T04 / S01):
    This adapter extracts the Consultant ``<o:DocumentProperties>`` block —
    document type, source role (provenance class), title, act number and
    edition date. Full structural hierarchy (chapters/articles/clauses) stays
    in ``scripts/build-consultant-hierarchy-records.py`` (M009 pattern) and
    hardens in a later milestone per the M034 roadmap. Here is only the
    document-level seam that proves the end-to-end ingest path; the
    ``SourceBlock`` list is therefore returned empty.

Trust boundary (S01 threat model):
    This is the first product surface that touches the filesystem with an
    untrusted-ish ``path``. Two mitigations are baked in:
      1. ``path`` is constrained to a trusted root (default ``law-source/``)
         with a typed :class:`ConsultantParseError` for traversal attempts.
      2. stdlib ``xml.etree`` already rejects classic XXE external entities
         (verified in S01). Entity-expansion DoS is a latent risk; Consultant
         fixtures in scope contain no expansion entities. ``defusedxml`` is the
         documented future hardening (adapter-only dependency), not added here.

The :class:`ConsultantWordMLParser` structurally satisfies the
:class:`law_nexus.ports.parser.Parser` protocol
(``parse(path) -> (SourceDocument, list[SourceBlock])``); that conformance is
asserted statically in ``law_nexus.composition``.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import date
from enum import Enum
from pathlib import Path

from law_nexus.domain import SourceBlock, SourceDocument, SourceProvenanceClass

#: Office namespace (``o:``) carrying ``DocumentProperties``.
_OFFICE_NS = "urn:schemas-microsoft-com:office:office"
#: WordML namespace (``w:``) — root ``w:wordDocument`` element lives here.
_WORDML_NS = "http://schemas.microsoft.com/office/word/2003/wordml"

#: Tag of the Office document-properties container.
_DOC_PROPS_TAG = f"{{{_OFFICE_NS}}}DocumentProperties"
#: ``<o:Title>`` — multi-line Consultant act title (type + number + redaction).
_TITLE_TAG = f"{{{_OFFICE_NS}}}Title"
#: ``<o:Company>`` — ConsultantPlus release marker (e.g. "Версия 4025.00.30").
_COMPANY_TAG = f"{{{_OFFICE_NS}}}Company"

#: Russian date ``DD.MM.YYYY`` as used by Consultant in ``<o:Title>`` redaction.
_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
#: Act number from the title's first ``от <date> N <номер>`` clause.
_ACT_NUMBER_RE = re.compile(r"\bN\s*([0-9A-Za-zА-Яа-яёЁ+\-/]+)", re.UNICODE)

#: Default trusted root for source fixtures.
DEFAULT_SOURCE_ROOT = "law-source"

#: ``source_system`` marker for ConsultantPlus sources.
SOURCE_SYSTEM_CONSULTANT = "consultant"

#: Chunk size for streaming file SHA-256.
_SHA_CHUNK = 1024 * 1024


class ConsultantDocumentType(str, Enum):
    """Coarse document-type classification derived from the Consultant title.

    Enumerated act kinds that appear in the project fixtures; unknown kinds
    fall through to :attr:`other`. The classification drives the
    :class:`SourceProvenanceClass` and future source-level mapping.

    Variants are grounded in the M072 S02 probe of the expanded fixture
    corpus (41 Consultant XML fixtures). Adding a new variant here requires
    a matching pattern matcher in :func:`_classify_document_type` and a
    per-variant test using REAL fixture title text (M072 S04).
    """

    federal_law = "federal_law"
    code = "code"
    code_amendment_overview = "code_amendment_overview"
    court_practice_review = "court_practice_review"
    fas_review = "fas_review"
    government_resolution = "government_resolution"
    constitutional_court_ruling = "constitutional_court_ruling"
    supreme_court_ruling = "supreme_court_ruling"
    lower_court_ruling = "lower_court_ruling"
    antimonopoly_decision = "antimonopoly_decision"
    document_list = "document_list"
    other_document = "other_document"


class ConsultantParseError(ValueError):
    """Raised when a Consultant WordML source cannot be parsed safely.

    Carries a bounded, non-sensitive ``detail`` (never raw file contents) so
    callers and logs cannot leak source text. Used for missing properties,
    malformed XML, and path-traversal attempts alike.
    """


def _sha256_of_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file's raw bytes."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_SHA_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


#: Pattern matchers for Consultant title classification. Each entry is
#: (ConsultantDocumentType, compiled regex). Order matters: more specific
#: patterns come first so they win against shorter generic matches (e.g.
#: ``Конституционного Суда`` before generic ``Суда``). Patterns are tested
#: against the first non-empty line of the Consultant ``<o:Title>``.
_DOCUMENT_TYPE_PATTERNS: tuple[tuple[ConsultantDocumentType, re.Pattern[str]], ...] = (
    (
        ConsultantDocumentType.constitutional_court_ruling,
        re.compile(
            r"(Постановление|Определение)\s+Конституционного\s+Суда", re.IGNORECASE | re.UNICODE
        ),
    ),
    (
        ConsultantDocumentType.supreme_court_ruling,
        re.compile(r"(Постановление|Определение)\s+Верховного\s+Суда", re.IGNORECASE | re.UNICODE),
    ),
    (
        ConsultantDocumentType.lower_court_ruling,
        re.compile(r"Постановление.*(?:арбитражн|кассацион)", re.IGNORECASE | re.UNICODE),
    ),
    (
        ConsultantDocumentType.antimonopoly_decision,
        re.compile(r"(Решение|Приказ)\s+(ФАС|УФАС)", re.IGNORECASE | re.UNICODE),
    ),
    (
        ConsultantDocumentType.government_resolution,
        re.compile(r"Постановление\s+Правительства", re.IGNORECASE | re.UNICODE),
    ),
    (
        ConsultantDocumentType.court_practice_review,
        re.compile(r"Обзор\s+судебной\s+практики", re.IGNORECASE | re.UNICODE),
    ),
    (
        ConsultantDocumentType.code_amendment_overview,
        re.compile(r"Обзор\s+изменений.*\bКодекс", re.IGNORECASE | re.UNICODE),
    ),
    (
        ConsultantDocumentType.fas_review,
        re.compile(r"Обзор.*\b(ФАС|Казначейств)", re.IGNORECASE | re.UNICODE),
    ),
    (
        ConsultantDocumentType.code,
        re.compile(r"\bКодекс\b", re.IGNORECASE | re.UNICODE),
    ),
    (
        ConsultantDocumentType.federal_law,
        re.compile(r"Федеральн[ыы]й\s+закон", re.IGNORECASE | re.UNICODE),
    ),
    (
        ConsultantDocumentType.document_list,
        re.compile(r"Список\s+документов", re.IGNORECASE | re.UNICODE),
    ),
)


def _classify_document_type(title: str) -> ConsultantDocumentType:
    """Classify the document kind from the first line of ``<o:Title>``.

    Consultant titles begin with the act kind, e.g.
    ``Федеральный закон от 05.04.2013 N 44-ФЗ`` or ``Постановление
    Конституционного Суда РФ от 18.03.2021 N 7-П``. Pattern matchers in
    :data:`_DOCUMENT_TYPE_PATTERNS` are tried in declared priority order;
    the first match wins. If no pattern matches, :attr:`ConsultantDocumentType.other`
    is returned.

    Classification is title-pattern matching only and is NOT a parser
    assertion (see :class:`ConsultantWordMLParser` and the explicit
    non-claims block in :file:`prd/parser/source_fixture_inventory.md`).
    """

    first_line = title.splitlines()[0] if title else ""
    for doc_type, pattern in _DOCUMENT_TYPE_PATTERNS:
        if pattern.search(first_line):
            return doc_type
    return ConsultantDocumentType.other_document


def _extract_consultant_title_first_line(path: Path) -> str | None:
    """Return the first non-empty line of the Consultant ``<o:Title>`` or ``None``.

    Uses stdlib ``iterparse`` to avoid loading the entire XML tree into memory
    — Consultant fixtures can be tens of MB. The function is exposed (no
    underscore) because downstream tooling (probe, tests, future ingest
    pipelines) reuses the same title extraction logic.
    """

    title_tag = f"{{{_OFFICE_NS}}}Title"
    try:
        for _, elem in ET.iterparse(path, events=("start",)):
            if elem.tag != title_tag:
                continue
            text = elem.text
            elem.clear()
            if not text:
                return None
            first_line = text.strip().splitlines()[0] if text.strip() else ""
            return first_line or None
    except ET.ParseError:
        return None
    return None


def _extract_act_number(title: str) -> str | None:
    """Return the act number (e.g. ``44-ФЗ``) from the title, or ``None``."""

    match = _ACT_NUMBER_RE.search(title)
    if match is None:
        return None
    candidate = match.group(1).strip().rstrip(".,;:")
    return candidate or None


def _extract_edition_date(title: str) -> date | None:
    """Return the redaction date from ``(ред. от DD.MM.YYYY)`` or ``None``.

    The redaction date is the second ``DD.MM.YYYY`` in the title (the first is
    the act's adoption date). We pick the date that appears after ``ред.``,
    falling back to ``None`` when absent.
    """

    lower = title.lower()
    marker = lower.find("ред.")
    if marker == -1:
        return None
    tail = title[marker:]
    match = _DATE_RE.search(tail)
    if match is None:
        return None
    day, month, year = (int(g) for g in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _read_document_properties(root: ET.Element) -> tuple[str, str | None]:
    """Return ``(title, company)`` from the ``<o:DocumentProperties>`` block.

    Raises :class:`ConsultantParseError` when the properties block or title is
    absent — without a title the document has no usable identity.
    """

    props = root.find(_DOC_PROPS_TAG)
    if props is None:
        msg = "missing <o:DocumentProperties> block"
        raise ConsultantParseError(msg)

    title_elem = props.find(_TITLE_TAG)
    if title_elem is None or title_elem.text is None:
        msg = "missing <o:Title> in DocumentProperties"
        raise ConsultantParseError(msg)

    company_elem = props.find(_COMPANY_TAG)
    company = company_elem.text if company_elem is not None else None
    title = title_elem.text.strip()
    return title, company


class ConsultantWordMLParser:
    """Parse a ConsultantPlus WordML ``*.xml`` into a SourceDocument.

    This is a minimal, deterministic, document-level parser: it reads the
    ``<o:DocumentProperties>`` metadata only (type, provenance class, title,
    act number, edition date). It does not parse the structural hierarchy, so
    the returned ``SourceBlock`` list is always empty in this milestone.

    The ``path`` argument is constrained to ``source_root`` (default
    ``law-source``) to refuse traversal outside the trusted source root.
    """

    def __init__(self, source_root: str = DEFAULT_SOURCE_ROOT) -> None:
        # Resolve once; comparison is by resolved path so symlinks cannot
        # escape the trusted root by name alone.
        self._source_root = Path(source_root).resolve()

    def _validate_path(self, raw_path: str | Path) -> Path:
        """Resolve ``raw_path`` and ensure it lives under the trusted root."""

        target = Path(raw_path).resolve()
        try:
            target.relative_to(self._source_root)
        except ValueError:
            msg = f"refusing path outside trusted source root {self._source_root!s}: {raw_path!r}"
            raise ConsultantParseError(msg) from None
        if not target.is_file():
            msg = f"source not found or not a file: {raw_path!r}"
            raise ConsultantParseError(msg) from None
        return target

    def parse(self, path: str | Path) -> tuple[SourceDocument, list[SourceBlock]]:
        """Parse a Consultant WordML file into a document root + source blocks.

        Returns a ``(SourceDocument, list[SourceBlock])`` tuple per the
        :class:`Parser` port contract. In this document-level seam the block
        list is empty — structural hierarchy extraction stays in ``scripts/``
        and hardens in a later milestone (M034 roadmap).

        Args:
            path: Path to a ``*.xml`` Consultant WordML source, resolved under
                the configured ``source_root`` (default ``law-source``).

        Raises:
            ConsultantParseError: If the path escapes the trusted root, the
                file is missing, the XML is malformed, or required
                document-properties are absent.
        """

        target = self._validate_path(path)

        try:
            tree = ET.parse(target)
        except ET.ParseError as exc:
            msg = f"malformed WordML XML in {target.name!r}: {exc}"
            raise ConsultantParseError(msg) from exc

        root = tree.getroot()
        if not root.tag.startswith(f"{{{_WORDML_NS}}}"):
            msg = f"expected WordML root in namespace {_WORDML_NS}, got {root.tag!r}"
            raise ConsultantParseError(msg)

        title, _company = _read_document_properties(root)
        doc_type = _classify_document_type(title)
        act_number = _extract_act_number(title)
        edition_date = _extract_edition_date(title)
        sha256 = _sha256_of_file(target)

        source_id = _derive_source_id(act_number, target.name, sha256 or "0" * 64)

        document = SourceDocument(
            source_id=source_id,
            sha256=sha256,
            source_system=SOURCE_SYSTEM_CONSULTANT,
            source_provenance_class=_provenance_for(doc_type),
            mime_type="application/xml",
            filename=target.name,
            act_number=act_number,
            edition_date=edition_date,
            imported_at=None,
        )
        # Document-level seam only: the structural SourceBlock sequence is
        # produced by scripts/ (M009) and hardens into the adapter later.
        return document, []


def _derive_source_id(act_number: str | None, filename: str, file_hash: str) -> str:
    """Return a stable, deterministic, corpus-unique ``source_id`` for a Consultant document.

    Format: ``consultant:{act_number or stem}-{file_hash[:8]}``. The act
    number (e.g. ``44-ФЗ``) is preferred; the filename stem is the fallback
    when the title yields no act number. The 8-character SHA-256 entropy
    suffix guarantees uniqueness across the corpus — without it, fixtures
    that share an act number (e.g. ``Обзор_Практика ФАС по Закону N 44-ФЗ``
    and ``44-FZ-2026.xml``) would collide on ``consultant:44-ФЗ``. Including
    the file hash in the suffix makes the source_id a function of the file
    contents, so re-importing the same file is idempotent and different
    files with the same act number are distinguishable.
    """

    head = act_number or Path(filename).stem
    short_hash = (file_hash or "0" * 64)[:8]
    return f"consultant:{head}-{short_hash}"


def _provenance_for(doc_type: ConsultantDocumentType) -> SourceProvenanceClass:
    """Map a Consultant document kind to its provenance class.

    Consultant Plus is a commercial consolidated legal database (a paid
    subscription product bundling primary law, secondary law, court
    practice, and editorial materials). Every recognised act kind —
    including federal laws, codes, court reviews, antimonopoly decisions,
    constitutional and other court rulings, government resolutions, and
    document lists — is sourced through the same commercial consolidated
    pipeline, so all variants map to
    :attr:`SourceProvenanceClass.commercial_consolidated`. This is a
    provenance provenance invariant per D046, not a per-variant policy
    decision.
    """

    return SourceProvenanceClass.commercial_consolidated

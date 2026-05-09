# Extractor API Contract

**Version:** 1.0.0
**Status:** Implemented
**Date:** 2026-01-01

## Overview

This document defines the API contracts for extractors in the normative document analysis system. All extractors follow consistent patterns for input validation, error handling, and output structure.

---

## HyperlinkExtractor

### Class: `HyperlinkExtractor`

**Location:** `src_common/extractors/hyperlink_extractor.py`

**Purpose:** Extract internal and external hyperlinks from Word 2003 ML XML documents.

---

### Method: `extract_all(xml_content: str | bytes) -> tuple[list[InternalLink], list[ExternalLink]]`

**Description:** Extract all hyperlinks (internal and external) from XML content.

#### Input

| Parameter | Type | Required | Constraints | Description |
|-----------|------|----------|-------------|-------------|
| `xml_content` | `str \| bytes` | Yes | Max 10 MB | Word 2003 ML XML document content |

#### Output

| Type | Description |
|------|-------------|
| `tuple[list[InternalLink], list[ExternalLink]]` | Tuple of (internal_links, external_links) |

**Output Guarantees:**
- Returns empty lists `([], [])` on valid but link-free XML
- Never returns `None`
- Links with empty text are skipped (not included in output)

#### Errors

| Exception | Condition | Recovery |
|-----------|-----------|----------|
| `XMLParsingError` | Malformed XML document | Cannot recover; fix input |
| `ContentTooLargeError` | Input exceeds 10 MB limit | Split document or increase limit |
| `ValidationError` (Pydantic) | Field exceeds length limits | Truncate content before extraction |

#### Thread Safety

Yes - extractor is stateless; safe for concurrent use.

#### Example

```python
from src_common.extractors.hyperlink_extractor import HyperlinkExtractor
from src_common.exceptions import XMLParsingError, ContentTooLargeError

extractor = HyperlinkExtractor()

try:
    internal, external = extractor.extract_all(xml_content)
    print(f"Found {len(internal)} internal and {len(external)} external links")
except XMLParsingError as e:
    print(f"Invalid XML: {e.message}")
except ContentTooLargeError as e:
    print(f"Content too large: {e.size} > {e.limit}")
```

---

### Method: `extract_internal_links(xml_content: str | bytes) -> list[InternalLink]`

**Description:** Extract only internal links (w:bookmark references).

#### Input/Output

Same constraints as `extract_all`; returns only internal links list.

---

### Method: `extract_external_links(xml_content: str | bytes) -> list[ExternalLink]`

**Description:** Extract only external links (w:dest URLs).

#### Input/Output

Same constraints as `extract_all`; returns only external links list.

---

### Method: `extract_from_element(element: ET.Element) -> tuple[list[InternalLink], list[ExternalLink]]`

**Description:** Extract hyperlinks from an already-parsed XML Element.

#### Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `element` | `xml.etree.ElementTree.Element` | Yes | Pre-parsed XML element |

#### Output

Same as `extract_all`.

#### Errors

- No size checking (already parsed)
- May raise `ValidationError` for invalid field values

---

## EditorialExtractor

### Class: `EditorialExtractor`

**Location:** `src_common/extractors/editorial_extractor.py`

**Purpose:** Extract editorial notes (ред., примечание) from normative text.

---

### Method: `extract_editorial_notes(text: str) -> tuple[str, list[EditorialNote]]`

**Description:** Extract editorial annotations from raw text.

#### Input

| Parameter | Type | Required | Constraints | Description |
|-----------|------|----------|-------------|-------------|
| `text` | `str` | Yes | None | Raw text with potential editorial notes |

#### Output

| Type | Description |
|------|-------------|
| `tuple[str, list[EditorialNote]]` | Tuple of (clean_text, notes) |

**Output Guarantees:**
- `clean_text` has editorial comments removed
- `notes` list may be empty if no annotations found
- Returns `("", [])` for empty/None input
- Never raises exceptions on valid string input

#### Errors

- Returns empty tuple components on `None`/empty input
- Never raises exceptions for malformed content

#### Thread Safety

Yes - extractor is stateless.

#### Example

```python
from src_common.extractors.editorial_extractor import EditorialExtractor

extractor = EditorialExtractor()

text = "Статья 1 (в ред. Федерального закона от 28.12.2013 N 396-ФЗ)"
clean, notes = extractor.extract_editorial_notes(text)

print(f"Clean: {clean}")  # "Статья 1"
print(f"Notes: {len(notes)}")  # 1
```

---

## Data Models

### InternalLink

**Location:** `src_common/models/hyperlinks.py`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `text` | `str` | 1-10,000 chars, NFC normalized | Visible link text |
| `bookmark` | `str` | 1-500 chars, NFC normalized | XML bookmark ID (e.g., "P637") |
| `screen_tip` | `str \| None` | Max 5,000 chars | Tooltip content |
| `resolved` | `bool` | Default: `False` | Whether target was found |
| `target_element` | `str \| None` | - | Resolved target path |

**Immutability:** Frozen (cannot be modified after creation)

---

### ExternalLink

**Location:** `src_common/models/hyperlinks.py`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `text` | `str` | 1-10,000 chars, NFC normalized | Visible link text |
| `url` | `str` | Max 2,000 chars | Original ConsultantPlus URL |
| `public_url` | `str \| None` | Max 2,000 chars | Transformed public URL |
| `screen_tip` | `str` | Max 5,000 chars | Tooltip with metadata |
| `doc_reference` | `DocReference \| None` | - | Parsed document reference |

**Immutability:** Frozen

---

### DocReference

**Location:** `src_common/models/references.py`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `law_type` | `str` | 1-50 chars, normalized | Type: ФЗ, Указ, etc. |
| `number` | `str` | 1-50 chars | Document number |
| `document_date` | `date` | Valid date | Adoption date |
| `title` | `str \| None` | Max 1,000 chars | Full title |
| `consultant_id` | `int \| None` | 1-999,999,999 | ConsultantPlus doc ID |

**Immutability:** Frozen

---

## Exception Hierarchy

**Location:** `src_common/exceptions.py`

```
ExtractionError (base)
├── XMLParsingError      - Malformed XML
├── ContentTooLargeError - Size limit exceeded
└── SanitizationError    - Content sanitization failed
```

### ExtractionError

Base exception for all extraction failures.

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Error description |
| `context` | `str \| None` | Additional context |

### ContentTooLargeError

| Attribute | Type | Description |
|-----------|------|-------------|
| `size` | `int \| None` | Actual content size |
| `limit` | `int \| None` | Maximum allowed size |

### SanitizationError

| Attribute | Type | Description |
|-----------|------|-------------|
| `field` | `str \| None` | Field that failed |
| `value` | `str \| None` | Problematic value (truncated) |

---

## Constants

### Size Limits

| Constant | Value | Location |
|----------|-------|----------|
| `MAX_XML_SIZE` | 10 MB (10,485,760 bytes) | `hyperlink_extractor.py` |

### Field Length Limits

| Constant | Value | Location |
|----------|-------|----------|
| `MAX_TEXT_LENGTH` | 10,000 chars | `hyperlinks.py` |
| `MAX_BOOKMARK_LENGTH` | 500 chars | `hyperlinks.py` |
| `MAX_SCREEN_TIP_LENGTH` | 5,000 chars | `hyperlinks.py` |
| `MAX_URL_LENGTH` | 2,000 chars | `hyperlinks.py` |
| `MAX_LAW_TYPE_LENGTH` | 50 chars | `references.py` |
| `MAX_NUMBER_LENGTH` | 50 chars | `references.py` |
| `MAX_TITLE_LENGTH` | 1,000 chars | `references.py` |

---

## Unicode Handling

All text fields are normalized to **NFC (Canonical Decomposition, followed by Canonical Composition)** form:

- Ensures consistent comparison and storage
- Applied before length validation
- Handles Cyrillic combining characters correctly

---

## Security Considerations

### URL Handling

- JavaScript URLs (`javascript:`) are extracted but should be validated by consumers
- Data URLs (`data:`) are extracted as-is
- Very long URLs (>2,000 chars) rejected at model level
- HTML entities are unescaped (`&amp;` → `&`)

### Bookmark Handling

- Unicode bookmark IDs are accepted (Cyrillic characters valid)
- Very long bookmarks (>500 chars) rejected at model level

### Screen Tip Handling

- HTML entities are decoded
- Script tags are NOT stripped (consumer responsibility)
- Content is NFC-normalized

### Size Protection

- XML content >10 MB rejected with `ContentTooLargeError`
- Prevents XML bomb and DoS attacks

---

## Versioning

This API follows semantic versioning:

- **Major:** Breaking changes to method signatures or output format
- **Minor:** New optional features, backward compatible
- **Patch:** Bug fixes, documentation updates

Current version: **1.0.0**

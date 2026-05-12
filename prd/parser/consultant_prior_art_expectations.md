# Consultant prior-art expectations

This artifact normalizes law-parser prior-art outputs into deterministic comparison safeguards. It is non-authoritative and does not claim legal correctness, parser completeness, or authoritative legal interpretation.

## Source freshness

- `/root/law-parser/doc_domain_44fz/cons/44-FZ/44-FZ-2026-structure.json` asset=`CPA-002` sha256=`da41e6c23f4449da39c79548c0b270d2747d7a50852f796b980c4b38742dbc5a` expected=`da41e6c23f4449da39c79548c0b270d2747d7a50852f796b980c4b38742dbc5a` match=`true` class=`adapt`
- `/root/law-parser/doc_domain_44fz/cons/44-FZ/44-FZ-2026-articles.jsonl` asset=`CPA-003` sha256=`de03cda6b266085a9b1f2376afcb9dffbb00fec922dee1f1553cadcfb6d03869` expected=`de03cda6b266085a9b1f2376afcb9dffbb00fec922dee1f1553cadcfb6d03869` match=`true` class=`adapt`
- `/root/law-parser/prompt_domain_44fz/validation/semantic_rules.yaml` asset=`CPA-008` sha256=`c53121270fe4e1436bc28879dc6b465b0ea71f29cda90d96beb50d637d62714c` expected=`c53121270fe4e1436bc28879dc6b465b0ea71f29cda90d96beb50d637d62714c` match=`true` class=`defer`
- `/root/law-parser/prompt_domain_44fz/validation/structural_rules.yaml` asset=`CPA-007` sha256=`a38b25b7dfb7523b86e6a9042f4bed14f9fa1d13b5b82d5e22b55d218a8d8a37` expected=`a38b25b7dfb7523b86e6a9042f4bed14f9fa1d13b5b82d5e22b55d218a8d8a37` match=`true` class=`adapt`

## Comparable counts

### Structure JSON

- `chapter_count`: `8`
- `chapter_article_refs_total`: `47`
- `chapter_paragraphs_total`: `9`
- `chapters_with_article_refs`: `7`
- `chapters_with_paragraphs`: `1`
- `metadata_field_count`: `7`
- `all_references_count`: `0`
- `external_laws_count`: `0`
- `key_dates_count`: `0`
- `definitions_count`: `0`

### Articles JSONL

- `article_record_count`: `94`
- `article_invalid_false_count`: `83`
- `article_invalid_true_count`: `11`
- `articles_without_parts`: `18`
- `part_count`: `668`
- `part_invalid_true_count`: `41`
- `clause_count`: `912`
- `clause_invalid_true_count`: `17`
- `subclause_count`: `272`
- `subclause_invalid_true_count`: `1`
- `part_references_count`: `0`
- `clause_references_count`: `0`
- `part_amendments_count`: `0`
- `clause_amendments_count`: `0`

## Validation rules

- `validation_file_count`: `2`
- `validation_rule_count`: `15`
- `comparable_rule_count`: `6`
- `advisory_rule_count`: `9`

### Comparable rules

- `STRUCT-001` `error` target=`article` check=`has_field` — Every article must have a number
- `STRUCT-002` `warning` target=`chapter` check=`has_field` — Every chapter should have a title
- `STRUCT-003` `warning` target=`article` check=`has_parent` — Articles should be contained in chapters
- `STRUCT-004` `error` target=`paragraph` check=`has_parent` — Paragraphs must be contained in articles
- `STRUCT-005` `warning` target=`text` check=`has_parent` — Text content should not be orphaned outside structure
- `STRUCT-006` `error` target=`document` check=`has_children` — Document must contain at least one article

### Advisory rules

- `SEM-001` `error` target=`article` check=`sequential_within` — Article numbers should be sequential within chapter
- `SEM-002` `error` target=`paragraph` check=`sequential_within` — Paragraph numbers should be sequential within article
- `SEM-003` `warning` target=`chapter` check=`sequential_within` — Chapter numbers should be sequential in document
- `SEM-004` `error` target=`date` check=`date_format` — Dates must be in valid format
- `SEM-005` `warning` target=`document_date` check=`date_not_after` — Document dates should not be in the future
- `SEM-006` `error` target=`reference` check=`reference_exists` — Internal article references must point to existing articles
- `SEM-007` `warning` target=`reference` check=`matches_pattern` — External law references must have valid format
- `SEM-008` `warning` target=`article` check=`has_content` — Articles should contain at least one paragraph
- `SEM-009` `info` target=`article` check=`contains_marker` — Detect articles marked as invalid

## Skipped/advisory fields

- `article.title/text and part/clause/subclause text` — text copied from prior-art output is source/provider-specific and not a compact structure expectation
- `semantic legal meaning and internal-reference validity` — requires citation-safe deterministic evidence beyond context-free count comparison
- `amendment/invalidation legal effect` — prior-art markers are advisory until temporal/legal evidence rules are verified separately

## Diagnostics

- Fatal errors: `0`
- Hash drift count: `0`
- Artifact freshness: `null`

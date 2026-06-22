# Consultant WordML Hierarchy Corpus (M072 S05)

This artifact is deterministic parser evidence only. It is non-authoritative and does not claim legal correctness, parser completeness, product ETL readiness, or FalkorDB load readiness. Out-of-scope fixtures are documented below; they remain on disk awaiting a later scope expansion (no silent skipping).

## Scope

- In-scope document types: `federal_law, code`
- In-scope fixtures: `4`
- Out-of-scope fixtures: `49`
- Total records emitted: `7860`
- Unique record ids: `7860`
- ID collisions: `0`
- Fatal errors: `0`

## In-scope per-fixture breakdown

| Scope id | Source path | Document type | Records | Levels | SHA-256 |
| --- | --- | --- | ---: | --- | --- |
| `CONS-44-FZ-2026` | `law-source/consultant/44-FZ-2026.xml` | `federal_law` | 2185 | article=94, chapter=8, clause=997, document=1, part=793, section=9, subclause=283 | `69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` |
| `CONS-31-07-1998-N-145` | `law-source/consultant/Бюджетный кодекс Российской Федерации  от 31.07.1998 N 145-Ф.xml` | `code` | 2516 | article=396, chapter=41, clause=597, document=1, part=1481 | `141d0463ccea5ac1f1e1d672a05cce9c39df288c23c824ced86740cd075c0215` |
| `CONS-3` | `law-source/consultant/Гражданский кодекс Российской Федерации (часть первая)  от 3.xml` | `code` | 2572 | article=591, chapter=32, clause=220, document=1, part=1704, section=24 | `4398e60096787b8b75acd5235b4eb988851a67dfa6b9298fd01eda5ee294a210` |
| `CONS-18-07-2011-N-223-08-08-2` | `law-source/consultant/Федеральный закон от 18.07.2011 N 223-ФЗ (ред. от 08.08.2024.xml` | `federal_law` | 587 | article=21, clause=253, document=1, part=241, subclause=71 | `dfc8314207faf37bd4bad1acbec7189db502a161a350a0969da08b6e653f4ece` |

## Out-of-scope fixtures (documented, not silently skipped)

| Document type | Fixture count | Reason |
| --- | ---: | --- |
| `antimonopoly_decision` | 5 | Antimonopoly decision; non-hierarchical structure for S05 scope. |
| `code_amendment_overview` | 5 | Amendment overview; not a full normative-act source-shape. |
| `constitutional_court_ruling` | 3 | Court ruling; treated as citation-evidence, not a full hierarchy. |
| `court_practice_review` | 4 | Court practice review; not a full normative-act source-shape. |
| `document_list` | 2 | Document list (relation candidate, not hierarchy). |
| `fas_review` | 3 | FAS / Treasury review; not a full normative-act source-shape. |
| `government_resolution` | 1 | Government resolution; structure is non-hierarchical for M072 S05 scope. |
| `lower_court_ruling` | 4 | Lower court ruling; treated as citation-evidence, not a full hierarchy. |
| `odt_document` | 12 | Garant ODT fixture; covered by separate ODT smoke path, not by Consultant parser. |
| `other_document` | 4 | Unclassified title; not a full normative-act source-shape. |
| `supreme_court_ruling` | 6 | Court ruling; treated as citation-evidence, not a full hierarchy. |

## Non-claims

- Consultant hierarchy corpus records are deterministic parser-source records only.
- The corpus does not claim legal correctness or authoritative legal interpretation.
- The corpus does not claim parser completeness for non-in-scope document kinds.
- The corpus does not claim product ETL or FalkorDB load readiness.
- Out-of-scope fixtures are documented but not silently skipped — they remain on disk awaiting a later scope expansion.

# Consultant WordML Hierarchy Corpus (M072 S05)

This artifact is deterministic parser evidence only. It is non-authoritative and does not claim legal correctness, parser completeness, product ETL readiness, or FalkorDB load readiness. Out-of-scope fixtures are documented below; they remain on disk awaiting a later scope expansion (no silent skipping).

## Scope

- In-scope document types: `federal_law, code`
- In-scope fixtures: `10`
- Out-of-scope fixtures: `84`
- Total records emitted: `15249`
- Unique record ids: `15249`
- ID collisions: `0`
- Fatal errors: `0`

## In-scope per-fixture breakdown

| Scope id | Source path | Document type | Records | Levels | SHA-256 |
| --- | --- | --- | ---: | --- | --- |
| `CONS-byudzhetnyi-kodeks-rossi` | `law-source/consultant/byudzhetnyi-kodeks-rossiiskoi-federatsii-ot-31-07-1998-n-145-fz-red-ot-26-06-2026-s-izm-i-dop-vstup-v-silu-s-01-07-2026--124297b4.xml` | `code` | 2544 | article=396, chapter=41, clause=608, document=1, part=1488, razdel=10 | `62f36ad995fd459ee08d93818f4c8bf27d15cf2c51998eddde5666eb278d5571` |
| `CONS-federalnyi-zakon-ot-05-0` | `law-source/consultant/federalnyi-zakon-ot-05-04-2013-n-44-fz-red-ot-28-12-2025-o-kontraktnoi-sisteme-v-sfere-zakupok-tovarov-rabot-uslug-dlya-obespecheniya-g--f9c8ca4c.xml` | `federal_law` | 2185 | article=94, chapter=8, clause=997, document=1, part=793, section=9, subclause=283 | `c111119c6c3001b5b4fde0e35bffbe382bcb877df2bba9cd54ab0290c92c1b14` |
| `CONS-federalnyi-zakon-ot-06-0` | `law-source/consultant/federalnyi-zakon-ot-06-04-2011-n-63-fz-red-ot-31-07-2025-ob-elektronnoi-podpisi--6caf7614.xml` | `federal_law` | 361 | article=29, clause=190, document=1, part=126, subclause=15 | `9608d06982dc1762844c6e0899b11dd3e53f9ced1a3813f940a33fc2153de3ed` |
| `CONS-federalnyi-zakon-ot-06-1` | `law-source/consultant/federalnyi-zakon-ot-06-12-2011-n-402-fz-red-ot-15-12-2025-o-bukhgalterskom-uchete--fcc0b660.xml` | `federal_law` | 364 | article=33, chapter=4, clause=140, document=1, part=186 | `30e60a556e7aa6d66121e0d69768905ffab8a41b452f6e3ac3eecfe5980fe606` |
| `CONS-federalnyi-zakon-ot-12-0` | `law-source/consultant/federalnyi-zakon-ot-12-04-2010-n-61-fz-red-ot-29-12-2025-ob-obrashchenii-lekarstvennykh-sredstv-s-izm-i-dop-vstup-v-silu-s-01-03-2026--5af26e08.xml` | `federal_law` | 1247 | article=86, chapter=17, clause=465, document=1, part=489, subclause=189 | `b89e6f5fa6d58fd75551396c2ab6e0dd07e074a809e34899cafd7d903730f444` |
| `CONS-federalnyi-zakon-ot-18-0` | `law-source/consultant/federalnyi-zakon-ot-18-07-2011-n-223-fz-red-ot-08-08-2024-o-zakupkakh-tovarov-rabot-uslug-otdelnymi-vidami-yuridicheskikh-lits-s-izm-i--86e8fd8d.xml` | `federal_law` | 587 | article=21, clause=253, document=1, part=241, subclause=71 | `9a6d8a3b49f27f9131259539ce1c03b5fb4199be1a1b3a5f6bdfa9685a01f0a2` |
| `CONS-federalnyi-zakon-ot-22-1` | `law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml` | `federal_law` | 120 | article=22, clause=22, document=1, part=75 | `62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d` |
| `CONS-federalnyi-zakon-ot-25-1` | `law-source/consultant/federalnyi-zakon-ot-25-12-2008-n-273-fz-red-ot-28-12-2025-o-protivodeistvii-korruptsii--da724f03.xml` | `federal_law` | 323 | article=30, clause=136, document=1, part=137, subclause=19 | `fe8a2d3dbc761d501e54e5167a1dcda3c3e44cee0781be07b3d87f2a56ed93f0` |
| `CONS-kodeks-rossiiskoi-federa` | `law-source/consultant/kodeks-rossiiskoi-federatsii-ob-administrativnykh-pravonarusheniyakh-ot-30-12-2001-n-195-fz-red-ot-04-07-2026-s-izm-i-dop-vstup-v-silu--b4fd4ec6.xml` | `code` | 5250 | article=1121, chapter=33, clause=910, document=1, part=3165, razdel=5, subclause=15 | `7a334df262c18968e435b8e888e1b12c76d68878c025d08298054f48c274c3e4` |
| `CONS-zemelnyi-kodeks-rossiisk` | `law-source/consultant/zemelnyi-kodeks-rossiiskoi-federatsii-ot-25-10-2001-n-136-fz-red-ot-02-05-2026-s-izm-i-dop-vstup-v-silu-s-01-07-2026--77238147.xml` | `code` | 2268 | article=179, clause=1054, document=1, part=1034 | `d8ab6dee35d94c5d744f87ec4a70e6a30c3d82e964f85acd9c6817efa74c8b87` |

## Out-of-scope fixtures (documented, not silently skipped)

| Document type | Fixture count | Reason |
| --- | ---: | --- |
| `antimonopoly_decision` | 9 | Antimonopoly decision; non-hierarchical structure for S05 scope. |
| `court_practice_review` | 4 | Court practice review; not a full normative-act source-shape. |
| `document_list` | 1 | Document list (relation candidate, not hierarchy). |
| `fas_review` | 3 | FAS / Treasury review; not a full normative-act source-shape. |
| `government_resolution` | 20 | Government resolution; structure is non-hierarchical for M072 S05 scope. |
| `lower_court_ruling` | 4 | Lower court ruling; treated as citation-evidence, not a full hierarchy. |
| `odt_document` | 12 | Garant ODT fixture; covered by separate ODT smoke path, not by Consultant parser. |
| `other_document` | 30 | Unclassified title; not a full normative-act source-shape. |
| `supreme_court_ruling` | 1 | Court ruling; treated as citation-evidence, not a full hierarchy. |

## Non-claims

- Consultant hierarchy corpus records are deterministic parser-source records only.
- The corpus does not claim legal correctness or authoritative legal interpretation.
- The corpus does not claim parser completeness for non-in-scope document kinds.
- The corpus does not claim product ETL or FalkorDB load readiness.
- Out-of-scope fixtures are documented but not silently skipped — they remain on disk awaiting a later scope expansion.

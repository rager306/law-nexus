# Universal Intelligent XML Parsing for Graph Import — Research Proposal

## Status

- Status: `research-proposal` (contract level, no implementation)
- Date: 2026-07-17
- Inputs:
  - `prd/research/source_structuring/25-corrected-consultant-xml-parser-roadmap.md` (M034 S04 corrected parser roadmap)
  - `prd/parser/README.md` (fixture inventory, record contracts, non-claims)
  - `prd/02_architecture.md` (target graph model, NormStatement contract, temporal layer)
  - `prd/10_m006_parser_graph_staging_recommendation.md` (staging graph recommendation)
  - `prd/research/google_doc_ontology_architecture_akoma_ntoso_lkif_gost_bfo.md` (Akoma Ntoso / LKIF / GOST BFO research)
  - `prd/research/ontology_architecture_requirements/05-01-structural-normalization-akoma-ntoso.md`
  - `prd/research/ontology_architecture_requirements/05-02-entity-extraction-deontic-mapping.md`
  - `prd/research/source_structuring/05-llm-worker-dspy-protocol.md` (M031 S05 LLM worker protocol)
  - `Old_project/` prior art (see §6)
- Non-validation boundaries: this document does not validate R035, R037, or R038; it proposes parsing architecture only and claims no legal correctness, parser completeness, product ETL readiness, or FalkorDB loading/runtime readiness.

## Purpose

Define how the parser layer evolves from the current single-source, single-regex-family baseline into a **universal, intelligent, graph-ready XML parsing subsystem** for Russian normative acts — without violating the project's deterministic-first, temporal-first, and LLM-non-authoritative guardrails. Every idea is grounded in existing project files.

## 1. Current state map (verified against code)

| Component | File | What it does today |
|---|---|---|
| Parser port | `src/law_nexus/ports/parser.py` | `parse(path) -> (SourceDocument, list[SourceBlock])` protocol |
| Document-level WordML adapter | `src/law_nexus/adapters/parsers/consultant_wordml.py` | `<o:DocumentProperties>` metadata only; full `ET.parse()`; path-traversal guard; `ConsultantDocumentType` 12-variant title classifier |
| Hierarchy port | `src/law_nexus/ports/source_hierarchy.py` | `SourceHierarchyParagraph(index, text, style)` — already format-agnostic IR seed |
| Hierarchy engine | `src/law_nexus/adapters/sources/consultant_hierarchy.py` | Context-first state machine over `iterparse`; levels `document/chapter/section/article/part/clause/subclause`; 2185 records on the canonical fixture (M009 baseline) |
| ODT smoke parsers | `scripts/build-odt-smoke-records.py`, `scripts/smoke-s05-odt-parser.py` | Full `fromstring()` on `content.xml`; heading/paragraph traversal with `style_name`/`outline_level` signals |
| Relation candidates | `scripts/build-consultant-relation-candidates.py` | One `RelationCandidateRecord` (`LAW:179581@11.05.2026`), unresolved by design |
| Staging graph | `scripts/build-parser-staging-graph.py` | NetworkX `MultiDiGraph` staging, unresolved-reference nodes preserved |
| Fixture corpus | `law-source/consultant/` (41 WordML), `law-source/garant/` (12 ODT) | 12 document types classified by M072 taxonomy (`prd/parser/README.md`) |
| Record contracts | `prd/parser/schemas/*.schema.json` | Strict JSON Schema per record kind |

## 2. Gap analysis: current → graph-import-ready

| Gap | Evidence | Consequence for graph import |
|---|---|---|
| Format logic hardcoded per source | `consultant_hierarchy.py` embeds WordML regexes; ODT logic duplicated in `scripts/` | Second source family = new code, not new config |
| Level ladder incomplete | `Level` in `consultant_hierarchy.py` lacks `раздел` (part/section above chapter), `абзац` (unnumbered paragraph), `преамбула`, `приложение` | Codes (ГК, БК in `law-source/consultant/`) structurally require `раздел`; articles lose unnumbered text blocks |
| No FRBR identity separation | `consultant_wordml.py` derives one `source_id`; `edition_date` exists but no `edition_id` | `LegalAct`/`ActEdition` nodes (`prd/02_architecture.md`) cannot be keyed deterministically; `VERSION_OF`/`SUPERSEDES` stay unanchored |
| No reference extraction in parse path | Only one list-fixture relation candidate exists (`prd/parser/consultant_relation_candidates.jsonl`) | `Reference`/`REFERS_TO` edges (target model) have no substrate |
| No norm candidates | `NormStatement` contract exists in `prd/02_architecture.md` §2a | Graph semantic layer empty at import |
| Memory posture inconsistent | `ConsultantWordMLParser.parse()` loads whole tree; `_extract_consultant_title_first_line` streams; docstring admits tens-of-MB fixtures | Scales poorly to full codes corpus |
| Security hardening deferred | `defusedxml` named "future hardening" in `consultant_wordml.py` module docstring; ODT readers have no zip-bomb guard | Threat model S01 mitigation incomplete |

## 3. Target architecture: separate format, profile, engine

```text
Consultant WordML ─┐
Garant ODT        ─┼─▶ [1] Format adapters ─▶ RawBlock stream (IR)
pravo.gov.ru XML  ─┘         │
                             ▼
                    [2] Source profiles (YAML, declarative)
                             │
                             ▼
                    [3] Two-pass structure engine
                        pass A: document profiler
                        pass B: context-first state machine
                             │
                             ▼
                    [4] Candidate extractors
                        references / norm statements / temporal markers
                             │
                             ▼
                    [5] Graph staging records
                        (existing NetworkX MultiDiGraph contract)
```

### Layer 1 — Format adapters (thin)

Each adapter converts one source format into the shared **RawBlock IR**. The seed already exists: `SourceHierarchyParagraph` in `src/law_nexus/ports/source_hierarchy.py`. Extend it to:

```python
RawBlock:
    order_index: int          # linear source order (existing convention)
    kind: heading|paragraph|table_row|list_item
    text: str                 # normalized (see profile char rules)
    style: str | None         # WordML pStyle / ODT style-name
    outline_level: int | None # ODT text:outline-level (already read in build-odt-smoke-records.py)
    num_id: str | None        # WordML numbering id (future)
    inline_refs: list[str]    # hyperlink/anchor targets (relation evidence)
    table_flag: bool
    source_span: str          # bounded selector, e.g. /w:wordDocument/w:body/w:p[123]
```

The ODT adapters already emit `style_name` and `outline_level` (`scripts/build-odt-smoke-records.py` `iter_raw_blocks`); the WordML side already emits style (`consultant_hierarchy.py` `paragraph_style`). The IR only standardizes what is already observed.

### Layer 2 — Source profiles (declarative YAML)

Direct successor of prior art `Old_project/sources/consultant_word2003xml.yaml` (namespaces, strip patterns, character normalization, element rules) merged with structure schemas like `Old_project/structures/44fz.yaml` (marker patterns per level with real counts: 8 chapters, 94 articles, 279 parts).

A profile declares:

- `format`: namespaces, element selectors, strip patterns, char normalization (`«»→"`, `–→-`, `nbsp→space` — same rules as the prior-art YAML)
- `structure`: ordered level ladder with marker regex families and numbering formats
- `style_map`: observed style → level hints (e.g. Consultant style `"5"` = document title, already exploited in `hierarchy_records`)
- `zones`: preamble / body / appendices segmentation rules

**Universality claim, bounded:** adding a new source family = adding a profile + a thin adapter, not a new engine. Verified per source by golden fixtures (§8).

### Layer 3 — Two-pass structure engine

Generalizes the proven M009 context-first machine (`hierarchy_records` in `src/law_nexus/adapters/sources/consultant_hierarchy.py`):

- **Pass A — document profiler.** One streaming pass collecting: style census (already collected as `style_observations`), marker census per candidate level, numbering format distribution, title-line shape. Output: chosen/confirmed structure profile + ambiguity diagnostics. This replaces brittle single-regex matching with evidence-based profile selection.
- **Pass B — extraction.** The existing state machine with the **full ladder**:

```text
раздел → глава → § → статья → часть (1.) → пункт (1), 7.1)) → подпункт (а)) → абзац
```

plus zones: `преамбула`, `приложение`, `таблица`.

### Layer 4 — Candidate extractors

Deterministic, span-bound, always `unverified`/candidate status:

- **References** (§7)
- **NormStatement candidates** via deontic lexeme table (§8)
- **Temporal/validity markers** (§6.4)

### Layer 5 — Graph staging records

Reuse the existing record families and validation chain (`scripts/validate-parser-records.py`, `scripts/build-parser-staging-graph.py`). New record kinds (`ReferenceCandidateRecord`, `NormCandidateRecord`, `EditionRecord`) get strict schemas under `prd/parser/schemas/` exactly like the existing four.

## 4. Why the current port design already supports this

`SourceHierarchyBuilder` (`src/law_nexus/ports/source_hierarchy.py`) consumes normalized paragraphs and returns records + diagnostics — it is already format-agnostic. `ConsultantHierarchyRecordBuilder` is one implementation. The proposal does not break the port; it:

1. widens the paragraph shape (RawBlock),
2. moves marker patterns from code to profiles,
3. adds the profiler pass and candidate extractors behind the same result contract.

The M034 S04 directive — *"Do not restart Consultant XML parsing from zero… return to M009 as the bounded parser baseline and harden it through explicit proof gates"* (`prd/research/source_structuring/25-corrected-consultant-xml-parser-roadmap.md`) — is preserved: every step is equivalence-checked against M009 output.

## 5. Russian NPA structural specifics the engine must encode

Grounded in `Old_project/parsing_prompt.yaml`, `Old_project/structures/44fz.yaml`, and the M072 fixture taxonomy (`prd/parser/README.md`).

### 5.1 Full level ladder and numbering variants

| Level | Markers | Evidence |
|---|---|---|
| Раздел | `Раздел I.`, `РАЗДЕЛ IV` (roman) | Codes in `law-source/consultant/` (ГК, БК) |
| Глава | `Глава 1. ОБЩИЕ ПОЛОЖЕНИЯ`, `ГЛАВА IV.` roman variant | `Old_project/parsing_prompt.yaml` hierarchy level 1 |
| § | `§ 1.`, `§ 3.1.` composite | `Old_project/structures/44fz.yaml` (§ only in chapter 3 of 44-FZ) |
| Статья | `Статья 24.1.`, `Статья 110.2.` composite | `44fz.yaml` article pattern |
| Часть | `1.`, `2.` | `44fz.yaml` part pattern (279 in doc) |
| Пункт | `1)`, composite `7.1)`, `8.1)` | `44fz.yaml` clause pattern (247 in doc) |
| Подпункт | `а)`–`и)` Cyrillic letters | `44fz.yaml` subclause pattern (66 in doc) |
| Абзац | unnumbered prose block inside a part | needed so article text is not lost between markers |

Numbering-continuation checks (gap/duplicate detection) become deterministic structural diagnostics, extending the existing `structural_errors` family in `hierarchy_records`.

### 5.2 Document-type-dependent structure

The M072 taxonomy already classifies 12 types. Structure profiles differ fundamentally:

- **codes/federal_laws** — full ladder above;
- **court rulings** (КС/ВС/ААС in `law-source/consultant/`) — no articles; zones are `установил/постановил/решил` operative parts;
- **обзоры** (reviews) — thematic sections, no legal hierarchy;
- **antimonopoly decisions** — case metadata + operative part.

The profiler pass selects the structure profile from `document_type` + observed marker census; a mismatch (e.g. code without any `Статья`) is a blocking structural diagnostic, not silent fallback.

### 5.3 Temporal and validity surface (data, not legal conclusions)

Extract as bounded fields, never as legal-effect assertions:

- `ред. от DD.MM.YYYY` — already parsed in `consultant_wordml.py` `_extract_edition_date`;
- entry-into-force phrasing (`вступает в силу с …`, `по истечении 10 дней после официального опубликования` — defaults per `Old_project/legislation_hierarchy.yaml` §2);
- invalidity markers (`утратил силу`, `не применяется`) — patterns already in `Old_project/structures/44fz.yaml` `invalidity_markers` and the M009 advisory check;
- secrecy/restriction markers (ДСП etc.) — `Old_project/legislation_hierarchy.yaml` §2A marker lists.

These populate the temporal fields defined in `prd/02_architecture.md` §3 (`edition_date`, `valid_from/to`, `temporal_confidence`) with `unknown` as the honest default.

### 5.4 Preamble and appendices

Russian acts carry a preamble (organ, title, основание) and appendices (перечни, формы). The engine treats them as zones with their own block sequences so body-level state (current article context) is not corrupted by appendix content.

## 6. FRBR identity → graph labels

Applying the Akoma Ntoso / FRBR model from `prd/research/google_doc_ontology_architecture_akoma_ntoso_lkif_gost_bfo.md` (Этап 1) to the target labels in `prd/02_architecture.md`:

| FRBR level | Graph node | Parser-emitted key | Example |
|---|---|---|---|
| Work | `LegalAct` | `act_id = {type}:{number}@{adoption_date}` | `fz:44-ФЗ@2013-04-05` |
| Expression | `ActEdition` | `edition_id = act_id#red-{edition_date}` | `fz:44-ФЗ@2013-04-05#red-2026-05-11` |
| Manifestation | `SourceDocument` | existing `source_id` (`consultant:{act}-{sha8}`, `consultant_wordml.py` `_derive_source_id`) | `consultant:44-ФЗ-a1b2c3d4` |
| Item | `source_path` / member | existing | `law-source/consultant/44-FZ-2026.xml` |

Parser consequences:

- `DocumentRecord` gains `act_id`, `edition_id` (both derived deterministically from `<o:Title>` + filename fallback, same inputs as today);
- hierarchy records gain `edition_id` so every `Chapter/Article/Part/...` node hangs under the correct `ActEdition` via `CONTAINS`;
- two manifestations of the same edition (Consultant XML + Garant ODT of 44-FZ) merge on `edition_id` while keeping distinct `source_id` provenance — this is what makes multi-source import possible at all;
- `VERSION_OF` / `SUPERSEDES` edges (currently deferred in `prd/02_architecture.md`) receive their deterministic anchor: `edition_id` ordering by `edition_date`.

## 7. Reference extraction (the graph's core edges)

Two classes, both emitted as `ReferenceCandidateRecord` with source span and `unresolved` status — consistent with the S04/S05 boundary (`prd/parser/README.md` consumer boundary):

1. **Internal** — `пункт 2 части 1 статьи 3 настоящего Федерального закона`. Regex family over the normalized ladder vocabulary; target key = path within the same `edition_id`. Resolvable deterministically at staging time against emitted hierarchy records.
2. **External** — `Федеральный закон от 05.04.2013 N 44-ФЗ`, `статья 166 Гражданского кодекса`. Extract `(act_type, date, number)` / named-code patterns; target key = candidate `act_id`. Resolution stays deferred: the staging graph already models these as unresolved-reference nodes (`scripts/build-parser-staging-graph.py`, `tests/test_parser_staging_graph.py::test_keyed_consultant_relation_uses_unresolved_reference_nodes_without_doc_rewrite`).

Inline hyperlink signals from WordML (`inline_refs` in RawBlock) give Consultant cross-document links as additional candidate evidence — the mechanism already proven by `LAW:179581@11.05.2026` in `scripts/build-consultant-relation-candidates.py`.

## 8. NormStatement candidates (deontic layer, deterministic)

Per `prd/research/ontology_architecture_requirements/05-02-entity-extraction-deontic-mapping.md` and the NormStatement verification contract (`prd/02_architecture.md` §2a):

| Lexemes (ru) | Candidate `norm_type`/`modality` |
|---|---|
| `обязан`, `должен`, `надлежит`, `необходимо` | `obligation` / `must` |
| `вправе`, `может`, `имеет право`, `допускается` | `permission` / `may` |
| `запрещается`, `нельзя`, `не допускается`, `не вправе` (negation handling) | `prohibition` / `must_not` |
| `признается`, `понимается`, `в целях настоящего ФЗ` | `definition` / `is_defined_as` |
| `в срок не позднее`, `в течение` | `deadline` |
| `за исключением`, `если иное не` | `exception`/`condition` |

Emission rules:

- every candidate carries `extraction_method: deterministic`, `verification_status: unverified`, `source_unit_ids`, `evidence_span_ids` — exactly the contract fields in §2a;
- negation-aware matching (the research doc's key warning: `не вправе` must flip permission → prohibition);
- `pymorphy3`/`razdel` may improve lexeme matching only as evaluated diagnostics per M034 S05 — never as legal authority.

## 9. Engineering contour (2026 baseline)

Carried over from the security/perf review and M034:

1. **`defusedxml`** as the parsing entry point in all adapters (named future hardening in `consultant_wordml.py` docstring); regression fixture with entity-expansion payload expecting `EntitiesForbidden`. ADR-0001 wording updated accordingly.
2. **Streaming everywhere**: `ConsultantWordMLParser.parse()` moves from full `ET.parse()` to the same `iterparse` early-exit pattern already used in `_extract_consultant_title_first_line`; relation-candidates script likewise.
3. **Bounded-memory contract**: stdlib `iterparse` + `elem.clear()` leaves a growing element skeleton; either document as a bounded non-claim or pass the M034 S02 `lxml` equivalence gate (`lxml.etree.iterparse(tag=...)` + previous-sibling deletion) for the full-codes corpus.
4. **Zip-bomb guard** in ODT readers (`scripts/build-odt-smoke-records.py` `read_content_xml`): check `ZipInfo.file_size` and compression ratio before `zf.read()`.
5. **Python 3.13+ floor** (already the project baseline per `prd/10_m006_parser_graph_staging_recommendation.md`): `iterparse.close()`, expat ≥ 2.6 reparse-deferral fixes.
6. **Helper dedup**: `flatten_text`/`namespaced`/`bounded_text`/`diagnostic` currently copied across `scripts/smoke-s05-odt-parser.py`, `scripts/build-odt-smoke-records.py`, `scripts/build-consultant-relation-candidates.py` — consolidate into one adapters module.

## 10. Slice plan (sequenced, proof-gated)

| Slice | Scope | Proof gate | Main touchpoints |
|---|---|---|---|
| **U1** | RawBlock IR + profile loader; migrate WordML + ODT adapters onto IR | Byte-equivalent M009 records + ODT smoke records | `ports/source_hierarchy.py`, `adapters/sources/consultant_hierarchy.py`, `scripts/build-odt-smoke-records.py`, new `adapters/sources/profiles/*.yaml` |
| **U2** | Two-pass engine; full ladder (раздел/абзац/преамбула/приложения); profile auto-selection | Golden fixtures per `document_type` (≥1 per type from the 53-fixture corpus); mismatch = blocking diagnostic | `adapters/sources/consultant_hierarchy.py`, `prd/parser/golden_cases.json` |
| **U3** | FRBR identity: `act_id`/`edition_id` in records; multi-manifestation merge rule | Same-act Consultant+Garant fixtures merge on `edition_id`; schema updates validate | `consultant_wordml.py`, `prd/parser/schemas/document_record.schema.json` |
| **U4** | Reference + NormStatement candidates | Internal refs resolve ≥X% on 44-FZ golden; external refs stay unresolved-by-design; all candidates `unverified` | new extractor modules, `scripts/build-consultant-relation-candidates.py` |
| **U5** | Temporal/validity marker surface | Markers → bounded fields with `temporal_confidence: unknown` default; no legal-effect strings in artifacts | `consultant_wordml.py`, hierarchy engine |

Each slice keeps the M034 verification contract (`prd/research/source_structuring/25-corrected-consultant-xml-parser-roadmap.md` §"Suggested verification contract") and adds its own checks.

## 11. LLM-agent role: where it strengthens the parser — and whether it is needed

### 11.1 The boundary is already decided

The project has a ratified protocol for LLM participation: `prd/research/source_structuring/05-llm-worker-dspy-protocol.md` (M031 S05, advances R039). Its rules:

- LLM workers (MiniMax, GPT-5.5, DSPy candidate, RLM router) may only **propose bounded structural hypotheses** over safe artifact refs;
- a **deterministic verifier is the sole acceptance gate**; rejected/needs-review queues are auditable;
- durable artifacts must not contain raw legal text, raw prompts/completions, provider payloads, or absolute paths;
- prior art exists: `Old_project/parsing_prompt.yaml` — a DSPy GEPA/MIPROv2-optimized prompt for structure extraction, already marked `manual_verified: true, llm_verified: true`.

So the question is not "may LLM touch parsing" (protocol says: as proposer only) but "where does a proposer add measurable value over deterministic parsing".

### 11.2 Where deterministic parsing is already sufficient (LLM NOT needed)

- **Core hierarchy extraction.** Russian NPA markers are closed-class and highly regular (`Глава N.`, `Статья N.`, `N.`, `N)`, `а)`). M009 proves deterministic context-first extraction works on the canonical fixture; 39/41 fixtures already parse at document level (`prd/parser/README.md` probe snapshot). Introducing LLM into the parse path would add nondeterminism, cost, and prompt-injection surface where precision is already ~total.
- **Identity/keys, hashes, spans, ordering** — pure determinism by definition.
- **Record validation, schema gates, staging graph invariants** — already executable.

**Verdict for the parse path: LLM is not needed and must stay out of it** (consistent with `02_architecture.md`: "минимизировать влияние LLM на юридически проверяемых участках").

### 11.3 Where an LLM agent measurably strengthens the parser (proposer role, behind the verifier)

| # | Role | Why LLM helps here | Acceptance gate (deterministic) |
|---|---|---|---|
| L1 | **Profile discovery for new document types** — propose marker families, style→level maps, zone rules for the 39 `success-as-other` fixtures and new sources | Pattern generalization over Cyrillic legalese is an LLM strength; the profiler pass (U2) supplies the safe aggregate inputs | Candidate profile must reproduce golden fixture structure with zero blocking diagnostics before adoption |
| L2 | **Anomaly triage** — classify `structural_errors`/rejected markers (orphan пункты, numbering gaps) into `parser_gap` vs `source_irregularity` buckets | Real Consultant exports contain irregular numbering (вставные пункты `7.1)`); judgment-like classification over bounded excerpts | Buckets only; each triage decision linked to source span; spot-check sampling by tests |
| L3 | **NormStatement candidate formulation** — turn deontic hits into normalized candidate payloads (norm_type/modality/subject) | Lexeme table catches presence, not argument structure; LLM proposes, e.g., `APPLIES_TO` subject candidates | All stay `verification_status: unverified`, `extraction_method: llm_candidate` per §2a contract; deterministic compatibility-matrix validator runs first |
| L4 | **External-reference normalization** — map noisy citation strings (`ФЗ от 05.04.2013 N 44-ФЗ`, `Закон о закупках`) to candidate `act_id`s | Citation surface forms vary widely; LLM ranks candidate matches | Resolution remains deferred; LLM output is one ranked hint among deterministic signals, never a resolved edge |
| L5 | **Golden/fixture authoring aid** — propose new golden cases and adversarial fixtures (roman numerals, missing chapters) | Cheap expansion of test coverage | Cases enter the corpus only through the existing generator/check chain (`scripts/build-parser-golden-cases.py --check`) |
| L6 | **Prior-art transfer review** — mine `Old_project/validation/structural_rules.yaml` / `semantic_rules.yaml` for rules worth downgrading to diagnostics | Reading/summarizing legacy rule bases at scale | M034 S04 rule: semantic rules land as advisory diagnostics only, never legal truth |

### 11.4 Hard prohibitions (unchanged)

- No LLM output in the parse path between source bytes and parser records.
- No LLM-resolved references as graph edges (candidates only).
- No raw legal text / raw prompts in durable artifacts (M031 S05 forbidden payload classes).
- No claims of parser completeness, legal correctness, R035/R037/R038 validation from any LLM-assisted artifact.

### 11.5 Overall verdict

**Needed? No — for parsing itself.** The deterministic engine covers structure; that is the project's founding bet and M009 proves it.

**Useful? Yes — in exactly one posture:** a *hypothesis proposer* operating on safe aggregates (profile discovery, triage, candidate formulation, fixture authoring), with the deterministic verifier from M031 S05/S06 as the only adoption gate. Recommended adoption order: L1 (profile discovery) first — it directly unblocks U2's per-type profiles — then L5, L2; L3/L4 only after U4 lands and can hold candidates.

## 12. Explicit non-claims

This proposal does not claim: parser completeness; legal correctness; authoritative legal interpretation; Consultant/Garant legal authority; multi-source parser readiness; product ETL readiness; FalkorDB loading/runtime readiness; retrieval quality; citation-safe answer readiness; R035/R037/R038 validation; LLM-output authority of any kind.

## 13. Suggested first verification commands (after U1)

```bash
uv run python scripts/inventory-parser-fixtures.py --check
uv run python scripts/validate-parser-records.py --check
uv run python scripts/build-consultant-hierarchy-records.py --check   # equivalence oracle
uv run python scripts/build-odt-smoke-records.py --check              # ODT equivalence
uv run pytest -q tests/test_consultant_hierarchy_records.py tests/test_odt_smoke_records.py
```

# M031 S01 — law-parser Prior-Art Assessment

## Status

- Milestone: `M031-oqgiow — Consultant XML Source Structuring CLI Foundation`
- Slice: `S01 — Prior Art and NLP Stack Assessment`
- Assessment status: `draft_for_s01_verification`
- Decision context: `D062` pauses same-fixture retrieval and descriptor proof cycles until a source-structuring foundation exists.
- Requirement context: `R039` calls for a reproducible ConsultantPlus WordML source-structuring CLI with safe inventories, logs, summaries, and GSD review packs.

## Executive conclusion

The old `law-parser` checkout is valuable as **prior art**, but not as trusted implementation. It provides:

- a useful ConsultantPlus WordML XML corpus across multiple document kinds;
- real WordML 2003 source-shape evidence;
- derived 44-FZ structure and article outputs that can serve as comparison baselines;
- YAML pattern/specification prior art for hierarchy, parsing, semantic checks, and structural checks;
- useful dependency choices for Russian tokenization and morphology;
- useful but deferred ideas for MiniMax, DSPy, and RLM-assisted structural discovery.

It does **not** provide a ready parser to copy into `law-nexus`. The planned `src/law_parser/parsing/*` and `src/law_parser/structure/*` source files are absent from the current checked-out tree, while old planning reports describe broken or unverified parser modules. Therefore M031 should reuse the corpus, contracts, patterns, and lessons, while rebuilding the CLI and source lifecycle in `law-nexus` with fresh tests and safe artifact boundaries.

## Proof pause boundary

Further same-fixture retrieval and descriptor proof cycles are paused until the project has a reproducible source foundation:

```text
ConsultantPlus WordML XML pool
-> deterministic source inventory
-> safe structural samples
-> source/revision registry
-> parser routing diagnostics
-> GSD review pack
```

This assessment does not validate R035 (`no R035 validation`) and does not claim parser completeness, legal correctness, product retrieval quality, graph-vector behavior, production ETL readiness, pilot readiness, or LLM legal authority.

## External prior-art source scope

The assessment used the external `law-parser` checkout as a prior-art source. Durable anchors below are relative to that checkout, not absolute host paths.

Important old-repo-relative paths:

- `doc_domain_44fz/cons/` — ConsultantPlus WordML XML corpus.
- `doc_domain_44fz/cons/44-FZ/44-FZ-2026.xml` — representative full-act WordML source.
- `doc_domain_44fz/cons/44-FZ/44-FZ-2026-structure.json` — prior derived 44-FZ structure output.
- `doc_domain_44fz/cons/44-FZ/44-FZ-2026-articles.jsonl` — prior derived article output.
- `scripts/validate_rlm_parsing.py` — streaming WordML/RLM prototype.
- `prompt_domain_44fz/sources/consultant_word2003xml.yaml` — source-format prior spec.
- `prompt_domain_44fz/parsing_prompt.yaml` — hierarchy and LLM/DSPy prompt prior art.
- `prompt_domain_44fz/structures/44fz.yaml` — 44-FZ hierarchy/pattern prior art.
- `prompt_domain_44fz/validation/semantic_rules.yaml` — semantic validation prior art.
- `prompt_domain_44fz/validation/structural_rules.yaml` — structural validation prior art.
- `prompt_domain_44fz/contracts/api.yaml` — older CLI contract idea.
- `prompt_domain_44fz/contracts/extractor-api.md` — extractor contract prior art.
- `pyproject.toml` — old dependency choices.
- `docs/RLM_RS_INTEGRATION_GUIDE.md` and `research/DSPy_vs_RLM-Toolkit.md` — RLM/DSPy comparison prior art.

## Corpus inventory

A safe inventory check found `51` XML files under the old ConsultantPlus corpus. Filename-based document-kind buckets were:

| Bucket | Count | Reuse decision |
| --- | ---: | --- |
| `court_act` | 13 | Reuse as future document-role coverage input. |
| `review` | 12 | Reuse for inventory/classification coverage, not as normative-act structure proof. |
| `fas_decision` | 8 | Reuse for FAS-decision route/classification coverage. |
| `44fz_related` | 5 | Reuse as primary early corpus slice and comparison baseline. |
| `list` | 5 | Reuse for relation-list route tests. |
| `other` | 4 | Inventory-only until classified. |
| `federal_law` | 2 | Reuse for law-role coverage beyond 44-FZ. |
| `government_resolution` | 1 | Reuse for government-resolution route coverage. |
| `order` | 1 | Reuse for order route coverage. |

The corpus is enough to justify M031's first source family as `consultant_wordml`, while preserving `document_role` as a separate dimension.

## Representative source-shape evidence

Representative safe structural metrics confirm the corpus uses WordML 2003 XML and carries useful structural signals. No raw legal text was needed for these checks.

| Representative role | SHA-256 prefix | Size bytes | Paragraphs | Links | Tables | WordML namespace |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 44-FZ full-act representative | `69df0b9d9e2b` | 5,235,817 | 3,601 | 3,771 | 52 | `http://schemas.microsoft.com/office/word/2003/wordml` |
| Government-resolution representative | `2ebda3f3db5b` | 793,172 | 733 | 612 | 11 | `http://schemas.microsoft.com/office/word/2003/wordml` |
| Order representative | `d68facbcfc1c` | 808,161 | 1,947 | 233 | 16 | `http://schemas.microsoft.com/office/word/2003/wordml` |
| FAS-decision representative | `9ec79db9082d` | 106,823 | 87 | 52 | 5 | `http://schemas.microsoft.com/office/word/2003/wordml` |

Common top-level WordML structural tags include `p`, `pPr`, `pStyle`, `r`, `rPr`, `t`, `hlink`, and table-related elements. Style values are mostly compact numeric identifiers such as `0`, `1`, `2`, and `5`; therefore early classification should record style IDs and counts, not assume human-readable style names.

## Source-format hazard

The old `consultant_word2003xml.yaml` prior spec is useful but must be adapted. It records WordprocessingML 2006 namespace mappings, while the observed corpus and the streaming prototype use WordML 2003:

```text
observed: http://schemas.microsoft.com/office/word/2003/wordml
```

Reuse decision: adapt the source-format spec after empirical namespace detection. Do not copy the old namespace configuration as truth.

## Derived 44-FZ baselines

The old checkout contains prior derived outputs:

| Artifact | Safe shape | Reuse decision |
| --- | --- | --- |
| `doc_domain_44fz/cons/44-FZ/44-FZ-2026-structure.json` | keys: `metadata`, `chapters`, `all_references`, `external_laws`, `key_dates`, `definitions`; `chapters=8` | Reuse as baseline for comparison only. |
| `doc_domain_44fz/cons/44-FZ/44-FZ-2026-articles.jsonl` | `94` JSONL rows; keys: `article`, `chapter`, `doc_id`, `invalid`, `parts`, `title` | Reuse as baseline for comparison only. |

These outputs should not be treated as verified legal truth or parser-completeness evidence. They can become regression comparison inputs once the M031 CLI produces its own safe structural records.

## WordML/RLM prototype assessment

`validate_rlm_parsing.py` contains a useful minimal prototype:

- uses `lxml.etree.iterparse` over WordML paragraph elements;
- extracts paragraph text from `w:p` elements;
- starts a new article when a paragraph begins with an article marker;
- clears elements during streaming to manage memory;
- stores a small fact sample in an RLM memory store.

Reuse decision: reuse the **streaming approach** and WordML 2003 namespace lesson. Do not reuse the implementation as a parser because it emits article text, handles only one article-heading heuristic, lacks canonical source/revision IDs, does not build safe source blocks, and does not satisfy M031 durable-output constraints.

## Hierarchy and parsing pattern prior art

`structures/44fz.yaml` and `parsing_prompt.yaml` contain strong reusable pattern knowledge for a federal-law-style hierarchy:

```text
Глава -> [Параграф] -> Статья -> Часть -> Пункт -> Подпункт
```

Reusable concepts:

- chapter, paragraph, article, part, clause, and subclause marker families;
- decimal article numbers and compound clause numbers;
- invalidity marker families;
- date and amendment marker families;
- rule that parts/clauses/subclauses require context-aware hierarchical parsing.

Critical prior lesson:

```text
Global regex matching for parts/clauses creates many false positives.
Context-aware hierarchy parsing is required.
```

Reuse decision: adapt as deterministic rule candidates and validation tests. Do not treat old YAML as complete or generalized beyond its tested source family and document kind.

## Structural and semantic validation prior art

`structural_rules.yaml` provides reusable structural validation ideas:

- every article needs a number;
- chapters should have titles;
- articles should belong to chapters;
- paragraph/text orphan checks;
- document must contain at least one article for full-act routes.

`semantic_rules.yaml` provides reusable semantic-consistency checks:

- article, paragraph, and chapter numbering sequences;
- date format checks;
- internal/external reference shape checks;
- empty article warnings;
- invalidity marker detection.

Reuse decision: adapt these as safe deterministic validators. They are not legal interpretation, and they should produce diagnostics and `needs_review` outcomes rather than legal conclusions.

## Old CLI and extractor contract prior art

The old `api.yaml` already proposed command categories resembling `analyze` and `batch`, with options for input paths, output directories, stages, retries, parallelism, checkpoints, and DSPy toggles. This supports the M031 direction of a lifecycle CLI.

Reuse decision: adapt concepts, not names. M031 uses the accepted lifecycle interface:

```text
source_cli.py register
source_cli.py classify
source_cli.py process
source_cli.py status
source_cli.py review-pack
source_cli.py run-batch
```

The old `extractor-api.md` also documents useful safety and contract practices: bounded size limits, explicit XML parsing errors, typed models, normalized Unicode, and thread-safety expectations. These are reusable as implementation guidance.

## NLP, morphology, and semantic stack assessment

### Recommended for MVP

| Area | Old choice | Evidence | M031 decision |
| --- | --- | --- | --- |
| XML parsing | `lxml` | dependency and streaming prototype | Reuse. First-class MVP dependency. |
| CLI | `typer`, `rich` | old dependency list | Reuse as candidate for operator-facing CLI. |
| Validation | `pydantic`, `pyyaml` | old dependency list | Reuse as schema/config foundation. |
| Logging | `loguru`, `structlog` | old dependency list and planning | Reuse one structured logging path; avoid duplicate noisy abstractions. |

### Recommended soon after MVP

| Area | Old choice | Evidence | M031 decision |
| --- | --- | --- | --- |
| Russian sentence/token segmentation | `razdel` | old dependency and research plan | Reuse for structural sample enrichment and marker processing after basic inventory works. |
| Russian morphology | `pymorphy3` | old dependency and research plan | Reuse for normalized marker families, invalidity markers, and less brittle structural rules. |

### Keep from current law-nexus evidence

| Area | Current choice | Decision |
| --- | --- | --- |
| Local embedding baseline | `deepvk/USER-bge-m3`, local files only, observed dimension `1024` | Keep as current bounded semantic scoring backend. Old MiniLM choices do not supersede it. |

### Defer

| Area | Old choice | Reason to defer |
| --- | --- | --- |
| DSPy / MIPRO / GEPA | `dspy`, prompt optimization configs | Needs stable sample schema, accepted examples, deterministic verifier metrics, and non-authoritative hypothesis protocol first. |
| MiniMax worker | prompt prior art | Useful later as structural discovery worker, not legal interpreter. Needs payload safety and deterministic verifier gate. |
| RLM / RLM-RS | old docs and RLM router/prototype | Useful later for large-document structural sample retrieval, but not required for deterministic MVP. |
| Sentence-transformers MiniLM router | `all-MiniLM-L6-v2`, fallback MiniLM | Reuse routing architecture only; do not reuse model choice as LegalGraph retrieval-quality evidence. |
| Docling, PyMuPDF, OCR | old dependencies | Defer until source families beyond ConsultantPlus WordML need them. |
| FalkorDB / GraphRAG runtime | old dependencies | Out of M031 MVP scope; source foundation first. |

## Old implementation status

The checked-out old tree does not contain the planned parser source files:

| Old path | Exists in checked-out source tree | Reuse decision |
| --- | --- | --- |
| `src/law_parser/parsing/wordml_extractor.py` | no | Do not reuse. |
| `src/law_parser/parsing/element_classifier.py` | no | Do not reuse. |
| `src/law_parser/structure/document.py` | no | Do not reuse. |
| `src/law_parser/structure/hierarchy.py` | no | Do not reuse. |

Old planning reports mention broken or unverified structure modules, including article ID auto-generation and runtime hierarchy type-check issues. The safe conclusion is that implementation must be rebuilt in `law-nexus` under fresh tests.

## Reuse map

| Asset | Classification | Rationale |
| --- | --- | --- |
| ConsultantPlus XML corpus | reuse | Real multi-kind WordML corpus for M031 inventory and routing. |
| 44-FZ derived outputs | adapt as baseline | Useful comparison outputs; not trusted truth. |
| WordML 2003 namespace evidence | reuse | Confirmed in representative XML files and prototype. |
| `validate_rlm_parsing.py` | adapt approach only | Useful streaming idea; output and model do not satisfy current safety contract. |
| `consultant_word2003xml.yaml` | adapt | Useful source-format idea but namespace mismatch must be corrected empirically. |
| `44fz.yaml` | adapt | Strong law-hierarchy pattern prior art; not generalized proof. |
| `parsing_prompt.yaml` | adapt | Useful hierarchy and DSPy/MiniMax protocol prior art; LLM remains non-authoritative. |
| `semantic_rules.yaml` | adapt | Useful deterministic diagnostics. |
| `structural_rules.yaml` | adapt | Useful deterministic diagnostics. |
| `api.yaml` and extractor contracts | adapt | Useful lifecycle and error contract ideas. |
| Old `src/law_parser` parser modules | reject for direct reuse | Source files absent or unverified/broken. |
| Heavy PDF/OCR/document conversion dependencies | defer | Not needed for ConsultantPlus WordML MVP. |
| RLM/RLM-RS | defer | Useful later for large-document sample retrieval. |
| DSPy | defer | Useful later after accepted examples and metrics exist. |

## Recommended M031 dependency policy

M031 deterministic CLI MVP should start with:

```text
lxml
pydantic
pyyaml
typer
rich
loguru or structlog
```

Add after basic inventory and schemas stabilize:

```text
razdel
pymorphy3
```

Keep semantic scoring baseline from current project evidence:

```text
deepvk/USER-bge-m3
local_files_only=true
observed vector dimension 1024
```

Do not add as M031 MVP requirements:

```text
DSPy
RLM/RLM-RS
Docling
PyMuPDF
OCR
FalkorDB graph loading
managed embedding APIs
```

## Safety and non-authoritative boundaries

The M031 source CLI and artifacts must preserve these boundaries:

- no raw legal text in durable assessment, registry, run summary, metrics, diagnostics, or review-pack artifacts;
- no raw XML content in durable proof artifacts;
- no raw vectors;
- no provider or external LLM payloads;
- no prompts containing source text;
- no secrets;
- no absolute host paths as proof anchors;
- no generated legal-answer prose;
- LLM outputs, if introduced later, are structural hypotheses only;
- deterministic verifier gates are required before adopting LLM-proposed structural rules.

## Implications for S02 and CLI design

S02 should formalize the accepted source workspace layout:

```text
law-source/consultant/fixtures/
law-source/consultant/inbox/
law-source/consultant/raw/
law-source/consultant/registry/
law-source/consultant/processed/
law-source/consultant/schemas/
law-source/consultant/runs/
```

`prd/research/source_structuring/` remains the GSD/research summary surface.

The CLI should expose one lifecycle interface:

```text
source_cli.py register
source_cli.py classify
source_cli.py process
source_cli.py status
source_cli.py review-pack
source_cli.py run-batch
```

Parser routing must keep `source_family` separate from `document_role`:

```text
source_family: consultant_wordml
document_role: full_normative_act | government_resolution | ministry_order | fas_decision | court_act | review | document_list | unknown
```

Ambiguous or unsupported inputs should route to `inventory_only` or `needs_review`, not to unsafe parser assumptions.

## S01 verification summary

Fresh safe inventory checks confirmed:

- old prior-art checkout exists;
- ConsultantPlus XML corpus count is `51`;
- representative source files use WordML 2003 namespace;
- representative source files expose paragraph, link, table, tag, and style-count signals;
- 44-FZ derived structure and article outputs exist;
- old dependency file contains lxml, razdel, pymorphy3, DSPy, LiteLLM, Docling, PyMuPDF, OCR, Typer, Rich, logging, FalkorDB, and GraphRAG dependencies;
- planned parser implementation source files are absent in the checked-out old tree;
- safe assessment content uses structural metrics and hashes, not raw legal text.

## Final S01 disposition

Proceed to S02 with this stance:

```text
Use old law-parser as corpus/spec/prior-art evidence.
Rebuild source lifecycle and CLI in law-nexus.
Pause further same-fixture retrieval proof until M031 produces safe source-structure artifacts.
```

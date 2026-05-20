# Old Project Transfer Decision List

## Purpose

This is a review matrix for human confirmation before any Old_project idea is transferred into the current Consultant XML parser workline.

No item below is accepted as trusted implementation. Decisions mean:

- `adopt-existing`: already adopted in the current repo through deterministic proof.
- `adapt-now`: useful for the next Consultant XML hardening milestone, but only via tests/proof.
- `adapt-later`: useful, but not the next parser-foundation step.
- `evidence-only`: keep as context/history, do not implement from it.
- `defer`: not usable until later proof exists.
- `reject`: do not use as implementation path.

Boundary: this list does not validate R035, does not validate R037, and does not validate R038. It does not claim legal correctness, parser completeness, product ETL readiness, FalkorDB ingestion, or citation-safe retrieval.

## Executive recommendation

Transfer ideas, not implementation. The current baseline is M009: `M009 is the current bounded Consultant XML hierarchy baseline`.

Priority order:

1. Adapt WordML source-format observations into parser diagnostics/tests.
2. Evaluate `lxml` only as a deliberate optional migration/hardening candidate for streaming, memory, and namespace behavior; do not switch from the M009 stdlib baseline silently.
3. Adapt structural hierarchy vocabulary and structural validation rules into deterministic tests around the M009 extractor.
4. Use old extracted JSON/JSONL only as comparison baselines, not as source of truth.
5. Defer semantic/legal rules and morphology/tokenization libraries until source-span and citation-safe evidence or a concrete parser rule proves they are needed.
6. Defer API/contracts until parser record gaps are resolved.

## Python semantic and parsing library decision matrix

These libraries come from the old `/root/law-parser` project metadata and planning notes, not from `Old_project/` YAML alone. They are included here because they materially affect parser/semantic design decisions.

| Library / stack | Old-project source | Intended old role | My decision | Why | Human review question |
|---|---|---|---|---|---|
| `lxml` | `prd/research/source_structuring/01-law-parser-prior-art-assessment.md`; `/root/law-parser/pyproject.toml`; Phase 2 research | Memory-efficient WordML XML parsing via `iterparse`; namespace-aware XML handling. | `adapt-now` / first-class MVP dependency candidate | Prior M031 assessment explicitly recommended `lxml` as a first-class MVP dependency. Current M009 stdlib parser is the working baseline, so actual migration still needs equivalence tests, but the library decision is already positive. | Confirm whether next hardening milestone should include an `lxml` equivalence/performance slice. |
| `razdel` | `01-law-parser-prior-art-assessment.md`; `/root/law-parser/pyproject.toml`; Phase 2 research/context | Russian tokenization and sentence segmentation. | `adapt-soon-after-mvp` | Prior M031 assessment says reuse after basic inventory works for structural sample enrichment and marker processing. Not rejected; timing depends on parser hardening needs. | Should `razdel` enter the next hardening milestone for marker/diagnostic enrichment? |
| `pymorphy3` | `01-law-parser-prior-art-assessment.md`; `/root/law-parser/pyproject.toml`; Phase 2 research/context | Russian morphology, lemmatization, POS/case normalization. | `adapt-soon-after-mvp` | Prior M031 assessment says reuse for normalized marker families, invalidity markers, and less brittle structural rules after inventory/schema baseline. | Which marker families or invalidity diagnostics should require morphology first? |
| `pymorphy3-dicts-ru` | Phase 2 research note | Required Russian dictionaries for `pymorphy3`. | `adapt-with-pymorphy3` | Required support package once morphology is adopted; should be pinned and smoke-tested together with `pymorphy3`. | Which dictionary/version pin is acceptable for reproducible parser diagnostics? |
| `loguru` / `structlog` / `python-json-logger` | `01-law-parser-prior-art-assessment.md`; `/root/law-parser/pyproject.toml`; Phase 2 research | Structured logging and JSON diagnostics. | `adapt-now-one-path` | Prior M031 assessment recommended reusing one structured logging path and avoiding duplicate noisy abstractions. Current JSON artifacts may satisfy some needs, but logging was not meant to be dismissed. | Choose `loguru`, `structlog`, or stdlib JSON logging for CLI/runtime diagnostics? |
| `pydantic` | `01-law-parser-prior-art-assessment.md`; current law-nexus parser records already use Pydantic v2 | Strict parser record validation. | `adopt-existing` | Already accepted as schema/record boundary via `scripts/parser_records.py` and schemas. | Continue Pydantic v2 as parser-record boundary? |
| `pyyaml` | `01-law-parser-prior-art-assessment.md`; `/root/law-parser/pyproject.toml`; Old_project YAML specs | YAML prompt/spec/rule loading. | `adapt-now-for-config/spec-loading` | Prior M031 assessment grouped PyYAML with schema/config foundation. Runtime parser authority still needs tests, but YAML reading itself is accepted for config/spec ingestion. | Which YAML specs become inputs to tests/config, and which remain documentation only? |
| `dspy` | `/root/law-parser/pyproject.toml`; old prompt configs mention DSPy | Prompt optimization / extraction experiments. | `defer` for parser authority | LLM/DSPy must remain non-authoritative. Could be used for proposal generation only after deterministic verifier exists. | Keep DSPy out of parser foundation entirely? |
| `litellm`, `anthropic`, `google-genai`, `google-cloud-aiplatform` | `/root/law-parser/pyproject.toml` | LLM provider integration. | `defer` / not parser foundation | Provider stack is unrelated to deterministic XML parsing and risks authority drift. | Exclude from XML parser milestone? |
| `langgraph`, `fast-langgraph`, `langsmith` | `/root/law-parser/pyproject.toml` | Agent orchestration and observability. | `defer` | Not needed for parser foundation; maybe later workflow orchestration. | Keep out of parser core? |
| `graphrag-sdk`, `falkordb`, `redis` | `/root/law-parser/pyproject.toml` | Graph/RAG/FalkorDB runtime. | `defer to R037 milestone` | Graph runtime must not be mixed with parser proof. | Separate graph ingestion milestone only? |
| `python-docx`, `PyMuPDF`, `pytesseract`, `Pillow`, `docling`, `pymupdf-layout` | `/root/law-parser/pyproject.toml` | Other document formats and OCR/layout extraction. | `defer` | Not relevant to Consultant WordML XML hardening unless future source formats require them. | Exclude from Consultant XML scope? |
| `fastapi`, `granian`, `httpx`, `typer`, `rich` | `/root/law-parser/pyproject.toml` | Service/API/CLI stack. | `defer` except current CLI stays stdlib unless needed | API/server stack is not parser foundation. Current law-nexus CLI intentionally avoided undeclared Typer. | Keep parser tools as stdlib CLIs for now? |

### Library-level recommendation

For the next Consultant XML hardening milestone:

1. Keep M009 stdlib parser as the current working baseline, but treat prior M031's `lxml` decision as positive: `lxml` should be evaluated in an explicit equivalence/performance hardening slice rather than silently substituted.
2. Treat `lxml` as a first-class parser dependency candidate for streaming/memory/namespace behavior, per `01-law-parser-prior-art-assessment.md`.
3. Treat `razdel` and `pymorphy3` as “soon after MVP” dependencies for marker enrichment, invalidity-marker normalization, and less brittle structural rules, not as rejected/deferred unknowns.
4. Keep LLM/DSPy/RAG/provider libraries out of parser authority.
5. Keep Pydantic v2 as the accepted parser-record validation boundary.
6. Treat PyYAML as accepted for config/spec loading, while keeping YAML-driven runtime parser authority test-gated.

## Artifact decision matrix

| # | Artifact | Type / idea | My decision | Why | Human review question |
|---:|---|---|---|---|---|
| 1 | `Old_project/sources/consultant_word2003xml.yaml` | Consultant Word 2003 XML namespaces, element paths, preprocessing ideas | `adapt-now` | Directly relevant to Consultant XML parser diagnostics and M009 hardening. Must be converted into tests against `44-FZ-2026.xml`; not copied as parser authority. | Which preprocessing rules are acceptable for preserving source spans? |
| 2 | `Old_project/structures/44fz.yaml` | 44-FZ hierarchy vocabulary and structure hypotheses | `adapt-now` | Useful for comparing hierarchy levels, parent rules, marker expectations, and missing boundaries against M009 records. | Which hierarchy rules should become hard parser invariants versus advisory diagnostics? |
| 3 | `Old_project/validation/structural_rules.yaml` | Structural validation rules | `adapt-now` | Good source for deterministic checks: parentage, ordering, duplicates, orphan markers. | Which structural rules should block parser output, and which should only warn? |
| 4 | `Old_project/legislation_hierarchy.yaml` | Russian legal document taxonomy / hierarchy vocabulary | `adapt-later` | Useful for broader legal taxonomy, but the immediate task is Consultant 44-FZ XML hardening. | Should this feed parser record enums now, or wait for multi-document/multi-source work? |
| 5 | `Old_project/parsing_prompt.yaml` | LLM/human parsing prompt and extraction guidance | `evidence-only` / `adapt-later` | Can reveal intended units and terminology, but prompts must not create parser facts. Convert only selected ideas into deterministic tests. | Are there specific extraction units in the prompt that should become parser gap tickets? |
| 6 | `Old_project/archive/parsing_prompt_1.0.0_20251231_1425.yaml` | Archived parser prompt | `evidence-only` | Historical prompt/spec snapshot. Useful for evolution context only. | Any old prompt section worth comparing against current M009 output? |
| 7 | `Old_project/archive/yaml_prompt_20251231_1230.yaml` | Archived document-structure prompt | `evidence-only` | Historical prompt/spec snapshot, not implementation. | Keep only as background, or mine for terminology? |
| 8 | `Old_project/validation/semantic_rules.yaml` | Semantic/legal validation rules | `adapt-for-diagnostics` / source-grounded legal semantics still deferred | Prior `01-law-parser-prior-art-assessment.md` classified semantic rules as useful deterministic diagnostics. They should not become legal truth, but some can be converted into marker/diagnostic checks. | Which semantic rules can be downgraded into deterministic structural/marker diagnostics? |
| 9 | `Old_project/memory/failed_experiments.yaml` | Failed experiment notes | `reject` as implementation; `evidence-only` as warning | Failed path should not be revived without a new hypothesis and test. | Are there warnings here that should become negative tests? |
| 10 | `Old_project/memory/learned_examples.yaml` | Learned examples | `adapt-later` | May contain useful examples, but must be checked against tracked source evidence. | Which examples are still relevant to Consultant XML? |
| 11 | `Old_project/memory/successful_patterns.yaml` | Successful pattern notes | `adapt-later` | Could become tests or docs only after source-backed verification. | Which patterns should be promoted into deterministic parser tests? |
| 12 | `Old_project/contracts/api.yaml` | API contract ideas for normative document analysis | `defer` | API design should follow current parser record contract, not drive it. | Review after parser output gaps are known. Any API terms worth preserving? |
| 13 | `Old_project/contracts/extractor-api.md` | Extractor API vocabulary | `defer` / `adapt-later` | Useful for naming, but premature before source spans and parser gaps are settled. | Should any extractor terms map to current `parser_records.py` fields? |
| 14 | `Old_project/index.yaml` | Specs index | `evidence-only` | Useful navigation aid for old project only. | No transfer unless it exposes missing artifact categories. |
| 15 | `Old_project/federal_authorities.yaml` | Federal authorities taxonomy | `defer` | Potential future entity/taxonomy source, not needed for Consultant structural parser hardening. | Should authority taxonomy be a separate future registry milestone? |
| 16 | `Old_project/federal_control_authorities.yaml` | Federal control/regulatory authorities taxonomy | `defer` | Same as above; not parser-foundation. | Future registry? |
| 17 | `Old_project/registers/federal_acts.yaml` | Federal acts registry | `adapt-later` | Could inform document identity/registry work after parser records stabilize. | Should this become a document registry fixture later? |
| 18 | `Old_project/registers/letters.yaml` | Letters registry | `defer` | Different document class. Not part of 44-FZ XML parser hardening. | Keep for later multi-document support? |
| 19 | `Old_project/development/REGIONAL_CONTROL_AUTHORITIES_PLAN.md` | Development roadmap for regional control authorities | `defer` | Product/domain roadmap, not current parser foundation. | Any domain taxonomy dependencies worth preserving? |
| 20 | `Old_project/structures/archive/44fz_1.1.0_20251231_1407.yaml` | Archived 44-FZ structure spec | `evidence-only` | Version history only; current `structures/44fz.yaml` is the candidate to inspect first. | Use for diff history only? |
| 21 | `Old_project/structures/archive/44fz_2.0.0_20251231_1436.yaml` | Archived 44-FZ structure spec | `evidence-only` | Version history only. | Use for evolution notes? |
| 22 | `Old_project/structures/archive/44fz_2.2.0_20260101_0029.yaml` | Archived 44-FZ structure spec | `evidence-only` | Version history only. | Any version contains rules missing from current structure file? |
| 23 | `Old_project/structures/archive/44fz_2.2.0_20260101_1448.yaml` | Archived 44-FZ structure spec | `evidence-only` | Version history only. | Same. |
| 24 | `Old_project/structures/archive/44fz_20251231_1200.yaml` | Archived 44-FZ structure spec | `evidence-only` | Version history only. | Same. |
| 25 | `Old_project/structures/archive/44fz_20251231_1340.yaml` | Archived 44-FZ structure spec | `evidence-only` | Version history only. | Same. |
| 26 | `Old_project/structures/archive/44fz_20251231_1341.yaml` | Archived 44-FZ structure spec | `evidence-only` | Version history only. | Same. |
| 27 | `Old_project/structures/archive/44fz_20260101_1918.yaml` | Archived 44-FZ structure spec | `evidence-only` | Version history only. | Same. |

## Ideas to transfer into the next Consultant XML hardening milestone

### Adapt now

1. WordML XML namespace and element diagnostics.
2. Paragraph/text-run extraction assumptions.
3. Whitespace and entity normalization checks, with source-span preservation review.
4. Structural hierarchy vocabulary: document, chapter, section, article, part, clause, subclause.
5. Parentage/order/orphan diagnostics from structural rules.
6. Prior-art comparison expectations as advisory checks, not truth.

### Adapt later

1. Registry/document identity ideas.
2. API/extractor vocabulary.
3. Authority taxonomy and document-class taxonomy.
4. Learned/successful examples after mapping them to tracked fixtures.

### Defer or reject

1. Semantic legal validation rules until citation-safe source spans and legal-domain review exist.
2. Any prompt-driven parsing as runtime authority.
3. Any old parsed JSON/JSONL output as canonical legal data.
4. Any Consultant XML assumption applied to Garant ODT without separate ODT proof.
5. Failed-experiment paths as implementation.

## Human review checklist

Please review these decisions first:

1. Do you agree that `consultant_word2003xml.yaml`, `structures/44fz.yaml`, and `validation/structural_rules.yaml` are the only `adapt-now` Old_project files?
2. Should `legislation_hierarchy.yaml` move from `adapt-later` to `adapt-now` for parser enums/taxonomy?
3. Are any semantic rules safe to downgrade into structural checks, or should all remain deferred?
4. Should API/extractor contracts remain deferred until parser records and source spans are hardened?
5. Should authority/register YAML files become a separate future registry milestone rather than part of Consultant XML parsing?

6. Do you agree that `lxml` should be evaluated as an explicit equivalence/performance hardening slice, preserving M009 stdlib output as the comparison oracle during migration?
7. Which `razdel` / `pymorphy3` use case should be first: marker-family normalization, invalidity-marker diagnostics, sentence segmentation for excerpts, or none yet?

## Non-claims

This decision list is a review artifact only. It does not transfer code, does not accept old outputs as legal truth, and does not validate R035, R037, or R038.

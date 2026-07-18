# S05 ODT Parser Findings

## Parser direction

Use the raw `content.xml` traversal as the ordering oracle for the next parser-design step, and treat `odfdo` as the current parser direction to investigate for unmodified ODT loading and higher-level API ergonomics. `odfpy` is not accepted as the sole parser because the unmodified-load phase fails on the real `META-INF/manifest.xml` DOCTYPE; its successful temp-clean-manifest phase is controlled parser-comparison evidence only, not proof that the original file loads unchanged.

This recommendation is conservative: it is smoke evidence for parser selection, not final legal hierarchy extraction, final table reconciliation, SourceBlock persistence, or product ETL implementation. Alternative parser comparison is complete for this slice when the explicit transient-dependency run is used because `odfdo` loaded the unmodified source; if the dependency-free verification command records an optional parser as `not-installed`, the alternative parser comparison is blocked for that environment and the resolution path is to rerun with explicit transient dependencies before using the result for parser selection. S06/S07/S08 still need to cite this artifact before changing skill, PRD, or architecture claims.

## Real ODT evidence

Machine-readable probe log: `prd/milestone_proofs/M001_S05_logs_odt-parser-probes.json`.

| Evidence field | Observed value | Owner | Resolution path | Verification criterion |
|---|---:|---|---|---|
| Real source path | `law-source/garant/44-fz.odt` | S05 | Preserve this tracked-source path as the only real-source smoke target. | `scripts/verify-s05-odt-parser.py` rejects fixture substitution. |
| Source size | 247971 bytes | S05 | Keep size and SHA-256 in the probe log for future source-change detection. | Probe log includes non-zero `size_bytes` and 64-character SHA-256. |
| SHA-256 | `73777d4741fa1b65229a8b22b97eb2cff4c5180105affb79b058d7007e3e4337` | S05 | Re-run the probe if the tracked ODT changes. | Verifier confirms source metadata exists; future agents compare hash deltas. |
| Manifest DOCTYPE | `true` | S05 | Keep the manifest issue visible for parser selection and security review. | Findings mention manifest and unmodified-load behavior. |
| Ordered heading/paragraph blocks | 5244 | S05 | Use raw traversal as ordering oracle for parser comparisons. | Probe status `raw-baseline=verified-source-evidence`. |
| Table count | 1 | S05/S07 | Treat as smoke-only count; reconcile with any later parser/table abstraction before PRD claims. | S07 must cite parser probe evidence before table-count or hierarchy claims. |
| Legal marker counts | `закон=2511`, `закупк=1786`, `контракт=1708`, `пункт=1379`, `статья=268`, `часть=898` | S05/S08 | Preserve markers as raw text observations, not extracted legal facts. | Downstream docs must keep LLM non-authoritative boundaries. |

Exact Russian marker examples preserved from the raw probe include:

- `Федеральный закон от 5 апреля 2013 г. N 44-ФЗ "О контрактной системе в сфере закупок товаров, работ, услуг для обеспечения государственных и муниципальных нужд"`
- `Статья 1. Сфера применения настоящего Федерального закона`
- `Пункт 3 изменен с 8 января 2020 г. - Федеральный закон от 27 декабря 2019 г. N 449-ФЗ`
- `Федеральным законом от 28 декабря 2013 г. N 396-ФЗ часть 2 статьи 1 дополнена пунктом 5, вступающим в силу с 1 января 2014 г.`

## Parser comparison

| Parser | Status | Evidence class | Owner | Resolution path | Verification criterion |
|---|---|---|---|---|---|
| raw-baseline | verified-source-evidence | verified-source-evidence | S05 | Keep raw `content.xml` ordering as the oracle for later parser comparison. | Probe issue `S05-raw-odt-baseline` remains present and verifier passes. |
| odfpy | loaded-temp-clean-manifest or not-installed | parser-comparison-evidence | S05/S06 | Do not choose odfpy alone until unmodified-load manifest failure is resolved or explicitly accepted as a controlled pre-processing requirement; if dependency-free verification records not-installed, rerun with `uv run --with odfpy --with odfdo`. | Probe issue `S05-optional-odfpy-loaded-temp-clean-manifest` or `S05-optional-odfpy-not-installed` remains owner/action/verifier-addressable. |
| odfdo | loaded-unmodified or not-installed | parser-comparison-evidence | S05/S06 | Investigate odfdo as the current parser direction when the transient-dependency run proves unmodified loading; if dependency-free verification records not-installed, treat parser selection as blocked for that environment until rerun with explicit transient dependencies. | Probe issue `S05-optional-odfdo-loaded-unmodified` or `S05-optional-odfdo-not-installed` remains present and verifier passes. |

The odfdo smoke summary reported `ordered_text_available=true`, `table_count_available=true`, `table_count=1`, `raw_ordered_block_count=5244`, and `raw_table_count=1`. It also recorded `forbidden_ordering_oracle=odfpy-getElementsByType(P/H)`, so downstream work should not infer legal ordering from odfpy element-type buckets.

## Manifest issue

`odfpy` failed the real unmodified-load phase because the ODT manifest contains an external `Manifest.dtd` reference. The controlled temp-copy mitigation removed only the manifest DOCTYPE and then loaded, with `source_mutated=false`; this proves a possible mitigation path but does not prove that odfpy can safely consume the original source directly.

Owner: S05/S06. Resolution path: either keep odfpy as comparison-only evidence, add a deliberate pre-processing step with tests and security review, or prefer a parser direction that loads the unmodified source. Verification criterion: any future parser claim must cite whether it uses unmodified-source loading or an explicitly tested manifest-cleaning boundary.

## Table-count reconciliation note

The raw baseline and odfdo both observed one table in the real ODT smoke run. This is a reconciliation signal only; it is not a final legal hierarchy count, citation-unit count, or SourceBlock extraction result. S07 must reject PRD wording that treats this smoke table count as production extraction proof.

## Old_project reuse classification

`Old_project/` remains prior art only. No legacy file is accepted as unchanged implementation because the older ConsultantPlus WordML/XML assumptions do not establish behavior for the current Garant ODT source.

| Candidate | Classification | Owner | Resolution path | Verification criterion |
|---|---|---|---|---|
| Old_project/structures/44fz.yaml | adapt/defer | S06/S08 | Reuse vocabulary cautiously only after mapping it to raw ODT evidence and current parser direction. | Later skill/architecture text cites S05 probe evidence and avoids claiming extracted hierarchy. |
| Old_project/parsing_prompt.yaml | adapt/defer | S06 | Reuse prompt ideas as human guidance only; do not let prompts create parser facts. | Skill updates preserve LLM non-authoritative language. |
| Old_project/validation/structural_rules.yaml | adapt/defer | S07/S08 | Convert useful rule concepts into future verifier requirements after real parser outputs exist. | PRD/architecture audits distinguish smoke evidence from production extraction. |
| Old_project/validation/semantic_rules.yaml | reject/defer | S07/S08 | Do not reuse semantic legal validation until authoritative source-grounded extraction exists. | Future acceptance tests require citation-backed evidence rather than legacy semantic assumptions. |
| Old_project/contracts/api.yaml | adapt/defer | S08 | Mine API-shape ideas only after parser findings and source-evidence boundaries are reflected in architecture docs. | Any API contract references EvidenceSpan/SourceBlock as future product work, not S05 output. |
| Old_project/contracts/extractor-api.md | adapt/defer | S08 | Reuse interface vocabulary only if it aligns with current parser-direction and evidence-boundary decisions. | Architecture guidance points to S05 and does not bless legacy extractor behavior. |
| Old_project/sources/consultant_word2003xml.yaml | reject/defer | S06/S07 | Treat as source-mismatch risk; do not map WordML/XML behavior onto Garant ODT without new proof. | Downstream docs explicitly separate ConsultantPlus XML assumptions from Garant ODT evidence. |

## Issues

| Issue ID | Owner | Resolution path | Verification criterion |
|---|---|---|---|
| S05-raw-odt-baseline | S05 | Preserve the generated raw source probe log and use raw `content.xml` traversal as the comparison oracle. | Verifier passes with `raw-baseline=verified-source-evidence`, real source path, source size, SHA-256, and issue ID. |
| S05-optional-odfpy-loaded-temp-clean-manifest | S05/S06 | Keep odfpy as controlled comparison evidence unless a future task explicitly implements and verifies manifest-cleaning as a parser boundary. | Verifier rejects ownerless issue rows and rejects accepting odfpy as the sole parser after unmodified-load failure. |
| S05-optional-odfpy-not-installed | S05/S06 | Treat dependency-free odfpy absence as blocked parser-comparison evidence; rerun with `uv run --with odfpy --with odfdo` before using odfpy status for parser selection. | Verifier passes only when the issue has owner, resolution path, and verification criterion. |
| S05-optional-odfdo-loaded-unmodified | S05/S06 | Carry odfdo forward as the current parser direction to investigate, while preserving raw ordering as oracle. | Verifier passes with an alternative parser status and issue row. |
| S05-optional-odfdo-not-installed | S05/S06 | Treat dependency-free odfdo absence as a blocked alternative parser comparison for that environment; rerun with explicit transient dependencies or record a replacement parser. | Verifier requires blocked alternative parser language and a resolution path when alternative status is `not-installed`. |

## Owners

S05 owns the generated smoke evidence and verifier contract. S06 owns skill updates that explain the parser direction and manifest-risk boundary. S07 owns PRD/source consistency checks that prevent overclaiming final hierarchy, table, or citation extraction. S08 owns final architecture consolidation and any future API wording derived from this evidence.

## Resolution paths

- Keep `prd/milestone_proofs/M001_S05_logs_odt-parser-probes.json` as the machine-readable status source for parser comparisons.
- Use odfdo as the current parser direction to investigate because it loaded the unmodified ODT in this smoke run.
- Keep odfpy in comparison evidence only unless future work explicitly verifies manifest-cleaning behavior and its safety boundary.
- Reclassify Old_project ideas only through current architecture and real-source verification; do not promote legacy WordML/XML assumptions into Garant ODT facts.

## Verification criteria

- `scripts/verify-s05-odt-parser.py` must pass against this findings file and `prd/milestone_proofs/M001_S05_logs_odt-parser-probes.json`.
- The probe log must include `raw-baseline`, `odfpy`, and an alternative parser status with non-empty issue IDs.
- Every parser issue and Old_project candidate must have owner, resolution path, and verification criterion fields.
- Findings must remain smoke/architecture evidence only and must not claim final legal hierarchy counts, final table extraction, production SourceBlock creation, or verified legal conclusions.

## S06/S07/S08 handoff notes

- S06: update Russian legal evidence/parser guidance to say the real ODT smoke run favors investigating odfdo while retaining raw `content.xml` as ordering oracle; preserve the odfpy manifest unmodified-load blocker.
- S07: audit PRD and milestone text for any claim that odfpy, old WordML/XML assumptions, table count, or marker counts prove product extraction.
- S08: consolidate parser direction as a bounded architecture recommendation, not final ETL implementation, and keep issue ownership traceable to the S05 JSON log.

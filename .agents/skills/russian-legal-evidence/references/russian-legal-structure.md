<reference>
<name>Russian legal structure and citation evidence vocabulary</name>

<purpose>
Provide durable terminology for Russian legal structure, citation units, EvidenceSpan, SourceBlock, citation-safe retrieval, temporal-first reasoning, and deterministic-first verification. These terms are modeling and answer-formatting vocabulary only; they are not extracted facts from the real `law-source/garant/44-fz.odt` until later parser/product extraction creates source-grounded records.
</purpose>

<evidence_anchors>
- S05 parser findings: `.gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md`.
- S05 parser probe log: `.gsd/milestones/M001/slices/S05/logs/odt-parser-probes.json`.
S05 verifies raw `content.xml` smoke observations and parser-comparison evidence; it does not verify final legal hierarchy, EvidenceSpan, SourceBlock, or product ETL output.
</evidence_anchors>

<core_terms>
- `LegalAct`: a legal document concept such as a federal law, decree, resolution, order, letter, or practice document. A model may use this label, but legal authority requires source-backed provenance.
- `ActEdition`: a time-scoped edition/version of a LegalAct. Temporal-first answers must name edition date or state that it is unknown.
- `LegalUnit`: a structural citation unit inside an act edition. Do not instantiate this from marker counts alone.
- `SourceBlock`: a parser-preserved source block, such as an ODT paragraph/table-derived block, with order, source path, and extraction metadata. S05 raw ordered blocks are not product SourceBlocks.
- `EvidenceSpan`: a bounded span linked to SourceBlock, LegalUnit, ActEdition, and SourceDocument for citation-safe retrieval. S05 does not create EvidenceSpan records.
- `TextChunk`: a retrieval representation that must remain linked back to legal units and evidence; it is not itself legal authority.
</core_terms>

<citation_unit_vocabulary>
Use English labels in durable skill artifacts, and preserve exact Russian labels in source-grounded answers when needed. The following examples are structural terms only, not claims that the real source contains a specific extracted instance:

| English model term | Russian term / citation label role | Example label pattern |
|---|---|---|
| law | федеральный закон / закон | `44-ФЗ` |
| article | статья | `ст. 31` |
| part | часть | `ч. 1` |
| clause | пункт | `п. 4` |
| subclause | подпункт | `подп. а` or similar source-specific form |
| paragraph | абзац / paragraph-like text unit | source-specific; verify before modeling as legal hierarchy |

Do not use this table as proof of a real hierarchy in `44-fz.odt`; later parser/product work must verify hierarchy levels, marker forms, ordering, tables, invalidity markers, and temporal markers from the actual source.
</citation_unit_vocabulary>

<raw_s05_observations>
S05 recorded smoke observations from raw `content.xml`, including ordered heading/paragraph block count, table count, and marker counts for terms such as закон, закупк, контракт, пункт, статья, and часть. These are raw observations only. They may support parser comparison, PRD overclaim detection, and future verifier design, but they must not be promoted into:
- legal units;
- citation units;
- SourceBlocks;
- EvidenceSpans;
- final extraction output;
- product ETL/import results;
- legal conclusions.

Use raw `content.xml` as the ordering oracle for parser comparison. Treat `odfdo` as the parser direction to investigate and `odfpy` as comparison evidence pending explicit manifest-cleaning design/review.
</raw_s05_observations>

<evidence_rules>
- Citation-safe retrieval means every answerable legal claim points to EvidenceSpan and SourceBlock, not only to a vector hit, raw marker count, parser smoke row, or LLM summary.
- LLM non-authoritative means an LLM cannot create legal facts, fill missing legal structure, or decide temporal validity without verified evidence.
- Deterministic-first means structure lookup, citation resolution, temporal filtering, evidence existence, and no-answer decisions should be algorithmic where possible.
- Temporal-first means edition date, validity interval, effective date, and status uncertainty must be explicit rather than inferred silently.
- If evidence is absent, return a no-answer or owner-routed gap instead of a confident legal conclusion.
</evidence_rules>

<claim_classes>
Use these claim classes for Russian legal evidence answers:
- `Verified from source`: direct current source/parser/smoke evidence supports the bounded claim, such as S05 raw ODT metadata or S10 runtime status.
- `Bounded by evidence`: PRD/S01/S05/S10/source text supports an architecture-level statement, but not runtime parser truth beyond the recorded boundary or product legal quality.
- `Hypothesis / pending verification`: the claim depends on future parser/product extraction, data refresh, legal-quality evaluation, or smoke evidence not yet produced.
- `Out of scope for M001`: the claim asks for product implementation, legal opinion, authoritative legal data, final ETL/import, or production retrieval quality beyond architecture review.
</claim_classes>

<common_traps>
- Do not treat PRD examples as extracted facts from `44-fz.odt`.
- Do not treat `Old_project/structures/44fz.yaml` counts or `validated: true` style claims as current proof.
- Do not let Russian legal vocabulary turn into legal authority without source citations.
- Do not collapse text paragraph, formal `Параграф`, clause, subclause, and source block into one field before real parser behavior is verified.
- Do not treat S05 marker/table counts as SourceBlock records, EvidenceSpan records, legal hierarchy counts, citation units, or final extraction output.
</common_traps>
</reference>

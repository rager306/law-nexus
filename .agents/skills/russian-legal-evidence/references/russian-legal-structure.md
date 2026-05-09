<reference>
<name>Russian legal structure and citation evidence vocabulary</name>

<purpose>
Provide durable terminology for Russian legal structure, citation units, EvidenceSpan, SourceBlock, citation-safe retrieval, temporal-first reasoning, and deterministic-first verification. These terms are modeling and answer-formatting vocabulary only; they are not extracted facts from the real `law-source/garant/44-fz.odt` until S05 proves parser behavior.
</purpose>

<core_terms>
- `LegalAct`: a legal document concept such as a federal law, decree, resolution, order, letter, or practice document. A model may use this label, but legal authority requires source-backed provenance.
- `ActEdition`: a time-scoped edition/version of a LegalAct. Temporal-first answers must name edition date or state that it is unknown.
- `LegalUnit`: a structural citation unit inside an act edition.
- `SourceBlock`: a parser-preserved source block, such as an ODT paragraph/table-derived block, with order, source path, and extraction metadata.
- `EvidenceSpan`: a bounded span linked to SourceBlock, LegalUnit, ActEdition, and SourceDocument for citation-safe retrieval.
- `TextChunk`: a retrieval representation that must remain linked back to legal units and evidence; it is not itself legal authority.
</core_terms>

<citation_unit_vocabulary>
Use English labels in durable skill artifacts, and preserve exact Russian labels in source-grounded answers when needed. The following examples are structural terms only, not claims that the real source contains a specific instance:

| English model term | Russian term / citation label role | Example label pattern |
|---|---|---|
| law | федеральный закон / закон | `44-ФЗ` |
| article | статья | `ст. 31` |
| part | часть | `ч. 1` |
| clause | пункт | `п. 4` |
| subclause | подпункт | `подп. а` or similar source-specific form |
| paragraph | абзац / paragraph-like text unit | source-specific; verify before modeling as legal hierarchy |

Do not use this table as proof of a real hierarchy in `44-fz.odt`; S05 must verify hierarchy levels, marker forms, ordering, tables, invalidity markers, and temporal markers from the actual source.
</citation_unit_vocabulary>

<evidence_rules>
- Citation-safe retrieval means every answerable legal claim points to EvidenceSpan and SourceBlock, not only to a vector hit or LLM summary.
- LLM non-authoritative means an LLM cannot create legal facts, fill missing legal structure, or decide temporal validity without verified evidence.
- Deterministic-first means structure lookup, citation resolution, temporal filtering, evidence existence, and no-answer decisions should be algorithmic where possible.
- Temporal-first means edition date, validity interval, effective date, and status uncertainty must be explicit rather than inferred silently.
- If evidence is absent, return a no-answer or owner-routed gap instead of a confident legal conclusion.
</evidence_rules>

<claim_classes>
Use these claim classes for Russian legal evidence answers:
- `Verified from source`: direct current source/parser/smoke evidence supports the bounded claim.
- `Bounded by evidence`: PRD/S01/source text supports an architecture-level statement, but not runtime parser truth.
- `Hypothesis / pending verification`: the claim depends on S05 parser proof, future data refresh, or smoke evidence.
- `Out of scope for M001`: the claim asks for product implementation, legal opinion, or authoritative legal data beyond architecture review.
</claim_classes>

<common_traps>
- Do not treat PRD examples as extracted facts from `44-fz.odt`.
- Do not treat `Old_project/structures/44fz.yaml` counts or `validated: true` style claims as current proof.
- Do not let Russian legal vocabulary turn into legal authority without source citations.
- Do not collapse text paragraph, formal `Параграф`, clause, subclause, and source block into one field before S05 verifies real ODT behavior.
</common_traps>
</reference>

---
name: russian-legal-evidence
description: Guides LegalGraph Nexus agents through Russian legal evidence, ODT parser assumptions, Old_project prior-art reuse checks, and citation-safe retrieval answer formatting while keeping LLM output non-authoritative and parser-sensitive claims bounded by verified S05 evidence.
---

<objective>
Use this focused skill when work touches Russian legal structure, EvidenceSpan, SourceBlock, citation-safe retrieval, `law-source/garant/44-fz.odt`, ODT parser assumptions, `Old_project/` prior art, temporal-first evidence, deterministic-first verification, or legal-answer formatting for LegalGraph Nexus.
</objective>

<scope>
This skill preserves M001 architecture-only and evidence boundaries. Parsing `44-fz.odt` into product legal facts, data import into FalkorDB, legal authority decisions, production citation extraction, and blessing old ConsultantPlus WordML/XML behavior remain outside this skill's implementation scope. S05 now provides bounded parser smoke evidence for raw ODT baseline, parser comparison, and Old_project classification; final PRD inconsistency reporting remains owned by S07/S08.
</scope>

<routing>
- For ODT parser assumptions, WordML-vs-ODT inconsistency, source-format mismatch, `44-fz.odt` smoke evidence, or requests to bless parser-sensitive claims: follow `workflows/review-odt-parser-assumption.md`.
- For Russian legal structure vocabulary, citation unit naming, EvidenceSpan/SourceBlock grounding, deterministic-first citation-safe retrieval, temporal-first evidence boundaries, or raw marker/table-count interpretation: read `references/russian-legal-structure.md`.
- For `Old_project/` reuse, legacy prompt reuse, stale ConsultantPlus XML assumptions, or prior-art classification: read `references/old-project-prior-art.md`.
- For future answer outputs, copy and fill `templates/evidence-answer.md` so every material claim has claim class, source path, confidence, downstream owner, and either EvidenceSpan/SourceBlock grounding or an explicit `pending later parser/product extraction` gap.
</routing>

<required_guardrails>
- LLM non-authoritative: an LLM may summarize verified evidence but must not create legal facts, parser facts, temporal facts, citation support, or extraction output.
- EvidenceSpan and SourceBlock are grounding concepts; do not claim they exist for the real Garant source until a later parser/product slice creates them from source evidence.
- S05 verifies bounded smoke facts about `law-source/garant/44-fz.odt`; it does not verify final legal hierarchy, citation units, SourceBlocks, EvidenceSpans, or product ETL.
- Raw `content.xml` is the ordering oracle for parser comparison. `odfdo` is the parser direction to investigate after unmodified-source loading evidence. `odfpy` is comparison evidence only unless an explicit manifest-cleaning design and review later accepts that boundary.
- `Old_project/` is prior art only. No legacy artifact is keep-as-is reusable for Garant ODT; classify candidates as adapt/defer/reject with owner, resolution, and verification status.
- Preserve exact Russian legal terms when needed, but keep durable skill content in English under the project durable-English policy.
</required_guardrails>

<evidence_anchors>
- Parser findings: `.gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md`.
- Parser probe log: `.gsd/milestones/M001/slices/S05/logs/odt-parser-probes.json`.
- Embedding runtime proof for answer-template boundaries: `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json`.
Use these as bounded evidence anchors, not as authorization to expand M001 beyond architecture-only guidance.
</evidence_anchors>

<failure_handling>
If S05 parser findings or `.gsd/milestones/M001/slices/S05/logs/odt-parser-probes.json` are missing, malformed, or lack owner/resolution/verification language, treat the gap as a verifier failure rather than filling assumptions. If an assumption is not covered by S05 evidence, classify it as bounded/pending with an explicit owner. If `Old_project/` files are missing or stale, use the S05/S01 classification summaries and treat legacy claims as prior-art risk, not authoritative design.
</failure_handling>

<s06_evidence_refresh>
Use `.gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md` and `.gsd/milestones/M001/slices/S05/logs/odt-parser-probes.json` as the bounded parser evidence anchors. They keep `odfdo`, `odfpy`, raw `content.xml`, marker counts, table count, and `Old_project` classifications visible with owner, resolution, and verification status. The current resolution is to investigate `odfdo`, keep raw `content.xml` ordering as oracle, keep `odfpy` as comparison/pending-manifest-cleaning evidence, and keep Old_project reuse as prior-art-only under the M001 architecture-only boundary.
</s06_evidence_refresh>

<success_criteria>
A correct use of this skill keeps Russian legal evidence citation-safe, distinguishes structural vocabulary from extracted facts, preserves temporal-first and deterministic-first boundaries, rejects unverified Old_project canonization, cites S05 for bounded parser evidence, routes PRD/source inconsistency reporting to S07/S08, and makes all uncertainty visible with downstream ownership.
</success_criteria>

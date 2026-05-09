---
name: russian-legal-evidence
description: Guides LegalGraph Nexus agents through Russian legal evidence, ODT parser assumptions, Old_project prior-art reuse checks, and citation-safe retrieval answer formatting while keeping LLM output non-authoritative and parser-sensitive claims owned by later proof slices.
---

<objective>
Use this focused skill when work touches Russian legal structure, EvidenceSpan, SourceBlock, citation-safe retrieval, `law-source/garant/44-fz.odt`, ODT parser assumptions, `Old_project/` prior art, temporal-first legal evidence, deterministic-first verification, or legal-answer formatting for LegalGraph Nexus.
</objective>

<scope>
This skill preserves M001 architecture-only and evidence boundaries. Parsing `44-fz.odt`, extracting legal facts, data import into FalkorDB, legal authority decisions, and blessing old ConsultantPlus WordML/XML behavior remain outside this skill's implementation scope. Real parser behavior proof is owned by S05, and final PRD inconsistency reporting is owned by S07/S08.
</scope>

<routing>
- For ODT parser assumptions, WordML-vs-ODT inconsistency, source-format mismatch, missing `44-fz.odt`, or requests to bless parser-sensitive claims: follow `workflows/review-odt-parser-assumption.md`.
- For Russian legal structure vocabulary, citation unit naming, EvidenceSpan/SourceBlock grounding, deterministic-first citation-safe retrieval, or temporal-first evidence boundaries: read `references/russian-legal-structure.md`.
- For `Old_project/` reuse, legacy prompt reuse, stale ConsultantPlus XML assumptions, or prior-art classification: read `references/old-project-prior-art.md`.
- For future answer outputs, copy and fill `templates/evidence-answer.md` so every material claim has claim class, source path, confidence, and downstream owner.
</routing>

<required_guardrails>
- LLM non-authoritative: an LLM may summarize verified evidence but must not create legal facts, parser facts, temporal facts, or citation support.
- EvidenceSpan and SourceBlock are grounding concepts; do not claim they exist for a real document until the parser creates them from source evidence.
- `44-fz.odt` is the current source-verification target, but this skill may only route verification to S05 and cannot assert extracted structure from it.
- `Old_project/` is prior art only. No legacy artifact is keep-as-is reusable without current architecture review and real evidence verification.
- Preserve exact Russian legal terms when needed, but keep durable skill content in English per D002.
</required_guardrails>

<failure_handling>
If `law-source/garant/44-fz.odt` is missing, inaccessible, malformed, or not yet smoke-tested, mark parser assumptions unverified and assign S05 as owner. If `Old_project/` files are missing or stale, use the S01 classification summary and treat legacy claims as prior-art risk, not authoritative design. If many legacy candidates are reviewed, require a compact table with candidate, posture, risk, owner, and verification instead of long copied excerpts.
</failure_handling>

<s06_evidence_refresh>
Use `.gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md` as the bounded parser evidence anchor. It keeps `odfdo`, `odfpy`, and raw `content.xml` evidence visible without naming any parser as sole or final. Keep `Old_project` reuse as prior-art-only and record each parser or reuse claim with owner, resolution, and verification status under the M001 architecture-only boundary.
</s06_evidence_refresh>

<success_criteria>
A correct use of this skill keeps Russian legal evidence citation-safe, distinguishes structural vocabulary from extracted facts, preserves temporal-first and deterministic-first boundaries, rejects unverified Old_project canonization, routes parser proof to S05, routes PRD/source inconsistency reporting to S07/S08, and makes all uncertainty visible with downstream ownership.
</success_criteria>

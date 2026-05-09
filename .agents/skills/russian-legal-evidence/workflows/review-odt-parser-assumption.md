<workflow>
<name>Review an ODT parser assumption</name>

<when_to_use>
Use this workflow when a task asks whether a parser behavior, legal-unit count, hierarchy level, source-format rule, WordML/XML extraction rule, raw marker/table count, SourceBlock/EvidenceSpan claim, or `44-fz.odt` claim can be accepted for LegalGraph Nexus.
</when_to_use>

<required_reading>
- `.gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md` for bounded S05 parser findings, Old_project classification, owner/resolution/verification rows, and S06/S07/S08 handoff notes.
- `.gsd/milestones/M001/slices/S05/logs/odt-parser-probes.json` for the machine-readable raw `content.xml`, `odfpy`, and `odfdo` probe statuses.
- `.gsd/milestones/M001/slices/S01/S01-RESEARCH.md` for earlier Old_project prior-art risks when S05 does not cover a candidate.
- `prd/03_PRD.md` for the PRD claim being assessed, especially the WordML XML extraction versus ODT requirements inconsistency.
- `references/old-project-prior-art.md` when legacy files are part of the assumption.
</required_reading>

<evidence_classes>
Use S05-specific classes before falling back to older pending labels:
- `verified-raw-ODT-baseline`: S05 direct evidence from the real `law-source/garant/44-fz.odt`, raw `content.xml`, package metadata, manifest facts, raw ordered block count, raw table count, or raw marker observations.
- `parser-comparison-evidence`: S05 bounded comparison evidence for `odfdo` loaded-unmodified / not-installed and `odfpy` loaded-temp-clean-manifest / not-installed. This class supports parser-direction discussion only.
- `bounded-prior-art`: S01/S05 or `Old_project/` suggests vocabulary, risks, or interface shapes but does not prove current Garant ODT behavior.
- `PRD-inconsistency-pending-S07/S08`: PRD wording conflicts or needs final report reconciliation, including WordML XML versus Garant ODT language.
- `pending-later-parser-product-extraction`: S05 did not create legal hierarchy, EvidenceSpan, SourceBlock, product ETL, or final extraction output; later parser/product work owns it.
- `out-of-scope-product-extraction`: the request asks this skill to parse, implement, legally validate, produce final legal hierarchy, or ship product ETL/import/API behavior.
- `hypothesis-pending-S05`: compatibility label for older S02 guidance; do not use it for facts already resolved by S05, but it may still describe assumptions absent from S05 evidence.
</evidence_classes>

<process>
1. Restate the assumption in one testable sentence. Separate source-format assumptions, legal hierarchy assumptions, parser behavior assumptions, raw observation assumptions, SourceBlock/EvidenceSpan assumptions, and legal fact assumptions.
2. Check S05 first. If the claim is covered by `.gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md` or `.gsd/milestones/M001/slices/S05/logs/odt-parser-probes.json`, classify it with the S05-specific evidence classes above and preserve owner, resolution path, and verification criterion language.
3. Use raw `content.xml` traversal as the ordering oracle for parser comparison. Do not infer legal ordering from `odfpy` element-type buckets.
4. Treat `odfdo` as the parser direction to investigate because S05 recorded unmodified-source loading when transient dependencies were present. If an environment only records `odfdo` as not-installed, require rerun with explicit transient dependencies before parser-selection claims.
5. Treat `odfpy` as comparison evidence pending explicit manifest-cleaning design/review. Do not describe odfpy as the sole, final, authoritative, or production parser after its unmodified-load manifest failure.
6. Check for the known WordML-vs-ODT inconsistency: PRD MVP text mentions WordML XML extraction while current requirements require ODT/Garant verification. Do not resolve the inconsistency by inventing compatibility; assign S07/S08 to report it and use S05 only for bounded parser evidence.
7. For `Old_project/` inputs, treat ConsultantPlus WordML/XML, MiniMax/DSPy/OpenAI, and legacy 44-ФЗ counts as prior-art risk unless current evidence proves relevance. No Old_project artifact is keep-as-is for Garant ODT.
8. Produce a compact claim table with assumption, evidence available, claim class, owner, and next verification. Avoid copying large source ODT or legacy prompt text.
</process>

<failure_modes>
- If S05 findings or the probe log are missing, unreadable, or malformed, output an explicit verifier failure or owner assignment instead of a synthetic parser claim.
- If an ODT parse errors or returns malformed data, treat the result as evidence for parser investigation, not as grounds to invent fallback behavior.
- If a request treats raw marker/table counts as legal units, citation units, SourceBlocks, or final extraction output, reject that promotion and classify the count as `verified-raw-ODT-baseline` smoke evidence only.
- If a request treats Old_project artifacts as canonical or keep-as-is, reject that premise and reclassify them as adapt/defer/reject prior art pending current verification.
- If PRD wording conflicts with S05 evidence, current requirements, or the ODT source direction, route the inconsistency to S07/S08 rather than silently normalizing it.
</failure_modes>

<output_format>
| Assumption | Evidence available | Claim class | Owner | Next verification |
|---|---|---|---|---|
| ... | S05 findings/probe log/PRD/S01/Old_project/none | verified-raw-ODT-baseline/parser-comparison-evidence/bounded-prior-art/PRD-inconsistency-pending-S07-S08/pending-later-parser-product-extraction/out-of-scope-product-extraction/hypothesis-pending-S05 | S05/S06/S07/S08/later/none | ... |

Add a short conclusion that says what can be used now, what remains bounded by S05 smoke evidence, what must wait for later parser/product extraction, and what must be reported in S07/S08.
</output_format>

<negative_tests>
- “The legacy WordML parser proves ODT behavior” must be rejected and routed to S05/S07/S08 as source-format mismatch evidence, not accepted as current proof.
- “44-fz.odt has 268 articles, so create LegalUnit records” must preserve the marker count as raw smoke evidence and reject promotion to LegalUnit/SourceBlock/product ETL claims.
- “odfpy loaded after manifest cleaning, so odfpy is the final parser” must fail; odfpy remains parser-comparison evidence pending explicit manifest-cleaning design/review.
- “The PRD says WordML, so implement WordML” must surface the ODT-vs-WordML inconsistency and route final reporting to S07/S08.
- “Old_project/structures/44fz.yaml can be reused unchanged” must fail because no legacy artifact is keep-as-is for Garant ODT.
</negative_tests>
</workflow>

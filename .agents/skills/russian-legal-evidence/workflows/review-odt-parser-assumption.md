<workflow>
<name>Review an ODT parser assumption</name>

<when_to_use>
Use this workflow when a task asks whether a parser behavior, legal-unit count, hierarchy level, source-format rule, WordML/XML extraction rule, or `44-fz.odt` claim can be accepted for LegalGraph Nexus.
</when_to_use>

<required_reading>
- `.gsd/milestones/M001/slices/S01/S01-RESEARCH.md` for Old_project prior-art classification and stale source-format risks.
- `.gsd/DECISIONS.md` for D007 real ODT verification target and D017 Old_project prior-art policy.
- `prd/03_PRD.md` for the PRD claim being assessed, especially the WordML XML extraction versus ODT requirements inconsistency.
- `references/old-project-prior-art.md` when legacy files are part of the assumption.
</required_reading>

<process>
1. Restate the assumption in one testable sentence. Separate source-format assumptions, legal hierarchy assumptions, parser behavior assumptions, and legal fact assumptions.
2. Classify the evidence currently available:
   - `verified-source-evidence`: direct current source/smoke proof exists from the real `law-source/garant/44-fz.odt`.
   - `bounded-prior-art`: S01 or `Old_project/` suggests a useful pattern but does not prove current behavior.
   - `hypothesis-pending-S05`: the assumption depends on real ODT parser proof.
   - `PRD-inconsistency-pending-S07/S08`: PRD wording conflicts or needs final report reconciliation.
   - `out-of-scope-for-S02`: the request asks this skill to parse, implement, or legally validate.
3. Check for the known WordML-vs-ODT inconsistency: PRD MVP text mentions WordML XML extraction while FR-1/FR-2 and D007 require ODT/Garant verification. Do not resolve the inconsistency by inventing compatibility; assign S07/S08 to report it and S05 to test actual parser behavior.
4. For `law-source/garant/44-fz.odt`, require S05 to verify real behavior before any parser-sensitive claim is blessed. This includes hierarchy counts, text block style handling, table behavior, citation-unit detection, invalidity markers, temporal markers, and EvidenceSpan/SourceBlock creation.
5. For `Old_project/` inputs, treat ConsultantPlus WordML/XML, MiniMax/DSPy/OpenAI, and legacy 44-ФЗ counts as prior-art risk unless current evidence proves relevance.
6. Produce a compact claim table with assumption, evidence available, claim class, owner, and next verification. Avoid copying large source ODT or legacy prompt text.
</process>

<failure_modes>
- If `law-source/garant/44-fz.odt` is unavailable or unreadable in S05, output an explicit blocker or owner assignment instead of a synthetic parser claim.
- If an ODT parse errors or returns malformed data, treat the result as evidence for S05 investigation, not as grounds to invent fallback behavior.
- If a request treats Old_project artifacts as canonical, reject that premise and reclassify them as prior art pending current verification.
- If the PRD wording conflicts with D007 or real source evidence, route the inconsistency to S07/S08 rather than silently normalizing it.
</failure_modes>

<output_format>
| Assumption | Evidence available | Claim class | Owner | Next verification |
|---|---|---|---|---|
| ... | PRD/S01/Old_project/current ODT smoke/none | verified-source-evidence/bounded-prior-art/hypothesis-pending-S05/PRD-inconsistency-pending-S07-S08/out-of-scope-for-S02 | S05/S07/S08/none | ... |

Add a short conclusion that says what can be used now, what must wait for S05, and what must be reported in S07/S08.
</output_format>

<negative_tests>
- “The legacy WordML parser proves ODT behavior” must be rejected and routed to S05.
- “44-fz.odt is missing, but assume the chapter/article counts from Old_project” must produce an explicit S05 owner/blocker, not synthetic proof.
- “The PRD says WordML, so implement WordML” must surface the ODT-vs-WordML inconsistency and route final reporting to S07/S08.
</negative_tests>
</workflow>

<reference>
<name>Old_project prior-art policy for LegalGraph Nexus</name>

<purpose>
Encode the S01 conservative reuse posture for `Old_project/`: legacy files are prior art only. They can suggest vocabulary, risks, contract shapes, and comparison checklists, but no artifact is keep-as-is reusable for current runtime behavior, parser truth, legal authority, or final architecture claims without current verification.
</purpose>

<policy>
- Treat `Old_project/` as legacy prior art, not a source of truth.
- No `Old_project/` artifact is currently classified as keep-as-is reusable.
- Use adapt/defer/reject until current architecture, real `law-source/garant/44-fz.odt` evidence, and relevant FalkorDB/ODT smoke checks verify relevance.
- ConsultantPlus WordML/XML extraction assumptions are incompatible with the current Garant ODT verification target until S05 proves an explicit bridge or replacement.
- LLM/provider assumptions such as MiniMax, DSPy, or OpenAI-compatible endpoints are not architecture evidence for M001.
</policy>

<reuse_postures>
| Posture | Meaning | Allowed use now | Owner |
|---|---|---|---|
| adapt | Concept is useful but must be rewritten for current evidence and architecture | vocabulary, risk checklist, interface shape | S02/S05/S08 depending on topic |
| defer | Candidate may help later but is too broad, stale, or unverified for M001 decisions | final caveat or future-scope note | S08 or later milestone |
| reject | Artifact should not influence current design beyond explaining why it was excluded | negative contrast only | S08 if report-worthy |
| keep-as-is | Not currently assigned to any legacy artifact | not allowed | none |
</reuse_postures>

<high_value_but_unverified>
- `Old_project/legislation_hierarchy.yaml`: useful legal taxonomy vocabulary; not legal authority.
- `Old_project/registers/letters.yaml`: useful for non-authoritative letter/clarification handling; normative-property judgments need evidence.
- `Old_project/structures/44fz.yaml`: useful comparison checklist for S05; counts, source format, and validation claims are untrusted.
- `Old_project/parsing_prompt.yaml`: useful lesson that parsing must be hierarchical/context-aware; provider and Consultant XML assumptions are stale.
- `Old_project/validation/*.yaml`: useful validation categories; terminology must be normalized against real ODT structure.
- `Old_project/contracts/*`: useful contract/error-taxonomy prior art; ODT support and current paths must be redesigned.
</high_value_but_unverified>

<known_risks>
- Stale index: `Old_project/index.yaml` claims a smaller inventory than actually existed in S01.
- Source-format drift: legacy materials focus on ConsultantPlus WordML/XML while M001 requires Garant `44-fz.odt` verification.
- Conflicting 44-ФЗ counts: legacy structure artifacts contain internally inconsistent article/chapter counts and validation claims.
- Stale hierarchy concepts: legacy prompt content includes hierarchy levels that later legacy notes may supersede.
- Hand-maintained registries: authority and act registries require refresh and provenance before data import.
- Empty memory artifacts: legacy `memory/*.yaml` demonstrate possible shapes but contain no reusable examples.
</known_risks>

<review_process>
When asked to reuse or evaluate a legacy candidate:
1. Name the exact candidate path and requested use.
2. Assign adapt/defer/reject/keep-as-is posture. Keep-as-is should be unavailable unless a later verified decision supersedes S01.
3. State the risk: source-format mismatch, stale data, provider assumption, legal-authority risk, or scope creep.
4. Assign owner: S05 for real ODT/parser verification, S07/S08 for PRD inconsistency or final prior-art reporting, later milestone for non-M001 expansion.
5. Use a compact table when reviewing many candidates: candidate, posture, risk, owner, verification.
</review_process>

<negative_tests>
- If a request says “Old_project is canonical,” answer that it is prior art only and require current verification.
- If files are missing, use the S01 classification summary rather than inventing the missing content.
- If a legacy prompt or WordML/XML rule conflicts with ODT direction, treat it as prior-art risk rather than authoritative parser design.
</negative_tests>
</reference>

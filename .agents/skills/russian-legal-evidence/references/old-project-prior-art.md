<reference>
<name>Old_project prior-art policy for LegalGraph Nexus</name>

<purpose>
Encode the S05/S01 conservative reuse posture for `Old_project/`: legacy files are prior art only. They can suggest vocabulary, risks, contract shapes, prompt lessons, and comparison checklists, but no artifact is keep-as-is reusable for current runtime behavior, parser truth, legal authority, or final architecture claims without current verification.
</purpose>

<evidence_anchors>
- Parser and reuse findings: `.gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md`.
- Machine-readable parser probe status: `.gsd/milestones/M001/slices/S05/logs/odt-parser-probes.json`.
Use these anchors for S05 classifications. If they are unavailable or malformed, preserve owner/resolution/verification gaps instead of inventing reuse approval.
</evidence_anchors>

<policy>
- Treat `Old_project/` as legacy prior art, not a source of truth.
- No `Old_project/` artifact is currently classified as keep-as-is reusable for Garant ODT.
- Use adapt/defer/reject until current architecture, real `law-source/garant/44-fz.odt` evidence, and relevant parser/FalkorDB smoke checks verify relevance.
- ConsultantPlus WordML/XML extraction assumptions are rejected or deferred for current Garant ODT unless a later task proves an explicit bridge or replacement.
- LLM/provider assumptions such as MiniMax, DSPy, OpenAI-compatible endpoints, or legacy prompt behavior are not architecture evidence for M001.
- Raw `content.xml` is the ordering oracle for parser comparison; `odfdo` is the parser direction to investigate; `odfpy` is comparison evidence pending explicit manifest-cleaning design/review.
</policy>

<reuse_postures>
| Posture | Meaning | Allowed use now | Owner |
|---|---|---|---|
| adapt | Concept is useful but must be rewritten for current evidence and architecture | vocabulary, risk checklist, interface shape, future verifier idea | S06/S07/S08 depending on topic |
| defer | Candidate may help later but is too broad, stale, source-mismatched, or unverified for M001 decisions | final caveat, issue, or future-scope note | S07/S08 or later milestone |
| reject | Artifact should not influence current design beyond explaining why it was excluded | negative contrast only | S07/S08 if report-worthy |
| keep-as-is | Not assigned to any legacy artifact for Garant ODT | not allowed | none |
</reuse_postures>

<s05_candidate_classification>
| Candidate | Current posture | Risk | Owner | Verification / resolution |
|---|---|---|---|---|
| `Old_project/structures/44fz.yaml` / `44fz.yaml` | adapt/defer | Conflicting or stale counts, source-format mismatch, untrusted validation claims | S06/S08 | Use as comparison checklist only after mapping to raw ODT evidence; never treat legacy counts as extracted hierarchy. |
| `Old_project/parsing_prompt.yaml` / `parsing_prompt.yaml` | adapt/defer | Prompt/provider assumptions and ConsultantPlus XML assumptions can create parser facts without evidence | S06 | Reuse only as human guidance that parsing must be hierarchical/context-aware; LLM remains non-authoritative. |
| `Old_project/validation/structural_rules.yaml` and related validation rules | adapt/defer | Rule terminology needs normalization against real ODT structure and later parser outputs | S07/S08 | Convert useful rule concepts into future verifier requirements after parser outputs exist. |
| `Old_project/validation/semantic_rules.yaml` and semantic validation rules | reject/defer | Semantic legal validation lacks authoritative source-grounded extraction | S07/S08 | Do not reuse until EvidenceSpan/SourceBlock-backed extraction exists. |
| `Old_project/contracts/api.yaml` and `Old_project/contracts/extractor-api.md` / contracts | adapt/defer | Contract paths and ODT support predate current evidence boundaries | S08 | Mine interface vocabulary only after parser findings and source-evidence boundaries are reflected in architecture docs. |
| `Old_project/sources/consultant_word2003xml.yaml` and ConsultantPlus WordML/XML assumptions | reject/defer | Source-format mismatch with Garant `44-fz.odt` | S06/S07 | Do not map WordML/XML behavior onto Garant ODT without new proof. |
</s05_candidate_classification>

<high_value_but_unverified>
- `Old_project/legislation_hierarchy.yaml`: useful legal taxonomy vocabulary; not legal authority.
- `Old_project/registers/letters.yaml`: useful for non-authoritative letter/clarification handling; normative-property judgments need evidence.
- `Old_project/structures/44fz.yaml`: useful comparison checklist for S05/S08; counts, source format, and validation claims are untrusted.
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
2. Assign adapt/defer/reject/keep-as-is posture. Keep-as-is is unavailable for Garant ODT unless a later verified decision supersedes S05/S01.
3. State the risk: source-format mismatch, stale data, provider assumption, legal-authority risk, parser-comparison gap, or scope creep.
4. Assign owner: S05/S06 for parser evidence interpretation, S07/S08 for PRD inconsistency or final prior-art reporting, later milestone for non-M001 expansion.
5. Preserve owner, resolution, and verification criteria from `.gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md` when available.
6. Use a compact table when reviewing many candidates: candidate, posture, risk, owner, verification.
</review_process>

<negative_tests>
- If a request says “Old_project is canonical,” answer that it is prior art only and require current verification.
- If a request asks to keep a legacy artifact as-is for Garant ODT, reject or defer it; no legacy artifact has keep-as-is status.
- If files are missing, use the S05/S01 classification summaries rather than inventing the missing content.
- If a legacy prompt or WordML/XML rule conflicts with ODT direction, treat it as prior-art risk rather than authoritative parser design.
</negative_tests>
</reference>

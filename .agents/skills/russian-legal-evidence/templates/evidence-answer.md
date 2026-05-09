<template>
<name>Evidence answer template</name>

<usage>
Copy and fill this template when answering future Russian legal evidence, ODT parser, embedding-runtime, citation-safe retrieval, or Old_project prior-art questions. Keep every material claim tied to a claim class, source path, confidence, downstream owner, and grounding status. Do not paste large source ODT, embedding arrays, credentials, managed API secret names, or legacy prompt text.
</usage>

<allowed_evidence>
Allowed bounded evidence anchors include:
- S05 parser findings: `.gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md`.
- S05 machine-readable probe log: `.gsd/milestones/M001/slices/S05/logs/odt-parser-probes.json`.
- S10 embedding runtime proof: `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json`.
S05 verified-source evidence can support raw `content.xml` metadata, raw ordering oracle status, parser-comparison evidence for `odfdo` and `odfpy`, and Old_project adapt/defer/reject classifications. S10 runtime evidence can support bounded local embedding runtime status. Neither S05 nor S10 creates citation-safe legal answers by itself.
</allowed_evidence>

<body>
Question: ...

Scope boundary:
- M001 architecture-only / S05 verified-source smoke evidence / pending later parser/product extraction / PRD reporting pending S07/S08 / S10 embedding runtime evidence / other: ...

Evidence summary:
| Evidence item | Source path | EvidenceSpan | SourceBlock | What it supports | Confidence |
|---|---|---|---|---|---|
| ... | `path` | `id` / `pending later parser/product extraction` | `id` / `pending later parser/product extraction` | ... | high/medium/low/pending |

Claim classification:
| Claim | Claim class | Source path | Confidence | Downstream owner | Notes |
|---|---|---|---|---|---|
| ... | Verified from source / Bounded by evidence / Hypothesis / pending verification / Out of scope for M001 | `path` | high/medium/low/pending | S05/S06/S07/S08/later/none | ... |

Answer:
- Use only the classified claims above.
- Preserve exact Russian legal terms where needed.
- State no-answer or evidence gap when EvidenceSpan/SourceBlock support is missing.
- Keep LLM non-authoritative; do not create legal facts, temporal facts, parser facts, or citation support.
- If relying on S05 raw `content.xml`, marker/table counts, `odfdo`, or `odfpy`, state the bounded parser-evidence class and avoid product extraction claims.
- If relying on S10 embedding runtime evidence, state runtime status only and avoid production legal retrieval quality claims.

Open gaps and owners:
| Gap | Owner | Verification expected |
|---|---|---|
| ... | S05/S06/S07/S08/later | ... |
</body>

<required_fields>
Every filled answer must include `EvidenceSpan`, `SourceBlock`, Claim class, source path, confidence, and downstream owner. If EvidenceSpan or SourceBlock does not yet exist, write `pending later parser/product extraction` instead of inventing an identifier. For citation-safe legal answers, material legal claims require real EvidenceSpan/SourceBlock grounding; otherwise return a no-answer, bounded evidence summary, or owner-routed gap.
</required_fields>

<negative_tests>
- Do not answer a legal question from raw marker counts, table counts, vector hits, or LLM summaries without EvidenceSpan/SourceBlock grounding.
- Do not cite S05 raw observations as final LegalUnit, SourceBlock, EvidenceSpan, or product ETL output.
- Do not cite S10 local embedding runtime proof as production Russian legal retrieval quality.
- Do not promote `odfpy` to the sole/final parser; it remains comparison evidence pending explicit manifest-cleaning design/review.
</negative_tests>
</template>

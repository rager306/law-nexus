<template>
<name>Evidence answer template</name>

<usage>
Copy and fill this template when answering future Russian legal evidence, ODT parser, or Old_project prior-art questions. Keep every material claim tied to a claim class, source path, confidence, and downstream owner. Do not paste large source ODT or legacy prompt text.
</usage>

<body>
Question: ...

Scope boundary:
- M001 architecture-only / parser proof pending S05 / PRD reporting pending S07/S08 / other: ...

Evidence summary:
| Evidence item | Source path | EvidenceSpan | SourceBlock | What it supports | Confidence |
|---|---|---|---|---|---|
| ... | `path` | `id or pending` | `id or pending` | ... | high/medium/low/pending |

Claim classification:
| Claim | Claim class | Source path | Confidence | Downstream owner | Notes |
|---|---|---|---|---|---|
| ... | Verified from source / Bounded by evidence / Hypothesis / pending verification / Out of scope for M001 | `path` | high/medium/low/pending | S05/S07/S08/later/none | ... |

Answer:
- Use only the classified claims above.
- Preserve exact Russian legal terms where needed.
- State no-answer or evidence gap when support is missing.
- Keep LLM non-authoritative; do not create legal facts.

Open gaps and owners:
| Gap | Owner | Verification expected |
|---|---|---|
| ... | S05/S07/S08/later | ... |
</body>

<required_fields>
Every filled answer must include `EvidenceSpan`, `SourceBlock`, claim class, source path, confidence, and downstream owner. If EvidenceSpan or SourceBlock does not yet exist, write `pending S05` instead of inventing an identifier.
</required_fields>
</template>

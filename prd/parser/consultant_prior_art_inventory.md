# Consultant prior-art inventory

This maintained report catalogs the reusable law-parser prior-art assets inspected for M009/S01/T02. It is an audit surface, not parser output.

## Status

- Status: `pass`
- Asset count: `28`
- Classification counts: `{'keep': 1, 'adapt': 13, 'defer': 13, 'reject': 1}`
- Missing prior-art files: `0`
- Hash drift paths: `0`
- Source fixture anchor: `prd/parser/source_fixture_inventory.json` / `law-source/consultant/44-FZ-2026.xml`

## Reuse boundaries

- Consultant Plus WordML is primary for M009 full normative-act source-shape evidence.
- Consultant WordML prior art is reusable only as source-shape, taxonomy, prompt, or rule hypothesis evidence.
- Garant ODT work is lower-priority/deferred from M009; prior ODT artifacts remain bounded evidence, not multi-source readiness.
- law-parser derived JSON/JSONL outputs are not imported as authoritative parsed legal data.

## Blocked claims

- This inventory does not claim parser completeness.
- This inventory does not claim legal correctness.
- This inventory does not claim Consultant WordML legal authority.
- This inventory does not claim product ETL readiness.
- This inventory does not claim FalkorDB loading/runtime readiness.
- This inventory does not claim citation-safe retrieval readiness.
- This inventory does not claim multi-source parser readiness.

## Asset catalog

| ID | Classification | Type | Path | SHA-256 | Boundary |
|---|---|---|---|---|---|
| `CPA-001` | `keep` | `full-fixture` | `law-source/consultant/44-FZ-2026.xml` | `69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86` | Keep as the canonical tracked Consultant Plus WordML source-shape fixture and hash anchor only; do not treat as parsed legal semantics or multi-source readiness. |
| `CPA-002` | `adapt` | `structure-json` | `/root/law-parser/doc_domain_44fz/cons/44-FZ/44-FZ-2026-structure.json` | `da41e6c23f4449da39c79548c0b270d2747d7a50852f796b980c4b38742dbc5a` | Adapt field ideas and structural examples only after re-deriving from canonical fixtures; do not import as authoritative parsed output. |
| `CPA-003` | `adapt` | `articles-jsonl` | `/root/law-parser/doc_domain_44fz/cons/44-FZ/44-FZ-2026-articles.jsonl` | `de03cda6b266085a9b1f2376afcb9dffbb00fec922dee1f1553cadcfb6d03869` | Adapt record-shape ideas and count expectations only; do not copy article text or assert article parsing correctness from this prior-art output. |
| `CPA-004` | `adapt` | `source-format-yaml` | `/root/law-parser/prompt_domain_44fz/sources/consultant_word2003xml.yaml` | `a09d953eca7219ec38bc435e3376901ea48ee1b31f844dbd234ee2f8d666e89a` | Adapt source-format observations for Consultant WordML diagnostics; do not mix them into deferred/lower-priority Garant ODT assumptions. |
| `CPA-005` | `adapt` | `structure-yaml` | `/root/law-parser/prompt_domain_44fz/structures/44fz.yaml` | `94c0be4d64c0fd44e369dea852bd397490cfc06c7ee5e672fa875f88136cd507` | Adapt hierarchy vocabulary and validation hypotheses only after testing against canonical fixtures. |
| `CPA-006` | `adapt` | `parsing-prompt-yaml` | `/root/law-parser/prompt_domain_44fz/parsing_prompt.yaml` | `5324c64554e4fb5eb8c0bb04231b6a6c46b8cdf1e255db01746daa801758d99f` | Adapt prompt taxonomy as documentation/prior art only; LLM output remains non-authoritative and cannot replace deterministic parser evidence. |
| `CPA-007` | `adapt` | `structural-rules-yaml` | `/root/law-parser/prompt_domain_44fz/validation/structural_rules.yaml` | `a38b25b7dfb7523b86e6a9042f4bed14f9fa1d13b5b82d5e22b55d218a8d8a37` | Adapt structural rule candidates into deterministic tests before relying on them. |
| `CPA-008` | `defer` | `semantic-rules-yaml` | `/root/law-parser/prompt_domain_44fz/validation/semantic_rules.yaml` | `c53121270fe4e1436bc28879dc6b465b0ea71f29cda90d96beb50d637d62714c` | Defer semantic rules until deterministic parser records and citation-safe evidence can support them. |
| `CPA-009` | `defer` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/archive/parsing_prompt_1.0.0_20251231_1425.yaml` | `2599fb084641e15e25e3e7e0852ab1bdcd081ea8c0198934704974eb70afadff` | Archived prompt/spec history; retain hash for provenance but do not reuse without a later migration decision. |
| `CPA-010` | `defer` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/archive/yaml_prompt_20251231_1230.yaml` | `e3bbb69550afa84de34e0099e9147eb2ba3c8ef45708b16d10331801e742bb40` | Archived prompt/spec history; retain hash for provenance but do not reuse without a later migration decision. |
| `CPA-011` | `adapt` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/contracts/api.yaml` | `db39ac7dbd0e77c6630cb84676159799fbbe96d2a9b3a7f39017739c699fe6c6` | Supporting taxonomy/config prior art; adapt selectively only after deterministic validation in law-nexus. |
| `CPA-012` | `adapt` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/federal_authorities.yaml` | `0107bc09056b8558cefb753c1f45cd71df202801ff8f5c07a269b4a5a0270c29` | Supporting taxonomy/config prior art; adapt selectively only after deterministic validation in law-nexus. |
| `CPA-013` | `adapt` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/federal_control_authorities.yaml` | `6c2dccf3297a3cb89ab9fa55c0288e27e66651f303aba8f018d6cf85c8a73946` | Supporting taxonomy/config prior art; adapt selectively only after deterministic validation in law-nexus. |
| `CPA-014` | `adapt` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/index.yaml` | `07c417903309d7d0430a94cf40b3f9bb229828bcbd7f9b71556bf7adbe548bdb` | Supporting taxonomy/config prior art; adapt selectively only after deterministic validation in law-nexus. |
| `CPA-015` | `adapt` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/legislation_hierarchy.yaml` | `72a06a19eaa28a4c8d84af1b64770eb98d94c618c94e77c66ba05c08fb181247` | Supporting taxonomy/config prior art; adapt selectively only after deterministic validation in law-nexus. |
| `CPA-016` | `reject` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/memory/failed_experiments.yaml` | `a5731a416c26eb5447b2819e5fa2430df0e47cdee4f36cee9f972a2971d77ed0` | Rejected as an implementation path; keep only as a warning that this prior-art approach previously failed. |
| `CPA-017` | `defer` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/memory/learned_examples.yaml` | `9b1b48a316b03211d0febca78541b9c4d62875278c9cce25d6dbeac727830b63` | Memory note; defer until a future parser design can verify the pattern independently. |
| `CPA-018` | `defer` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/memory/successful_patterns.yaml` | `68ab3f224351f126cd09bcdeeb39ae78cd7f9a2bd6a26ca29c78d9d9ff16962b` | Memory note; defer until a future parser design can verify the pattern independently. |
| `CPA-019` | `adapt` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/registers/federal_acts.yaml` | `1a6cc86501e40292904fd10bc4119da8b7c3d184588f36a4b9840ef1d338bef9` | Supporting taxonomy/config prior art; adapt selectively only after deterministic validation in law-nexus. |
| `CPA-020` | `adapt` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/registers/letters.yaml` | `307ba817c651786900d2c36671ed4a25192646355c9730965a1e65cf9544092c` | Supporting taxonomy/config prior art; adapt selectively only after deterministic validation in law-nexus. |
| `CPA-021` | `defer` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/structures/archive/44fz_1.1.0_20251231_1407.yaml` | `52e8232ce5fc5a174063fee1172c29c2346e2d6225834a326dea1590cc240fc3` | Archived prompt/spec history; retain hash for provenance but do not reuse without a later migration decision. |
| `CPA-022` | `defer` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/structures/archive/44fz_2.0.0_20251231_1436.yaml` | `bcc3251c302fd6ae4d70c4e5df9255b53f184618afb08249d7475220b18cfc8e` | Archived prompt/spec history; retain hash for provenance but do not reuse without a later migration decision. |
| `CPA-023` | `defer` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/structures/archive/44fz_2.2.0_20260101_0029.yaml` | `898325dc9199a839fd67db79e47d6351e47894030a9dfebdea09ecb9965a2ac3` | Archived prompt/spec history; retain hash for provenance but do not reuse without a later migration decision. |
| `CPA-024` | `defer` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/structures/archive/44fz_2.2.0_20260101_1448.yaml` | `898325dc9199a839fd67db79e47d6351e47894030a9dfebdea09ecb9965a2ac3` | Archived prompt/spec history; retain hash for provenance but do not reuse without a later migration decision. |
| `CPA-025` | `defer` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/structures/archive/44fz_20251231_1200.yaml` | `3113929039ca3e83e5a0c1ac4d59288a135ac1f35e6a0f19d70b3437896fe8e7` | Archived prompt/spec history; retain hash for provenance but do not reuse without a later migration decision. |
| `CPA-026` | `defer` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/structures/archive/44fz_20251231_1340.yaml` | `3113929039ca3e83e5a0c1ac4d59288a135ac1f35e6a0f19d70b3437896fe8e7` | Archived prompt/spec history; retain hash for provenance but do not reuse without a later migration decision. |
| `CPA-027` | `defer` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/structures/archive/44fz_20251231_1341.yaml` | `f2b17542f3ff28d4bc3ea59f6ba555175003b75fb84b95e29f09974783d3bbf3` | Archived prompt/spec history; retain hash for provenance but do not reuse without a later migration decision. |
| `CPA-028` | `defer` | `supporting-yaml` | `/root/law-parser/prompt_domain_44fz/structures/archive/44fz_20260101_1918.yaml` | `de237fc1dc3c9dd2cedc3028b8ea3b56f1c08ee60f4a210d1eafd7976ef40932` | Archived prompt/spec history; retain hash for provenance but do not reuse without a later migration decision. |

## Diagnostics

- `missing_prior_art_files`: `[]`
- `hash_drift_paths`: `[]`
- `classification_count_total`: `28`

No raw full legal text is embedded in this report; it records paths, hashes, bounded shape/count metadata, classifications, and non-claims only.

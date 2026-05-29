---
id: EA-ACP-0001
record_kind: evidence_anchor
title: ACP source-record and lifecycle model evidence
status: active
anchor_kind: tracked-prd-contract
repo_relative_path: prd/architecture/acp/M048-S02-SOURCE-RECORD-MODEL.md
section_or_line_hint: ACP Core Record Categories
secondary_repo_relative_paths:
  - prd/architecture/acp/M048-S03-LIFECYCLE-HEALTH-MODEL.md
evidence_role: source-record-model-contract
claim_scope: ACP governance mechanics only
durability: tracked-source-artifact
safety_classification: safe-repository-relative-source
allowed_acp_use:
  - source model reference
  - lifecycle model reference
  - proof checklist reference
blocked_acp_use:
  - product validation
  - legal correctness proof
  - domain completeness proof
  - falkordb runtime proof
  - independent review satisfaction
safety:
  contains_secrets: false
  contains_provider_payloads: false
  contains_raw_vectors: false
  contains_unnecessary_raw_legal_text: false
  contains_local_absolute_paths: false
  claims_product_readiness: false
  claims_parser_completeness: false
  claims_falkordb_ingestion: false
  claims_legal_correctness: false
  claims_r035_validated: false
  claims_r037_validated: false
  claims_r038_validated: false
---

# EA-ACP-0001 — ACP source-record and lifecycle model evidence

This anchor points only to durable repository-relative source artifacts. It does not cite transient logs, ignored files, absolute paths, provider payloads, vectors, secrets, or raw legal text.

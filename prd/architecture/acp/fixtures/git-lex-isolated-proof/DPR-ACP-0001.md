---
id: DPR-ACP-0001
record_kind: derived_projection_reference
title: Example non-authoritative ACP recovery projection
status: registered
projection_kind: recovery-json
repo_relative_path: prd/architecture/acp/derived/git-lex-isolated-proof-recovery.json
derived_from:
  - APR-ACP-0001
  - AP-ACP-0001
  - DC-ACP-0001
  - PG-ACP-0001
freshness_status: not-generated-fixture-reference-only
authority_status: non_authoritative
allowed_acp_use:
  - diagnose extraction shape
  - support query/recovery smoke checks
  - guide regeneration from source records
blocked_acp_use:
  - serve as sole source anchor
  - validate requirements
  - override source records
  - become canonical architecture rows by copying
source_refs:
  - id: EA-ACP-0001
    role: projection-boundary
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

# DPR-ACP-0001 — Example non-authoritative ACP recovery projection

This record references a possible derived output path for extraction/query/recovery mechanics. It is explicitly non-authoritative and cannot override source records.

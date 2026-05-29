---
id: RB-ACP-0001
record_kind: requirement_binding
title: Bind ACP isolated proof to M048 mechanics requirement context
status: active
requirement_id: R040
requirement_status: not-validated-by-this-fixture
source_ref: EA-ACP-0001
binding_scope: ACP governance mechanics fixture only
allowed_acp_use:
  - expose required proof gates
  - link blocked validation paths
  - show downstream lifecycle status
blocked_acp_use:
  - change requirement status
  - validate requirements from projection evidence alone
  - infer active requirements from stale project-state outputs
proof_gates:
  - PG-ACP-0001
profile_constraints:
  - PC-LN-0001
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

# RB-ACP-0001 — Bind ACP isolated proof to M048 mechanics requirement context

This binding exposes ACP mechanics context only. It cannot update requirement status or validate requirements from fixture or projection evidence.

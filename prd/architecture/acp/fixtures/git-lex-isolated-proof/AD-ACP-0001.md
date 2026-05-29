---
id: AD-ACP-0001
record_kind: architecture_decision
title: Keep S04 fixture proof isolated and non-adoptive
status: requires_proof
decision: ACP git-lex mechanics may be represented as isolated source fixtures, but main-repo git-lex adoption remains blocked.
rationale: The project needs deterministic mechanics evidence without confusing source records, derived projections, and runtime adoption readiness.
accepted_by_or_source: prd/architecture/acp/M048-S03-LIFECYCLE-HEALTH-MODEL.md#s04-isolated-git-lex-mechanic-checklist
date: '2026-05-27'
source_ref: EA-ACP-0001
proof_gates:
  - PG-ACP-0001
supersedes: []
non_claims:
  - product-readiness
  - parser-completeness
  - falkordb-ingestion
  - legal-correctness
  - independent-review-satisfaction
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

# AD-ACP-0001 — Keep S04 fixture proof isolated and non-adoptive

This decision record captures the fixture boundary only. Accepted doctrine and proof satisfaction remain separate states.

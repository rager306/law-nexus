---
id: AHF-ACP-0001
record_kind: architecture_health_finding
title: Main-repo git-lex adoption remains blocked
status: blocked
severity: critical
finding_type: blocked_adoption
surface: git-lex main-repo state
description: The isolated fixture can exercise ACP mechanics, but main-repo git-lex adoption and .lex state creation remain blocked until separate proof and adoption authority exist.
blocked_actions:
  - BA-ACP-0001
allowed_next_actions:
  - Run deterministic fixture validation.
  - Extract non-authoritative derived projection references from source records.
  - Reassess adoption only after proof and a separate accepted decision.
recommended_fix: Keep proof fixtures source-controlled and isolated; do not run git lex init or create .lex in the main repository.
source_refs:
  - id: EA-ACP-0001
    role: lifecycle-checklist
related_proof_gates:
  - PG-ACP-0001
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

# AHF-ACP-0001 — Main-repo git-lex adoption remains blocked

This finding makes the unsafe adoption path visible and machine-checkable.

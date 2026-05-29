---
id: BA-ACP-0001
record_kind: blocked_action
title: Do not initialize git-lex in main repository
status: active
action: Run git lex init or create .lex state in the main repository.
surface: main-repo-git-lex-state
severity: critical
reason: Isolated fixture proof is not adoption authority and does not prove runtime compatibility or project readiness.
blocked_until: Separate isolated proof evidence and a later accepted adoption decision exist.
required_unblock_evidence:
  - PG-ACP-0001 satisfied by durable tracked evidence.
  - A separate architecture decision explicitly accepts main-repo git-lex adoption.
proof_gates:
  - PG-ACP-0001
source_refs:
  - id: EA-ACP-0001
    role: blocked-action-contract
related_findings:
  - AHF-ACP-0001
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

# BA-ACP-0001 — Do not initialize git-lex in main repository

The blocked action keeps the fixture pack isolated from main-repo adoption state.

---
id: DC-ACP-0001
record_kind: decision_candidate
title: Require isolated fixture proof before git-lex adoption
status: requires_proof
origin_prompt_record: APR-ACP-0001
origin_proposal: AP-ACP-0001
cluster: acp-git-lex-mechanics
significance:
  - adoption-boundary
  - proof-burden
  - source-projection-separation
alternatives:
  - Initialize git-lex in the main repository immediately.
  - Keep git-lex as research only.
  - First validate an isolated ACP fixture pack and defer main-repo adoption.
consequences:
  - Main-repo git-lex adoption remains blocked until proof and a later accepted decision exist.
  - The fixture can demonstrate mechanics without changing product authority.
conflicts:
  - BA-ACP-0001
required_proof_gates:
  - PG-ACP-0001
authority_required: true
source_refs:
  - id: EA-ACP-0001
    role: proposal-source
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

# DC-ACP-0001 — Require isolated fixture proof before git-lex adoption

This candidate is non-authoritative. It requires proof and later acceptance before it can become architecture doctrine.

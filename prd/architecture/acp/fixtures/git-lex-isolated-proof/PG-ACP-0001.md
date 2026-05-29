---
id: PG-ACP-0001
record_kind: proof_gate
title: Isolated ACP git-lex fixture mechanics gate
status: pending_evidence
claim_or_requirement: Isolated fixtures cover ACP typed records, validation, extraction/projection, query/recovery, lifecycle/proof-gate, source/projection boundary, and blocked-action mechanics.
required_evidence:
  - deterministic pytest validation of fixture shape and links
  - explicit source-versus-derived authority assertions
  - explicit main-repo mutation and .lex absence checks
verification_commands:
  - uv run pytest tests/test_m048_s04_git_lex_isolated_fixtures.py
acceptance_criteria:
  - all required record kinds are present exactly once
  - relationship references resolve to fixture records or durable repository-relative source artifacts
  - derived projections are non-authoritative
  - profile-specific constraints appear only in ProfileConstraint records
  - blocked actions prevent main-repo git-lex adoption and .lex creation
  - requirement validation is not claimed by fixture or projection proof
evidence_anchors:
  - EA-ACP-0001
blocked_claims:
  - git-lex adoption readiness
  - product runtime readiness
  - domain runtime validation
  - external review validation
blocks:
  - DC-ACP-0001
  - BA-ACP-0001
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

# PG-ACP-0001 — Isolated ACP git-lex fixture mechanics gate

The gate definition is not proof by itself. It remains pending until deterministic tests produce evidence from source-controlled fixtures.

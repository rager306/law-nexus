---
id: AP-ACP-0001
record_kind: architecture_proposal
title: Build isolated ACP typed-record fixture pack
status: candidate_extracted
scope: Model reusable ACP records as source-controlled git-lex-style Markdown/frontmatter files without initializing git-lex.
non_goals:
  - Do not create .lex state.
  - Do not run git lex init in the main repository.
  - Do not validate product, domain-specific runtime, parser, or review readiness.
dependencies:
  - APR-ACP-0001
interfaces:
  - Markdown frontmatter source records
  - deterministic pytest fixture validation
nfrs:
  - repository-relative durable anchors only
  - deterministic offline inspection
  - profile-specific constraints remain outside reusable core fields
data_or_state_impacts:
  - Adds tracked fixture source records only.
  - Adds no runtime telemetry and no git-lex state.
operational_impacts:
  - Future extraction, projection, query, and recovery checks can consume the records.
risks:
  - Mistaking derived projection references for source authority.
  - Letting profile-specific proof boundaries leak into reusable core record definitions.
validation_plan: Validate record identity uniqueness, typed coverage, relationship references, lifecycle and proof-gate chain coverage, source/projection authority separation, profile boundary fields, blocked actions, and non-claim flags.
origin_prompt_record: APR-ACP-0001
decision_candidates:
  - DC-ACP-0001
source_refs:
  - id: EA-ACP-0001
    role: source-record-model
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

# AP-ACP-0001 — Build isolated ACP typed-record fixture pack

This proposal defines an isolated source-record proof fixture. It can produce candidates and proof gates, but it cannot itself become accepted doctrine or satisfy a proof gate.

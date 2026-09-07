# NPA control artifact verification

Status: `[proposed]` verification assessment; non-authoritative.

## Scope and authority

This assessment verifies the machine-readable control contracts introduced for
Review Case `RC-2026-09-05-001`. It does not execute the corpus, parse legal
text, create product facts, promote parser readiness, or validate R035/R070.
It is not legal gold and cannot establish legal truth.
The only full-corpus authority named by these artifacts is
`consru_export/consru_export/exports`; `law-source/consultant/` and
`law-source/garant/` are explicitly non-authoritative for this contract.

## Artifact inventory

| Artifact | Schema | Role | Lifecycle |
|---|---|---|---|
| `prd/architecture/npa-corpus-control.yaml` | `law-nexus-npa-corpus-control/v1` | C0-C5 strata, manifest admission, source boundary | `[proposed]` |
| `prd/architecture/npa-metric-baselines.yaml` | `law-nexus-npa-metric-baselines/v1` | measurement binding, exact/estimate/proxy semantics, provisional thresholds | `[proposed]` |
| `prd/architecture/npa-control-ledgers.yaml` | `law-nexus-npa-control-ledgers/v1` | append-only metric, regression, gap and semantic-correction records | `[proposed]` |

## Verification contract

The tracked tests load YAML as data and assert:

1. all six strata C0 fixtures, C1 hostile, C2 bounded, C3 holdout, C4 full
diagnostic and C5 double-coded gold exist with explicit lifecycle and admission;
2. full corpus authority is exact and raw text persistence is forbidden;
3. manifest entries require parser revision, corpus snapshot hash, provider
strata, non-secret environment and source-safe `source_span` evidence anchors;
4. every metric classification is `exact`, `estimate`, or `proxy`, and proxy
measurements cannot be treated as semantic frames;
5. zero-tolerance semantic/accounting counters and rollback criteria are
present, while numeric operational bounds remain `deferred-undefined`;
6. each ledger has a schema, required payload, stable code policy where
applicable, and shared append-only envelope requirements;
7. incomparable regression results fail closed and accepted corrections require
a human disposition plus a superseding event;
8. raw corpus text is absent from all durable control artifact content.

## Evidence and disposition boundary

The tests are contract evidence for repository control artifacts only.
Full-corpus observations, thresholds, semantic corrections, and C5 gold remain
unpopulated until their respective lifecycle and human disposition gates are
satisfied. No row in these files is an accepted legal or product fact.

## Known deferred items

- Operational memory, top-K, and candidate ceilings remain
  `deferred-undefined` until runtime evidence and review.
- C5 double-coded gold requires independent coders and an explicit acceptance
event outside these YAML contracts.
- The T03 governor contract check validates YAML presence, parseability, schema
  version, proposed lifecycle, and non-authoritative status via
  `governor --only corpus`; it does not scan corpus text, execute measurements,
  validate freshness, or establish parser readiness. Full enforcement and
  cross-artifact freshness remain deferred to T04. `governor --only proof` is a
  separate existing hostile-proof group and is not evidence for these artifacts.

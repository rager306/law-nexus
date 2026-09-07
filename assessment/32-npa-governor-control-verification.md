# NPA governor control verification

Status: `[proposed]` repository-control verification assessment; non-authoritative.

## Scope and authority

This assessment verifies additive governor and CLI controls for Review Case
`RC-2026-09-05-001`. It does not execute the legal corpus, parse legal text,
create legal facts, validate R035/R070, or promote NPA parser or product
readiness. The governor remains a repository-control-only harness.

## Enforced contracts

The canonical `law-nexus-harness governor` surface now exposes additive,
version-compatible checks for:

- canonical P0-P9 pipeline order and the orthogonal document-readiness,
  mention, context-dependency, and binding FSM catalog;
- proposed/non-authoritative lifecycle boundaries, including rejection of
  accidental `[validated]` or `authoritative: true` promotion;
- metric comparability requirements, fail-closed incomparable regressions, and
  semantic non-smoothing language;
- vendor licensing and generated-registry authority boundaries.

The existing `corpus` and all prior governor groups remain registered. The new
checks are in the separate `npa-control` group and add no product runtime
logic. Findings retain the `law-nexus-governor-report/v1` shape and include
observed, expected, remediation, rule, and evidence fields.

Direct `python -m law_nexus_harness.governor ...` invocation delegates to the
canonical CLI rather than silently returning an empty all-zero success. The
canonical CLI preserves exit classes: 0 for no errors, 1 for repository
errors or requested advisory failure, and 2 for tool/selector errors.

## Verification evidence

| Check | Result |
|---|---|
| `uv run pytest -q` | PASS: 752 passed, 4 skipped |
| `uv run pytest -q tests/test_harness_governor.py tests/test_npa_control_artifacts.py` | PASS: 206 passed |
| `uv run ruff format src/law_nexus_harness/governor.py tests/test_harness_governor.py` | PASS: unchanged after formatting |
| `uv run ruff check src/law_nexus_harness/governor.py tests/test_harness_governor.py` | PASS |
| `uv run python -m law_nexus_harness governor` | PASS: status=ok, pass_count=74, warn_count=15, error_count=0 |
| `uv run python -m law_nexus_harness preflight` | PASS: status=ok, pass_count=6, warn_count=2, error_count=0 |

The governor warnings are existing/advisory repository-control findings; they
are visible in the machine-readable report and do not claim product failure or
readiness. NPA checks do not scan `consru_export/consru_export/exports`, read
raw corpus text, invoke network APIs, or generate legal facts.

## Negative and exit-class coverage

Tracked tests cover missing NPA artifacts, incomplete FSM input, corpus-group
selection, full NPA control-group pass behavior, and dotted-module delegation.
The CLI's existing selector/tool-error paths retain exit 2, repository error
paths retain exit 1, and successful canonical or delegated invocations return
0. Stale generator checks in the repository test suite invoke generators with
`--check`, so write-mode success cannot mask stale outputs.

## Deferred boundaries

- Metric thresholds remain provisional and non-authoritative.
- C5 double-coded gold, semantic acceptance, full-corpus observations, and
  human dispositions remain outside this task.
- Rust-produced receipt validation and product generator implementations remain
  future integration work; this harness only validates tracked control
  contracts and lifecycle boundaries.
- R035 and R070 remain active.

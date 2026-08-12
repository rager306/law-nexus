# ADR governor verification design

**Lifecycle:** `[proposed]` repository-control design.
**Authority:** this document is not an ADR and cannot change architecture or promote lifecycle. Canonical substance remains in `prd/ARCHITECTURE.md` and `doc/adr/**`.

## 1. Goal

Make ADR drift understandable and deterministically verifiable without turning the governor, a generated matrix, or an LLM into architecture authority.

The governor checks publication consistency. It does not decide architecture, legal correctness, product readiness, or implementation completeness.

## 2. Current deterministic baseline

| Check | Current rule | Default effect |
|---|---|---|
| `adr-truth-oracle-sync` | Discover every `doc/adr/0*.md`, read the lifecycle from its Status, and require the same lifecycle beside its citation in `prd/ARCHITECTURE.md` | blocking `error` |
| `adr-index-completeness` | Require every present ADR and its own lifecycle tag on the corresponding `doc/adr/README.md` line | advisory `warn` |
| `adr-doc-matrix-coverage` | Require explicit ADR-0016..0022 citations with `[proposed]` ceiling in tracked Product and Requirements | advisory `warn` |
| `adr-structure-hygiene` | Require Status lifecycle plus Context, Decision, Consequences and Non-claims | advisory `warn` |
| `adr-cross-surface-matrix` | Require every present ADR on the living oracle, root README and ADR index | advisory `warn` |
| `adr-link-integrity` | Resolve relative Markdown targets and local heading fragments in active ADR files | advisory `warn` |
| `adr-supersession-graph` | Validate metadata-owned partial/whole supersession targets, reciprocity and DAG shape | advisory `warn` |
| `adr-matrix-freshness` | Compare tracked non-authoritative `law-nexus-adr-matrix/v1` output with current ADR inputs | advisory `warn`; parser/I/O failures use exit 2 |
| `adr-retired-id-ban` | Reject unqualified living references to retired ADR-0001/0002/0003/0006 | advisory `warn` |
| `active-surface-era-noise` | Require archive/historical/non-claim qualification for ACP, git-lex, FalkorDB and PyO3 vocabulary | advisory `warn` |
| `archive-path-policy` | Require historical vaults ignored/untracked and reject known or generic active symlinks into them | advisory `warn` |
| `published-trace-contract` | Check every published PC-001..020→RQ-001..020 chain, detect future undeclared IDs, and preserve assessment process-only authority separation | advisory `warn` |
| `document-freshness-triggers` | Validate a non-authoritative change-impact catalog and require a distinct non-derived companion refresh for matched dirty-tree sources | advisory `warn`; Git/catalog parser failure uses exit 2 |
| `temporal-vocabulary-contract` | Validate the non-authoritative vocabulary catalog, required glossary rows/status markers and TSG gap-ID continuity | advisory `warn`; catalog/parser failure uses exit 2 |
| `verify-adr-conformance.py` | Require lifecycle tags and ADR references on targeted binding claims | separate blocking gate |

Default exit semantics remain stable: failed deterministic policy `error` checks produce exit 1 and warn-only debt produces exit 0. Unknown/conflicting selectors and check-runner IO/parser/tool failures produce structured exit 2 with `tool_error_count`. Archive Git inventory, semantic-stub/historical-test reads, dynamic coverage/readiness verifier loads and quality-gate inventory reads now use this shared classification without exposing exception text.

## 3. Machine-readable matrix contract

The implemented matrix is derived from present ADR files and living citation surfaces, not hand-maintained ID lists. Tracked output: `prd/architecture/adr-matrix.json`; it is guarded by `adr-matrix-freshness` and remains explicitly non-authoritative.

```json
{
  "schema_version": "law-nexus-adr-matrix/v1",
  "authoritative": false,
  "generated_from": ["doc/adr/0*.md", "prd/ARCHITECTURE.md"],
  "rows": [
    {
      "adr_id": "ADR-0023",
      "path": "doc/adr/0023-applicability-protocol-ownership.md",
      "status_lifecycle": "proposed",
      "oracle_lifecycle": "proposed",
      "index_lifecycle": "proposed",
      "supersedes": ["ADR-0017#applicability-ownership"],
      "surfaces": {
        "architecture": true,
        "root_readme": true,
        "adr_index": true,
        "product": true,
        "requirements": true
      }
    }
  ]
}
```

The generated matrix may report drift but cannot amend an ADR or satisfy a requirement.

## 4. Finding and evidence contract

The next compatible governor schema should add evidence without removing existing fields:

```json
{
  "check_id": "adr-truth-oracle-sync",
  "rule_id": "truth-oracle.lifecycle-mismatch",
  "status": "fail",
  "severity": "error",
  "expected": "ADR-0014 [proposed]",
  "observed": "ARCHITECTURE cites [validated]",
  "evidence": [
    {"path": "doc/adr/0014-ruvector-primary-infrastructure.md", "line": 15},
    {"path": "prd/ARCHITECTURE.md", "line": 56}
  ],
  "remediation": "Align the oracle to ADR Status; never promote in a projection."
}
```

Every fail must identify `rule_id`, expected/observed values and repository-relative `path:line` evidence. Snippets must be bounded and must not contain secrets or raw legal text.

## 5. Understandable CLI

Implemented bounded CLI subset:

```text
uv run python -m law_nexus_harness governor --only adr
uv run python -m law_nexus_harness governor --only semantic
uv run python -m law_nexus_harness governor --check adr-truth-oracle-sync
uv run python -m law_nexus_harness governor --explain adr-truth-oracle-sync
uv run python -m law_nexus_harness governor --format text
uv run python -m law_nexus_harness governor --list-checks
uv run python -m law_nexus_harness governor --only semantic --fail-on-warn
```

The default command remains backward-compatible JSON with advisory warnings returning exit 0. Unknown or conflicting selectors return structured exit 2. `--explain` is read-only and reports purpose, group, deterministic/heuristic kind, authority inputs, default severity and non-claim. `--list-checks` emits a non-authoritative machine-readable inventory without running checks. `--fail-on-warn` is opt-in execution policy: retained warnings return exit 1 without changing report status, finding severity or the default behavior.

Implemented matrix CLI:

```text
uv run python -m law_nexus_harness adr-verify --matrix generate --stdout
uv run python -m law_nexus_harness adr-verify --matrix check --output prd/architecture/adr-matrix.json
```

`--matrix generate` writes only to stdout; check requires an explicit repository-local derived path and rejects living authority targets. `--explain` shows purpose, authority inputs, deterministic/heuristic kind, default severity and non-claim; exact per-rule evidence expansion remains MVP B debt.

## 6. Staged implementation

### MVP A — current slice

- discover all present ADRs dynamically;
- include ADR-0023 and future ADRs automatically;
- require per-entry index lifecycle;
- exclude ignored Python-era ADRs from default conformance;
- reject active aliases into historical vaults;
- retain existing schema and exit behavior.

### MVP B — evidence and explain (partially implemented)

Implemented:

- additive `rule_id`, `expected` and `evidence` fields while preserving report v1 fields;
- exact repository-relative line evidence for ADR lifecycle, link, supersession, index lifecycle, ontology weave, structure, cross-surface citation, semantic-stub, retired-ID and era-noise findings when a concrete source line exists; missing surfaces remain honest path-only evidence;
- static check registry with group, deterministic/heuristic kind, inputs and non-claim;
- `--only`, `--check`, `--explain` and text output;
- selector contract failures use exit 2; warn-only semantic selection stays exit 0;
- default JSON remains compatible with preflight and existing consumers.

Remaining before MVP B closure:

- expand exact repository-relative `path:line` evidence beyond the implemented ADR-group checks; generic authority-input paths remain for other checks and aggregate inventories;
- audit future check additions so inventory/read/tool exceptions continue to reach the shared `tool-error` boundary instead of being reclassified as policy findings;
- add broader missing-file, unreadable-file and subprocess-failure contract tests.

Closed in the current follow-up: `scripts/verify-adr-conformance.py` findings now retain only repository-relative `path:line`, kind and bounded message; raw claim snippets are neither stored nor printed.

### Stage C — matrix and graph checks (partially implemented)

Implemented bounded checks:

- `published-trace-contract` checks all published PC-001..020→RQ-001..020 chains, rejects undeclared future IDs and preserves the assessment process-only boundary;
- `adr-link-integrity` resolves relative Markdown files and heading fragments inside the repository;
- `adr-supersession-graph` reads canonical active frontmatter `supersedes`/`superseded_by`, rejects legacy `superseds` on active ADRs, validates optional `#scope` reciprocity and target existence, and rejects cycles; parser compatibility may still read the legacy key from historical inputs, but it is not valid active metadata;
- active partial edges are metadata-normalized as `ADR-0011 → ADR-0005#crate-map-only` and `ADR-0023 → ADR-0017#applicability-ownership`;
- `adr-verify --matrix generate|check` implements `law-nexus-adr-matrix/v1` with stdout-only generation, explicit check target and authority-target rejection;
- `adr-matrix-freshness` keeps tracked `prd/architecture/adr-matrix.json` synchronized.

These checks and the matrix validate publication/metadata structure only and do not satisfy requirements or amend an ADR.

Remaining:

- add optional review/revisit dates as warn-only staleness signals.

### Stage D — semantic advisory input

An external/LLM review may submit cited findings, but the harness must force them to non-blocking status and require explicit human disposition. It must never set exit 1, promote lifecycle, or close a requirement.

## 7. Required negative tests

1. New ADR not cited by the oracle → blocking failure.
2. Oracle lifecycle stronger than ADR Status → blocking failure with both citations.
3. ADR missing from index or missing per-entry lifecycle → warn.
4. Missing MADR section → warn.
5. Retired ADR cited without qualifier → warn.
6. ACP/FalkorDB/PyO3 named as current direction → warn.
7. Vault tracked, unignored, or reachable through a known active alias → warn.
8. Local `python_archive/adr` exists → default active conformance still ignores it.
9. Advisory semantic report contains `critical` → no blocking exit when deterministic checks pass.
10. Matrix output attempts to target an authority path → reject.
11. A single ADR citation carrying both its real lifecycle and a stronger lifecycle → blocking failure.
12. A historical-only token with an unrelated qualifier on an adjacent line → advisory finding, not a laundered pass.
13. Semantic stub evidence exposes `path:line` but not the matched source text.
14. ADR conformance findings retain `path:line` while secret-like claim text is absent from the finding object and formatted stderr.

## 8. Non-claims

- Green ADR checks do not validate product behavior, legal correctness, ontology semantics or infrastructure readiness.
- The governor does not author ADRs or resolve architectural trade-offs.
- A generated matrix is diagnostic only.
- Archived Python/ACP/git-lex evidence cannot re-enter active authority through an index, symlink, test fixture or semantic review.

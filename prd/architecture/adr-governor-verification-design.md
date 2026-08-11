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
| `adr-doc-matrix-coverage` | Require ontology design citations on workflow projection surfaces | advisory `warn` |
| `adr-structure-hygiene` | Require Status lifecycle plus Context, Decision, Consequences and Non-claims | advisory `warn` |
| `adr-cross-surface-matrix` | Require every present ADR on the living oracle, root README and ADR index | advisory `warn` |
| `adr-retired-id-ban` | Reject unqualified living references to retired ADR-0001/0002/0003/0006 | advisory `warn` |
| `active-surface-era-noise` | Require archive/historical/non-claim qualification for ACP, git-lex, FalkorDB and PyO3 vocabulary | advisory `warn` |
| `archive-path-policy` | Require historical vaults ignored/untracked and reject known active aliases into them | advisory `warn` |
| `verify-adr-conformance.py` | Require lifecycle tags and ADR references on targeted binding claims | separate blocking gate |

Default exit semantics remain stable: failed `error` checks produce exit 1; warn-only debt produces exit 0; tool/contract failures should eventually use exit 2.

## 3. Machine-readable matrix contract

A future matrix must be derived from present ADR files, not hand-maintained ID lists.

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

Proposed control-plane UX:

```text
uv run python -m law_nexus_harness governor --only adr
uv run python -m law_nexus_harness governor --check adr-truth-oracle-sync
uv run python -m law_nexus_harness governor --explain adr-truth-oracle-sync
uv run python -m law_nexus_harness governor --format text
uv run python -m law_nexus_harness adr-verify --matrix check
uv run python -m law_nexus_harness adr-verify --matrix generate --stdout
```

`--explain` must show purpose, authority inputs, deterministic rule, severity, evidence and remediation. `--matrix generate` writes only to stdout or an explicitly derived/non-authoritative path.

## 6. Staged implementation

### MVP A — current slice

- discover all present ADRs dynamically;
- include ADR-0023 and future ADRs automatically;
- require per-entry index lifecycle;
- exclude ignored Python-era ADRs from default conformance;
- reject active aliases into historical vaults;
- retain existing schema and exit behavior.

### MVP B — evidence and explain

- add `Evidence` and `rule_id` fields additively;
- implement `--only adr`, `--check`, `--explain` and text output;
- preserve current JSON fields for preflight and existing consumers;
- test mismatch, missing file, unreadable file and warn-only paths.

### Stage C — matrix and graph checks

- generate/check `law-nexus-adr-matrix/v1`;
- check relative Markdown links;
- validate partial and whole-ADR supersession targets;
- reject supersession cycles;
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

## 8. Non-claims

- Green ADR checks do not validate product behavior, legal correctness, ontology semantics or infrastructure readiness.
- The governor does not author ADRs or resolve architectural trade-offs.
- A generated matrix is diagnostic only.
- Archived Python/ACP/git-lex evidence cannot re-enter active authority through an index, symlink, test fixture or semantic review.

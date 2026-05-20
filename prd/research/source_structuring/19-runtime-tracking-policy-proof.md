# M033 S05 — Runtime Tracking Policy Proof

## Status

- Milestone: `M033-1vpo4b — Graph Context Formation from Verified Candidates`
- Slice: `S05 — Runtime Tracking Policy Implementation`
- Proof status: `draft_t01_tracking_contract`
- Requirement advanced: follow-on bounded `R039`
- Requirements not validated: `R035`, `R037`, `R038`

## Purpose

S05 implements the repository tracking policy for generated source-discovery and graph-context runtime outputs. Generated outputs under `law-source/consultant/runtime/` should not be accidentally committed. Source documents, proof docs, scripts, and tests should remain trackable.

This slice is operational hygiene only. It does not run provider calls, does not perform FalkorDB ingestion, and does not validate legal or product claims.

## Generated outputs to ignore

The generated runtime root is:

```text
law-source/consultant/runtime/
```

This root may contain generated outputs such as:

- `runtime/inbox/`
- `runtime/raw/`
- `runtime/registry/`
- `runtime/processed/`
- `runtime/runs/`
- `runtime/trajectory/`
- `runtime/discovery/`
- `runtime/minimax-attempts/`
- `runtime/verifier/`
- `runtime/external-review/`
- `runtime/graph-context/`

The intended `.gitignore` policy is narrow:

```gitignore
law-source/consultant/runtime/
```

## Paths that must remain trackable

The policy must not ignore source documents or durable proof work:

- source documents: `law-source/consultant/*.xml`, `law-source/garant/*.odt`;
- proof docs: `prd/research/source_structuring/*.md`;
- scripts: `scripts/*.py`;
- tests: `tests/*.py`.

## Git status verification shape

Verification should create a temporary sentinel under `law-source/consultant/runtime/`, check git ignore/status behavior, then remove the sentinel.

Expected behavior:

- `git check-ignore law-source/consultant/runtime/<sentinel>` succeeds;
- `git status --short --untracked-files=all` does not list the sentinel;
- representative source/proof paths are not ignored;
- sentinel is removed before task completion.

## Observed runtime ignore evidence

T04 sentinel smoke created:

```text
law-source/consultant/runtime/gsd-ignore-smoke/manual-sentinel.generated.json
```

Observed result:

```json
{
  "m033_s05_runtime_ignore_smoke": "pass",
  "check_ignore": "law-source/consultant/runtime/gsd-ignore-smoke/manual-sentinel.generated.json",
  "sentinel_status_absent": true
}
```

The sentinel was removed after the smoke. `git check-ignore` matched the runtime sentinel, and `git status --short --untracked-files=all` did not list it.

Runtime tracking tests also verify representative source/proof/script/test paths remain trackable.

## Non-claims

S05 does not validate R035, does not validate R037, and does not validate R038.

S05 does not claim:

- legal correctness;
- parser completeness;
- product retrieval quality;
- production ETL readiness;
- FalkorDB graph ingestion;
- independent GPT-5.5 review completion.

## T01 verification markers

This proof intentionally includes `law-source/consultant/runtime`, `.gitignore`, `git status`, generated outputs, source documents, proof docs, `R035`, `R037`, and `R038`.

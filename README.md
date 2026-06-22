# law-nexus

**A citation-safe, evidence-verifiable legal graph for Russian normative acts.**

The goal is to turn a normative act into a graph-vector representation for exact
article / semantic search, temporal filtering by edition and effective date, and
provable answers with legal citations. **The LLM is never legal authority** —
every checkable operation is algorithmic, via FalkorDB + a formal Legal KnowQL.

> **Status:** `[bounded]` foundation — structural plumbing complete and
> enforced, but data is **not** prepared and **no** product capability is ready.
> Truth over optimism (D098): every state claim below is lifecycle-tagged, and
> nothing is smoothed up to `[validated]`.

[![compliance-gate](https://github.com/rager306/law-nexus/actions/workflows/compliance-gate.yml/badge.svg)](https://github.com/rager306/law-nexus/actions/workflows/compliance-gate.yml)

## What this is (and is not)

**law-nexus is a profile consumer** of the externalized reusable ACP/git-lex core
at [`rager306/git-lex-kit-acp`](https://github.com/rager306/git-lex-kit-acp). It
owns the law-specific substance (Russian legal evidence, the FalkorDB legal
graph, the Garant/Consultant parser, citation-safe retrieval) and the GSD
governance layer (D098 anti-drift).

| It is | It is not |
|---|---|
| Structural foundation: an enforced onion package + ADR standard + compliance gate | A working product. No retrieval, no legal answers, no production runtime yet. |
| A bounded parser baseline (`M009`) + a proof-gated hardening roadmap | Parser-complete for all sources. |
| An anti-drift discipline (D098 lifecycle tags, living truth oracle) | A FalkorDB production deployment. |

## Current status (D098 lifecycle tags)

```
[STRUCTURAL FOUNDATION — COMPLETE, enforceable locally + in CI]
  M068  src/law_nexus onion package (ADR-0001) + ADR standard (ADR-0002)
        + compliance gate: pre-commit hooks AND GitHub Actions CI     [bounded]
  M069  library boundary contract (ADR-0003) + gate-green tree        [bounded]
  M070  project-state roadmap freshness guard (pytest)                [bounded]

[PRODUCT TRACK — RESUMES HERE]
  Consultant XML Parser Hardening (M034 roadmap)                      [proposed]  ← next
    baseline lock → lxml eval → structural rules → semantic diagnostics →
    razdel/pymorphy3 → source-span/stable-ID → final proof package

[DOWNSTREAM — BLOCKED until parser data is ready]
  graph materialization → retrieval / citation-safe answers →
  R035 / R037 / R038 validation

[FROZEN]
  ACP/git-lex — checkpoint mode (detect+log+flag, non-blocking) until parser
  data is ready (D098). Not a milestone track, not a gate.
  R035 / R037 / R038 — not validatable from documentation/projection evidence
  alone; deferred to downstream product-data milestones.
```

See [`prd/project-state/roadmap.md`](prd/project-state/roadmap.md) for the full
trajectory and [`prd/ARCHITECTURE.md`](prd/ARCHITECTURE.md) for the living truth
oracle (**read that first**, not this README).

## Architecture (pointers, not duplicates)

The architecture lives in three places — this README only points at them.

- **Living truth oracle:** [`prd/ARCHITECTURE.md`](prd/ARCHITECTURE.md) — the
  single-page forced truth about law-nexus state. **Read this first.**
- **Package structure (ADR-0001):** `src/law_nexus` — a dependency-directed
  onion: `domain/` (Pydantic `[proposed]` forms: SourceDocument, SourceBlock,
  LegalUnit, ActEdition, EvidenceSpan, NormStatement, …) → `ports/` (pure
  `typing.Protocol`s: Parser, GraphStore, Embedder, LLMClient) → `application/`
  (Ingest use case) → `adapters/parsers/` (ConsultantWordMLParser) →
  `composition.py` (factory root, no DI framework).
- **ADR standard (ADR-0002):** [`doc/adr/`](doc/adr/) — MADR-format Architecture
  Decision Records with mandatory D098 lifecycle tags and an explicit split
  with `.gsd/DECISIONS.md`. Live: [ADR-0001](doc/adr/0001-onion-package-structure.md)
  (onion structure), [ADR-0002](doc/adr/0002-adr-standard-and-compliance-gate.md)
  (ADR standard + compliance-gate/ACP-checkpoint split),
  [ADR-0003](doc/adr/0003-library-boundary-contract.md) (library boundary).
- **Library boundary (ADR-0003):** Pydantic v2 = domain forms + parser I/O
  boundary records + JSON Schema; stdlib `@dataclass` = verifier/extractor
  records; Adaptix = `[deferred]` boundary-record↔domain-form mapping (activates
  when the parser product wires it).
- **Compliance gate (ADR-0002):** structural, hard-fail, code-architecture.
  Enforced both locally (`.pre-commit-config.yaml`) and in CI
  (`.github/workflows/compliance-gate.yml`):
  - `import-linter` onion-layer contracts (ADR-0001 layer direction)
  - `verify-adr-conformance` D098 lifecycle-tag + ADR-reference checker
  - `ruff check` / `ruff format --check` on `src/`
  - Per ADR-0002, this gate ≠ the ACP checkpoint (D098); they must never merge.

## Quick start

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/rager306/law-nexus.git
cd law-nexus
uv sync                       # install runtime + dev deps (ruff, import-linter, pre-commit, …)
uv run pre-commit install     # wire the local compliance gate (optional but recommended)
```

Run the compliance gate (same 4 checks CI runs):

```bash
uv run pre-commit run --all-files
# or each check directly:
uv run ruff check src/
uv run ruff format --check src/
uv run lint-imports
uv run python scripts/verify-adr-conformance.py
```

Type-check the package and run the architecture verifier:

```bash
uv run basedpyright src/
uv run python scripts/verify-architecture-graph.py   # R029 architecture-graph verifier
```

Run the test suite:

```bash
uv run pytest -q
```

## Where to read next

1. **[`prd/ARCHITECTURE.md`](prd/ARCHITECTURE.md)** — living truth oracle. Read first.
2. **[`prd/project-state/roadmap.md`](prd/project-state/roadmap.md)** — trajectory (where we are, next milestone, what's blocked).
3. **[`doc/adr/README.md`](doc/adr/README.md)** — the MADR ADR standard + significance gating + the ADR/`.gsd/DECISIONS.md` split.
4. **[`prd/research/source_structuring/25-corrected-consultant-xml-parser-roadmap.md`](prd/research/source_structuring/25-corrected-consultant-xml-parser-roadmap.md)** — the next milestone (parser hardening).
5. **`.gsd/PROJECT.md` / `.gsd/DECISIONS.md` / `.gsd/REQUIREMENTS.md`** — GSD governance (current state, decision register, capability contract).

## Non-claims (what this project does **not** prove today)

Following the D098 anti-smoothing discipline, law-nexus today does **not** claim:

- any `[validated]` product capability — all product work is `[bounded]`/`[smoke]`/`[proposed]`;
- parser completeness, multi-document Consultant expansion, or Garant parity;
- legal correctness or authoritative legal interpretation;
- citation-safe retrieval quality or legal-answer correctness;
- a FalkorDB production runtime or KnowQL product;
- R035 / R037 / R038 validation.

These are explicit deferrals, tracked in the roadmap, not gaps being hidden.

## Governance

- **D098** — anti-drift: ACP/git-lex role = checkpoint enforcement (detect+log+flag,
  non-blocking); mandatory `[proposed]`/`[bounded]`/`[smoke]`/`[validated]`/
  `[deferred]` lifecycle tags on architectural/state claims; never smooth a
  bounded/proposed claim up to `[validated]`.
- **D097** — law-nexus is a profile consumer of the externalized
  `rager306/git-lex-kit-acp` core.
- Decisions live in `.gsd/DECISIONS.md` (governance events) and
  [`doc/adr/`](doc/adr/) (architectural substance) — complementary, not duplicate.

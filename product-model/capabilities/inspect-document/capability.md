---
availability:
  - place: terminal
references:
  - kind: code
    role: implementation
    target: crates/ln-product-cli/src/main.rs#inspect
    title: inspect()
---

# Inspect document

Decode one act file and print a bounded JSON report of what the decoders
found: blocks, hierarchy markers and their registry lifts, membership
proposals, admits, and commits, the structural AST assembly with its oracle
drift counters, text-CTV resolutions, the detected document group, reference,
temporal, and deontic counts, one retrieval hit count, and the presence
report.

The vector and graph stores behind the report are in-memory adapters:
nothing survives the run and nothing is written to disk. The retrieval count
is produced through `StubEmbedding`, the fail-closed stub of the embedding
port: hash-derived deterministic vectors with no semantics, where a
construction failure is a typed storage error and never a silent all-zero
vector. Every report ends with an explicit non-claims list.

---
appliesTo:
  - type: capability
    id: inspect-document
    contexts:
      - place: terminal
---

# Inspect retrieval is deterministic, non-semantic, and never a silent zero

The retrieval count in the inspect report comes from hash-derived vectors over
the in-memory store, ranked by cosine similarity; an empty hit prints count 0
with status ok, an execution error prints status unavailable, and a typed
mismatch prints unexpected_result.

## Rationale

The vectors come from `StubEmbedding`, the fail-closed stub of the embedding
port: a construction failure is a typed storage error, never a silent
all-zero vector, and semantic embedding would require infrastructure the
product does not ship.

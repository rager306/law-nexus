---
id: law-nexus
summary: >-
  law-nexus-inspect is a terminal CLI that decodes Russian normative act
  documents (Consultant WordML, Garant ODT), reports bounded structural
  analysis, replays edition diffs, and resolves subordinate-act punkt units.
category: legal-document-inspection
tags:
  - cli
  - legal-documents
  - structural-analysis
limitations:
  - A command run keeps nothing between runs; every store is an in-memory adapter.
  - Retrieval vectors come from the fail-closed StubEmbedding; they are deterministic and non-semantic.
  - Reports claim no legal correctness, no citation authority, and no corpus completeness; every report carries explicit non-claims.
  - Only Consultant WordML (.xml) and Garant ODT (.odt) inputs are accepted.
---

# law-nexus

law-nexus is a terminal inspection tool for Russian normative acts. One
binary, `law-nexus-inspect`, decodes a document file (Consultant WordML or
Garant ODT), reports what it found in one bounded JSON verdict, compares two
editions of an act, or resolves the punkt structure of a subordinate act.

Every command is a single process: it builds its stores from in-memory
adapters, prints one report or one typed failure record, and exits. Nothing
persists between runs, and there is no sign-in: whoever can run the binary can
run every subcommand.

Retrieval inside the inspect report is exercised through `StubEmbedding`, the
fail-closed stub of the embedding port: hash-derived deterministic vectors
with no semantics, where a construction failure is a typed storage error and
never a silent all-zero vector.

---
kind: primary
routes:
  cli: CLI
steps:
  - text: The operator runs law-nexus-inspect inspect with the path of a Consultant WordML file
    kind: actor
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::document-report
  - text: The Product reads the document and records its path, byte size, content fingerprint, and source family
    kind: product
    actor: operator
    entities:
      - entity: document
        effect: reads
        facts: [Path, Byte size, Content fingerprint, Source family]
    contexts:
      cli:
        place: terminal::document-report
  - text: The Product decodes the blocks and counts hierarchy markers, reference mentions, temporal phrases, deontic lexemes, and unknown forms
    kind: product
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::document-report
  - text: The Product stores one deterministic vector and one graph node per hierarchy block in its in-memory stores and runs one bounded retrieval query through the fail-closed StubEmbedding stub
    kind: product
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::document-report
  - text: The Product prints the report with status ok, the assembly and presence results, the retrieval count, and the non-claims list
    kind: product
    actor: operator
    entities:
      - entity: document
        effect: reads
        facts: [Path, Byte size, Content fingerprint, Source family]
    contexts:
      cli:
        place: terminal::document-report
---

# Inspect a Consultant WordML file

## Trigger

The operator wants a bounded structural report for a Consultant WordML file.

## Outcome

The report prints with status ok: counted blocks, markers, lifts, membership,
assembly, retrieval, and presence, every unknown a visible counter, and the
non-claims list last.

## Edge cases

- A truncated or malformed Consultant file fails atomically as one typed Parse failure record, never a partial report.

---
kind: edge
routes:
  cli: CLI
steps:
  - text: The operator runs law-nexus-inspect inspect with an empty .xml file
    kind: actor
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::document-report
  - text: The Product decodes zero blocks and prints the report with status ok and zero counters
    kind: product
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::document-report
---

# An empty input is an explicit zero

## Trigger

The operator inspects a valid but empty `.xml` file.

## Outcome

The report prints with status ok and `blocks: 0`; the empty result is visible,
not an error and not silence.

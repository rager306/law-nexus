---
kind: edge
routes:
  cli: CLI
steps:
  - text: The operator runs law-nexus-inspect subordinates with a path whose filename carries no date
    kind: actor
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::document-report
  - text: The Product reports the document with an explicit no_document_date skip reason and zero text-version counters
    kind: product
    actor: operator
    entities:
      - entity: document
        effect: reads
        facts: [Path]
    contexts:
      cli:
        place: terminal::document-report
---

# A missing document date fails closed

## Trigger

The filename of the act carries no derivable date.

## Outcome

The report prints with status ok, `skip_reason: no_document_date`, and zero
text-version counts; nothing is inferred silently.

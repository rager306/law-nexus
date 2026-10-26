---
kind: validation
routes:
  cli: CLI
steps:
  - text: The operator runs law-nexus-inspect inspect with a path whose extension selects no supported family
    kind: actor
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::document-report
  - text: The Product prints one typed failure record naming the Parse phase and the unsupported family kind, and exits nonzero
    kind: product
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::document-report
---

# Inspect refuses an unsupported family

## Trigger

The operator names a file that is neither `.xml` nor `.odt`.

## Outcome

One typed failure record (phase Parse, kind UnsupportedFamily) prints and the
command exits 1; no decoding starts.

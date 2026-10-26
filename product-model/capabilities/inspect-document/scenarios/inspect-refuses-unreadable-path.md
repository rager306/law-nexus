---
kind: validation
routes:
  cli: CLI
steps:
  - text: The operator runs law-nexus-inspect inspect with a path the filesystem cannot read as a file
    kind: actor
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::document-report
  - text: The Product prints one typed failure record naming the Io phase and the read failure kind, and exits nonzero
    kind: product
    actor: operator
    entities: []
    contexts:
      cli:
        place: terminal::document-report
---

# Inspect refuses an unreadable path

## Trigger

The operator names a path that does not exist or is a directory.

## Outcome

One typed failure record (phase Io, kind ReadFailure, message fingerprint,
duration) prints and the command exits 1; no report follows.

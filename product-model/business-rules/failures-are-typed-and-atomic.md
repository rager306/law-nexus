---
appliesTo:
  - type: capability
    id: inspect-document
  - type: capability
    id: replay-edition
  - type: capability
    id: resolve-subordinates
---

# A failed command prints one typed failure and exits nonzero

A command that cannot complete prints exactly one failure record naming its
phase and kind and exits nonzero; it never prints a partial report.

## Rationale

Every failure carries a typed kind (a read failure, an unsupported family, a
malformed input), a fingerprint of the message, and the duration; usage
errors print the usage line and exit 2 before any input is read.

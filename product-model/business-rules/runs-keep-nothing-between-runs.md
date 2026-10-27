---
appliesTo:
  - type: capability
    id: check-health
  - type: capability
    id: inspect-document
  - type: capability
    id: replay-edition
  - type: capability
    id: resolve-subordinates
---

# A run keeps nothing between runs

Every command builds its stores in memory, prints its report, and exits; no
document, count, vector, or graph node survives the process.

## Rationale

The storage ports are served by in-memory adapters, so a second identical run
produces the same report.

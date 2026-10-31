# Patch Findings

<!-- Written at ship when the project verify blocked the final gate; consumed by patch planning. -->

Reviewed HEAD: 4a0ceb46fc30fb2521c6e0cd8c07eb642a9823e4
State: ship/blocked

## Findings

### P001 — stale DOCS-AUDIT rulings pin fails the project verify

- **Source**: `.project/review/final-gap-1.md`
- **Locator**: Risk: project Verify
- **Evidence**: Project Verify failed at the reviewed commit.
- **Fix direction**: Resolve the recorded command failure before shipping.

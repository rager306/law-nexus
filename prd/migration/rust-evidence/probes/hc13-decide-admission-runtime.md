# HC-13 Decide Admission runtime proof

**Evidence ID:** `S10-HC-13-RT`  
**Date:** 2026-07-23  
**Lifecycle:** `[bounded]`  
**Verdict:** `PASS`  
**Implementation revision:** `24dc9aa0fc271464f00d3e8c2b42b41791ef7489`

## Decision question

Does application admission policy fail closed on bound-unknown, saturated and
retry-amplification, keep capacity unknown without a measured local bound, and
reject vendor/foreign benchmark numbers as capacity precision without inferring
legal-delay or completeness meaning?

## Execution

```bash
cargo run --offline --quiet -p ln-hc13-runner -- verdict
```

Scenarios:

- `bound-unknown-pauses` — unknown bound pauses; capacity unknown;
- `saturated-rejects` — saturated rejects; capacity unknown;
- `retry-amplification-rejects` — retry storm rejects;
- `measured-bound-admits` — clean local measured bound may admit;
- `hostile-vendor-rejects` — vendor numbers reject even if pretend-measured;
- `forbidden-inference-matrix` — legal-delay/completeness/vendor claims reject.

## Objective checks

| Check | Result |
|---|---|
| Bound-unknown pauses | PASS |
| Saturated rejects | PASS |
| Retry amplification rejects | PASS |
| Measured bound admits | PASS |
| Hostile vendor rejects | PASS |
| Forbidden inference matrix | PASS |
| Vendor number never used | PASS |
| Capacity unknown on reject | PASS |
| Queue/hardware/throughput selected | No |

## Interpretation

HC-13 moves from `unsupported-case` to bounded runtime `PASS`. After HC-01 through HC-13:

```text
13 PASS
0 FAIL
7 unsupported-case
```

Capacity remains unknown without local measured bound identity.

## Non-claims

- No queue, hardware or throughput selected.
- Bounded-local is synthetic measured-bound identity only; E1-E3 unproven.
- No product storage/backend selected.

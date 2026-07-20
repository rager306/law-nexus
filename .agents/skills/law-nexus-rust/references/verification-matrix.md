# Rust verification matrix

Use the smallest set that proves the changed behavior and its diagnostic surface. Inspect test collection and fixtures before any potentially expensive run.

| Change | Required checks | Additional evidence |
|---|---|---|
| Formatting-only Rust change | `cargo fmt --all --check` | Confirm no semantic diff |
| New or changed Rust behavior | `cargo fmt --all --check`; targeted `cargo test`; `cargo check --workspace --offline` | Test one failure or diagnostic path |
| Cargo/workspace change | `cargo metadata --no-deps --format-version 1`; `cargo check --workspace --offline`; targeted tests | Confirm lockfile and dependency intent |
| Public API or serialized schema | Targeted unit/integration tests; deterministic repeat-output check | Compatibility or explicit break evidence |
| Python-to-Rust parity slice | Rust tests; frozen artifact comparison; subprocess harness test | Prove Python product imports/FFI are absent |
| Error handling | Targeted failing input or forced failure | Exit code, bounded stderr/JSON, no sensitive payload |
| Performance change | Representative before/after benchmark in release mode | Same-output assertion and resource measurements |
| Async/concurrency | Targeted cancellation, shutdown, ordering, and backpressure tests | No lock held across await; deterministic result where required |
| Unsafe code | Normal tests plus targeted Miri where feasible | Written invariants and `// SAFETY:` audit |
| CI/pre-commit | Local equivalent command and contract test | Path gating and failure propagation |

## Default command set

Use offline checks where dependencies are already locked and available:

```bash
cargo fmt --all --check
cargo check --workspace --offline
cargo test --workspace --offline
cargo clippy --workspace --all-targets --offline -- -D warnings
```

Do not run the full matrix blindly. For a zero-dependency tracer, targeted build/test and direct process checks may be sufficient. For parser parity, inspect fixtures and avoid hidden corpus regeneration before running any suite.

## Completion rule

Compilation alone is insufficient. Verification must demonstrate:

1. intended behavior;
2. a relevant failure or diagnostic surface;
3. no boundary regression such as FFI, Python product imports, tracked-artifact mutation, or nondeterministic output.

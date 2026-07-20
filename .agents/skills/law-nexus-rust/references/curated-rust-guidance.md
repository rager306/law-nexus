# Curated Rust guidance

Rule IDs preserve traceability to the pinned `leonardomso/rust-skills` corpus. The wording below is adapted for law-nexus. Apply only the categories relevant to the current task and always apply `project-policy.md` first.

## Ownership and allocation

- `own-borrow-over-clone`: borrow when the callee does not need ownership; do not clone to silence borrow-checker design problems.
- `own-slice-over-vec`: accept `&[T]` and `&str` instead of `&Vec<T>` and `&String` at read-only boundaries.
- `own-clone-explicit`: keep potentially expensive duplication visible and intentional.
- `own-lifetime-elision`: add explicit lifetimes only when they clarify a real relationship.
- `mem-with-capacity`: preallocate only when a reliable bound is known and profiling or scale makes it relevant.
- `mem-take-replace`: use `mem::take` or `mem::replace` to move from mutable state without cloning.
- `perf-iter-lazy` and `perf-collect-once`: avoid unnecessary intermediate collections, but prefer clarity outside proven hot paths.
- `perf-io-buffering`: buffer repeated small reads or writes over legal corpus artifacts.

## Errors and diagnostics

- `err-result-over-panic`: represent expected input, I/O, parse, compatibility, and subprocess failures as `Result`.
- `err-question-mark`: propagate errors cleanly while retaining useful boundary context.
- `err-source-chain`: preserve source errors; do not replace them with context-free strings.
- `err-expect-bugs-only`: reserve `expect` for documented invariants that indicate programmer defects.
- `err-no-unwrap-prod`: avoid `unwrap` in product paths; tests may use it when failure location remains obvious.
- `err-custom-type`: use typed errors when callers need stable branching or machine-readable failure classes.
- `obs-structured-fields`: use stable structured fields for document IDs, phases, counts, durations, and retry state.
- `obs-no-sensitive-data`: never log secrets, credentials, raw vectors, or unnecessary legal text.
- `obs-error-chain`: record an error once at the owning boundary with its source chain.

## Domain and API design

- `api-parse-dont-validate`: convert external strings and records into types that encode validated invariants.
- `api-newtype-safety` and `type-newtype-ids`: distinguish act IDs, edition IDs, evidence IDs, source offsets, and graph IDs at compile time.
- `type-enum-states`: encode mutually exclusive parser, ingest, retrieval, and lifecycle states as enums.
- `type-option-nullable`: use `Option` only for genuine absence, not as a substitute for failure classification.
- `type-result-fallible`: use `Result` for operations that can fail and make error ownership explicit.
- `type-no-stringly`: prefer enums and validated types for lifecycle tags, source kinds, edge kinds, and status values.
- `api-from-not-into`: implement `From` for infallible conversions and `TryFrom` for validation/failure.
- `conv-fromstr-parsing`: use `FromStr` where text-to-domain parsing is a stable public operation.
- `api-must-use`: mark results or builders only when ignoring them is likely a defect.
- `api-non-exhaustive`: use only for public compatibility surfaces that are expected to grow; do not hide internal exhaustive-state checks.

## Numeric and deterministic behavior

- `num-overflow-explicit`: choose checked, saturating, wrapping, or overflowing arithmetic deliberately.
- `num-cast-try-from`: use `TryFrom` for narrowing source offsets, counts, lengths, and external IDs.
- `num-float-compare`: avoid exact float equality for scores; define tolerance and ordering semantics.
- `pat-exhaustive-enum`: match owned internal enums exhaustively so new legal/parser states cause compile failures.
- `pat-let-else`: use early extraction where it shortens the happy path without hiding diagnostics.
- Prefer deterministic ordered collections or explicit sorting before serialization, hashing, comparison, and proof generation.

## Serde and contract boundaries

- `serde-rename-all`: state external naming conventions explicitly.
- `serde-deny-unknown-fields`: use for strict contracts where silent forward acceptance is unsafe; do not combine blindly with compatibility requirements.
- `serde-default-compat`: add defaults only where absence has a defined backward-compatible meaning.
- `serde-enum-representation`: choose tagging deliberately and test exact JSON shape.
- `serde-try-from-validate`: deserialize through a raw type when validation must occur before domain construction.
- Avoid `serde(flatten)` when it obscures the contract or permits ambiguous fields.

## Testing and documentation

- `test-descriptive-names`: name the behavior, condition, and expected outcome.
- `test-cfg-test-module`: keep focused unit tests near internal behavior when appropriate.
- `test-integration-dir`: use process or public-contract tests for CLI, crate, and cross-boundary behavior.
- `test-doctest-examples`: use executable docs for stable public APIs, not for volatile internal details.
- Property testing is useful for parser invariants, round trips, ordering, and malformed input only after a bounded generator is defined.
- Snapshot tests are acceptable for stable complex output when reviewed and protected from automatic corpus rewrites.
- `doc-errors-section`, `doc-panics-section`, and `doc-safety-section`: document observable failure and safety contracts on public APIs.

## Project structure and linting

- `proj-flat-small`: keep the current small tracer flat; split modules only around real seams.
- `proj-lib-main-split`: when a binary accumulates reusable/testable logic, keep `main` as orchestration and move behavior into a library crate or module.
- `proj-mod-by-feature`: group parser, evidence, retrieval, graph, and orchestration behavior by capability rather than by generic type buckets.
- `proj-pub-crate-internal`: expose the smallest visibility needed.
- `proj-workspace-deps`: centralize shared dependency versions only after multiple crates actually share them.
- `proj-feature-additive`: features should add capability rather than silently remove or mutate existing semantics.
- `proj-build-rs-minimal`: build scripts must be deterministic, bounded, and free of hidden network or repository mutation.
- `lint-rustfmt-check`: enforce formatting in CI.
- `lint-workspace-lints`: add shared lint policy when the workspace has enough crates to benefit.
- Apply Clippy groups selectively; do not suppress warnings globally without a recorded rationale.

## Unsafe and concurrency

- `unsafe-safety-comment`: every owned unsafe block needs a nearby invariant explanation.
- `unsafe-minimize-scope`: keep only the operation requiring unsafe inside the block.
- `unsafe-send-sync-manual`: manual `Send`/`Sync` requires explicit thread-safety invariants and review.
- `unsafe-miri-ci`: use targeted pinned Miri checks if owned unsafe code exists; safe-only crates do not need Miri ceremony.
- `async-no-lock-await`: never hold synchronous or async locks across await unless the primitive and invariant explicitly require it.
- `async-bounded-channel`: bounded queues are the default when future pipeline stages need backpressure.
- `async-cancel-safety`: define partial-progress semantics before racing or cancelling ingestion/retrieval operations.
- `conc-atomic-ordering`: atomic ordering must be justified; never default to weaker ordering from intuition alone.

## Anti-patterns to reject

- `anti-over-abstraction`: no generic framework before a second concrete use demonstrates the seam.
- `anti-premature-optimize`: no optimization without representative measurement.
- `anti-clone-excessive`: no clone-based borrow-checker avoidance without ownership analysis.
- `anti-panic-expected`: no panic for malformed legal input, absent files, graph failure, or user/process errors.
- `anti-stringly-typed`: no free-form strings for stable domain state.
- `anti-empty-catch`: no ignored errors; classify, propagate, or explicitly justify best-effort behavior.
- `anti-type-erasure`: choose generics versus trait objects from API and runtime needs; neither is universally superior.

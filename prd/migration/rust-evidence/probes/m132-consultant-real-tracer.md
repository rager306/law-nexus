# M132 Consultant real-document tracer

- **Evidence ID:** `M132-S05-CONSULTANT-REAL-TRACER`
- **Lifecycle:** `[bounded]`
- **Verdict:** PASS
- **Executable contract:** `crates/ln-decode/tests/consultant_real_tracer.rs`
- **Command:** `cargo test -p ln-decode --test consultant_real_tracer --offline`

## Tracked source

`law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml`

- Bytes: `193726`
- SHA-256: `62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d`
- Runtime fingerprint: `fnv1a64:d7697a0ea8cc3970`

## Bounded result

Two independent Rust decodes produced identical `ParsedBlock` values. The tracer emitted 167 validated blocks and 22 markers covered by the bounded shared hierarchy rules. Every block's `SourceSpan` sliced a complete original WordML paragraph; every hierarchy `TextSpan` remained within decoded block text. A truncated copy failed atomically as `Parse/MalformedInput` without returning prior blocks or persisting raw legal text.

## Architecture closure

The Consultant adapter implements `BlockDecoderPort`. Shared hierarchy consumes `ParsedBlock` and has no adapter dependency. Artifact `SourceSpan` and decoded `TextSpan` remain independent; the tracer does not claim an automatic translation between them.

## Non-claims

This single tracked document does not prove Consultant corpus completeness, parser parity, complete style or hierarchy coverage, legal correctness, temporal/deontic/relation extraction, retrieval, citations, storage, RuVector, TEI, or Garant ODT behavior. `Часть`, `пункт`, and `подпункт` remain outside the bounded hierarchy extractor.

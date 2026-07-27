# M133 Garant real-document tracer

- **Evidence ID:** `M133-S06-GARANT-REAL-TRACER`
- **Lifecycle:** `[bounded]`
- **Verdict:** PASS
- **Executable contract:** `crates/ln-decode/tests/garant_real_tracer.rs`
- **Command:** `cargo test -p ln-decode --test garant_real_tracer --offline`

## Tracked source

`law-source/garant/44-fz.odt`

- Package bytes: `247971`
- SHA-256: `73777d4741fa1b65229a8b22b97eb2cff4c5180105affb79b058d7007e3e4337`
- Runtime fingerprint: `fnv1a64:d4143a172688f8c3`
- ZIP entries: `8`
- `content.xml` bytes: `2387452`

## Bounded result

Two independent Rust decodes produced identical `ParsedBlock` values. The tracer emitted 5,124 non-empty blocks and 140 markers covered by the bounded shared hierarchy rules. Every block uses `package-member:content.xml`; every `SourceSpan` slices a complete `text:p` or `text:h` member element, and every hierarchy `TextSpan` remains within decoded block text.

The current adapter initially failed closed at member offset `13744` on a real empty `text:bookmark`, followed by an inline `text:a`. Synthetic hostile contracts were added before supporting those two evidence-required ODF elements. Empty bookmarks preserve no text; links preserve nested decoded text. Non-empty bookmarks, mismatched inline topology and unknown `text:*` semantics remain fail-closed.

## Architecture closure

`GarantOdtBlockDecoder` implements `BlockDecoderPort` and composes bounded in-memory package intake with an independent ODF state machine. Shared hierarchy consumes `ParsedBlock` and has no Garant adapter dependency. Member `SourceLocation` and decoded marker `TextSpan` remain independent; no automatic mapping is claimed. No filesystem extraction or external entity resolution occurs.

## Non-claims

This single tracked document does not prove Garant corpus completeness, complete ODF element or provider style coverage, Consultant/Garant parity, legal hierarchy completeness, legal correctness, temporal/deontic/relation extraction, retrieval, citations, storage, RuVector or TEI readiness. `Часть`, `пункт`, and `подпункт` remain outside the bounded hierarchy extractor.

# Upstream provenance

This skill is an adapted, project-specific work derived from ideas and selected guidance in:

- Source: https://github.com/leonardomso/rust-skills
- Pinned commit: `fd2a861ab0406a4ac536a55274d14ea6fd1ca9c9`
- Commit date: 2026-06-14T19:51:09-03:00
- Upstream version in frontmatter: 1.5.1
- Upstream `SKILL.md` SHA-256: `5a74070e740c8aacec1264adfc537daeab14c0f629bb604943295c08fd9252e6`
- Upstream `LICENSE` SHA-256: `663ce6f8f087dc366602ac34eefd4cf71a5d8db411359422298a1399a014a9d5`
- License: MIT

## Adaptation boundary

The upstream package contains 265 rules aimed at broad Rust usage and identifies itself as current for Rust 1.96 and edition 2024. law-nexus used Rust 1.94.1 and edition 2021 when this adaptation was created.

This adaptation:

- replaces the universal router with a law-nexus-specific Rust migration workflow;
- retains selected rule identifiers and principles in a compact curated reference;
- adds the Rust-only product and subprocess-only Python harness boundary;
- rejects speculative dependencies, blanket optimization flags, and FFI guidance;
- adds bounded verification and GSD eval contracts;
- does not claim that every upstream recommendation is authoritative or applicable.

No upstream rule file is reproduced verbatim except the MIT license. Update this skill only through an explicit review of a newly pinned upstream revision, its license, version-sensitive claims, and the project policy overlay.

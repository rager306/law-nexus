# M134 shared lexical extractor real-source census

- **Evidence ID:** `M134-S05-SHARED-EXTRACTORS-REAL`
- **Lifecycle:** `[bounded]`
- **Verdict:** PASS
- **Runtime:** Rust-only `ln-decode`
- **Command:** `cargo test -p ln-decode --test shared_extractors_real_tracer --offline`

## Proven boundary

The unchanged Consultant WordML and Garant ODT adapters were composed with the
shared reference, temporal and deontic lexical extractors. Repeated decode and
census runs were identical. Candidate coordinates remain decoded `TextSpan`
values; source-location translation is not claimed. Provider comments remain
in adapter output but produce no lexical candidates.

## Tracked sources and aggregate counts

| Provider | Blocks | Comments | Article | Point | Enters force | Loses force | Obligation | Permission | Prohibition | Negated deontic |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Consultant WordML | 167 | 0 | 53 | 16 | 1 | 0 | 0 | 4 | 0 | 1 |
| Garant ODT | 5,124 | 355 | 976 | 906 | 9 | 27 | 50 | 176 | 2 | 10 |

The two fixtures are different legal documents. Their counts are independent
bounded observations and are not a cross-format parity comparison.

## Source identity

- Consultant: `law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml`
  - bytes: `193726`
  - SHA-256: `62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d`
  - runtime fingerprint: `fnv1a64:d7697a0ea8cc3970`
- Garant: `law-source/garant/44-fz.odt`
  - bytes: `247971`
  - SHA-256: `73777d4741fa1b65229a8b22b97eb2cff4c5180105affb79b058d7007e3e4337`
  - runtime fingerprint: `fnv1a64:d4143a172688f8c3`

## Non-claims

- No corpus completeness, parser recall/precision or legal correctness claim.
- No cross-format legal or count parity claim.
- No resolved-reference or citation correctness claim.
- No effective-date, five-clock, applicability or edition-state claim.
- No `NormStatement`, actor/action scope, modality or legal-effect claim.
- No retrieval, storage, RuVector or TEI readiness claim.
- No raw legal text is persisted in this evidence.

# FalkorDB Index, Full-Text, and Vector Notes

## Treat as capability-sensitive

Index, full-text, vector, UDF/procedure, and GraphBLAS-related claims are often version/runtime sensitive. Always classify evidence before recommending production use.

## Minimum proof for index-like features

A useful smoke test should:

1. Start with a disposable graph.
2. Create the index or capability under test.
3. Wait/check readiness if the runtime exposes readiness.
4. Insert synthetic data.
5. Run the intended lookup/search/query.
6. Assert result rows and key scores/fields when applicable.
7. Clean up.

## Vector-specific proof

Do not claim vector suitability from embedding generation alone. Separate:

- model encode proof
- vector dimension and dtype proof
- FalkorDB storage/index creation proof
- vector storage/index creation proof
- vector query proof
- filtered retrieval proof if filters matter
- product quality proof on real fixtures

## Full-text-specific proof

Separate:

- index creation
- tokenization/language behavior
- query syntax
- ranking/scores if used
- interaction with filters

## Common caveat

A feature proven in a server/container runtime is not automatically proven in FalkorDBLite, and a feature proven in FalkorDBLite is not automatically proven in server/container FalkorDB.

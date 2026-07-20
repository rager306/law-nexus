# git-lex-kit-acp

ACP semantic kit for `git-lex`.

## Correct install command

Use the explicit GitHub owner/repository kit spec:

```bash
git-lex init --kit rager306/git-lex-kit-acp <target-repo>
```

Example disposable proof run:

```bash
workdir=$(mktemp -d /tmp/acp-kit-proof-XXXXXX)
git -C "$workdir" init
git-lex init --kit rager306/git-lex-kit-acp "$workdir"
```

Do **not** use the short kit name for ACP-kit runtime proof:

```bash
# Not the ACP-kit canonical invocation
git-lex init --kit acp <target-repo>
```

The short form resolves through git-lex default short-name rules and may try to fetch `repolex-ai/git-lex-kit-acp`. The accepted ACP-kit repository for this project is explicitly:

```text
rager306/git-lex-kit-acp
```

## Authority boundary

This kit packages ACP vocabulary for semantic diagnostics. It is not ACP source truth, not production evidence, and not validation evidence for law-nexus profile requirements such as R035, R037, or R038.

Use it only in isolated/disposable runtime proofs until a separate adoption decision approves broader use.

## Current runtime status

Verified so far:

- `git-lex init --kit rager306/git-lex-kit-acp <disposable-workspace>` succeeds.
- The main law-nexus checkout remains free of `.lex`, `Squad`, `Raw`, and `.artifacts` residue when proof runs are isolated.

Still requires separate proof before runtime-dependent ACP adoption:

- class discovery behavior, including `git-lex list --json`;
- `sync`, `query`, and `validate` behavior on ACP fixtures;
- negative validation failure on invalid ACP fixtures;
- non-authoritative diagnostic classification for any generated RDF/SHACL/SPARQL surfaces.

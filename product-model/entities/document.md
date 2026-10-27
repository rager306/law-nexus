# Document

A normative act file on disk that the operator names by path. The product
reads it, reports on it, and never changes it; nothing about it survives the
run.

## Information kept

- **Path** — the filesystem path the operator names on the command line
- **Byte size** — the size of the file in bytes
- **Content fingerprint** — the deterministic fingerprint of the file bytes
- **Source family** — the document family the path selects: Consultant WordML for `.xml`, Garant ODT for `.odt`

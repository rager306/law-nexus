# SQLite vs Turso crash/recovery probe

**Lifecycle:** `[bounded]`  
**Disposition:** SQLite is the comparison baseline only, not the product authority ledger; Turso remains `defer`.  
**Adoption:** none.

This isolated Rust package compares bundled stock SQLite through `rusqlite
0.39.0` and local Turso Database (`turso 0.7.1`) with the same synthetic
typed-event schema. Bundled C SQLite is used only inside this isolated comparison
probe; it is not a product-runtime storage selection.
It exercises clean commit, kill before commit, kill after commit before an
explicit checkpoint, fresh-process reopen, checksum verification, integrity
surfaces, and reopening a Turso-created file through stock SQLite.

The package is intentionally not a member of the root Cargo workspace. It uses
no legal text, vectors, credentials, remote service, cloud sync, MCP, CDC, FTS,
encryption, MVCC or multiprocess WAL.

## Run

```bash
cd probes/sqlite-turso-crash-recovery
cargo fetch
cargo test --offline
cargo run --offline --release -- matrix .probe-work/run-1 > .probe-work/run-1.json
```

Runtime artifacts under `.probe-work/` are ignored. A matrix run returns nonzero
if a runnable assertion fails. Individual scenarios can be inspected with:

```bash
cargo run --offline -- parent sqlite S02_kill_mid_txn .probe-work/s02
cargo run --offline -- parent turso S07_exit_to_stock_sqlite .probe-work/s07
```

## Scenarios

| ID | Behavior |
|---|---|
| `S01_clean_commit` | Clean transaction and reopen |
| `S02_kill_mid_txn` | Parent kills worker after half of an uncommitted transaction |
| `S03_kill_after_commit_before_checkpoint` | Parent kills worker after commit, without requesting checkpoint |
| `S04_kill_during_checkpoint` | Typed `unsupported`; no reliable cross-engine checkpoint window is fabricated |
| `S05_disk_full` | Typed `unsupported`; host disk is never filled and a simulated quota is not promoted as kernel ENOSPC proof |
| `S06_reopen_integrity` | Clean close and fresh-connection verification |
| `S07_exit_to_stock_sqlite` | Turso-created file opened read-only by bundled stock SQLite |

## Proof ceiling

A passing run is only bounded local compatibility and crash-mechanics evidence.
It does not prove production durability, power-loss safety, legal correctness,
capacity, encryption, concurrent-writer safety, backup/restore, cloud sync,
agent safety or database adoption. Turso remains `defer` until ADR-0012
re-evaluation gates pass.

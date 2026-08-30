//! Shared EffectLedgerPort contract suite (ADR-0015).
//!
//! Covers both honest adapters — the in-memory test double and the durable
//! append-only JSONL ledger — against the same shared semantic contract
//! (`assert_effect_ledger_port_contract`), plus the durable-specific failure
//! contract: durability across reopen, fail-closed env resolution
//! (empty-as-unset, no default), and corrupt/truncated persistence refusing
//! to hydrate. Lifecycle `[bounded]`: temp files live under the OS temp dir
//! and are removed on drop.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use ln_replay::adapters::{
    EffectLedgerError, HostileDuplicateEffectLedger, InMemoryEffectLedger, JsonlEffectLedger,
    EFFECT_LEDGER_PATH_ENV,
};
use ln_replay::domain::{CheckpointDigest, EffectId, OperationId};
use ln_replay::ports::EffectLedgerPort;
use ln_testkit::{
    assert_effect_ledger_port_contract,
    assert_hostile_duplicate_effect_ledger_fails_honest_contract,
};

static TEMP_SEQ: AtomicU64 = AtomicU64::new(0);

fn unique_ledger_path(label: &str) -> PathBuf {
    let seq = TEMP_SEQ.fetch_add(1, Ordering::Relaxed);
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    std::env::temp_dir().join(format!(
        "ln-testkit-effect-ledger-{}-{}-{}-{}.jsonl",
        std::process::id(),
        nanos,
        seq,
        label
    ))
}

/// Temp ledger file removed on drop; tests never mutate tracked artifacts.
struct TempLedgerFile {
    path: PathBuf,
}

impl TempLedgerFile {
    fn new(label: &str) -> Self {
        Self {
            path: unique_ledger_path(label),
        }
    }

    fn path(&self) -> &Path {
        &self.path
    }

    fn write_seed(&self, contents: &str) {
        std::fs::write(&self.path, contents).expect("seed ledger file");
    }
}

impl Drop for TempLedgerFile {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.path);
    }
}

fn op_id(value: &str) -> OperationId {
    OperationId::parse(value).expect("static operation id")
}

fn effect_id(value: &str) -> EffectId {
    EffectId::parse(value).expect("static effect id")
}

fn digest(value: &str) -> CheckpointDigest {
    CheckpointDigest::parse(value).expect("static digest")
}

#[test]
fn in_memory_ledger_satisfies_shared_port_contract() {
    let mut ledger = InMemoryEffectLedger::new();
    assert_effect_ledger_port_contract(&mut ledger);
}

#[test]
fn durable_jsonl_ledger_satisfies_shared_port_contract() {
    let temp = TempLedgerFile::new("contract");
    let mut ledger = JsonlEffectLedger::open(temp.path()).expect("fresh ledger opens");
    assert_effect_ledger_port_contract(&mut ledger);
    assert!(
        ledger.take_error().is_none(),
        "honest contract run must not surface persistence errors"
    );
}

#[test]
fn hostile_duplicate_ledger_still_fails_honest_contract() {
    let mut hostile = HostileDuplicateEffectLedger::new();
    assert_hostile_duplicate_effect_ledger_fails_honest_contract(&mut hostile);
}

#[test]
fn durable_append_survives_process_reopen() {
    let temp = TempLedgerFile::new("durable");
    let op1 = op_id("op:dur-1");
    let op2 = op_id("op:dur-2");
    let op3 = op_id("op:dur-3");
    let ef1 = effect_id("ef:dur-1");
    let ef2 = effect_id("ef:dur-2");
    let ef3 = effect_id("ef:dur-3");
    let d1 = digest("digest:dur-1");
    let d2 = digest("digest:dur-2");
    let d3 = digest("digest:dur-3");

    {
        let mut ledger = JsonlEffectLedger::open(temp.path()).expect("open fresh ledger");
        assert_eq!(ledger.applied_count(), 0);
        assert!(ledger
            .try_apply_checked(&op1, &ef1, &d1)
            .expect("first append"));
        assert!(ledger
            .try_apply_checked(&op2, &ef2, &d2)
            .expect("second append"));
        assert_eq!(ledger.applied_count(), 2);
    } // drop simulates process exit

    let persisted = std::fs::read_to_string(temp.path()).expect("read persisted ledger");
    let line1 =
        "{\"operation_id\":\"op:dur-1\",\"effect_id\":\"ef:dur-1\",\"digest\":\"digest:dur-1\"}\n";
    let line2 =
        "{\"operation_id\":\"op:dur-2\",\"effect_id\":\"ef:dur-2\",\"digest\":\"digest:dur-2\"}\n";
    assert_eq!(persisted, format!("{line1}{line2}"));

    let mut reopened = JsonlEffectLedger::open(temp.path()).expect("reopen after process exit");
    assert_eq!(reopened.applied_count(), 2);
    assert!(reopened.has_applied(&op1, &ef1));
    assert!(reopened.has_applied(&op2, &ef2));
    assert_eq!(
        reopened
            .prior_digest(&op1, &ef1)
            .as_ref()
            .map(|d| d.as_str()),
        Some("digest:dur-1")
    );

    // Fresh identity still applies and is persisted for the next process.
    assert!(reopened
        .try_apply_checked(&op3, &ef3, &d3)
        .expect("third append"));
    assert_eq!(reopened.applied_count(), 3);
    drop(reopened);

    let final_ledger = JsonlEffectLedger::open(temp.path()).expect("final reopen");
    assert_eq!(final_ledger.applied_count(), 3);
}

#[test]
fn ledger_env_fail_closed() {
    // One test function owns the env var so parallel tests never race it.
    std::env::remove_var(EFFECT_LEDGER_PATH_ENV);

    // Unset: fail closed, no default path.
    assert!(matches!(
        JsonlEffectLedger::from_env(),
        Err(EffectLedgerError::LedgerPathUnset)
    ));

    // Empty is treated exactly as unset.
    std::env::set_var(EFFECT_LEDGER_PATH_ENV, "");
    assert!(matches!(
        JsonlEffectLedger::from_env(),
        Err(EffectLedgerError::LedgerPathUnset)
    ));

    // Whitespace-only is treated exactly as unset.
    std::env::set_var(EFFECT_LEDGER_PATH_ENV, "   ");
    assert!(matches!(
        JsonlEffectLedger::from_env(),
        Err(EffectLedgerError::LedgerPathUnset)
    ));

    // A real path opens (creating the empty ledger file).
    let temp = TempLedgerFile::new("env-valid");
    std::env::set_var(EFFECT_LEDGER_PATH_ENV, temp.path());
    let opened = JsonlEffectLedger::from_env().expect("valid env path opens");
    assert_eq!(opened.path(), temp.path());

    std::env::remove_var(EFFECT_LEDGER_PATH_ENV);
}

#[test]
fn corrupt_ledger_file_fails_closed_without_hydration() {
    let canonical = |op: &str, ef: &str, dg: &str| {
        format!("{{\"operation_id\":\"{op}\",\"effect_id\":\"{ef}\",\"digest\":\"{dg}\"}}")
    };
    let cases: &[(&str, String, &'static str, usize)] = &[
        (
            "garbage",
            "not-json\n".to_owned(),
            "not canonical record",
            1,
        ),
        (
            "truncated",
            "{\"operation_id\":\"op:cor\",\"effect_id\":\"ef:cor\"\n".to_owned(),
            "not canonical record",
            1,
        ),
        (
            "bad-effect-id",
            canonical("op:cor", "ef|invalid", "digest:cor"),
            "invalid effect id",
            1,
        ),
        (
            "bad-digest",
            canonical("op:cor", "ef:cor", "digest has space"),
            "invalid digest",
            1,
        ),
        (
            "duplicate-identity",
            format!(
                "{}\n{}\n",
                canonical("op:dup", "ef:dup", "digest:dup"),
                canonical("op:dup", "ef:dup", "digest:dup")
            ),
            "duplicate applied identity",
            2,
        ),
        (
            "extra-field",
            "{\"operation_id\":\"op:cor\",\"effect_id\":\"ef:cor\",\"digest\":\"digest:cor\",\"extra\":1}\n"
                .to_owned(),
            "not canonical record",
            1,
        ),
        (
            "second-line-corrupt",
            format!("{}\ngarbage\n", canonical("op:ok", "ef:ok", "digest:ok")),
            "not canonical record",
            2,
        ),
    ];

    for (label, contents, reason, line) in cases {
        let temp = TempLedgerFile::new(label);
        temp.write_seed(contents);
        let err =
            JsonlEffectLedger::open(temp.path()).expect_err("corrupt ledger must fail closed");
        match err {
            EffectLedgerError::CorruptRecord {
                path,
                line: corrupt_line,
                reason: corrupt_reason,
            } => {
                assert_eq!(&path, temp.path(), "case {label}: path must round-trip");
                assert_eq!(corrupt_line, *line, "case {label}: corrupt line number");
                assert_eq!(corrupt_reason, *reason, "case {label}: corrupt reason");
            }
            other => panic!("case {label}: expected CorruptRecord, got {other:?}"),
        }
        // Fail-closed: the seeded bytes were not rewritten or "repaired".
        assert_eq!(
            std::fs::read(temp.path()).expect("seed intact"),
            contents.as_bytes(),
            "case {label}: failed hydration must not mutate the file"
        );
    }
}

#[test]
fn missing_parent_directory_is_io_error() {
    let unused = TempLedgerFile::new("unused");
    let nested = unused
        .path()
        .with_file_name("missing-parent-dir")
        .join("ledger.jsonl");
    let err = JsonlEffectLedger::open(&nested).expect_err("missing parent must fail closed");
    assert!(matches!(err, EffectLedgerError::Io { .. }));
}

#[cfg(unix)]
#[test]
fn ledger_path_directory_is_io_error() {
    let dir = std::env::temp_dir().join(format!(
        "ln-testkit-effect-ledger-dir-{}-{}",
        std::process::id(),
        TEMP_SEQ.fetch_add(1, Ordering::Relaxed)
    ));
    std::fs::create_dir_all(&dir).expect("create temp dir");
    let result = JsonlEffectLedger::open(&dir);
    let _ = std::fs::remove_dir(&dir);
    assert!(matches!(result, Err(EffectLedgerError::Io { .. })));
}

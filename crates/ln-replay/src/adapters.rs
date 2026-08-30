use std::collections::HashMap;
use std::error::Error;
use std::fmt;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

use crate::domain::{
    CheckpointDigest, CheckpointId, CheckpointRecord, EffectId, OperationId, RuleVersion,
};
use crate::ports::{CheckpointPort, EffectLedgerPort};

#[derive(Debug, Default, Clone)]
pub struct InMemoryCheckpointStore {
    records: HashMap<String, CheckpointRecord>,
}

impl InMemoryCheckpointStore {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(mut self, record: CheckpointRecord) -> Self {
        self.records
            .insert(record.checkpoint_id.as_str().to_owned(), record);
        self
    }
}

impl CheckpointPort for InMemoryCheckpointStore {
    fn load(&self, checkpoint_id: &CheckpointId) -> Option<CheckpointRecord> {
        self.records.get(checkpoint_id.as_str()).cloned()
    }
}

#[derive(Debug, Default, Clone)]
pub struct InMemoryEffectLedger {
    /// key: operation_id + effect_id
    applied: HashMap<String, CheckpointDigest>,
}

impl InMemoryEffectLedger {
    pub fn new() -> Self {
        Self::default()
    }

    fn key(operation_id: &OperationId, effect_id: &EffectId) -> String {
        ledger_key(operation_id, effect_id)
    }
}

impl EffectLedgerPort for InMemoryEffectLedger {
    fn applied_count(&self) -> usize {
        self.applied.len()
    }

    fn has_applied(&self, operation_id: &OperationId, effect_id: &EffectId) -> bool {
        self.applied
            .contains_key(&Self::key(operation_id, effect_id))
    }

    fn prior_digest(
        &self,
        operation_id: &OperationId,
        effect_id: &EffectId,
    ) -> Option<CheckpointDigest> {
        self.applied
            .get(&Self::key(operation_id, effect_id))
            .cloned()
    }

    fn try_apply(
        &mut self,
        operation_id: &OperationId,
        effect_id: &EffectId,
        digest: &CheckpointDigest,
    ) -> bool {
        let key = Self::key(operation_id, effect_id);
        if self.applied.contains_key(&key) {
            return false;
        }
        self.applied.insert(key, digest.clone());
        true
    }
}

/// Hostile ledger that claims apply always succeeds and inflates counts,
/// attempting to force duplicate external effects.
#[derive(Debug, Default)]
pub struct HostileDuplicateEffectLedger {
    inner: InMemoryEffectLedger,
    forced_applies: usize,
}

impl HostileDuplicateEffectLedger {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn forced_applies(&self) -> usize {
        self.forced_applies
    }
}

impl EffectLedgerPort for HostileDuplicateEffectLedger {
    fn applied_count(&self) -> usize {
        // Inflate count to confuse callers that trust the adapter.
        self.inner.applied_count() + self.forced_applies
    }

    fn has_applied(&self, operation_id: &OperationId, effect_id: &EffectId) -> bool {
        // Lie: always claim not applied so application must still suppress via
        // its own check path — application freezes has_applied from a single
        // call and uses try_apply return for authority.
        let _ = (operation_id, effect_id);
        false
    }

    fn prior_digest(
        &self,
        operation_id: &OperationId,
        effect_id: &EffectId,
    ) -> Option<CheckpointDigest> {
        self.inner.prior_digest(operation_id, effect_id)
    }

    fn try_apply(
        &mut self,
        operation_id: &OperationId,
        effect_id: &EffectId,
        digest: &CheckpointDigest,
    ) -> bool {
        // Always report success and force-insert again under a salted key path
        // via forced counter — application must not re-apply when it already
        // recorded the identity in its own freeze of has_applied.
        let first = self.inner.try_apply(operation_id, effect_id, digest);
        if !first {
            self.forced_applies += 1;
            // Pretend success even on duplicate.
            return true;
        }
        true
    }
}

pub fn sample_checkpoint(
    checkpoint_id: &str,
    digest: &str,
    rules: &str,
    operation: &str,
    effect: &str,
    history: &str,
) -> CheckpointRecord {
    CheckpointRecord {
        checkpoint_id: CheckpointId::parse(checkpoint_id).expect("static id"),
        digest: CheckpointDigest::parse(digest).expect("static id"),
        rule_version: RuleVersion::parse(rules).expect("static id"),
        operation_id: OperationId::parse(operation).expect("static id"),
        effect_id: EffectId::parse(effect).expect("static id"),
        history_digest: CheckpointDigest::parse(history).expect("static id"),
    }
}

/// Environment variable that must point at the durable effect ledger file.
/// Unset, empty, and whitespace-only all resolve to fail-closed: there is no
/// default ledger path (deliberately unlike `CONSULTANT_EXPORT_DIR`).
pub const EFFECT_LEDGER_PATH_ENV: &str = "EFFECT_LEDGER_PATH";

/// Injective ledger key for operation/effect identity. The `|` separator is
/// outside the domain id whitelist (`[A-Za-z0-9-_:.]`), so the composition
/// cannot collide or be injected through a crafted id.
fn ledger_key(operation_id: &OperationId, effect_id: &EffectId) -> String {
    format!("{}|{}", operation_id.as_str(), effect_id.as_str())
}

/// Typed failure surface of the durable effect ledger. Every variant is
/// fail-closed: no default path is substituted for an unset env var, and a
/// corrupt persisted line never partially hydrates into state.
#[derive(Debug)]
pub enum EffectLedgerError {
    /// `EFFECT_LEDGER_PATH` is unset, empty, or whitespace-only.
    LedgerPathUnset,
    /// Filesystem failure while opening, hydrating, or appending the ledger.
    Io {
        path: PathBuf,
        source: std::io::Error,
    },
    /// A persisted line is not a canonical ledger record; hydration refused.
    CorruptRecord {
        path: PathBuf,
        line: usize,
        reason: &'static str,
    },
}

impl fmt::Display for EffectLedgerError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::LedgerPathUnset => write!(
                formatter,
                "{EFFECT_LEDGER_PATH_ENV} is unset, empty, or whitespace-only; \
                 refusing to guess a ledger path (fail-closed)"
            ),
            Self::Io { path, source } => write!(
                formatter,
                "effect ledger io failure at {}: {source}",
                path.display()
            ),
            Self::CorruptRecord { path, line, reason } => write!(
                formatter,
                "corrupt effect ledger record at {}:{line}: {reason}",
                path.display()
            ),
        }
    }
}

impl Error for EffectLedgerError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Io { source, .. } => Some(source),
            Self::LedgerPathUnset | Self::CorruptRecord { .. } => None,
        }
    }
}

/// Canonical one-line JSON record layout (D102: append-only JSONL storage).
const RECORD_PREFIX: &str = "{\"operation_id\":";
const EFFECT_FIELD: &str = ",\"effect_id\":";
const DIGEST_FIELD: &str = ",\"digest\":";

fn record_line(
    operation_id: &OperationId,
    effect_id: &EffectId,
    digest: &CheckpointDigest,
) -> String {
    format!(
        "{RECORD_PREFIX}\"{}\"{EFFECT_FIELD}\"{}\"{DIGEST_FIELD}\"{}\"}}",
        operation_id.as_str(),
        effect_id.as_str(),
        digest.as_str()
    )
}

/// Strictly parse one canonical ledger record. Domain ids are
/// whitelist-validated (`[A-Za-z0-9-_:.]`, <=64 bytes), so canonical records
/// never contain JSON escapes and any other byte sequence is corruption.
fn parse_record_line(line: &str) -> Result<(&str, &str, &str), &'static str> {
    let rest = line
        .strip_prefix(RECORD_PREFIX)
        .ok_or("not canonical record")?;
    let rest = rest.strip_prefix('"').ok_or("not canonical record")?;
    let (operation_id, rest) = rest.split_once('"').ok_or("not canonical record")?;
    let rest = rest
        .strip_prefix(EFFECT_FIELD)
        .ok_or("not canonical record")?;
    let rest = rest.strip_prefix('"').ok_or("not canonical record")?;
    let (effect_id, rest) = rest.split_once('"').ok_or("not canonical record")?;
    let rest = rest
        .strip_prefix(DIGEST_FIELD)
        .ok_or("not canonical record")?;
    let rest = rest.strip_prefix('"').ok_or("not canonical record")?;
    let (digest, rest) = rest.split_once('"').ok_or("not canonical record")?;
    if rest != "}" {
        return Err("not canonical record");
    }
    Ok((operation_id, effect_id, digest))
}

/// Durable append-only JSONL `EffectLedgerPort` adapter — the first durable
/// storage target for the external effect ledger (decision D102).
///
/// Semantics:
/// - `try_apply` returns `true` only when the record is durably appended and
///   synced. Persistence failures surface as `false` through the infallible
///   port (conservative: an unrecorded effect must never be treated as
///   applied) and as a typed `Err` through [`JsonlEffectLedger::try_apply_checked`]
///   / [`JsonlEffectLedger::take_error`].
/// - `open` / `from_env` hydrate strictly: malformed, truncated, duplicated,
///   or non-canonical records fail closed with
///   [`EffectLedgerError::CorruptRecord`] instead of silently trusting disk.
#[derive(Debug)]
pub struct JsonlEffectLedger {
    path: PathBuf,
    applied: HashMap<String, CheckpointDigest>,
    append: File,
    last_error: Option<EffectLedgerError>,
}

impl JsonlEffectLedger {
    /// Open (creating if absent) the ledger at `path` and hydrate from disk.
    pub fn open(path: &Path) -> Result<Self, EffectLedgerError> {
        let io_error = |source| EffectLedgerError::Io {
            path: path.to_path_buf(),
            source,
        };
        let mut applied = HashMap::new();
        if path.exists() {
            let file = File::open(path).map_err(io_error)?;
            for (index, line) in BufReader::new(file).lines().enumerate() {
                let line = line.map_err(io_error)?;
                let line_number = index + 1;
                if line.is_empty() {
                    continue;
                }
                let corrupt = |reason| EffectLedgerError::CorruptRecord {
                    path: path.to_path_buf(),
                    line: line_number,
                    reason,
                };
                let (operation_id, effect_id, digest) =
                    parse_record_line(&line).map_err(corrupt)?;
                let operation_id = OperationId::parse(operation_id)
                    .map_err(|_| corrupt("invalid operation id"))?;
                let effect_id =
                    EffectId::parse(effect_id).map_err(|_| corrupt("invalid effect id"))?;
                let digest =
                    CheckpointDigest::parse(digest).map_err(|_| corrupt("invalid digest"))?;
                if applied
                    .insert(ledger_key(&operation_id, &effect_id), digest)
                    .is_some()
                {
                    return Err(corrupt("duplicate applied identity"));
                }
            }
        }
        let append = OpenOptions::new()
            .append(true)
            .create(true)
            .open(path)
            .map_err(io_error)?;
        Ok(Self {
            path: path.to_path_buf(),
            applied,
            append,
            last_error: None,
        })
    }

    /// Resolve the ledger path from `EFFECT_LEDGER_PATH` (empty-as-unset,
    /// whitespace-as-unset, no default) and [`JsonlEffectLedger::open`] it.
    pub fn from_env() -> Result<Self, EffectLedgerError> {
        let raw = std::env::var(EFFECT_LEDGER_PATH_ENV)
            .map_err(|_| EffectLedgerError::LedgerPathUnset)?;
        let trimmed = raw.trim();
        if trimmed.is_empty() {
            return Err(EffectLedgerError::LedgerPathUnset);
        }
        Self::open(Path::new(trimmed))
    }

    /// Ledger file path this adapter appends to.
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Take the last persistence error observed through the infallible
    /// [`EffectLedgerPort`] surface, if any.
    pub fn take_error(&mut self) -> Option<EffectLedgerError> {
        self.last_error.take()
    }

    /// Fallible durable apply: `Ok(true)` appended and synced, `Ok(false)`
    /// duplicate identity, `Err` when the record could not be persisted
    /// (in-memory state stays unchanged).
    pub fn try_apply_checked(
        &mut self,
        operation_id: &OperationId,
        effect_id: &EffectId,
        digest: &CheckpointDigest,
    ) -> Result<bool, EffectLedgerError> {
        let key = ledger_key(operation_id, effect_id);
        if self.applied.contains_key(&key) {
            return Ok(false);
        }
        let mut bytes = record_line(operation_id, effect_id, digest).into_bytes();
        bytes.push(b'\n');
        self.append
            .write_all(&bytes)
            .and_then(|()| self.append.sync_all())
            .map_err(|source| EffectLedgerError::Io {
                path: self.path.clone(),
                source,
            })?;
        self.applied.insert(key, digest.clone());
        Ok(true)
    }

    /// White-box constructor for unit tests that inject a pre-opened handle
    /// (e.g. `/dev/full`) to prove the write-failure path.
    #[cfg(test)]
    fn from_parts(path: PathBuf, applied: HashMap<String, CheckpointDigest>, append: File) -> Self {
        Self {
            path,
            applied,
            append,
            last_error: None,
        }
    }
}

impl EffectLedgerPort for JsonlEffectLedger {
    fn applied_count(&self) -> usize {
        self.applied.len()
    }

    fn has_applied(&self, operation_id: &OperationId, effect_id: &EffectId) -> bool {
        self.applied
            .contains_key(&ledger_key(operation_id, effect_id))
    }

    fn prior_digest(
        &self,
        operation_id: &OperationId,
        effect_id: &EffectId,
    ) -> Option<CheckpointDigest> {
        self.applied
            .get(&ledger_key(operation_id, effect_id))
            .cloned()
    }

    fn try_apply(
        &mut self,
        operation_id: &OperationId,
        effect_id: &EffectId,
        digest: &CheckpointDigest,
    ) -> bool {
        match self.try_apply_checked(operation_id, effect_id, digest) {
            Ok(applied) => applied,
            Err(error) => {
                self.last_error = Some(error);
                false
            }
        }
    }
}

#[cfg(test)]
mod durable_ledger_tests {
    use super::*;

    #[test]
    fn canonical_record_round_trips_through_strict_parser() {
        let line = record_line(
            &OperationId::parse("op:round").expect("id"),
            &EffectId::parse("ef:round").expect("id"),
            &CheckpointDigest::parse("digest:round").expect("id"),
        );
        assert_eq!(
            line,
            "{\"operation_id\":\"op:round\",\"effect_id\":\"ef:round\",\"digest\":\"digest:round\"}"
        );
        let parsed = parse_record_line(&line).expect("canonical record parses");
        assert_eq!(parsed, ("op:round", "ef:round", "digest:round"));
    }

    #[test]
    fn strict_parser_rejects_non_canonical_shapes() {
        let cases = [
            "hello",
            "{\"operation_id\":\"op:x\",\"effect_id\":\"ef:x\"}",
            "{\"operation_id\":\"op:\\\"x\",\"effect_id\":\"ef:x\",\"digest\":\"digest:x\"}",
            "{\"operation_id\":\"op:x\",\"effect_id\":\"ef:x\",\"digest\":\"digest:x\"} ",
            "{\"operation_id\":\"op:x\",\"effect_id\":\"ef:x\",\"digest\":\"digest:x\"},\"extra\":1}",
        ];
        for case in cases {
            assert_eq!(parse_record_line(case), Err("not canonical record"));
        }
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn append_write_failure_is_fail_closed() {
        let file = OpenOptions::new()
            .append(true)
            .create(false)
            .open("/dev/full")
            .expect("/dev/full is openable for append");
        let mut ledger =
            JsonlEffectLedger::from_parts(PathBuf::from("/dev/full"), HashMap::new(), file);
        let operation_id = OperationId::parse("op:full").expect("id");
        let effect_id = EffectId::parse("ef:full").expect("id");
        let digest = CheckpointDigest::parse("digest:full").expect("id");

        let checked = ledger.try_apply_checked(&operation_id, &effect_id, &digest);
        assert!(matches!(checked, Err(EffectLedgerError::Io { .. })));
        assert_eq!(
            ledger.applied_count(),
            0,
            "failed append must not mutate state"
        );
        assert!(!ledger.has_applied(&operation_id, &effect_id));

        assert!(
            !ledger.try_apply(&operation_id, &effect_id, &digest),
            "infallible port must report false when persistence fails"
        );
        assert!(ledger.take_error().is_some());
        assert!(ledger.take_error().is_none(), "error is taken exactly once");
    }
}

//! Operational metric receipts and append-only control-ledger helpers.
//! These artifacts are diagnostic controls, never legal assertions or gold.
use std::{fs, io, path::Path};

pub const METRIC_SCHEMA: &str = "law-nexus-npa-metric-event/v1";
pub const REGRESSION_SCHEMA: &str = "law-nexus-npa-regression-event/v1";
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Classification {
    Exact,
    Estimate,
    Proxy,
}
impl Classification {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Exact => "exact",
            Self::Estimate => "estimate",
            Self::Proxy => "proxy",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OperationalMetrics {
    pub elapsed_ms: u64,
    pub peak_memory_bytes: Option<u64>,
    pub candidate_limit_events: u64,
    pub cycle_limit_events: u64,
}

/// Reads Linux VmHWM. Absence is represented explicitly because this module is
/// also used on non-Linux hosts; it is never silently reported as zero.
pub fn peak_memory_bytes() -> io::Result<Option<u64>> {
    let status = match fs::read_to_string("/proc/self/status") {
        Ok(v) => v,
        Err(e) if e.kind() == io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(e),
    };
    for line in status.lines() {
        if let Some(value) = line.strip_prefix("VmHWM:") {
            let kb = value
                .split_whitespace()
                .next()
                .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "VmHWM has no value"))?
                .parse::<u64>()
                .map_err(|_| {
                    io::Error::new(io::ErrorKind::InvalidData, "VmHWM is not an integer")
                })?;
            return Ok(Some(kb.saturating_mul(1024)));
        }
    }
    Ok(None)
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MeasurementContext<'a> {
    pub measurement_id: &'a str,
    pub parser_revision: &'a str,
    pub snapshot: &'a str,
    pub manifest_id: &'a str,
    pub provider_strata: &'a str,
    pub environment: &'a str,
    pub evidence_anchors: &'a str,
    pub classification: Classification,
}

pub fn measurement_json(ctx: &MeasurementContext<'_>, metrics: &OperationalMetrics) -> String {
    let memory = metrics
        .peak_memory_bytes
        .map_or_else(|| "null".to_string(), |v| v.to_string());
    format!(
        r##"{{"schema":"{METRIC_SCHEMA}","event_id":"NPA-METRIC-20260909-000001","sequence":1,"recorded_at":"2026-09-09T00:00:00Z","measurement_id":"{}","parser_revision":"{}","corpus_snapshot_hash":"{}","manifest_id":"{}","provider_strata":{},"environment":{},"classification":"{}","evidence_anchors":{},"supersedes":null,"metric_family":"operational","metrics":{{"elapsed_ms":{},"peak_memory_bytes":{},"candidate_limit_events":{},"cycle_limit_events":{}}},"raw_text":false,"result":"observed"}}"##,
        ctx.measurement_id,
        ctx.parser_revision,
        ctx.snapshot,
        ctx.manifest_id,
        ctx.provider_strata,
        ctx.environment,
        ctx.classification.as_str(),
        ctx.evidence_anchors,
        metrics.elapsed_ms,
        memory,
        metrics.candidate_limit_events,
        metrics.cycle_limit_events
    )
}

pub fn comparable(
    same_metric_definition: bool,
    same_manifest: bool,
    same_snapshot_or_declared_delta: bool,
    same_classification: bool,
) -> bool {
    same_metric_definition
        && same_manifest
        && same_snapshot_or_declared_delta
        && same_classification
}

/// Incomparability is deliberately never a pass: callers receive the
/// quarantine disposition required by the baseline contract.
pub fn regression_disposition(is_comparable: bool, drift: bool) -> &'static str {
    if !is_comparable {
        "quarantine"
    } else if drift {
        "fail"
    } else {
        "pass"
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RegressionContext<'a> {
    pub event_id: &'a str,
    pub sequence: u64,
    pub recorded_at: &'a str,
    pub parser_revision: &'a str,
    pub snapshot: &'a str,
    pub manifest_id: &'a str,
    pub provider_strata: &'a str,
    pub environment: &'a str,
    pub anchors: &'a str,
    pub baseline_id: &'a str,
    pub candidate_id: &'a str,
    pub delta: &'a str,
    pub is_comparable: bool,
    pub drift: bool,
}

pub fn regression_json(ctx: &RegressionContext<'_>) -> String {
    let comparability = if ctx.is_comparable {
        "comparable"
    } else {
        "incomparable"
    };
    format!(
        r##"{{"schema":"{REGRESSION_SCHEMA}","event_id":"{}","sequence":{},"recorded_at":"{}","parser_revision":"{}","corpus_snapshot_hash":"{}","manifest_id":"{}","provider_strata":{},"environment":{},"evidence_anchors":{},"supersedes":null,"metric_id":"operational","baseline_event_id":"{}","candidate_event_id":"{}","delta":{},"comparability":"{comparability}","disposition":"{}","raw_text":false}}"##,
        ctx.event_id,
        ctx.sequence,
        ctx.recorded_at,
        ctx.parser_revision,
        ctx.snapshot,
        ctx.manifest_id,
        ctx.provider_strata,
        ctx.environment,
        ctx.anchors,
        ctx.baseline_id,
        ctx.candidate_id,
        ctx.delta,
        regression_disposition(ctx.is_comparable, ctx.drift)
    )
}

/// Validate the structural, order-sensitive portion of a ledger without a JSON
/// dependency. It rejects rewrites, gaps, duplicate ids and proxy/exact mixing.
pub fn validate_ledger(text: &str) -> Result<(), String> {
    let mut previous = 0u64;
    let mut ids = std::collections::BTreeSet::new();
    for (line_no, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let sequence = field(line, "sequence")
            .ok_or_else(|| format!("line {} missing sequence", line_no + 1))?
            .parse::<u64>()
            .map_err(|_| "sequence is not integer".to_string())?;
        if sequence != previous + 1 {
            return Err(format!(
                "sequence is not contiguous at line {}",
                line_no + 1
            ));
        }
        previous = sequence;
        let id = field(line, "event_id").ok_or("missing event_id")?;
        if !valid_event_id(id) || !ids.insert(id.to_string()) {
            return Err(format!("invalid or duplicate event_id: {id}"));
        }
        if !line.contains("\"supersedes\":null") && !line.contains("\"supersedes\":\"") {
            return Err("supersedes must be null or a prior event id".into());
        }
        if line.contains("\"supersedes\":\"") {
            let supersedes = field(line, "supersedes").ok_or("malformed supersedes")?;
            if !ids.contains(supersedes) {
                return Err(format!("supersedes future or missing event: {supersedes}"));
            }
        }
        if line.contains("\"classification\":\"proxy\"")
            && line.contains("\"metric_family\":\"exact\"")
        {
            return Err("proxy cannot replace exact metric".into());
        }
    }
    if previous == 0 {
        return Err("ledger is empty".into());
    }
    Ok(())
}
fn field<'a>(line: &'a str, name: &str) -> Option<&'a str> {
    let needle = format!("\"{name}\":");
    let start = line.find(&needle)? + needle.len();
    let rest = &line[start..];
    if let Some(v) = rest.strip_prefix('"') {
        Some(v.split('"').next().unwrap_or(""))
    } else {
        Some(rest.split([',', '}']).next().unwrap_or(""))
    }
}
fn valid_event_id(id: &str) -> bool {
    let p: Vec<_> = id.split('-').collect();
    p.len() == 4
        && p[0] == "NPA"
        && !p[1].is_empty()
        && p[2].len() == 8
        && p[2].chars().all(|c| c.is_ascii_digit())
        && p[3].len() == 6
        && p[3].chars().all(|c| c.is_ascii_digit())
}

pub fn check_file(path: &Path) -> Result<(), String> {
    let text = fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
    validate_ledger(&text)
}

//! Layered, fail-closed quality receipts for C2/C3/C5 evidence.
//! These are measurements, never legal truth or accepted gold.
use std::collections::BTreeMap;

pub const SCHEMA: &str = "npa-quality-receipts/v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LayerCounts {
    pub matched: u64,
    pub missed: u64,
    pub extra: u64,
}
impl LayerCounts {
    pub const fn new(matched: u64, missed: u64, extra: u64) -> Self {
        Self {
            matched,
            missed,
            extra,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QualityReceipt {
    pub evidence_id: String,
    pub family: String,
    pub parser_revision: String,
    pub corpus_snapshot_hash: String,
    pub manifest_id: String,
    pub layers: BTreeMap<String, LayerCounts>,
    pub zero_tolerance: BTreeMap<String, u64>,
    pub human_acceptance: Option<String>,
    pub non_claims: Vec<String>,
}
impl QualityReceipt {
    pub fn validate(&self) -> Result<(), String> {
        if self.evidence_id.trim().is_empty() || self.manifest_id.trim().is_empty() {
            return Err("missing evidence identity".into());
        }
        if !self.corpus_snapshot_hash.starts_with("sha256:") {
            return Err("snapshot must be sha256 pinned".into());
        }
        if self.human_acceptance.is_some() {
            return Err("human acceptance is typed absent for this receipt".into());
        }
        if self.zero_tolerance.values().any(|v| *v != 0) {
            return Err("zero-tolerance counter is non-zero".into());
        }
        Ok(())
    }
}

pub fn render_jsonl(receipts: &[QualityReceipt]) -> Result<String, String> {
    let mut out = String::new();
    for r in receipts {
        r.validate()?;
        let layers = r
            .layers
            .iter()
            .map(|(k, v)| {
                format!(
                    "\"{}\":{{\"matched\":{},\"missed\":{},\"extra\":{}}}",
                    esc(k),
                    v.matched,
                    v.missed,
                    v.extra
                )
            })
            .collect::<Vec<_>>()
            .join(",");
        let zero = r
            .zero_tolerance
            .iter()
            .map(|(k, v)| format!("\"{}\":{}", esc(k), v))
            .collect::<Vec<_>>()
            .join(",");
        let claims = r
            .non_claims
            .iter()
            .map(|x| format!("\"{}\"", esc(x)))
            .collect::<Vec<_>>()
            .join(",");
        out.push_str(&format!("{{\"schema\":\"{}\",\"evidence_id\":\"{}\",\"family\":\"{}\",\"parser_revision\":\"{}\",\"corpus_snapshot_hash\":\"{}\",\"manifest_id\":\"{}\",\"layers\":{{{layers}}},\"zero_tolerance\":{{{zero}}},\"human_acceptance\":null,\"non_claims\":[{claims}]}}\n", SCHEMA, esc(&r.evidence_id), esc(&r.family), esc(&r.parser_revision), esc(&r.corpus_snapshot_hash), esc(&r.manifest_id)));
    }
    Ok(out)
}
fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn zero_tolerance_and_human_absence_are_fail_closed() {
        let mut z = BTreeMap::new();
        z.insert("false_fact_mint".into(), 0);
        let r = QualityReceipt {
            evidence_id: "x".into(),
            family: "c5".into(),
            parser_revision: "r".into(),
            corpus_snapshot_hash: "sha256:x".into(),
            manifest_id: "m".into(),
            layers: BTreeMap::new(),
            zero_tolerance: z,
            human_acceptance: None,
            non_claims: vec!["not validated gold".into()],
        };
        assert!(render_jsonl(&[r]).is_ok());
    }
    #[test]
    fn nonzero_counter_rejected() {
        let mut z = BTreeMap::new();
        z.insert("source_span_loss".into(), 1);
        let r = QualityReceipt {
            evidence_id: "x".into(),
            family: "c5".into(),
            parser_revision: "r".into(),
            corpus_snapshot_hash: "sha256:x".into(),
            manifest_id: "m".into(),
            layers: BTreeMap::new(),
            zero_tolerance: z,
            human_acceptance: None,
            non_claims: vec![],
        };
        assert!(render_jsonl(&[r]).is_err());
    }
}

//! Strict, dependency-free parser for the proposed acceptance contract.
//! The file is YAML-as-data: only the deliberately small schema below is accepted.

use std::{collections::BTreeSet, fs, path::Path};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AcceptanceContract {
    pub schema: String,
    pub lifecycle: String,
    pub contract_version: String,
    pub checks: Vec<AcceptanceCheck>,
    pub non_claims: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AcceptanceCheck {
    pub check_id: String,
    pub mode: CheckMode,
    pub command_template: String,
    pub binding_fields: Vec<String>,
    pub reuse_policy: String,
    pub supersession_policy: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CheckMode {
    Runtime,
    Artifact,
}

impl AcceptanceContract {
    pub fn parse_file(path: impl AsRef<Path>) -> Result<Self, String> {
        let text = fs::read_to_string(path.as_ref()).map_err(|e| format!("read contract: {e}"))?;
        Self::parse_str(&text)
    }

    pub fn parse_str(text: &str) -> Result<Self, String> {
        let mut schema = None;
        let mut lifecycle = None;
        let mut contract_version = None;
        let mut checks = Vec::new();
        let mut non_claims = Vec::new();
        let mut current: Option<AcceptanceCheck> = None;
        let mut section = "root";
        let mut seen_root = BTreeSet::new();
        let mut seen_check = BTreeSet::new();
        for (line_no, raw) in text.lines().enumerate() {
            let line = raw.split('#').next().unwrap_or("").trim_end();
            if line.trim().is_empty() || line.trim() == "---" {
                continue;
            }
            let indent = line.chars().take_while(|c| *c == ' ').count();
            let trimmed = line.trim();
            if indent == 0 {
                if trimmed == "checks:" {
                    if contract_version.is_none() {
                        return Err(format!(
                            "line {}: contract_version must precede checks",
                            line_no + 1
                        ));
                    }
                    section = "checks";
                    continue;
                }
                if trimmed == "non_claims:" {
                    section = "non_claims";
                    continue;
                }
                let (key, value) = split_pair(trimmed, line_no)?;
                if !seen_root.insert(key.to_string()) {
                    return Err(format!("line {}: duplicate root key '{key}'", line_no + 1));
                }
                match key {
                    "schema" => schema = Some(scalar(value, line_no)?),
                    "lifecycle" => lifecycle = Some(scalar(value, line_no)?),
                    "contract_version" => contract_version = Some(scalar(value, line_no)?),
                    _ => return Err(format!("line {}: unknown root key '{key}'", line_no + 1)),
                }
                continue;
            }
            if section == "non_claims" {
                if indent == 2 && trimmed.starts_with("- ") {
                    non_claims.push(scalar(trimmed[2..].trim(), line_no)?);
                } else {
                    return Err(format!("line {}: non_claims must be a list", line_no + 1));
                }
                continue;
            }
            if section != "checks" {
                return Err(format!("line {}: unexpected indentation", line_no + 1));
            }
            if indent == 2 && trimmed == "-" {
                return Err(format!("line {}: empty check", line_no + 1));
            }
            if indent == 2 && trimmed.starts_with("- ") {
                if let Some(c) = current.take() {
                    checks.push(finish(c, &seen_check)?);
                }
                seen_check.clear();
                let pair = trimmed[2..].trim();
                let (key, value) = split_pair(pair, line_no)?;
                if key != "check_id" {
                    return Err(format!(
                        "line {}: check must start with check_id",
                        line_no + 1
                    ));
                }
                let id = scalar(value, line_no)?;
                current = Some(AcceptanceCheck {
                    check_id: id,
                    mode: CheckMode::Runtime,
                    command_template: String::new(),
                    binding_fields: Vec::new(),
                    reuse_policy: String::new(),
                    supersession_policy: String::new(),
                });
                seen_check.insert(key.to_string());
            } else if indent >= 4 {
                let (key, value) = split_pair(trimmed, line_no)?;
                let c = current
                    .as_mut()
                    .ok_or_else(|| format!("line {}: field without check", line_no + 1))?;
                if !seen_check.insert(key.to_string()) {
                    return Err(format!("line {}: duplicate check key '{key}'", line_no + 1));
                }
                match key {
                    "mode" => {
                        c.mode = match scalar(value, line_no)?.as_str() {
                            "runtime" => CheckMode::Runtime,
                            "artifact" => CheckMode::Artifact,
                            other => {
                                return Err(format!("line {}: invalid mode '{other}'", line_no + 1))
                            }
                        }
                    }
                    "command_template" => c.command_template = scalar(value, line_no)?,
                    "binding_fields" => c.binding_fields = list(value, line_no)?,
                    "reuse_policy" => c.reuse_policy = scalar(value, line_no)?,
                    "supersession_policy" => c.supersession_policy = scalar(value, line_no)?,
                    _ => return Err(format!("line {}: unknown check key '{key}'", line_no + 1)),
                }
            } else {
                return Err(format!("line {}: malformed indentation", line_no + 1));
            }
        }
        if let Some(c) = current {
            checks.push(finish(c, &seen_check)?);
        }
        let schema = schema.ok_or("missing schema")?;
        let lifecycle = lifecycle.ok_or("missing lifecycle")?;
        let version = contract_version.ok_or("missing contract_version")?;
        if schema != "npa-acceptance-contract/v1" || version != schema {
            return Err(format!(
                "unsupported contract schema/version '{schema}' '{version}'"
            ));
        }
        if lifecycle != "proposed" {
            return Err(format!("unsupported lifecycle '{lifecycle}'"));
        }
        if checks.is_empty() {
            return Err("checks must not be empty".into());
        }
        Ok(Self {
            schema,
            lifecycle,
            contract_version: version,
            checks,
            non_claims,
        })
    }
}

fn finish(c: AcceptanceCheck, seen: &BTreeSet<String>) -> Result<AcceptanceCheck, String> {
    for key in [
        "mode",
        "command_template",
        "binding_fields",
        "reuse_policy",
        "supersession_policy",
    ] {
        if !seen.contains(key) {
            return Err(format!("check '{}' missing {key}", c.check_id));
        }
    }
    if c.check_id.is_empty() || c.command_template.is_empty() || c.binding_fields.is_empty() {
        return Err(format!("check '{}' has empty required value", c.check_id));
    }
    Ok(c)
}
fn split_pair(line: &str, n: usize) -> Result<(&str, &str), String> {
    line.split_once(':')
        .map(|(k, v)| (k.trim(), v.trim()))
        .ok_or_else(|| format!("line {}: expected key: value", n + 1))
}
fn scalar(value: &str, n: usize) -> Result<String, String> {
    let v = value.trim();
    if v.is_empty() || v.starts_with('[') || v.starts_with('{') {
        return Err(format!("line {}: scalar expected", n + 1));
    }
    Ok(v.trim_matches('"').trim_matches('\'').to_string())
}
fn list(value: &str, n: usize) -> Result<Vec<String>, String> {
    let v = value.trim();
    if !(v.starts_with('[') && v.ends_with(']')) {
        return Err(format!("line {}: inline list expected", n + 1));
    }
    let values = v[1..v.len() - 1]
        .split(',')
        .map(str::trim)
        .filter(|x| !x.is_empty())
        .map(|x| x.trim_matches('"').trim_matches('\'').to_string())
        .collect::<Vec<_>>();
    if values.is_empty() {
        return Err(format!("line {}: binding_fields must not be empty", n + 1));
    }
    Ok(values)
}

#[cfg(test)]
mod tests {
    use super::*;
    const GOOD: &str = "schema: npa-acceptance-contract/v1\nlifecycle: proposed\ncontract_version: npa-acceptance-contract/v1\nchecks:\n  - check_id: c4-live-check\n    mode: runtime\n    command_template: npa-contour-diagnostics --check\n    binding_fields: [parser_revision, inventory_digest, profile, limit, source_revision]\n    reuse_policy: equivalent-retry-preserves-receipt\n    supersession_policy: explicit-from-to-reason-authorization\n";
    #[test]
    fn parses_strict_contract() {
        assert_eq!(
            AcceptanceContract::parse_str(GOOD).unwrap().checks[0].mode,
            CheckMode::Runtime
        );
    }
    #[test]
    fn rejects_unknown_and_duplicate_keys() {
        assert!(
            AcceptanceContract::parse_str(&GOOD.replace("mode: runtime", "wat: runtime")).is_err()
        );
        assert!(AcceptanceContract::parse_str(&GOOD.replace(
            "    mode: runtime\n",
            "    mode: runtime\n    mode: artifact\n"
        ))
        .is_err());
    }
    #[test]
    fn rejects_wrong_version() {
        assert!(AcceptanceContract::parse_str(&GOOD.replace("/v1", "/v2")).is_err());
    }
}

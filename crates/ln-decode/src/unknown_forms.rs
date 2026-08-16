use crate::domain::{fingerprint_bytes, ParagraphStyle, ParsedBlock, TextSpan};
use crate::tokenizer::tokenize;
use std::fmt;

/// Bounded unsupported-form classes discovered outside existing taxonomies.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum UnknownFormKind {
    UnsupportedTemporalNearMiss,
    UnsupportedDeonticNearMiss,
    UnsupportedHierarchyPrefix,
}

/// One unsupported lexical form occurrence in decoded block text.
///
/// This value carries only a decoded `TextSpan`, a kind and a stable lexeme
/// fingerprint. No raw legal text, resolved target, legal interpretation or
/// authority is present.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnknownForm {
    kind: UnknownFormKind,
    span: TextSpan,
    fingerprint: String,
}

impl UnknownForm {
    pub fn kind(&self) -> UnknownFormKind {
        self.kind
    }

    pub fn span(&self) -> TextSpan {
        self.span
    }

    /// Stable FNV-1a fingerprint of the normalized lexeme (see
    /// `domain::fingerprint_bytes`). Diagnostic identity only.
    pub fn fingerprint(&self) -> &str {
        &self.fingerprint
    }
}

/// Aggregate counts of unsupported forms per kind.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct UnknownFormCensus {
    temporal_unsupported: usize,
    deontic_unsupported: usize,
    hierarchy_prefix_unsupported: usize,
}

impl UnknownFormCensus {
    pub fn temporal_unsupported(self) -> usize {
        self.temporal_unsupported
    }

    pub fn deontic_unsupported(self) -> usize {
        self.deontic_unsupported
    }

    pub fn hierarchy_prefix_unsupported(self) -> usize {
        self.hierarchy_prefix_unsupported
    }

    fn from_forms(forms: &[UnknownForm]) -> Self {
        let mut c = Self::default();
        for f in forms {
            match f.kind {
                UnknownFormKind::UnsupportedTemporalNearMiss => c.temporal_unsupported += 1,
                UnknownFormKind::UnsupportedDeonticNearMiss => c.deontic_unsupported += 1,
                UnknownFormKind::UnsupportedHierarchyPrefix => c.hierarchy_prefix_unsupported += 1,
            }
        }
        c
    }
}

const UNSUPPORTED_TEMPORAL: &[&str] = &[
    "вступала",
    "вступало",
    "вступавший",
    "вступающего",
    "вступающему",
    "утрачивал",
    "утрачивавшая",
    "утрачивавший",
    "утрачивающего",
    "утрата",
];

const UNSUPPORTED_DEONTIC: &[&str] = &[
    "нельзя",
    "недопустимо",
    "запретить",
    "запрещение",
    "запрещающий",
    "запрет",
];

const UNSUPPORTED_HIERARCHY: &[&str] = &[
    "подпункт",
    "подпункта",
    "подпункту",
    "подпунктом",
    "подпункте",
    "подпункты",
    "подпунктов",
    "подпунктам",
    "подпунктами",
    "подпунктах",
    "часть",
    "части",
    "частью",
    "частей",
    "частям",
    "частями",
    "частях",
    "параграф",
    "параграфа",
    "параграфу",
    "параграфом",
    "параграфе",
    "параграфы",
    "параграфов",
    "абзац",
    "абзаца",
    "абзацу",
    "абзацем",
    "абзаце",
    "абзацы",
    "абзацев",
];

fn classify_unknown(word: &str) -> Option<UnknownFormKind> {
    if UNSUPPORTED_TEMPORAL.contains(&word) {
        Some(UnknownFormKind::UnsupportedTemporalNearMiss)
    } else if UNSUPPORTED_DEONTIC.contains(&word) {
        Some(UnknownFormKind::UnsupportedDeonticNearMiss)
    } else if UNSUPPORTED_HIERARCHY.contains(&word) {
        Some(UnknownFormKind::UnsupportedHierarchyPrefix)
    } else {
        None
    }
}

/// Collect unsupported lexical forms from raw decoded text.
pub fn collect_unknown_forms_from_text(text: &str) -> Vec<UnknownForm> {
    tokenize(text)
        .into_iter()
        .filter_map(|t| {
            classify_unknown(&t.normalized).map(|kind| UnknownForm {
                kind,
                span: TextSpan::try_new(t.start, t.end)
                    .expect("alphabetic token has a non-empty decoded span"),
                fingerprint: fingerprint_bytes(t.normalized.as_bytes()),
            })
        })
        .collect()
}

/// Build a deterministic unsupported-form census for a parsed block.
///
/// Returns `UnknownFormCensus::default()` for `ProviderComment` blocks.
pub fn census_unknown_forms(block: &ParsedBlock) -> UnknownFormCensus {
    if block.style() == ParagraphStyle::ProviderComment {
        return UnknownFormCensus::default();
    }
    UnknownFormCensus::from_forms(&collect_unknown_forms_from_text(block.text()))
}

// ─── M169 S04 T01: ranked census + YAML patch candidate ─────────────────────
//
// Learning-loop surface (bounded): ranked frequencies of unsupported forms
// across blocks, a fingerprint-only census report, plus a deterministic YAML
// patch candidate a human reviews and applies. Emits lexemes and fingerprint
// ids only — never raw legal prose — and performs no writes: applying a
// candidate is an explicit human/PR action (`apply_patch_candidates`), never
// a runtime mutation.

/// One ranked unsupported-form entry: kind, lexeme fingerprint, lexeme,
/// occurrence count.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RankedUnknownForm {
    kind: UnknownFormKind,
    fingerprint: String,
    token: String,
    count: usize,
}

impl RankedUnknownForm {
    pub fn kind(&self) -> UnknownFormKind {
        self.kind
    }

    /// Stable FNV-1a fingerprint of the normalized lexeme (see
    /// `domain::fingerprint_bytes`). Diagnostic identity only.
    pub fn fingerprint(&self) -> &str {
        &self.fingerprint
    }

    pub fn token(&self) -> &str {
        &self.token
    }

    pub fn count(&self) -> usize {
        self.count
    }
}

fn kind_label(kind: UnknownFormKind) -> &'static str {
    match kind {
        UnknownFormKind::UnsupportedTemporalNearMiss => "UnsupportedTemporalNearMiss",
        UnknownFormKind::UnsupportedDeonticNearMiss => "UnsupportedDeonticNearMiss",
        UnknownFormKind::UnsupportedHierarchyPrefix => "UnsupportedHierarchyPrefix",
    }
}

/// Rank unsupported forms across parsed blocks by occurrence count
/// (descending; ties by lexeme ascending). `ProviderComment` blocks are
/// excluded. Deterministic; carries no block text beyond the lexemes.
pub fn rank_unknown_forms(blocks: &[ParsedBlock]) -> Vec<RankedUnknownForm> {
    use std::collections::BTreeMap;
    let mut counts: BTreeMap<(UnknownFormKind, String), (String, usize)> = BTreeMap::new();
    for block in blocks {
        if block.style() == ParagraphStyle::ProviderComment {
            continue;
        }
        for form in collect_unknown_forms_from_text(block.text()) {
            let span = form.span();
            let token = block.text()[span.start()..span.end()].trim().to_lowercase();
            let entry = counts
                .entry((form.kind(), form.fingerprint().to_owned()))
                .or_insert_with(|| (token, 0));
            entry.1 += 1;
        }
    }
    let mut ranked: Vec<RankedUnknownForm> = counts
        .into_iter()
        .map(|((kind, fingerprint), (token, count))| RankedUnknownForm {
            kind,
            fingerprint,
            token,
            count,
        })
        .collect();
    ranked.sort_by(|a, b| b.count.cmp(&a.count).then_with(|| a.token.cmp(&b.token)));
    ranked
}

/// Render a deterministic YAML patch-candidate block for human review.
///
/// Lines list `kind`, lexeme `token` and `count`. This is a proposal for a
/// tracked dictionary change; nothing is applied at runtime.
pub fn render_yaml_patch_candidates(ranked: &[RankedUnknownForm]) -> String {
    let mut out = String::from("# ranked unknown-form candidates (human review required)\n");
    if ranked.is_empty() {
        out.push_str("(none)\n");
        return out;
    }
    for r in ranked {
        out.push_str(&format!(
            "- {{kind: {}, token: {}, count: {}}}\n",
            kind_label(r.kind),
            r.token,
            r.count
        ));
    }
    out
}

/// Render a deterministic ranked census report: fingerprint ids and counts
/// only — no lexemes and no raw legal text. Companion to the human-oriented
/// YAML patch candidate: the report is the stable machine-readable identity
/// view, the YAML candidate is the human-editable dictionary proposal.
pub fn render_ranked_census_report(ranked: &[RankedUnknownForm]) -> String {
    let mut out = String::from("# ranked unknown-form census (fingerprint ids, no text)\n");
    if ranked.is_empty() {
        out.push_str("(none)\n");
        return out;
    }
    for r in ranked {
        out.push_str(&format!(
            "- {{kind: {}, fingerprint: {}, count: {}}}\n",
            kind_label(r.kind),
            r.fingerprint,
            r.count
        ));
    }
    out
}

/// A validated set of applied patch candidates.
///
/// Holds `(kind, fingerprint)` pairs only — never raw lexemes — so the
/// exclusion set carries no legal text. Deterministic and immutable once
/// built; produced by `apply_patch_candidates`.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct AppliedPatch {
    candidates: std::collections::BTreeSet<(UnknownFormKind, String)>,
}

impl AppliedPatch {
    pub fn len(&self) -> usize {
        self.candidates.len()
    }

    pub fn is_empty(&self) -> bool {
        self.candidates.is_empty()
    }

    /// Whether this patch covers the given (kind, fingerprint) form.
    pub fn covers(&self, kind: UnknownFormKind, fingerprint: &str) -> bool {
        self.candidates.contains(&(kind, fingerprint.to_owned()))
    }

    /// Collect unknown forms, excluding lexemes covered by this applied patch.
    ///
    /// This is the "census after apply" surface: after a human approves and
    /// applies a candidate, the census for those forms drops to zero.
    pub fn collect_unknown_forms(&self, text: &str) -> Vec<UnknownForm> {
        collect_unknown_forms_from_text(text)
            .into_iter()
            .filter(|f| !self.covers(f.kind(), f.fingerprint()))
            .collect()
    }

    /// Rank unknown forms across blocks, excluding applied-patch lexemes.
    pub fn rank_unknown_forms(&self, blocks: &[ParsedBlock]) -> Vec<RankedUnknownForm> {
        rank_unknown_forms(blocks)
            .into_iter()
            .filter(|r| !self.covers(r.kind(), r.fingerprint()))
            .collect()
    }
}

/// Parse a YAML patch-candidate block (as rendered by
/// `render_yaml_patch_candidates`, possibly hand-edited) into an
/// [`AppliedPatch`].
///
/// This is the explicit human-driven apply step: the runtime never
/// auto-applies; a human reviews the rendered candidates and this function
/// turns the approved lines into the exclusion set used by later census
/// runs. Malformed lines are rejected — never silently skipped — and every
/// token is re-fingerprinted from the approved lexeme.
pub fn apply_patch_candidates(yaml: &str) -> Result<AppliedPatch, PatchParseError> {
    use std::collections::BTreeSet;
    let mut candidates = BTreeSet::new();
    for (idx, raw_line) in yaml.lines().enumerate() {
        let line_number = idx + 1;
        let line = raw_line.trim();
        if line.is_empty() || line.starts_with('#') || line == "(none)" {
            continue;
        }
        let inner = line
            .strip_prefix("- {")
            .and_then(|rest| rest.strip_suffix('}'))
            .ok_or_else(|| PatchParseError::MalformedLine {
                line_number,
                line: line.to_owned(),
            })?;
        let mut kind: Option<UnknownFormKind> = None;
        let mut token: Option<String> = None;
        let mut has_count = false;
        for field in inner.split(',') {
            let field = field.trim();
            if let Some(label) = field.strip_prefix("kind:") {
                let label = label.trim();
                kind = Some(match label {
                    "UnsupportedTemporalNearMiss" => UnknownFormKind::UnsupportedTemporalNearMiss,
                    "UnsupportedDeonticNearMiss" => UnknownFormKind::UnsupportedDeonticNearMiss,
                    "UnsupportedHierarchyPrefix" => UnknownFormKind::UnsupportedHierarchyPrefix,
                    other => {
                        return Err(PatchParseError::UnknownKind {
                            label: other.to_owned(),
                            line_number,
                        })
                    }
                });
            } else if let Some(value) = field.strip_prefix("token:") {
                let value = value.trim();
                if value.is_empty() || !value.chars().all(|c| c.is_alphabetic()) {
                    return Err(PatchParseError::InvalidToken {
                        token: value.to_owned(),
                        line_number,
                    });
                }
                token = Some(value.to_owned());
            } else if let Some(value) = field.strip_prefix("count:") {
                value
                    .trim()
                    .parse::<usize>()
                    .map_err(|_| PatchParseError::InvalidCount {
                        token: value.trim().to_owned(),
                        line_number,
                    })?;
                has_count = true;
            } else {
                return Err(PatchParseError::MalformedLine {
                    line_number,
                    line: line.to_owned(),
                });
            }
        }
        let (kind, token) = match (kind, token) {
            (Some(kind), Some(token)) => (kind, token),
            _ => {
                return Err(PatchParseError::MalformedLine {
                    line_number,
                    line: line.to_owned(),
                })
            }
        };
        if !has_count {
            return Err(PatchParseError::MalformedLine {
                line_number,
                line: line.to_owned(),
            });
        }
        candidates.insert((kind, fingerprint_bytes(token.as_bytes())));
    }
    Ok(AppliedPatch { candidates })
}

/// Errors produced while parsing a YAML patch candidate.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PatchParseError {
    /// A line that is not a comment, `(none)` or a valid `- {kind, token,
    /// count}` flow mapping.
    MalformedLine { line_number: usize, line: String },
    /// Unknown `kind:` label (must be one of the three closed kinds).
    UnknownKind { label: String, line_number: usize },
    /// `token:` is empty or contains a non-alphabetic character (the
    /// tokenizer contract that keeps the YAML render injection-free).
    InvalidToken { token: String, line_number: usize },
    /// `count:` does not parse as a `usize`.
    InvalidCount { token: String, line_number: usize },
}

impl fmt::Display for PatchParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MalformedLine { line_number, line } => {
                write!(f, "malformed patch line {line_number}: {line:?}")
            }
            Self::UnknownKind { label, line_number } => {
                write!(f, "unknown kind label {label:?} on line {line_number}")
            }
            Self::InvalidToken { token, line_number } => write!(
                f,
                "invalid token {token:?} on line {line_number}: alphabetic lexeme required"
            ),
            Self::InvalidCount { token, line_number } => {
                write!(
                    f,
                    "invalid count {token:?} on line {line_number}: usize required"
                )
            }
        }
    }
}

impl std::error::Error for PatchParseError {}

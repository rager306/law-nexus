//! Export-bank → normativity closed vocabulary for the consultant corpus
//! (ADR-0030 D2).
//!
//! `document_groups` owns the *structural* axis (which group a path binds to);
//! this module owns the *principal* axis: which export bank a manifest path
//! belongs to and whether that bank is normative law or non-normative practice.
//! The two axes are deliberately separate (D667): an unresolved structural
//! group is *not* evidence of legal non-normativity, and an unknown bank is a
//! structural quarantine, not a silent default.
//!
//! A bank here is the export bucket, i.e. the first `/`-separated component of
//! a manifest `relative_path` — the same convention already used by S02
//! (`anchor_coverage::bank_of`) and S03 (`key_unresolved_by_bank`). It is not a
//! catalog legal bank (`fld`) and it is never derived from an absolute path.
//!
//! The mapping is closed and fail-visible (ADR-0030 D2, D667):
//! - `courts`, `fas` → [`BankNormativity::NonNormative`] (practice/control);
//! - `npa`, `xml` → [`BankNormativity::Normative`];
//! - anything else (including empty/whitespace and catalog-only banks such as
//!   `ARB`) → [`BankNormativity::Unknown`], never a silent default.
//!
//! The module is stdlib-only and carries no I/O.

use std::fmt;

/// Normativity class of an export bank.
///
/// Stable lowercase strings (see [`BankNormativity::as_str`]) are the artifact
/// contract; variants are exhaustive so a new class cannot be added silently.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum BankNormativity {
    /// Normative law banks (`npa`, `xml`).
    Normative,
    /// Non-normative practice/control banks (`courts`, `fas`).
    NonNormative,
    /// Fail-closed structural quarantine for an unrecognized bank.
    Unknown,
}

impl BankNormativity {
    /// Stable string used by coverage artifacts and diagnostics.
    pub fn as_str(&self) -> &'static str {
        match self {
            BankNormativity::Normative => "normative",
            BankNormativity::NonNormative => "non-normative",
            BankNormativity::Unknown => "unknown",
        }
    }
}

impl fmt::Display for BankNormativity {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

/// The four known export banks of the consultant corpus, in canonical order.
pub const KNOWN_BANKS: [&str; 4] = ["courts", "fas", "npa", "xml"];

/// The bank of a manifest path: its first `/`-separated component.
///
/// Mirrors `ln_consultant_parser::anchor_coverage::bank_of` (S02). An empty or
/// slash-less path is returned as-is (never mapped to a default bank).
pub fn bank_of(relative_path: &str) -> &str {
    relative_path.split('/').next().unwrap_or(relative_path)
}

/// Closed bank → normativity mapping (ADR-0030 D2).
///
/// The bank is trimmed and ASCII-lowercased before matching. Any value outside
/// the closed set — including `""`, whitespace-only, and catalog-only banks
/// such as `ARB` — yields [`BankNormativity::Unknown`] (fail-closed).
pub fn bank_normativity(bank: &str) -> BankNormativity {
    match bank.trim().to_ascii_lowercase().as_str() {
        "courts" | "fas" => BankNormativity::NonNormative,
        "npa" | "xml" => BankNormativity::Normative,
        _ => BankNormativity::Unknown,
    }
}

/// Whether the assembly CTV stage must be blocked for a bank class.
///
/// Only [`BankNormativity::NonNormative`] blocks CTV (practice text is not a
/// structural AST, ADR-0020). `Unknown` deliberately does **not** block: a
/// structural quarantine (e.g. an unrecognized fixture path such as
/// `law-source/consultant/...`) is not a legal non-normativity claim
/// (DP2/D667), and folding it in would regress those normative fixture paths.
pub fn ctv_blocked_by_bank(normativity: BankNormativity) -> bool {
    matches!(normativity, BankNormativity::NonNormative)
}

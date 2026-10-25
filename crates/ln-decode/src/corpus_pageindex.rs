//! Corpus page index: address the corpus by `(bank, document_key, para)`
//! (M224/S03/T01, ADR-0030 D1/D5).
//!
//! The catalog addresses corpus documents in the *legal-identity* key space —
//! `(bank, document_key)` — never by filesystem path. A document may also carry
//! one exact offline token (`consultantplus://offline/ref=…`), which law-nexus
//! cannot decode; the sanctioned join is an **exact-token match**, byte-exact,
//! with no decoding and no normalization.
//!
//! Paragraph addressing is a *consumer* interpretation of the anchor `para`
//! field: `para == 4294967295` ([`WHOLE_DOCUMENT_PARA`]) means the whole
//! document, every other value is an ordinary paragraph number. The anchor
//! token is never rewritten — reading a scope does not mutate identity.
//!
//! This module owns addressing and scope semantics only. It mints no JSONL
//! artifact (S03/T02–T03), performs no catalog join (S03/T02), and resolves no
//! paragraph *extent* (S05). A query that cannot be answered returns a closed
//! typed [`PageIndexMiss`]; a path-like key is refused at build time and can
//! never become a hit at query time. Stdlib only: no `rusqlite`, no serde.

use std::collections::BTreeMap;
use std::error::Error;
use std::fmt;

use crate::consultant_uri_anchor::ConsultantUriAnchor;

/// The sentinel `para` that denotes the whole document.
///
/// Retained as an ordinary [`u64`] here; `WholeDocument` is a *scope* reading,
/// not a rewrite of the anchor.
pub const WHOLE_DOCUMENT_PARA: u64 = 4_294_967_295;

/// Maximum characters retained in a [`PageIndexRefusal`] detail. Mirrors the
/// bounded-detail discipline of `consultant_uri_anchor`.
const MAX_DETAIL_CHARS: usize = 240;

/// A corpus document address in the catalog key space: `(bank, document_key)`.
///
/// `bank` is the catalog bank token as-is (for example `LAW`, `ARB`); it is
/// **not** a path and **not** the internal URI `fld` field.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct PageIndexKey {
    /// Catalog bank token, verbatim.
    pub bank: String,
    /// Decimal document key within the bank, verbatim.
    pub document_key: String,
}

impl PageIndexKey {
    /// Construct an address key.
    pub fn new(bank: impl Into<String>, document_key: impl Into<String>) -> Self {
        Self {
            bank: bank.into(),
            document_key: document_key.into(),
        }
    }
}

/// The scope a resolved hit addresses.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DocumentScope {
    /// A single paragraph (`para != WHOLE_DOCUMENT_PARA`).
    Paragraph(u64),
    /// The whole document (`para == WHOLE_DOCUMENT_PARA`).
    WholeDocument,
}

impl DocumentScope {
    /// Read the scope of a raw `para` field: the sentinel maps to
    /// [`DocumentScope::WholeDocument`], every other value to
    /// [`DocumentScope::Paragraph`].
    pub const fn from_para(para: u64) -> Self {
        if para == WHOLE_DOCUMENT_PARA {
            Self::WholeDocument
        } else {
            Self::Paragraph(para)
        }
    }

    /// Stable machine-readable identifier of the scope.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Paragraph(_) => "paragraph",
            Self::WholeDocument => "whole_document",
        }
    }

    /// The whole-document branch predicate.
    pub const fn is_whole_document(self) -> bool {
        matches!(self, Self::WholeDocument)
    }
}

/// One indexed corpus document.
///
/// `relative_path` is the document's identity (the manifest key), **not** a
/// resolution key — queries never resolve by path. `offline_token`, when
/// present, is stored byte-exact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PageIndexEntry {
    /// Catalog bank token.
    pub bank: String,
    /// Decimal document key within the bank.
    pub document_key: String,
    /// Corpus-relative path: document identity, not a query key.
    pub relative_path: String,
    /// The document's offline token, byte-exact, or `None`.
    pub offline_token: Option<String>,
}

/// Closed refusal vocabulary of [`CorpusPageIndex::build`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PageIndexRefusalKind {
    /// The entry `bank` was empty.
    EmptyBank,
    /// The entry `document_key` was empty.
    EmptyDocumentKey,
    /// The entry `bank`/`document_key` was path-like (contains `/` or `\`).
    PathLikeKey,
    /// The entry `relative_path` was empty.
    EmptyRelativePath,
    /// Two entries shared the same `(bank, document_key)` address.
    DuplicateKey,
}

impl PageIndexRefusalKind {
    /// Stable machine-readable identifier of the refusal kind.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::EmptyBank => "empty_bank",
            Self::EmptyDocumentKey => "empty_document_key",
            Self::PathLikeKey => "path_like_key",
            Self::EmptyRelativePath => "empty_relative_path",
            Self::DuplicateKey => "duplicate_key",
        }
    }
}

/// A typed, bounded build refusal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PageIndexRefusal {
    kind: PageIndexRefusalKind,
    detail: String,
}

impl PageIndexRefusal {
    /// Build a refusal, bounding the detail to [`MAX_DETAIL_CHARS`] characters
    /// and dropping control characters.
    pub fn new(kind: PageIndexRefusalKind, detail: impl Into<String>) -> Self {
        Self {
            kind,
            detail: bound_detail(detail.into()),
        }
    }

    /// The refusal kind.
    pub fn kind(&self) -> PageIndexRefusalKind {
        self.kind
    }

    /// The bounded human-readable detail.
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for PageIndexRefusal {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "corpus page index refused ({}): {}",
            self.kind.as_str(),
            self.detail
        )
    }
}

impl Error for PageIndexRefusal {}

/// Closed miss vocabulary of the resolver.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PageIndexMissKind {
    /// The `(bank, document_key)` address is absent from the index.
    AddressNotInIndex,
    /// The offline token is absent from the index (exact-token miss).
    OfflineTokenNotInIndex,
    /// The query key was path-like and can never resolve.
    PathLikeQuery,
    /// The anchor is of a shape the resolver does not address.
    UnknownAnchor,
}

impl PageIndexMissKind {
    /// Stable machine-readable identifier of the miss kind.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::AddressNotInIndex => "address_not_in_index",
            Self::OfflineTokenNotInIndex => "offline_token_not_in_index",
            Self::PathLikeQuery => "path_like_query",
            Self::UnknownAnchor => "unknown_anchor",
        }
    }
}

/// A typed resolver miss.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct PageIndexMiss {
    /// Why the query did not resolve.
    pub kind: PageIndexMissKind,
}

impl PageIndexMiss {
    /// Construct a miss of the given kind.
    pub const fn new(kind: PageIndexMissKind) -> Self {
        Self { kind }
    }
}

impl fmt::Display for PageIndexMiss {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.kind.as_str())
    }
}

/// A resolved corpus document address.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PageIndexHit {
    /// Corpus-relative path of the resolved document.
    pub relative_path: String,
    /// The document's offline token, byte-exact, or `None`.
    pub offline_token: Option<String>,
    /// The addressed scope (paragraph or whole document).
    pub scope: DocumentScope,
}

/// The closed outcome of a pageindex query.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PageIndexResolution {
    /// The query resolved to a corpus document address.
    Hit(PageIndexHit),
    /// The query did not resolve.
    Miss(PageIndexMiss),
}

impl PageIndexResolution {
    /// Borrow the hit, if any.
    pub fn hit(&self) -> Option<&PageIndexHit> {
        match self {
            Self::Hit(hit) => Some(hit),
            Self::Miss(_) => None,
        }
    }

    /// Whether the query resolved.
    pub fn is_hit(&self) -> bool {
        matches!(self, Self::Hit(_))
    }
}

/// An in-memory corpus page index keyed by legal identity.
///
/// Two deterministic `BTreeMap`s back the resolver: `(bank, document_key) →
/// entry` for address queries and `offline_token → (bank, document_key)` for
/// exact-token queries (byte-exact, no decoding).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CorpusPageIndex {
    by_key: BTreeMap<(String, String), PageIndexEntry>,
    by_token: BTreeMap<String, (String, String)>,
}

impl CorpusPageIndex {
    /// Build the index from entries, fail-closed.
    ///
    /// Refuses an empty `bank`, empty `document_key`, path-like `bank`/
    /// `document_key`, an empty `relative_path`, or a duplicate address. A
    /// duplicate offline token keeps the first-seen deterministic mapping.
    pub fn build(entries: &[PageIndexEntry]) -> Result<Self, PageIndexRefusal> {
        let mut by_key: BTreeMap<(String, String), PageIndexEntry> = BTreeMap::new();
        let mut by_token: BTreeMap<String, (String, String)> = BTreeMap::new();
        for entry in entries {
            if entry.bank.is_empty() {
                return Err(PageIndexRefusal::new(
                    PageIndexRefusalKind::EmptyBank,
                    "pageindex entry has an empty bank",
                ));
            }
            if entry.document_key.is_empty() {
                return Err(PageIndexRefusal::new(
                    PageIndexRefusalKind::EmptyDocumentKey,
                    "pageindex entry has an empty document_key",
                ));
            }
            if is_path_like(&entry.bank) || is_path_like(&entry.document_key) {
                return Err(PageIndexRefusal::new(
                    PageIndexRefusalKind::PathLikeKey,
                    "pageindex entry key is path-like",
                ));
            }
            if entry.relative_path.is_empty() {
                return Err(PageIndexRefusal::new(
                    PageIndexRefusalKind::EmptyRelativePath,
                    "pageindex entry has an empty relative_path",
                ));
            }
            let key = (entry.bank.clone(), entry.document_key.clone());
            if by_key.contains_key(&key) {
                return Err(PageIndexRefusal::new(
                    PageIndexRefusalKind::DuplicateKey,
                    "pageindex entry duplicates an existing (bank, document_key)",
                ));
            }
            if let Some(token) = &entry.offline_token {
                // Byte-exact token: `String` equality/ordering are byte-wise.
                by_token.entry(token.clone()).or_insert_with(|| key.clone());
            }
            by_key.insert(key, entry.clone());
        }
        Ok(Self { by_key, by_token })
    }

    /// Number of indexed documents.
    pub fn len(&self) -> usize {
        self.by_key.len()
    }

    /// Whether the index holds no documents.
    pub fn is_empty(&self) -> bool {
        self.by_key.is_empty()
    }

    /// Documents per catalog bank, deterministic by bank token.
    pub fn key_bank_counts(&self) -> BTreeMap<String, usize> {
        let mut counts: BTreeMap<String, usize> = BTreeMap::new();
        for (bank, _) in self.by_key.keys() {
            *counts.entry(bank.clone()).or_insert(0) += 1;
        }
        counts
    }

    /// All indexed addresses, deterministic key order.
    pub fn keys(&self) -> impl Iterator<Item = PageIndexKey> + '_ {
        self.by_key.keys().map(|(bank, document_key)| PageIndexKey {
            bank: bank.clone(),
            document_key: document_key.clone(),
        })
    }

    /// Resolve an address `(bank, document_key, para)`.
    ///
    /// A path-like `bank`/`document_key` always yields
    /// [`PageIndexMissKind::PathLikeQuery`] — a path can never become a hit.
    /// The `para` only selects the scope; the token is never rewritten.
    pub fn resolve_key(&self, bank: &str, document_key: &str, para: u64) -> PageIndexResolution {
        if is_path_like(bank) || is_path_like(document_key) {
            return PageIndexResolution::Miss(PageIndexMiss::new(PageIndexMissKind::PathLikeQuery));
        }
        match self.by_key.get(&(bank.to_owned(), document_key.to_owned())) {
            Some(entry) => PageIndexResolution::Hit(PageIndexHit {
                relative_path: entry.relative_path.clone(),
                offline_token: entry.offline_token.clone(),
                scope: DocumentScope::from_para(para),
            }),
            None => {
                PageIndexResolution::Miss(PageIndexMiss::new(PageIndexMissKind::AddressNotInIndex))
            }
        }
    }

    /// Resolve an offline token by exact-token match (byte-exact, no decoding).
    ///
    /// A token addresses the whole document, so a hit always carries
    /// [`DocumentScope::WholeDocument`].
    pub fn resolve_offline_token(&self, token: &str) -> PageIndexResolution {
        match self.by_token.get(token) {
            Some(key) => {
                let entry = self
                    .by_key
                    .get(key)
                    .expect("token index is derived from the key index");
                PageIndexResolution::Hit(PageIndexHit {
                    relative_path: entry.relative_path.clone(),
                    offline_token: entry.offline_token.clone(),
                    scope: DocumentScope::WholeDocument,
                })
            }
            None => PageIndexResolution::Miss(PageIndexMiss::new(
                PageIndexMissKind::OfflineTokenNotInIndex,
            )),
        }
    }

    /// Resolve a parsed Consultant URI anchor.
    ///
    /// `Offline` anchors resolve by exact token; `Internal` anchors resolve by
    /// their `(bank, document_key, para)` address. The anchor is never
    /// rewritten.
    pub fn resolve_anchor(&self, anchor: &ConsultantUriAnchor) -> PageIndexResolution {
        match anchor {
            ConsultantUriAnchor::Offline { token } => self.resolve_offline_token(token),
            ConsultantUriAnchor::Internal {
                bank,
                document_key,
                para,
                ..
            } => self.resolve_key(bank, document_key, *para),
        }
    }
}

/// A path-like key contains a `/` or `\` separator and is never a legal
/// identity address.
fn is_path_like(value: &str) -> bool {
    value.contains('/') || value.contains('\\')
}

fn bound_detail(raw: String) -> String {
    let mut out = String::new();
    for ch in raw.chars() {
        if ch.is_control() {
            continue;
        }
        if out.chars().count() >= MAX_DETAIL_CHARS {
            break;
        }
        out.push(ch);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn entry(bank: &str, key: &str, path: &str, token: Option<&str>) -> PageIndexEntry {
        PageIndexEntry {
            bank: bank.to_owned(),
            document_key: key.to_owned(),
            relative_path: path.to_owned(),
            offline_token: token.map(str::to_owned),
        }
    }

    #[test]
    fn whole_document_para_reads_as_scope_without_rewrite() {
        assert_eq!(
            DocumentScope::from_para(WHOLE_DOCUMENT_PARA),
            DocumentScope::WholeDocument
        );
        assert_eq!(DocumentScope::from_para(1), DocumentScope::Paragraph(1));
        let index =
            CorpusPageIndex::build(&[entry("LAW", "12345", "exports/x.xml", None)]).unwrap();
        let resolution = index.resolve_key("LAW", "12345", WHOLE_DOCUMENT_PARA);
        match resolution {
            PageIndexResolution::Hit(hit) => {
                assert_eq!(hit.scope, DocumentScope::WholeDocument);
                assert_eq!(hit.relative_path, "exports/x.xml");
            }
            other => panic!("expected whole-document hit, got {other:?}"),
        }
    }

    #[test]
    fn offline_token_matches_byte_exact_and_keeps_case() {
        let token = "consultantplus://offline/ref=AbCdEf0123";
        let index =
            CorpusPageIndex::build(&[entry("LAW", "1", "exports/a.xml", Some(token))]).unwrap();
        assert!(index.resolve_offline_token(token).is_hit());
        if let PageIndexResolution::Hit(hit) = index.resolve_offline_token(token) {
            assert_eq!(hit.offline_token.as_deref(), Some(token));
            assert_eq!(hit.scope, DocumentScope::WholeDocument);
        }
        // A case-folded or decoded variant is a different token.
        assert!(matches!(
            index.resolve_offline_token("consultantplus://offline/ref=abcdef0123"),
            PageIndexResolution::Miss(PageIndexMiss {
                kind: PageIndexMissKind::OfflineTokenNotInIndex
            })
        ));
    }
}

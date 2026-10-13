//! Contract suite for the corpus page index (M224/S03/T01, ADR-0030 D1/D5).
//!
//! Asserts `(bank, document_key, para)` addressing, the whole-document scope
//! sentinel, byte-exact offline-token join, the closed refusal/miss
//! vocabulary, and the invariant that a path can never resolve. No decoding,
//! no normalization, no file-path resolution.

use ln_decode::consultant_uri_anchor::ConsultantUriAnchor;
use ln_decode::corpus_pageindex::{
    CorpusPageIndex, DocumentScope, PageIndexEntry, PageIndexMiss, PageIndexMissKind,
    PageIndexRefusal, PageIndexRefusalKind, PageIndexResolution, WHOLE_DOCUMENT_PARA,
};

/// A real offline token: uppercase hex body with a mixed-case tail (`a4RCK`).
const OFFLINE_TOKEN: &str = "consultantplus://offline/ref=235B1A968E4D59A97657E85BD86F6A71B8663B3F47605928A0B816F3C818983C064F496A1349154AB2FDE3A7CC220A36DABFB0FC2Ea4RCK";

fn entry(bank: &str, key: &str, path: &str, token: Option<&str>) -> PageIndexEntry {
    PageIndexEntry {
        bank: bank.to_owned(),
        document_key: key.to_owned(),
        relative_path: path.to_owned(),
        offline_token: token.map(str::to_owned),
    }
}

fn fixture() -> CorpusPageIndex {
    CorpusPageIndex::build(&[
        entry("LAW", "12345", "exports/xml/1.xml", None),
        entry("LAW", "777", "exports/npa/2.xml", Some(OFFLINE_TOKEN)),
        entry("ARB", "2973294", "exports/courts/3.xml", None),
        // Internal anchors carry the URI `fld` (digits) as their bank field.
        entry("134", "12345", "exports/xml/internal.xml", None),
    ])
    .expect("fixture index builds")
}

fn refusal_kind(entry: PageIndexEntry) -> PageIndexRefusalKind {
    CorpusPageIndex::build(&[entry])
        .err()
        .unwrap_or_else(|| panic!("expected a build refusal"))
        .kind()
}

fn miss_kind(resolution: PageIndexResolution) -> PageIndexMissKind {
    match resolution {
        PageIndexResolution::Miss(PageIndexMiss { kind }) => kind,
        other => panic!("expected a miss, got {other:?}"),
    }
}

// ---------------------------------------------------------- scope semantics #

#[test]
fn whole_document_para_resolves_to_whole_document_scope() {
    let index = fixture();
    let resolution = index.resolve_key("LAW", "12345", WHOLE_DOCUMENT_PARA);
    match resolution {
        PageIndexResolution::Hit(hit) => {
            assert_eq!(hit.scope, DocumentScope::WholeDocument);
            assert_eq!(hit.relative_path, "exports/xml/1.xml");
            assert_eq!(hit.offline_token, None);
        }
        other => panic!("expected whole-document hit, got {other:?}"),
    }
    // The sentinel is read as a scope, never mixed with a real paragraph.
    assert_ne!(
        DocumentScope::from_para(WHOLE_DOCUMENT_PARA),
        DocumentScope::from_para(1)
    );
    assert_eq!(
        DocumentScope::from_para(1_000_000),
        DocumentScope::Paragraph(1_000_000)
    );
}

#[test]
fn paragraph_para_resolves_to_paragraph_scope() {
    let index = fixture();
    match index.resolve_key("LAW", "12345", 7) {
        PageIndexResolution::Hit(hit) => {
            assert_eq!(hit.scope, DocumentScope::Paragraph(7));
            // The document's own offline token is carried, not rewritten.
            assert_eq!(hit.relative_path, "exports/xml/1.xml");
        }
        other => panic!("expected paragraph hit, got {other:?}"),
    }
}

#[test]
fn whole_document_hit_preserves_the_carried_token() {
    let index = fixture();
    match index.resolve_key("LAW", "777", WHOLE_DOCUMENT_PARA) {
        PageIndexResolution::Hit(hit) => {
            // Scope is a consumer reading; the anchor token bytes are intact.
            assert_eq!(hit.scope, DocumentScope::WholeDocument);
            assert_eq!(hit.offline_token.as_deref(), Some(OFFLINE_TOKEN));
            assert_eq!(
                hit.offline_token.as_deref().unwrap().as_bytes(),
                OFFLINE_TOKEN.as_bytes()
            );
        }
        other => panic!("expected whole-document hit, got {other:?}"),
    }
}

// ---------------------------------------------------------------- address #

#[test]
fn unknown_address_is_address_not_in_index() {
    let index = fixture();
    assert_eq!(
        miss_kind(index.resolve_key("LAW", "999999", 1)),
        PageIndexMissKind::AddressNotInIndex
    );
    assert_eq!(
        miss_kind(index.resolve_key("NO_SUCH_BANK", "1", 1)),
        PageIndexMissKind::AddressNotInIndex
    );
}

// ------------------------------------------------------- path never wins #

#[test]
fn path_like_entry_key_is_refused_at_build() {
    assert_eq!(
        refusal_kind(entry("exports/xml", "1", "p", None)),
        PageIndexRefusalKind::PathLikeKey
    );
    assert_eq!(
        refusal_kind(entry("LAW", "x\\y", "p", None)),
        PageIndexRefusalKind::PathLikeKey
    );
}

#[test]
fn path_like_query_is_a_miss_never_a_hit() {
    let index = fixture();
    // A manifest path used as a key can never resolve to a document.
    assert_eq!(
        miss_kind(index.resolve_key("exports/xml/1.xml", "", 1)),
        PageIndexMissKind::PathLikeQuery
    );
    assert_eq!(
        miss_kind(index.resolve_key("", "exports/xml/1.xml", 1)),
        PageIndexMissKind::PathLikeQuery
    );
    // Even for an address that exists under its legal key.
    assert!(!index.resolve_key("LAW", "exports/xml/1.xml", 1).is_hit());
}

// ------------------------------------------------------------- refusals #

#[test]
fn empty_components_are_refused() {
    assert_eq!(
        refusal_kind(entry("", "1", "p", None)),
        PageIndexRefusalKind::EmptyBank
    );
    assert_eq!(
        refusal_kind(entry("LAW", "", "p", None)),
        PageIndexRefusalKind::EmptyDocumentKey
    );
    assert_eq!(
        refusal_kind(entry("LAW", "1", "", None)),
        PageIndexRefusalKind::EmptyRelativePath
    );
}

#[test]
fn duplicate_address_is_refused() {
    let result =
        CorpusPageIndex::build(&[entry("LAW", "1", "a", None), entry("LAW", "1", "b", None)]);
    let refusal: PageIndexRefusal = result.expect_err("duplicate address refused");
    assert_eq!(refusal.kind(), PageIndexRefusalKind::DuplicateKey);
    assert!(!refusal.detail().is_empty());
    assert!(refusal.detail().chars().count() <= 240);
}

#[test]
fn refusal_kind_strings_are_stable() {
    assert_eq!(PageIndexRefusalKind::EmptyBank.as_str(), "empty_bank");
    assert_eq!(PageIndexRefusalKind::PathLikeKey.as_str(), "path_like_key");
    assert_eq!(PageIndexRefusalKind::DuplicateKey.as_str(), "duplicate_key");
    assert_eq!(PageIndexMissKind::PathLikeQuery.as_str(), "path_like_query");
    assert_eq!(
        PageIndexMissKind::OfflineTokenNotInIndex.as_str(),
        "offline_token_not_in_index"
    );
}

// ---------------------------------------------------- offline exact token #

#[test]
fn offline_token_matches_byte_exact_and_keeps_case() {
    let index = fixture();
    match index.resolve_offline_token(OFFLINE_TOKEN) {
        PageIndexResolution::Hit(hit) => {
            assert_eq!(hit.relative_path, "exports/npa/2.xml");
            assert_eq!(hit.offline_token.as_deref(), Some(OFFLINE_TOKEN));
            assert_eq!(hit.scope, DocumentScope::WholeDocument);
            // Byte-exact: the stored token is the query token, untouched.
            assert_eq!(
                hit.offline_token.as_deref().unwrap().as_bytes(),
                OFFLINE_TOKEN.as_bytes()
            );
        }
        other => panic!("expected offline-token hit, got {other:?}"),
    }
    // Case-folded or decoded variants are different tokens → exact miss.
    assert_eq!(
        miss_kind(index.resolve_offline_token(&OFFLINE_TOKEN.to_lowercase())),
        PageIndexMissKind::OfflineTokenNotInIndex
    );
    assert_eq!(
        miss_kind(index.resolve_offline_token("consultantplus://offline/ref=deadbeef")),
        PageIndexMissKind::OfflineTokenNotInIndex
    );
}

#[test]
fn offline_query_does_not_fall_through_to_address_space() {
    let index = fixture();
    // A token that looks like an address is still matched only by bytes.
    assert_eq!(
        miss_kind(index.resolve_offline_token("LAW")),
        PageIndexMissKind::OfflineTokenNotInIndex
    );
}

// ---------------------------------------------------------- 0-match negative #

#[test]
fn decoded_document_numbers_do_not_resolve() {
    // The offline token encrypts the document number; a decrypt-derived number
    // must be a 0-match against the index, both as an address and as a token.
    let index = fixture();
    for number in ["44-ФЗ", "402-ФЗ", "5-фкз"] {
        assert_eq!(
            miss_kind(index.resolve_key("LAW", number, 1)),
            PageIndexMissKind::AddressNotInIndex,
            "decoded number {number:?} must not resolve as an address"
        );
        assert_eq!(
            miss_kind(index.resolve_offline_token(number)),
            PageIndexMissKind::OfflineTokenNotInIndex,
            "decoded number {number:?} must not resolve as a token"
        );
    }
}

// ---------------------------------------------------------- anchor bridge #

#[test]
fn resolve_anchor_bridges_offline_and_internal() {
    let index = fixture();

    // Offline anchor → exact-token hit (whole document).
    let offline = ConsultantUriAnchor::parse(OFFLINE_TOKEN).expect("valid offline anchor");
    match index.resolve_anchor(&offline) {
        PageIndexResolution::Hit(hit) => {
            assert_eq!(hit.relative_path, "exports/npa/2.xml");
            assert_eq!(hit.scope, DocumentScope::WholeDocument);
        }
        other => panic!("expected offline anchor hit, got {other:?}"),
    }

    // Internal anchor → address hit, scope from para, token not rewritten.
    let whole = ConsultantUriAnchor::parse("consultantplus-internal://134/12345#P4294967295")
        .expect("valid internal anchor");
    assert_eq!(
        whole.as_token(),
        "consultantplus-internal://134/12345#P4294967295"
    );
    match index.resolve_anchor(&whole) {
        PageIndexResolution::Hit(hit) => {
            assert_eq!(hit.scope, DocumentScope::WholeDocument);
            assert_eq!(hit.relative_path, "exports/xml/internal.xml");
        }
        other => panic!("expected internal whole-doc hit, got {other:?}"),
    }

    let para = ConsultantUriAnchor::parse("consultantplus-internal://134/12345#P12")
        .expect("valid internal anchor");
    match index.resolve_anchor(&para) {
        PageIndexResolution::Hit(hit) => assert_eq!(hit.scope, DocumentScope::Paragraph(12)),
        other => panic!("expected internal paragraph hit, got {other:?}"),
    }

    // Internal anchor for an absent address → closed miss.
    let missing = ConsultantUriAnchor::parse("consultantplus-internal://134/999999#P1")
        .expect("valid internal anchor");
    assert_eq!(
        miss_kind(index.resolve_anchor(&missing)),
        PageIndexMissKind::AddressNotInIndex
    );
}

// ------------------------------------------------------------ observability #

#[test]
fn len_and_bank_counts_are_deterministic() {
    let index = fixture();
    assert_eq!(index.len(), 4);
    assert!(!index.is_empty());
    let counts = index.key_bank_counts();
    assert_eq!(counts.get("LAW"), Some(&2));
    assert_eq!(counts.get("ARB"), Some(&1));
    assert_eq!(counts.get("134"), Some(&1));
    // BTreeMap ordering: digits sort before uppercase bank tokens.
    assert_eq!(
        counts.keys().cloned().collect::<Vec<_>>(),
        vec!["134", "ARB", "LAW"]
    );

    let empty = CorpusPageIndex::build(&[]).expect("empty index builds");
    assert!(empty.is_empty());
    assert_eq!(empty.len(), 0);
}

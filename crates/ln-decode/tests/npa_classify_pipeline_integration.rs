//! M211 S04 T03: `classify_members` pipeline integration over the frozen seed.
//!
//! The 40-document frozen seed is read from
//! `tests/fixtures/npa-members/typed-parity-fixture.tsv` and the fragment
//! texts from `tests/fixtures/npa-lawref/` with a hand-rolled reader (D602;
//! no external de/serializer). A missing source fails closed.
//!
//! The classification pipeline must replay deterministically, must not mutate
//! the linked document or its input paragraphs, must anchor every member to a
//! valid source-local span, and must never panic.

use std::collections::BTreeMap;
use std::path::PathBuf;

use ln_decode::npa_anchor;
use ln_decode::npa_classify::{ClassificationDiagnostic, classify_members};
use ln_decode::npa_link;

fn fixture_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa-lawref")
}

fn fixture_tsv() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/npa-members/typed-parity-fixture.tsv")
}

fn read_fixture() -> BTreeMap<String, Vec<String>> {
    let text = std::fs::read_to_string(fixture_tsv()).expect("typed parity fixture must exist");
    let mut docs: BTreeMap<String, Vec<String>> = BTreeMap::new();
    let mut current: Option<String> = None;
    for line in text.lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let cols: Vec<&str> = line.split('\t').collect();
        match cols.first().copied() {
            Some("doc") => {
                current = Some(cols[1].to_string());
                docs.entry(cols[1].to_string()).or_default();
            }
            Some("frag") if cols.len() >= 2 => {
                if let Some(cur) = current.as_deref()
                    && let Some(frags) = docs.get_mut(cur)
                {
                    frags.push(cols[1].to_string());
                }
            }
            _ => {}
        }
    }
    assert!(!docs.is_empty(), "MISSING SOURCE: fixture is mandatory");
    docs
}

fn load_doc(docs: &BTreeMap<String, Vec<String>>, doc: &str) -> Vec<String> {
    let frags = docs
        .get(doc)
        .unwrap_or_else(|| panic!("MISSING SOURCE: {doc} absent from fixture"));
    assert!(!frags.is_empty(), "MISSING SOURCE: {doc} has no fragments");
    frags
        .iter()
        .map(|frag| {
            let path = fixture_dir().join(frag);
            std::fs::read_to_string(&path)
                .unwrap_or_else(|e| panic!("MISSING SOURCE: {}: {e}", path.display()))
        })
        .collect()
}

/// `classify_members` over every frozen document is deterministic, does not
/// mutate the linked document or its inputs, and anchors every emitted member
/// to a valid source-local span without panic.
#[test]
fn every_frozen_document_classifies_deterministically_and_immutably() {
    let docs = read_fixture();
    assert_eq!(docs.len(), 40, "the frozen seed is exactly 40 documents");

    let mut total_members = 0usize;
    for doc in docs.keys() {
        let paras = load_doc(&docs, doc);
        let paras_before = paras.clone();
        let linked = npa_link::build_linked_document(&paras);
        let linked_before = linked.clone();

        let (first, first_diags) = classify_members(&linked, &paras);
        let (second, second_diags) = classify_members(&linked, &paras);

        assert_eq!(first, second, "{doc}: classification replay is not stable");
        assert_eq!(
            first_diags, second_diags,
            "{doc}: classification diagnostics replay is not stable"
        );
        assert_eq!(
            linked, linked_before,
            "{doc}: classification mutated the linked document"
        );
        assert_eq!(
            paras, paras_before,
            "{doc}: classification mutated its input"
        );

        for member in &first {
            let source = paras
                .get(member.evidence.block)
                .unwrap_or_else(|| panic!("{doc}: classified member evidence block out of range"));
            npa_anchor::check_span(source, member.evidence).unwrap_or_else(|e| {
                panic!(
                    "{doc}: classified member {} has an invalid span: {e:?}",
                    member.member_id
                )
            });
        }

        total_members += first.len();
    }
    assert!(total_members > 0, "expected classified members in the seed");
}

/// Every non-skipped member carries a valid span, so the fail-closed
/// `SpanInvalid` diagnostic must be empty on the frozen seed; `type_missing`
/// and `unknown_kind` members are surfaced, not dropped.
#[test]
fn span_diagnostics_are_absent_and_form_diagnostics_are_surfaced() {
    let docs = read_fixture();
    let mut saw_form_diagnostic = false;

    for doc in docs.keys() {
        let paras = load_doc(&docs, doc);
        let linked = npa_link::build_linked_document(&paras);
        let (members, diagnostics) = classify_members(&linked, &paras);

        assert!(
            !diagnostics.contains(&ClassificationDiagnostic::SpanInvalid),
            "{doc}: a frozen member span failed validation: {diagnostics:?}"
        );
        if diagnostics.iter().any(|d| {
            matches!(
                d,
                ClassificationDiagnostic::TypeMissing | ClassificationDiagnostic::UnknownKind
            )
        }) {
            saw_form_diagnostic = true;
        }
        let span_invalid = diagnostics
            .iter()
            .filter(|d| **d == ClassificationDiagnostic::SpanInvalid)
            .count();
        assert_eq!(
            members.len() + span_invalid,
            linked.members.len(),
            "{doc}: every linked member is either classified or skipped as SpanInvalid"
        );
    }

    assert!(
        saw_form_diagnostic,
        "the frozen seed should surface at least one form diagnostic"
    );
}

/// A member whose span is out of range or inverted must fail closed with
/// `SpanInvalid` and must not panic or fabricate a classification.
#[test]
fn invalid_member_spans_fail_closed_without_panic() {
    use ln_decode::npa_anchor::LocalSpan;
    use ln_decode::npa_link::{LinkDerivation, LinkedDocument, LinkedMember, LinkedMemberKind};

    fn member(evidence: LocalSpan) -> LinkedMember {
        LinkedMember {
            id: 0,
            kind: LinkedMemberKind::Anchored,
            date: String::new(),
            number: String::new(),
            type_name: "Федеральный закон".to_string(),
            approved_by: None,
            alias: None,
            derivation: LinkDerivation::TypedAnchor,
            evidence,
            provenance: Vec::new(),
        }
    }

    let paras = vec!["Федеральный закон от 01.01.2020 N 1-ФЗ".to_string()];
    let cases = [
        // Block index past the end of the paragraph slice.
        LocalSpan {
            block: 7,
            start: 0,
            end: 1,
        },
        // Inverted / empty half-open range.
        LocalSpan {
            block: 0,
            start: 5,
            end: 5,
        },
        // Past the byte length of the block.
        LocalSpan {
            block: 0,
            start: 0,
            end: 10_000,
        },
    ];

    for evidence in cases {
        let linked = LinkedDocument {
            members: vec![member(evidence)],
            relations: Vec::new(),
            letterhead: None,
            diagnostics: Vec::new(),
        };
        let (members, diagnostics) = classify_members(&linked, &paras);
        assert!(
            members.is_empty(),
            "no member may be fabricated: {evidence:?}"
        );
        assert_eq!(
            diagnostics,
            vec![ClassificationDiagnostic::SpanInvalid],
            "invalid span must fail closed: {evidence:?}"
        );
    }
}

/// The classification source stays free of the external (de)serializer and of
/// filesystem / environment / child-process access (D602).
#[test]
fn classification_source_stays_serde_fs_env_free() {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/npa_classify.rs");
    let source = std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("read source: {e}"));
    for forbidden in [
        "serde",
        "Serialize",
        "serde_json",
        "std::fs",
        "std::env",
        "std::process",
    ] {
        assert!(
            !source.contains(forbidden),
            "npa_classify.rs must stay serde/fs/env/process-free (D602): found {forbidden}"
        );
    }
}

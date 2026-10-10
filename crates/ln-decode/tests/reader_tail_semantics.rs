//! Bounded regression oracles for text following a closed WordML element.
use ln_decode::reader_contract::{ReaderSemantic, ReaderViewKind};
use ln_decode::reader_projection::build_projection;
use ln_decode::reader_verifier::{verify_projection, VerifyCode};
use ln_decode::source_package::{capture, Limits, Record, TextSlot};

// value, capture owner, slot, primary view kind, primary view anchor, semantic
type Expected<'a> = (
    &'a str,
    &'a str,
    TextSlot,
    ReaderViewKind,
    &'a str,
    ReaderSemantic,
);

fn assert_fragments(xml: &str, expected: &[Expected<'_>]) {
    let package = capture(xml.as_bytes(), &Limits::default()).expect("real XML capture");
    let projection = build_projection(package.records()).expect("reader projection");
    let texts: Vec<_> = package
        .records()
        .iter()
        .filter_map(|record| match record {
            Record::Text(text) => Some(text),
            _ => None,
        })
        .collect();
    assert_eq!(texts.len(), expected.len());
    assert_eq!(projection.segments.len(), texts.len());
    // Establish source conservation and ownership before checking semantics.
    let mut actual_semantics = Vec::new();
    for (i, (text, &(value, owner, slot, kind, anchor, _))) in
        texts.iter().zip(expected).enumerate()
    {
        assert_eq!(text.id, format!("t{i}"));
        assert_eq!(text.value, value);
        assert_eq!(text.owner, owner);
        assert_eq!(text.slot, slot);
        let segments: Vec<_> = projection
            .segments
            .iter()
            .filter(|segment| {
                segment
                    .fragment_ref
                    .as_ref()
                    .is_some_and(|fragment| fragment.as_str() == text.id)
            })
            .collect();
        assert_eq!(segments.len(), 1, "{} must occur exactly once", text.id);
        let segment = segments[0];
        assert_eq!(segment.element_ref.as_str(), owner);
        assert_eq!(segment.slot, Some(slot));
        let span = segment.span.as_ref().expect("source span");
        assert_eq!((span.start, span.end), (0, value.len()));
        assert_eq!(segment.chars, value.chars().count());
        assert_eq!(segment.output_end - segment.output_start, value.len());
        let view = projection.view(&segment.view).expect("primary owner");
        assert_eq!(view.kind, kind, "{value}");
        assert_eq!(view.element_ref.as_str(), anchor, "{value}");
        assert_eq!(segment.contextual, segment.semantic != ReaderSemantic::Body);
        actual_semantics.push((value, segment.semantic));
    }
    let expected_semantics: Vec<_> = expected.iter().map(|row| (row.0, row.5)).collect();
    assert_eq!(actual_semantics, expected_semantics);
    assert_eq!(verify_projection(&projection, package.records()), Ok(()));

    // Each tail must reject a semantic rewrite even with a fresh content seal
    // and a contextual flag consistent with the forged semantic.
    for text in texts.iter().filter(|text| text.slot == TextSlot::Tail) {
        let mut tampered = projection.clone();
        tampered.reseal();
        let original_hash = tampered.content_hash().unwrap().to_string();
        let segment = tampered
            .segments
            .iter_mut()
            .find(|segment| {
                segment
                    .fragment_ref
                    .as_ref()
                    .is_some_and(|fragment| fragment.as_str() == text.id)
            })
            .expect("tail segment");
        segment.semantic = if segment.semantic == ReaderSemantic::Body {
            ReaderSemantic::RevisionDeletion
        } else {
            ReaderSemantic::Body
        };
        segment.contextual = segment.semantic != ReaderSemantic::Body;
        tampered.reseal();
        assert_ne!(tampered.content_hash().unwrap(), original_hash);
        let findings = verify_projection(&tampered, package.records())
            .expect_err("resealing cannot authorize a tail semantic rewrite");
        assert!(
            findings
                .iter()
                .any(|finding| { finding.code == VerifyCode::SegmentSourceMismatch }),
            "{}: {findings:?}",
            text.id
        );
    }
}

#[test]
fn closed_deletion_and_field_do_not_contaminate_following_tails() {
    use ReaderSemantic::{Body, FieldCode, RevisionDeletion};
    use ReaderViewKind::{Paragraph, Residual};
    use TextSlot::{Tail, Text};
    // Exact self-contained copy of the audit tails.xml, without a /tmp dependency.
    let xml = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:del><w:r><w:t>DELETED</w:t></w:r></w:del>LIVE<w:r><w:instrText>CODE</w:instrText>AFTER_CODE<w:t>A</w:t>AFTER_TEXT</w:r></w:p></w:body></w:wordDocument>"#;
    assert_fragments(
        xml,
        &[
            ("DELETED", "e5", Text, Paragraph, "e2", RevisionDeletion),
            ("LIVE", "e3", Tail, Paragraph, "e2", Body),
            ("CODE", "e7", Text, Paragraph, "e2", FieldCode),
            ("AFTER_CODE", "e7", Tail, Residual, "e0", Body),
            ("A", "e8", Text, Paragraph, "e2", Body),
            ("AFTER_TEXT", "e8", Tail, Residual, "e0", Body),
        ],
    );
}

#[test]
fn tails_retain_open_ancestors_but_not_closed_inner_roles() {
    use ReaderSemantic::{Body, FieldCode, RevisionDeletion, RevisionInsertion, Whitespace};
    use ReaderViewKind::{Paragraph, Residual};
    use TextSlot::{Tail, Text};
    let xml = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:del><w:instrText>CODE</w:instrText>СТАРОЕ</w:del>ЖИВОЕ<w:ins><w:del>INNER</w:del>INSERTED</w:ins>AFTER_INS<w:fldSimple><w:del>FIELD_INNER</w:del>FIELD_TAIL</w:fldSimple>AFTER_FIELD<w:del>REMOVED</w:del> </w:p></w:body></w:wordDocument>"#;
    assert_fragments(
        xml,
        &[
            ("CODE", "e4", Text, Paragraph, "e2", FieldCode),
            ("СТАРОЕ", "e4", Tail, Residual, "e0", RevisionDeletion),
            ("ЖИВОЕ", "e3", Tail, Paragraph, "e2", Body),
            ("INNER", "e6", Text, Paragraph, "e2", RevisionInsertion),
            ("INSERTED", "e6", Tail, Residual, "e0", RevisionInsertion),
            ("AFTER_INS", "e5", Tail, Paragraph, "e2", Body),
            ("FIELD_INNER", "e8", Text, Paragraph, "e2", FieldCode),
            ("FIELD_TAIL", "e8", Tail, Residual, "e0", FieldCode),
            ("AFTER_FIELD", "e7", Tail, Paragraph, "e2", Body),
            ("REMOVED", "e9", Text, Paragraph, "e2", RevisionDeletion),
            (" ", "e9", Tail, Paragraph, "e2", Whitespace),
        ],
    );
}

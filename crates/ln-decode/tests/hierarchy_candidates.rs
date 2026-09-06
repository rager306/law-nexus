//! TDD red contract for the public hierarchy candidate extraction API
//! (M202-9qf3ta S01, extraction-only boundary).
//!
//! `extract_hierarchy_candidates` folds `extract_hierarchy` over decoded
//! blocks in document order, builds catalog-token ladder paths, dedupes
//! `(level, key_path)` first-wins and reports typed diagnostics. It never
//! mints ComponentConcepts, never writes YAML, never performs registry
//! admission and is never legal truth — pinned by
//! `HierarchyCandidateReport::HIERARCHY_CANDIDATE_NON_CLAIMS`.
//!
//! Git-tracked inline WordML fixture only: no consru_export corpus access.
//!
//! T02 contract notes: `HierarchyCandidate` must derive `Clone + PartialEq +
//! Debug`; `HierarchyExtractDiagnostic` must derive `Debug + PartialEq`.
//! Report accessors: `candidates() -> &[HierarchyCandidate]`,
//! `diagnostics() -> &[HierarchyExtractDiagnostic]`,
//! `extracted_count() -> usize`, `unique_count() -> usize`.
//! `DuplicateKey` indices address the raw document-order extracted hit
//! stream (duplicates included).

use ln_decode::adapters::ConsultantWordMlBlockDecoder;
use ln_decode::domain::{
    DecodeRequest, FamilyFormat, HierarchyLevel, ParagraphStyle, ParsedBlock, PayloadRef,
    SourceFormatId, SourceLocation, SourceSpan, SourceStreamId, TextSpan,
};
use ln_decode::hierarchy::{
    catalog_token, extract_hierarchy_candidates, HierarchyCandidateReport,
    HierarchyExtractDiagnostic,
};
use ln_decode::ports::BlockDecoderPort;

fn block(text: &str) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        ParagraphStyle::Heading,
        SourceLocation::new(
            SourceStreamId::parse("fixture:hierarchy-candidates").unwrap(),
            SourceSpan::try_new(500, 900).expect("independent artifact span"),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .expect("valid parsed block")
}

fn provider_comment_block(text: &str) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        ParagraphStyle::ProviderComment,
        SourceLocation::new(
            SourceStreamId::parse("fixture:hierarchy-candidates").unwrap(),
            SourceSpan::try_new(500, 900).expect("independent artifact span"),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .expect("valid parsed block")
}

fn decode(xml: &[u8]) -> Vec<ParsedBlock> {
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:m202-hierarchy-candidates").unwrap(),
        FamilyFormat::parse("family:consultant-wordml").unwrap(),
        xml,
    );
    ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("inline WordML fixture must decode")
}

/// Same git-tracked inline fixture as `registry_bindings_generator`: one
/// glava container, two statya units, nested punkt ladders. The punkt-1
/// under statya-4 appears twice (duplicate key); the punkt-1 under statya-5
/// is a distinct ladder path.
const INLINE_FIXTURE: &str = r#"<w:wordDocument xmlns:w="urn:word"><w:body>
<w:p><w:r><w:t>Глава 1. Общие положения</w:t></w:r></w:p>
<w:p><w:r><w:t>Статья 4. Требования к участникам</w:t></w:r></w:p>
<w:p><w:r><w:t>1) пункт первый</w:t></w:r></w:p>
<w:p><w:r><w:t>4.1) пункт четыре точка один</w:t></w:r></w:p>
<w:p><w:r><w:t>1) пункт первый дубль</w:t></w:r></w:p>
<w:p><w:r><w:t>Статья 5. Сфера применения</w:t></w:r></w:p>
<w:p><w:r><w:t>1) пункт первый в статье пять</w:t></w:r></w:p>
</w:body></w:wordDocument>"#;

#[test]
fn candidate_report_document_order_ladder_paths_and_counts() {
    let blocks = decode(INLINE_FIXTURE.as_bytes());
    let report = extract_hierarchy_candidates(&blocks);

    // Raw hits (including the duplicate) vs first-wins unique candidates.
    assert_eq!(report.extracted_count(), 7, "7 marker hits in the fixture");
    assert_eq!(report.unique_count(), 6, "duplicate punkt-1 collapses");
    assert_eq!(report.candidates().len(), report.unique_count());

    // Deterministic document order with catalog-token ladder paths.
    let keys: Vec<&str> = report
        .candidates()
        .iter()
        .map(|candidate| candidate.key_path())
        .collect();
    assert_eq!(
        keys,
        vec![
            "1",
            "4",
            "statya-4/punkt-1",
            "statya-4/punkt-4.1",
            "5",
            "statya-5/punkt-1",
        ],
        "document order with catalog-token ladder paths"
    );

    // Flat container: no ladder path, key defaults to the bare number.
    let glava = &report.candidates()[0];
    assert_eq!(glava.level(), HierarchyLevel::Glava);
    assert_eq!(glava.catalog_token(), "glava");
    assert_eq!(glava.number(), "1");
    assert_eq!(glava.path(), None, "glava is a container, flat key");
    assert_eq!(glava.key_path(), "1");
    assert_eq!(glava.depth(), 1);
    assert_eq!(glava.title(), Some("Общие положения"));
    assert_eq!(glava.marker_span(), TextSpan::try_new(0, 13).unwrap());

    // Flat unit: single-segment statya path stays unqualified.
    let statya4 = &report.candidates()[1];
    assert_eq!(statya4.level(), HierarchyLevel::Statya);
    assert_eq!(statya4.catalog_token(), "statya");
    assert_eq!(statya4.number(), "4");
    assert_eq!(statya4.path(), None, "single-segment statya path is flat");
    assert_eq!(statya4.key_path(), "4");
    assert_eq!(statya4.depth(), 1);
    assert_eq!(statya4.title(), Some("Требования к участникам"));
    assert_eq!(statya4.marker_span(), TextSpan::try_new(0, 15).unwrap());

    // Nested punkt carries its statya parent via catalog tokens.
    let punkt1 = &report.candidates()[2];
    assert_eq!(punkt1.level(), HierarchyLevel::Punkt);
    assert_eq!(punkt1.catalog_token(), "punkt");
    assert_eq!(punkt1.number(), "1");
    assert_eq!(punkt1.path(), Some("statya-4/punkt-1"));
    assert_eq!(punkt1.key_path(), "statya-4/punkt-1");
    assert_eq!(punkt1.depth(), 2);
    assert_eq!(punkt1.title(), Some("пункт первый"));
    assert_eq!(punkt1.marker_span(), TextSpan::try_new(0, 2).unwrap());

    // Compound number nested under the same statya.
    let punkt41 = &report.candidates()[3];
    assert_eq!(punkt41.number(), "4.1");
    assert_eq!(punkt41.path(), Some("statya-4/punkt-4.1"));
    assert_eq!(punkt41.depth(), 2);
    assert_eq!(punkt41.marker_span(), TextSpan::try_new(0, 4).unwrap());

    // Ladder pops back to statya level without leaking the previous punkt.
    let statya5 = &report.candidates()[4];
    assert_eq!(statya5.level(), HierarchyLevel::Statya);
    assert_eq!(statya5.number(), "5");
    assert_eq!(statya5.path(), None);
    assert_eq!(statya5.title(), Some("Сфера применения"));

    // Same number under a different statya stays distinct.
    let st5_punkt = &report.candidates()[5];
    assert_eq!(st5_punkt.path(), Some("statya-5/punkt-1"));
    assert_ne!(punkt1.path(), st5_punkt.path(), "ladders must not collide");
}

#[test]
fn duplicate_key_is_first_wins_with_typed_diagnostic() {
    let blocks = decode(INLINE_FIXTURE.as_bytes());
    let report = extract_hierarchy_candidates(&blocks);

    // Exactly one duplicate: punkt-1 twice under statya-4.
    assert_eq!(report.diagnostics().len(), 1, "only the punkt-1 duplicate");
    match &report.diagnostics()[0] {
        HierarchyExtractDiagnostic::DuplicateKey {
            level,
            key_path,
            first_index,
            later_index,
        } => {
            assert_eq!(*level, HierarchyLevel::Punkt);
            assert_eq!(key_path, "statya-4/punkt-1");
            // Indices address the raw document-order hit stream (7 hits).
            assert_eq!(*first_index, 2);
            assert_eq!(*later_index, 4);
        }
    }

    // First wins: the surviving candidate carries the first title.
    let survived = report
        .candidates()
        .iter()
        .find(|candidate| candidate.key_path() == "statya-4/punkt-1")
        .expect("first-wins candidate kept");
    assert_eq!(survived.title(), Some("пункт первый"));
    assert_eq!(survived.number(), "1");

    // Diagnostics are identifiers only — never raw block text.
    let rendered = format!("{:?}", report.diagnostics());
    assert!(!rendered.contains("дубль"), "no raw text in diagnostics");
    assert!(!rendered.contains("первый"), "no raw text in diagnostics");
}

#[test]
fn repeated_calls_are_deterministic() {
    let blocks = decode(INLINE_FIXTURE.as_bytes());
    let first = extract_hierarchy_candidates(&blocks);
    let second = extract_hierarchy_candidates(&blocks);

    assert_eq!(first.candidates(), second.candidates());
    assert_eq!(first.diagnostics(), second.diagnostics());
    assert_eq!(first.extracted_count(), second.extracted_count());
    assert_eq!(first.unique_count(), second.unique_count());
}

#[test]
fn empty_input_yields_empty_report() {
    let report = extract_hierarchy_candidates(&[]);

    assert!(report.candidates().is_empty());
    assert!(report.diagnostics().is_empty());
    assert_eq!(report.extracted_count(), 0);
    assert_eq!(report.unique_count(), 0);
}

#[test]
fn prose_and_structural_only_markers_are_silent_skips() {
    // `extract_hierarchy == None` is a silent skip, not an error and not a
    // diagnostic: prose mentions, unparseable markers and unsupported
    // structural surface tokens (hierarchy_contract hostile rows + R8-09).
    let blocks = [
        block("В статье 5 описаны требования."),
        block("Статья без номера"),
        block("Статья IV. Не numeric article"),
        block("Примечание"),
        block("примечание"),
        block("Приложение 1"),
    ];
    let report = extract_hierarchy_candidates(&blocks);

    assert!(report.candidates().is_empty());
    assert!(report.diagnostics().is_empty());
    assert_eq!(report.extracted_count(), 0);
    assert_eq!(report.unique_count(), 0);
}

#[test]
fn provider_comment_blocks_are_skipped_and_not_counted() {
    // Provider comments are not structure: skipped by block style (align
    // with inspect), never by text heuristics. They produce no candidate,
    // no raw hit and no diagnostic, so counts cannot inflate.
    let blocks = [
        provider_comment_block("Статья 77. Провайдерский комментарий"),
        block("Статья 4. Настоящая статья"),
    ];
    let report = extract_hierarchy_candidates(&blocks);

    assert_eq!(report.extracted_count(), 1, "comment block not counted");
    assert_eq!(report.unique_count(), 1);
    assert_eq!(report.candidates().len(), 1);
    assert_eq!(report.candidates()[0].number(), "4");
    assert!(report.diagnostics().is_empty());
}

#[test]
fn catalog_tokens_are_lowercase_aliases_not_variant_names() {
    // Catalog tokens mirror kb-ontology decode_level_aliases values; the
    // Title-case as_str contract stays pinned in parser_domain_contract.
    let cases = [
        (HierarchyLevel::Razdel, "razdel"),
        (HierarchyLevel::Glava, "glava"),
        (HierarchyLevel::Paragraph, "paragraph"),
        (HierarchyLevel::Statya, "statya"),
        (HierarchyLevel::Chast, "chast"),
        (HierarchyLevel::Punkt, "punkt"),
        (HierarchyLevel::Podpunkt, "podpunkt"),
    ];
    for (level, token) in cases {
        assert_eq!(catalog_token(level), token, "{token} catalog token");
    }
    assert_eq!(HierarchyLevel::Statya.as_str(), "Statya", "as_str pinned");
}

#[test]
fn non_claims_constant_denies_minting_yaml_admission_and_legal_truth() {
    // The report type carries the D185 extraction boundary: candidates are
    // proposals only. The constant must name every denied capability so the
    // boundary cannot silently erode downstream.
    let claims = HierarchyCandidateReport::HIERARCHY_CANDIDATE_NON_CLAIMS;
    assert!(!claims.is_empty(), "non-claims boundary must be explicit");
    assert!(
        claims.iter().all(|claim| !claim.trim().is_empty()),
        "every non-claim entry must be non-empty"
    );
    let lowered = claims.join("\n").to_lowercase();
    assert!(
        lowered.contains("componentconcept"),
        "must deny ComponentConcept minting"
    );
    assert!(
        lowered.contains("yaml"),
        "must deny YAML writes / auto-apply"
    );
    assert!(
        lowered.contains("admission"),
        "must deny registry admission"
    );
    assert!(
        lowered.contains("legal"),
        "must deny legal truth / registry authority"
    );
}

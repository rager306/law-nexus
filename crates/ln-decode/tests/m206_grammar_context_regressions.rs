//! M206/S06 red reproduction oracle for RC28-F06..F10.
//! These tests intentionally assert the admitted desired contract; they must fail
//! against the pre-remediation runtime and pass after the minimal fix.

use ln_decode::document_context::{
    build_document_analysis_overlay, build_document_structure_index, detect_this_ref_grammar,
    BlockId, ContainerRole, ContextBudgets, ContextEnvironment, ContextRequest, ContextStatus,
    ContextWorklist, DocumentVersionRef, StructureEdgeRelation,
};
use ln_decode::domain::{
    ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
};
use ln_decode::lawref::capture_lawrefs;
use ln_decode::lexer::lex;
use ln_decode::local_grammar::{extract_act_list_frames, extract_structural_frames, FrameStatus};
use ln_decode::morphology::find_legal_markers;

fn block(text: &str, style: ParagraphStyle, order: usize) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse("fixture:m206-s06").unwrap(),
            SourceSpan::try_new(order * 100, order * 100 + text.len()).unwrap(),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .unwrap()
}

fn index(
    blocks: &[ParsedBlock],
) -> Result<
    ln_decode::document_context::DocumentStructureIndex,
    ln_decode::document_context::IndexBuildError,
> {
    build_document_structure_index(
        DocumentVersionRef::try_new("doc-v1".into(), "rev-1".into(), "profile-1".into()).unwrap(),
        blocks,
    )
}

#[test]
fn rc28_f06_sibling_heading_closes_previous_container() {
    let blocks = vec![
        block("Закон", ParagraphStyle::Title, 0),
        block("Статья 1. Первый", ParagraphStyle::Heading, 1),
        block("Первый текст", ParagraphStyle::BodyText, 2),
        block("Статья 2. Второй", ParagraphStyle::Heading, 3),
        block("Второй текст", ParagraphStyle::BodyText, 4),
    ];
    let built = index(&blocks);
    assert!(
        built.is_ok(),
        "RC28-F06 structure index must admit sibling headings: {built:?}"
    );
    let built = built.unwrap();
    let path = built
        .ancestor_path(&BlockId::parse("block-4").unwrap())
        .unwrap_or_else(|error| panic!("RC28-F06 expected a sibling path, got {error:?}"));
    assert_eq!(
        path[0].role(),
        ContainerRole::Article,
        "RC28-F06 sibling body must be in the second article"
    );
    assert_eq!(
        path.iter()
            .filter(|node| node.role() == ContainerRole::Article)
            .count(),
        1,
        "RC28-F06 sibling closure must not retain the first article"
    );
    assert_eq!(
        path[0].designation(),
        Some("statya:2"),
        "RC28-F06 case identifier: sibling article 2"
    );
}

#[test]
fn rc28_f07_three_unrelated_blocks_have_no_parent_edges() {
    let blocks = vec![
        block(
            "Первое независимое предложение.",
            ParagraphStyle::BodyText,
            0,
        ),
        block(
            "Второе независимое предложение.",
            ParagraphStyle::BodyText,
            1,
        ),
        block(
            "Третье независимое предложение.",
            ParagraphStyle::BodyText,
            2,
        ),
    ];
    let built = index(&blocks).unwrap();
    let parent_edges = built
        .edges()
        .iter()
        .filter(|edge| {
            edge.relation() == StructureEdgeRelation::ParentOf
                || edge.relation() == StructureEdgeRelation::ContainedIn
        })
        .count();
    assert_eq!(
        parent_edges, 0,
        "RC28-F07 case identifier: unrelated blocks must not gain parent edges"
    );
}

#[test]
fn rc28_f08_this_ref_survives_nonempty_worklist_and_empty_or_cited_is_negative() {
    let blocks = vec![block(
        "Настоящего Закона следует придерживаться.",
        ParagraphStyle::BodyText,
        0,
    )];
    let built = index(&blocks).unwrap();
    let overlay = build_document_analysis_overlay(&built, &[], &[]).unwrap();
    let evidence = detect_this_ref_grammar(blocks[0].text());
    assert!(
        !evidence.is_empty(),
        "RC28-F08 case identifier: ThisRef evidence must be nonempty"
    );
    let request = ContextRequest::current_document_requisites(
        ln_decode::document_context::FrameRef::parse("block-0").unwrap(),
        ln_decode::current_requisites::ThisRefGrammarEvidence::new([
            ln_decode::current_requisites::RequisitesField::Type,
        ]),
    );
    let environment = ContextEnvironment {
        index: &built,
        overlay: &overlay,
        requisites: None,
    };
    let mut worklist = ContextWorklist::new(ContextBudgets::default());
    let report = worklist.run(environment, &[request]);
    let result = report.results.values().next().unwrap();
    assert_eq!(
        result.status,
        ContextStatus::Resolved,
        "RC28-F08 case identifier: nonempty ThisRef must resolve through worklist"
    );
    assert!(
        detect_this_ref_grammar("").is_empty(),
        "RC28-F08 empty ThisRef must remain negative"
    );
    assert!(
        detect_this_ref_grammar("согласно статье 5").is_empty(),
        "RC28-F08 cited-act wording must remain negative"
    );
}

#[test]
fn rc28_f09_independent_sentences_and_incomplete_tail_keep_local_origins() {
    let first = "федерального закона от 01.01.2020 N 1-ФЗ";
    let second = "федерального закона от 02.02.2021 N 2-ФЗ";
    let source = format!("{first}. {second}.");
    let captures = capture_lawrefs(&source);
    let frames = extract_act_list_frames(&source, &captures);
    assert_eq!(
        frames.len(),
        2,
        "RC28-F09 case identifier: independent sentences must not be merged"
    );
    assert!(
        frames
            .iter()
            .all(|frame| frame.local_anchor.start() < frame.local_anchor.end()),
        "RC28-F09 every frame needs an origin span"
    );
    let incomplete = extract_act_list_frames(
        "федерального закона от 03.03.2022",
        &capture_lawrefs("федерального закона от 03.03.2022"),
    );
    assert_eq!(
        incomplete.len(),
        1,
        "RC28-F09 case identifier: incomplete tail must remain observable"
    );
    assert_eq!(
        incomplete[0].status,
        FrameStatus::Ambiguous,
        "RC28-F09 incomplete tail must be ambiguous, not silently dropped"
    );
}

#[test]
fn rc28_f10_original_spans_accept_en_and_em_dash_range_variants() {
    for dash in ["–", "—"] {
        let source = format!("статьями 7.29 {dash} 7.32");
        let captures = capture_lawrefs(&source);
        let range = captures
            .captures()
            .iter()
            .find(|capture| capture.slots.range.is_some());
        assert!(
            range.is_some(),
            "RC28-F10 case identifier: original {dash} range must be captured"
        );
        let capture = range.unwrap();
        assert_eq!(
            capture.user_text(&source),
            source,
            "RC28-F10 original span must preserve the source dash"
        );
    }
    let _ = extract_structural_frames(
        &lex("статьями 7.29 – 7.32"),
        "статьями 7.29 – 7.32",
        &find_legal_markers("статьями 7.29 – 7.32"),
    );
}

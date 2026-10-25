//! T04 hostile battery (M214-es3jvw S02).
//!
//! Executable core of `prd/architecture/npa-analysis-jsonl-contract.md` §8A.9
//! and §12: `inspect_npa_analysis_wire` must refuse a structural break, a
//! temporal stop-sign field, an inline decoded-corpus text channel and a
//! refused analytical record presented as `complete`. The writer limits are
//! validated before any byte is written. `inspect` is structure-only: it never
//! recomputes a seal, which the last case proves.
//!
//! Fixtures are inline non-legal synthetic WordML documents. Raw decoded corpus
//! text is never logged.

use ln_decode::analysis_source_mapping::{SourceIdentity, SourceMapping};
use ln_decode::document_context::DocumentVersionRef;
use ln_decode::npa_analysis_records::{DocumentAnalysis, analyze_document};
use ln_decode::npa_analysis_wire::{
    AnalysisEnvelopeRequest, AnalysisLimits, AnalysisScope, AnalysisWireErrorKind,
    inspect_npa_analysis_wire, render_npa_analysis,
};
use ln_decode::reader_contract::{FragmentRef, ReaderRecordIndex};
use ln_decode::reader_projection::{ReaderProjection, build_projection};
use ln_decode::source_package::{Limits, capture};

fn wrap(body: &str) -> String {
    format!(
        "<w:wordDocument xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\"><w:body>{body}</w:body></w:wordDocument>"
    )
}

struct Pipeline {
    analysis: DocumentAnalysis,
    projection: ReaderProjection,
    index: ReaderRecordIndex,
    mapping: SourceMapping,
}

fn pipeline(xml: &str) -> Pipeline {
    let package = capture(xml.as_bytes(), &Limits::default()).expect("fixture must capture");
    let index = ReaderRecordIndex::new(package.records()).expect("substrate index");
    let projection = build_projection(package.records()).expect("projection must build");
    let identity = SourceIdentity::try_new(
        package.manifest().source.sha256.clone(),
        package.manifest().source.bytes,
        "law-nexus/source-package-model/v1".to_string(),
        package.footer().records_seal_hash.clone(),
        package.footer().manifest_hash.clone(),
    )
    .expect("manifest identity must be well formed");
    let version = DocumentVersionRef::try_new(
        "doc-version-1".to_string(),
        "rev-1".to_string(),
        "reader_wordml_profile/v1".to_string(),
    )
    .expect("version triple must be well formed");
    let mut mapping = SourceMapping::new(identity.clone(), version);
    for text in index.texts() {
        mapping
            .pin_fragment(
                FragmentRef::from(text.id.as_str()),
                text.value.clone(),
                &identity,
            )
            .expect("every substrate fragment must pin");
    }
    let analysis = analyze_document(&projection, &index, &mapping).expect("analysis must build");
    Pipeline {
        analysis,
        projection,
        index,
        mapping,
    }
}

fn render_with(xml: &str, limits: AnalysisLimits) -> Result<String, AnalysisWireErrorKind> {
    let p = pipeline(xml);
    render_npa_analysis(&AnalysisEnvelopeRequest {
        analysis: &p.analysis,
        projection: &p.projection,
        index: &p.index,
        mapping: &p.mapping,
        limits,
        scope: AnalysisScope::Bounded,
    })
    .map_err(|error| error.kind())
}

fn render(xml: &str) -> String {
    render_with(xml, AnalysisLimits::default()).expect("valid analysis renders")
}

fn lines(text: &str) -> Vec<String> {
    assert!(text.ends_with('\n'), "envelope ends with one trailing LF");
    let body = &text[..text.len() - 1];
    body.split('\n').map(str::to_string).collect()
}

fn join(all: &[String]) -> String {
    let mut out = all.join("\n");
    out.push('\n');
    out
}

/// Prepends a top-level key/value pair to the first record line (index 2).
fn add_field_to_first_record(text: &str, pair: &str) -> String {
    let mut all = lines(text);
    let line = &mut all[2];
    *line = line.replacen('{', &format!("{{{pair}"), 1);
    join(&all)
}

const TYPED_BODY: &str = "<w:p><w:r><w:t>Федеральный закон от 01.01.2020 N 1-ФЗ</w:t></w:r></w:p>";

/// A typed member whose anchor straddles two source fragments (T02 refusal).
const SPLIT_BODY: &str =
    "<w:p><w:r><w:t>от 01.01.2020 N </w:t></w:r><w:r><w:t>1-ФЗ</w:t></w:r></w:p>";

#[test]
fn valid_envelope_inspects() {
    let text = render(&wrap(TYPED_BODY));
    inspect_npa_analysis_wire(&text).expect("the baseline envelope is valid");
}

// ---------------------------------------------------------- structure #

#[test]
fn missing_trailing_lf_is_refused() {
    let text = render(&wrap(TYPED_BODY));
    let truncated = text[..text.len() - 1].to_string();
    assert_eq!(
        inspect_npa_analysis_wire(&truncated)
            .expect_err("no trailing LF")
            .kind(),
        AnalysisWireErrorKind::MissingTrailingLf
    );
}

#[test]
fn carriage_return_is_refused() {
    let text = render(&wrap(TYPED_BODY));
    let crlf = text.replace('\n', "\r\n");
    assert_eq!(
        inspect_npa_analysis_wire(&crlf)
            .expect_err("CR is forbidden")
            .kind(),
        AnalysisWireErrorKind::CarriageReturn
    );
}

#[test]
fn empty_interior_line_is_refused() {
    let text = render(&wrap(TYPED_BODY));
    let all = lines(&text);
    let mut injected = vec![all[0].clone(), String::new()];
    injected.extend(all[1..].iter().cloned());
    assert_eq!(
        inspect_npa_analysis_wire(&join(&injected))
            .expect_err("empty interior line")
            .kind(),
        AnalysisWireErrorKind::EmptyLine
    );
}

#[test]
fn missing_footer_is_refused() {
    let text = render(&wrap(TYPED_BODY));
    let all = lines(&text);
    let without_footer = join(&all[..all.len() - 1]);
    assert_eq!(
        inspect_npa_analysis_wire(&without_footer)
            .expect_err("footer is mandatory")
            .kind(),
        AnalysisWireErrorKind::EnvelopeStructural
    );
}

#[test]
fn trailing_record_after_footer_is_refused() {
    let text = render(&wrap(TYPED_BODY));
    let mut trailing = text.clone();
    trailing.push_str("{\"family\":\"diagnostic\"}\n");
    assert_eq!(
        inspect_npa_analysis_wire(&trailing)
            .expect_err("footer must be last")
            .kind(),
        AnalysisWireErrorKind::EnvelopeStructural
    );
}

#[test]
fn misordered_manifest_and_policies_are_refused() {
    let text = render(&wrap(TYPED_BODY));
    let mut all = lines(&text);
    all.swap(0, 1);
    assert_eq!(
        inspect_npa_analysis_wire(&join(&all))
            .expect_err("manifest must be line 0")
            .kind(),
        AnalysisWireErrorKind::EnvelopeStructural
    );
}

// ------------------------------------------------------- stop-signs #

#[test]
fn temporal_field_is_refused() {
    let text = render(&wrap(TYPED_BODY));
    let hostile = add_field_to_first_record(&text, "\"edition_date\":\"2020-01-01\",");
    assert_eq!(
        inspect_npa_analysis_wire(&hostile)
            .expect_err("temporal stop-sign")
            .kind(),
        AnalysisWireErrorKind::TemporalFieldForbidden
    );
}

#[test]
fn corpus_transfer_is_refused() {
    let text = render(&wrap(TYPED_BODY));
    let hostile = add_field_to_first_record(&text, "\"text\":\"inline corpus\",");
    assert_eq!(
        inspect_npa_analysis_wire(&hostile)
            .expect_err("inline corpus text")
            .kind(),
        AnalysisWireErrorKind::CorpusTransferForbidden
    );
}

// ----------------------------------------------------------- limits #

#[test]
fn record_limit_refusal_happens_before_write() {
    let kind = render_with(
        &wrap(TYPED_BODY),
        AnalysisLimits {
            max_records: 0,
            ..AnalysisLimits::default()
        },
    )
    .expect_err("record limit must refuse");
    assert_eq!(kind, AnalysisWireErrorKind::RecordsLimit);
}

#[test]
fn line_limit_refusal_happens_before_write() {
    let kind = render_with(
        &wrap(TYPED_BODY),
        AnalysisLimits {
            max_line_bytes: 8,
            ..AnalysisLimits::default()
        },
    )
    .expect_err("line limit must refuse");
    assert_eq!(kind, AnalysisWireErrorKind::LineBytesLimit);
}

// --------------------------------------------------- completion honesty #

#[test]
fn refused_record_is_not_promoted() {
    let text = render(&wrap(SPLIT_BODY));
    let summary = inspect_npa_analysis_wire(&text).expect("honest refusal inspects");
    assert_eq!(summary.completion, "incomplete");
    assert_eq!(summary.completion_basis, "refused_record");
    assert_eq!(
        summary.incomplete_reasons,
        vec!["refused_record".to_string()]
    );

    let promoted = text.replace(
        "\"completion\":\"incomplete\"",
        "\"completion\":\"complete\"",
    );
    assert_eq!(
        inspect_npa_analysis_wire(&promoted)
            .expect_err("a refusal cannot be presented as complete")
            .kind(),
        AnalysisWireErrorKind::RefusedRecordNotPromoted
    );
}

// ------------------------------------------------- structure-only inspect #

#[test]
fn inspect_does_not_recompute_seals() {
    let text = render(&wrap(TYPED_BODY));
    // Adding a benign field changes the record bytes (and therefore the seals),
    // but `inspect` is structure-only: it must not recompute or reject.
    let mutated = add_field_to_first_record(&text, "\"note\":\"x\",");
    assert_ne!(mutated, text, "the mutation changed the record line");
    inspect_npa_analysis_wire(&mutated)
        .expect("inspect does not recompute seals, so the stale seal is not rechecked");
}

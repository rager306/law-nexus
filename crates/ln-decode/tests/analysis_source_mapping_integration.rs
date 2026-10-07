//! T03 integration battery (M214-es3jvw S01).
//!
//! Connects the existing evidence pipeline (`source_package::capture` →
//! `reader_projection::build_projection`) to the T02 source-mapping seam on the
//! approved reader fixtures and one declared real input. The mapping is built
//! exclusively from the pipeline output: fragment ids and decoded text come from
//! the `ReaderRecordIndex`, never from a hand-copied literal, and every resolved
//! span is asserted to be the exact UTF-8 slice of the substrate text.
//!
//! Cases: valid spans, block→fragment mapping, tampered parent identity,
//! cross-document fragment, and the cleaned-wire `Hold`/`TextOnly` completion
//! bases (which must not change source coordinates).
//!
//! Non-claims: this battery is `[bounded]` to the named fixtures and the single
//! declared real input. It is **not** corpus coverage, **not** source
//! authenticity, **not** a full analysis/context export and **not** semantic
//! gold. The declared real input is the tracked bounded Consultant fixture, not
//! the restricted corpus (`consru_export/exports/`); only counts and sha256 are
//! asserted, and no decoded legal text is copied into tracked evidence. Frozen
//! oracles are not modified.

use std::collections::BTreeSet;
use std::fs;
use std::path::PathBuf;

use ln_decode::analysis_source_mapping::{
    check_coordinate_kind, check_no_corpus_transfer, check_temporal_fields, check_token_span,
    check_token_view, CoordinateKind, MappingRefusal, MappingRefusalKind, SourceIdentity,
    SourceMapping, TokenView,
};
use ln_decode::cleaned_completion::{classify_completion, ScopeDeclaration};
use ln_decode::cleaned_wire::{IncompleteReason, WireCompletion};
use ln_decode::document_context::DocumentVersionRef;
use ln_decode::npa_analysis_records::build_analysis_block_layout;
use ln_decode::npa_anchor::LocalSpan;
use ln_decode::reader_contract::{FragmentRef, ReaderFragmentSpan, ReaderRecordIndex};
use ln_decode::reader_gate::{gate_reader, ReaderSourceClass};
use ln_decode::reader_projection::{build_projection, ReaderProjection};
use ln_decode::source_package::{capture, Limits, Package, Record, MODEL, PROFILE};
use sha2::{Digest, Sha256};

// --------------------------------------------------------------- fixtures #

/// One approved, sha256-pinned synthetic reader fixture.
#[derive(Clone, Copy)]
struct Fixture {
    file: &'static str,
    xml: &'static str,
    sha256: &'static str,
}

const MIXED: Fixture = Fixture {
    file: "mixed-wordml.xml",
    xml: include_str!("fixtures/reader/mixed-wordml.xml"),
    sha256: "d2fc1cd17f0697f575e94f09d83da5027d73afd37c700772eafa4c4a4fbc76db",
};

const CONTROLS: Fixture = Fixture {
    file: "controls.xml",
    xml: include_str!("fixtures/reader/diverse/controls.xml"),
    sha256: "86440c8cf2f16b88f9da919c77f04e9a2487ed3a0032305dd195aaf48e40988f",
};

const TEXT_ONLY: Fixture = Fixture {
    file: "text-only.xml",
    xml: include_str!("fixtures/reader/diverse/text-only.xml"),
    sha256: "e13b8c7424100989028d95bd4c37bfadcd3970972329d93624c8da384507c55f",
};

const APPROVED: &[Fixture] = &[MIXED, CONTROLS, TEXT_ONLY];

/// The single declared real input: a tracked bounded Consultant WordML fixture
/// (not the restricted corpus). Pinned by byte length and sha256.
const REAL_INPUT: &str =
    "law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml";
const REAL_INPUT_SHA256: &str = "62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d";
const REAL_INPUT_BYTES: usize = 193_726;

fn real_input_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(REAL_INPUT)
}

// -------------------------------------------------------------- pipeline #

/// Captures an approved fixture and re-pins its sha256 oracle from the bytes on
/// disk, so a content drift fails loud instead of silently rebasing.
fn capture_fixture(fixture: &Fixture) -> Package {
    let package = capture(fixture.xml.as_bytes(), &Limits::default())
        .unwrap_or_else(|error| panic!("{} must capture: {error:?}", fixture.file));
    assert_eq!(
        package.manifest().source.sha256,
        fixture.sha256,
        "{}: content changed; re-pin the sha256 oracle",
        fixture.file
    );
    package
}

fn project(package: &Package) -> ReaderProjection {
    build_projection(package.records()).expect("a captured package must project")
}

/// Pinned parent evidence identity from the captured package itself (manifest +
/// footer) — the pipeline is the identity authority, not a local literal.
fn identity_of(package: &Package) -> SourceIdentity {
    SourceIdentity::try_new(
        package.manifest().source.sha256.clone(),
        package.manifest().source.bytes,
        MODEL.to_string(),
        package.footer().records_seal_hash.clone(),
        package.footer().manifest_hash.clone(),
    )
    .expect("a captured package yields a well-formed parent identity")
}

/// One document version triple bound to the decoded source revision.
fn version_of(package: &Package, document_version_ref: &str) -> DocumentVersionRef {
    DocumentVersionRef::try_new(
        document_version_ref.to_string(),
        package.manifest().source.sha256.clone(),
        PROFILE.to_string(),
    )
    .expect("a captured package yields a well-formed document version triple")
}

fn record_counts(package: &Package) -> (usize, usize) {
    let mut elements = 0usize;
    let mut texts = 0usize;
    for record in package.records() {
        match record {
            Record::Element(_) => elements += 1,
            Record::Text(_) => texts += 1,
        }
    }
    (elements, texts)
}

/// A `SourceMapping` built from the pipeline: the fragment catalog is populated
/// by walking the projected source segments and reading each fragment's decoded
/// text from the reader substrate index, and the block→fragment rule maps each
/// distinct fragment to a caller-side analysis block.
fn mapping_from_pipeline(
    package: &Package,
    projection: &ReaderProjection,
    document_version_ref: &str,
) -> SourceMapping {
    let index = ReaderRecordIndex::new(package.records())
        .expect("captured records must index as substrate");
    let document = identity_of(package);
    let mut mapping =
        SourceMapping::new(document.clone(), version_of(package, document_version_ref));

    let mut seen: BTreeSet<String> = BTreeSet::new();
    let mut block = 0usize;
    for segment in &projection.segments {
        let Some(fragment) = &segment.fragment_ref else {
            continue;
        };
        if segment.origin.derived_kind().is_some() {
            continue;
        }
        if !seen.insert(fragment.as_str().to_string()) {
            continue;
        }
        let text = index.text(fragment.as_str()).unwrap_or_else(|| {
            panic!("segment names fragment {fragment} absent from the captured substrate")
        });
        mapping
            .pin_fragment(fragment.clone(), text.value.clone(), &document)
            .unwrap_or_else(|error| panic!("fragment {fragment} must pin: {error}"));
        mapping
            .map_block(block, fragment.clone())
            .unwrap_or_else(|error| panic!("block {block} must map to {fragment}: {error}"));
        block += 1;
    }
    mapping
}

fn whole_span(fragment: &FragmentRef, text: &str) -> ReaderFragmentSpan {
    ReaderFragmentSpan::new(fragment.clone(), 0, text.len())
}

fn kind_of<T>(result: Result<T, MappingRefusal>) -> MappingRefusalKind {
    match result {
        Ok(_) => panic!("input must be refused"),
        Err(refusal) => refusal.kind(),
    }
}

/// Asserts every projected source segment resolves through the seam to the
/// exact substrate UTF-8 slice, and every analyzed block resolves to its whole
/// fragment. Returns `(source_segments, resolved_bytes)` for the evidence
/// receipt.
fn assert_pipeline_resolves(
    package: &Package,
    projection: &ReaderProjection,
    mapping: &SourceMapping,
    label: &str,
) -> (usize, u64) {
    let index = ReaderRecordIndex::new(package.records())
        .expect("captured records must index as substrate");
    let mut source_segments = 0usize;
    let mut resolved_bytes = 0u64;

    for segment in &projection.segments {
        let Some(fragment) = &segment.fragment_ref else {
            continue;
        };
        if segment.origin.derived_kind().is_some() {
            continue;
        }
        let text = index
            .text(fragment.as_str())
            .unwrap_or_else(|| panic!("{label}: fragment {fragment} absent from substrate"));
        let span = segment
            .span
            .clone()
            .unwrap_or_else(|| whole_span(fragment, &text.value));
        let resolved = mapping
            .resolve_fragment_span(&span)
            .unwrap_or_else(|error| panic!("{label}: span on {fragment} must resolve: {error}"));
        let expected = &text.value[span.start..span.end];
        let slice = mapping
            .slice(&resolved)
            .unwrap_or_else(|error| panic!("{label}: resolved span must slice: {error}"));
        assert_eq!(
            slice, expected,
            "{label}: resolved slice must be the substrate slice"
        );
        assert_eq!(
            (resolved.start, resolved.end),
            (span.start, span.end),
            "{label}: resolved coordinates must be preserved"
        );
        source_segments += 1;
        resolved_bytes += slice.len() as u64;
    }

    assert!(
        source_segments > 0,
        "{label}: the pipeline must expose at least one source fragment"
    );

    // The caller-side block rule resolves the whole fragment for every pinned
    // block, deduplicating fragments so each block index corresponds to exactly
    // one catalog entry.
    let mut seen_blocks: BTreeSet<String> = BTreeSet::new();
    let mut blocks = 0usize;
    for segment in &projection.segments {
        let Some(fragment) = &segment.fragment_ref else {
            continue;
        };
        if segment.origin.derived_kind().is_some() {
            continue;
        }
        if !seen_blocks.insert(fragment.as_str().to_string()) {
            continue;
        }
        let text = index.text(fragment.as_str()).expect("substrate text");
        let resolved = mapping
            .resolve_local_span(LocalSpan {
                block: blocks,
                start: 0,
                end: text.value.len(),
            })
            .unwrap_or_else(|error| panic!("{label}: block {blocks} must resolve: {error}"));
        assert_eq!(
            mapping.slice(&resolved).expect("block slice"),
            text.value.as_str(),
            "{label}: block {blocks} must resolve to its whole fragment"
        );
        blocks += 1;
    }
    assert_eq!(
        blocks,
        mapping.fragment_count(),
        "{label}: every pinned fragment must be reachable by block"
    );

    (source_segments, resolved_bytes)
}

// ------------------------------------------------------- positive battery #

#[test]
fn approved_fixtures_resolve_from_the_capture_reader_pipeline() {
    for fixture in APPROVED {
        let package = capture_fixture(fixture);
        assert_eq!(
            gate_reader(package.records()).expect("a captured fixture must gate"),
            ReaderSourceClass::SupportedWordml,
            "{}: approved fixture must be supported WordML",
            fixture.file
        );
        let projection = project(&package);
        let document_version_ref = format!("reader-fixture:{}", fixture.file);
        let mapping = mapping_from_pipeline(&package, &projection, &document_version_ref);

        let (segments, bytes) =
            assert_pipeline_resolves(&package, &projection, &mapping, fixture.file);
        assert!(
            mapping.fragment_count() > 0,
            "{}: catalog pinned",
            fixture.file
        );
        // Identity and version checks are satisfied by the pipeline's own
        // output, not by a hand-authored claim.
        assert_eq!(
            mapping.check_parent_citation(&identity_of(&package)),
            Ok(())
        );
        assert_eq!(
            mapping.check_document_version(&version_of(&package, &document_version_ref)),
            Ok(())
        );
        let (elements, texts) = record_counts(&package);
        // Portable receipt: counts and file identity only, no legal text.
        eprintln!(
            "m214_s01 fixture={} bytes={} sha256={} elements={} text_records={} fragments={} source_segments={} resolved_bytes={}",
            fixture.file,
            fixture.xml.len(),
            fixture.sha256,
            elements,
            texts,
            mapping.fragment_count(),
            segments,
            bytes,
        );
    }
}

#[test]
fn declared_real_input_is_bounded_and_resolves() {
    let path = real_input_path();
    let xml = fs::read(&path).unwrap_or_else(|error| panic!("{REAL_INPUT}: {error}"));
    assert_eq!(
        xml.len(),
        REAL_INPUT_BYTES,
        "{REAL_INPUT}: byte length drift"
    );
    assert_eq!(
        format!("{:x}", Sha256::digest(&xml)),
        REAL_INPUT_SHA256,
        "{REAL_INPUT}: content drift; re-pin the sha256 oracle"
    );

    let package = capture(&xml, &Limits::default()).expect("declared real input must capture");
    assert_eq!(package.manifest().source.sha256, REAL_INPUT_SHA256);
    assert_eq!(
        gate_reader(package.records()).expect("declared real input must gate"),
        ReaderSourceClass::SupportedWordml
    );
    let projection = project(&package);
    let mapping = mapping_from_pipeline(&package, &projection, "declared-real:435-fz-d71bf702");
    let (segments, bytes) = assert_pipeline_resolves(&package, &projection, &mapping, REAL_INPUT);

    // The envelope carries no inline decoded text; a supplied text channel is a
    // closed refusal, so the restricted corpus is never re-carried.
    assert_eq!(check_no_corpus_transfer(None), Ok(()));
    assert_eq!(
        kind_of(check_no_corpus_transfer(Some(
            "restricted corpus would go here"
        ))),
        MappingRefusalKind::CorpusTransferForbidden
    );

    let (elements, texts) = record_counts(&package);
    eprintln!(
        "m214_s01 real_input={} bytes={} sha256={} elements={} text_records={} fragments={} source_segments={} resolved_bytes={}",
        REAL_INPUT,
        xml.len(),
        REAL_INPUT_SHA256,
        elements,
        texts,
        mapping.fragment_count(),
        segments,
        bytes,
    );
}

#[test]
fn token_views_connect_to_real_fragments_and_stay_separate() {
    let package = capture_fixture(&MIXED);
    let projection = project(&package);
    let mapping = mapping_from_pipeline(&package, &projection, "reader-fixture:mixed-wordml.xml");
    let index = ReaderRecordIndex::new(package.records()).expect("substrate index");

    let text = projection
        .segments
        .iter()
        .filter(|segment| segment.origin.derived_kind().is_none())
        .filter_map(|segment| segment.fragment_ref.as_ref())
        .find_map(|fragment| {
            index
                .text(fragment.as_str())
                .map(|record| record.value.clone())
        })
        .expect("the fixture exposes a decodable fragment");
    let token = ln_decode::lexer::lex(&text)
        .into_iter()
        .next()
        .expect("a non-empty fragment yields a covering token");
    assert_eq!(
        check_token_span(
            &text,
            TokenView::Covering,
            token.span.start(),
            token.span.end()
        ),
        Ok(())
    );
    // A morphology outcome may not declare the alphabetic view: mixing the two
    // views is a closed refusal.
    assert_eq!(
        kind_of(check_token_view(
            TokenView::CoveringWord,
            TokenView::Alphabetic
        )),
        MappingRefusalKind::TokenViewMismatch
    );
    assert!(mapping.fragment_count() > 0);
}

// ----------------------------- F04 coordinate surfaces (real pipeline) #

/// Synthetic two-fragment WordML on which both the S01 block→fragment seam and
/// the S02 analysis-block layout are built from the same `capture ->
/// build_projection` pipeline.
const TWO_RUNS_WORDML: &str = "<w:wordDocument xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\"><w:body><w:p><w:r><w:t>Alpha</w:t></w:r><w:r><w:t>Beta</w:t></w:r></w:p></w:body></w:wordDocument>";

/// R29-F04: the S01 caller-declared block rule and the S02 analysis-block
/// coordinate are two distinct surfaces over the same numeric block index.
/// They are not interchangeable — the same `block: 0, 5..9` coordinate is
/// `out_of_bounds` on the seam (fragment `Alpha` is five bytes) but resolves to
/// the second fragment `(0,4)` on the analysis layout — and each misuse is a
/// closed refusal. Both surfaces are built from one real pipeline run.
#[test]
fn s01_and_analysis_coordinates_are_not_interchangeable() {
    let package = capture(TWO_RUNS_WORDML.as_bytes(), &Limits::default())
        .expect("the two-run fixture must capture");
    let index = ReaderRecordIndex::new(package.records()).expect("substrate index");
    let projection = project(&package);
    let mut mapping = mapping_from_pipeline(&package, &projection, "reader-fixture:two-runs");

    // S01 seam: block 0 is the first fragment (Alpha), block 1 the second (Beta).
    let alpha = mapping
        .resolve_local_span(LocalSpan {
            block: 0,
            start: 0,
            end: 5,
        })
        .expect("block 0 resolves to the first fragment");
    assert_eq!(mapping.slice(&alpha).expect("slice"), "Alpha");
    let beta = mapping
        .resolve_local_span(LocalSpan {
            block: 1,
            start: 0,
            end: 4,
        })
        .expect("block 1 resolves to the second fragment");
    assert_eq!(mapping.slice(&beta).expect("slice"), "Beta");

    // Analysis surface: the same numeric block 1 does not exist — the analysis
    // layout has exactly one block (one primary view).
    let layout = build_analysis_block_layout(&projection, &index).expect("layout builds");
    assert_eq!(layout.block_count(), 1, "one primary view -> one block");
    assert_eq!(
        layout
            .localize(LocalSpan {
                block: 1,
                start: 0,
                end: 4,
            })
            .expect_err("analysis block 1 does not exist")
            .token(),
        "unmapped_block"
    );

    // The S01 block 0 range 5..9 is out of bounds (its fragment is "Alpha"),
    // while the analysis block 0 range 5..9 is the second fragment's "Beta".
    assert_eq!(
        kind_of(mapping.resolve_local_span(LocalSpan {
            block: 0,
            start: 5,
            end: 9,
        })),
        MappingRefusalKind::OutOfBounds,
        "the S01 fragment for block 0 is five bytes long"
    );
    let block = layout.block(0).expect("one analysis block");
    let bound = layout
        .localize(LocalSpan {
            block: 0,
            start: 5,
            end: 9,
        })
        .expect("the analysis coordinate resolves to the second fragment");
    assert_eq!(bound.fragment, block.segments[1].fragment);
    assert_eq!((bound.start, bound.end), (0, 4));
    let resolved = mapping
        .resolve_fragment_span(&bound.as_fragment_span())
        .expect("the analysis bound span resolves through the S01 seam");
    assert_eq!(mapping.slice(&resolved).expect("slice"), "Beta");

    // Misuse is closed: an unmapped block is `unsupported_mapping`, and a remap
    // of an already-declared block is a structural refusal.
    assert_eq!(
        kind_of(mapping.resolve_local_span(LocalSpan {
            block: 7,
            start: 0,
            end: 1,
        })),
        MappingRefusalKind::UnsupportedMapping
    );
    assert_eq!(
        kind_of(mapping.map_block(0, FragmentRef::new("remapped-fragment"))),
        MappingRefusalKind::EnvelopeStructural
    );
}

// ------------------------------------------------------- negative battery #

#[test]
fn tampered_parent_identity_is_refused() {
    let package = capture_fixture(&MIXED);
    let projection = project(&package);
    let mapping = mapping_from_pipeline(&package, &projection, "reader-fixture:mixed-wordml.xml");
    let genuine = identity_of(&package);

    // Different sha256 with the same shape: the citation no longer matches.
    let foreign_sha = SourceIdentity::try_new(
        "0".repeat(64),
        genuine.source_bytes,
        genuine.parent_schema.clone(),
        genuine.records_seal_hash.clone(),
        genuine.manifest_hash.clone(),
    )
    .expect("a 64-hex sha is well formed");
    assert_eq!(
        kind_of(mapping.check_parent_citation(&foreign_sha)),
        MappingRefusalKind::SourceIdentityMismatch
    );

    // The envelope claims a frame seal the cited (unsealed) parent does not
    // carry; the claim is refused rather than trusted.
    let unsealed = SourceIdentity::try_new(
        genuine.source_sha256.clone(),
        genuine.source_bytes,
        genuine.parent_schema.clone(),
        None,
        None,
    )
    .expect("an unsealed identity is well formed");
    assert_eq!(
        kind_of(mapping.check_parent_citation(&unsealed)),
        MappingRefusalKind::SourceIdentityMismatch
    );

    // A record whose decoding revision differs from the envelope's version.
    let foreign_version = DocumentVersionRef::try_new(
        "reader-fixture:mixed-wordml.xml".to_string(),
        "0000000000000000000000000000000000000000000000000000000000000000".to_string(),
        PROFILE.to_string(),
    )
    .expect("well formed");
    assert_eq!(
        kind_of(mapping.check_document_version(&foreign_version)),
        MappingRefusalKind::DocumentVersionMismatch
    );

    // An unsupported coordinate system is a closed refusal, never a rebase.
    assert_eq!(
        kind_of(check_coordinate_kind(CoordinateKind::XmlArtifactSpan)),
        MappingRefusalKind::UnsupportedMapping
    );
    assert_eq!(
        kind_of(check_temporal_fields(&["fragment_ref", "effective_from"])),
        MappingRefusalKind::TemporalFieldForbidden
    );
}

#[test]
fn cross_document_fragment_is_refused() {
    let package_a = capture_fixture(&MIXED);
    let projection_a = project(&package_a);
    let mut mapping =
        mapping_from_pipeline(&package_a, &projection_a, "reader-fixture:mixed-wordml.xml");

    let package_b = capture_fixture(&TEXT_ONLY);
    let projection_b = project(&package_b);
    let identity_b = identity_of(&package_b);
    assert_ne!(
        identity_b.source_sha256,
        identity_of(&package_a).source_sha256,
        "the two fixtures must be distinct documents"
    );
    let index_b = ReaderRecordIndex::new(package_b.records()).expect("substrate index");
    let foreign_fragment = projection_b
        .segments
        .iter()
        .find_map(|segment| segment.fragment_ref.clone())
        .expect("text-only fixture exposes a fragment");
    let foreign_text = index_b
        .text(foreign_fragment.as_str())
        .expect("foreign fragment text")
        .value
        .clone();

    assert_eq!(
        kind_of(mapping.pin_fragment(foreign_fragment, foreign_text, &identity_b)),
        MappingRefusalKind::CrossDocument
    );
}

#[test]
fn hold_and_text_only_bases_do_not_change_source_coordinates() {
    for fixture in [MIXED, TEXT_ONLY] {
        let package = capture_fixture(&fixture);
        let records = package.records();
        let source_class = gate_reader(records).expect("fixture must gate");
        assert_eq!(source_class, ReaderSourceClass::SupportedWordml);

        // The producer declares a partial basis; the closed completion maps to
        // the frozen Hold/TextOnly vocabulary.
        assert_eq!(
            classify_completion(source_class, ScopeDeclaration::StructureHold),
            WireCompletion::Incomplete {
                basis: IncompleteReason::Hold,
                reasons: vec![IncompleteReason::Hold],
            }
        );
        assert_eq!(
            classify_completion(source_class, ScopeDeclaration::TextOnlyScope),
            WireCompletion::Incomplete {
                basis: IncompleteReason::TextOnly,
                reasons: vec![IncompleteReason::TextOnly],
            }
        );

        // Regardless of the cleaned-structure completion basis, identity and
        // coordinates resolve the same way: the source boundary is independent
        // of structural completion.
        let projection = project(&package);
        let mapping = mapping_from_pipeline(
            &package,
            &projection,
            &format!("reader-fixture:{}", fixture.file),
        );
        let (segments, _) = assert_pipeline_resolves(&package, &projection, &mapping, fixture.file);
        assert!(segments > 0, "{}: source segments present", fixture.file);
    }
}

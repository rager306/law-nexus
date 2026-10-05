//! T05 integration battery (M214-es3jvw S02).
//!
//! End-to-end document-scoped NPA analysis over the real pipeline:
//! `source_package::capture` → `reader_gate::gate_reader` →
//! `reader_projection::build_projection` → `npa_analysis_records::analyze_document`
//! (block layout → typed → linked → relations → classifications → diagnostics)
//! → `npa_analysis_wire::render_npa_analysis` →
//! `inspect_npa_analysis_wire`.
//!
//! Inputs are the three approved reader fixtures and the single declared
//! bounded real input (Consultant 435-ФЗ WordML, pinned by byte length and
//! sha256). The battery asserts: every bound record span resolves to the exact
//! substrate UTF-8 slice; a span that straddles two fragments is a closed
//! refusal (`cross_fragment`, or `derived_separator` when it crosses a typed
//! derived boundary); unresolved typed members are not promoted; the
//! parent identity, parent seals and document version are pinned; tamper,
//! cross-document and version-mismatch are refused; the envelope is
//! structurally valid, carries no inline decoded corpus text and no temporal
//! stop-sign fields; and the portable receipt
//! `prd/migration/rust-evidence/m214-s02-analysis-export.json` is count/hash
//! only and matches the live pipeline.
//!
//! S03 T05 extends the same battery with the opt-in seventh `context` family:
//! `npa_context_records::build_context_records` →
//! `render_npa_analysis_with_context` → `read_back_npa_analysis` →
//! `verify_npa_analysis_wire`, whose independent verifier re-derives the
//! canonical records from the pinned parent and detects a resealed member-span
//! or fragment substitution. The S02 six-family envelope stays byte-identical.
//!
//! Non-claims: this battery is `[bounded]` to the named fixtures and the one
//! declared real input. It is **not** corpus coverage, **not** source
//! authenticity and **not** semantic/legal gold; context outcomes are
//! structural candidates only. R1000 stays active and unclosed. Frozen oracles
//! and the M213 cleaned wire bytes are not modified. Raw decoded corpus text is
//! never logged: the receipts record counts, closed codes and sha256 only.

use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;

use ln_decode::analysis_source_mapping::{
    check_temporal_fields, MappingRefusalKind, SourceIdentity, SourceMapping,
    TEMPORAL_FORBIDDEN_FIELDS,
};
use ln_decode::document_context::{ContextStatus, DocumentVersionRef};
use ln_decode::npa_analysis_records::{
    analyze_document, resolve_span, AnalysisRefusalKind, DocumentAnalysis, SourceRef,
};
use ln_decode::npa_analysis_verify::{
    read_back_npa_analysis, verify_npa_analysis_wire, AnalysisVerifyCode, AnalysisVerifyFinding,
};
use ln_decode::npa_analysis_wire::{
    inspect_npa_analysis_wire, recompute_analysis_seals, render_npa_analysis,
    render_npa_analysis_with_context, AnalysisEnvelopeRequest, AnalysisLimits, AnalysisScope,
};
use ln_decode::npa_anchor::LocalSpan;
use ln_decode::npa_context_records::{
    build_context_records, diagnostic_token, status_token, ContextRecord,
};
use ln_decode::npa_typed::TypeDerivation;
use ln_decode::reader_contract::{FragmentRef, ReaderRecordIndex};
use ln_decode::reader_gate::{gate_reader, ReaderSourceClass};
use ln_decode::reader_projection::{build_projection, ReaderProjection};
use ln_decode::source_package::{capture, Limits, Package, MODEL, PROFILE};
use serde_json::json;
use sha2::{Digest, Sha256};

// --------------------------------------------------------------- fixtures #

/// One approved, sha256-pinned synthetic reader fixture (non-legal content).
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
const REAL_DOC_VERSION: &str = "declared-real:435-fz-d71bf702";

/// Inline synthetic two-run paragraph: one primary view, two source-fragment
/// segments, so a whole-block span straddles them.
const TWO_RUNS: &str = "<w:wordDocument xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\"><w:body><w:p><w:r><w:t>Alpha</w:t></w:r><w:r><w:t>Beta</w:t></w:r></w:p></w:body></w:wordDocument>";

const RECEIPT_REL: &str = "prd/migration/rust-evidence/m214-s02-analysis-export.json";

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn real_input_path() -> PathBuf {
    repo_root().join(REAL_INPUT)
}

fn hex_lower(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push_str(&format!("{byte:02x}"));
    }
    out
}

fn file_sha256(rel: &str) -> String {
    let path = repo_root().join(rel);
    let bytes = fs::read(&path).unwrap_or_else(|error| panic!("{rel}: {error}"));
    hex_lower(&Sha256::digest(&bytes))
}

// -------------------------------------------------------------- pipeline #

struct Pipeline {
    package: Package,
    index: ReaderRecordIndex,
    mapping: SourceMapping,
    analysis: DocumentAnalysis,
    projection: ReaderProjection,
    /// The byte-stable S02 six-family envelope (empty context slice).
    envelope: String,
    /// The S03 context records derived from the same analysis layout.
    contexts: Vec<ContextRecord>,
    /// The opt-in seven-family context envelope.
    context_envelope: String,
}

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

fn version_of(package: &Package, document_version_ref: &str) -> DocumentVersionRef {
    DocumentVersionRef::try_new(
        document_version_ref.to_string(),
        package.manifest().source.sha256.clone(),
        PROFILE.to_string(),
    )
    .expect("a captured package yields a well-formed document version triple")
}

/// Runs the real pipeline and renders the analysis envelope. The fragment
/// catalog is populated from `ReaderRecordIndex`, never a hand-copied literal.
fn build_pipeline(xml: &[u8], document_version_ref: &str, label: &str) -> Pipeline {
    let package = capture(xml, &Limits::default())
        .unwrap_or_else(|error| panic!("{label}: capture must succeed: {error:?}"));
    assert_eq!(
        gate_reader(package.records()).unwrap_or_else(|error| panic!("{label}: gate: {error:?}")),
        ReaderSourceClass::SupportedWordml,
        "{label}: approved/declared input must gate as supported WordML"
    );
    let index = ReaderRecordIndex::new(package.records())
        .unwrap_or_else(|error| panic!("{label}: substrate index: {error:?}"));
    let projection = build_projection(package.records())
        .unwrap_or_else(|error| panic!("{label}: projection: {error:?}"));
    let identity = identity_of(&package);
    let version = version_of(&package, document_version_ref);
    let mut mapping = SourceMapping::new(identity.clone(), version);
    for text in index.texts() {
        mapping
            .pin_fragment(
                FragmentRef::from(text.id.as_str()),
                text.value.clone(),
                &identity,
            )
            .unwrap_or_else(|error| panic!("{label}: fragment {} must pin: {error}", text.id));
    }
    let analysis = analyze_document(&projection, &index, &mapping)
        .unwrap_or_else(|error| panic!("{label}: document analysis must build: {error}"));
    let request = AnalysisEnvelopeRequest {
        analysis: &analysis,
        projection: &projection,
        index: &index,
        mapping: &mapping,
        limits: AnalysisLimits::default(),
        scope: AnalysisScope::Bounded,
    };
    // The S02 six-family envelope stays the empty-context path (D662).
    let envelope = render_npa_analysis(&request)
        .unwrap_or_else(|error| panic!("{label}: envelope must render: {error}"));
    // The S03 seventh `context` family over the same pinned parent.
    let contexts = build_context_records(&analysis.layout, &mapping);
    let context_envelope = render_npa_analysis_with_context(&request, &contexts)
        .unwrap_or_else(|error| panic!("{label}: context envelope must render: {error}"));
    Pipeline {
        package,
        index,
        mapping,
        analysis,
        projection,
        envelope,
        contexts,
        context_envelope,
    }
}

// ------------------------------------------------------- span invariants #

fn for_each_source_ref(analysis: &DocumentAnalysis, mut visit: impl FnMut(&SourceRef)) {
    for member in &analysis.typed {
        visit(&member.span);
        if let Some(evidence) = &member.type_evidence {
            visit(evidence);
        }
        for alternative in &member.alternatives {
            visit(&alternative.span);
        }
    }
    for member in &analysis.linked {
        visit(&member.evidence);
        for reference in &member.provenance {
            visit(reference);
        }
    }
    for relation in &analysis.relations {
        for reference in &relation.evidence {
            visit(reference);
        }
    }
    for record in &analysis.classifications {
        visit(&record.evidence);
    }
    for diagnostic in &analysis.diagnostics {
        if let Some(span) = &diagnostic.span {
            visit(span);
        }
    }
}

/// Asserts every bound record span resolves to the exact substrate UTF-8 slice,
/// and every refused span carries a non-empty closed token. Returns
/// `(bound, refused)`.
fn assert_all_refs_resolve(pipeline: &Pipeline, label: &str) -> (usize, usize) {
    let mut bound = 0usize;
    let mut refused = 0usize;
    for_each_source_ref(&pipeline.analysis, |reference| match reference {
        SourceRef::Bound(span) => {
            let resolved = pipeline
                .mapping
                .resolve_fragment_span(&span.as_fragment_span())
                .unwrap_or_else(|error| panic!("{label}: bound span must resolve: {error}"));
            let slice = pipeline
                .mapping
                .slice(&resolved)
                .unwrap_or_else(|error| panic!("{label}: resolved span must slice: {error}"));
            let substrate = pipeline
                .index
                .text(span.fragment.as_str())
                .unwrap_or_else(|| panic!("{label}: fragment {} absent", span.fragment));
            assert_eq!(
                slice,
                &substrate.value[span.start..span.end],
                "{label}: resolved slice must be the exact substrate slice"
            );
            assert!(
                span.start < span.end,
                "{label}: a bound span is a non-empty range"
            );
            bound += 1;
        }
        SourceRef::Refused(refusal) => {
            assert!(
                !refusal.token().is_empty(),
                "{label}: a refusal carries a closed token"
            );
            refused += 1;
        }
    });
    (bound, refused)
}

fn count_resolved_typed(analysis: &DocumentAnalysis) -> usize {
    analysis.typed.iter().filter(|m| m.span.is_bound()).count()
}

fn assert_document_outcome(pipeline: &Pipeline, label: &str, document_version_ref: &str) {
    assert!(
        pipeline.analysis.layout.block_count() > 0,
        "{label}: the document must expose at least one analysis block"
    );

    let (_bound, refused) = assert_all_refs_resolve(pipeline, label);
    let resolved_typed = count_resolved_typed(&pipeline.analysis);
    let span_bearing = !pipeline.analysis.typed.is_empty()
        || !pipeline.analysis.linked.is_empty()
        || !pipeline.analysis.relations.is_empty()
        || !pipeline.analysis.classifications.is_empty();
    if span_bearing {
        assert!(
            resolved_typed > 0 || refused > 0,
            "{label}: analysis must be source-bound or explicitly refused, never a silent success"
        );
    }

    // Unresolved members keep their derivation and never invent a TYPE surface.
    for member in &pipeline.analysis.typed {
        if member.unresolved {
            assert_eq!(
                member.derivation,
                TypeDerivation::Unresolved,
                "{label}: unresolved keeps its derivation"
            );
            assert!(
                member.type_name.is_empty(),
                "{label}: an unresolved member has no TYPE surface"
            );
        }
    }

    // A multi-fragment block refuses a whole-block span that straddles its
    // fragments. When the block also carries a derived separator, the span
    // crosses that typed boundary first, so the closed refusal is
    // `derived_separator`; a boundary-free multi-fragment block still yields
    // `cross_fragment`. Neither path is rebased onto a fragment span nor
    // promoted to a source span.
    if let Some((block_index, block)) = pipeline
        .analysis
        .layout
        .blocks
        .iter()
        .enumerate()
        .find(|(_, block)| block.segments.len() >= 2)
    {
        let refusal = pipeline
            .analysis
            .layout
            .localize(LocalSpan {
                block: block_index,
                start: 0,
                end: block.text.len(),
            })
            .expect_err("a whole-block span over two fragments must be refused");
        let expected = if block.boundaries.is_empty() {
            AnalysisRefusalKind::CrossFragment.as_str()
        } else {
            AnalysisRefusalKind::DerivedSeparator.as_str()
        };
        assert_eq!(
            refusal.token(),
            expected,
            "{label}: a whole-block span over multiple source fragments stays a closed refusal \
             (derived_separator across a typed boundary, else cross_fragment)"
        );
    }

    // Parent identity and document version are pinned from the pipeline itself.
    assert_eq!(
        *pipeline.mapping.envelope(),
        identity_of(&pipeline.package),
        "{label}: the envelope pins the captured manifest identity"
    );
    assert_eq!(
        pipeline.mapping.version().document_version_ref(),
        document_version_ref,
        "{label}: version triple carries the declared document version ref"
    );
    assert_eq!(
        pipeline.mapping.version().source_revision(),
        pipeline.package.manifest().source.sha256,
        "{label}: source revision is the captured source sha256"
    );
    assert_eq!(
        pipeline.mapping.version().decoder_profile(),
        PROFILE,
        "{label}: decoder profile is the captured profile"
    );
    assert_eq!(
        pipeline
            .mapping
            .check_parent_citation(&identity_of(&pipeline.package)),
        Ok(()),
        "{label}: the pipeline's own parent citation verifies"
    );
    assert_eq!(
        pipeline
            .mapping
            .check_document_version(&version_of(&pipeline.package, document_version_ref)),
        Ok(()),
        "{label}: the pipeline's own document version verifies"
    );

    // Envelope shape, completion and recomputable, non-cyclic seals.
    let summary = inspect_npa_analysis_wire(&pipeline.envelope)
        .unwrap_or_else(|error| panic!("{label}: envelope must inspect: {error}"));
    assert_eq!(
        summary.families.get("document").copied(),
        Some(1),
        "{label}: exactly one document record"
    );
    assert_eq!(
        summary.families.values().sum::<u64>(),
        summary.records,
        "{label}: family counts sum to the record count"
    );
    let seals = recompute_analysis_seals(&pipeline.envelope)
        .unwrap_or_else(|error| panic!("{label}: seals must recompute: {error}"));
    assert_eq!(
        summary.records_seal_hash.as_deref(),
        Some(seals.records_seal_hash.as_str()),
        "{label}: footer records seal matches recomputation"
    );
    assert_eq!(
        summary.manifest_hash.as_deref(),
        Some(seals.manifest_hash.as_str()),
        "{label}: footer manifest hash matches recomputation"
    );
    assert_ne!(
        seals.records_seal_hash, seals.manifest_hash,
        "{label}: the two seals are distinct (non-cyclic chain)"
    );
    match summary.completion.as_str() {
        "complete" => {
            assert_eq!(summary.completion_basis, "bounded_analysis_complete");
            assert!(summary.incomplete_reasons.is_empty());
        }
        "incomplete" => {
            assert!(!summary.incomplete_reasons.is_empty());
            assert!(summary
                .incomplete_reasons
                .contains(&summary.completion_basis));
        }
        other => panic!("{label}: unknown completion token {other:?}"),
    }
    if refused > 0 {
        assert_eq!(summary.completion, "incomplete", "{label}");
        assert_eq!(
            summary.completion_basis, "refused_record",
            "{label}: a refused record is never promoted to complete"
        );
    }

    // No inline decoded corpus text and no temporal stop-sign field.
    for forbidden in [
        "\"text\":",
        "\"source_utf8\":",
        "\"inline_text\":",
        "\"decoded_text\":",
        "\"segment_text\":",
    ] {
        assert!(
            !pipeline.envelope.contains(forbidden),
            "{label}: envelope must not carry inline decoded text ({forbidden})"
        );
    }
    for field in TEMPORAL_FORBIDDEN_FIELDS {
        assert!(
            !pipeline.envelope.contains(&format!("\"{field}\":")),
            "{label}: envelope must not carry temporal field {field}"
        );
    }
    for line in pipeline.envelope.lines() {
        if line.contains("\"schema\":\"law-nexus/npa-analysis-fragment/v1\"") {
            assert!(
                line.contains("\"content_sha256\":\""),
                "{label}: a fragment record hashes its substrate"
            );
            assert!(
                line.contains("\"byte_length\":"),
                "{label}: a fragment record counts its bytes"
            );
        }
    }
}

// --------------------------------------------------------- measurements #

fn measure(pipeline: &Pipeline) -> serde_json::Value {
    let summary = inspect_npa_analysis_wire(&pipeline.envelope).expect("envelope inspects");
    let families: BTreeMap<String, u64> = summary.families.clone();
    let (_, refused) = assert_all_refs_resolve(pipeline, "receipt");
    json!({
        "blocks": pipeline.analysis.layout.block_count(),
        "classifications": pipeline.analysis.classifications.len(),
        "completion": summary.completion,
        "completion_basis": summary.completion_basis,
        "diagnostics": pipeline.analysis.diagnostics.len(),
        "envelope_lines": pipeline.envelope.lines().count(),
        "envelope_sha256": hex_lower(&Sha256::digest(pipeline.envelope.as_bytes())),
        "families": families,
        "linked_members": pipeline.analysis.linked.len(),
        "records": summary.records,
        "refused_refs": refused,
        "relations": pipeline.analysis.relations.len(),
        "resolved_typed_members": count_resolved_typed(&pipeline.analysis),
        "typed_members": pipeline.analysis.typed.len(),
        "unresolved_members": pipeline.analysis.typed.iter().filter(|m| m.unresolved).count(),
    })
}

fn collect_long_texts(pipeline: &Pipeline, out: &mut Vec<String>) {
    for text in pipeline.index.texts() {
        if text.value.chars().count() >= 24 && !out.contains(&text.value) {
            out.push(text.value.clone());
        }
    }
}

fn build_receipt_with_texts() -> (serde_json::Value, Vec<String>) {
    let mut fixtures: Vec<serde_json::Value> = Vec::new();
    let mut texts: Vec<String> = Vec::new();
    for fixture in APPROVED {
        let pipeline = build_pipeline(
            fixture.xml.as_bytes(),
            &format!("reader-fixture:{}", fixture.file),
            fixture.file,
        );
        collect_long_texts(&pipeline, &mut texts);
        fixtures.push(json!({
            "file": fixture.file,
            "sha256": fixture.sha256,
            "bytes": fixture.xml.len(),
            "measurement": measure(&pipeline),
        }));
    }

    let xml = fs::read(real_input_path()).expect("the declared real input must be readable");
    assert_eq!(
        xml.len(),
        REAL_INPUT_BYTES,
        "{REAL_INPUT}: byte length drift"
    );
    assert_eq!(
        hex_lower(&Sha256::digest(&xml)),
        REAL_INPUT_SHA256,
        "{REAL_INPUT}: content drift; re-pin the sha256 oracle"
    );
    let real = build_pipeline(&xml, REAL_DOC_VERSION, REAL_INPUT);
    collect_long_texts(&real, &mut texts);
    let declared_real_input = json!({
        "path": REAL_INPUT,
        "sha256": REAL_INPUT_SHA256,
        "bytes": REAL_INPUT_BYTES,
        "measurement": measure(&real),
    });

    let receipt = json!({
        "schema": "m214-s02-analysis-export/v1",
        "schema_version": 1,
        "lifecycle": "[bounded]",
        "milestone": "M214-es3jvw",
        "slice": "S02",
        "task": "T05",
        "generated_utc": std::env::var("M214_S02_GENERATED_UTC")
            .unwrap_or_else(|_| "unspecified".to_string()),
        "count_only": true,
        "ascii_only": true,
        "non_claims": [
            "this receipt is [bounded] to the three approved reader fixtures and the single declared real input; it is not corpus coverage",
            "the declared real input is one tracked bounded Consultant WordML fixture, not the restricted corpus (consru_export/exports/); no decoded legal text enters tracked evidence",
            "counts and sha256 are integrity evidence, not coverage and not source authenticity",
            "this is not a read-back verifier (S03), not a context export and not semantic/legal gold",
            "R1000 stays active and unclosed; this receipt never auto-closes it",
            "frozen oracles and the M213 cleaned wire bytes are not modified"
        ],
        "source_binding": {
            "contract_doc": {
                "path": "prd/architecture/npa-analysis-jsonl-contract.md",
                "sha256": file_sha256("prd/architecture/npa-analysis-jsonl-contract.md"),
            },
            "records_module": {
                "path": "crates/ln-decode/src/npa_analysis_records.rs",
                "sha256": file_sha256("crates/ln-decode/src/npa_analysis_records.rs"),
            },
            "wire_module": {
                "path": "crates/ln-decode/src/npa_analysis_wire.rs",
                "sha256": file_sha256("crates/ln-decode/src/npa_analysis_wire.rs"),
            },
            "seam_module": {
                "path": "crates/ln-decode/src/analysis_source_mapping.rs",
                "sha256": file_sha256("crates/ln-decode/src/analysis_source_mapping.rs"),
            },
            "integration_test": {
                "path": "crates/ln-decode/tests/npa_analysis_export_integration.rs",
                "sha256": file_sha256("crates/ln-decode/tests/npa_analysis_export_integration.rs"),
            },
            "declared_real_input": {
                "path": REAL_INPUT,
                "sha256": REAL_INPUT_SHA256,
                "bytes": REAL_INPUT_BYTES,
            }
        },
        "pipeline": "source_package::capture -> reader_gate::gate_reader -> reader_projection::build_projection -> npa_analysis_records::analyze_document -> npa_analysis_wire::render_npa_analysis -> npa_analysis_wire::inspect_npa_analysis_wire",
        "approved_fixtures": fixtures,
        "declared_real_input": declared_real_input,
        "proof_classes": {
            "identity": "the envelope parent pins the captured manifest sha256/bytes and both footer seals; check_parent_citation and check_document_version succeed on the pipeline's own output",
            "coordinates": "every bound record span resolves through the seam to the exact substrate UTF-8 slice; a bound span is a non-empty range",
            "block_binding": "analysis blocks are reader primary views; block text is the ordered concatenation of source-fragment segments and each span localizes to exactly one fragment",
            "fail_closed": "a document with records yields resolved typed members or explicit refused spans; a refused span forces completion=incomplete/refused_record and is never promoted",
            "cross_fragment_refusal": "a span that straddles two source fragments is a closed cross_fragment refusal, never rebased and never dropped",
            "unresolved_not_promoted": "an unresolved typed member keeps TypeDerivation::Unresolved and an empty TYPE surface",
            "envelope": "manifest/policies/records/footer shape, two recomputable non-cyclic seals and a closed completion marker",
            "no_corpus_transfer": "fragment records are count/hash only; the envelope carries no inline decoded text",
            "no_temporal_fields": "no temporal stop-sign field enters the identity/coordinate envelope",
            "bounded_real_input": "the declared real input is pinned by byte length and sha256; only counts and hashes are recorded"
        },
        "refusals_observed": [
            "cross_fragment: a whole-block span over two source-fragment segments",
            "invalid_span: an empty local span",
            "out_of_bounds: a local span beyond the block text",
            "SourceIdentityMismatch: a tampered source sha256 and a claimed seal on an unsealed parent",
            "DocumentVersionMismatch: a record revision differing from the envelope triple",
            "CrossDocument: a fragment from another fixture pinned into this envelope",
            "TemporalFieldForbidden: a temporal stop-sign field"
        ],
        "re_test_set": [
            "cargo test -p ln-decode --offline --test npa_analysis_export_integration --test analysis_source_mapping_contract --test analysis_source_mapping_hostile --test analysis_source_mapping_integration --test npa_document_context_contract --test npa_document_context_hostile_contract --test npa_link_pipeline_integration --test cleaned_projection_verify",
            "cargo fmt --all --check",
            "cargo clippy --workspace --all-targets --offline -- -D warnings",
            "cargo check --workspace --offline"
        ]
    });
    (receipt, texts)
}

/// Recursively refuses any string value that contains a long decoded substrate
/// fragment. Only the char count of the offending fragment is named; the
/// decoded text itself is never printed.
fn assert_no_fragment_text(value: &serde_json::Value, texts: &[String], path: &str) {
    match value {
        serde_json::Value::String(text) => {
            for fragment in texts {
                assert!(
                    !text.contains(fragment.as_str()),
                    "{path}: leaked a decoded substrate fragment of {} chars",
                    fragment.chars().count()
                );
            }
        }
        serde_json::Value::Array(items) => {
            for (index, item) in items.iter().enumerate() {
                assert_no_fragment_text(item, texts, &format!("{path}[{index}]"));
            }
        }
        serde_json::Value::Object(members) => {
            for (key, item) in members {
                assert_no_fragment_text(item, texts, &format!("{path}.{key}"));
            }
        }
        _ => {}
    }
}

// ----------------------------------------------------------- positive #

#[test]
fn approved_fixtures_and_real_input_export_document_scoped_analysis() {
    for fixture in APPROVED {
        let pipeline = build_pipeline(
            fixture.xml.as_bytes(),
            &format!("reader-fixture:{}", fixture.file),
            fixture.file,
        );
        assert_document_outcome(
            &pipeline,
            fixture.file,
            &format!("reader-fixture:{}", fixture.file),
        );
    }

    let xml = fs::read(real_input_path()).expect("the declared real input must be readable");
    assert_eq!(xml.len(), REAL_INPUT_BYTES);
    assert_eq!(hex_lower(&Sha256::digest(&xml)), REAL_INPUT_SHA256);
    let real = build_pipeline(&xml, REAL_DOC_VERSION, REAL_INPUT);
    assert_document_outcome(&real, REAL_INPUT, REAL_DOC_VERSION);

    // The real document genuinely passes typing: at least one typed member with
    // a resolved source ref, or an explicit refusal (fail-closed).
    let resolved_typed = count_resolved_typed(&real.analysis);
    let (_, refused) = assert_all_refs_resolve(&real, REAL_INPUT);
    assert!(
        resolved_typed > 0 || refused > 0,
        "the declared real input must be source-bound or explicitly refused, never a silent empty analysis"
    );
}

// ------------------------------------------------------------ refusals #

#[test]
fn cross_fragment_and_invalid_spans_are_closed_refusals() {
    let pipeline = build_pipeline(TWO_RUNS.as_bytes(), "inline:two-runs", "two-runs");
    let block = pipeline.analysis.layout.block(0).expect("one block");
    assert_eq!(block.text, "AlphaBeta");
    assert_eq!(block.segments.len(), 2, "two source-fragment segments");

    let crossed = pipeline
        .analysis
        .layout
        .localize(LocalSpan {
            block: 0,
            start: 0,
            end: block.text.len(),
        })
        .expect_err("a whole-block span must be refused");
    assert_eq!(crossed.token(), AnalysisRefusalKind::CrossFragment.as_str());

    let resolved = resolve_span(
        &pipeline.analysis.layout,
        &pipeline.mapping,
        LocalSpan {
            block: 0,
            start: 4,
            end: 6,
        },
    )
    .expect_err("resolve_span must also refuse a cross-fragment span");
    assert_eq!(
        resolved.token(),
        AnalysisRefusalKind::CrossFragment.as_str()
    );

    let first = pipeline
        .analysis
        .layout
        .localize(LocalSpan {
            block: 0,
            start: 0,
            end: 5,
        })
        .expect("a span inside the first segment localizes");
    let second = pipeline
        .analysis
        .layout
        .localize(LocalSpan {
            block: 0,
            start: 5,
            end: 9,
        })
        .expect("a span inside the second segment localizes");
    assert_ne!(
        first.fragment, second.fragment,
        "the two segments name two fragments"
    );

    assert_eq!(
        pipeline
            .analysis
            .layout
            .localize(LocalSpan {
                block: 0,
                start: 2,
                end: 2,
            })
            .expect_err("an empty span is refused")
            .token(),
        AnalysisRefusalKind::InvalidSpan.as_str()
    );
    assert_eq!(
        pipeline
            .analysis
            .layout
            .localize(LocalSpan {
                block: 0,
                start: 0,
                end: 999,
            })
            .expect_err("an out-of-bounds span is refused")
            .token(),
        AnalysisRefusalKind::OutOfBounds.as_str()
    );
}

#[test]
fn tamper_cross_document_and_version_mismatch_are_refused() {
    let pipeline = build_pipeline(
        MIXED.xml.as_bytes(),
        "reader-fixture:mixed-wordml.xml",
        MIXED.file,
    );
    let genuine = identity_of(&pipeline.package);

    // A different sha256 with the same shape no longer matches the pin.
    let foreign = SourceIdentity::try_new(
        "0".repeat(64),
        genuine.source_bytes,
        genuine.parent_schema.clone(),
        genuine.records_seal_hash.clone(),
        genuine.manifest_hash.clone(),
    )
    .expect("a 64-hex sha is well formed");
    assert_eq!(
        pipeline
            .mapping
            .check_parent_citation(&foreign)
            .expect_err("a tampered sha must be refused")
            .kind(),
        MappingRefusalKind::SourceIdentityMismatch
    );

    // The pin claims a seal the cited (unsealed) parent does not carry.
    let unsealed = SourceIdentity::try_new(
        genuine.source_sha256.clone(),
        genuine.source_bytes,
        genuine.parent_schema.clone(),
        None,
        None,
    )
    .expect("an unsealed identity is well formed");
    assert_eq!(
        pipeline
            .mapping
            .check_parent_citation(&unsealed)
            .expect_err("a seal claim against an unsealed parent must be refused")
            .kind(),
        MappingRefusalKind::SourceIdentityMismatch
    );

    // A record revision that differs from the envelope triple.
    let foreign_version = DocumentVersionRef::try_new(
        "reader-fixture:elsewhere".to_string(),
        "0".repeat(64),
        PROFILE.to_string(),
    )
    .expect("a well-formed foreign triple");
    assert_eq!(
        pipeline
            .mapping
            .check_document_version(&foreign_version)
            .expect_err("a foreign revision must be refused")
            .kind(),
        MappingRefusalKind::DocumentVersionMismatch
    );

    // A fragment pinned from another document is a cross-document refusal.
    let other = build_pipeline(
        TEXT_ONLY.xml.as_bytes(),
        "reader-fixture:text-only.xml",
        TEXT_ONLY.file,
    );
    let foreign_fragment = FragmentRef::from(other.index.texts()[0].id.as_str());
    let foreign_text = other.index.texts()[0].value.clone();
    let foreign_identity = identity_of(&other.package);
    let mut fresh = SourceMapping::new(
        identity_of(&pipeline.package),
        version_of(&pipeline.package, "reader-fixture:mixed-wordml.xml"),
    );
    assert_eq!(
        fresh
            .pin_fragment(foreign_fragment, foreign_text, &foreign_identity)
            .expect_err("a foreign fragment must be refused")
            .kind(),
        MappingRefusalKind::CrossDocument
    );

    // A temporal stop-sign field is a closed refusal, never a rebase.
    assert_eq!(
        check_temporal_fields(&["effective_from"])
            .expect_err("a temporal field must be refused")
            .kind(),
        MappingRefusalKind::TemporalFieldForbidden
    );
}

// ------------------------------------------------------------ receipt #

#[test]
fn emit_portable_receipt_json() {
    if std::env::var("M214_S02_EMIT_RECEIPT").ok().as_deref() != Some("1") {
        return;
    }
    let (receipt, _) = build_receipt_with_texts();
    println!("M214_S02_RECEIPT_BEGIN");
    println!(
        "{}",
        serde_json::to_string_pretty(&receipt).expect("receipt serializes")
    );
    println!("M214_S02_RECEIPT_END");
}

#[test]
fn portable_receipt_valid_and_matches_live_pipeline() {
    let path = repo_root().join(RECEIPT_REL);
    let raw = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("{RECEIPT_REL} must exist: {error}"));
    assert!(raw.is_ascii(), "the portable receipt must be ascii_only");
    let stored: serde_json::Value =
        serde_json::from_str(&raw).expect("the portable receipt must be valid JSON");
    assert_eq!(stored["schema"], "m214-s02-analysis-export/v1");
    assert_eq!(stored["schema_version"], 1);
    assert_eq!(stored["count_only"], true);
    assert_eq!(stored["ascii_only"], true);
    assert!(
        stored["source_binding"]["declared_real_input"]["sha256"] == REAL_INPUT_SHA256,
        "the receipt pins the declared real input sha256"
    );

    let (live, long_texts) = build_receipt_with_texts();
    assert_eq!(
        stored["approved_fixtures"], live["approved_fixtures"],
        "the receipt's approved-fixture measurements match the live pipeline"
    );
    assert_eq!(
        stored["declared_real_input"], live["declared_real_input"],
        "the receipt's declared-real-input measurement matches the live pipeline"
    );
    assert_no_fragment_text(&stored, &long_texts, "receipt");
}

// ===================================================================== #
// M214-es3jvw S03 T05: context export -> read-back -> independent verify #
// ===================================================================== #

const RECEIPT_S03_REL: &str = "prd/migration/rust-evidence/m214-s03-context-verify.json";

/// The inline synthetic frame fixture used to assert that a non-resolved
/// context outcome yields an honest `context_incomplete` footer with no
/// refusal outranking it.
const CONTEXT_HONESTY_BODY: &str =
    "<w:p><w:r><w:t>Статья 1. Предмет регулирования</w:t></w:r></w:p>\
     <w:p><w:r><w:t>Федерального закона от 01.01.2020 N 1-ФЗ,</w:t></w:r></w:p>\
     <w:p><w:r><w:t>от 02.02.2021 N 2-ФЗ</w:t></w:r></w:p>";

// ------------------------------------------------------- context refs #

fn for_each_context_ref(contexts: &[ContextRecord], mut visit: impl FnMut(&SourceRef)) {
    for record in contexts {
        if let ContextRecord::Result(result) = record {
            for anchor in &result.anchors {
                visit(anchor);
            }
            for claim in &result.claims {
                visit(&claim.anchor);
            }
            for edge in &result.derivations {
                visit(&edge.anchor);
            }
        }
    }
}

/// Asserts every bound context anchor resolves to the exact substrate UTF-8
/// slice and every refused anchor carries a closed non-empty token. Returns
/// `(bound, refused)`.
fn assert_context_anchors_resolve(pipeline: &Pipeline, label: &str) -> (usize, usize) {
    let mut bound = 0usize;
    let mut refused = 0usize;
    for_each_context_ref(&pipeline.contexts, |reference| match reference {
        SourceRef::Bound(span) => {
            let resolved = pipeline
                .mapping
                .resolve_fragment_span(&span.as_fragment_span())
                .unwrap_or_else(|error| panic!("{label}: a context span must resolve: {error}"));
            let slice = pipeline
                .mapping
                .slice(&resolved)
                .unwrap_or_else(|error| panic!("{label}: a context span must slice: {error}"));
            let substrate = pipeline
                .index
                .text(span.fragment.as_str())
                .unwrap_or_else(|| panic!("{label}: context fragment {} absent", span.fragment));
            assert_eq!(
                slice,
                &substrate.value[span.start..span.end],
                "{label}: a context anchor must equal the exact substrate slice"
            );
            bound += 1;
        }
        SourceRef::Refused(refusal) => {
            assert!(
                !refusal.token().is_empty(),
                "{label}: a refused context anchor carries a closed token"
            );
            refused += 1;
        }
    });
    (bound, refused)
}

fn context_result_count(
    contexts: &[ContextRecord],
    predicate: impl Fn(ContextStatus) -> bool,
) -> usize {
    contexts
        .iter()
        .filter(
            |record| matches!(record, ContextRecord::Result(result) if predicate(result.status)),
        )
        .count()
}

// --------------------------------------------------- envelope editing #

fn envelope_lines(text: &str) -> Vec<String> {
    assert!(text.ends_with('\n'), "envelope ends with one trailing LF");
    text[..text.len() - 1]
        .split('\n')
        .map(str::to_string)
        .collect()
}

fn join_envelope(lines: &[String]) -> String {
    let mut out = lines.join("\n");
    out.push('\n');
    out
}

fn family_of(line: &str) -> Option<String> {
    let value: serde_json::Value = serde_json::from_str(line).ok()?;
    value.get("family")?.as_str().map(str::to_string)
}

/// Recomputes the two non-cyclic seals over the tampered content and patches
/// the footer, emulating an attacker who reseals after a substitution.
fn reseal(text: &str) -> String {
    let seals = recompute_analysis_seals(text).expect("seals recompute over the tampered content");
    let mut lines = envelope_lines(text);
    let last = lines.len() - 1;
    let mut footer = lines[last].clone();
    footer = replace_hex(&footer, "records_seal_hash", &seals.records_seal_hash);
    footer = replace_hex(&footer, "manifest_hash", &seals.manifest_hash);
    lines[last] = footer;
    join_envelope(&lines)
}

fn replace_hex(line: &str, key: &str, value: &str) -> String {
    let needle = format!("\"{key}\":\"");
    let start = line.find(&needle).expect("seal key present") + needle.len();
    let end = start + 64;
    let mut out = line.to_string();
    out.replace_range(start..end, value);
    out
}

/// Replaces the first `"<key>":{...}` object (balanced braces, string-aware).
fn replace_field_object(line: &str, key: &str, new_obj: &str) -> String {
    let needle = format!("\"{key}\":{{");
    let pos = line.find(&needle).expect("field present");
    let obj_start = pos + format!("\"{key}\":").len();
    let bytes = line.as_bytes();
    let mut depth = 0i32;
    let mut index = obj_start;
    loop {
        match bytes[index] {
            b'"' => {
                index += 1;
                while bytes[index] != b'"' {
                    if bytes[index] == b'\\' {
                        index += 1;
                    }
                    index += 1;
                }
            }
            b'{' => depth += 1,
            b'}' => {
                depth -= 1;
                if depth == 0 {
                    break;
                }
            }
            _ => {}
        }
        index += 1;
    }
    let end = index + 1;
    let mut out = line.to_string();
    out.replace_range(obj_start..end, new_obj);
    out
}

fn bound_span_of(line: &str, key: &str) -> Option<(String, usize, usize)> {
    let value: serde_json::Value = serde_json::from_str(line).ok()?;
    let object = value.get(key)?;
    let fragment = object.get("fragment")?.as_str()?.to_string();
    let start = object.get("start")?.as_u64()? as usize;
    let end = object.get("end")?.as_u64()? as usize;
    Some((fragment, start, end))
}

/// A different, valid, in-fragment span on UTF-8 code point boundaries.
fn alternate_span(
    index: &ReaderRecordIndex,
    fragment: &str,
    start: usize,
    end: usize,
) -> Option<(usize, usize)> {
    let value = &index.text(fragment)?.value;
    let length = value.len();
    if end < length {
        let mut candidate = end + 1;
        while candidate < length && !value.is_char_boundary(candidate) {
            candidate += 1;
        }
        if candidate > start && value.is_char_boundary(candidate) {
            return Some((start, candidate));
        }
    }
    if start > 0 {
        let mut candidate = start - 1;
        while candidate > 0 && !value.is_char_boundary(candidate) {
            candidate -= 1;
        }
        if candidate < end && value.is_char_boundary(candidate) {
            return Some((candidate, end));
        }
    }
    None
}

/// A span whose end leaves the fragment (out of bounds), still parseable.
fn out_of_bounds_span(
    index: &ReaderRecordIndex,
    fragment: &str,
    start: usize,
) -> Option<(usize, usize)> {
    let value = &index.text(fragment)?.value;
    Some((start, value.len() + 5))
}

/// The first bound member span mutated to a different in-fragment range.
fn mutate_member_span_in_fragment(pipeline: &Pipeline) -> Option<String> {
    let mut lines = envelope_lines(&pipeline.context_envelope);
    for index in 0..lines.len() {
        if family_of(&lines[index]).as_deref() != Some("member") {
            continue;
        }
        for key in ["span", "evidence"] {
            if let Some((fragment, start, end)) = bound_span_of(&lines[index], key) {
                if let Some((new_start, new_end)) =
                    alternate_span(&pipeline.index, &fragment, start, end)
                {
                    let new_obj = format!(
                        r#"{{"end":{new_end},"fragment":"{fragment}","start":{new_start}}}"#
                    );
                    lines[index] = replace_field_object(&lines[index], key, &new_obj);
                    return Some(join_envelope(&lines));
                }
            }
        }
    }
    None
}

/// The first bound member span mutated out of the fragment bounds.
fn mutate_member_span_out_of_bounds(pipeline: &Pipeline) -> Option<String> {
    let mut lines = envelope_lines(&pipeline.context_envelope);
    for index in 0..lines.len() {
        if family_of(&lines[index]).as_deref() != Some("member") {
            continue;
        }
        for key in ["span", "evidence"] {
            if let Some((fragment, start, _)) = bound_span_of(&lines[index], key) {
                if let Some((new_start, new_end)) =
                    out_of_bounds_span(&pipeline.index, &fragment, start)
                {
                    let new_obj = format!(
                        r#"{{"end":{new_end},"fragment":"{fragment}","start":{new_start}}}"#
                    );
                    lines[index] = replace_field_object(&lines[index], key, &new_obj);
                    return Some(join_envelope(&lines));
                }
            }
        }
    }
    None
}

fn mutate_member_span(pipeline: &Pipeline) -> Option<(String, &'static str)> {
    if let Some(tampered) = mutate_member_span_in_fragment(pipeline) {
        return Some((tampered, "span_in_fragment"));
    }
    mutate_member_span_out_of_bounds(pipeline).map(|tampered| (tampered, "span_out_of_bounds"))
}

fn mutate_first_fragment_hash(text: &str) -> String {
    let mut lines = envelope_lines(text);
    for index in 0..lines.len() {
        if family_of(&lines[index]).as_deref() != Some("fragment") {
            continue;
        }
        let value: serde_json::Value =
            serde_json::from_str(&lines[index]).expect("fragment line parses");
        let hash = value
            .get("content_sha256")
            .and_then(|value| value.as_str())
            .expect("content_sha256");
        let mut chars: Vec<char> = hash.chars().collect();
        chars[0] = if chars[0] == 'a' { 'b' } else { 'a' };
        let new_hash: String = chars.into_iter().collect();
        lines[index] = lines[index].replacen(hash, &new_hash, 1);
        return join_envelope(&lines);
    }
    panic!("the envelope must expose a fragment record");
}

fn verify(pipeline: &Pipeline, text: &str) -> Result<(), Vec<AnalysisVerifyFinding>> {
    verify_npa_analysis_wire(
        text,
        &pipeline.projection,
        &pipeline.index,
        &pipeline.mapping,
    )
}

fn has_code(findings: &[AnalysisVerifyFinding], code: AnalysisVerifyCode) -> bool {
    findings.iter().any(|finding| finding.code() == code)
}

/// Applies a resealed member-span substitution and returns `(kind, code)` when
/// a bound member span exists (the declared real input), else `None` (the
/// synthetic fixtures expose no typed/linked member records).
fn resealed_span_tamper_code(pipeline: &Pipeline) -> Option<(&'static str, &'static str)> {
    let (tampered, kind) = mutate_member_span(pipeline)?;
    let resealed = reseal(&tampered);
    let findings = verify(pipeline, &resealed)
        .expect_err("a resealed member-span substitution must be detected");
    let code = if kind == "span_in_fragment" {
        assert!(
            has_code(&findings, AnalysisVerifyCode::SourceRefSubstitution),
            "an in-fragment span move is source_ref_substitution: {findings:?}"
        );
        "source_ref_substitution"
    } else {
        assert!(
            has_code(&findings, AnalysisVerifyCode::SpanSliceMismatch),
            "an out-of-bounds span is span_slice_mismatch: {findings:?}"
        );
        "span_slice_mismatch"
    };
    Some((kind, code))
}

/// Applies a resealed fragment-content substitution (always available).
fn resealed_fragment_hash_code(pipeline: &Pipeline) -> &'static str {
    let tampered = reseal(&mutate_first_fragment_hash(&pipeline.context_envelope));
    let findings =
        verify(pipeline, &tampered).expect_err("a resealed fragment hash must be detected");
    assert!(
        has_code(&findings, AnalysisVerifyCode::FragmentHashMismatch),
        "a fragment hash substitution is fragment_hash_mismatch: {findings:?}"
    );
    "fragment_hash_mismatch"
}

/// Applies a non-resealed member-span substitution; the footer seals now
/// disagree with the tampered content.
fn non_resealed_tamper_code(pipeline: &Pipeline) -> Option<&'static str> {
    let (tampered, _kind) = mutate_member_span(pipeline)?;
    let findings = verify(pipeline, &tampered).expect_err("a non-resealed tamper must be detected");
    assert!(
        has_code(&findings, AnalysisVerifyCode::SealMismatch),
        "a non-resealed tamper is seal_mismatch: {findings:?}"
    );
    Some("seal_mismatch")
}

// --------------------------------------------------------- measurement #

fn measure_s03(pipeline: &Pipeline) -> serde_json::Value {
    let summary = inspect_npa_analysis_wire(&pipeline.context_envelope)
        .expect("the context envelope must inspect");
    let families: BTreeMap<String, u64> = summary.families.clone();
    let readback_ok = read_back_npa_analysis(&pipeline.context_envelope).is_ok();
    let verified = verify(pipeline, &pipeline.context_envelope);
    assert!(
        verified.is_ok(),
        "a valid context envelope must verify Ok: {verified:?}"
    );
    let seals_recompute = recompute_analysis_seals(&pipeline.context_envelope).is_ok();

    let (context_bound, context_refused) = assert_context_anchors_resolve(pipeline, "receipt");
    let non_resolved = context_result_count(&pipeline.contexts, |status| {
        status != ContextStatus::Resolved
    });
    let mut status_counts: BTreeMap<String, u64> = BTreeMap::new();
    for record in &pipeline.contexts {
        if let ContextRecord::Result(result) = record {
            *status_counts
                .entry(status_token(result.status).to_string())
                .or_default() += 1;
        }
    }
    let run_record = pipeline.contexts.iter().find_map(|record| match record {
        ContextRecord::Run(run) => Some(run),
        ContextRecord::Result(_) => None,
    });
    let context_requests = run_record.map(|run| run.requests).unwrap_or(0);
    let context_run_limit_reached = run_record.map(|run| run.limit_reached).unwrap_or(false);
    let context_run_diagnostics: Vec<String> = run_record
        .map(|run| {
            run.diagnostics
                .iter()
                .map(|diagnostic| diagnostic_token(*diagnostic).to_string())
                .collect()
        })
        .unwrap_or_default();

    let span_tamper = match resealed_span_tamper_code(pipeline) {
        Some((kind, code)) => json!({"detected": true, "kind": kind, "code": code}),
        None => json!({"detected": false}),
    };
    let fragment_tamper = resealed_fragment_hash_code(pipeline);
    let non_resealed = match non_resealed_tamper_code(pipeline) {
        Some(code) => json!({"detected": true, "code": code}),
        None => json!({"detected": false}),
    };

    json!({
        "context_records": pipeline.contexts.len(),
        "context_requests": context_requests,
        "context_results": context_result_count(&pipeline.contexts, |_| true),
        "context_non_resolved": non_resolved,
        "context_limit_reached": context_result_count(&pipeline.contexts, |status| status == ContextStatus::Limit),
        "context_run_limit_reached": context_run_limit_reached,
        "context_run_diagnostics": context_run_diagnostics,
        "context_bound_anchors": context_bound,
        "context_refused_anchors": context_refused,
        "context_status_counts": status_counts,
        "families": families,
        "records": summary.records,
        "completion": summary.completion,
        "completion_basis": summary.completion_basis,
        "incomplete_reasons": summary.incomplete_reasons,
        "readback_ok": readback_ok,
        "verify_ok": verified.is_ok(),
        "seals_recompute": seals_recompute,
        "resealed_span_tamper": span_tamper,
        "resealed_fragment_hash_tamper": fragment_tamper,
        "non_resealed_tamper": non_resealed,
    })
}

fn build_s03_receipt_with_texts() -> (serde_json::Value, Vec<String>) {
    let mut fixtures: Vec<serde_json::Value> = Vec::new();
    let mut texts: Vec<String> = Vec::new();
    for fixture in APPROVED {
        let pipeline = build_pipeline(
            fixture.xml.as_bytes(),
            &format!("reader-fixture:{}", fixture.file),
            fixture.file,
        );
        collect_long_texts(&pipeline, &mut texts);
        fixtures.push(json!({
            "file": fixture.file,
            "sha256": fixture.sha256,
            "bytes": fixture.xml.len(),
            "measurement": measure_s03(&pipeline),
        }));
    }

    let xml = fs::read(real_input_path()).expect("the declared real input must be readable");
    assert_eq!(
        xml.len(),
        REAL_INPUT_BYTES,
        "{REAL_INPUT}: byte length drift"
    );
    assert_eq!(
        hex_lower(&Sha256::digest(&xml)),
        REAL_INPUT_SHA256,
        "{REAL_INPUT}: content drift; re-pin the sha256 oracle"
    );
    let real = build_pipeline(&xml, REAL_DOC_VERSION, REAL_INPUT);
    collect_long_texts(&real, &mut texts);
    let declared_real_input = json!({
        "path": REAL_INPUT,
        "sha256": REAL_INPUT_SHA256,
        "bytes": REAL_INPUT_BYTES,
        "measurement": measure_s03(&real),
    });

    // One inline synthetic frame fixture: it exercises the context result,
    // bound-anchor and honest non-resolved mechanics that the approved reader
    // fixtures and the declared real input do not reach (their blocks build no
    // document-context frames; the real input's multi-marker headings are a
    // closed ConflictingRoleEvidence, so its context line is an honest run).
    let synthetic_xml = format!(
        "<w:wordDocument xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\"><w:body>{CONTEXT_HONESTY_BODY}</w:body></w:wordDocument>"
    );
    let synthetic = build_pipeline(
        synthetic_xml.as_bytes(),
        "inline:context-honesty",
        "context-honesty",
    );
    collect_long_texts(&synthetic, &mut texts);
    let synthetic_context_fixture = json!({
        "label": "inline-context-honesty",
        "note": "inline synthetic non-legal WordML frame fixture: exercises context results, bound anchors and an honest non-resolved outcome",
        "sha256": hex_lower(&Sha256::digest(synthetic_xml.as_bytes())),
        "bytes": synthetic_xml.len(),
        "measurement": measure_s03(&synthetic),
    });

    let receipt = json!({
        "schema": "m214-s03-context-verify/v1",
        "schema_version": 1,
        "lifecycle": "[bounded]",
        "milestone": "M214-es3jvw",
        "slice": "S03",
        "task": "T05",
        "generated_utc": std::env::var("M214_S03_GENERATED_UTC")
            .unwrap_or_else(|_| "unspecified".to_string()),
        "count_only": true,
        "ascii_only": true,
        "non_claims": [
            "this receipt is [bounded] to the three approved reader fixtures, the single declared real input and one inline synthetic frame fixture; it is not corpus coverage",
            "the declared real input is one tracked bounded Consultant WordML fixture, not the restricted corpus (consru_export/exports/); no decoded legal text enters tracked evidence",
            "context counts, verify codes and sha256 are integrity evidence, not coverage and not source authenticity",
            "context outcomes are structural candidates only; this is not semantic/legal gold and not a legal-effect claim",
            "R1000 stays active and unclosed; this receipt never auto-closes it",
            "frozen oracles and the M213 cleaned wire bytes are not modified; the S02 receipt is not rewritten"
        ],
        "source_binding": {
            "contract_doc": {
                "path": "prd/architecture/npa-analysis-jsonl-contract.md",
                "sha256": file_sha256("prd/architecture/npa-analysis-jsonl-contract.md"),
            },
            "context_module": {
                "path": "crates/ln-decode/src/npa_context_records.rs",
                "sha256": file_sha256("crates/ln-decode/src/npa_context_records.rs"),
            },
            "wire_module": {
                "path": "crates/ln-decode/src/npa_analysis_wire.rs",
                "sha256": file_sha256("crates/ln-decode/src/npa_analysis_wire.rs"),
            },
            "verify_module": {
                "path": "crates/ln-decode/src/npa_analysis_verify.rs",
                "sha256": file_sha256("crates/ln-decode/src/npa_analysis_verify.rs"),
            },
            "seam_module": {
                "path": "crates/ln-decode/src/analysis_source_mapping.rs",
                "sha256": file_sha256("crates/ln-decode/src/analysis_source_mapping.rs"),
            },
            "integration_test": {
                "path": "crates/ln-decode/tests/npa_analysis_export_integration.rs",
                "sha256": file_sha256("crates/ln-decode/tests/npa_analysis_export_integration.rs"),
            },
            "declared_real_input": {
                "path": REAL_INPUT,
                "sha256": REAL_INPUT_SHA256,
                "bytes": REAL_INPUT_BYTES,
            }
        },
        "pipeline": "source_package::capture -> reader_gate::gate_reader -> reader_projection::build_projection -> npa_analysis_records::analyze_document -> npa_context_records::build_context_records -> npa_analysis_wire::render_npa_analysis_with_context -> npa_analysis_verify::read_back_npa_analysis -> npa_analysis_verify::verify_npa_analysis_wire",
        "approved_fixtures": fixtures,
        "declared_real_input": declared_real_input,
        "synthetic_context_fixture": synthetic_context_fixture,
        "proof_classes": {
            "context_family": "the opt-in seventh family renders after diagnostics with closed request_kind/status/view tokens and one aggregate run line",
            "read_back": "read_back_npa_analysis reconstructs all seven families from the rendered JSONL text",
            "independent_verify": "verify_npa_analysis_wire recomputes the seals, then re-derives the canonical records from the pinned parent and never treats artifact seals as a pass",
            "resealed_substitution": "a resealed member-span move is detected as source_ref_substitution (or span_slice_mismatch when out of bounds); a resealed fragment hash is fragment_hash_mismatch",
            "non_resealed_tamper": "a tamper without resealing is seal_mismatch",
            "context_anchor_exactness": "every bound context anchor equals the exact substrate UTF-8 slice; a localization failure is a closed refusal",
            "honest_incomplete": "a non-resolved context outcome forces incomplete/context_incomplete and is never promoted to complete",
            "no_corpus_transfer": "fragment records are count/hash only; the envelope carries no inline decoded text",
            "bounded_real_input": "the declared real input is pinned by byte length and sha256; only counts, closed codes and hashes are recorded"
        },
        "re_test_set": [
            "cargo test -p ln-decode --offline --test npa_analysis_export_integration --test npa_analysis_context_contract --test npa_analysis_wire_context --test npa_analysis_verify_contract --test npa_analysis_verify_hostile --test npa_analysis_records_contract --test npa_analysis_records_link_classify --test npa_analysis_wire_contract --test npa_analysis_wire_hostile --test analysis_source_mapping_contract --test analysis_source_mapping_hostile --test analysis_source_mapping_integration --test npa_document_context_contract --test npa_document_context_hostile_contract --test npa_link_pipeline_integration --test cleaned_projection_verify",
            "cargo fmt --all --check",
            "cargo clippy --workspace --all-targets --offline -- -D warnings",
            "cargo check --workspace --offline"
        ]
    });
    (receipt, texts)
}

// ----------------------------------------------------------- positive #

fn assert_s03_outcome(pipeline: &Pipeline, label: &str) {
    let summary = inspect_npa_analysis_wire(&pipeline.context_envelope)
        .unwrap_or_else(|error| panic!("{label}: context envelope must inspect: {error}"));
    assert!(
        summary.families.get("context").copied().unwrap_or(0) >= 1,
        "{label}: the context family must be present"
    );
    assert_eq!(
        summary.families.values().sum::<u64>(),
        summary.records,
        "{label}: family counts sum to the record count"
    );

    let readback = read_back_npa_analysis(&pipeline.context_envelope)
        .unwrap_or_else(|error| panic!("{label}: read-back must succeed: {error}"));
    assert_eq!(
        readback.records.len() as u64,
        summary.records,
        "{label}: read-back reconstructs every interior record"
    );
    assert!(
        !readback.contexts.is_empty(),
        "{label}: read-back reconstructs the context family"
    );

    assert_eq!(
        verify(pipeline, &pipeline.context_envelope),
        Ok(()),
        "{label}: an untouched context envelope must verify Ok"
    );
    assert!(
        recompute_analysis_seals(&pipeline.context_envelope).is_ok(),
        "{label}: the seals must recompute"
    );

    let _ = assert_context_anchors_resolve(pipeline, label);

    let non_resolved = context_result_count(&pipeline.contexts, |status| {
        status != ContextStatus::Resolved
    });
    if summary.completion_basis == "context_incomplete" {
        assert!(
            non_resolved > 0,
            "{label}: context_incomplete requires a non-resolved result"
        );
        assert_eq!(summary.completion, "incomplete", "{label}");
    }
    if non_resolved > 0 && summary.completion_basis != "refused_record" {
        assert_eq!(
            summary.completion, "incomplete",
            "{label}: a non-resolved context is never complete"
        );
        assert_eq!(
            summary.completion_basis, "context_incomplete",
            "{label}: a non-resolved context forces context_incomplete"
        );
    }
}

#[test]
fn approved_fixtures_and_real_input_export_readback_verify() {
    for fixture in APPROVED {
        let pipeline = build_pipeline(
            fixture.xml.as_bytes(),
            &format!("reader-fixture:{}", fixture.file),
            fixture.file,
        );
        assert_s03_outcome(&pipeline, fixture.file);
    }

    let xml = fs::read(real_input_path()).expect("the declared real input must be readable");
    assert_eq!(xml.len(), REAL_INPUT_BYTES);
    assert_eq!(hex_lower(&Sha256::digest(&xml)), REAL_INPUT_SHA256);
    let real = build_pipeline(&xml, REAL_DOC_VERSION, REAL_INPUT);
    assert_s03_outcome(&real, REAL_INPUT);
}

#[test]
fn non_resolved_context_forces_honest_context_incomplete() {
    let xml = format!(
        "<w:wordDocument xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\"><w:body>{CONTEXT_HONESTY_BODY}</w:body></w:wordDocument>"
    );
    let pipeline = build_pipeline(xml.as_bytes(), "inline:context-honesty", "context-honesty");
    let summary = inspect_npa_analysis_wire(&pipeline.context_envelope)
        .expect("the honest-partial context envelope must inspect");
    assert_eq!(summary.completion, "incomplete");
    assert_eq!(summary.completion_basis, "context_incomplete");
    assert!(
        summary
            .incomplete_reasons
            .contains(&"context_incomplete".to_string()),
        "the basis token is a reason"
    );
    assert!(
        summary
            .incomplete_reasons
            .iter()
            .any(|reason| reason.starts_with("context_") && reason != "context_incomplete"),
        "at least one closed non-resolved status reason is present"
    );
    assert_eq!(verify(&pipeline, &pipeline.context_envelope), Ok(()));
    let _ = assert_context_anchors_resolve(&pipeline, "context-honesty");
}

// ------------------------------------------------------------ hostile #

#[test]
fn resealed_span_substitution_on_declared_real_input_is_detected() {
    let xml = fs::read(real_input_path()).expect("the declared real input must be readable");
    assert_eq!(xml.len(), REAL_INPUT_BYTES);
    assert_eq!(hex_lower(&Sha256::digest(&xml)), REAL_INPUT_SHA256);
    let pipeline = build_pipeline(&xml, REAL_DOC_VERSION, REAL_INPUT);
    let (kind, code) = resealed_span_tamper_code(&pipeline)
        .expect("the declared real input exposes a bound member span");
    assert!(
        matches!(kind, "span_in_fragment" | "span_out_of_bounds"),
        "the tamper is a span substitution ({kind})"
    );
    assert!(
        matches!(code, "source_ref_substitution" | "span_slice_mismatch"),
        "a resealed span substitution yields a closed span code ({code})"
    );
}

#[test]
fn resealed_fragment_hash_on_declared_real_input_is_detected() {
    let xml = fs::read(real_input_path()).expect("the declared real input must be readable");
    let pipeline = build_pipeline(&xml, REAL_DOC_VERSION, REAL_INPUT);
    assert_eq!(
        resealed_fragment_hash_code(&pipeline),
        "fragment_hash_mismatch"
    );
}

#[test]
fn non_resealed_tamper_on_declared_real_input_is_seal_mismatch() {
    let xml = fs::read(real_input_path()).expect("the declared real input must be readable");
    let pipeline = build_pipeline(&xml, REAL_DOC_VERSION, REAL_INPUT);
    assert_eq!(
        non_resealed_tamper_code(&pipeline),
        Some("seal_mismatch"),
        "a tamper without resealing is detected as seal_mismatch"
    );
}

// ------------------------------------------------------------ receipt #

#[test]
fn write_portable_receipt_s03_json() {
    if std::env::var("M214_S03_WRITE_RECEIPT").ok().as_deref() != Some("1") {
        return;
    }
    let (receipt, _) = build_s03_receipt_with_texts();
    let mut raw = serde_json::to_string_pretty(&receipt).expect("receipt serializes");
    raw.push('\n');
    fs::write(repo_root().join(RECEIPT_S03_REL), raw).expect("the S03 receipt must be writable");
}

#[test]
fn emit_portable_receipt_s03_json() {
    if std::env::var("M214_S03_EMIT_RECEIPT").ok().as_deref() != Some("1") {
        return;
    }
    let (receipt, _) = build_s03_receipt_with_texts();
    println!("M214_S03_RECEIPT_BEGIN");
    println!(
        "{}",
        serde_json::to_string_pretty(&receipt).expect("receipt serializes")
    );
    println!("M214_S03_RECEIPT_END");
}

#[test]
fn portable_receipt_s03_valid_and_matches_live_pipeline() {
    let path = repo_root().join(RECEIPT_S03_REL);
    let raw = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("{RECEIPT_S03_REL} must exist: {error}"));
    assert!(raw.is_ascii(), "the portable receipt must be ascii_only");
    let stored: serde_json::Value =
        serde_json::from_str(&raw).expect("the portable receipt must be valid JSON");
    assert_eq!(stored["schema"], "m214-s03-context-verify/v1");
    assert_eq!(stored["schema_version"], 1);
    assert_eq!(stored["count_only"], true);
    assert_eq!(stored["ascii_only"], true);
    assert!(
        stored["source_binding"]["declared_real_input"]["sha256"] == REAL_INPUT_SHA256,
        "the receipt pins the declared real input sha256"
    );

    let (live, long_texts) = build_s03_receipt_with_texts();
    assert_eq!(
        stored["approved_fixtures"], live["approved_fixtures"],
        "the receipt's approved-fixture context measurements match the live pipeline"
    );
    assert_eq!(
        stored["declared_real_input"], live["declared_real_input"],
        "the receipt's declared-real-input context measurement matches the live pipeline"
    );
    assert_eq!(
        stored["synthetic_context_fixture"], live["synthetic_context_fixture"],
        "the receipt's synthetic context-fixture measurement matches the live pipeline"
    );
    assert_no_fragment_text(&stored, &long_texts, "receipt");
}

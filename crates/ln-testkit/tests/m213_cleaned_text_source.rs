//! M215 S05 Integration: the embedding text originates in the M213 cleaned
//! projection, not in a self-contained constant.
//!
//! This is a *consuming* integration proof, not another self-contained unit
//! test. It drives the real, enabled `ln-decode` pipeline over one
//! sha256-pinned synthetic non-legal reader fixture (the same frozen bytes
//! `ln-decode/tests/cleaned_consumer_admission.rs` pins)
//!
//! ```text
//! capture -> gate_reader(SupportedWordml) -> build_projection ->
//! export_cleaned_projection(Complete) -> read_cleaned_wire -> inline text
//! ```
//!
//! and then feeds the text *taken from the cleaned projection* into an
//! [`EmbeddingRequest`] through the deterministic test transport and the
//! [`TeiEmbeddingAdapter`] transport seam (no socket, no network, no weights).
//!
//! What each control establishes:
//! - positivity: the same projection text yields a byte-identical vector on
//!   repeated calls and on independently constructed embedders/adapters
//!   (`deterministic-mismatch` names the invariant on failure);
//! - ORIGIN (the Integration-class point): building the projection from
//!   altered source bytes changes the extracted text and therefore the
//!   embedding input and vector digest (`text-not-from-projection` names the
//!   invariant on failure) — a local constant could not track the projection
//!   this way;
//! - fail-closed: an unavailable or bad-response transport still yields the
//!   existing typed [`StorageError`] and produces no artifact, no panic and no
//!   leaked payload.
//!
//! Non-claims: no retrieval-quality, product-runtime or live-TEI validation
//! claim. R1000/M213 stays an upstream-only input; its acceptance is neither
//! reopened nor repeated. The `[bounded]` ceiling of the cleaned-projection
//! contract is unchanged. Structural facts are printed without payload: the
//! fixture sha256, the projection text length + digest, and the vector digest.
//! Test-local digests are non-cryptographic FNV-1a 64 labels, not seals.

use ln_decode::cleaned_wire::{
    CleanedProjection, WireCompletion, WireLimits, export_cleaned_projection, read_cleaned_wire,
};
use ln_decode::reader_gate::{ReaderSourceClass, gate_reader};
use ln_decode::reader_projection::{ReaderProjection, build_projection};
use ln_decode::source_package::{Limits, Package, capture};
use ln_storage::adapters::tei::{EmbeddingTransport, TeiEmbeddingAdapter, TransportError};
use ln_storage::{
    EmbeddingArtifactPort, EmbeddingArtifactRequest, EmbeddingPort, EmbeddingRequest,
    ModelProvenance, ProvenancedEmbedding, StorageError,
};
use ln_testkit::{DeterministicEmbedding, DeterministicEmbeddingTransport};

/// One sha256-pinned synthetic, non-legal WordML fixture. `capture` recomputes
/// the sha256 over these exact bytes; a content drift fails the pin assertion
/// in [`pinned`] rather than being silently re-pinned.
const MIXED_XML: &str = include_str!("../../ln-decode/tests/fixtures/reader/mixed-wordml.xml");
const MIXED_SHA256: &str = "d2fc1cd17f0697f575e94f09d83da5027d73afd37c700772eafa4c4a4fbc76db";

/// Deterministic model identity/dimensionality for the CI transport seam.
const MODEL_ID: &str = "det-model";
const DIMENSIONS: usize = 16;

/// Subject the artifact path embeds the cleaned projection under.
const SUBJECT_REF: &str = "m213-cleaned-doc";

// -------------------------------------------------------------- pipeline #

/// The frozen substrate, its reader projection and the cleaned-projection
/// read-back. Built by the real enabled pipeline; no field is a literal.
struct CleanedSource {
    package: Package,
    projection: ReaderProjection,
    readback: CleanedProjection,
}

/// Drive `capture -> gate_reader -> build_projection -> export -> read_back`
/// over `xml` and return the read-back cleaned projection.
fn build(xml: &str) -> CleanedSource {
    let package = capture(xml.as_bytes(), &Limits::default())
        .expect("the fixture bytes must capture as a source package");
    let class =
        gate_reader(package.records()).expect("the fixture must gate as a supported reader source");
    assert_eq!(
        class,
        ReaderSourceClass::SupportedWordml,
        "the pinned fixture is expected to be supported WordML"
    );
    let projection = build_projection(package.records()).expect("the fixture must project");
    let artifact = export_cleaned_projection(
        &package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .expect("a gated, projected fixture must export a complete artifact");
    let readback = read_cleaned_wire(&artifact).expect("the exported artifact must read back");
    CleanedSource {
        package,
        projection,
        readback,
    }
}

/// Build the cleaned projection from the sha256-pinned fixture and assert the
/// pin. A drift is a failure, never a silent re-pin.
fn pinned() -> CleanedSource {
    let source = build(MIXED_XML);
    assert_eq!(
        source.package.manifest().source.sha256,
        MIXED_SHA256,
        "fixture content drift; re-pin the sha256 oracle instead of silently accepting it"
    );
    assert_eq!(
        source.package.manifest().source.bytes,
        MIXED_XML.len() as u64,
        "the pinned fixture length must match the captured source length"
    );
    source
}

// ------------------------------------------------------- projection text #

/// The embedding input: the cleaned projection's inline decoded text, in
/// record order, joined deterministically. It is read from the projection's
/// read-back — never from a constant in this file.
fn projection_text(readback: &CleanedProjection) -> String {
    let mut text = String::new();
    for (index, entry) in readback.inline_texts.iter().enumerate() {
        if index > 0 {
            text.push('\n');
        }
        text.push_str(&entry.text);
    }
    text
}

// ----------------------------------------------------------- digests #

/// FNV-1a (64-bit) over raw bytes. A deterministic structural label, not a
/// seal and never a payload carrier.
fn fnv1a64_hex(bytes: &[u8]) -> String {
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    for byte in bytes {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
    }
    format!("{hash:016x}")
}

fn text_digest(text: &str) -> String {
    fnv1a64_hex(text.as_bytes())
}

/// Digest over the exact `f32` bit patterns, so a `NaN` or a one-bit drift
/// surfaces as a different digest.
fn vector_digest(vector: &[f32]) -> String {
    let mut bytes = Vec::with_capacity(vector.len() * 4);
    for value in vector {
        bytes.extend_from_slice(&value.to_bits().to_le_bytes());
    }
    fnv1a64_hex(&bytes)
}

/// Raw bit patterns so equality is exact.
fn bits(vector: &[f32]) -> Vec<u32> {
    vector.iter().map(|value| value.to_bits()).collect()
}

// ------------------------------------------------------------- the seam #

/// Deterministic TEI adapter over the shared test transport: the same
/// [`TeiEmbeddingAdapter`] boundary the live S02 path uses, with no socket.
fn deterministic_adapter() -> TeiEmbeddingAdapter<DeterministicEmbeddingTransport> {
    let transport =
        DeterministicEmbeddingTransport::new(DIMENSIONS).expect("valid deterministic transport");
    TeiEmbeddingAdapter::try_new(transport, MODEL_ID, DIMENSIONS).expect("valid TEI adapter")
}

/// Provenance-bound artifact port over the deterministic seam.
fn deterministic_artifact_port()
-> ProvenancedEmbedding<TeiEmbeddingAdapter<DeterministicEmbeddingTransport>> {
    let adapter = deterministic_adapter();
    ProvenancedEmbedding::try_new(adapter, MODEL_ID, provenance(DIMENSIONS))
        .expect("valid provenance composition")
}

fn provenance(dimensions: usize) -> ModelProvenance {
    ModelProvenance::try_new(
        "https://example.invalid/embedding-model",
        "Apache-2.0",
        &format!("sha256:{}", "a".repeat(64)),
        dimensions,
        vec![
            ("pooling".to_owned(), "mean".to_owned()),
            ("normalize".to_owned(), "true".to_owned()),
        ],
    )
    .expect("valid provenance")
}

fn embedding_request(text: &str) -> EmbeddingRequest {
    EmbeddingRequest::try_new(text, MODEL_ID, DIMENSIONS).expect("valid embedding request")
}

// ----------------------------------------------------------- positivity #

#[test]
fn projection_text_is_non_empty_and_matches_declared_counts() {
    let source = pinned();
    let text = projection_text(&source.readback);

    // The text is a projection of what was captured, and the declared footer
    // counters recompute over the inline records it was taken from.
    assert!(
        !text.is_empty(),
        "text-not-from-projection: the cleaned projection must carry inline decoded text"
    );
    assert_eq!(
        source.readback.inline_texts.len(),
        source.projection.segments.len(),
        "every projected segment must have exactly one inline text record"
    );
    let declared_bytes: u64 = source
        .readback
        .inline_texts
        .iter()
        .map(|e| e.text_bytes)
        .sum();
    let declared_chars: u64 = source.readback.inline_texts.iter().map(|e| e.chars).sum();
    assert_eq!(
        declared_bytes, source.readback.counts.text_bytes,
        "inline text_bytes must recompute to the declared footer count"
    );
    assert_eq!(
        declared_chars, source.readback.counts.text_chars,
        "inline text_chars must recompute to the declared footer count"
    );

    // The fixture's own decoded literals must be present in the projection
    // text: the input really is this document's content.
    for token in ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"] {
        assert!(
            text.contains(token),
            "text-not-from-projection: projection text must carry fixture token {token}"
        );
    }

    println!(
        "S05 fixture_sha256={} text_len={} text_digest={} records_seal={}",
        source.package.manifest().source.sha256,
        text.len(),
        text_digest(&text),
        source.readback.records_seal_hash,
    );
}

#[test]
fn projection_text_reaches_tei_transport_seam_deterministically() {
    let source = pinned();
    let text = projection_text(&source.readback);
    let request = embedding_request(&text);

    // 1) Direct `EmbeddingRequest` through the TEI seam.
    let adapter = deterministic_adapter();
    let first = adapter
        .embed(&request)
        .expect("an honest deterministic seam must embed the projection text");
    assert_eq!(first.dimensions(), DIMENSIONS);
    assert_eq!(first.vector().len(), DIMENSIONS);
    assert!(first.vector().iter().all(|value| value.is_finite()));

    // 2) Repeat call and an independently constructed adapter agree exactly.
    let second = adapter.embed(&request).expect("repeat embed");
    assert_eq!(
        bits(first.vector()),
        bits(second.vector()),
        "deterministic-mismatch: repeat calls must be byte-identical"
    );
    let independent = deterministic_adapter()
        .embed(&request)
        .expect("independently constructed adapter");
    assert_eq!(
        bits(first.vector()),
        bits(independent.vector()),
        "deterministic-mismatch: independent adapters must agree byte-for-byte"
    );

    // 3) The bare deterministic port agrees with the seam it wraps.
    let embedder = DeterministicEmbedding::try_new(MODEL_ID, DIMENSIONS).expect("valid embedder");
    let direct = embedder
        .embed(&request)
        .expect("direct deterministic embed");
    assert_eq!(
        bits(first.vector()),
        bits(direct.vector()),
        "deterministic-mismatch: the seam and the port must produce the same vector"
    );

    // 4) The provenance-bearing artifact path over the same seam.
    let port = deterministic_artifact_port();
    let artifact_request =
        EmbeddingArtifactRequest::try_new(SUBJECT_REF, &text).expect("valid artifact request");
    let artifact = port
        .embed_artifact(&artifact_request)
        .expect("the artifact path must embed the projection text");
    assert_eq!(artifact.subject_ref(), SUBJECT_REF);
    assert_eq!(artifact.dimensions(), DIMENSIONS);
    assert_eq!(
        bits(artifact.vector()),
        bits(first.vector()),
        "deterministic-mismatch: the artifact path must share the seam's vector"
    );

    println!(
        "S05 text_len={} text_digest={} vector_digest={}",
        text.len(),
        text_digest(&text),
        vector_digest(first.vector()),
    );
}

// ------------------------------------------------------- origin control #

/// The Integration-class proof: the embedding input tracks the projection.
///
/// Building the projection from altered source bytes changes the extracted
/// text, its digest and the resulting vector. A self-contained constant in
/// this test could not exhibit that dependency, so the sensitivity is the
/// evidence that the text genuinely comes from the projection.
#[test]
fn changed_projection_text_changes_the_embedding_input() {
    let honest = pinned();
    let honest_text = projection_text(&honest.readback);

    let altered_xml = MIXED_XML.replace("Alpha", "Omega");
    assert_ne!(
        altered_xml, MIXED_XML,
        "the origin control needs an actually altered fixture"
    );
    let altered = build(&altered_xml);

    // The pin is a real discriminator: the altered bytes are not the frozen
    // fixture, which is why they are built without the pin assertion.
    assert_ne!(
        altered.package.manifest().source.sha256,
        MIXED_SHA256,
        "text-not-from-projection: altered bytes must not collide with the pinned fixture"
    );

    let altered_text = projection_text(&altered.readback);
    assert!(
        honest_text.contains("Alpha") && !honest_text.contains("Omega"),
        "text-not-from-projection: the honest projection must carry the original literal"
    );
    assert!(
        altered_text.contains("Omega") && !altered_text.contains("Alpha"),
        "text-not-from-projection: the altered projection must carry the replacement literal"
    );
    assert_ne!(
        honest_text, altered_text,
        "text-not-from-projection: changed projection text must change the extracted text"
    );
    assert_ne!(
        text_digest(&honest_text),
        text_digest(&altered_text),
        "text-not-from-projection: changed projection text must change the input digest"
    );

    // ... and the change propagates through the transport seam.
    let adapter = deterministic_adapter();
    let honest_vector = adapter
        .embed(&embedding_request(&honest_text))
        .expect("honest projection embed")
        .vector()
        .to_vec();
    let altered_vector = adapter
        .embed(&embedding_request(&altered_text))
        .expect("altered projection embed")
        .vector()
        .to_vec();
    assert_ne!(
        bits(&honest_vector),
        bits(&altered_vector),
        "text-not-from-projection: different projection text must yield a different vector"
    );
    assert_ne!(
        vector_digest(&honest_vector),
        vector_digest(&altered_vector),
        "text-not-from-projection: different projection text must yield a different vector digest"
    );
}

// ----------------------------------------------------------- fail closed #

/// A transport that is unreachable, for the fail-closed control.
struct UnavailableTransport;

impl EmbeddingTransport for UnavailableTransport {
    fn embed_text(&self, _text: &str) -> Result<Vec<f32>, TransportError> {
        Err(TransportError::Unavailable)
    }
}

/// A transport that answers with a server-side detail that must not leak.
struct BadResponseTransport;

impl EmbeddingTransport for BadResponseTransport {
    fn embed_text(&self, _text: &str) -> Result<Vec<f32>, TransportError> {
        Err(TransportError::BadResponse(
            "server-side detail that must not leak".to_owned(),
        ))
    }
}

#[test]
fn unavailable_transport_is_fail_closed_without_artifact() {
    let source = pinned();
    let text = projection_text(&source.readback);
    let request = embedding_request(&text);

    // Direct seam: the closed typed error, no panic.
    let adapter = TeiEmbeddingAdapter::try_new(UnavailableTransport, MODEL_ID, DIMENSIONS)
        .expect("valid adapter over the unavailable transport");
    assert_eq!(
        adapter.embed(&request),
        Err(StorageError::TransportUnavailable)
    );

    // Artifact path: the same typed error and therefore no artifact.
    let port = ProvenancedEmbedding::try_new(adapter, MODEL_ID, provenance(DIMENSIONS))
        .expect("valid provenance composition");
    let artifact_request =
        EmbeddingArtifactRequest::try_new(SUBJECT_REF, &text).expect("valid artifact request");
    assert_eq!(
        port.embed_artifact(&artifact_request),
        Err(StorageError::TransportUnavailable)
    );
}

#[test]
fn bad_response_transport_is_typed_and_does_not_leak_payload() {
    let source = pinned();
    let text = projection_text(&source.readback);
    let request = embedding_request(&text);

    let adapter = TeiEmbeddingAdapter::try_new(BadResponseTransport, MODEL_ID, DIMENSIONS)
        .expect("valid adapter over the bad-response transport");
    let error = adapter
        .embed(&request)
        .expect_err("a bad transport response must fail closed");
    assert_eq!(error, StorageError::TransportBadResponse);
    assert!(
        !format!("{error:?}").contains("server-side detail"),
        "the boundary error must not carry raw transport payload"
    );
    assert!(
        !error.to_string().contains("server-side detail"),
        "the boundary error display must not carry raw transport payload"
    );
}

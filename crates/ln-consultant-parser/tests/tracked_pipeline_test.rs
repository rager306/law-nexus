//! Tracked Consultant system contract: hyperlink → scored classify → edges → observations.
//!
//! Non-claims: one tracked fixture; bounded pipeline mechanics only.
//! This is not legal, corpus, or citation correctness.

use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;

use ln_consultant_parser::{
    classify_all_scored_for_path, collect_observations, derive_edges, extract_hyperlinks,
    ClassifiedLink, DerivedEdge, Observation, RawLink,
};
use ln_decode::{
    adapters::ConsultantWordMlBlockDecoder,
    domain::{BlockDecodeErrorKind, DecodePhase, DecodeRequest, FamilyFormat, PayloadRef},
    ports::BlockDecoderPort,
};

/// Tracked 435-ФЗ Consultant WordML fixture (repository-relative).
const TRACKED_FIXTURE: &str = "law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml";

/// Stable source consid token for this contract (not a legal identifier).
const SOURCE_CONSID: &str = "consultantplus://offline/ref=TRACKED_435_FZ";

/// Counts observed independently on two pipeline runs before locking.
const EXPECTED_LINKS: usize = 61;
const EXPECTED_AMENDS: usize = 2;
const EXPECTED_IMPLEMENTS: usize = 2;
const EXPECTED_UNKNOWN: usize = 57;
const EXPECTED_EDGES: usize = 4;
const EXPECTED_OBSERVATIONS: usize = 45;
const EXPECTED_OCCURRENCE_TOTAL: usize = 57;
const EXPECTED_UNIQUE_DEST_TOTAL: usize = 52;

#[derive(Debug, Clone, PartialEq, Eq)]
struct PipelineSummary {
    link_count: usize,
    classified_count: usize,
    kind_counts: BTreeMap<String, usize>,
    edge_count: usize,
    edge_kind_counts: BTreeMap<String, usize>,
    observation_count: usize,
    observation_occurrence_total: usize,
    observation_unique_dest_total: usize,
}

fn tracked_fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(TRACKED_FIXTURE)
}

fn count_kinds(items: impl Iterator<Item = String>) -> BTreeMap<String, usize> {
    let mut counts = BTreeMap::new();
    for kind in items {
        *counts.entry(kind).or_insert(0) += 1;
    }
    counts
}

fn summarize(
    links: &[RawLink],
    classified: &[ClassifiedLink],
    edges: &[DerivedEdge],
    observations: &[Observation],
) -> PipelineSummary {
    PipelineSummary {
        link_count: links.len(),
        classified_count: classified.len(),
        kind_counts: count_kinds(classified.iter().map(|c| c.kind.clone())),
        edge_count: edges.len(),
        edge_kind_counts: count_kinds(edges.iter().map(|e| e.kind.clone())),
        observation_count: observations.len(),
        observation_occurrence_total: observations.iter().map(|o| o.occurrences).sum(),
        observation_unique_dest_total: observations.iter().map(|o| o.unique_dests).sum(),
    }
}

fn run_pipeline(xml: &[u8], source_path: &str) -> PipelineSummary {
    let links = extract_hyperlinks(xml);
    let classified = classify_all_scored_for_path(&links, source_path);
    let edges = derive_edges(&classified, SOURCE_CONSID);
    let observations = collect_observations(&classified);
    summarize(&links, &classified, &edges, &observations)
}

#[test]
fn tracked_435fz_pipeline_is_deterministic_and_bounded() {
    let path = tracked_fixture_path();
    let xml = std::fs::read(&path).unwrap_or_else(|err| {
        panic!(
            "tracked Consultant fixture must be readable at {}; error={err}",
            path.display()
        )
    });
    let source_path = path.to_string_lossy();

    let first = run_pipeline(&xml, &source_path);
    let second = run_pipeline(&xml, &source_path);

    eprintln!(
        "tracked 435-FZ pipeline: links={} classified={} kinds={:?} edges={} edge_kinds={:?} observations={} occ={} unique_dests={}",
        first.link_count,
        first.classified_count,
        first.kind_counts,
        first.edge_count,
        first.edge_kind_counts,
        first.observation_count,
        first.observation_occurrence_total,
        first.observation_unique_dest_total
    );

    assert_eq!(first, second, "repeat pipeline must be deterministic");
    assert!(
        first.link_count > 0,
        "tracked fixture must extract hyperlinks"
    );
    assert_eq!(first.link_count, first.classified_count);
    assert!(
        first.edge_count > 0,
        "known classified links must yield edges"
    );
    assert!(
        first.observation_count > 0,
        "unknown classified links must yield observations"
    );

    assert_eq!(first.link_count, EXPECTED_LINKS);
    assert_eq!(first.classified_count, EXPECTED_LINKS);
    assert_eq!(
        first.kind_counts.get("amends").copied(),
        Some(EXPECTED_AMENDS)
    );
    assert_eq!(
        first.kind_counts.get("implements").copied(),
        Some(EXPECTED_IMPLEMENTS)
    );
    assert_eq!(
        first.kind_counts.get("unknown").copied(),
        Some(EXPECTED_UNKNOWN)
    );
    assert_eq!(first.edge_count, EXPECTED_EDGES);
    assert_eq!(
        first.edge_kind_counts.get("amends").copied(),
        Some(EXPECTED_AMENDS)
    );
    assert_eq!(
        first.edge_kind_counts.get("implements").copied(),
        Some(EXPECTED_IMPLEMENTS)
    );
    assert_eq!(first.observation_count, EXPECTED_OBSERVATIONS);
    assert_eq!(
        first.observation_occurrence_total,
        EXPECTED_OCCURRENCE_TOTAL
    );
    assert_eq!(
        first.observation_unique_dest_total,
        EXPECTED_UNIQUE_DEST_TOTAL
    );

    let kind_sum: usize = first.kind_counts.values().sum();
    assert_eq!(kind_sum, first.classified_count);
    let known: usize = first
        .kind_counts
        .iter()
        .filter(|(kind, _)| kind.as_str() != "unknown")
        .map(|(_, count)| *count)
        .sum();
    let unknown = first.kind_counts.get("unknown").copied().unwrap_or(0);
    assert_eq!(known + unknown, first.classified_count);
    assert_eq!(known, first.edge_count);
    assert_eq!(unknown, first.observation_occurrence_total);
    assert!(first.observation_unique_dest_total > 0);
    assert!(first.observation_unique_dest_total <= first.observation_occurrence_total);

    let links = extract_hyperlinks(&xml);
    let classified = classify_all_scored_for_path(&links, &source_path);
    let edges = derive_edges(&classified, SOURCE_CONSID);
    let observations = collect_observations(&classified);

    for edge in &edges {
        assert!(
            edge.confidence > 0.0,
            "derived edge confidence must be positive"
        );
        assert_eq!(edge.provenance, SOURCE_CONSID);
        if edge.kind == "amends" {
            assert_eq!(
                edge.to_consider, SOURCE_CONSID,
                "amends edge must point dest/amending token -> source token"
            );
            assert_ne!(edge.from_consider, SOURCE_CONSID);
        } else {
            assert_eq!(
                edge.from_consider, SOURCE_CONSID,
                "non-amends edge must point source token -> dest"
            );
            assert_ne!(edge.to_consider, SOURCE_CONSID);
        }
    }

    let unknown_texts: BTreeSet<&str> = classified
        .iter()
        .filter(|c| c.kind == "unknown")
        .map(|c| c.text.as_str())
        .collect();
    for observation in &observations {
        assert!(
            unknown_texts.contains(observation.link_text.as_str()),
            "observations must correspond only to unknown links"
        );
        assert!(observation.occurrences > 0);
        assert!(observation.unique_dests > 0);
        assert!(observation.unique_dests <= observation.occurrences);
        assert_eq!(observation.status, "candidate");
    }
    assert_eq!(
        observations.iter().map(|o| o.occurrences).sum::<usize>(),
        unknown
    );

    // Independently inspectable dest/text/context triples from the tracked fixture.
    // Failure messages stay bounded: no large legal text, no full dest dump.
    let brand_anchor = classified.iter().find(|c| {
        c.dest == "https://www.consultant.ru"
            && c.text == "КонсультантПлюс"
            && c.context.contains("КонсультантПлюс")
    });
    assert!(
        brand_anchor.is_some(),
        "brand tracked anchor dest/text/context must be present"
    );

    let host_anchor = classified.iter().find(|c| {
        c.dest == "https://www.consultant.ru"
            && c.text == "www.consultant.ru"
            && c.context.contains("www.consultant.ru")
    });
    assert!(
        host_anchor.is_some(),
        "host tracked anchor dest/text/context must be present"
    );

    let amendment_anchor = classified.iter().find(|c| {
        c.dest.starts_with("consultantplus://offline/ref=")
            && c.text == "закона"
            && c.context.contains("в ред.")
            && c.context.contains("Федерального закона")
    });
    assert!(
        amendment_anchor.is_some(),
        "internal amendment-context dest/text/context must be present"
    );
    assert_ne!(
        brand_anchor.map(|c| c.text.as_str()),
        host_anchor.map(|c| c.text.as_str()),
        "selected anchors must be independently inspectable"
    );
}

#[test]
fn malformed_consultant_wordml_fails_atomically_in_decode() {
    // extract_hyperlinks is a bounded scanner, not an XML validator.
    // Decode owns typed atomic validation via BlockDecoderPort.
    let malformed = b"<w:wordDocument xmlns:w=\"urn:word\"><w:p><w:r><w:t>x";
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:tracked-pipeline-malformed").expect("valid payload ref"),
        FamilyFormat::parse("family:consultant-wordml").expect("valid family format"),
        malformed,
    );

    // Bounded scanner boundary: extract_hyperlinks scans for <w:hlink without
    // validating XML, so the same malformed input yields an empty scan, never
    // a panic and never a partial link.
    assert!(
        extract_hyperlinks(malformed).is_empty(),
        "bounded scanner must not validate malformed XML"
    );

    // Decode owns XML validation: the same input fails atomically with a typed
    // error and no partial blocks (decode_blocks returns Err, not Ok(partial)).
    let error = ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect_err("malformed Consultant WordML must fail atomically");

    assert_eq!(error.phase(), DecodePhase::Parse);
    assert_eq!(error.kind(), BlockDecodeErrorKind::MalformedInput);
    assert_eq!(error.byte_offset(), Some(malformed.len()));
    assert!(!error.to_string().contains("w:wordDocument"));
}

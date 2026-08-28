//! M186 S03 T01 evidence battery: 484-FZ -> 44-FZ statya 93 `amends` as a
//! documented composition of three hops over the pinned S01 canon:
//!
//! 1. Parser hop (skip-capable): the real ConsultantPlus XML on disk matches
//!    the pinned SHA and yields >=1 hyperlink referencing statya 93 of 44-FZ.
//!    `w:dest` stays an opaque consultantplus:// token - parse is not
//!    resolve, and `derive_edges` is deliberately not called here.
//! 2. Constructor hop (always, no disk): the D292 composition replayed -
//!    works-table expression minting, hierarchy-map lift of 44-FZ statya 93,
//!    cross-act edge port. Same APIs as real_cross_act_edges.rs; no new
//!    product constructors.
//! 3. Timeline hop (always): an empty force timeline resolves Unknown, and
//!    an Unknown "transition" is rejected - no InForce laundering of R070.
//!
//! Plus one pitfall guard: feeding a classified amends link found inside the
//! C1 amending act into the generic `derive_edges` INVERTS the edge (from =
//! link dest, to = source document) - exactly why this battery composes the
//! constructor instead (MEM1166/D293).
//!
//! R070 stays named-open: nothing here claims a named-amendment graph,
//! official-corpus admission, or an in-force date. Honesty leftovers are
//! T02's job, not this test's.

use ln_consultant_parser::{derive_edges, extract_hyperlinks, ClassifiedLink};
use ln_kb_ontology::domain::{
    map_hierarchy_marker, try_cross_act_edge, HierarchyMapOutcome, HierarchyMarker,
};
use ln_kb_ontology::registry::{load_expression_id_for_path, load_hierarchy_map_for_path};
use ln_temporal::domain::{
    resolve_force_status_at, AmendingActId, ComponentConceptId, ForceStatusEvent,
    ForceStatusTimeline, NormativeState, NormativeStateError,
};

/// S01 pin: sha256 of the real consru_export canon 484-FZ XML (252478 bytes).
/// The twin `law_2024-12-26_484-fz_rev-unknown_49a92fbb.xml` is NOT canon.
const PINNED_CANON_484_SHA256: &str =
    "67f781dbd6a7d03d6035e6a509c983b17fcc519213c493987cf8f71debc1a37d";
const EXPECTED_484_EXPRESSION_ID: &str = "expr:ru:federal:zakon:2024-12-26:484-fz:2024-12-26";

const CONSULTANT_EXPORT_DIR_ENV: &str = "CONSULTANT_EXPORT_DIR";
const CONSULTANT_EXPORT_DIR_DEFAULT: &str = "consru_export";

/// CONSULTANT_EXPORT_DIR with empty-as-unset semantics (M185 S03): unset,
/// empty, or whitespace-only values fall back to the default export dir.
fn consultant_export_dir() -> String {
    match std::env::var(CONSULTANT_EXPORT_DIR_ENV) {
        Ok(value) if !value.trim().is_empty() => value,
        _ => CONSULTANT_EXPORT_DIR_DEFAULT.to_owned(),
    }
}

/// Real consru_export canon file for the 484-FZ amending act (M186 S01 pin;
/// skip-capable: None when the gitignored local export is absent).
fn real_484_canon_path() -> Option<std::path::PathBuf> {
    let dir = consultant_export_dir();
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(dir)
        .join("consru_export/exports/npa/law_2024-12-26_484-fz_rev-unknown_1a599b98.xml");
    root.exists().then_some(root)
}

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

/// Needles from the task plan: dative, genitive, and the explicit part-1
/// reference of 44-FZ statya 93.
fn mentions_statya_93(s: &str) -> bool {
    s.contains("статье 93") || s.contains("статьи 93") || s.contains("части 1 статьи 93")
}

/// Hop 1 - parser (skip-capable). The pinned canon is read as bytes only:
/// no XML copy into law-source, no include_str, no classifier needle
/// changes, and `derive_edges` is not called (that path would invert the
/// amends edge - see the pitfall guard below).
#[test]
fn parser_hop_pinned_canon_yields_statya_93_hyperlink() {
    let Some(path) = real_484_canon_path() else {
        eprintln!("SKIP: consru_export 484 not available");
        return;
    };
    let xml = match std::fs::read(&path) {
        Ok(xml) => xml,
        Err(err) => {
            eprintln!("SKIP: consru_export 484 not available: {err}");
            return;
        }
    };

    // Pin integrity: sha256sum subprocess (argv array, not a shell string).
    let output = match std::process::Command::new("sha256sum").arg(&path).output() {
        Ok(output) => output,
        Err(err) => {
            eprintln!("SKIP: sha256sum not available: {err}");
            return;
        }
    };
    if !output.status.success() {
        eprintln!(
            "SKIP: sha256sum failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        return;
    }
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        stdout.starts_with(PINNED_CANON_484_SHA256),
        "canon on disk must match the pinned sha256 (twin 49a92fbb is not canon): got {}",
        stdout.trim()
    );

    let links = extract_hyperlinks(&xml);
    assert!(!links.is_empty(), "canon must contain w:hlink hyperlinks");
    let statya_93 = links
        .iter()
        .filter(|l| mentions_statya_93(&l.text) || mentions_statya_93(&l.context))
        .count();
    eprintln!(
        "[parser-hop] hyperlinks={} statya93_hits={}",
        links.len(),
        statya_93
    );
    assert!(
        statya_93 >= 1,
        "expected >=1 hyperlink referencing 44-FZ statya 93, got {statya_93}"
    );
    assert!(
        links.iter().all(|l| !l.dest.starts_with("cc:")),
        "w:dest must stay opaque consultantplus:// - parse is not resolve"
    );
}

/// Hop 2 - constructor (always, no disk). S02 composition replayed end to
/// end: the 484 works entry mints its real expression id, the real 44-FZ
/// corpus map lifts statya 93, and the cross-act edge port accepts the
/// amends edge. NOT derive_edges-as-constructor (D292/D216), and NOT the
/// toy n-44-fz fixture (31/43/95 only - statya 93 would stay Unknown there).
#[test]
fn constructor_hop_484_amends_44fz_statya_93() {
    let expr = load_expression_id_for_path("law_2024-12-26_484-fz").expect("484 expression");
    assert_eq!(expr, EXPECTED_484_EXPRESSION_ID);

    let map = load_hierarchy_map_for_path("law_2013-04-05_44-fz").expect("44 map");
    // work_id stays None: 44-FZ registry bindings are work-less; number is
    // the flat key_path.
    let marker = HierarchyMarker::try_new(None, "statya", "93", None).expect("marker");
    let bound = match map_hierarchy_marker(&map, &marker) {
        HierarchyMapOutcome::Bound { component } => component,
        other => panic!("expected Bound for 44-fz statya 93, got {other:?}"),
    };
    assert_eq!(bound.as_str(), "cc:44-fz:statya-93");

    let edge = try_cross_act_edge("amends", &cc("cc:484-fz:statya-1"), &bound, &expr)
        .expect("real 484 amends edge");
    assert_eq!(edge.kind, "amends");
    assert_eq!(edge.from_cc.as_str(), "cc:484-fz:statya-1");
    assert_eq!(edge.to_cc.as_str(), "cc:44-fz:statya-93");
    let prov = edge.provenance().as_str();
    assert!(
        prov.contains("484-fz"),
        "provenance must carry the amending act: {prov}"
    );
    assert!(
        prov.contains("2024-12-26"),
        "provenance must carry the enactment/edition day: {prov}"
    );
}

/// Hop 3a - timeline (always). The edge minted above carries no force
/// status: with an empty timeline the resolver must answer Unknown, never
/// InForce (no append, no project_force_event - that would launder R070).
#[test]
fn timeline_hop_empty_timeline_resolves_unknown_not_in_force() {
    let timeline = ForceStatusTimeline::empty();
    let result = resolve_force_status_at(&timeline, &cc("cc:44-fz:statya-93"), 1).expect("resolve");
    assert_eq!(result.status, NormativeState::Unknown);
}

/// Hop 3b - timeline (always). Unknown is not a transition status: an event
/// claiming "statya 93 became Unknown because of 484-FZ" cannot even be
/// built (fail-closed ADR-0018).
#[test]
fn timeline_hop_unknown_is_rejected_as_transition_status() {
    let act = AmendingActId::parse("act:ru:federal:zakon:2024-12-26:484-fz").expect("act id");
    let err = ForceStatusEvent::try_new(cc("cc:44-fz:statya-93"), NormativeState::Unknown, 1, act)
        .expect_err("unknown is not a transition");
    assert!(matches!(err, NormativeStateError::UnknownNotTransition));
}

/// Pitfall guard (MEM1166/D293): the generic product deriver, fed a
/// classified amends link found *inside the C1 amending act*, inverts the
/// edge - `from` = link dest, `to` = the source document. That inversion is
/// correct for links inside 44-FZ but wrong as a constructor for parsed C1
/// acts, which is why hop 2 composes the registry/map/edge port instead and
/// this battery never calls derive_edges on the real canon.
#[test]
fn pitfall_guard_derive_edges_on_c1_source_inverts_amends_edge() {
    let link = ClassifiedLink {
        kind: "amends".to_owned(),
        dest: "consultantplus://offline/ref=FAKE44".to_owned(),
        text: "статьи 93".to_owned(),
        confidence: 0.9,
        context: String::new(),
    };
    let edges = derive_edges(&[link], "484-source");
    assert_eq!(edges.len(), 1);
    assert_eq!(edges[0].kind, "amends");
    // Inversion: from = link dest (amended act), to = source (amending act).
    assert_eq!(
        edges[0].from_consider,
        "consultantplus://offline/ref=FAKE44"
    );
    assert_eq!(edges[0].to_consider, "484-source");
    // The dest is never resolved to cc:44-fz:statya-93 by the deriver.
    assert_ne!(edges[0].from_consider, "cc:44-fz:statya-93");
}

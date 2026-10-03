//! S03 cleaned-navigation battery: unified node addressability, structural
//! links, the two deterministic orders and bounded note resolution over the
//! S02 read-back artifact.
//!
//! Every expected node set and order in this file is a **handwritten oracle**
//! computed by this test's own traversal of `ReaderProjection` plus the frozen
//! `source_package` pre-order element positions. It never calls `cleaned_nav`
//! or `cleaned_nav_verifier` internals and never reuses their helpers: the
//! builder and the independent verifier are the two things under test, so a
//! third private derivation is the evidence.
//!
//! The pinned `mixed-wordml.xml` fixture and the nine positive reader fixtures
//! are driven through `source_package::capture` →
//! `reader_projection::build_projection` →
//! `cleaned_wire::render_cleaned_projection` →
//! `cleaned_wire::read_cleaned_wire` → `cleaned_nav::build_nav_index` →
//! `cleaned_nav_verifier::verify_nav_index`.
//!
//! Non-claims: `[bounded]` to the ten self-authored non-legal synthetic
//! fixtures under `tests/fixtures/reader/`. Not corpus coverage, not source
//! authenticity, not legal completeness, not a graph projection, not citation
//! resolution, not region classification. R1000 stays active. Raw decoded legal
//! text is never logged.

use std::collections::{BTreeMap, BTreeSet, HashMap};

use ln_decode::cleaned_nav::{
    build_nav_index, NavErrorKind, NavIndex, NavLink, NavLinkKind, NavResolveReason, NodeAddress,
};
use ln_decode::cleaned_nav_verifier::{verify_nav_index, NavVerifyCode};
use ln_decode::cleaned_wire::{
    read_cleaned_wire, render_cleaned_projection, CleanedProjection, WireCompletion, WireLimits,
};
use ln_decode::reader_contract::{ReaderDerivedKind, ReaderReferenceType, ReaderViewKind};
use ln_decode::reader_projection::{
    build_projection, ProjectedView, ReaderProjection, ReferenceId, SegmentId, SegmentOrigin,
    ViewId,
};
use ln_decode::source_package::{capture, ElementRecord, Limits, Package, Record};

// ---------------------------------------------------------------- fixtures #

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

const NAV_DEMO: Fixture = Fixture {
    file: "navigation-demo.xml",
    xml: include_str!("fixtures/reader/diverse/navigation-demo.xml"),
    sha256: "b12bed26bde92a5516c9e2cbfe25333168cdd32101c3a4790c77357554c0a3f0",
};

const ALL: &[Fixture] = &[
    MIXED,
    Fixture {
        file: "controls.xml",
        xml: include_str!("fixtures/reader/diverse/controls.xml"),
        sha256: "86440c8cf2f16b88f9da919c77f04e9a2487ed3a0032305dd195aaf48e40988f",
    },
    Fixture {
        file: "unknown-wordml.xml",
        xml: include_str!("fixtures/reader/diverse/unknown-wordml.xml"),
        sha256: "afdfbd3f50377e95d31e736a14cbb2d72d1b2cd13446c4a672ebbc2037a20232",
    },
    Fixture {
        file: "residual-and-tails.xml",
        xml: include_str!("fixtures/reader/diverse/residual-and-tails.xml"),
        sha256: "424f7f117255472e320a1d86adb2a63d8985b97b435a262e3d2403c2767a6834",
    },
    Fixture {
        file: "encoding.xml",
        xml: include_str!("fixtures/reader/diverse/encoding.xml"),
        sha256: "6eaff6f86c7c542f875065f1ba383e52b0bd0703576d5fc58f90d7316807dbb2",
    },
    Fixture {
        file: "empty-structure.xml",
        xml: include_str!("fixtures/reader/diverse/empty-structure.xml"),
        sha256: "84a17e721a37879a8bd3e424a991168639766ec02921892bdc8994e9fcddeec4",
    },
    Fixture {
        file: "notes-nested.xml",
        xml: include_str!("fixtures/reader/diverse/notes-nested.xml"),
        sha256: "36d874f81bc456583687b6189d21ae2c7f5c3621a0373c6248cbe733e4fa9a75",
    },
    Fixture {
        file: "fields-revisions.xml",
        xml: include_str!("fixtures/reader/diverse/fields-revisions.xml"),
        sha256: "4e6ca62093eefb95fa49471b41de072a8e144ac2a867ffe894c0ce507ff17b0e",
    },
    NAV_DEMO,
    Fixture {
        file: "text-only.xml",
        xml: include_str!("fixtures/reader/diverse/text-only.xml"),
        sha256: "e13b8c7424100989028d95bd4c37bfadcd3970972329d93624c8da384507c55f",
    },
];

// ----------------------------------------------------------- build helpers #

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

fn read_back(fixture: &Fixture) -> (Package, CleanedProjection) {
    let package = capture_fixture(fixture);
    let projection = build_projection(package.records())
        .unwrap_or_else(|error| panic!("{} must project: {error:?}", fixture.file));
    let artifact = render_cleaned_projection(
        &package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .unwrap_or_else(|error| panic!("{} must render: {error:?}", fixture.file));
    let cleaned = read_cleaned_wire(&artifact)
        .unwrap_or_else(|error| panic!("{} must read back: {error:?}", fixture.file));
    (package, cleaned)
}

fn index_fixture(fixture: &Fixture) -> (Package, CleanedProjection, NavIndex) {
    let (package, cleaned) = read_back(fixture);
    let index = build_nav_index(&cleaned, &package)
        .unwrap_or_else(|error| panic!("{} must index: {error:?}", fixture.file));
    (package, cleaned, index)
}

// ------------------------------------------------------------ handwritten #
// The following oracle is deliberately a third, private re-derivation: it must
// not share code with `cleaned_nav` or `cleaned_nav_verifier`.

struct Oracle {
    nodes: BTreeSet<NodeAddress>,
    record_order: Vec<NodeAddress>,
    source_order: Vec<NodeAddress>,
}

/// Pre-order element position taken from the frozen package (element records
/// only), never parsed from an `eN` token.
fn element_positions(package: &Package) -> HashMap<&str, usize> {
    let mut positions: HashMap<&str, usize> = HashMap::new();
    let mut position = 0usize;
    for record in package.records() {
        if let Record::Element(element) = record {
            positions.entry(element.id.as_str()).or_insert(position);
            position += 1;
        }
    }
    positions
}

fn oracle(projection: &ReaderProjection, positions: &HashMap<&str, usize>) -> Oracle {
    let mut nodes: BTreeSet<NodeAddress> = BTreeSet::new();
    let mut record_order: Vec<NodeAddress> = Vec::new();
    for view in &projection.views {
        let address = NodeAddress::View(view.id.clone());
        nodes.insert(address.clone());
        record_order.push(address);
    }
    for segment in &projection.segments {
        let address = NodeAddress::Segment(segment.id.clone());
        nodes.insert(address.clone());
        record_order.push(address);
    }
    for reference in &projection.references {
        let address = NodeAddress::Reference(reference.id.clone());
        nodes.insert(address.clone());
        record_order.push(address);
    }

    let mut ordered_views: Vec<(usize, usize, &ProjectedView)> = projection
        .views
        .iter()
        .enumerate()
        .map(|(index, view)| {
            let position = positions
                .get(view.element_ref.as_str())
                .copied()
                .unwrap_or(usize::MAX);
            (position, index, view)
        })
        .collect();
    ordered_views.sort_by(|left, right| left.0.cmp(&right.0).then(left.1.cmp(&right.1)));

    let segment_ordinal: HashMap<&str, usize> = projection
        .segments
        .iter()
        .map(|segment| (segment.id.as_str(), segment.ordinal))
        .collect();
    let reference_ordinal: HashMap<&str, usize> = projection
        .references
        .iter()
        .map(|reference| (reference.id.as_str(), reference.ordinal))
        .collect();

    let mut source_order: Vec<NodeAddress> = Vec::new();
    for (_, _, view) in &ordered_views {
        source_order.push(NodeAddress::View(view.id.clone()));
    }
    for (_, _, view) in &ordered_views {
        let mut ids: Vec<&str> = view.segment_refs.iter().map(|id| id.as_str()).collect();
        ids.sort_by_key(|id| segment_ordinal.get(id).copied().unwrap_or(usize::MAX));
        for id in ids {
            source_order.push(NodeAddress::Segment(SegmentId::new(id)));
        }
    }
    for (_, _, view) in &ordered_views {
        let mut ids: Vec<&str> = view.reference_refs.iter().map(|id| id.as_str()).collect();
        ids.sort_by_key(|id| reference_ordinal.get(id).copied().unwrap_or(usize::MAX));
        for id in ids {
            source_order.push(NodeAddress::Reference(ReferenceId::new(id)));
        }
    }

    Oracle {
        nodes,
        record_order,
        source_order,
    }
}

// ------------------------------------------- private Clark-attribute oracle #

fn clark_local(name: &str) -> &str {
    if let Some(rest) = name.strip_prefix('{') {
        if let Some(close) = rest.find('}') {
            return &rest[close + 1..];
        }
    }
    name
}

fn attr_local<'a>(attrs: &'a BTreeMap<String, String>, local: &str) -> Option<&'a str> {
    attrs
        .iter()
        .find(|(key, _)| clark_local(key) == local)
        .map(|(_, value)| value.as_str())
}

fn element<'a>(package: &'a Package, id: &str) -> &'a ElementRecord {
    package
        .records()
        .iter()
        .find_map(|record| match record {
            Record::Element(element) if element.id == id => Some(element),
            _ => None,
        })
        .unwrap_or_else(|| panic!("element {id} must exist"))
}

fn reference_by_element<'a>(
    cleaned: &'a CleanedProjection,
    element_ref: &str,
) -> &'a ln_decode::reader_projection::ProjectedReference {
    cleaned
        .projection
        .references
        .iter()
        .find(|reference| reference.element_ref.as_str() == element_ref)
        .unwrap_or_else(|| panic!("reference on {element_ref} must exist"))
}

fn resolves_to_targets(index: &NavIndex, reference: &ReferenceId) -> Vec<NodeAddress> {
    index
        .links
        .iter()
        .filter(|link| {
            link.from == NodeAddress::Reference(reference.clone())
                && link.kind == NavLinkKind::ResolvesTo
        })
        .map(|link| link.to.clone())
        .collect()
}

fn view_kind_of(cleaned: &CleanedProjection, id: &ViewId) -> Option<ReaderViewKind> {
    cleaned
        .projection
        .views
        .iter()
        .find(|view| &view.id == id)
        .map(|view| view.kind)
}

fn ancestry_kinds(
    index: &NavIndex,
    cleaned: &CleanedProjection,
    view: &ProjectedView,
) -> Vec<ReaderViewKind> {
    index
        .path_to_root(&NodeAddress::View(view.id.clone()))
        .into_iter()
        .filter_map(|address| match address {
            NodeAddress::View(id) => view_kind_of(cleaned, &id),
            _ => None,
        })
        .collect()
}

// ------------------------------------------------------------------ tests #

#[test]
fn every_fixture_indexes_verifies_and_matches_oracle() {
    for fixture in ALL {
        let (package, cleaned, index) = index_fixture(fixture);
        let positions = element_positions(&package);
        let expected = oracle(&cleaned.projection, &positions);

        let actual_nodes: BTreeSet<NodeAddress> = index.nodes_by_address.keys().cloned().collect();
        assert_eq!(actual_nodes, expected.nodes, "{}: node set", fixture.file);
        assert_eq!(
            index.record_order, expected.record_order,
            "{}: record order",
            fixture.file
        );
        assert_eq!(
            index.source_order, expected.source_order,
            "{}: source order",
            fixture.file
        );
        assert_eq!(
            index.nodes_in_source_order(),
            expected.source_order.as_slice(),
            "{}: source order accessor",
            fixture.file
        );

        for view in &cleaned.projection.views {
            assert!(
                index.resolve(&NodeAddress::View(view.id.clone())).is_some(),
                "{}: view {} must resolve",
                fixture.file,
                view.id
            );
        }
        for segment in &cleaned.projection.segments {
            assert!(
                index
                    .resolve(&NodeAddress::Segment(segment.id.clone()))
                    .is_some(),
                "{}: segment {} must resolve",
                fixture.file,
                segment.id
            );
        }
        for reference in &cleaned.projection.references {
            assert!(
                index
                    .resolve(&NodeAddress::Reference(reference.id.clone()))
                    .is_some(),
                "{}: reference {} must resolve",
                fixture.file,
                reference.id
            );
        }

        for link in &index.links {
            assert!(
                index.resolve(&link.from).is_some(),
                "{}: link source must resolve",
                fixture.file
            );
            assert!(
                index.resolve(&link.to).is_some(),
                "{}: link target must resolve",
                fixture.file
            );
        }

        for view in &cleaned.projection.views {
            let address = NodeAddress::View(view.id.clone());
            assert!(index
                .anchors_of_element(&view.element_ref)
                .contains(&address));
        }
        for segment in &cleaned.projection.segments {
            let address = NodeAddress::Segment(segment.id.clone());
            assert!(index
                .anchors_of_element(&segment.element_ref)
                .contains(&address));
            if let Some(fragment) = &segment.fragment_ref {
                assert_eq!(
                    index.anchors_of_fragment(fragment),
                    Some(&address),
                    "{}: fragment anchor",
                    fixture.file
                );
            }
        }
        for reference in &cleaned.projection.references {
            let address = NodeAddress::Reference(reference.id.clone());
            assert!(index
                .anchors_of_element(&reference.element_ref)
                .contains(&address));
        }

        verify_nav_index(&index, &cleaned, &package)
            .unwrap_or_else(|findings| panic!("{}: nav verify failed: {findings:?}", fixture.file));
    }
}

#[test]
fn record_order_is_grouped_projection_order() {
    let (_package, cleaned, index) = index_fixture(&MIXED);
    let mut expected: Vec<NodeAddress> = Vec::new();
    for view in &cleaned.projection.views {
        expected.push(NodeAddress::View(view.id.clone()));
    }
    for segment in &cleaned.projection.segments {
        expected.push(NodeAddress::Segment(segment.id.clone()));
    }
    for reference in &cleaned.projection.references {
        expected.push(NodeAddress::Reference(reference.id.clone()));
    }
    assert_eq!(index.record_order, expected);
    assert_eq!(
        index.record_order.len(),
        cleaned.projection.views.len()
            + cleaned.projection.segments.len()
            + cleaned.projection.references.len()
    );
}

#[test]
fn mixed_footnote_resolves_to_its_note_view() {
    let (package, cleaned, index) = index_fixture(&MIXED);
    let reference = reference_by_element(&cleaned, "e41");
    assert_eq!(reference.reference_type, ReaderReferenceType::NoteReference);

    // Independent resolution: the anchor's local `id`, the single matching
    // `footnote` definition, and the note view anchored on it.
    let anchor = element(&package, "e41");
    let anchor_id = attr_local(&anchor.attrs, "id").expect("e41 must carry w:id");
    let definitions: Vec<&str> = package
        .records()
        .iter()
        .filter_map(|record| match record {
            Record::Element(element) => {
                if clark_local(&element.clark_tag) == "footnote"
                    && attr_local(&element.attrs, "id") == Some(anchor_id)
                {
                    Some(element.id.as_str())
                } else {
                    None
                }
            }
            Record::Text(_) => None,
        })
        .collect();
    assert_eq!(definitions.len(), 1, "exactly one footnote definition");

    let note_view = cleaned
        .projection
        .views
        .iter()
        .find(|view| {
            view.kind == ReaderViewKind::Note && view.element_ref.as_str() == definitions[0]
        })
        .expect("the definition must be anchored by a note view");

    assert_eq!(index.resolve_reason(&reference.id), None);
    assert_eq!(
        resolves_to_targets(&index, &reference.id),
        vec![NodeAddress::View(note_view.id.clone())]
    );
}

#[test]
fn mixed_second_footnote_reference_is_addressable_and_unresolved() {
    let (_package, cleaned, index) = index_fixture(&MIXED);
    let reference = reference_by_element(&cleaned, "e46");
    assert_eq!(reference.reference_type, ReaderReferenceType::NoteReference);
    assert!(index
        .resolve(&NodeAddress::Reference(reference.id.clone()))
        .is_some());
    assert_eq!(
        index.resolve_reason(&reference.id),
        Some(NavResolveReason::NoMatchingNoteDefinition)
    );
    assert!(resolves_to_targets(&index, &reference.id).is_empty());
}

#[test]
fn non_note_references_stay_closed_across_fixtures() {
    let mut seen_foreign = false;
    let mut seen_unknown = false;
    for fixture in ALL {
        let (_package, cleaned, index) = index_fixture(fixture);
        for reference in &cleaned.projection.references {
            assert!(
                index
                    .resolve(&NodeAddress::Reference(reference.id.clone()))
                    .is_some(),
                "{}: reference {} must be addressable",
                fixture.file,
                reference.id
            );
            match reference.reference_type {
                ReaderReferenceType::NoteReference | ReaderReferenceType::EndnoteReference => {}
                other => {
                    assert_eq!(
                        index.resolve_reason(&reference.id),
                        Some(NavResolveReason::NotAResolvableReference),
                        "{}: reference {} must stay closed",
                        fixture.file,
                        reference.id
                    );
                    assert!(
                        resolves_to_targets(&index, &reference.id).is_empty(),
                        "{}: reference {} must not resolve",
                        fixture.file,
                        reference.id
                    );
                    if other == ReaderReferenceType::ForeignElement {
                        seen_foreign = true;
                    }
                    if other == ReaderReferenceType::UnknownWordmlElement {
                        seen_unknown = true;
                    }
                }
            }
        }
    }
    assert!(
        seen_foreign,
        "a foreign-namespace reference must be covered"
    );
    assert!(seen_unknown, "an unknown WordML reference must be covered");
}

#[test]
fn navigation_demo_covers_structural_classes_and_nesting() {
    let (_package, cleaned, index) = index_fixture(&NAV_DEMO);

    for kind in [
        ReaderViewKind::Paragraph,
        ReaderViewKind::Table,
        ReaderViewKind::Row,
        ReaderViewKind::Cell,
        ReaderViewKind::Note,
    ] {
        let mut count = 0usize;
        for view in cleaned
            .projection
            .views
            .iter()
            .filter(|view| view.kind == kind)
        {
            count += 1;
            assert!(
                index.resolve(&NodeAddress::View(view.id.clone())).is_some(),
                "navigation-demo: {kind:?} view {} must be addressable",
                view.id
            );
        }
        assert!(count > 0, "navigation-demo must carry a {kind:?} view");
    }

    // The derived page-break segment is a first-class addressable node.
    let page_break = cleaned
        .projection
        .segments
        .iter()
        .find(|segment| segment.origin == SegmentOrigin::Derived(ReaderDerivedKind::PageBreak))
        .expect("navigation-demo must carry a derived page-break segment");
    assert!(index
        .resolve(&NodeAddress::Segment(page_break.id.clone()))
        .is_some());

    // A table nests under a note view; a note nests under another note view.
    let table_under_note = cleaned
        .projection
        .views
        .iter()
        .filter(|view| view.kind == ReaderViewKind::Table)
        .any(|table| ancestry_kinds(&index, &cleaned, table).contains(&ReaderViewKind::Note));
    assert!(table_under_note, "a table must nest under a note");

    let note_under_note = cleaned
        .projection
        .views
        .iter()
        .filter(|view| view.kind == ReaderViewKind::Note)
        .any(|note| {
            let chain = ancestry_kinds(&index, &cleaned, note);
            chain.len() >= 2 && chain[..chain.len() - 1].contains(&ReaderViewKind::Note)
        });
    assert!(note_under_note, "a note must nest under a note");
}

#[test]
fn paragraph_views_are_addressable_without_region_classification() {
    let mut total = 0usize;
    for fixture in ALL {
        let (_package, cleaned, index) = index_fixture(fixture);
        for view in cleaned
            .projection
            .views
            .iter()
            .filter(|view| view.kind == ReaderViewKind::Paragraph)
        {
            total += 1;
            let address = NodeAddress::View(view.id.clone());
            assert!(index.resolve(&address).is_some());
            assert!(index.source_order.contains(&address));
            // Bounded: no heading/body/annex region classifier is applied; a
            // paragraph node is returned by address wherever it sits in the
            // document.
        }
    }
    assert!(total > 0, "the fixture set must carry paragraph views");
}

#[test]
fn unknown_and_foreign_references_are_addressable() {
    let (_package, cleaned, index) = index_fixture(&MIXED);
    let mut foreign = 0usize;
    let mut unknown = 0usize;
    for reference in &cleaned.projection.references {
        match reference.reference_type {
            ReaderReferenceType::ForeignElement => {
                foreign += 1;
                assert!(index
                    .resolve(&NodeAddress::Reference(reference.id.clone()))
                    .is_some());
            }
            ReaderReferenceType::UnknownWordmlElement => {
                unknown += 1;
                assert!(index
                    .resolve(&NodeAddress::Reference(reference.id.clone()))
                    .is_some());
            }
            _ => {}
        }
    }
    assert!(foreign > 0, "mixed must carry a foreign reference");
    assert!(unknown > 0, "mixed must carry an unknown reference");
}

// --------------------------------------------------------------- tamper #

fn any_code(findings: &[ln_decode::cleaned_nav_verifier::NavFinding], code: NavVerifyCode) -> bool {
    findings.iter().any(|finding| finding.code == code)
}

#[test]
fn tampered_index_clone_fails_closed() {
    let (package, cleaned, index) = index_fixture(&MIXED);
    let first = index
        .nodes_by_address
        .keys()
        .next()
        .cloned()
        .expect("index must carry nodes");

    // Removed node.
    let mut removed = index.clone();
    removed.nodes_by_address.remove(&first);
    let findings = verify_nav_index(&removed, &cleaned, &package).expect_err("removal must refuse");
    assert!(any_code(&findings, NavVerifyCode::NodeSetMismatch));

    // Dangling link.
    let mut dangling = index.clone();
    dangling.links.push(NavLink {
        from: first.clone(),
        to: NodeAddress::View(ViewId::new("v999999")),
        kind: NavLinkKind::Contains,
    });
    let findings =
        verify_nav_index(&dangling, &cleaned, &package).expect_err("dangling must refuse");
    assert!(any_code(&findings, NavVerifyCode::LinkDangling));

    // Reordered source order.
    let mut reordered = index.clone();
    assert!(
        reordered.source_order.len() >= 2,
        "fixture must carry nodes"
    );
    reordered.source_order.swap(0, 1);
    let findings =
        verify_nav_index(&reordered, &cleaned, &package).expect_err("reorder must refuse");
    assert!(any_code(&findings, NavVerifyCode::SourceOrderMismatch));

    // Duplicate link.
    let mut duplicated = index.clone();
    duplicated.links.push(duplicated.links[0].clone());
    let findings =
        verify_nav_index(&duplicated, &cleaned, &package).expect_err("duplicate must refuse");
    assert!(any_code(
        &findings,
        NavVerifyCode::LinkDuplicateOrMisordered
    ));
}

#[test]
fn dangling_child_ref_fails_closed_in_builder() {
    let (package, mut cleaned, _index) = index_fixture(&MIXED);
    cleaned.projection.views[0]
        .children
        .push(ViewId::new("v999999"));
    let error = build_nav_index(&cleaned, &package).expect_err("dangling child must refuse");
    assert_eq!(error.kind(), NavErrorKind::DanglingViewRef);
}

#[test]
fn extra_or_missing_projection_node_fails_closed_in_verifier() {
    let (package, cleaned, index) = index_fixture(&MIXED);

    // Extra node in the projection the index does not describe.
    let mut extra = cleaned.clone();
    let mut clone = extra.projection.views[0].clone();
    clone.id = ViewId::new("v999999");
    extra.projection.views.push(clone);
    let findings = verify_nav_index(&index, &extra, &package).expect_err("extra node must refuse");
    assert!(any_code(&findings, NavVerifyCode::NodeSetMismatch));

    // Missing node the index still claims.
    let mut missing = cleaned.clone();
    missing.projection.views.pop();
    let findings =
        verify_nav_index(&index, &missing, &package).expect_err("missing node must refuse");
    assert!(any_code(&findings, NavVerifyCode::NodeSetMismatch));
}

#[test]
fn diagnostics_carry_no_decoded_text() {
    const NEEDLES: &[&str] = &[
        "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa",
        "Lambda", "Nu",
    ];

    // A builder failure.
    let (package, mut cleaned, _index) = index_fixture(&MIXED);
    cleaned.projection.views[0]
        .children
        .push(ViewId::new("v999999"));
    let error = build_nav_index(&cleaned, &package).expect_err("dangling child must refuse");
    for needle in NEEDLES {
        assert!(
            !error.detail().contains(needle),
            "NavError detail leaked decoded text"
        );
    }
    assert!(error.detail().contains("v999999"));

    // A verifier failure.
    let (package, cleaned, index) = index_fixture(&MIXED);
    let first = index.nodes_by_address.keys().next().cloned().expect("node");
    let mut dangling = index.clone();
    dangling.links.push(NavLink {
        from: first,
        to: NodeAddress::View(ViewId::new("v999999")),
        kind: NavLinkKind::Contains,
    });
    let findings = verify_nav_index(&dangling, &cleaned, &package).expect_err("must refuse");
    for finding in &findings {
        for needle in NEEDLES {
            assert!(
                !finding.detail.contains(needle),
                "NavFinding detail leaked decoded text"
            );
        }
    }
}

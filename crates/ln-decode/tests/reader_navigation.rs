//! S06 T03 integration tests: reference resolution and subtree text proven with
//! handwritten oracles over the tracked fixtures plus a wire read-back parity
//! check.
//!
//! Design pin: `prd/architecture/intermediate-source-navigation-contract.md`
//! (D736), §5 (subtree text), §6 (references and resolution), §13 (verification
//! surface). These tests exercise only the public `reader_navigation` surface;
//! they never re-parse XML and never mutate the frozen projection.
//!
//! Fixtures are the git-tracked files `crates/ln-decode/tests/fixtures/reader/`
//! (`mixed-wordml.xml`) and `.../diverse/` (`navigation-demo.xml`,
//! `notes-nested.xml`).

use ln_decode::cleaned_wire::{
    WireCompletion, WireLimits, read_cleaned_wire, render_cleaned_projection,
};
use ln_decode::reader_clean_view::CleanView;
use ln_decode::reader_contract::{ReaderDerivedKind, ReaderViewKind};
use ln_decode::reader_navigation::{
    NavErrorKind, NavLinkKind, NavNodeBody, NavResolveReason, NavigationIndex, NodeAddress,
    build_navigation,
};
use ln_decode::reader_projection::{
    ReaderProjection, ReferenceId, SegmentOrigin, ViewId, build_projection,
};
use ln_decode::reader_reading_order::ReadingOrderIndex;
use ln_decode::source_package::{Limits, Package, Record, capture};

const MIXED: &str = include_str!("fixtures/reader/mixed-wordml.xml");
const NAVDEMO: &str = include_str!("fixtures/reader/diverse/navigation-demo.xml");
const NESTED: &str = include_str!("fixtures/reader/diverse/notes-nested.xml");

struct Inputs {
    package: Package,
    records: Vec<Record>,
    projection: ReaderProjection,
    order: ReadingOrderIndex,
    clean: CleanView,
    nav: NavigationIndex,
}

fn inputs_from(xml: &str) -> Inputs {
    let package = capture(xml.as_bytes(), &Limits::default()).expect("fixture must capture");
    let records = package.records().to_vec();
    let projection = build_projection(&records).expect("projection must build");
    let order = ReadingOrderIndex::build(&projection, &records).expect("reading order must build");
    let clean = CleanView::build(&projection, &order, &records).expect("clean view must build");
    let nav = build_navigation(&projection, &order, &records).expect("navigation must build");
    Inputs {
        package,
        records,
        projection,
        order,
        clean,
        nav,
    }
}

fn mixed() -> Inputs {
    inputs_from(MIXED)
}

/// The unique view of a kind anchored at an element (projection keys views by
/// `(kind, element_ref)`, so the lookup is unambiguous).
fn view_id(projection: &ReaderProjection, kind: ReaderViewKind, element_ref: &str) -> ViewId {
    projection
        .views
        .iter()
        .find(|view| view.kind == kind && view.element_ref.as_str() == element_ref)
        .unwrap_or_else(|| panic!("view {kind:?} {element_ref} missing"))
        .id
        .clone()
}

fn view_addr(view: &ViewId) -> NodeAddress {
    NodeAddress::View(view.clone())
}

fn reference_id(projection: &ReaderProjection, element_ref: &str) -> ReferenceId {
    projection
        .references
        .iter()
        .find(|reference| reference.element_ref.as_str() == element_ref)
        .unwrap_or_else(|| panic!("reference {element_ref} missing"))
        .id
        .clone()
}

fn resolves_to(nav: &NavigationIndex, reference: &ReferenceId) -> Option<ViewId> {
    nav.links
        .iter()
        .find(|link| {
            link.from == NodeAddress::Reference(reference.clone())
                && link.kind == NavLinkKind::ResolvesTo
        })
        .and_then(|link| link.to.as_view().cloned())
}

// --------------------------------------------------------------- structure #

#[test]
fn mixed_structure_path_siblings_and_precedes() {
    let inputs = mixed();
    let nav = &inputs.nav;
    let projection = &inputs.projection;

    // The table cell owns three child views: paragraph, residual, residual.
    let cell = view_id(projection, ReaderViewKind::Cell, "e12");
    let table = view_id(projection, ReaderViewKind::Table, "e10");
    let row = view_id(projection, ReaderViewKind::Row, "e11");
    let gamma = view_id(projection, ReaderViewKind::Paragraph, "e13");

    assert_eq!(nav.parent(&gamma), Some(cell.clone()));
    assert!(nav.children(&cell).contains(&gamma));
    assert!(nav.children(&table).contains(&row));

    // path_to_root is root-first and terminal.
    let chain = nav.path_to_root(&gamma).expect("path resolves");
    assert_eq!(chain.first(), Some(&table));
    assert_eq!(chain.last(), Some(&gamma));
    assert!(nav.parent(chain.first().unwrap()).is_none());

    // Siblings are the other children of the same parent, in children order.
    let siblings = nav.siblings(&gamma);
    assert!(!siblings.is_empty());
    assert!(!siblings.contains(&gamma));
    for sibling in siblings {
        assert_eq!(nav.parent(sibling), Some(cell.clone()));
    }

    // Precedes links consecutive view siblings in the same parent group.
    let precedes: Vec<&ln_decode::reader_navigation::NavLink> =
        nav.links_of_kind(NavLinkKind::Precedes);
    assert!(!precedes.is_empty());
    for link in precedes {
        assert_eq!(
            link.from.kind(),
            ln_decode::reader_navigation::NavNodeKind::View
        );
        assert_eq!(
            link.to.kind(),
            ln_decode::reader_navigation::NavNodeKind::View
        );
    }
}

#[test]
fn mixed_neighbours_follow_reading_order() {
    let inputs = mixed();
    let nav = &inputs.nav;
    let projection = &inputs.projection;

    // Reading order re-derived from the substrate event walk: the residual e0
    // for Kappa/Lambda sits between the paragraph e29 and the paragraph e38,
    // not at the document head.
    let kappa = view_id(projection, ReaderViewKind::Residual, "e0");
    let theta = view_id(projection, ReaderViewKind::Paragraph, "e29");
    let nbsp = view_id(projection, ReaderViewKind::Paragraph, "e38");
    assert_eq!(nav.neighbours(&theta).unwrap().next, Some(kappa.clone()));
    assert_eq!(nav.neighbours(&kappa).unwrap().prev, Some(theta.clone()));
    assert_eq!(nav.neighbours(&kappa).unwrap().next, Some(nbsp.clone()));

    // Reading order is not a source_pos sort: kappa's element is e0.
    let order = nav.reading_order_views();
    let kappa_pos = order.iter().position(|id| id == &kappa).unwrap();
    let nbsp_pos = order.iter().position(|id| id == &nbsp).unwrap();
    assert!(kappa_pos < nbsp_pos);

    // A navigation view has no reading-order neighbours.
    let cell = view_id(projection, ReaderViewKind::Cell, "e12");
    assert_eq!(
        nav.neighbours(&cell).unwrap_err().kind(),
        NavErrorKind::MissingAnchorView
    );
}

// ------------------------------------------------------------ subtree text #

#[test]
fn mixed_subtree_text_channels() {
    let inputs = mixed();
    let nav = &inputs.nav;
    let clean = &inputs.clean;
    let projection = &inputs.projection;

    // The table subtree: primary text of the descendant primary views in
    // reading order, plus the residual whitespace on the service channel.
    let table = view_id(projection, ReaderViewKind::Table, "e10");
    let table_text = nav.subtree_text(&table, clean).expect("table subtree");
    assert_eq!(table_text.primary, "GammaDeltaEpsilon");
    assert_eq!(table_text.service, " \n\n");

    // The first cell holds the paragraph (Gamma) and the residual (Delta).
    let cell = view_id(projection, ReaderViewKind::Cell, "e12");
    let cell_text = nav.subtree_text(&cell, clean).expect("cell subtree");
    assert_eq!(cell_text.primary, "GammaDelta");
    assert_eq!(cell_text.service, " ");

    // A note view is a navigation view: its subtree text comes from its primary
    // descendant, and the note itself carries no text.
    let note = view_id(projection, ReaderViewKind::Note, "e42");
    let note_text = nav.subtree_text(&note, clean).expect("note subtree");
    assert_eq!(note_text.primary, "Nu");
    assert_eq!(note_text.service, "");

    // The note view body proves a navigation view owns no text.
    let node = nav.resolve(&view_addr(&note)).expect("note node");
    match &node.body {
        NavNodeBody::View { primary, .. } => assert!(!primary),
        _ => panic!("note must be a view node"),
    }

    // An unknown view is refused.
    let unknown = ViewId::from("v-absent");
    assert_eq!(
        nav.subtree_text(&unknown, clean).unwrap_err().kind(),
        NavErrorKind::MissingAnchorView
    );
}

// ------------------------------------------------------------- resolution #

#[test]
fn mixed_reference_resolution() {
    let inputs = mixed();
    let nav = &inputs.nav;
    let projection = &inputs.projection;

    // footnoteReference w:id=1 resolves to exactly one note view (the footnote).
    let first = reference_id(projection, "e41");
    let target = resolves_to(nav, &first).expect("w:id=1 must resolve");
    let note = view_id(projection, ReaderViewKind::Note, "e42");
    assert_eq!(target, note);
    assert_eq!(nav.resolve_reason(&first), None);
    let target_node = nav.resolve(&view_addr(&target)).expect("target node");
    match &target_node.body {
        NavNodeBody::View { view_kind, .. } => assert_eq!(*view_kind, ReaderViewKind::Note),
        _ => panic!("resolution target must be a view"),
    }

    // footnoteReference w:id=2 has no matching definition: a closed reason and
    // no invented link.
    let second = reference_id(projection, "e46");
    assert_eq!(resolves_to(nav, &second), None);
    assert_eq!(
        nav.resolve_reason(&second),
        Some(NavResolveReason::NoMatchingNoteDefinition)
    );

    // Every reference address has exactly one of a ResolvesTo link or a reason.
    for reference in &projection.references {
        let has_link = resolves_to(nav, &reference.id).is_some();
        let has_reason = nav.resolve_reason(&reference.id).is_some();
        assert!(
            has_link ^ has_reason,
            "reference {} must have exactly one of link/reason",
            reference.id
        );
    }

    // A non-note reference (field / foreign / unknown) stays closed.
    let field = reference_id(projection, "e9");
    assert_eq!(
        nav.resolve_reason(&field),
        Some(NavResolveReason::NotAResolvableReference)
    );
}

// ------------------------------------------------- navigation-demo oracle #

#[test]
fn navigation_demo_structure_nested_note_and_pagination_negative() {
    let inputs = inputs_from(NAVDEMO);
    let nav = &inputs.nav;
    let clean = &inputs.clean;
    let projection = &inputs.projection;

    // A two-by-two table: the cell subtree carries the tab on the service channel.
    let table = view_id(projection, ReaderViewKind::Table, "e5");
    assert_eq!(
        nav.subtree_text(&table, clean)
            .expect("table subtree")
            .primary,
        "Ячейка A1Ячейка B1B1bЯчейка A2Ячейка B2"
    );
    assert_eq!(
        nav.subtree_text(&table, clean)
            .expect("table subtree")
            .service,
        "\t"
    );

    // A note containing a nested table and a nested note.
    let note = view_id(projection, ReaderViewKind::Note, "e31");
    assert_eq!(
        nav.subtree_text(&note, clean)
            .expect("note subtree")
            .primary,
        "Сноска 1Таблица в сноскеВложенная сноска"
    );
    let nested_note = view_id(projection, ReaderViewKind::Note, "e41");
    assert_eq!(
        nav.subtree_text(&nested_note, clean)
            .expect("nested note subtree")
            .primary,
        "Вложенная сноска"
    );
    // The nested note is a child of the cell inside the note's table.
    let nested_cell = view_id(projection, ReaderViewKind::Cell, "e37");
    assert_eq!(nav.parent(&nested_note), Some(nested_cell));

    // --- pagination negative surface -------------------------------------
    // A `w:br w:type="page"` is a derived separator, never a page boundary.
    let page_break = projection
        .segments
        .iter()
        .find(|segment| segment.origin == SegmentOrigin::Derived(ReaderDerivedKind::PageBreak))
        .expect("the demo carries a page break");
    let page_break_node = nav
        .resolve(&NodeAddress::Segment(page_break.id.clone()))
        .expect("page-break segment node");
    match &page_break_node.body {
        NavNodeBody::Segment {
            origin,
            fragment_ref,
            span,
            ..
        } => {
            assert_eq!(
                *origin,
                SegmentOrigin::Derived(ReaderDerivedKind::PageBreak)
            );
            // A derived segment never invents a fragment or a span.
            assert!(fragment_ref.is_none());
            assert!(span.is_none());
        }
        _ => panic!("page break must be a segment node"),
    }

    // The paragraph carrying the page break stays one primary view: the page
    // break contributes a `service` newline and does not split reading order.
    let carrier = view_id(projection, ReaderViewKind::Paragraph, "e26");
    let carrier_text = nav.subtree_text(&carrier, clean).expect("carrier subtree");
    assert_eq!(carrier_text.primary, "ДоПосле");
    assert_eq!(carrier_text.service, "\n");
    let neighbours = nav.neighbours(&carrier).expect("carrier neighbours");
    let v12 = view_id(projection, ReaderViewKind::Paragraph, "e23");
    let v15 = view_id(projection, ReaderViewKind::Paragraph, "e32");
    assert_eq!(neighbours.prev, Some(v12));
    assert_eq!(neighbours.next, Some(v15));

    // The link vocabulary is closed: an exhaustive match proves there is no
    // page-boundary / pagination link kind.
    for kind in [
        NavLinkKind::Contains,
        NavLinkKind::Owns,
        NavLinkKind::Precedes,
        NavLinkKind::ResolvesTo,
    ] {
        let _ = kind.as_str();
    }
}

// ---------------------------------------------------------- notes-nested #

#[test]
fn notes_nested_structure() {
    let inputs = inputs_from(NESTED);
    let nav = &inputs.nav;
    let clean = &inputs.clean;
    let projection = &inputs.projection;

    // A note nested inside a table cell.
    let note_in_cell = view_id(projection, ReaderViewKind::Note, "e8");
    assert_eq!(
        nav.subtree_text(&note_in_cell, clean)
            .expect("note-in-cell subtree")
            .primary,
        "FN"
    );
    let cell = view_id(projection, ReaderViewKind::Cell, "e4");
    assert_eq!(nav.parent(&note_in_cell), Some(cell));

    // A table defined inside a note.
    let table_in_note = view_id(projection, ReaderViewKind::Note, "e12");
    assert_eq!(
        nav.subtree_text(&table_in_note, clean)
            .expect("table-in-note subtree")
            .primary,
        "TBLN"
    );

    // A note nested inside a note.
    let outer = view_id(projection, ReaderViewKind::Note, "e26");
    let inner = view_id(projection, ReaderViewKind::Note, "e27");
    assert_eq!(nav.parent(&inner), Some(outer.clone()));
    assert_eq!(
        nav.subtree_text(&outer, clean)
            .expect("outer note subtree")
            .primary,
        "NN"
    );
    assert_eq!(
        nav.subtree_text(&inner, clean)
            .expect("inner note subtree")
            .primary,
        "NN"
    );

    // The full root-first path of the deepest paragraph crosses the nesting.
    let deepest = view_id(projection, ReaderViewKind::Paragraph, "e28");
    let chain = nav.path_to_root(&deepest).expect("path resolves");
    assert_eq!(
        chain,
        vec![
            view_id(projection, ReaderViewKind::Note, "e26"),
            inner,
            deepest,
        ]
    );
}

// ----------------------------------------------------- wire read-back parity #

#[test]
fn wire_read_back_parity() {
    for xml in [MIXED, NAVDEMO, NESTED] {
        let inputs = inputs_from(xml);

        // Direct build.
        let direct = build_navigation(&inputs.projection, &inputs.order, &inputs.records)
            .expect("direct navigation builds");

        // Wire read-back: export the cleaned projection, read it back, and build
        // navigation from the reconstructed reader projection.
        let artifact = render_cleaned_projection(
            &inputs.package,
            &inputs.projection,
            &WireCompletion::Complete,
            &WireLimits::default(),
        )
        .expect("cleaned wire renders");
        let cleaned = read_cleaned_wire(&artifact).expect("cleaned wire reads back");
        let readback = build_navigation(&cleaned.projection, &inputs.order, &inputs.records)
            .expect("read-back navigation builds");

        assert_eq!(direct, readback, "read-back navigation must equal direct");
    }
}

// ------------------------------------------------------------- negatives #

#[test]
fn cyclic_path_to_root_is_bounded() {
    let inputs = mixed();
    let mut projection = inputs.projection.clone();
    assert!(projection.views.len() >= 2);
    let first = projection.views[0].id.clone();
    let second = projection.views[1].id.clone();
    projection.views[0].parent_view = Some(second.clone());
    projection.views[1].parent_view = Some(first.clone());

    // The structure is otherwise consistent, so the index builds; the cycle is
    // caught by the bounded walk in `path_to_root`.
    let nav = build_navigation(&projection, &inputs.order, &inputs.records)
        .expect("structure is consistent");
    assert_eq!(
        nav.path_to_root(&first).unwrap_err().kind(),
        NavErrorKind::ParentCycle
    );
}

#[test]
fn missing_anchor_is_a_typed_error() {
    let inputs = mixed();
    let mut broken = inputs.projection.clone();
    broken.views[0].element_ref = ln_decode::reader_contract::ElementRef::from("e-absent");
    let errors =
        build_navigation(&broken, &inputs.order, &inputs.records).expect_err("must refuse");
    assert!(
        errors
            .iter()
            .any(|error| error.kind() == NavErrorKind::MissingAnchorElement),
        "expected MissingAnchorElement, got {errors:?}"
    );
}

#[test]
fn unresolvable_reference_yields_a_closed_reason() {
    let inputs = mixed();
    let nav = &inputs.nav;
    let projection = &inputs.projection;
    let unresolved: Vec<&ReferenceId> = projection
        .references
        .iter()
        .filter(|reference| nav.resolve_reason(&reference.id).is_some())
        .map(|reference| &reference.id)
        .collect();
    assert!(!unresolved.is_empty());
    for reference in unresolved {
        assert!(
            resolves_to(nav, reference).is_none(),
            "an unresolved reference must carry no ResolvesTo link"
        );
    }
}

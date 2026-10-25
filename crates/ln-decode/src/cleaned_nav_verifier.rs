//! Independent verifier for the S03 navigation index over a read-back
//! cleaned projection.
//!
//! [`crate::cleaned_nav::build_nav_index`] derives a [`NavIndex`] from a frozen
//! projection plus a frozen package. Like the artifact seals (D634), that
//! derived index must not be trusted: a caller can hand this verifier a mutated
//! index (or a projection that disagrees with it) and every structural claim is
//! re-derived from `CleanedProjection` + `Package` with an independent walk.
//!
//! Checks performed (each maps to one closed [`NavVerifyCode`]):
//! - node set and grouped record order (`NodeSetMismatch`),
//! - source order from the package pre-order anchor position (`SourceOrderMismatch`),
//! - link endpoints, duplicate links and the `Precedes` chain
//!   (`LinkDangling` / `LinkDuplicateOrMisordered`),
//! - element anchors and source-fragment fragment/span bounds (`AnchorMissing`),
//! - the frozen "projection is never mutated" flag (`ResolvedFlagViolated`).
//!
//! Non-claims: a pass is not source authenticity, not legal completeness, not a
//! coverage claim, not a graph projection, not CST/AST/CTV and not citation
//! resolution. This module is dependency-free, logs no decoded legal text and
//! never calls [`crate::cleaned_nav::build_nav_index`]: the oracle is rebuilt
//! here so the verifier stays independent of the builder.

use std::collections::{BTreeSet, HashMap, HashSet};

use crate::cleaned_nav::{NavIndex, NavLink, NavLinkKind, NodeAddress};
use crate::cleaned_wire::CleanedProjection;
use crate::reader_projection::{
    ProjectedView, ReaderProjection, ReferenceId, SegmentId, SegmentOrigin,
};
use crate::source_package::{Package, Record};

// ------------------------------------------------------------------- codes #

/// Closed navigation verification vocabulary. A code names one concrete
/// invariant the index/projection pair violated; it never carries a legal
/// claim.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NavVerifyCode {
    /// The index node set (or grouped record order) disagrees with the
    /// projection.
    NodeSetMismatch,
    /// A link endpoint does not resolve to an indexed node.
    LinkDangling,
    /// The link set carries a duplicate, or the `Precedes` chain does not match
    /// the independently computed source order.
    LinkDuplicateOrMisordered,
    /// The index source order disagrees with the independently computed one.
    SourceOrderMismatch,
    /// An element/fragment/span anchor is absent or out of bounds.
    AnchorMissing,
    /// A projected reference carries `resolved == true`, which the reading
    /// layer must never set.
    ResolvedFlagViolated,
}

impl NavVerifyCode {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            NavVerifyCode::NodeSetMismatch => "node_set_mismatch",
            NavVerifyCode::LinkDangling => "link_dangling",
            NavVerifyCode::LinkDuplicateOrMisordered => "link_duplicate_or_misordered",
            NavVerifyCode::SourceOrderMismatch => "source_order_mismatch",
            NavVerifyCode::AnchorMissing => "anchor_missing",
            NavVerifyCode::ResolvedFlagViolated => "resolved_flag_violated",
        }
    }
}

/// One typed navigation defect. `detail` is for diagnostics only, carries ids,
/// closed codes and counters, and never interpolates decoded fragment text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NavFinding {
    /// The closed defect code.
    pub code: NavVerifyCode,
    /// Text-free detail.
    pub detail: String,
}

impl NavFinding {
    /// Builds a finding from a closed code and a text-free detail.
    pub fn new(code: NavVerifyCode, detail: impl Into<String>) -> Self {
        NavFinding {
            code,
            detail: detail.into(),
        }
    }
}

// ----------------------------------------------------------- oracle build #

/// Independently derived expectations for one projection/package pair.
struct Oracle {
    nodes: BTreeSet<NodeAddress>,
    record_order: Vec<NodeAddress>,
    source_order: Vec<NodeAddress>,
}

/// Rebuilds the expected node set, grouped record order and source order from
/// the projection plus the package pre-order element positions. This never
/// consults the index under verification.
fn build_oracle(projection: &ReaderProjection, element_pos: &HashMap<&str, usize>) -> Oracle {
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
            let position = element_pos
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
        let mut segment_ids: Vec<&str> = view.segment_refs.iter().map(|id| id.as_str()).collect();
        segment_ids.sort_by_key(|id| segment_ordinal.get(id).copied().unwrap_or(usize::MAX));
        for id in segment_ids {
            source_order.push(NodeAddress::Segment(SegmentId::new(id)));
        }
    }
    for (_, _, view) in &ordered_views {
        let mut reference_ids: Vec<&str> =
            view.reference_refs.iter().map(|id| id.as_str()).collect();
        reference_ids.sort_by_key(|id| reference_ordinal.get(id).copied().unwrap_or(usize::MAX));
        for id in reference_ids {
            source_order.push(NodeAddress::Reference(ReferenceId::new(id)));
        }
    }

    Oracle {
        nodes,
        record_order,
        source_order,
    }
}

/// Stable, text-free token for a node address, used only in diagnostics.
fn address_token(address: &NodeAddress) -> String {
    match address {
        NodeAddress::View(id) => format!("view:{}", id.as_str()),
        NodeAddress::Segment(id) => format!("segment:{}", id.as_str()),
        NodeAddress::Reference(id) => format!("reference:{}", id.as_str()),
    }
}

// ---------------------------------------------------------------- verifier #

/// Independently verifies a navigation index against the projection it claims
/// to describe and the frozen package.
///
/// Returns `Ok(())` when the index node set and grouped record order match the
/// projection, its source order matches the independently recomputed document
/// order, every link endpoint resolves and the link set is duplicate-free with
/// a `Precedes` chain equal to the source order, every element/fragment/span
/// anchor is present and in bounds, and every projected reference still carries
/// `resolved == false`.
///
/// Otherwise it returns one [`NavFinding`] per violated invariant. The verifier
/// never calls the builder and never trusts the index's own fields as proof.
pub fn verify_nav_index(
    index: &NavIndex,
    projection: &CleanedProjection,
    package: &Package,
) -> Result<(), Vec<NavFinding>> {
    let mut findings: Vec<NavFinding> = Vec::new();

    // Substrate: the package is the only authority for element positions and
    // decoded fragment values. Raw decoded text is compared but never logged.
    let mut element_ids: HashSet<&str> = HashSet::new();
    let mut element_pos: HashMap<&str, usize> = HashMap::new();
    let mut texts: HashMap<&str, &str> = HashMap::new();
    let mut position = 0usize;
    for record in package.records() {
        match record {
            Record::Element(element) => {
                element_ids.insert(element.id.as_str());
                element_pos.entry(element.id.as_str()).or_insert(position);
                position += 1;
            }
            Record::Text(text) => {
                texts.insert(text.id.as_str(), text.value.as_str());
            }
        }
    }

    let proj = &projection.projection;
    let oracle = build_oracle(proj, &element_pos);

    // (a) node set and grouped record order.
    let actual_nodes: BTreeSet<NodeAddress> = index.nodes_by_address.keys().cloned().collect();
    if actual_nodes != oracle.nodes {
        let missing = oracle.nodes.difference(&actual_nodes).count();
        let extra = actual_nodes.difference(&oracle.nodes).count();
        findings.push(NavFinding::new(
            NavVerifyCode::NodeSetMismatch,
            format!(
                "node set mismatch: index={} projection={} missing={} extra={}",
                actual_nodes.len(),
                oracle.nodes.len(),
                missing,
                extra
            ),
        ));
    }
    if index.record_order != oracle.record_order {
        findings.push(NavFinding::new(
            NavVerifyCode::NodeSetMismatch,
            format!(
                "record order mismatch: index={} projection={}",
                index.record_order.len(),
                oracle.record_order.len()
            ),
        ));
    }

    // (c) source order.
    if index.source_order != oracle.source_order {
        findings.push(NavFinding::new(
            NavVerifyCode::SourceOrderMismatch,
            format!(
                "source order mismatch: index={} projection={}",
                index.source_order.len(),
                oracle.source_order.len()
            ),
        ));
    }

    // (d) anchors: element presence, source-fragment substrate fragment and
    // validated in-bounds span.
    for view in &proj.views {
        if !element_ids.contains(view.element_ref.as_str()) {
            findings.push(NavFinding::new(
                NavVerifyCode::AnchorMissing,
                format!(
                    "view {} anchors absent element {}",
                    view.id,
                    view.element_ref.as_str()
                ),
            ));
        }
    }
    for segment in &proj.segments {
        if !element_ids.contains(segment.element_ref.as_str()) {
            findings.push(NavFinding::new(
                NavVerifyCode::AnchorMissing,
                format!(
                    "segment {} anchors absent element {}",
                    segment.id,
                    segment.element_ref.as_str()
                ),
            ));
        }
        if segment.origin != SegmentOrigin::SourceFragment {
            continue;
        }
        let Some(fragment_ref) = &segment.fragment_ref else {
            findings.push(NavFinding::new(
                NavVerifyCode::AnchorMissing,
                format!("source segment {} has no fragment reference", segment.id),
            ));
            continue;
        };
        let Some(value) = texts.get(fragment_ref.as_str()) else {
            findings.push(NavFinding::new(
                NavVerifyCode::AnchorMissing,
                format!(
                    "source segment {} fragment {} is absent from the substrate",
                    segment.id,
                    fragment_ref.as_str()
                ),
            ));
            continue;
        };
        let span_ok = match &segment.span {
            None => false,
            Some(span) => {
                span.fragment.as_str() == fragment_ref.as_str()
                    && span.start < span.end
                    && span.end <= value.len()
                    && value.is_char_boundary(span.start)
                    && value.is_char_boundary(span.end)
            }
        };
        if !span_ok {
            findings.push(NavFinding::new(
                NavVerifyCode::AnchorMissing,
                format!(
                    "source segment {} span is absent or out of bounds for fragment {}",
                    segment.id,
                    fragment_ref.as_str()
                ),
            ));
        }
    }
    for reference in &proj.references {
        if !element_ids.contains(reference.element_ref.as_str()) {
            findings.push(NavFinding::new(
                NavVerifyCode::AnchorMissing,
                format!(
                    "reference {} anchors absent element {}",
                    reference.id,
                    reference.element_ref.as_str()
                ),
            ));
        }
    }

    // (b) link endpoints, duplicate links and the Precedes chain.
    for link in &index.links {
        if !index.nodes_by_address.contains_key(&link.from)
            || !index.nodes_by_address.contains_key(&link.to)
        {
            findings.push(NavFinding::new(
                NavVerifyCode::LinkDangling,
                format!(
                    "link {} -{}-> {} has an absent endpoint",
                    address_token(&link.from),
                    link.kind.as_str(),
                    address_token(&link.to)
                ),
            ));
        }
    }
    let unique_links: BTreeSet<&NavLink> = index.links.iter().collect();
    if unique_links.len() != index.links.len() {
        findings.push(NavFinding::new(
            NavVerifyCode::LinkDuplicateOrMisordered,
            format!(
                "duplicate links: total={} unique={}",
                index.links.len(),
                unique_links.len()
            ),
        ));
    }
    let expected_precedes: BTreeSet<(NodeAddress, NodeAddress)> = oracle
        .source_order
        .windows(2)
        .map(|pair| (pair[0].clone(), pair[1].clone()))
        .collect();
    let actual_precedes: BTreeSet<(NodeAddress, NodeAddress)> = index
        .links
        .iter()
        .filter(|link| link.kind == NavLinkKind::Precedes)
        .map(|link| (link.from.clone(), link.to.clone()))
        .collect();
    if actual_precedes != expected_precedes {
        findings.push(NavFinding::new(
            NavVerifyCode::LinkDuplicateOrMisordered,
            format!(
                "precedes chain mismatch: index={} expected={}",
                actual_precedes.len(),
                expected_precedes.len()
            ),
        ));
    }

    // (e) the reading layer never mutates the projection.
    for reference in &proj.references {
        if reference.resolved {
            findings.push(NavFinding::new(
                NavVerifyCode::ResolvedFlagViolated,
                format!("reference {} carries resolved=true", reference.id),
            ));
        }
    }

    if findings.is_empty() {
        Ok(())
    } else {
        Err(findings)
    }
}

// -------------------------------------------------------------------- tests #

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cleaned_nav::{NavNodeBody, build_nav_index};
    use crate::cleaned_wire::{
        WireCompletion, WireLimits, read_cleaned_wire, render_cleaned_projection,
    };
    use crate::reader_contract::ElementRef;
    use crate::reader_projection::build_projection;
    use crate::source_package::{Limits, capture};

    const FIXTURE: &str = include_str!("../tests/fixtures/reader/mixed-wordml.xml");

    fn fixture() -> (Package, CleanedProjection, NavIndex) {
        let package =
            capture(FIXTURE.as_bytes(), &Limits::default()).expect("fixture must capture");
        let projection = build_projection(package.records()).expect("projection must build");
        let artifact = render_cleaned_projection(
            &package,
            &projection,
            &WireCompletion::Complete,
            &WireLimits::default(),
        )
        .expect("render must succeed");
        let cleaned = read_cleaned_wire(&artifact).expect("read-back must succeed");
        let index = build_nav_index(&cleaned, &package).expect("nav index must build");
        (package, cleaned, index)
    }

    fn any_code(findings: &[NavFinding], code: NavVerifyCode) -> bool {
        findings.iter().any(|finding| finding.code == code)
    }

    #[test]
    fn accepts_a_valid_index() {
        let (package, cleaned, index) = fixture();
        verify_nav_index(&index, &cleaned, &package).expect("valid index must verify");
    }

    #[test]
    fn detects_a_removed_node() {
        let (package, cleaned, mut index) = fixture();
        let removed = index
            .nodes_by_address
            .keys()
            .next()
            .cloned()
            .expect("index must hold at least one node");
        index.nodes_by_address.remove(&removed);
        let findings =
            verify_nav_index(&index, &cleaned, &package).expect_err("node removal must refuse");
        assert!(any_code(&findings, NavVerifyCode::NodeSetMismatch));
    }

    #[test]
    fn detects_a_dangling_link() {
        let (package, cleaned, mut index) = fixture();
        let from = index
            .nodes_by_address
            .keys()
            .next()
            .cloned()
            .expect("index must hold at least one node");
        index.links.push(NavLink {
            from,
            to: NodeAddress::View(crate::reader_projection::ViewId::new("v999999")),
            kind: NavLinkKind::Contains,
        });
        let findings =
            verify_nav_index(&index, &cleaned, &package).expect_err("dangling link must refuse");
        assert!(any_code(&findings, NavVerifyCode::LinkDangling));
    }

    #[test]
    fn detects_a_duplicate_link() {
        let (package, cleaned, mut index) = fixture();
        let duplicate = index.links[0].clone();
        index.links.push(duplicate);
        let findings =
            verify_nav_index(&index, &cleaned, &package).expect_err("duplicate link must refuse");
        assert!(any_code(
            &findings,
            NavVerifyCode::LinkDuplicateOrMisordered
        ));
    }

    #[test]
    fn detects_a_reordered_source_order() {
        let (package, cleaned, mut index) = fixture();
        assert!(index.source_order.len() >= 2, "fixture must carry nodes");
        index.source_order.swap(0, 1);
        let findings =
            verify_nav_index(&index, &cleaned, &package).expect_err("reorder must refuse");
        assert!(any_code(&findings, NavVerifyCode::SourceOrderMismatch));
    }

    #[test]
    fn detects_a_resolved_flag_violation() {
        let (package, mut cleaned, index) = fixture();
        let reference = cleaned
            .projection
            .references
            .first_mut()
            .expect("fixture must carry a reference");
        reference.resolved = true;
        let findings =
            verify_nav_index(&index, &cleaned, &package).expect_err("resolved flag must refuse");
        assert!(any_code(&findings, NavVerifyCode::ResolvedFlagViolated));
    }

    #[test]
    fn detects_an_extra_projection_node() {
        let (package, mut cleaned, index) = fixture();
        let mut extra = cleaned.projection.views[0].clone();
        extra.id = crate::reader_projection::ViewId::new("v999999");
        cleaned.projection.views.push(extra);
        let findings =
            verify_nav_index(&index, &cleaned, &package).expect_err("extra node must refuse");
        assert!(any_code(&findings, NavVerifyCode::NodeSetMismatch));
    }

    #[test]
    fn detects_a_missing_projection_node() {
        let (package, mut cleaned, index) = fixture();
        cleaned.projection.views.pop();
        let findings =
            verify_nav_index(&index, &cleaned, &package).expect_err("missing node must refuse");
        assert!(any_code(&findings, NavVerifyCode::NodeSetMismatch));
    }

    #[test]
    fn detects_a_missing_anchor_element() {
        let (package, mut cleaned, index) = fixture();
        cleaned.projection.views[0].element_ref = ElementRef::new("e999999");
        let findings =
            verify_nav_index(&index, &cleaned, &package).expect_err("absent anchor must refuse");
        assert!(any_code(&findings, NavVerifyCode::AnchorMissing));
    }

    #[test]
    fn diagnostics_carry_no_decoded_text() {
        let (package, cleaned, mut index) = fixture();
        let from = index
            .nodes_by_address
            .keys()
            .next()
            .cloned()
            .expect("index must hold at least one node");
        index.links.push(NavLink {
            from,
            to: NodeAddress::View(crate::reader_projection::ViewId::new("v999999")),
            kind: NavLinkKind::Contains,
        });
        let findings =
            verify_nav_index(&index, &cleaned, &package).expect_err("dangling link must refuse");
        for finding in &findings {
            for needle in ["Alpha", "Beta", "Gamma", "Epsilon", "Lambda"] {
                assert!(
                    !finding.detail.contains(needle),
                    "diagnostic leaked decoded text"
                );
            }
        }
    }

    #[test]
    fn node_bodies_stay_unmutated_after_verification() {
        let (package, cleaned, index) = fixture();
        let before = index.nodes_by_address.clone();
        verify_nav_index(&index, &cleaned, &package).expect("valid index must verify");
        assert_eq!(index.nodes_by_address, before);
        // Sanity: the fixture actually carries view nodes.
        assert!(
            index
                .nodes_by_address
                .values()
                .any(|node| matches!(node.body, NavNodeBody::View { .. }))
        );
    }
}

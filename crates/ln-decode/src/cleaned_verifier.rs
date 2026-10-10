//! Independent verifier for a cleaned-projection artifact.
//!
//! The verifier re-derives semantics from the **frozen source package** and
//! never accepts the artifact's own seals as proof. A re-sealed semantic tamper
//! therefore still passes [`crate::cleaned_wire::read_cleaned_wire`] (its seals
//! are internally consistent) but is caught here.
//!
//! The semantic layer is delegated to the frozen
//! [`crate::reader_verifier::verify_projection`]; this module adds the checks
//! that surface does not make: the parent source/seal pins, an independent text
//! channel over the inline decoded text, and the footer counts.
//!
//! Non-claims: a pass here is not source authenticity, not legal completeness,
//! and not a coverage claim. It only states that the artifact is internally
//! consistent and agrees with the supplied package. This module is
//! dependency-free and logs no decoded legal text.

use std::collections::HashMap;

use crate::cleaned_wire::{CleanedCounts, CleanedProjection, SegmentText, read_cleaned_wire};
use crate::reader_projection::SegmentOrigin;
use crate::source_package::{Package, Record, TextRecord};

// ------------------------------------------------------------------- codes #

/// Closed verifier finding vocabulary. A finding names one concrete invariant
/// the artifact violated; it never carries a legal claim.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CleanedVerifyCode {
    /// The artifact could not be read back at all.
    ArtifactUnreadable,
    /// The artifact's source pin disagrees with the package manifest.
    ParentSourcePinMismatch,
    /// The artifact's parent seal pin disagrees with the package footer.
    ParentSealPinMismatch,
    /// The reconstructed projection violates a frozen reader invariant.
    ProjectionInvalid,
    /// The inline text channel disagrees with the substrate or its own counts.
    TextChannelMismatch,
    /// A substrate text record is covered by no source inline text, or by more
    /// than one.
    TextChannelMembershipMismatch,
    /// The footer counts disagree with the reconstructed model.
    CountsMismatch,
}

impl CleanedVerifyCode {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            CleanedVerifyCode::ArtifactUnreadable => "artifact_unreadable",
            CleanedVerifyCode::ParentSourcePinMismatch => "parent_source_pin_mismatch",
            CleanedVerifyCode::ParentSealPinMismatch => "parent_seal_pin_mismatch",
            CleanedVerifyCode::ProjectionInvalid => "projection_invalid",
            CleanedVerifyCode::TextChannelMismatch => "text_channel_mismatch",
            CleanedVerifyCode::TextChannelMembershipMismatch => "text_channel_membership_mismatch",
            CleanedVerifyCode::CountsMismatch => "counts_mismatch",
        }
    }
}

/// One typed artifact defect. `detail` is for diagnostics only, carries no
/// decoded legal text, and is never parsed.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CleanedFinding {
    pub code: CleanedVerifyCode,
    pub detail: String,
}

impl CleanedFinding {
    /// Builds a finding from a code and a human-readable detail.
    pub fn new(code: CleanedVerifyCode, detail: impl Into<String>) -> Self {
        CleanedFinding {
            code,
            detail: detail.into(),
        }
    }
}

// ---------------------------------------------------------------- verifier #

/// Independently verifies a cleaned-projection artifact against the frozen
/// package it claims to project.
///
/// Returns `Ok(())` when the artifact reads back, pins the package source and
/// seals, reconstructs a projection `verify_projection` accepts, carries a text
/// channel that agrees with the substrate, and declares counts consistent with
/// the reconstructed model. Otherwise it returns one typed [`CleanedFinding`]
/// per violated invariant.
///
/// A reading failure is a single `ArtifactUnreadable` finding whose detail is
/// the closed [`crate::cleaned_wire::WireErrorKind`] token; no further checks run on an unreadable
/// artifact.
pub fn verify_cleaned_wire(artifact: &str, package: &Package) -> Result<(), Vec<CleanedFinding>> {
    let readback: CleanedProjection = match read_cleaned_wire(artifact) {
        Ok(readback) => readback,
        Err(error) => {
            return Err(vec![CleanedFinding::new(
                CleanedVerifyCode::ArtifactUnreadable,
                error.kind().as_str(),
            )]);
        }
    };

    let mut findings: Vec<CleanedFinding> = Vec::new();

    verify_source_pin(&readback, package, &mut findings);
    verify_parent_seal_pin(&readback, package, &mut findings);
    verify_projection_semantics(&readback, package, &mut findings);
    verify_text_channel(&readback, package, &mut findings);
    verify_counts(&readback, &mut findings);

    if findings.is_empty() {
        Ok(())
    } else {
        Err(findings)
    }
}

/// The artifact's `manifest.source` pin must equal the package source pin.
fn verify_source_pin(
    readback: &CleanedProjection,
    package: &Package,
    findings: &mut Vec<CleanedFinding>,
) {
    let source = &package.manifest().source;
    if readback.source.sha256 != source.sha256 || readback.source.bytes != source.bytes {
        findings.push(CleanedFinding::new(
            CleanedVerifyCode::ParentSourcePinMismatch,
            format!(
                "artifact source pin ({}, {} bytes) does not match the package source pin ({}, {} bytes)",
                readback.source.sha256, readback.source.bytes, source.sha256, source.bytes
            ),
        ));
    }
}

/// The artifact's `manifest.parent` seal pin must equal the package footer.
/// `None` pins an unsealed parent, so the comparison is over the full option.
fn verify_parent_seal_pin(
    readback: &CleanedProjection,
    package: &Package,
    findings: &mut Vec<CleanedFinding>,
) {
    let footer = package.footer();
    if readback.parent.records_seal_hash != footer.records_seal_hash
        || readback.parent.manifest_hash != footer.manifest_hash
    {
        findings.push(CleanedFinding::new(
            CleanedVerifyCode::ParentSealPinMismatch,
            "artifact parent seal pin does not match the package footer".to_string(),
        ));
    }
}

/// Delegates the semantic layer to the frozen reader verifier. It never calls
/// `build_projection` and never reads `content_hash`.
fn verify_projection_semantics(
    readback: &CleanedProjection,
    package: &Package,
    findings: &mut Vec<CleanedFinding>,
) {
    match crate::reader_verifier::verify_projection(&readback.projection, package.records()) {
        Ok(()) => {}
        Err(projection_findings) => {
            for finding in projection_findings {
                findings.push(CleanedFinding::new(
                    CleanedVerifyCode::ProjectionInvalid,
                    format!("{}: {}", finding.code.as_str(), finding.detail),
                ));
            }
        }
    }
}

/// The independent text channel: every source segment's inline decoded text
/// must equal the substrate fragment value, its declared `chars` / `text_bytes`
/// must match the inline text, and every substrate text record must be covered
/// exactly once.
fn verify_text_channel(
    readback: &CleanedProjection,
    package: &Package,
    findings: &mut Vec<CleanedFinding>,
) {
    let substrate: HashMap<&str, &TextRecord> = package
        .records()
        .iter()
        .filter_map(|record| match record {
            Record::Text(text) => Some((text.id.as_str(), text)),
            Record::Element(_) => None,
        })
        .collect();
    let inline_by_segment: HashMap<&str, &SegmentText> = readback
        .inline_texts
        .iter()
        .map(|inline| (inline.segment_id.as_str(), inline))
        .collect();

    let mut attributed: HashMap<&str, usize> = HashMap::new();
    for segment in &readback.projection.segments {
        if segment.origin != SegmentOrigin::SourceFragment {
            continue;
        }
        let Some(inline) = inline_by_segment.get(segment.id.as_str()) else {
            findings.push(CleanedFinding::new(
                CleanedVerifyCode::TextChannelMismatch,
                format!("source segment {} has no inline text entry", segment.id),
            ));
            continue;
        };
        let Some(fragment) = segment.fragment_ref.as_ref() else {
            findings.push(CleanedFinding::new(
                CleanedVerifyCode::TextChannelMismatch,
                format!("source segment {} has no fragment reference", segment.id),
            ));
            continue;
        };
        if inline.fragment_ref.as_deref() != Some(fragment.as_str()) {
            findings.push(CleanedFinding::new(
                CleanedVerifyCode::TextChannelMismatch,
                format!(
                    "source segment {} inline fragment reference disagrees",
                    segment.id
                ),
            ));
            continue;
        }
        *attributed.entry(fragment.as_str()).or_insert(0) += 1;
        let Some(record) = substrate.get(fragment.as_str()) else {
            findings.push(CleanedFinding::new(
                CleanedVerifyCode::TextChannelMismatch,
                format!(
                    "source segment {} fragment {} is absent from the substrate",
                    segment.id, fragment
                ),
            ));
            continue;
        };
        if inline.text != record.value {
            findings.push(CleanedFinding::new(
                CleanedVerifyCode::TextChannelMismatch,
                format!(
                    "source segment {} inline text differs from the substrate value",
                    segment.id
                ),
            ));
        }
        if inline.chars != inline.text.chars().count() as u64 {
            findings.push(CleanedFinding::new(
                CleanedVerifyCode::TextChannelMismatch,
                format!(
                    "source segment {} declared text_chars disagrees with the inline text",
                    segment.id
                ),
            ));
        }
        if inline.text_bytes != inline.text.len() as u64 {
            findings.push(CleanedFinding::new(
                CleanedVerifyCode::TextChannelMismatch,
                format!(
                    "source segment {} declared text_bytes disagrees with the inline text",
                    segment.id
                ),
            ));
        }
    }

    for record in package.records() {
        if let Record::Text(text) = record {
            let seen = attributed.get(text.id.as_str()).copied().unwrap_or(0);
            if seen == 0 {
                findings.push(CleanedFinding::new(
                    CleanedVerifyCode::TextChannelMembershipMismatch,
                    format!(
                        "substrate text record {} is covered by no source inline text",
                        text.id
                    ),
                ));
            } else if seen > 1 {
                findings.push(CleanedFinding::new(
                    CleanedVerifyCode::TextChannelMembershipMismatch,
                    format!(
                        "substrate text record {} is covered by {seen} source inline texts",
                        text.id
                    ),
                ));
            }
        }
    }
}

/// Recomputes the footer counts from the reconstructed model and compares them
/// to the declared footer counts. `text_chars` / `text_bytes` are summed from
/// the actual inline text, so a declared-vs-actual drift at the record level is
/// caught by the text channel while an aggregate drift is caught here.
fn verify_counts(readback: &CleanedProjection, findings: &mut Vec<CleanedFinding>) {
    let views = readback.projection.views.len() as u64;
    let segments = readback.projection.segments.len() as u64;
    let references = readback.projection.references.len() as u64;
    let source_segments = readback
        .projection
        .segments
        .iter()
        .filter(|segment| segment.origin == SegmentOrigin::SourceFragment)
        .count() as u64;
    let derived_segments = segments - source_segments;
    let text_chars: u64 = readback
        .inline_texts
        .iter()
        .map(|inline| inline.text.chars().count() as u64)
        .sum();
    let text_bytes: u64 = readback
        .inline_texts
        .iter()
        .map(|inline| inline.text.len() as u64)
        .sum();
    let records = views + segments + references;
    let recomputed = CleanedCounts {
        views,
        segments,
        references,
        source_segments,
        derived_segments,
        text_chars,
        text_bytes,
        records,
    };
    if recomputed != readback.counts {
        findings.push(CleanedFinding::new(
            CleanedVerifyCode::CountsMismatch,
            format!(
                "recomputed counts views={} segments={} references={} source_segments={} derived_segments={} text_chars={} text_bytes={} records={} disagree with the footer",
                recomputed.views,
                recomputed.segments,
                recomputed.references,
                recomputed.source_segments,
                recomputed.derived_segments,
                recomputed.text_chars,
                recomputed.text_bytes,
                recomputed.records
            ),
        ));
    }
}

// -------------------------------------------------------------------- tests #

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cleaned_wire::{
        WireCompletion, WireLimits, read_cleaned_wire, render_cleaned_projection,
    };
    use crate::reader_projection::{ReaderProjection, build_projection};
    use crate::source_package::{Limits, capture};

    const FIXTURE: &str = include_str!("../tests/fixtures/reader/mixed-wordml.xml");

    fn fixture_package() -> Package {
        capture(FIXTURE.as_bytes(), &Limits::default()).expect("fixture must capture")
    }

    fn fixture_projection(package: &Package) -> ReaderProjection {
        build_projection(package.records()).expect("projection must build")
    }

    fn render(package: &Package, projection: &ReaderProjection) -> String {
        render_cleaned_projection(
            package,
            projection,
            &WireCompletion::Complete,
            &WireLimits::default(),
        )
        .expect("complete render")
    }

    fn codes(findings: &[CleanedFinding]) -> Vec<CleanedVerifyCode> {
        findings.iter().map(|finding| finding.code).collect()
    }

    /// Replaces one ASCII letter in the first text record that has one, keeping
    /// the code-point and byte counts identical.
    fn replace_first_ascii_letter(records: &mut [Record]) -> bool {
        for record in records.iter_mut() {
            if let Record::Text(text) = record {
                let mut chars: Vec<char> = text.value.chars().collect();
                if let Some(index) = chars.iter().position(|c| c.is_ascii_alphabetic()) {
                    chars[index] = if chars[index] == 'a' { 'b' } else { 'a' };
                    text.value = chars.into_iter().collect();
                    return true;
                }
            }
        }
        false
    }

    #[test]
    fn accepts_a_round_tripped_artifact() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let artifact = render(&package, &projection);
        verify_cleaned_wire(&artifact, &package).expect("round-trip must verify");
    }

    #[test]
    fn refuses_parent_source_pin_mismatch() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let mut manifest = package.manifest().clone();
        manifest.source.sha256 = "a".repeat(64);
        manifest.source.bytes += 1;
        let other = Package::from_parts(
            manifest,
            package.records().to_vec(),
            package.footer().clone(),
        );
        let artifact = render(&other, &projection);
        assert!(
            read_cleaned_wire(&artifact).is_ok(),
            "the renderer re-seals its own footer, so read-back must stay Ok"
        );
        let findings =
            verify_cleaned_wire(&artifact, &package).expect_err("pin mismatch must refuse");
        assert!(codes(&findings).contains(&CleanedVerifyCode::ParentSourcePinMismatch));
    }

    #[test]
    fn refuses_parent_seal_pin_mismatch() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let mut footer = package.footer().clone();
        footer.records_seal_hash = None;
        footer.manifest_hash = None;
        let other = Package::from_parts(
            package.manifest().clone(),
            package.records().to_vec(),
            footer,
        );
        let artifact = render(&other, &projection);
        assert!(
            read_cleaned_wire(&artifact).is_ok(),
            "the renderer recomputes its own footer seals"
        );
        let findings =
            verify_cleaned_wire(&artifact, &package).expect_err("pin mismatch must refuse");
        assert!(codes(&findings).contains(&CleanedVerifyCode::ParentSealPinMismatch));
    }

    #[test]
    fn refuses_text_channel_mismatch() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let mut records = package.records().to_vec();
        assert!(
            replace_first_ascii_letter(&mut records),
            "fixture must carry a mutable text record"
        );
        let other = Package::from_parts(
            package.manifest().clone(),
            records,
            package.footer().clone(),
        );
        let artifact = render(&other, &projection);
        assert!(
            read_cleaned_wire(&artifact).is_ok(),
            "a re-sealed semantic tamper still reads back"
        );
        let findings =
            verify_cleaned_wire(&artifact, &package).expect_err("channel mismatch must refuse");
        assert!(codes(&findings).contains(&CleanedVerifyCode::TextChannelMismatch));
    }

    #[test]
    fn refuses_unreadable_artifact() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let artifact = render(&package, &projection);

        let mut lines: Vec<&str> = artifact.split_terminator('\n').collect();
        lines.pop();
        let truncated = format!("{}\n", lines.join("\n"));
        let findings =
            verify_cleaned_wire(&truncated, &package).expect_err("truncation must refuse");
        assert_eq!(
            codes(&findings),
            vec![CleanedVerifyCode::ArtifactUnreadable]
        );

        let with_cr = artifact.replacen('\n', "\r\n", 1);
        let findings = verify_cleaned_wire(&with_cr, &package).expect_err("CR must refuse");
        assert_eq!(
            codes(&findings),
            vec![CleanedVerifyCode::ArtifactUnreadable]
        );
    }
}

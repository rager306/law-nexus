use ln_decode::reader_projection::{SegmentOrigin, build_projection};
use ln_decode::source_package::{Limits, Record, capture};

const XML: &str = include_str!("fixtures/reader/mixed-wordml.xml");

#[test]
fn dump() {
    let package = capture(XML.as_bytes(), &Limits::default()).unwrap();
    let records = package.records().to_vec();
    let projection = build_projection(&records).unwrap();
    eprintln!("=== text records ===");
    for r in &records {
        if let Record::Text(t) = r {
            eprintln!(
                "{} owner={} slot={:?} value={:?}",
                t.id, t.owner, t.slot, t.value
            );
        }
    }
    eprintln!("=== views (order) ===");
    for (i, v) in projection.views.iter().enumerate() {
        eprintln!(
            "idx={} id={} kind={:?} elem={} parent={:?}",
            i, v.id, v.kind, v.element_ref, v.parent_view
        );
    }
    eprintln!("=== segments (global order) ===");
    for s in &projection.segments {
        let tok = match &s.origin {
            SegmentOrigin::SourceFragment => s.fragment_ref.as_ref().unwrap().as_str().to_string(),
            SegmentOrigin::Derived(k) => format!("derived:{}", k.as_str()),
        };
        eprintln!(
            "{} view={} ord={} out={}..{} srcpos={} elem={} tok={}",
            s.id, s.view, s.ordinal, s.output_start, s.output_end, s.source_pos, s.element_ref, tok
        );
    }
    eprintln!("=== per view segment_refs ===");
    for v in &projection.views {
        eprintln!(
            "{} {:?} {} -> {:?}",
            v.id, v.kind, v.element_ref, v.segment_refs
        );
    }
}

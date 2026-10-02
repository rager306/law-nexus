//! Contract tests for the bounded source-preserving JSONL package
//! (`ln_decode::source_package`): XML bytes -> decoded-source JSONL -> verify.
//!
//! The expected decoded text and topology below are handwritten against the XML
//! specification and ElementTree `text`/`tail` semantics. They are NOT produced
//! by the module under test (no oracle collapse). This slice carries a decoded
//! source model, not an XML lexical byte roundtrip, and keeps no XML byte
//! coordinates.

use std::cell::Cell;
use std::io::{self, Read, Write};
use std::rc::Rc;

use ln_decode::source_package::{
    capture, read_package, verify_against_source, write_package, ElementRecord, ErrorKind, Footer,
    Limits, Package, Record, TextRecord, TextSlot,
};

fn limits() -> Limits {
    Limits::default()
}

fn elements(pkg: &Package) -> Vec<&ElementRecord> {
    pkg.records()
        .iter()
        .filter_map(|r| match r {
            Record::Element(e) => Some(e),
            Record::Text(_) => None,
        })
        .collect()
}

fn texts(pkg: &Package) -> Vec<&TextRecord> {
    pkg.records()
        .iter()
        .filter_map(|r| match r {
            Record::Element(_) => None,
            Record::Text(t) => Some(t),
        })
        .collect()
}

fn element(pkg: &Package, id: &str) -> ElementRecord {
    elements(pkg)
        .into_iter()
        .find(|e| e.id == id)
        .expect("element id must exist")
        .clone()
}

fn jsonl(pkg: &Package) -> String {
    pkg.to_jsonl().expect("serialize")
}

fn lines(text: &str) -> Vec<String> {
    text.lines().map(str::to_owned).collect()
}

fn join(lines: &[String]) -> String {
    let mut out = lines.join("\n");
    out.push('\n');
    out
}

/// Remove the `"key":<value>` member (and a following comma, if any) from a
/// canonical JSON object line. Supports `null` and JSON-string values.
fn drop_key(line: &str, key: &str) -> String {
    let needle = format!("\"{key}\":");
    let start = line.find(&needle).expect("key present");
    let vstart = start + needle.len();
    let vend = if line[vstart..].starts_with("null") {
        vstart + 4
    } else {
        assert_eq!(&line[vstart..vstart + 1], "\"", "string value expected");
        let mut i = vstart + 1;
        let bytes = line.as_bytes();
        while bytes[i] != b'"' {
            i += 1;
        }
        i + 1
    };
    let mut end = vend;
    if line[end..].starts_with(',') {
        end += 1;
        return format!("{}{}", &line[..start], &line[end..]);
    }
    // Last member: consume the preceding comma instead.
    assert_eq!(line.as_bytes()[start - 1], b',', "expected preceding comma");
    format!("{}{}", &line[..start - 1], &line[vend..])
}

fn reseal(mut pkg: Package) -> Package {
    pkg.resign().expect("resign");
    pkg
}

// ------------------------------------------------------------------ capture #

#[test]
fn mixed_content_text_and_tail_ownership() {
    let pkg = capture(b"<a>one<b>two</b>three<c/>four</a>", &limits()).expect("capture");
    let els = elements(&pkg);
    assert_eq!(els.len(), 3);
    let txt = texts(&pkg);
    assert_eq!(txt.len(), 4);
    assert_eq!((txt[0].owner.as_str(), txt[0].slot), ("e0", TextSlot::Text));
    assert_eq!(txt[0].value, "one");
    assert_eq!((txt[1].owner.as_str(), txt[1].slot), ("e1", TextSlot::Text));
    assert_eq!(txt[1].value, "two");
    assert_eq!((txt[2].owner.as_str(), txt[2].slot), ("e1", TextSlot::Tail));
    assert_eq!(txt[2].value, "three");
    assert_eq!((txt[3].owner.as_str(), txt[3].slot), ("e2", TextSlot::Tail));
    assert_eq!(txt[3].value, "four");

    let root = element(&pkg, "e0");
    assert_eq!(root.parent, None);
    assert_eq!(root.child_index, None);
    assert_eq!(root.depth, 0);
    assert_eq!(root.text_ref.as_deref(), Some("t0"));

    let b = element(&pkg, "e1");
    assert_eq!(b.parent.as_deref(), Some("e0"));
    assert_eq!(b.child_index, Some(0));
    assert_eq!(b.depth, 1);
    assert_eq!(b.text_ref.as_deref(), Some("t1"));
    assert_eq!(b.tail_ref.as_deref(), Some("t2"));

    let c = element(&pkg, "e2");
    assert_eq!(c.parent.as_deref(), Some("e0"));
    assert_eq!(c.child_index, Some(1));
    assert_eq!(c.text_ref, None);
    assert_eq!(c.tail_ref.as_deref(), Some("t3"));
}

#[test]
fn namespace_clark_and_default_namespace_attrs_not_applied() {
    let xml = br#"<r xmlns="urn:d" xmlns:p="urn:p" id="x" p:k="v"><p:c q="w"/></r>"#;
    let pkg = capture(xml, &limits()).expect("capture");
    let root = element(&pkg, "e0");
    assert_eq!(root.clark_tag, "{urn:d}r");
    // Unprefixed attributes do NOT inherit the default namespace.
    assert_eq!(root.attrs.get("id").map(String::as_str), Some("x"));
    assert_eq!(root.attrs.get("{urn:p}k").map(String::as_str), Some("v"));
    assert_eq!(
        root.namespace_declarations.get("").map(String::as_str),
        Some("urn:d")
    );
    assert_eq!(
        root.namespace_declarations.get("p").map(String::as_str),
        Some("urn:p")
    );
    let child = element(&pkg, "e1");
    assert_eq!(child.clark_tag, "{urn:p}c");
    assert_eq!(child.attrs.get("q").map(String::as_str), Some("w"));
}

#[test]
fn xml_space_declared_and_inherited() {
    let preserve = capture(br#"<r xml:space="preserve"><c/></r>"#, &limits()).expect("capture");
    assert_eq!(element(&preserve, "e0").xml_space_declared, Some(true));
    assert!(element(&preserve, "e0").xml_space_effective);
    assert_eq!(element(&preserve, "e1").xml_space_declared, None);
    assert!(element(&preserve, "e1").xml_space_effective);

    let default = capture(br#"<r xml:space="default"><c/></r>"#, &limits()).expect("capture");
    assert_eq!(element(&default, "e0").xml_space_declared, Some(false));
    assert!(!element(&default, "e1").xml_space_effective);
}

#[test]
fn nbsp_whitespace_cdata_entities_merge_and_preserve() {
    let pkg = capture(b"<a>  x&#160;y  <![CDATA[cd]]>z</a>", &limits()).expect("capture");
    let txt = texts(&pkg);
    assert_eq!(
        txt.len(),
        1,
        "adjacent same-owner slot text must merge once"
    );
    assert_eq!(txt[0].value, "  x\u{a0}y  cdz");
    assert_eq!(txt[0].chars, txt[0].value.chars().count() as u64);
    assert_eq!(txt[0].bytes, txt[0].value.len() as u64);
}

#[test]
fn unknown_foreign_same_local_names_preserved() {
    let xml = br#"<r xmlns:a="urn:a" xmlns:b="urn:b"><a:x/><b:x/></r>"#;
    let pkg = capture(xml, &limits()).expect("capture");
    let tags: Vec<&str> = elements(&pkg)
        .iter()
        .map(|e| e.clark_tag.as_str())
        .collect();
    assert!(tags.contains(&"{urn:a}x"));
    assert!(tags.contains(&"{urn:b}x"));
}

#[test]
fn self_closing_element_has_no_text_fragment() {
    let pkg = capture(b"<r><e/></r>", &limits()).expect("capture");
    assert_eq!(texts(&pkg).len(), 0);
    assert_eq!(elements(&pkg).len(), 2);
    assert_eq!(element(&pkg, "e1").text_ref, None);
    assert_eq!(element(&pkg, "e1").tail_ref, None);
}

#[test]
fn legal_shaped_rev_notes_tables_elements_preserved() {
    let xml = br#"<r><rev>1</rev><notes><note>n</note></notes><tables><table><row/></table></tables></r>"#;
    let pkg = capture(xml, &limits()).expect("capture");
    let tags: Vec<&str> = elements(&pkg)
        .iter()
        .map(|e| e.clark_tag.as_str())
        .collect();
    for expected in ["r", "rev", "notes", "note", "tables", "table", "row"] {
        assert!(tags.contains(&expected), "missing element {expected}");
    }
}

// -------------------------------------------------------- reject at capture #

#[test]
fn dtd_is_rejected() {
    let err = capture(b"<!DOCTYPE r [<!ENTITY x \"v\">]><r>&x;</r>", &limits())
        .expect_err("DTD must be rejected");
    assert_eq!(err.kind(), ErrorKind::DtdForbidden);
}

#[test]
fn unsupported_encoding_is_rejected() {
    let xml = b"<?xml version=\"1.0\" encoding=\"windows-1251\"?><r/>";
    let err = capture(xml, &limits()).expect_err("non-UTF-8 declaration must be rejected");
    assert_eq!(err.kind(), ErrorKind::UnsupportedEncoding);
}

#[test]
fn duplicate_attribute_is_rejected() {
    let err = capture(b"<r a=\"1\" a=\"2\"/>", &limits()).expect_err("duplicate attrs rejected");
    assert_eq!(err.kind(), ErrorKind::DuplicateAttribute);
}

#[test]
fn unbound_prefix_is_rejected() {
    let err = capture(b"<r><p:x/></r>", &limits()).expect_err("unbound prefix rejected");
    assert_eq!(err.kind(), ErrorKind::UnboundPrefix);
}

#[test]
fn malformed_close_is_rejected() {
    let err = capture(b"<r></nope>", &limits()).expect_err("mismatched close rejected");
    assert_eq!(err.kind(), ErrorKind::MalformedXml);
}

#[test]
fn multiple_roots_are_rejected() {
    let err = capture(b"<a/><b/>", &limits()).expect_err("multiple roots rejected");
    assert_eq!(err.kind(), ErrorKind::MultipleRoots);
}

#[test]
fn node_cap_is_rejected() {
    let mut lim = limits();
    lim.max_nodes = 1;
    let err = capture(b"<r><a/><b/></r>", &lim).expect_err("node cap rejected");
    assert_eq!(err.kind(), ErrorKind::NodeCapExceeded);
}

#[test]
fn depth_cap_is_rejected() {
    let mut lim = limits();
    lim.max_depth = 1;
    let err = capture(b"<r><a><b/></a></r>", &lim).expect_err("depth cap rejected");
    assert_eq!(err.kind(), ErrorKind::DepthExceeded);
}

#[test]
fn input_byte_cap_is_rejected() {
    let mut lim = limits();
    lim.max_input_bytes = 3;
    let err = capture(b"<r></r>", &lim).expect_err("input cap rejected");
    assert_eq!(err.kind(), ErrorKind::InputTooLarge);
}

// ------------------------------------------------------------- read/write #

#[test]
fn write_then_read_roundtrips() {
    let pkg = capture(b"<a>one<b/>two</a>", &limits()).expect("capture");
    let mut buf: Vec<u8> = Vec::new();
    write_package(&pkg, &mut buf, &limits()).expect("write");
    let reread = read_package(&buf[..], &limits()).expect("read");
    assert_eq!(jsonl(&pkg), jsonl(&reread));
}

#[test]
fn write_validates_before_writing() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let mut records = pkg.records().to_vec();
    records[0] = match &records[0] {
        Record::Element(e) => {
            let mut e = e.clone();
            e.parent = Some("e99".to_string());
            Record::Element(e)
        }
        other => other.clone(),
    };
    let invalid = reseal(Package::from_parts(
        pkg.manifest().clone(),
        records,
        pkg.footer().clone(),
    ));
    let mut buf: Vec<u8> = Vec::new();
    let err = write_package(&invalid, &mut buf, &limits()).expect_err("must refuse");
    assert_eq!(err.kind(), ErrorKind::ParentDangling);
    assert!(buf.is_empty(), "invalid package must write nothing");
}

struct FailingWriter {
    budget: usize,
}

impl Write for FailingWriter {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        if self.budget == 0 {
            return Err(io::Error::other("synthetic midstream failure"));
        }
        let take = buf.len().min(self.budget);
        self.budget -= take;
        Ok(take)
    }

    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

#[test]
fn midstream_write_error_returns_error() {
    let pkg = capture(
        b"<a>some text that is long enough to need two writes</a>",
        &limits(),
    )
    .expect("capture");
    let mut writer = FailingWriter { budget: 8 };
    let err = write_package(&pkg, &mut writer, &limits()).expect_err("must surface io error");
    assert_eq!(err.kind(), ErrorKind::Io);
}

#[test]
fn read_rejects_missing_trailing_lf() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let text = jsonl(&pkg);
    let trimmed = text.trim_end_matches('\n').to_string();
    let err = read_package(trimmed.as_bytes(), &limits()).expect_err("missing LF rejected");
    assert_eq!(err.kind(), ErrorKind::MissingTrailingLf);
}

#[test]
fn read_rejects_carriage_return() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let text = jsonl(&pkg).replace('\n', "\r\n");
    let err = read_package(text.as_bytes(), &limits()).expect_err("CR rejected");
    assert_eq!(err.kind(), ErrorKind::CarriageReturnForbidden);
}

#[test]
fn read_rejects_duplicate_json_key() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let mut ls = lines(&jsonl(&pkg));
    ls[0] = ls[0].replacen('{', "{\"kind\":\"source_package_manifest\",", 1);
    let err = read_package(join(&ls).as_bytes(), &limits()).expect_err("dup key rejected");
    assert_eq!(err.kind(), ErrorKind::DuplicateJsonKey);
}

#[test]
fn read_rejects_unknown_field() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let mut ls = lines(&jsonl(&pkg));
    ls[0] = ls[0].replacen(
        "\"non_authoritative\":true",
        "\"non_authoritative\":true,\"bogus\":1",
        1,
    );
    let err = read_package(join(&ls).as_bytes(), &limits()).expect_err("unknown field rejected");
    assert_eq!(err.kind(), ErrorKind::TypeMismatch);
}

#[test]
fn read_rejects_bool_integer() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let mut ls = lines(&jsonl(&pkg));
    ls[1] = ls[1].replacen("\"depth\":0", "\"depth\":false", 1);
    let err = read_package(join(&ls).as_bytes(), &limits()).expect_err("bool for u64 rejected");
    assert_eq!(err.kind(), ErrorKind::TypeMismatch);
}

#[test]
fn read_rejects_unknown_version() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let mut ls = lines(&jsonl(&pkg));
    ls[0] = ls[0].replacen("\"version\":1", "\"version\":2", 1);
    let err = read_package(join(&ls).as_bytes(), &limits()).expect_err("unknown version rejected");
    assert_eq!(err.kind(), ErrorKind::VersionUnsupported);
}

#[test]
fn read_rejects_unknown_capture_status() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let mut ls = lines(&jsonl(&pkg));
    let last = ls.len() - 1;
    ls[last] = ls[last].replacen("\"complete\"", "\"weird\"", 1);
    let err = read_package(join(&ls).as_bytes(), &limits()).expect_err("unknown status rejected");
    assert_eq!(err.kind(), ErrorKind::TypeMismatch);
}

#[test]
fn read_rejects_truncated_footer() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let mut ls = lines(&jsonl(&pkg));
    ls.pop();
    let err = read_package(join(&ls).as_bytes(), &limits()).expect_err("missing footer rejected");
    assert_eq!(err.kind(), ErrorKind::MissingFooter);
}

#[test]
fn read_rejects_trailing_record_after_footer() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let mut ls = lines(&jsonl(&pkg));
    let record = ls[1].clone();
    ls.push(record);
    let err = read_package(join(&ls).as_bytes(), &limits()).expect_err("trailing record rejected");
    assert_eq!(err.kind(), ErrorKind::MisorderedFooter);
}

// -------------------------------------------------------------- verify #

#[test]
fn verify_rejects_duplicate_element_id() {
    let pkg = capture(b"<a><b/></a>", &limits()).expect("capture");
    let mut records = pkg.records().to_vec();
    let dup = match &records[0] {
        Record::Element(e) => e.clone(),
        Record::Text(_) => unreachable!(),
    };
    records[1] = Record::Element(dup);
    let tampered = reseal(Package::from_parts(
        pkg.manifest().clone(),
        records,
        pkg.footer().clone(),
    ));
    let err = tampered
        .verify()
        .expect_err("duplicate id must be rejected");
    assert_eq!(err.kind(), ErrorKind::DuplicateRecordId);
}

#[test]
fn verify_rejects_dangling_parent() {
    let pkg = capture(b"<a><b/></a>", &limits()).expect("capture");
    let mut records = pkg.records().to_vec();
    records[1] = match &records[1] {
        Record::Element(e) => {
            let mut e = e.clone();
            e.parent = Some("e42".to_string());
            Record::Element(e)
        }
        other => other.clone(),
    };
    let tampered = reseal(Package::from_parts(
        pkg.manifest().clone(),
        records,
        pkg.footer().clone(),
    ));
    let err = tampered.verify().expect_err("dangling parent rejected");
    assert_eq!(err.kind(), ErrorKind::ParentDangling);
}

#[test]
fn verify_rejects_wrong_counts() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let mut footer: Footer = pkg.footer().clone();
    footer.counts.elements += 1;
    let tampered = reseal(Package::from_parts(
        pkg.manifest().clone(),
        pkg.records().to_vec(),
        footer,
    ));
    let err = tampered.verify().expect_err("count mismatch rejected");
    assert_eq!(err.kind(), ErrorKind::CountMismatch);
}

#[test]
fn verify_rejects_misplaced_tail() {
    let pkg = capture(b"<a>one<b/>two<c/></a>", &limits()).expect("capture");
    let mut records = pkg.records().to_vec();
    for record in records.iter_mut() {
        if let Record::Text(t) = record {
            if t.slot == TextSlot::Tail {
                t.owner = "e2".to_string();
            }
        }
    }
    let tampered = reseal(Package::from_parts(
        pkg.manifest().clone(),
        records,
        pkg.footer().clone(),
    ));
    let err = tampered.verify().expect_err("tail placement rejected");
    assert_eq!(err.kind(), ErrorKind::TextOrderMismatch);
}

#[test]
fn verify_accepts_untampered_and_rejects_resigned_tamper() {
    let pkg = capture(b"<a>hello<b>world</b></a>", &limits()).expect("capture");
    pkg.verify().expect("clean package verifies");

    let mut records = pkg.records().to_vec();
    if let Record::Element(e) = &mut records[0] {
        e.depth = 7;
    }
    let tampered = reseal(Package::from_parts(
        pkg.manifest().clone(),
        records,
        pkg.footer().clone(),
    ));
    // Re-sealing repairs the hashes; the structural topology check must still
    // reject the tampered depth.
    let err = tampered.verify().expect_err("resigned tamper rejected");
    assert_eq!(err.kind(), ErrorKind::DepthMismatch);
}

// -------------------------------------------------- verify_against_source #

#[test]
fn verify_against_source_matches_clean_and_detects_tamper() {
    let xml = b"<a>one<b>two</b></a>";
    let pkg = capture(xml, &limits()).expect("capture");
    let clean = verify_against_source(&pkg, xml, &limits()).expect("compare");
    assert!(clean.source_sha256_matches);
    assert!(clean.structurally_equal);

    let mut records = pkg.records().to_vec();
    let text_pos = records
        .iter()
        .position(|record| matches!(record, Record::Text(_)))
        .expect("fixture has decoded text");
    if let Record::Text(t) = &mut records[text_pos] {
        t.value = "changed".to_string();
        t.owner = "e99".to_string();
    }
    let tampered = reseal(Package::from_parts(
        pkg.manifest().clone(),
        records,
        pkg.footer().clone(),
    ));
    let comparison = verify_against_source(&tampered, xml, &limits()).expect("compare tampered");
    assert!(comparison.source_sha256_matches, "source hash is unchanged");
    assert!(
        !comparison.structurally_equal,
        "recapture must differ from tampered package"
    );
}

// ------------------------------------------------------------- no leakage #

#[test]
fn error_detail_does_not_contain_source_text() {
    let xml = b"<!DOCTYPE r [<!ENTITY leak \"TOP_SECRET_LEGAL_TEXT\">]><r>&leak;</r>";
    let err = capture(xml, &limits()).expect_err("rejected");
    assert!(
        !err.detail().contains("TOP_SECRET_LEGAL_TEXT"),
        "error detail must not carry source text"
    );
    assert!(
        !err.to_string().contains("TOP_SECRET_LEGAL_TEXT"),
        "error display must not carry source text"
    );
}

#[test]
fn package_is_lf_terminated_and_three_part() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let text = jsonl(&pkg);
    assert!(text.ends_with('\n'));
    assert!(!text.contains('\r'));
    let ls = lines(&text);
    assert!(ls[0].contains("source_package_manifest"));
    assert!(ls.last().expect("footer").contains("source_package_footer"));
}

// ------------------------------------------------ hostile-review regressions #

/// A linear parent chain of `n` elements, `e_i.depth == i`. Built iteratively so
/// the test itself never recurses.
fn element_chain(n: usize) -> Vec<Record> {
    (0..n)
        .map(|i| {
            Record::Element(ElementRecord {
                kind: "element".to_string(),
                schema: "law-nexus/source-package-element/v1".to_string(),
                id: format!("e{i}"),
                parent: if i == 0 {
                    None
                } else {
                    Some(format!("e{}", i - 1))
                },
                child_index: if i == 0 { None } else { Some(0) },
                depth: i as u64,
                clark_tag: format!("n{i}"),
                attrs: Default::default(),
                namespace_declarations: Default::default(),
                xml_space_declared: None,
                xml_space_effective: false,
                text_ref: None,
                tail_ref: None,
            })
        })
        .collect()
}

#[test]
fn deep_chain_default_cap_rejects_without_abort() {
    let base = capture(b"<a/>", &limits()).expect("capture");
    let records = element_chain(20_000);
    let pkg = Package::from_parts(base.manifest().clone(), records, base.footer().clone());
    // Caps are enforced before any traversal; the default depth cap rejects and
    // the iterative verifier must not overflow the stack.
    let err = pkg.verify().expect_err("depth cap must reject");
    assert_eq!(err.kind(), ErrorKind::LimitExceeded);
}

#[test]
fn deep_chain_raised_cap_verifies_iteratively() {
    let base = capture(b"<a/>", &limits()).expect("capture");
    let n = 20_000usize;
    let records = element_chain(n);
    let mut manifest = base.manifest().clone();
    manifest.limits.max_depth = 25_000;
    let mut footer = base.footer().clone();
    footer.counts.elements = n as u64;
    footer.counts.records = n as u64;
    let mut pkg = Package::from_parts(manifest, records, footer);
    pkg.resign().expect("resign");
    pkg.verify()
        .expect("deep chain within the raised cap must verify iteratively");
}

#[test]
fn deep_capture_and_verify_are_iterative() {
    let depth = 20_000usize;
    let mut xml = String::with_capacity(depth * 8);
    for _ in 0..depth {
        xml.push_str("<n>");
    }
    for _ in 0..depth {
        xml.push_str("</n>");
    }
    let mut lim = limits();
    lim.max_depth = 25_000;
    let pkg = capture(xml.as_bytes(), &lim).expect("deep capture must be iterative");
    assert_eq!(elements(&pkg).len(), depth);
    pkg.verify().expect("deep verify must be iterative");
}

#[test]
fn read_rejects_caller_node_cap() {
    let pkg = capture(b"<a><b/></a>", &limits()).expect("capture");
    let mut bytes: Vec<u8> = Vec::new();
    write_package(&pkg, &mut bytes, &limits()).expect("write");
    let mut caller = limits();
    caller.max_nodes = 1;
    let err = read_package(&bytes[..], &caller).expect_err("caller node cap must reject");
    assert_eq!(err.kind(), ErrorKind::NodeCapExceeded);
}

#[test]
fn read_rejects_caller_attrs_cap() {
    let pkg = capture(b"<a x=\"1\"><b/></a>", &limits()).expect("capture");
    let mut bytes: Vec<u8> = Vec::new();
    write_package(&pkg, &mut bytes, &limits()).expect("write");
    let mut caller = limits();
    caller.max_attrs_per_element = 0;
    let err = read_package(&bytes[..], &caller).expect_err("caller attrs cap must reject");
    assert_eq!(err.kind(), ErrorKind::AttributeCountExceeded);
}

#[test]
fn verify_rejects_attrs_over_manifest_cap() {
    let base = capture(b"<r/>", &limits()).expect("capture");
    let mut records = base.records().to_vec();
    if let Record::Element(element) = &mut records[0] {
        for i in 0..2_000 {
            element.attrs.insert(format!("a{i}"), "v".to_string());
        }
    }
    let mut pkg = Package::from_parts(base.manifest().clone(), records, base.footer().clone());
    pkg.resign().expect("resign");
    let err = pkg.verify().expect_err("attrs cap must reject");
    assert_eq!(err.kind(), ErrorKind::LimitExceeded);
}

#[test]
fn read_fails_fast_on_non_manifest_first_line() {
    struct CountingBuf {
        data: Vec<u8>,
        pos: Rc<Cell<usize>>,
        cap: usize,
    }
    impl Read for CountingBuf {
        fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
            let pos = self.pos.get();
            let end = self.cap.min(self.data.len());
            if pos >= end {
                return Ok(0);
            }
            let take = (end - pos).min(buf.len());
            buf[..take].copy_from_slice(&self.data[pos..pos + take]);
            self.pos.set(pos + take);
            Ok(take)
        }
    }
    impl io::BufRead for CountingBuf {
        fn fill_buf(&mut self) -> io::Result<&[u8]> {
            let pos = self.pos.get();
            let end = self.cap.min(self.data.len());
            if pos >= end {
                Ok(&self.data[pos..pos])
            } else {
                Ok(&self.data[pos..end])
            }
        }
        fn consume(&mut self, amount: usize) {
            self.pos.set(self.pos.get() + amount);
        }
    }

    let mut data = Vec::new();
    for _ in 0..50_000 {
        data.extend_from_slice(b"0\n");
    }
    let pos = Rc::new(Cell::new(0usize));
    let reader = CountingBuf {
        data,
        pos: pos.clone(),
        cap: 8,
    };
    let err = read_package(reader, &limits()).expect_err("first line must be a manifest");
    assert_eq!(err.kind(), ErrorKind::MisorderedManifest);
    assert!(
        pos.get() <= 4,
        "read consumed {} bytes; it must stop after the first line and never materialize the stream",
        pos.get()
    );
}

#[test]
fn error_detail_does_not_leak_value() {
    let err =
        capture(b"<r xml:space=\"SECRET_LEAK_VALUE\"/>", &limits()).expect_err("invalid xml:space");
    assert_eq!(err.kind(), ErrorKind::InvalidXmlSpace);
    assert!(!err.detail().contains("SECRET_LEAK_VALUE"));
    assert!(!err.to_string().contains("SECRET_LEAK_VALUE"));

    let err = capture(
        b"<?xml version=\"1.0\" encoding=\"SECRET_ENC_1251\"?><r/>",
        &limits(),
    )
    .expect_err("unsupported encoding");
    assert_eq!(err.kind(), ErrorKind::UnsupportedEncoding);
    assert!(!err.detail().contains("SECRET_ENC_1251"));

    let err = capture(b"<r><SECRETPREFIX:x/></r>", &limits()).expect_err("unbound prefix");
    assert_eq!(err.kind(), ErrorKind::UnboundPrefix);
    assert!(!err.detail().contains("SECRETPREFIX"));
}

#[test]
fn xml_eol_normalization() {
    let crlf = capture(b"<r>a\r\nb</r>", &limits()).expect("capture");
    assert_eq!(texts(&crlf)[0].value, "a\nb");
    let cr = capture(b"<r>a\rb</r>", &limits()).expect("capture");
    assert_eq!(texts(&cr)[0].value, "a\nb");
    // The source digest stays over the original, un-normalized bytes.
    assert_eq!(crlf.manifest().source.bytes, 11);
}

#[test]
fn xml_attribute_whitespace_normalization() {
    let pkg = capture(b"<r a=\"x\ty\" b=\"x\ny\"/>", &limits()).expect("capture");
    let root = element(&pkg, "e0");
    assert_eq!(root.attrs.get("a").map(String::as_str), Some("x y"));
    assert_eq!(root.attrs.get("b").map(String::as_str), Some("x y"));
    // A character reference for whitespace is preserved, not collapsed.
    let pkg = capture(b"<r a=\"x&#9;y\"/>", &limits()).expect("capture");
    assert_eq!(
        element(&pkg, "e0").attrs.get("a").map(String::as_str),
        Some("x\ty")
    );
}

#[test]
fn invalid_xml_char_is_rejected() {
    let err = capture(b"<r>&#1;X</r>", &limits()).expect_err("control char ref rejected");
    assert_eq!(err.kind(), ErrorKind::InvalidXmlChar);
    let err = capture(b"<r a=\"&#1;\"/>", &limits()).expect_err("attr control char ref rejected");
    assert_eq!(err.kind(), ErrorKind::InvalidXmlChar);
}

#[test]
fn xml_decl_position_duplicate_and_version() {
    assert_eq!(
        capture(b"<r><?xml version=\"1.0\"?></r>", &limits())
            .unwrap_err()
            .kind(),
        ErrorKind::MalformedXml
    );
    assert_eq!(
        capture(b"<?xml version=\"2.0\"?><r/>", &limits())
            .unwrap_err()
            .kind(),
        ErrorKind::VersionUnsupported
    );
    assert_eq!(
        capture(b"<?xml version=\"1.1\"?><r/>", &limits())
            .unwrap_err()
            .kind(),
        ErrorKind::VersionUnsupported
    );
    assert_eq!(
        capture(b"<?xml?><r/>", &limits()).unwrap_err().kind(),
        ErrorKind::MalformedXml
    );
    assert_eq!(
        capture(b"<?xml version=\"1.0\" version=\"1.0\"?><r/>", &limits())
            .unwrap_err()
            .kind(),
        ErrorKind::MalformedXml
    );
}

#[test]
fn namespace_declaration_reference_is_rejected() {
    let err = capture(b"<r xmlns:p=\"urn:a&amp;b\"><p:x/></r>", &limits())
        .expect_err("entity in namespace declaration rejected");
    assert_eq!(err.kind(), ErrorKind::MalformedXml);
}

#[test]
fn capture_rejects_unexportable_line() {
    let mut lim = limits();
    lim.max_line_bytes = 8_192;
    let mut xml: Vec<u8> = Vec::new();
    xml.extend_from_slice(b"<r>");
    xml.resize(xml.len() + 5_000, b'\n');
    xml.extend_from_slice(b"</r>");
    let err = capture(&xml, &lim).expect_err("escaped text exceeds the line cap");
    assert_eq!(err.kind(), ErrorKind::LineTooLong);
}

#[test]
fn verify_against_source_ignores_execution_limits() {
    let xml = b"<a>one<b>two</b></a>";
    let pkg = capture(xml, &limits()).expect("capture");
    let mut other = limits();
    other.max_line_bytes = 4_096;
    other.max_package_bytes = 1_048_576;
    let comparison = verify_against_source(&pkg, xml, &other).expect("compare");
    assert!(comparison.source_sha256_matches);
    assert!(
        comparison.structurally_equal,
        "execution limits must not change structural equality"
    );
}

// ------------------------------------------------ XML name / attribute hardening #

#[test]
fn rejects_non_name_xml_names() {
    for xml in [
        &b"<1/>"[..],
        b"<r><1/></r>",
        b"<r 1a=\"x\"/>",
        b"<a/b/>",
        b"<p:a:b/>",
        b"<:/>",
        b"<r a:b:c=\"x\"/>",
    ] {
        let err = capture(xml, &limits()).expect_err("invalid XML name must be rejected");
        assert_eq!(
            err.kind(),
            ErrorKind::MalformedXml,
            "xml={:?}",
            String::from_utf8_lossy(xml)
        );
    }
}

#[test]
fn accepts_valid_unicode_and_namespace_names() {
    // CJK NameStartChar (U+4E2D in [#x3001-#xD7FF]).
    let pkg = capture("<\u{4e2d}/>".as_bytes(), &limits()).expect("CJK name");
    assert_eq!(element(&pkg, "e0").clark_tag, "\u{4e2d}");
    // Astral NameStartChar (U+1F600 in [#x10000-#xEFFFF]).
    let pkg = capture("<\u{1F600}/>".as_bytes(), &limits()).expect("astral name");
    assert_eq!(element(&pkg, "e0").clark_tag, "\u{1F600}");
    // Combining mark (U+0301) is a NameChar but not a NameStartChar.
    let pkg = capture("<a\u{0301}/>".as_bytes(), &limits()).expect("combining mark in name");
    assert_eq!(element(&pkg, "e0").clark_tag, "a\u{0301}");
    // Underscore start plus a digit NameChar.
    let pkg = capture(b"<_x1/>", &limits()).expect("underscore + digit name");
    assert_eq!(element(&pkg, "e0").clark_tag, "_x1");
    // A single colon with a bound prefix; `xmlns:p` declaration name validates.
    let pkg = capture(b"<r xmlns:p=\"urn:p\"><p:x a=\"v\"/></r>", &limits())
        .expect("bound prefixed QName");
    assert_eq!(element(&pkg, "e1").clark_tag, "{urn:p}x");
}

#[test]
fn attribute_value_literal_lt_rejected_but_escaped_allowed() {
    let err = capture(b"<r a=\"<b>\"/>", &limits()).expect_err("literal < in attr rejected");
    assert_eq!(err.kind(), ErrorKind::MalformedXml);
    let pkg = capture(b"<r a=\"&lt;b&gt;\"/>", &limits()).expect("escaped < allowed");
    assert_eq!(
        element(&pkg, "e0").attrs.get("a").map(String::as_str),
        Some("<b>")
    );
    let err = capture(b"<r xmlns:p=\"<urn>\"><p:x/></r>", &limits())
        .expect_err("literal < in namespace declaration rejected");
    assert_eq!(err.kind(), ErrorKind::MalformedXml);
}

#[test]
fn read_rejects_every_absent_nullable_key() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let base = jsonl(&pkg);

    // Element nullable members: null for this fixture except `text_ref`.
    for key in [
        "parent",
        "child_index",
        "xml_space_declared",
        "text_ref",
        "tail_ref",
    ] {
        let mut ls = lines(&base);
        ls[1] = drop_key(&ls[1], key);
        let err = read_package(join(&ls).as_bytes(), &limits())
            .expect_err("absent nullable element key must be rejected");
        assert_eq!(
            err.kind(),
            ErrorKind::TypeMismatch,
            "absent element key {key}"
        );
    }

    // Footer nullable integrity hashes.
    for key in ["records_seal_hash", "manifest_hash"] {
        let mut ls = lines(&base);
        let last = ls.len() - 1;
        ls[last] = drop_key(&ls[last], key);
        let err = read_package(join(&ls).as_bytes(), &limits())
            .expect_err("absent nullable footer key must be rejected");
        assert_eq!(
            err.kind(),
            ErrorKind::TypeMismatch,
            "absent footer key {key}"
        );
    }

    // Explicit null stays accepted: the canonical package round-trips.
    read_package(base.as_bytes(), &limits()).expect("canonical package with null members accepted");
}

#[test]
fn to_jsonl_validates_before_emitting() {
    let pkg = capture(b"<a>x</a>", &limits()).expect("capture");
    let mut records = pkg.records().to_vec();
    if let Record::Element(e) = &mut records[0] {
        e.parent = Some("e42".to_string());
    }
    let bad = Package::from_parts(pkg.manifest().clone(), records, pkg.footer().clone());
    let err = bad
        .to_jsonl()
        .expect_err("unverified parts must not serialize");
    assert_eq!(err.kind(), ErrorKind::ParentDangling);
}

#[test]
fn comment_double_hyphen_rejected() {
    let err = capture(b"<r><!-- a -- b --></r>", &limits())
        .expect_err("-- inside comment must be rejected");
    assert_eq!(err.kind(), ErrorKind::MalformedXml);
    capture(b"<r><!-- ok --></r>", &limits()).expect("valid comment accepted");
}

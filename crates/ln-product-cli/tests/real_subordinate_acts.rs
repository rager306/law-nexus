//! Subordinate-act punkt smoke on the real Garant corpus (M171 S03 T02).
//!
//! Skip-capable: CI without the corpus stays green — each corpus test
//! returns after an `eprintln!("SKIP: ...")` when the tracked files are
//! absent. Bounded: two real Постановления Правительства (PP) files plus an
//! inline departmental-order fixture; fixture-minted CCs are NOT registry
//! identity and the effect day is a synthetic document-date ordinal — no
//! YAML path bindings and no edition-day registry (which is federal_law-only,
//! `load_edition_day_for_path` parses only law_* paths).
//!
//! The slice goal: пункты приказов и ПП получают CC и резолвятся тела
//! (points of orders and government resolutions get CCs and their bodies
//! resolve via text-CTV).

use ln_decode::article_body::{collect_article_texts, ArticleText};
use ln_decode::domain::{
    ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
};
use ln_decode::structural_profile::{GroupProfile, StructuralProfile};
use ln_decode::{
    adapters::garant_odt::GarantOdtBlockDecoder,
    domain::{DecodeRequest, FamilyFormat, PayloadRef},
    ports::BlockDecoderPort,
};
use ln_kb_ontology::domain::{
    build_text_log_from_articles, resolve_ctv, CtvResolution, HierarchyBinding, HierarchyMap,
};
use ln_temporal::calendar::legal_act_effect_day_to_ordinal;
use ln_temporal::domain::ComponentConceptId;

fn garant_dir() -> std::path::PathBuf {
    std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("law-source/garant")
}

fn decode_odt(bytes: &[u8]) -> Result<Vec<ParsedBlock>, ln_decode::domain::BlockDecodeError> {
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:m171-s03-t02").unwrap(),
        FamilyFormat::parse("family:garant-odt").unwrap(),
        bytes,
    );
    GarantOdtBlockDecoder.decode_blocks(&request)
}

fn group(id: &str) -> GroupProfile {
    let profile = StructuralProfile::embedded().expect("embedded kb-ontology.yaml");
    profile
        .group(id)
        .unwrap_or_else(|| panic!("{id} group"))
        .clone()
}

/// Fixture CC minting (documented non-claim: NOT registry identity — the
/// hierarchy registry holds only ФЗ bindings). Flat `cc:pp-<act>:punkt-<n>`;
/// duplicate numbers across sections collide on the flat key and surface as
/// resolve_ctv Conflicts (fail-closed, never silent merge).
fn fixture_punkt_map(units: &[ArticleText], act: &str) -> (HierarchyMap, usize) {
    let mut map = HierarchyMap::empty();
    let mut cc_punkts = 0usize;
    for unit in units {
        let Ok(cc) = ComponentConceptId::parse(&format!("cc:{act}:punkt-{}", unit.number())) else {
            continue;
        };
        let Ok(binding) = HierarchyBinding::try_new(None, "punkt", unit.number(), cc) else {
            continue;
        };
        if map.register(binding).is_ok() {
            cc_punkts += 1;
        }
    }
    (map, cc_punkts)
}

/// Single-snapshot text-CTV: build the log at `day` and count unique CCs
/// resolved / conflicted (fail-closed: duplicate same-day texts -> Conflict).
fn resolve_count(
    units: &[ArticleText],
    map: &HierarchyMap,
    day: i64,
    provenance: &str,
) -> (usize, usize) {
    let log = build_text_log_from_articles(
        map,
        units
            .iter()
            .map(|u| ("punkt", u.number(), u.title(), u.text() as &str)),
        day,
        provenance,
    );
    let mut seen = std::collections::HashSet::new();
    let mut resolved = 0usize;
    let mut conflict = 0usize;
    for event in log.events() {
        if !seen.insert(event.component().as_str()) {
            continue;
        }
        match resolve_ctv(&log, event.component(), day) {
            CtvResolution::Resolved { .. } => resolved += 1,
            CtvResolution::Conflict { .. } => conflict += 1,
            _ => {}
        }
    }
    (resolved, conflict)
}

// ─── PP_60: primary rich smoke ─────────────────────────────────────────────

#[test]
fn pp_60_punkt_units_receive_cc_and_resolve_bodies() {
    let path = garant_dir().join("PP_60_27-01-2022.odt");
    if !path.exists() {
        eprintln!("SKIP: Garant corpus not available");
        return;
    }
    let bytes = std::fs::read(&path).expect("read PP_60");
    let blocks = decode_odt(&bytes).expect("PP_60 must decode");
    let profile = group("government_resolution");
    let units = collect_article_texts(&profile, &blocks);
    eprintln!("PP_60 punkt units: {}", units.len());
    assert!(
        units.len() >= 3,
        "PP_60 must yield punkt units, got {}",
        units.len()
    );

    // Punkt 1 is "1. Утвердить прилагаемые:"; its body lists the appended
    // regulations (Положение/Правила names) — the marker line stays in the
    // title, the body carries the collected prose.
    let p1 = units.iter().find(|u| u.number() == "1").expect("punkt 1");
    assert_eq!(p1.title(), Some("Утвердить прилагаемые:"));
    assert!(
        p1.text().contains("Положение"),
        "punkt-1 body must list the appended regulations; got: {}",
        &p1.text()[..p1.text().len().min(200)]
    );
    assert!(
        p1.text().chars().count() > 500,
        "punkt-1 body must be substantial"
    );

    // Synthetic effect day from the document date (27-01-2022). NOT the
    // edition-day registry — PP files have no registry entry.
    let day = legal_act_effect_day_to_ordinal("2022-01-27").expect("day");
    let (map, cc_punkts) = fixture_punkt_map(&units, "pp-60");
    assert!(cc_punkts > 0, "punkt units must be minted to CCs");
    let (resolved, conflict) = resolve_count(&units, &map, day, "fixture:subordinate:pp-60");
    eprintln!("PP_60 cc_punkts={cc_punkts} resolved={resolved} conflict={conflict}");
    assert!(
        resolved > 0,
        "punkt units must resolve text-CTV, got resolved={resolved}"
    );
}

// ─── Bounded corpus breadth: every tracked PP decodes to punkt units ───────

#[test]
fn pp_corpus_bounded_breadth_all_files_yield_punkt_units() {
    let dir = garant_dir();
    if !dir.exists() {
        eprintln!("SKIP: Garant corpus not available");
        return;
    }
    let mut files: Vec<std::path::PathBuf> = std::fs::read_dir(&dir)
        .expect("read garant dir")
        .filter_map(|entry| entry.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension().is_some_and(|ext| ext == "odt")
                && p.file_name()
                    .and_then(|n| n.to_str())
                    .is_some_and(|n| n.starts_with("Постановление") || n.starts_with("PP_"))
        })
        .collect();
    files.sort();
    assert!(
        !files.is_empty(),
        "tracked PP corpus must contain at least one ODT"
    );
    eprintln!("PP corpus sample: {} files", files.len());
    let mut total_units = 0usize;
    let mut with_units = 0usize;
    let mut zero_units: Vec<String> = Vec::new();
    let mut decode_failed: Vec<String> = Vec::new();
    for path in &files {
        let name = path.file_name().unwrap().to_string_lossy().into_owned();
        let bytes = std::fs::read(path).expect("read PP file");
        let Ok(blocks) = decode_odt(&bytes) else {
            // Pre-existing Garant ODT adapter limitation: files with embedded
            // images (`<draw:image>` inside content.xml) fail decode with
            // MalformedInput. Tracked N 1875 is one such file — the decode
            // boundary is outside T02's scope, so it is documented, not
            // asserted as a T02 regression.
            eprintln!("{name}: DECODE FAILED (embedded-image ODT limitation)");
            decode_failed.push(name);
            continue;
        };
        let units = collect_article_texts(&group("government_resolution"), &blocks);
        eprintln!("{name}: punkt units={}", units.len());
        total_units += units.len();
        if units.is_empty() {
            zero_units.push(name);
        } else {
            with_units += 1;
        }
    }
    assert!(
        total_units >= 10,
        "bounded sample must yield a meaningful total"
    );
    assert!(with_units >= 1, "the sample must prove group applicability");
    assert!(
        decode_failed.len() <= 1,
        "at most the known embedded-image file may fail decode; got {decode_failed:?}"
    );
    // Documented honest zero: "О внесении изменений" amendment PPs are
    // lettered (а/б) without numbered "N." points — the profile does not
    // invent an implied parent (fail-closed, no invented structure).
    if let Some(path) = files.iter().find(|p| p.to_string_lossy().contains("2368")) {
        let bytes = std::fs::read(path).expect("read amendment PP");
        let blocks = decode_odt(&bytes).expect("amendment PP must decode");
        let units = collect_article_texts(&group("government_resolution"), &blocks);
        assert_eq!(
            units.len(),
            0,
            "amendment PP (lettered items, no numbered points) must stay 0 units"
        );
    }
}

// ─── departmental_order: inline fixture (no real приказ in the corpus) ─────

fn block(style: ParagraphStyle, text: &str) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse("fixture:m171-s03-t02-order").unwrap(),
            SourceSpan::try_new(10, 900).unwrap(),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .expect("block")
}

#[test]
fn order_punkt_units_resolve_via_inline_fixture() {
    // departmental_order unit=punkt uses the bracket style ("1)") — matches
    // the decode Punkt marker directly. The corpus has no приказ ODT, so the
    // smoke uses an inline fixture (test-side, same as article_body_contract).
    let blocks = vec![
        block(
            ParagraphStyle::BodyText,
            "1) Утвердить прилагаемые правила.",
        ),
        block(ParagraphStyle::BodyText, "Правила действуют с 1 марта."),
        block(ParagraphStyle::BodyText, "2) Установить, что:"),
        block(ParagraphStyle::BodyText, "а) положение применяется;"),
        block(ParagraphStyle::BodyText, "б) контроль возлагается."),
    ];
    let units = collect_article_texts(&group("departmental_order"), &blocks);
    assert_eq!(units.len(), 2, "order fixture must yield two punkt units");
    let p1 = &units[0];
    assert_eq!(p1.number(), "1");
    assert!(p1.text().contains("Правила действуют"), "{}", p1.text());
    let p2 = &units[1];
    assert!(p2.text().contains("положение применяется"), "{}", p2.text());
    assert!(p2.text().contains("контроль возлагается"), "{}", p2.text());

    let day = legal_act_effect_day_to_ordinal("2030-01-01").expect("fixture day");
    let (map, cc_punkts) = fixture_punkt_map(&units, "order-fixture");
    assert_eq!(cc_punkts, 2);
    let (resolved, conflict) =
        resolve_count(&units, &map, day, "fixture:subordinate:order-fixture");
    eprintln!("order fixture resolved={resolved} conflict={conflict}");
    assert_eq!(resolved, 2, "both order punkt units must resolve");
}

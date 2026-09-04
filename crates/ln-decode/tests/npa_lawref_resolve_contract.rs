//! Contract tests for the LawRef resolution layer (M199 S03 T01/T02/T03).
//!
//! T01 shipped the resolved SURFACE over frozen capture (D350): the
//! `lawref_resolve` module (never fields on `LawRef`), the
//! `npa_lawref_resolution` YAML table (resolution as data, KBO-R025
//! idiom), and the fail-closed `CanonicalAnchor`. T02 lifts resolution
//! to behavior: the chain reverse (ELI 5.4.1: `ч. 1 ст. 42` ->
//! `art_42/par_1`), the per-src context stack, anaphora binding with
//! `art_ctx`/`sec_ctx` as the honest missing-frame tokens, the `doc`
//! sink (never a minted `doc_*`), and the quoted-enum `sub_а` append.
//! T03 adds the range half: the expanded endpoint pair (left-scan head,
//! stack fallback, art/ctx prefix, the false hyphen-split range, the
//! compound comma list) and the canonical dedup dump round-trip
//! (`m199-s03-resolution-demo.json` - a projection, never a second
//! canon). Amendment/date windows stay out of scope (R070).
//!
//! Inline fixtures and tracked src/YAML reads only; the corpus
//! (`consru_export`) is never opened. No `#[path]` include of
//! `npa_lawref_support` (D335).

use std::fs;
use std::path::{Path, PathBuf};

use ln_decode::lawref_resolve::{resolve_lawrefs, CanonicalAnchor, ResolutionTable};
use ln_decode::prefix_catalog::EMBEDDED_ONTOLOGY_YAML;

/// The exact embedded `marker_to_eid` canon line (kept in sync with
/// `prd/architecture/kb-ontology.yaml`).
const MARKER_TO_EID_LINE: &str =
    "    marker_to_eid: {st: art, stst: art, ch: par, p: pnt, pp: pnt, podp: sub, abz: aln, gl: chp, razd: sec}\n";

/// (a) Green: the embedded table parses with the closed canon.
fn embedded_resolution() -> ResolutionTable {
    ResolutionTable::embedded()
        .expect("embedded kb-ontology.yaml must carry a valid npa_lawref_resolution table")
}

#[test]
fn embedded_yaml_carries_the_resolution_heading_and_canon() {
    assert!(
        EMBEDDED_ONTOLOGY_YAML.contains("npa_lawref_resolution:"),
        "the npa_lawref_resolution heading must exist in the tracked ontology"
    );
    let resolution = embedded_resolution();

    let mut markers: Vec<&str> = resolution
        .marker_to_eid
        .iter()
        .map(|(marker, _)| marker.as_str())
        .collect();
    let mut want = vec!["st", "stst", "ch", "p", "pp", "podp", "abz", "gl", "razd"];
    markers.sort_unstable();
    want.sort_unstable();
    assert_eq!(
        markers, want,
        "marker_to_eid carries exactly the nine closed marker ids"
    );

    assert_eq!(resolution.range_policy, "expanded_pair");
    assert_eq!(resolution.eid_start_at, "art");
    assert_eq!(resolution.sort_key, ["start", "end", "path"]);

    let tail = |needle: &str| {
        resolution
            .inflected_tail_to_marker
            .iter()
            .find(|(tail, _)| tail.as_str() == needle)
            .map(|(_, marker)| marker.as_str())
    };
    assert_eq!(tail("статьи"), Some("st"));
    assert_eq!(tail("частями"), Some("ch"));
    assert_eq!(tail("подпункта"), Some("pp"));

    let target = |needle: &str| {
        resolution
            .anaphora_target_to_level
            .iter()
            .find(|(target, _)| target.as_str() == needle)
            .map(|(_, level)| level.as_str())
    };
    assert_eq!(target("статье"), Some("st"));
    assert_eq!(
        target("Кодекса"),
        Some("doc"),
        "doc is the non-eId sink value"
    );
}

// ---------------------------------------------------------------------------
// (b) Hostile YAML: fail closed, error names the key/heading, never panics.
// ---------------------------------------------------------------------------

fn parse_resolution_mutated(
    mutate: impl FnOnce(&str) -> String,
) -> Result<ResolutionTable, String> {
    ResolutionTable::parse_yaml(&mutate(EMBEDDED_ONTOLOGY_YAML))
}

#[test]
fn hostile_extra_key_fails_closed() {
    let error = parse_resolution_mutated(|yaml| {
        yaml.replacen(
            "  npa_lawref_resolution:\n",
            "  npa_lawref_resolution:\n    future_hint: invented-keys-fail-closed\n",
            1,
        )
    })
    .expect_err("an invented key must fail closed");
    assert!(
        error.contains("unknown key 'future_hint'"),
        "expected the closed-key rejection to name the key, got: {error}"
    );
}

#[test]
fn hostile_missing_marker_to_eid_fails_closed() {
    let error = parse_resolution_mutated(|yaml| yaml.replace(MARKER_TO_EID_LINE, ""))
        .expect_err("a missing marker_to_eid must fail closed");
    assert!(
        error.contains("marker_to_eid") && error.contains("missing"),
        "expected the missing-key rejection to name the key, got: {error}"
    );
}

#[test]
fn hostile_unknown_marker_id_fails_closed() {
    let error = parse_resolution_mutated(|yaml| {
        yaml.replacen(
            "marker_to_eid: {st: art,",
            "marker_to_eid: {st: art, zz: par,",
            1,
        )
    })
    .expect_err("a marker id outside npa_abbrev_lexicon must fail closed");
    assert!(
        error.contains("id 'zz' is outside npa_abbrev_lexicon"),
        "got: {error}"
    );
}

#[test]
fn hostile_doc_is_never_an_eid_unit_in_marker_to_eid() {
    let error = parse_resolution_mutated(|yaml| yaml.replacen("gl: chp", "gl: doc", 1))
        .expect_err("'doc' is a non-eId sink, never an eId unit");
    assert!(error.contains("unknown eId unit 'doc'"), "got: {error}");
}

#[test]
fn hostile_duplicate_inline_map_key_fails_closed() {
    let error = parse_resolution_mutated(|yaml| {
        yaml.replacen(
            "marker_to_eid: {st: art,",
            "marker_to_eid: {st: art, st: par,",
            1,
        )
    })
    .expect_err("a duplicate inline-map key must fail closed");
    assert!(error.contains("duplicate key 'st'"), "got: {error}");
}

#[test]
fn hostile_unknown_range_policy_fails_closed() {
    let error = parse_resolution_mutated(|yaml| {
        yaml.replace("range_policy: expanded_pair", "range_policy: nested_pair")
    })
    .expect_err("an unknown range policy must fail closed");
    assert!(
        error.contains("range_policy") && error.contains("nested_pair"),
        "got: {error}"
    );
}

#[test]
fn hostile_unknown_eid_start_at_fails_closed() {
    let error =
        parse_resolution_mutated(|yaml| yaml.replace("eid_start_at: art", "eid_start_at: par"))
            .expect_err("eid_start_at other than art must fail closed");
    assert!(error.contains("eid_start_at"), "got: {error}");
}

#[test]
fn hostile_sort_key_drift_fails_closed() {
    let error = parse_resolution_mutated(|yaml| {
        yaml.replace(
            "sort_key: [start, end, path]",
            "sort_key: [path, start, end]",
        )
    })
    .expect_err("sort_key drift must fail closed");
    assert!(error.contains("sort_key"), "got: {error}");
}

#[test]
fn hostile_latin_inflected_tail_fails_closed() {
    let error = parse_resolution_mutated(|yaml| {
        yaml.replacen(
            "inflected_tail_to_marker: {статьи: st,",
            "inflected_tail_to_marker: {статьи: st, articles: st,",
            1,
        )
    })
    .expect_err("a non-Cyrillic inflected tail must fail closed");
    assert!(
        error.contains("inflected_tail_to_marker") && error.contains("articles"),
        "got: {error}"
    );
}

#[test]
fn hostile_anaphora_level_neither_marker_nor_doc_fails_closed() {
    let error = parse_resolution_mutated(|yaml| {
        yaml.replacen(
            "anaphora_target_to_level: {статьи: st,",
            "anaphora_target_to_level: {статьи: st9,",
            1,
        )
    })
    .expect_err("an anaphora level that is neither a marker id nor doc must fail closed");
    assert!(
        error.contains("anaphora_target_to_level") && error.contains("st9"),
        "got: {error}"
    );
}

#[test]
fn hostile_missing_heading_fails_closed() {
    let error =
        ResolutionTable::parse_yaml("vocabulary:\n  npa_abbrev_lexicon:\n    st: \"ст.\"\n")
            .expect_err("a missing npa_lawref_resolution heading must fail closed");
    assert!(
        error.contains("npa_lawref_resolution:") && error.contains("missing"),
        "the error must name the heading, got: {error}"
    );
}

#[test]
fn hostile_broken_tables_return_err_without_panicking() {
    for broken in [
        "",
        "npa_lawref_resolution:\n",
        "npa_lawref_resolution:\n  oops\n",
        "npa_lawref_resolution:\n  sort_key: []\n",
    ] {
        let error = ResolutionTable::parse_yaml(broken)
            .expect_err("broken resolution tables must fail closed");
        assert!(
            error.contains("npa_lawref_resolution") || error.contains("sort_key"),
            "the error must name the heading or key, got: {error}"
        );
    }
}

// ---------------------------------------------------------------------------
// (c) CanonicalAnchor: closed segment grammar, fail-closed constructor.
// ---------------------------------------------------------------------------

#[test]
fn canonical_anchor_accepts_pinned_segment_forms() {
    // `sub_а` carries the Cyrillic letter а (U+0430), the quoted-enum form.
    for path in ["art_42/par_1", "art_26.2", "art_ctx", "sub_\u{0430}"] {
        CanonicalAnchor::try_new(path)
            .unwrap_or_else(|err| panic!("'{path}' must construct: {err}"));
    }
    assert_eq!(
        CanonicalAnchor::try_new("art_42/par_1").expect("ok").path,
        "art_42/par_1",
        "only the canonical path is stored"
    );
}

#[test]
fn canonical_anchor_rejects_hostile_paths_naming_the_rule() {
    let cases: [(&str, &str); 5] = [
        ("", "empty"),
        ("/art_1", "leading"),
        ("doc_1", "unknown eId unit 'doc'"),
        ("art_", "empty label"),
        ("ART_1", "unknown eId unit 'ART'"),
    ];
    for (path, needle) in cases {
        let error =
            CanonicalAnchor::try_new(path).expect_err(&format!("'{path}' must fail closed"));
        assert!(
            error.contains(needle),
            "'{path}': expected '{needle}' in the error, got: {error}"
        );
    }
}

// ---------------------------------------------------------------------------
// (d) Placement pins: resolution lives in the new module; capture pins hold.
// ---------------------------------------------------------------------------

#[test]
fn resolution_lives_in_lawref_resolve_and_capture_pins_hold() {
    let manifest_dir = Path::new(env!("CARGO_MANIFEST_DIR"));

    let resolve_src = fs::read_to_string(manifest_dir.join("src/lawref_resolve.rs"))
        .expect("read src/lawref_resolve.rs");
    assert!(
        resolve_src.contains("pub struct CanonicalAnchor"),
        "CanonicalAnchor must exist in src/lawref_resolve.rs"
    );
    assert!(
        resolve_src.contains("pub fn resolve_lawrefs"),
        "resolve_lawrefs must exist in src/lawref_resolve.rs"
    );
    assert!(
        !resolve_src.contains("todo!"),
        "the library path must never be an unimplemented stub"
    );
    assert!(
        !resolve_src.contains("println!") && !resolve_src.contains("eprintln!"),
        "the stub must not log (the library path never prints)"
    );

    let lib_src = fs::read_to_string(manifest_dir.join("src/lib.rs")).expect("read src/lib.rs");
    assert!(
        lib_src.contains("pub mod lawref_resolve;"),
        "lawref_resolve must be a public ln-decode module"
    );

    // Do not invert the S02 capture pins: identity and anchor names stay
    // out of the capture module.
    let lawref_src =
        fs::read_to_string(manifest_dir.join("src/lawref.rs")).expect("read src/lawref.rs");
    for forbidden in ["eId", "canonical_anchor", "resolve_anaphora"] {
        assert!(
            !lawref_src.contains(forbidden),
            "src/lawref.rs must not name '{forbidden}' (capture, not resolution)"
        );
    }
}

// ---------------------------------------------------------------------------
// (e) Freeze pins: no parsing deps, no LawRef TokenKind.
// ---------------------------------------------------------------------------

#[test]
fn freeze_no_parsing_deps_and_no_lawref_tokenkind() {
    let manifest_dir = Path::new(env!("CARGO_MANIFEST_DIR"));
    let cargo_toml = fs::read_to_string(manifest_dir.join("Cargo.toml"))
        .expect("read crates/ln-decode/Cargo.toml");
    for dependency in ["serde", "clap", "walkdir"] {
        assert!(
            !cargo_toml.contains(dependency),
            "ln-decode must not gain a '{dependency}' dependency (hand-rolled readers, D328 idiom)"
        );
    }
    let lexer_src =
        fs::read_to_string(manifest_dir.join("src/lexer.rs")).expect("read src/lexer.rs");
    assert!(
        !lexer_src.contains("TokenKind::LawRef"),
        "the closed nine-kind lexer set must not gain TokenKind::LawRef"
    );
}

// ---------------------------------------------------------------------------
// (f) Behavior: empty src and the hostile initial stay empty (the resolver
// only mints what capture proves; a hostile initial captures nothing).
// ---------------------------------------------------------------------------

#[test]
fn resolve_returns_empty_for_empty_and_hostile_input() {
    assert!(
        resolve_lawrefs("").is_empty(),
        "empty source: stub-ok empty resolution"
    );
    assert!(
        resolve_lawrefs("Ч.").is_empty(),
        "hostile capitalized initial: stub-ok empty resolution"
    );
}

// ---------------------------------------------------------------------------
// First proof - green in T02: the abbrev-hier-chain reverse maps
// `[ch, st] + [1, 42]` to the outer-first `art_42/par_1` (ELI 5.4.1).
// ---------------------------------------------------------------------------

#[test]
fn first_proof_chain_reverse_and_hostile_initial() {
    let refs = resolve_lawrefs("ч. 1 ст. 42");
    assert_eq!(
        refs.len(),
        1,
        "the chained capture resolves into exactly one ResolvedLawRef"
    );
    assert_eq!(refs[0].capture.pattern_id, "abbrev-hier-chain");
    assert_eq!(refs[0].capture.slots.marker_chain, ["ch", "st"]);
    assert_eq!(refs[0].capture.slots.hier_nums, ["1", "42"]);
    let anchor = refs[0]
        .anchor
        .as_ref()
        .expect("the first proof must mint the canonical anchor");
    assert_eq!(anchor.path, "art_42/par_1", "ELI 5.4.1 reverse order");

    // C2 fold: the uppercase initial `Ч.` is not an abbrev, so no capture
    // headed at byte 0 may ever mint an anchor.
    for resolved in resolve_lawrefs("Ч. 1.1 ст. 33") {
        assert_ne!(
            resolved.capture.span.start(),
            0,
            "the hostile initial must never head an anchor"
        );
    }
}

// ---------------------------------------------------------------------------
// T02 pins: chain emission, fullword tails, live frag-173, anaphora
// bind/ctx, the doc sink, the quoted-enum append, out-of-scope
// pass-through. Inline synthetics are first-class (sample poverty is why)
// plus one tracked live fixture read.
// ---------------------------------------------------------------------------

/// Tracked fragment fixture directory.
fn fixture_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa-lawref")
}

#[test]
fn chain_reverse_mints_dotted_relative_and_drops_above_art() {
    // Dotted numbers stay dotted: `26.2` is one label, never split.
    let refs = resolve_lawrefs("ст. 26.2");
    assert_eq!(refs.len(), 1);
    assert_eq!(
        refs[0]
            .anchor
            .as_ref()
            .expect("an st chain must mint its art anchor")
            .path,
        "art_26.2"
    );
    assert_eq!(refs[0].dedup_key.as_deref(), Some("art_26.2"));
    assert!(refs[0].members.is_empty(), "range pairs belong to T03");

    // A numbered chain that never named an article stays relative and
    // invents no `art_ctx` (negative pin).
    let refs = resolve_lawrefs("п. 2.1");
    assert_eq!(refs.len(), 1);
    assert_eq!(
        refs[0]
            .anchor
            .as_ref()
            .expect("a p chain must mint its relative pnt anchor")
            .path,
        "pnt_2.1"
    );

    // Above-art units drop from the minted path (eid_start_at: art) while
    // their frames still feed the context stack.
    let refs = resolve_lawrefs("разд. 2");
    assert_eq!(refs.len(), 1);
    assert!(
        refs[0].anchor.is_none() && refs[0].dedup_key.is_none(),
        "a sec-only chain mints no canonical anchor"
    );
}

#[test]
fn fullword_inflected_tail_maps_through_the_table() {
    // The head word is left-scanned out of the capture span (never stored):
    // `статьи` -> st -> art.
    let refs = resolve_lawrefs("статьи 19.5");
    assert_eq!(refs.len(), 1);
    assert_eq!(
        refs[0]
            .anchor
            .as_ref()
            .expect("a mapped fullword tail must mint its anchor")
            .path,
        "art_19.5"
    );

    // Unknown tails fail closed: `закона` is a doc-level head with no
    // inflected-tail row, so the numbered fullword stays unresolved.
    let refs = resolve_lawrefs("закона 5");
    assert_eq!(refs.len(), 1);
    assert!(
        refs[0].anchor.is_none(),
        "an unmapped fullword tail must not invent an anchor"
    );
}

#[test]
fn live_frag_173_chain_resolves_art_26_2_par_1() {
    let src = fs::read_to_string(fixture_dir().join("npa-frag-173.txt"))
        .expect("read the tracked live fixture npa-frag-173.txt");
    let first = resolve_lawrefs(&src);
    let second = resolve_lawrefs(&src);
    assert_eq!(
        first, second,
        "resolution over the live fragment must be deterministic"
    );
    let hit = first
        .iter()
        .find(|resolved| resolved.capture.span.start() == 251 && resolved.capture.span.end() == 267)
        .expect("frag-173 holds the tracked capture at [251, 267)");
    assert_eq!(hit.capture.pattern_id, "abbrev-hier-chain");
    assert_eq!(hit.capture.slots.marker_chain, ["ch", "st"]);
    assert_eq!(hit.capture.slots.hier_nums, ["1", "26.2"]);
    assert_eq!(
        hit.anchor
            .as_ref()
            .expect("the live chain must mint its canonical anchor")
            .path,
        "art_26.2/par_1",
        "ELI 5.4.1: outer-first from the article, dotted number intact"
    );
}

#[test]
fn anaphora_binds_nearest_frame_or_emits_honest_ctx_tokens() {
    // Bound: the nearest previous art frame on the stack.
    let refs = resolve_lawrefs("ч. 1 ст. 42 согласно настоящей статьи");
    let chain = refs
        .iter()
        .find(|resolved| resolved.capture.pattern_id == "abbrev-hier-chain")
        .expect("the chain must be captured");
    assert_eq!(
        chain.anchor.as_ref().expect("first proof").path,
        "art_42/par_1"
    );
    let anaphora = refs
        .iter()
        .find(|resolved| resolved.capture.pattern_id == "anaphora_candidate")
        .expect("the anaphora must be captured");
    assert_eq!(
        anaphora
            .anchor
            .as_ref()
            .expect("a prior art frame exists on the stack")
            .path,
        "art_42"
    );

    // Missing frame: `art_ctx` is the literal unresolved current-article
    // token (the roadmap art_ctx contract).
    let refs = resolve_lawrefs("согласно настоящей статьи");
    let anaphora = refs
        .iter()
        .find(|resolved| resolved.capture.pattern_id == "anaphora_candidate")
        .expect("the anaphora must be captured");
    assert_eq!(
        anaphora
            .anchor
            .as_ref()
            .expect("the ctx token is an emitted anchor")
            .path,
        "art_ctx"
    );

    // The target is the LAST Word of the span, not the head: `того же
    // раздела` binds `раздела` -> razd -> the prior `разд. 2` sec frame.
    let refs = resolve_lawrefs("разд. 2 пунктом 5 того же раздела");
    let anaphora = refs
        .iter()
        .find(|resolved| resolved.capture.pattern_id == "anaphora_candidate")
        .expect("the anaphora must be captured");
    assert_eq!(
        anaphora
            .anchor
            .as_ref()
            .expect("the prior sec frame exists")
            .path,
        "sec_2"
    );

    // Empty stack at a sec level: `sec_ctx`, never a panic.
    let refs = resolve_lawrefs("того же раздела");
    let anaphora = refs
        .iter()
        .find(|resolved| resolved.capture.pattern_id == "anaphora_candidate")
        .expect("the anaphora must be captured");
    assert_eq!(
        anaphora
            .anchor
            .as_ref()
            .expect("the ctx token is an emitted anchor")
            .path,
        "sec_ctx"
    );
}

#[test]
fn doc_anaphora_and_hostile_inputs_stay_none_without_panicking() {
    // `doc` is the non-eId sink: `Кодекса` resolves to None, never doc_*.
    let refs = resolve_lawrefs("настоящего Кодекса");
    assert_eq!(refs.len(), 1);
    assert!(refs[0].anchor.is_none());
    assert!(refs[0].dedup_key.is_none());

    // Hostile empty-stack `того же` (no target word) captures nothing at
    // all: empty result, no panic.
    assert!(resolve_lawrefs("того же").is_empty());

    // The C2 hostile initial still never heads an anchor.
    for resolved in resolve_lawrefs("Ч. 1.1 ст. 33") {
        assert_ne!(
            resolved.capture.span.start(),
            0,
            "the hostile initial must never head an anchor"
        );
    }
}

#[test]
fn quoted_enum_appends_sub_letter_to_the_nearest_unit_frame() {
    // The word head left-scans through the inflected-tail table
    // (`подпункта` -> pp -> pnt) and appends the letter as written.
    let refs = resolve_lawrefs("п. 2.1 подпункта \"а\"");
    let quoted = refs
        .iter()
        .find(|resolved| resolved.capture.pattern_id == "quoted-enum")
        .expect("the quoted enumeration must be captured");
    assert_eq!(
        quoted
            .anchor
            .as_ref()
            .expect("the prior pnt frame exists")
            .path,
        "pnt_2.1/sub_\u{0430}",
        "the Cyrillic letter rides the anchor as written"
    );

    // No prior frame of the head's unit: honestly unresolved, no panic.
    let refs = resolve_lawrefs("подпункта \"а\"");
    let quoted = refs
        .iter()
        .find(|resolved| resolved.capture.pattern_id == "quoted-enum")
        .expect("the quoted enumeration must be captured");
    assert!(
        quoted.anchor.is_none(),
        "a quoted enum with no pnt frame must not invent one"
    );
}

#[test]
fn out_of_scope_patterns_pass_through_unresolved() {
    // Amendment windows stay out of resolution scope (R070).
    let refs = resolve_lawrefs("в ред. от 01.01.2028 44-ФЗ");
    let window = refs
        .iter()
        .find(|resolved| resolved.capture.pattern_id == "abbrev-amendment-window")
        .expect("the amendment window must be captured");
    assert!(window.anchor.is_none() && window.dedup_key.is_none());

    // A headless range with no stack context stays honestly unresolved
    // (fail-closed): the T03 range pins below cover the resolvable shapes.
    let refs = resolve_lawrefs("1.1 - 4.1");
    assert_eq!(refs.len(), 1);
    assert_eq!(refs[0].capture.pattern_id, "range_candidate");
    assert!(refs[0].anchor.is_none());
    assert!(refs[0].members.is_empty() && refs[0].dedup_key.is_none());
}

// ---------------------------------------------------------------------------
// T03 pins: ranges as the expanded endpoint pair (left-scan head, stack
// fallback, art/ctx prefix, the false hyphen-split range, the compound
// comma list) and the canonical dedup dump round-trip. Live pins read
// named tracked fixtures; the dump walk is disk-backed over the
// manifest-indexed fragments plus the synthetic demos. Inline fixtures
// and tracked src/YAML reads only; the corpus is never opened; hand-rolled
// JSON readers (D328), no `#[path]` include of test support (D335).
// ---------------------------------------------------------------------------

/// Repo-root-relative evidence directory holding the tracked artifacts.
fn evidence_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../prd/migration/rust-evidence")
}

/// Repo-root-relative path of the tracked resolution demo dump.
fn resolution_dump_path() -> PathBuf {
    evidence_dir().join("m199-s03-resolution-demo.json")
}

#[test]
fn range_expands_to_exactly_two_members_with_left_scan_head() {
    // `частями` -> ch -> par (left-scan head over the covering token
    // stream); dotted HierNum endpoints expand to the pair.
    let refs = resolve_lawrefs("частями 5.1 - 5.4");
    assert_eq!(refs.len(), 1);
    let range = &refs[0];
    assert_eq!(range.capture.pattern_id, "range_candidate");
    assert_eq!(
        range
            .members
            .iter()
            .map(|a| a.path.as_str())
            .collect::<Vec<_>>(),
        ["par_5.1", "par_5.4"],
        "expanded pair: exactly two members, never an enumeration"
    );
    assert_eq!(
        range.anchor.as_ref().expect("first member").path,
        "par_5.1",
        "the anchor may be the first member"
    );
    assert_eq!(
        range.dedup_key.as_deref(),
        Some("par_5.1..par_5.4"),
        "the dedup key carries the literal '..' - never a walk"
    );
}

#[test]
fn live_frag_001_range_resolves_art_pair_without_stack_article() {
    let src =
        fs::read_to_string(fixture_dir().join("npa-frag-001.txt")).expect("read npa-frag-001.txt");
    let refs = resolve_lawrefs(&src);
    let range = refs
        .iter()
        .find(|r| r.capture.span.start() == 645 && r.capture.span.end() == 656)
        .expect("frag-001 holds the tracked range at [645, 656)");
    assert_eq!(
        range
            .capture
            .slots
            .range
            .as_ref()
            .map(|(f, t)| (f.as_str(), t.as_str())),
        Some(("7.29", "7.32"))
    );
    // The left tail `статьями` maps st -> art, so the endpoints ARE the
    // article anchors: no stack article exists and none is invented.
    assert_eq!(
        range
            .members
            .iter()
            .map(|a| a.path.as_str())
            .collect::<Vec<_>>(),
        ["art_7.29", "art_7.32"]
    );
    assert_eq!(range.dedup_key.as_deref(), Some("art_7.29..art_7.32"));
}

#[test]
fn range_over_art_ctx_supplied_by_following_anaphora() {
    // Roadmap demo in its dotted executable form (the bare-integer
    // `части 1 - 3` endpoints are C2 digit-Words for the frozen lexer -
    // never HierNum - so the frozen capture mints no range_candidate for
    // them; the dump non_claims document the substitution). Left-scan
    // части -> ch -> par; the FOLLOWING anaphora `настоящей статьи`
    // supplies art_ctx (a look-ahead over the sorted captures, never a
    // text right-scan).
    let refs = resolve_lawrefs("части 2.1 - 2.3 настоящей статьи");
    let range = refs
        .iter()
        .find(|r| r.capture.pattern_id == "range_candidate")
        .expect("the dotted range must be captured");
    assert_eq!(
        range
            .members
            .iter()
            .map(|a| a.path.as_str())
            .collect::<Vec<_>>(),
        ["art_ctx/par_2.1", "art_ctx/par_2.3"]
    );
    assert_eq!(
        range.dedup_key.as_deref(),
        Some("art_ctx/par_2.1..art_ctx/par_2.3")
    );

    // The same range WITHOUT the anaphora invents no art_ctx.
    let refs = resolve_lawrefs("части 2.1 - 2.3");
    let range = refs
        .iter()
        .find(|r| r.capture.pattern_id == "range_candidate")
        .expect("the range must be captured");
    assert_eq!(
        range
            .members
            .iter()
            .map(|a| a.path.as_str())
            .collect::<Vec<_>>(),
        ["par_2.1", "par_2.3"],
        "no following art anaphora: no honest ctx token is invented"
    );
}

#[test]
fn live_frag_057_range_pin_names_the_yielded_shape() {
    // Plan pin: name whichever shape the algorithm yields. The left-scan
    // head `подпункты` maps pp -> pnt through the YAML table (NOT `sub`:
    // `pp` maps to `pnt` by canon), and the fullword `пункта 4` sits to
    // the RIGHT of the range - capture order sorts the range [51,60)
    // first and the resolver never right-scans text - so no pnt_4 frame
    // can prefix the pair. Yielded shape: the bare pair pnt_4.1..pnt_4.3;
    // the fullword separately mints pnt_4 when walked.
    let src =
        fs::read_to_string(fixture_dir().join("npa-frag-057.txt")).expect("read npa-frag-057.txt");
    let refs = resolve_lawrefs(&src);
    let range = refs
        .iter()
        .find(|r| r.capture.span.start() == 51 && r.capture.span.end() == 60)
        .expect("frag-057 holds the tracked range at [51, 60)");
    assert_eq!(
        range
            .members
            .iter()
            .map(|a| a.path.as_str())
            .collect::<Vec<_>>(),
        ["pnt_4.1", "pnt_4.3"]
    );
    assert_eq!(range.dedup_key.as_deref(), Some("pnt_4.1..pnt_4.3"));
    let fullword = refs
        .iter()
        .find(|r| r.capture.pattern_id == "fullword-ref")
        .expect("the fullword `пункта 4` must be captured");
    assert_eq!(
        fullword.anchor.as_ref().map(|a| a.path.as_str()),
        Some("pnt_4"),
        "the fullword to the right mints its own frame when walked"
    );
}

#[test]
fn false_range_from_hyphen_split_stays_unresolved() {
    // Live pin: npa-frag-009 [562,573) is the lexer split of `16.6-2` -
    // capture froze `16.6 - 16.6` because `-2` is not a second HierNum.
    // Equal endpoints continuing a hyphen split prove no range.
    let src =
        fs::read_to_string(fixture_dir().join("npa-frag-009.txt")).expect("read npa-frag-009.txt");
    let refs = resolve_lawrefs(&src);
    let range = refs
        .iter()
        .find(|r| r.capture.span.start() == 562 && r.capture.span.end() == 573)
        .expect("frag-009 holds the tracked range at [562, 573)");
    assert_eq!(
        range
            .capture
            .slots
            .range
            .as_ref()
            .map(|(f, t)| (f.as_str(), t.as_str())),
        Some(("16.6", "16.6"))
    );
    assert!(
        range.anchor.is_none() && range.members.is_empty() && range.dedup_key.is_none(),
        "the false range stays honestly unresolved"
    );

    // The same guard on a synthetic: the unit IS provable (`статьями` ->
    // st -> art) and the range still stays unresolved.
    let refs = resolve_lawrefs("статьями 16.6 - 16.6-2 настоящего закона");
    let range = refs
        .iter()
        .find(|r| r.capture.pattern_id == "range_candidate")
        .expect("the range must be captured");
    assert!(range.anchor.is_none() && range.members.is_empty());
}

#[test]
fn stack_frame_supplies_range_unit_when_left_scan_is_blocked() {
    // `;` is a Punct: the left-scan stops without a head, and the nearest
    // previous numbered stack frame (`art_15` from the chain) supplies
    // the unit per the plan fallback. The unit IS art, so the endpoints
    // carry no additional article prefix.
    let refs = resolve_lawrefs("ч. 2 ст. 15; 4.5 - 4.7");
    let chain = refs
        .iter()
        .find(|r| r.capture.pattern_id == "abbrev-hier-chain")
        .expect("the chain must be captured");
    assert_eq!(
        chain.anchor.as_ref().map(|a| a.path.as_str()),
        Some("art_15/par_2")
    );
    let range = refs
        .iter()
        .find(|r| r.capture.pattern_id == "range_candidate")
        .expect("the range must be captured");
    assert_eq!(
        range
            .members
            .iter()
            .map(|a| a.path.as_str())
            .collect::<Vec<_>>(),
        ["art_4.5", "art_4.7"]
    );
    assert_eq!(range.dedup_key.as_deref(), Some("art_4.5..art_4.7"));

    // Hostile: a headless range with an EMPTY stack stays unresolved
    // (fail-closed; no invented unit).
    let refs = resolve_lawrefs("4.5 - 4.7");
    assert_eq!(refs.len(), 1);
    assert!(refs[0].anchor.is_none() && refs[0].members.is_empty());
}

#[test]
fn range_under_a_stacked_article_prefixes_both_endpoints() {
    // The chain mints art_42/par_1.1 and stacks the art frame; the
    // range's left-scan head `ч.` supplies par, and both endpoints carry
    // the stacked article prefix (art_42/par_1.1 + art_42/par_1.3).
    let refs = resolve_lawrefs("ст. 42 ч. 1.1 - 1.3");
    let range = refs
        .iter()
        .find(|r| r.capture.pattern_id == "range_candidate")
        .expect("the range must be captured");
    assert_eq!(
        range
            .members
            .iter()
            .map(|a| a.path.as_str())
            .collect::<Vec<_>>(),
        ["art_42/par_1.1", "art_42/par_1.3"]
    );
    assert_eq!(
        range.dedup_key.as_deref(),
        Some("art_42/par_1.1..art_42/par_1.3")
    );
}

#[test]
fn compound_comma_list_invents_no_pairs_and_no_eighth_matcher() {
    // npa-frag-034 `части 1 - 2, 2.2 - 2.3-1, 2.6, 4 и 5 статьи 3, ...`:
    // ONLY the already-emitted HierNum - HierNum capture (2.2 - 2.3) is a
    // pair candidate - the bare `1 - 2` endpoints are digit-Words (no
    // capture) and `2.6, 4 и 5` is no eighth matcher. The candidate
    // itself stays honestly unresolved: its left-scan head is blocked by
    // the `,` of the preceding list item (the governing `части` belongs
    // to the whole comma list, and resolution invents no list logic - a
    // comma-list member never borrows the list head). The trailing `-1`
    // of `2.3-1` does not matter either way: the false-range guard is
    // equal-endpoints-only, and the pair is endpoint-based, never a walk.
    let src =
        fs::read_to_string(fixture_dir().join("npa-frag-034.txt")).expect("read npa-frag-034.txt");
    let refs = resolve_lawrefs(&src);
    let ranges: Vec<_> = refs
        .iter()
        .filter(|r| r.capture.pattern_id == "range_candidate")
        .collect();
    assert_eq!(
        ranges.len(),
        1,
        "the bare `1 - 2` endpoints are digit-Words: no second range capture"
    );
    assert_eq!(
        ranges[0]
            .capture
            .slots
            .range
            .as_ref()
            .map(|(f, t)| (f.as_str(), t.as_str())),
        Some(("2.2", "2.3"))
    );
    assert!(
        ranges[0].anchor.is_none() && ranges[0].members.is_empty() && ranges[0].dedup_key.is_none(),
        "the comma-list member invents no head and no pair"
    );
    // The fullwords of the same fragment resolve on their own heads.
    let fullwords: Vec<_> = refs
        .iter()
        .filter(|r| r.capture.pattern_id == "fullword-ref")
        .collect();
    assert_eq!(fullwords.len(), 2);
    assert_eq!(
        fullwords[0].anchor.as_ref().map(|a| a.path.as_str()),
        Some("art_3")
    );
    assert_eq!(
        fullwords[1].anchor.as_ref().map(|a| a.path.as_str()),
        Some("art_18")
    );
}

#[test]
fn range_unit_above_art_stays_unresolved() {
    // Same eid_start_at contour as chains: a `гл.` head never mints a
    // chp_ range.
    let refs = resolve_lawrefs("гл. 2.1 - 2.3");
    let range = refs
        .iter()
        .find(|r| r.capture.pattern_id == "range_candidate")
        .expect("the range must be captured");
    assert!(
        range.anchor.is_none() && range.members.is_empty() && range.dedup_key.is_none(),
        "units above the article never mint range endpoints"
    );
}

// ---------------------------------------------------------------------------
// T03 dump: the tracked m199-s03-resolution-demo.json is a PROJECTION of
// the engine (same S02 dump idiom), never a second canon. Envelope closed;
// hand-rolled JSON readers (D328); the dump grouping test re-walks the
// manifest-indexed fragments plus the synthetic demos (Q6: tracked txt
// only, milliseconds - no corpus).
// ---------------------------------------------------------------------------

/// The synthetic demos the grouping walks (invented demo fragment ids;
/// the texts are inline synthetics, never corpus payload).
const DEMO_SYNTHETICS: [(&str, &str); 3] = [
    ("demo:chain_first_proof", "ч. 1 ст. 42"),
    (
        "demo:range_over_art_ctx",
        "части 2.1 - 2.3 настоящей статьи",
    ),
    ("demo:expanded_pair_not_enum", "пп. 2.1 - 4.1"),
];

/// Mandatory non-claim substrings of the dump (slice plan T03 item 3).
const DUMP_MANDATORY_NON_CLAIMS: [&str; 7] = [
    "R070 open",
    "not official publication",
    "sample ≠ gold",
    "no resolution accuracy",
    "no alpha",
    "no ADR-0028 lifecycle flip",
    "Consultant-only",
];

/// The dump's non_claims: the S02 seven adapted to S03, the explicit
/// grouping-vs-accuracy row, and the documented roadmap-range substitution.
const DUMP_NON_CLAIMS: [&str; 9] = [
    "R070 open: not official publication provenance; anchors are lexical resolutions, never edition provenance, and the 180-fragment sample stays pre-annotation",
    "sample ≠ gold: the S01 sample and its rule-seed are pre-annotation (D366), never gold",
    "no resolution accuracy: the resolver mints lexical canonical anchors only - no Layer-3 accuracy, no span-F1, no correctness claim is measured here",
    "no alpha: no inter-annotator agreement is computed in S03; the agreement gate belongs to S04",
    "no ADR-0028 lifecycle flip: kb-ontology.yaml stays [proposed] and this dump stays [bounded]",
    "Consultant-only: fragments come from the tracked Consultant 44-ФЗ harvest; no other provider and no corpus sweep in S03",
    "resolution canon: the npa_lawref_resolution YAML table stays the single canon; this dump is an observable projection, not a second canon",
    "S03 ships grouping, S04 measures bundesrecht Layer-3: dedup grouping is a canonical-identity demo, accuracy measurement belongs to S04",
    "roadmap range phrasings with bare-integer endpoints (части 1 - 3, пп. 1 - 4.1) never capture range_candidate: a bare integer lexes as a C2 digit-Word, never a HierNum, so the frozen 159-record seed pins that contour; roadmap_rows carry the dotted executable forms with the same left-scan head and pair shape (and the same following-anaphora art_ctx supply where the roadmap row has one)",
];

/// Closed envelope key set of the dump artifact.
const DUMP_ENVELOPE_KEYS: [&str; 6] = [
    "schema",
    "schema_version",
    "lifecycle",
    "non_claims",
    "roadmap_rows",
    "dedup_groups",
];

/// One roadmap demo row: (id, note_kind, user reference, canonical anchor,
/// dedup key, quoted labels, generation note) — data only, the round-trip
/// tests recompute every field from the engine.
type DumpRow = (
    &'static str,
    &'static str,
    &'static str,
    &'static str,
    &'static str,
    &'static [&'static str],
    &'static str,
);

/// Canonical dedup member: (fragment id, span start, span end) — payload-free
/// per Q3; the fragment id resolves the text via the tracked txt.
type DedupMember = (String, usize, usize);

/// The four roadmap demo rows the dump carries (generation data only -
/// the round-trip tests recompute every field from the engine).
const DUMP_ROWS: [DumpRow; 4] = [
    (
        "chain_first_proof",
        "synthetic",
        "ч. 1 ст. 42",
        "art_42/par_1",
        "art_42/par_1",
        &[],
        "ELI 5.4.1 chain reverse (T02 first proof): capture order [ch, st] + [1, 42] mints the outer-first art_42/par_1",
    ),
    (
        "range_over_art_ctx",
        "synthetic",
        "части 2.1 - 2.3 настоящей статьи",
        "art_ctx/par_2.1",
        "art_ctx/par_2.1..art_ctx/par_2.3",
        &["art_ctx/par_2.1", "art_ctx/par_2.3"],
        "roadmap row 'части 1 - 3 настоящей статьи' in its dotted executable form: left-scan head части -> ch -> par, the following art anaphora supplies art_ctx; the bare-integer phrasing never captures range_candidate (see non_claims)",
    ),
    (
        "expanded_pair_not_enum",
        "synthetic",
        "пп. 2.1 - 4.1",
        "pnt_2.1",
        "pnt_2.1..pnt_4.1",
        &["pnt_2.1", "pnt_4.1"],
        "roadmap row 'пп. 1 - 4.1' in its dotted executable form: pp maps to pnt via YAML; exactly two members with the literal '..' dedup key - never the 1..=4.1 enumeration",
    ),
    (
        "live_chain_frag_173",
        "live",
        "npa-frag-173@[251,267)",
        "art_26.2/par_1",
        "art_26.2/par_1",
        &[],
        "live tracked fixture: the ч. 1 ст. 26.2 chain at [251,267); the dump carries fragment_id + offsets, never fragment payload",
    ),
];

/// Skips whitespace and commas, then reads one `(key, raw-value)` member of
/// a JSON object body. Hand-rolled (D328): the dump carries no escapes; any
/// escape fails closed.
fn json_object_members(body: &str) -> Result<Vec<(String, String)>, String> {
    let bytes = body.as_bytes();
    let mut cursor = 0usize;
    let mut members = Vec::new();
    loop {
        while cursor < bytes.len() && (bytes[cursor].is_ascii_whitespace() || bytes[cursor] == b',')
        {
            cursor += 1;
        }
        if cursor >= bytes.len() {
            return Ok(members);
        }
        if bytes[cursor] != b'"' {
            return Err(format!("dump member {cursor} must open with a quoted key"));
        }
        let (key, next) = json_string_at(body, cursor)?;
        cursor = next;
        while cursor < bytes.len() && bytes[cursor].is_ascii_whitespace() {
            cursor += 1;
        }
        if bytes.get(cursor) != Some(&b':') {
            return Err(format!("dump key '{key}' must be followed by ':'"));
        }
        cursor += 1;
        while cursor < bytes.len() && bytes[cursor].is_ascii_whitespace() {
            cursor += 1;
        }
        let end = json_value_end(body, cursor)?;
        members.push((key, body[cursor..end].to_owned()));
        cursor = end;
    }
}

/// Reads the `"..."` string starting at `start`; returns the value and the
/// end offset. Escapes fail closed.
fn json_string_at(text: &str, start: usize) -> Result<(String, usize), String> {
    let bytes = text.as_bytes();
    if bytes.get(start) != Some(&b'"') {
        return Err("expected a JSON string".to_owned());
    }
    let mut value = String::new();
    let mut cursor = start + 1;
    while let Some(&byte) = bytes.get(cursor) {
        match byte {
            b'"' => return Ok((value, cursor + 1)),
            b'\\' => return Err("dump strings must not carry escape sequences".to_owned()),
            _ => {
                let ch = text[cursor..]
                    .chars()
                    .next()
                    .ok_or_else(|| "invalid string boundary".to_owned())?;
                value.push(ch);
                cursor += ch.len_utf8();
            }
        }
    }
    Err("unterminated JSON string".to_owned())
}

/// End offset of the JSON value starting at `start` (string, number, array,
/// or object; balanced and string-aware). Anything else fails closed.
fn json_value_end(text: &str, start: usize) -> Result<usize, String> {
    match text.as_bytes().get(start) {
        Some(b'"') => json_string_at(text, start).map(|(_, end)| end),
        Some(byte) if byte.is_ascii_digit() => {
            let mut end = start;
            while text
                .as_bytes()
                .get(end)
                .is_some_and(|byte| byte.is_ascii_digit())
            {
                end += 1;
            }
            Ok(end)
        }
        Some(open @ (b'[' | b'{')) => {
            let close = if *open == b'[' { b']' } else { b'}' };
            let mut depth = 0usize;
            let mut in_string = false;
            let mut cursor = start;
            while let Some(&byte) = text.as_bytes().get(cursor) {
                if in_string {
                    match byte {
                        b'\\' => {
                            return Err("dump strings must not carry escape sequences".to_owned())
                        }
                        b'"' => in_string = false,
                        _ => {}
                    }
                } else {
                    match byte {
                        b'"' => in_string = true,
                        b'[' | b'{' => depth += 1,
                        b']' | b'}' => {
                            depth -= 1;
                            if depth == 0 && byte == close {
                                return Ok(cursor + 1);
                            }
                        }
                        _ => {}
                    }
                }
                cursor += 1;
            }
            Err("unterminated JSON container".to_owned())
        }
        _ => Err(format!("unsupported JSON value at byte {start}")),
    }
}

/// Top-level items of a raw JSON array (string-aware, depth-aware split).
fn json_array_items(raw: &str) -> Result<Vec<&str>, String> {
    let trimmed = raw.trim();
    let inner = trimmed
        .strip_prefix('[')
        .ok_or_else(|| format!("expected a JSON array, got: {trimmed}"))?
        .strip_suffix(']')
        .ok_or_else(|| "unterminated JSON array".to_owned())?;
    let mut items = Vec::new();
    let mut depth = 0usize;
    let mut in_string = false;
    let mut start: Option<usize> = None;
    for (offset, &byte) in inner.as_bytes().iter().enumerate() {
        if in_string {
            match byte {
                b'\\' => return Err("dump strings must not carry escape sequences".to_owned()),
                b'"' => in_string = false,
                _ => {}
            }
            continue;
        }
        match byte {
            b'"' => {
                in_string = true;
                start = start.or(Some(offset));
            }
            b'[' | b'{' => {
                depth += 1;
                start = start.or(Some(offset));
            }
            b']' | b'}' => depth -= 1,
            b',' if depth == 0 => {
                if let Some(begin) = start.take() {
                    items.push(inner[begin..offset].trim());
                }
            }
            byte if byte.is_ascii_whitespace() => {}
            _ => start = start.or(Some(offset)),
        }
    }
    if in_string {
        return Err("unterminated JSON string".to_owned());
    }
    if let Some(begin) = start {
        items.push(inner[begin..].trim());
    }
    Ok(items.into_iter().filter(|item| !item.is_empty()).collect())
}

fn object_body(raw: &str) -> Result<&str, String> {
    raw.trim()
        .strip_prefix('{')
        .ok_or_else(|| format!("expected a JSON object, got: {raw}"))?
        .strip_suffix('}')
        .ok_or_else(|| "unterminated JSON object".to_owned())
}

fn dump_string_field(row: &[(String, String)], key: &str) -> Result<String, String> {
    let raw = row
        .iter()
        .find(|(name, _)| name == key)
        .map(|(_, value)| value.as_str())
        .ok_or_else(|| format!("dump row is missing '{key}'"))?;
    let inner = raw
        .trim()
        .strip_prefix('"')
        .ok_or_else(|| format!("'{key}' must be a JSON string"))?
        .strip_suffix('"')
        .ok_or_else(|| format!("'{key}' must be a closed JSON string"))?;
    if inner.contains('\\') {
        return Err(format!("'{key}' must not carry escape sequences"));
    }
    Ok(inner.to_owned())
}

fn dump_number_field(row: &[(String, String)], key: &str) -> Result<usize, String> {
    let raw = row
        .iter()
        .find(|(name, _)| name == key)
        .map(|(_, value)| value.as_str())
        .ok_or_else(|| format!("dump row is missing '{key}'"))?;
    raw.trim()
        .parse::<usize>()
        .map_err(|_| format!("'{key}' must be a JSON number, got '{raw}'"))
}

fn dump_string_list(raw: &str) -> Result<Vec<String>, String> {
    json_array_items(raw)?
        .iter()
        .map(|item| {
            let inner = item
                .strip_prefix('"')
                .ok_or_else(|| format!("expected a JSON string, got: {item}"))?
                .strip_suffix('"')
                .ok_or_else(|| format!("unterminated JSON string: {item}"))?;
            if inner.contains('\\') {
                return Err("list strings must not carry escape sequences".to_owned());
            }
            Ok(inner.to_owned())
        })
        .collect()
}

/// One roadmap demo row of the parsed dump.
#[derive(Debug)]
struct RoadmapRow {
    demo: String,
    kind: String,
    input: String,
    anchor: String,
    dedup_key: String,
    members: Vec<String>,
    note: String,
}

/// The parsed dump view (closed envelope).
#[derive(Debug)]
struct DumpView {
    schema: String,
    schema_version: usize,
    lifecycle: String,
    non_claims: Vec<String>,
    roadmap_rows: Vec<RoadmapRow>,
    dedup_groups: Vec<(String, Vec<DedupMember>)>,
}

/// Closed-envelope parse of the tracked dump; extra keys fail closed.
fn analyze_dump(text: &str) -> Result<DumpView, String> {
    let inner = text
        .trim()
        .strip_prefix('{')
        .ok_or_else(|| "dump must be a JSON object".to_owned())?
        .strip_suffix('}')
        .ok_or_else(|| "dump must be one closed JSON object".to_owned())?;
    let top = json_object_members(inner)?;
    for (index, (key, _)) in top.iter().enumerate() {
        if top[..index].iter().any(|(seen, _)| seen == key) {
            return Err(format!("dump: duplicate key '{key}'"));
        }
    }
    for (key, _) in &top {
        if !DUMP_ENVELOPE_KEYS.contains(&key.as_str()) {
            return Err(format!(
                "dump: extra key '{key}' is outside the closed envelope"
            ));
        }
    }
    for key in DUMP_ENVELOPE_KEYS {
        if !top.iter().any(|(name, _)| name == key) {
            return Err(format!("dump: closed envelope is missing key '{key}'"));
        }
    }
    let field = |key: &str| dump_string_field(&top, key);
    let schema = field("schema")?;
    let schema_version = dump_number_field(&top, "schema_version")?;
    let lifecycle = field("lifecycle")?;
    let non_claims_raw = top
        .iter()
        .find(|(name, _)| name == "non_claims")
        .map(|(_, value)| value.as_str())
        .ok_or_else(|| "dump: missing non_claims".to_owned())?;
    let non_claims = dump_string_list(non_claims_raw)?;
    let rows_raw = json_array_items(
        top.iter()
            .find(|(name, _)| name == "roadmap_rows")
            .map(|(_, value)| value.as_str())
            .ok_or_else(|| "dump: missing roadmap_rows".to_owned())?,
    )?;
    let mut roadmap_rows = Vec::new();
    for row_raw in rows_raw {
        let row = json_object_members(object_body(row_raw)?)?;
        for (key, _) in &row {
            if !matches!(
                key.as_str(),
                "demo" | "kind" | "input" | "anchor" | "dedup_key" | "members" | "note"
            ) {
                return Err(format!("dump roadmap row: extra key '{key}'"));
            }
        }
        let members_raw = row
            .iter()
            .find(|(name, _)| name == "members")
            .map(|(_, value)| value.as_str())
            .ok_or_else(|| "dump roadmap row: missing members".to_owned())?;
        roadmap_rows.push(RoadmapRow {
            demo: dump_string_field(&row, "demo")?,
            kind: dump_string_field(&row, "kind")?,
            input: dump_string_field(&row, "input")?,
            anchor: dump_string_field(&row, "anchor")?,
            dedup_key: dump_string_field(&row, "dedup_key")?,
            members: dump_string_list(members_raw)?,
            note: dump_string_field(&row, "note")?,
        });
    }
    let groups_raw = json_array_items(
        top.iter()
            .find(|(name, _)| name == "dedup_groups")
            .map(|(_, value)| value.as_str())
            .ok_or_else(|| "dump: missing dedup_groups".to_owned())?,
    )?;
    let mut dedup_groups = Vec::new();
    for group_raw in groups_raw {
        let group = json_object_members(object_body(group_raw)?)?;
        for (key, _) in &group {
            if !matches!(key.as_str(), "path" | "member_spans") {
                return Err(format!("dump dedup group: extra key '{key}'"));
            }
        }
        let path = dump_string_field(&group, "path")?;
        let spans_raw = json_array_items(
            group
                .iter()
                .find(|(name, _)| name == "member_spans")
                .map(|(_, value)| value.as_str())
                .ok_or_else(|| "dump dedup group: missing member_spans".to_owned())?,
        )?;
        let mut member_spans = Vec::new();
        for span_raw in spans_raw {
            let span = json_object_members(object_body(span_raw)?)?;
            for (key, _) in &span {
                // Q3: identity + offsets only - never fragment payload.
                if !matches!(key.as_str(), "fragment_id" | "start" | "end") {
                    return Err(format!("dump member span: extra key '{key}'"));
                }
            }
            member_spans.push((
                dump_string_field(&span, "fragment_id")?,
                dump_number_field(&span, "start")?,
                dump_number_field(&span, "end")?,
            ));
        }
        dedup_groups.push((path, member_spans));
    }
    Ok(DumpView {
        schema,
        schema_version,
        lifecycle,
        non_claims,
        roadmap_rows,
        dedup_groups,
    })
}

/// Tracked seed/manifest strings carry no escape sequences; any escape fails
/// loudly (the S02 capture-contract reader idiom, duplicated here - no
/// `#[path]` include, D335).
fn json_string_after_colon(rest: &str) -> Option<String> {
    let rest = rest.trim_start().strip_prefix(':')?.trim_start();
    let rest = rest.strip_prefix('"')?;
    let mut value = String::new();
    for ch in rest.chars() {
        match ch {
            '"' => return Some(value),
            '\\' => return None,
            _ => value.push(ch),
        }
    }
    None
}

/// Hand-rolled manifest reader (D328): the (`id`, `file`) pairs of the
/// `fragments` array in document order.
fn manifest_fragments(manifest: &str) -> Vec<(String, String)> {
    let anchor = manifest
        .find("\"fragments\"")
        .expect("manifest must index a fragments array");
    let array_start = anchor
        + manifest[anchor..]
            .find('[')
            .expect("fragments must be an array");
    let mut depth = 0usize;
    let mut array_end = manifest.len();
    for (offset, byte) in manifest.as_bytes()[array_start..].iter().enumerate() {
        match byte {
            b'[' => depth += 1,
            b']' => {
                depth -= 1;
                if depth == 0 {
                    array_end = array_start + offset;
                    break;
                }
            }
            _ => {}
        }
    }
    let body = &manifest[array_start + 1..array_end];
    let mut fragments = Vec::new();
    let mut cursor = 0usize;
    while let Some(found) = body[cursor..].find("\"id\"") {
        let after = cursor + found + "\"id\"".len();
        let Some(id) = json_string_after_colon(&body[after..]) else {
            break;
        };
        let Some(file_found) = body[after..].find("\"file\"") else {
            break;
        };
        let Some(file) = json_string_after_colon(&body[after + file_found + "\"file\"".len()..])
        else {
            break;
        };
        assert!(
            file == format!("{id}.txt"),
            "manifest file field must mirror the fragment id: {id} vs {file}"
        );
        fragments.push((id, file));
        cursor = after;
    }
    fragments
}

/// The engine walk the dump must project: resolve every manifest-indexed
/// fragment plus the three synthetic demos and group the resolved refs by
/// their canonical dedup key (Q3: members carry fragment_id + offsets,
/// never payload; Q6: tracked txt only, milliseconds - no corpus).
fn compute_dedup_groups() -> Vec<(String, Vec<DedupMember>)> {
    let manifest = fs::read_to_string(evidence_dir().join("m199-s01-gold-sample-manifest.json"))
        .expect("read the S01 gold sample manifest");
    let fragments = manifest_fragments(&manifest);
    let mut members: Vec<(String, String, usize, usize)> = Vec::new();
    for (fragment_id, file) in &fragments {
        let src = fs::read_to_string(fixture_dir().join(file))
            .unwrap_or_else(|err| panic!("read fragment {fragment_id} ({file}): {err}"));
        for resolved in resolve_lawrefs(&src) {
            if let Some(key) = resolved.dedup_key {
                members.push((
                    key,
                    fragment_id.clone(),
                    resolved.capture.span.start(),
                    resolved.capture.span.end(),
                ));
            }
        }
    }
    for (fragment_id, text) in DEMO_SYNTHETICS {
        for resolved in resolve_lawrefs(text) {
            if let Some(key) = resolved.dedup_key {
                members.push((
                    key.to_owned(),
                    fragment_id.to_owned(),
                    resolved.capture.span.start(),
                    resolved.capture.span.end(),
                ));
            }
        }
    }
    members.sort();
    let mut groups: Vec<(String, Vec<DedupMember>)> = Vec::new();
    for (key, fragment_id, start, end) in members {
        match groups.last_mut() {
            Some((group_key, list)) if *group_key == key => {
                list.push((fragment_id, start, end));
            }
            _ => groups.push((key, vec![(fragment_id, start, end)])),
        }
    }
    groups
}

/// Renders the full tracked dump text (generation data only).
fn render_resolution_dump_json() -> String {
    let mut out = String::new();
    out.push_str("{\n");
    out.push_str("  \"schema\": \"npa-lawref-resolution-demo/v1\",\n");
    out.push_str("  \"schema_version\": 1,\n");
    out.push_str("  \"lifecycle\": \"[bounded]\",\n");
    out.push_str("  \"non_claims\": [\n");
    let claims: Vec<String> = DUMP_NON_CLAIMS
        .iter()
        .map(|claim| format!("    \"{claim}\""))
        .collect();
    out.push_str(&claims.join(",\n"));
    out.push_str("\n  ],\n");
    let rows: Vec<String> = DUMP_ROWS
        .iter()
        .map(|(demo, kind, input, anchor, dedup, members, note)| {
            let member_list = members
                .iter()
                .map(|member| format!("\"{member}\""))
                .collect::<Vec<_>>()
                .join(", ");
            format!(
                "    {{\"demo\": \"{demo}\", \"kind\": \"{kind}\", \"input\": \"{input}\", \
                 \"anchor\": \"{anchor}\", \"dedup_key\": \"{dedup}\", \"members\": \
                 [{member_list}], \"note\": \"{note}\"}}"
            )
        })
        .collect();
    out.push_str("  \"roadmap_rows\": [\n");
    out.push_str(&rows.join(",\n"));
    out.push_str("\n  ],\n");
    let groups: Vec<String> = compute_dedup_groups()
        .iter()
        .map(|(path, members)| {
            let spans = members
                .iter()
                .map(|(fragment_id, start, end)| {
                    format!("{{\"fragment_id\": \"{fragment_id}\", \"start\": {start}, \"end\": {end}}}")
                })
                .collect::<Vec<_>>()
                .join(", ");
            format!("    {{\"path\": \"{path}\", \"member_spans\": [{spans}]}}")
        })
        .collect();
    out.push_str("  \"dedup_groups\": [\n");
    out.push_str(&groups.join(",\n"));
    out.push_str("\n  ]\n}\n");
    out
}

/// One-shot generator for the tracked dump (D328/D335: no serde, no src
/// support). Run explicitly, never in the default battery:
/// `cargo test -p ln-decode --offline --test npa_lawref_resolve_contract \
///  generate_resolution_demo_dump_writes_tracked_projection -- --ignored`
#[test]
#[ignore = "one-shot dump generator: writes the tracked projection; run explicitly with --ignored"]
fn generate_resolution_demo_dump_writes_tracked_projection() {
    let json = render_resolution_dump_json();
    let path = resolution_dump_path();
    fs::write(&path, &json).unwrap_or_else(|err| panic!("write {}: {err}", path.display()));
    println!("wrote {} ({} bytes)", path.display(), json.len());
}

#[test]
fn resolution_dump_envelope_and_non_claims_hold() {
    let dump = fs::read_to_string(resolution_dump_path())
        .expect("the tracked resolution dump must be readable");
    let view = analyze_dump(&dump).expect("the dump must parse against the closed envelope");
    assert_eq!(view.schema, "npa-lawref-resolution-demo/v1");
    assert_eq!(view.schema_version, 1);
    assert_eq!(view.lifecycle, "[bounded]");
    let joined = view.non_claims.join("\n");
    for mandatory in DUMP_MANDATORY_NON_CLAIMS {
        assert!(
            joined.contains(mandatory),
            "non_claims must carry '{mandatory}'"
        );
    }
    assert!(
        joined.contains("S03 ships grouping, S04 measures bundesrecht Layer-3"),
        "the explicit grouping-vs-accuracy non claim must be present"
    );
    assert_eq!(view.roadmap_rows.len(), 4, "the four roadmap demos");
    assert!(
        !view.dedup_groups.is_empty(),
        "the sample must surface real dedup groups"
    );
}

/// `npa-frag-173@[251,267)` -> (fragment id, (start, end)).
fn parse_live_row_input(input: &str) -> (String, (usize, usize)) {
    let (fragment_id, span) = input
        .split_once('@')
        .unwrap_or_else(|| panic!("live row input must be 'id@[start,end)': {input}"));
    let span = span.trim().trim_start_matches('[').trim_end_matches(')');
    let (start, end) = span
        .split_once(',')
        .unwrap_or_else(|| panic!("live span must be [start,end): {input}"));
    (
        fragment_id.to_owned(),
        (
            start.trim().parse().expect("live span start"),
            end.trim().parse().expect("live span end"),
        ),
    )
}

#[test]
fn resolution_dump_roadmap_rows_recompute_from_the_engine() {
    let dump = fs::read_to_string(resolution_dump_path()).expect("read the dump");
    let view = analyze_dump(&dump).expect("parse the dump");
    let mut seen_demos: Vec<&str> = Vec::new();
    let mut synthetic_inputs: Vec<&str> = Vec::new();
    for row in &view.roadmap_rows {
        assert!(
            !seen_demos.contains(&row.demo.as_str()),
            "duplicate demo row '{}'",
            row.demo
        );
        seen_demos.push(&row.demo);
        assert!(!row.note.is_empty(), "each row documents its shape");
        let (anchor_path, member_paths) = if row.kind == "synthetic" {
            synthetic_inputs.push(&row.input);
            let refs = resolve_lawrefs(&row.input);
            let hit = refs
                .iter()
                .find(|resolved| resolved.dedup_key.as_deref() == Some(row.dedup_key.as_str()))
                .unwrap_or_else(|| {
                    panic!(
                        "row {}: the engine must resolve the dumped dedup key",
                        row.demo
                    )
                });
            (
                hit.anchor
                    .as_ref()
                    .map(|anchor| anchor.path.clone())
                    .unwrap_or_default(),
                hit.members
                    .iter()
                    .map(|anchor| anchor.path.clone())
                    .collect::<Vec<_>>(),
            )
        } else {
            let (fragment_id, span) = parse_live_row_input(&row.input);
            let src = fs::read_to_string(fixture_dir().join(format!("{fragment_id}.txt")))
                .unwrap_or_else(|err| panic!("read {fragment_id}: {err}"));
            let hit = resolve_lawrefs(&src)
                .into_iter()
                .find(|resolved| {
                    resolved.capture.span.start() == span.0 && resolved.capture.span.end() == span.1
                })
                .unwrap_or_else(|| panic!("row {}: the live capture must exist", row.demo));
            (
                hit.anchor.map(|anchor| anchor.path).unwrap_or_default(),
                hit.members
                    .iter()
                    .map(|anchor| anchor.path.clone())
                    .collect::<Vec<_>>(),
            )
        };
        assert_eq!(anchor_path, row.anchor, "row {}: anchor", row.demo);
        assert_eq!(member_paths, row.members, "row {}: members", row.demo);
    }
    let mut demo_inputs: Vec<&str> = DEMO_SYNTHETICS.iter().map(|(_, text)| *text).collect();
    demo_inputs.sort_unstable();
    synthetic_inputs.sort_unstable();
    assert_eq!(
        synthetic_inputs, demo_inputs,
        "the dump's synthetic rows and the grouping synthetics are the same demos"
    );
}

#[test]
fn resolution_dump_dedup_groups_project_the_engine_walk() {
    let dump = fs::read_to_string(resolution_dump_path()).expect("read the dump");
    let view = analyze_dump(&dump).expect("parse the dump");
    let expected = compute_dedup_groups();
    assert_eq!(
        view.dedup_groups, expected,
        "the dump is a projection of the engine walk over the sample plus the synthetic demos - not a second canon"
    );
    assert!(
        view.dedup_groups
            .iter()
            .any(|(_, members)| members.len() > 1),
        "the demo must surface real variant grouping across fragments"
    );
    assert!(
        view.dedup_groups
            .iter()
            .any(|(path, _)| path.contains("..")),
        "range dedup keys must surface as groups"
    );
}

#[test]
fn hostile_extra_dump_key_fails_closed() {
    let dump = fs::read_to_string(resolution_dump_path()).expect("read the dump");
    let mutated = dump.replacen("{", "{\n  \"future_hint\": 1,", 1);
    assert_ne!(mutated, dump, "the hostile mutation must change the dump");
    let error = analyze_dump(&mutated).expect_err("an extra dump key must fail closed");
    assert!(
        error.contains("future_hint") && error.contains("extra key"),
        "expected the extra-key rejection to name the key, got: {error}"
    );
}

#[test]
fn resolution_freeze_pins_hold() {
    assert_eq!(
        embedded_resolution().range_policy,
        "expanded_pair",
        "range_policy stays the expanded-pair policy"
    );
    let manifest_dir = Path::new(env!("CARGO_MANIFEST_DIR"));
    let cargo_toml = fs::read_to_string(manifest_dir.join("Cargo.toml")).expect("read Cargo.toml");
    for dependency in ["serde", "clap", "walkdir"] {
        assert!(
            !cargo_toml.contains(dependency),
            "ln-decode must not gain a '{dependency}' dependency (hand-rolled dump readers, D328)"
        );
    }
    let lexer_src = fs::read_to_string(manifest_dir.join("src/lexer.rs")).expect("read lexer");
    assert!(
        !lexer_src.contains("TokenKind::LawRef"),
        "the closed nine-kind lexer set must not gain TokenKind::LawRef"
    );
    let lawref_src = fs::read_to_string(manifest_dir.join("src/lawref.rs")).expect("read lawref");
    assert!(
        !lawref_src.contains("eId"),
        "the eId vocabulary stays out of the capture module"
    );
    let resolve_src =
        fs::read_to_string(manifest_dir.join("src/lawref_resolve.rs")).expect("read resolve");
    assert!(
        resolve_src.contains("eId"),
        "the eId vocabulary lives in the resolve module (and may appear in the dump)"
    );
}

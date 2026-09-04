//! Contract tests for the LawRef resolution layer (M199 S03 T01/T02).
//!
//! T01 shipped the resolved SURFACE over frozen capture (D350): the
//! `lawref_resolve` module (never fields on `LawRef`), the
//! `npa_lawref_resolution` YAML table (resolution as data, KBO-R025
//! idiom), and the fail-closed `CanonicalAnchor`. T02 lifts resolution
//! to behavior: the chain reverse (ELI 5.4.1: `ч. 1 ст. 42` ->
//! `art_42/par_1`), the per-src context stack, anaphora binding with
//! `art_ctx`/`sec_ctx` as the honest missing-frame tokens, the `doc`
//! sink (never a minted `doc_*`), and the quoted-enum `sub_а` append.
//! The first proof runs un-ignored; ranges stay honestly unresolved (the
//! next task owns the expanded pair) and amendment/date windows stay out
//! of scope (R070).
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

    // Ranges stay honestly unresolved: the expanded pair belongs to T03.
    let refs = resolve_lawrefs("1.1 - 4.1");
    assert_eq!(refs.len(), 1);
    assert_eq!(refs[0].capture.pattern_id, "range_candidate");
    assert!(refs[0].anchor.is_none());
    assert!(refs[0].members.is_empty() && refs[0].dedup_key.is_none());
}

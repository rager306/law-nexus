//! Load test for NPA golden reference fixtures (M197 S01; loader shared S02).
//!
//! The fixture set under `tests/fixtures/npa/` carries decoded reference
//! fragments from the tracked Consultant 44-ФЗ WordML (`ConsultantWordMlBlockDecoder`
//! harvest; never a naive `w:t` join). The sidecar `fz44_npa_tokens.json` pins
//! the expected `TokenKind` + UTF-8 byte span markup; the `.txt` files are the
//! span coordinate system (lexemes are reconstructed as `text[start..end]`,
//! never duplicated into the JSON).
//!
//! This file keeps only the `#[test]` surface (plus the `#[ignore]` harvest
//! audit); the loader itself lives in `tests/npa_support/mod.rs`. Default
//! tests never decode the 5.2 MB source XML (provenance is pinned by path +
//! sha256 + byte length checked against `fs::metadata` only; the `#[ignore]`
//! harvest audit decodes it only on demand).
//!
//! D330 marking rules, frozen here so two executors cannot mark `15.1` or
//! `пп.` differently:
//! 1. `Abbrev` consumes its trailing dot: `ст.` is one token (`id: st`);
//!    `пп.` is ONE token (`id: pp`), never two `п` tokens.
//! 2. `HierNum` is the longest `\d+(\.\d+)+` run (`15.1`, `2.3.1`) — one token.
//! 3. `Date` is `dd.mm.yyyy` with plausible day/month and beats `HierNum` on
//!    that shape (`01.01.2028` is never HierNum).
//! 4. Undotted digit runs (`16`, `2028`) are `Word`, not HierNum.
//! 5. Headings `Глава 1.` / `Статья 16.` are `Word + Space + Word + Punct`
//!    (not HierNum, not EnumMarker).
//! 6. `EnumMarker` is the list marker as typed, without surrounding quotes
//!    (`1)`, `1.`, `а)`; a quoted subpoint label `п "а"` = Punct + EnumMarker
//!    + Punct).
//! 7. `Space` is contiguous Unicode whitespace (NBSP included when the
//!    decoder emits it).
//! 8. `Punct` is everything else non-alphanumeric.
//! 9. `Word` is an alphabetic run (plus undotted digit runs); no lowercasing
//!    in fixtures.
//! 10. Latin `N` in `N 44-ФЗ` is Word, `44-ФЗ` is DocNo, lone `ФЗ`/`ФКЗ` is
//!     LawCode.

mod npa_support;

use std::collections::BTreeMap;
use std::fs;

use ln_decode::{
    adapters::ConsultantWordMlBlockDecoder,
    domain::{DecodeRequest, FamilyFormat, PayloadRef},
    ports::BlockDecoderPort,
};
use npa_support::*;

// ---------------------------------------------------------------------------
// Green path.
// ---------------------------------------------------------------------------

#[test]
fn golden_fixtures_load_with_covering_span_invariants() {
    let fragments = load_golden_fixtures(&fixtures_dir(), &repo_root())
        .expect("NPA golden fixtures must load fail-closed");
    assert!(fragments.len() >= 2, "the two seed goldens must be present");

    let fz44_001 = fragments
        .iter()
        .find(|fragment| fragment.id == "fz44-001")
        .expect("seed golden fz44-001");
    assert_eq!(fz44_001.source_block_index, 877, "fz44-001 block pin");
    assert_eq!(fz44_001.bucket, "abbrev-hier");
    assert_eq!(fz44_001.note_kind, "enacting");
    assert!(
        fz44_001
            .abbrev_ids
            .iter()
            .any(|id| id.as_deref() == Some("st")),
        "fz44-001 must pin an Abbrev st lexeme"
    );
    assert!(
        fz44_001.kinds.contains(&"HierNum"),
        "fz44-001 must pin a dotted HierNum token"
    );

    let fz44_002 = fragments
        .iter()
        .find(|fragment| fragment.id == "fz44-002")
        .expect("seed golden fz44-002");
    assert_eq!(fz44_002.source_block_index, 31, "fz44-002 block pin");
    assert_eq!(fz44_002.bucket, "date-docno");
    assert_eq!(fz44_002.note_kind, "enacting");
    assert!(fz44_002.kinds.contains(&"Date"), "fz44-002 must pin a Date");
    assert!(
        fz44_002.kinds.contains(&"DocNo"),
        "fz44-002 must pin a DocNo"
    );

    // TextSpan slices must reconstruct every pinned lexeme byte-exactly.
    for fragment in &fragments {
        assert_eq!(
            fragment.spans.len(),
            fragment.lexemes.len(),
            "span/lexeme parallel arrays must stay aligned"
        );
        for (span, lexeme) in fragment.spans.iter().zip(&fragment.lexemes) {
            assert_eq!(
                &fragment.text[span.start()..span.end()],
                lexeme,
                "fragment {} span {}..{} must slice its lexeme",
                fragment.id,
                span.start(),
                span.end()
            );
        }
    }

    assert!(
        count_corpus_fragments(&fragments) >= 2,
        "seed goldens are corpus fragments (T02 raises the quota to >= 40)"
    );
}

// ---------------------------------------------------------------------------
// T02: corpus harvest quotas and named collision locks (fixtures only; the
// 5.2 MB XML stays undecoded in CI — provenance is the pinned metadata).
// ---------------------------------------------------------------------------

/// Full-form reference words that must appear as Word tokens in the
/// fullword-ref bucket (running text, not headings; T02 quota table).
const FULLWORD_FORMS: [&str; 14] = [
    "статья",
    "статьи",
    "статье",
    "статью",
    "статьей",
    "статей", //
    "часть",
    "части",
    "частью",
    "частями",
    "частей", //
    "пункта",
    "пунктом",
    "подпунктом",
];

/// Punct lexemes that satisfy the misc-punct bucket (quotes / list separators).
const MISC_PUNCT_LEXEMES: [&str; 5] = ["\"", ";", ":", "«", "»"];

#[test]
fn t02_corpus_goldens_hold_quota_and_collision_locks() {
    let fragments = load_golden_fixtures(&fixtures_dir(), &repo_root())
        .expect("NPA golden fixtures must load fail-closed");

    let corpus: Vec<&LoadedFragment> = fragments
        .iter()
        .filter(|fragment| fragment.note_kind != "synthetic")
        .collect();
    assert!(
        corpus.len() >= 40,
        "T02 quota: >= 40 corpus goldens (got {})",
        corpus.len()
    );

    let bucket = |name: &str| -> Vec<&LoadedFragment> {
        corpus
            .iter()
            .copied()
            .filter(|fragment| fragment.bucket == name)
            .collect()
    };
    let has_abbrev = |fragment: &LoadedFragment, id: &str| {
        fragment
            .abbrev_ids
            .iter()
            .any(|candidate| candidate.as_deref() == Some(id))
    };

    // abbrev-hier >= 8: an Abbrev from {st,ch,p,pp} AND a HierNum per fragment.
    let abbrev_hier = bucket("abbrev-hier");
    assert!(
        abbrev_hier.len() >= 8,
        "abbrev-hier quota: >= 8 (got {})",
        abbrev_hier.len()
    );
    for fragment in &abbrev_hier {
        assert!(
            fragment
                .abbrev_ids
                .iter()
                .any(|id| matches!(id.as_deref(), Some("st" | "ch" | "p" | "pp"))),
            "{} must carry a reference Abbrev",
            fragment.id
        );
        assert!(
            fragment.kinds.contains(&"HierNum"),
            "{} must pair the Abbrev with a HierNum",
            fragment.id
        );
    }

    // date-docno >= 6: Date AND DocNo per fragment.
    let date_docno = bucket("date-docno");
    assert!(
        date_docno.len() >= 6,
        "date-docno quota: >= 6 (got {})",
        date_docno.len()
    );
    for fragment in &date_docno {
        assert!(
            fragment.kinds.contains(&"Date") && fragment.kinds.contains(&"DocNo"),
            "{} must carry both Date and DocNo",
            fragment.id
        );
    }

    // enum-list >= 4: EnumMarker per fragment.
    let enum_list = bucket("enum-list");
    assert!(
        enum_list.len() >= 4,
        "enum-list quota: >= 4 (got {})",
        enum_list.len()
    );
    for fragment in &enum_list {
        assert!(
            fragment.kinds.contains(&"EnumMarker"),
            "{} must carry an EnumMarker",
            fragment.id
        );
    }

    // heading >= 4: `Глава/Статья N.` = Word + Space + Word(digits) + Punct(".");
    // both heading words must occur across the bucket.
    let heading = bucket("heading");
    assert!(
        heading.len() >= 4,
        "heading quota: >= 4 (got {})",
        heading.len()
    );
    let mut have_glava = false;
    let mut have_statya = false;
    for fragment in &heading {
        assert!(
            fragment.kinds.len() >= 4,
            "{} too short for a heading",
            fragment.id
        );
        assert_eq!(
            fragment.kinds[0], "Word",
            "{} heading must open with a Word",
            fragment.id
        );
        let is_glava = fragment.lexemes[0] == "Глава";
        let is_statya = fragment.lexemes[0] == "Статья";
        assert!(
            is_glava || is_statya,
            "{} must open with Глава/Статья, got {}",
            fragment.id,
            fragment.lexemes[0]
        );
        have_glava |= is_glava;
        have_statya |= is_statya;
        assert_eq!(fragment.kinds[1], "Space");
        assert_eq!(
            fragment.kinds[2], "Word",
            "{} heading number is an undotted-digit Word, never HierNum",
            fragment.id
        );
        assert!(
            fragment.lexemes[2].chars().all(|ch| ch.is_ascii_digit()),
            "{} heading number must be digits",
            fragment.id
        );
        assert_eq!(fragment.kinds[3], "Punct");
        assert_eq!(
            fragment.lexemes[3], ".",
            "{} heading dot stays Punct",
            fragment.id
        );
    }
    assert!(
        have_glava && have_statya,
        "heading bucket needs both Глава and Статья"
    );

    // fullword-ref >= 6: >= 1 full-form Word token per fragment.
    let fullword = bucket("fullword-ref");
    assert!(
        fullword.len() >= 6,
        "fullword-ref quota: >= 6 (got {})",
        fullword.len()
    );
    for fragment in &fullword {
        assert!(
            fragment
                .lexemes
                .iter()
                .zip(&fragment.kinds)
                .any(|(lexeme, kind)| *kind == "Word" && FULLWORD_FORMS.contains(&lexeme.as_str())),
            "{} must carry a full-form reference word",
            fragment.id
        );
    }

    // lawcode >= 2: lone ФЗ and lone ФКЗ across the bucket.
    let lawcode = bucket("lawcode");
    assert!(
        lawcode.len() >= 2,
        "lawcode quota: >= 2 (got {})",
        lawcode.len()
    );
    assert!(
        lawcode
            .iter()
            .any(|f| f.lexemes.iter().any(|lexeme| lexeme == "ФЗ")),
        "lawcode bucket must pin a lone ФЗ"
    );
    assert!(
        lawcode
            .iter()
            .any(|f| f.lexemes.iter().any(|lexeme| lexeme == "ФКЗ")),
        "lawcode bucket must pin a lone ФКЗ"
    );

    // dense-note: >= 3 and <= 5, each pinning `ред.` as Abbrev id=red.
    let dense_note = bucket("dense-note");
    assert!(
        dense_note.len() >= 3,
        "dense-note quota: >= 3 (got {})",
        dense_note.len()
    );
    assert!(
        dense_note.len() <= 5,
        "dense-note quota: <= 5 (got {})",
        dense_note.len()
    );
    for fragment in &dense_note {
        assert!(
            has_abbrev(fragment, "red"),
            "{} must pin `ред.` as Abbrev id=red",
            fragment.id
        );
    }

    // misc-punct >= 3: quotes / `;` / `:` Punct lexemes per fragment.
    let misc_punct = bucket("misc-punct");
    assert!(
        misc_punct.len() >= 3,
        "misc-punct quota: >= 3 (got {})",
        misc_punct.len()
    );
    for fragment in &misc_punct {
        assert!(
            fragment
                .lexemes
                .iter()
                .zip(&fragment.kinds)
                .any(|(lexeme, kind)| *kind == "Punct"
                    && MISC_PUNCT_LEXEMES.contains(&lexeme.as_str())),
            "{} must carry a quote/semicolon/colon Punct",
            fragment.id
        );
    }

    // Every kind from the closed vocab occurs at least once in the corpus.
    for kind in TOKEN_KINDS {
        assert!(
            corpus.iter().any(|fragment| fragment.kinds.contains(&kind)),
            "kind {kind} must occur at least once in the corpus"
        );
    }
    // The four reference abbrevs each occur (пп. is one token id=pp).
    for id in ["st", "ch", "p", "pp"] {
        assert!(
            corpus.iter().any(|fragment| has_abbrev(fragment, id)),
            "corpus must pin Abbrev id={id}"
        );
    }
    // Corpus Abbrev ids never come from the D329 forbidden zero set.
    for fragment in &corpus {
        for id in &fragment.abbrev_ids {
            if let Some(id) = id.as_deref() {
                assert!(
                    !CORPUS_FORBIDDEN_ABBREV_IDS.contains(&id),
                    "{}: forbidden corpus Abbrev id {id}",
                    fragment.id
                );
            }
        }
    }

    // Lexeme-shape locks T01 deliberately left to the load layer:
    // >= 1 Abbrev with trailing dot, >= 1 two-part HierNum, >= 1 dd.mm.yyyy
    // Date, >= 1 -ФЗ/-ФКЗ DocNo, and no date-shaped HierNum anywhere.
    let mut saw_abbrev_dot = false;
    let mut saw_two_part_hier = false;
    let mut saw_date = false;
    let mut saw_docno = false;
    for fragment in &corpus {
        for (kind, lexeme) in fragment.kinds.iter().zip(&fragment.lexemes) {
            match *kind {
                "Abbrev" => saw_abbrev_dot |= lexeme.ends_with('.'),
                "HierNum" => {
                    saw_two_part_hier |=
                        is_hier_num_lexeme(lexeme) && lexeme.matches('.').count() == 1;
                    assert!(
                        !is_date_lexeme(lexeme),
                        "{}: date-shaped HierNum lexeme {lexeme} is forbidden",
                        fragment.id
                    );
                }
                "Date" => saw_date |= is_date_lexeme(lexeme),
                "DocNo" => saw_docno |= lexeme.contains("-ФЗ") || lexeme.contains("-ФКЗ"),
                _ => {}
            }
        }
    }
    assert!(saw_abbrev_dot, "corpus must pin a dotted Abbrev lexeme");
    assert!(saw_two_part_hier, "corpus must pin a \\d+\\.\\d+ HierNum");
    assert!(saw_date, "corpus must pin a dd.mm.yyyy Date");
    assert!(saw_docno, "corpus must pin a -ФЗ/-ФКЗ DocNo");

    // Named corpus collisions (T02 plan item 7):
    // 1. `п. 9.1` = Abbrev + Space + HierNum (fz44-003).
    let fz44_003 = corpus
        .iter()
        .find(|fragment| fragment.id == "fz44-003")
        .expect("fz44-003 must exist");
    assert!(
        fz44_003
            .kinds
            .windows(3)
            .any(|window| window == ["Abbrev", "Space", "HierNum"]),
        "fz44-003 must pin Abbrev+Space+HierNum (п. 9.1)"
    );

    // 2. dotted HierNum directly after an Abbrev (fz44-010: ст. 111.4).
    let fz44_010 = corpus
        .iter()
        .find(|fragment| fragment.id == "fz44-010")
        .expect("fz44-010 must exist");
    assert!(
        has_abbrev(fz44_010, "st") && fz44_010.lexemes.iter().any(|lexeme| lexeme == "111.4"),
        "fz44-010 must pin Abbrev(st) before the dotted HierNum 111.4"
    );

    // 3. `пп. "а"` = Abbrev(pp) + Space + Punct + EnumMarker + Punct.
    let quoted_label = corpus.iter().any(|fragment| {
        (0..fragment.kinds.len().saturating_sub(4)).any(|index| {
            fragment.kinds[index] == "Abbrev"
                && fragment.abbrev_ids[index].as_deref() == Some("pp")
                && fragment.kinds[index + 1] == "Space"
                && fragment.kinds[index + 2] == "Punct"
                && fragment.kinds[index + 3] == "EnumMarker"
                && fragment.kinds[index + 4] == "Punct"
        })
    });
    assert!(
        quoted_label,
        "corpus must pin the quoted subpoint label collision"
    );

    // 4. `N 44-ФЗ` = Word("N") + Space + DocNo.
    let n_docno = corpus.iter().any(|fragment| {
        (0..fragment.kinds.len().saturating_sub(2)).any(|index| {
            fragment.kinds[index] == "Word"
                && fragment.lexemes[index] == "N"
                && fragment.kinds[index + 1] == "Space"
                && fragment.kinds[index + 2] == "DocNo"
        })
    });
    assert!(n_docno, "corpus must pin Word(N)+Space+DocNo");

    // 5. `01.01.2028` stays Date, never HierNum (fz44-037).
    let fz44_037 = corpus
        .iter()
        .find(|fragment| fragment.id == "fz44-037")
        .expect("fz44-037 must exist");
    assert!(
        fz44_037
            .lexemes
            .iter()
            .zip(&fz44_037.kinds)
            .any(|(lexeme, kind)| lexeme == "01.01.2028" && *kind == "Date"),
        "fz44-037 must pin 01.01.2028 as Date"
    );

    // Frequency caps from the T02 marking contract.
    let amendment_lists = corpus
        .iter()
        .filter(|fragment| {
            (0..fragment.kinds.len().saturating_sub(1)).any(|index| {
                fragment.kinds[index] == "DocNo"
                    && fragment.kinds[index + 1] == "Punct"
                    && fragment.lexemes[index + 1] == ","
            })
        })
        .count();
    assert!(
        amendment_lists <= 5,
        "amendment-list fragments must stay <= 5 (got {amendment_lists})"
    );
    let provider_notes = fragments
        .iter()
        .filter(|fragment| fragment.note_kind == "provider_note")
        .count();
    assert!(
        provider_notes <= 5,
        "provider_note fragments must stay <= 5 (got {provider_notes})"
    );
}

// ---------------------------------------------------------------------------
// Hostile: in-memory manifests must fail the loader closed (goldens untouched).
// ---------------------------------------------------------------------------

const HOSTILE_FILE: &str = "hostile-001.txt";

fn hostile_source_block() -> String {
    format!(
        r#""source": {{
    "path": "{SOURCE_RELATIVE_PATH}",
    "sha256": "{SOURCE_SHA256}",
    "decoder": "{SOURCE_DECODER}",
    "non_claims": [
      "not official-publication provenance (R070 open)",
      "not LawRef / act-tree / clause segmentation",
      "not legal interpretation"
    ]
  }}"#
    )
}

fn hostile_manifest(fragments_json: &str) -> String {
    format!(
        r#"{{
  "schema_version": 1,
  "lifecycle": "[bounded]",
  {source_block},
  "fragments": {fragments_json}
}}"#,
        source_block = hostile_source_block(),
    )
}

fn hostile_fragment_json(tokens_json: &str) -> String {
    format!(
        r#"[{{"id": "hostile-001", "file": "{HOSTILE_FILE}", "source_block_index": 0, "bucket": "abbrev-hier", "note_kind": "enacting", "tokens": [{tokens_json}]}}]"#
    )
}

fn run_hostile_loader(tokens_json: &str, text: &str) -> String {
    let mut files = BTreeMap::new();
    files.insert(HOSTILE_FILE.to_string(), text.to_string());
    let manifest = hostile_manifest(&hostile_fragment_json(tokens_json));
    validate_fixture_set(&manifest, &files, None)
        .expect_err("hostile manifest must fail the loader closed")
}

#[test]
fn hostile_overlap_spans_fail_closed() {
    // text = "абв" (6 bytes); the second token starts inside the first one.
    let error = run_hostile_loader(
        r#"{"kind": "Word", "start": 0, "end": 4},
           {"kind": "Word", "start": 2, "end": 6}"#,
        "абв",
    );
    assert!(
        error.contains("overlap"),
        "expected overlap error, got: {error}"
    );

    // Exact duplicate spans collide the same way.
    let error = run_hostile_loader(
        r#"{"kind": "Word", "start": 0, "end": 2},
           {"kind": "Word", "start": 0, "end": 2}"#,
        "аб",
    );
    assert!(
        error.contains("overlap"),
        "expected overlap error, got: {error}"
    );
}

#[test]
fn hostile_covering_gap_fails_closed() {
    // text = "ст. 15.1" (10 bytes); the Space at bytes 5..6 is unclaimed.
    let error = run_hostile_loader(
        r#"{"kind": "Abbrev", "id": "st", "start": 0, "end": 5},
           {"kind": "HierNum", "start": 6, "end": 10}"#,
        "ст. 15.1",
    );
    assert!(
        error.contains("gap"),
        "expected covering-gap error, got: {error}"
    );
}

#[test]
fn hostile_unknown_editorial_kind_fails_closed() {
    let error = run_hostile_loader(
        r#"{"kind": "Abbrev", "id": "st", "start": 0, "end": 5},
           {"kind": "Space", "start": 5, "end": 6},
           {"kind": "Editorial", "start": 6, "end": 10}"#,
        "ст. 15.1",
    );
    assert!(
        error.contains("unknown token kind 'Editorial'"),
        "expected Editorial rejection, got: {error}"
    );
}

#[test]
fn hostile_pp_split_into_two_abbrevs_fails_closed() {
    // text = "пп." (5 bytes): `пп.` must be ONE Abbrev id=pp (D330 rule 1);
    // two `п` tokens leave `п` without its canonical trailing dot.
    let error = run_hostile_loader(
        r#"{"kind": "Abbrev", "id": "p", "start": 0, "end": 2},
           {"kind": "Abbrev", "id": "p", "start": 2, "end": 5}"#,
        "пп.",
    );
    assert!(
        error.contains("canonical"),
        "expected canonical-lexeme rejection for the split `пп.`, got: {error}"
    );
}

#[test]
fn hostile_empty_span_fails_closed() {
    let error = run_hostile_loader(r#"{"kind": "Punct", "start": 0, "end": 0}"#, ".");
    assert!(
        error.contains(">= end"),
        "expected empty-span rejection, got: {error}"
    );
}

#[test]
fn hostile_date_shaped_hier_num_fails_closed() {
    // D330 rule 3: Date beats HierNum on `dd.mm.yyyy` ("01.01.2028").
    let error = run_hostile_loader(
        r#"{"kind": "Word", "start": 0, "end": 4},
           {"kind": "Space", "start": 4, "end": 5},
           {"kind": "HierNum", "start": 5, "end": 15},
           {"kind": "Space", "start": 15, "end": 16},
           {"kind": "Word", "start": 16, "end": 34}"#,
        "До 01.01.2028 действует",
    );
    assert!(
        error.contains("Date"),
        "expected Date-beats-HierNum rejection, got: {error}"
    );
}

#[test]
fn hostile_corpus_forbidden_abbrev_id_fails_closed() {
    // D329: `гл.` has zero hits in the tracked 44-ФЗ — never mint it as corpus.
    let error = run_hostile_loader(
        r#"{"kind": "Abbrev", "id": "gl", "start": 0, "end": 5},
           {"kind": "Space", "start": 5, "end": 6},
           {"kind": "Word", "start": 6, "end": 7}"#,
        "гл. 2",
    );
    assert!(
        error.contains("D329-forbidden"),
        "expected forbidden-abbrev rejection, got: {error}"
    );
}

#[test]
fn hostile_malformed_manifest_json_fails_closed() {
    let mut files = BTreeMap::new();
    files.insert(HOSTILE_FILE.to_string(), "ст. 15.1".to_string());
    let manifest = hostile_manifest(&hostile_fragment_json(
        r#"{"kind": "Abbrev", "id": "st", "start": 0, "end": 5},,,"#,
    ));
    let error = validate_fixture_set(&manifest, &files, None)
        .expect_err("malformed manifest JSON must fail closed");
    assert!(
        error.contains("JSON parse error"),
        "expected JSON parse rejection, got: {error}"
    );
}

#[test]
fn hostile_bijection_violations_fail_closed() {
    // Extra .txt on disk without a manifest entry.
    let mut files = BTreeMap::new();
    files.insert(HOSTILE_FILE.to_string(), "ст. 15.1".to_string());
    files.insert("orphan-001.txt".to_string(), "лишний".to_string());
    let manifest = hostile_manifest(&hostile_fragment_json(
        r#"{"kind": "Abbrev", "id": "st", "start": 0, "end": 5},
           {"kind": "Space", "start": 5, "end": 6},
           {"kind": "HierNum", "start": 6, "end": 10}"#,
    ));
    let error = validate_fixture_set(&manifest, &files, None)
        .expect_err("extra txt without a manifest entry must fail closed");
    assert!(
        error.contains("extra fixture file"),
        "expected extra-file rejection, got: {error}"
    );

    // Manifest entry whose .txt is missing.
    let empty_files: BTreeMap<String, String> = BTreeMap::new();
    let error = validate_fixture_set(&manifest, &empty_files, None)
        .expect_err("manifest entry without its txt must fail closed");
    assert!(
        error.contains("no .txt fixture"),
        "expected missing-file rejection, got: {error}"
    );
}

// ---------------------------------------------------------------------------
// T03: synthetic collision pair, corpus exclusion, bucket pairing lock.
// ---------------------------------------------------------------------------

#[test]
fn t03_synthetic_collision_pair_is_marked_and_excluded_from_corpus() {
    let fragments = load_golden_fixtures(&fixtures_dir(), &repo_root())
        .expect("NPA golden fixtures must load fail-closed");

    let corpus = count_corpus_fragments(&fragments);
    let synthetic: Vec<&LoadedFragment> = fragments
        .iter()
        .filter(|fragment| fragment.note_kind == "synthetic")
        .collect();

    assert!(corpus >= 40, "corpus quota stays >= 40 (got {corpus})");
    assert_eq!(
        synthetic.len(),
        2,
        "exactly syn-001 and syn-002; no syn-003+ sprawl"
    );
    assert_eq!(
        fragments.len(),
        corpus + synthetic.len(),
        "synthetic fragments must be excluded from the corpus count"
    );
    for fragment in &synthetic {
        assert_eq!(
            fragment.bucket, SYNTHETIC_BUCKET,
            "{} must carry bucket {SYNTHETIC_BUCKET}",
            fragment.id
        );
        assert_eq!(
            fragment.source_block_index, 0,
            "{} is constructed, not a decoded block",
            fragment.id
        );
    }

    // syn-001: one line carrying BOTH a dotted non-date HierNum and a
    // dd.mm.yyyy Date (D330: Date beats HierNum on dd.mm.yyyy only).
    let syn_001 = fragments
        .iter()
        .find(|fragment| fragment.id == "syn-001")
        .expect("syn-001 collision fixture");
    assert!(
        !syn_001.text.contains('\n'),
        "syn-001 must hold the collision on one line"
    );
    let hier = syn_001
        .lexemes
        .iter()
        .zip(&syn_001.kinds)
        .find(|(_, kind)| **kind == "HierNum")
        .map(|(lexeme, _)| lexeme)
        .expect("syn-001 must pin a dotted HierNum");
    assert!(
        is_hier_num_lexeme(hier) && !is_date_lexeme(hier),
        "syn-001 HierNum {hier} must be a dotted non-date"
    );
    let date = syn_001
        .lexemes
        .iter()
        .zip(&syn_001.kinds)
        .find(|(_, kind)| **kind == "Date")
        .map(|(lexeme, _)| lexeme)
        .expect("syn-001 must pin a Date");
    assert!(
        is_date_lexeme(date),
        "syn-001 Date {date} must be dd.mm.yyyy"
    );
    assert_ne!(hier, date, "the two collision lexemes must be distinct");

    // syn-002: list-start EnumMarker `1.` (dot inside) plus a separate
    // in-sentence HierNum `5.1`; no reference Abbrevs smuggled in.
    let syn_002 = fragments
        .iter()
        .find(|fragment| fragment.id == "syn-002")
        .expect("syn-002 collision fixture");
    assert_eq!(
        syn_002.kinds[0], "EnumMarker",
        "syn-002 must open with the list-start marker"
    );
    assert_eq!(syn_002.lexemes[0], "1.", "the dot stays inside the marker");
    assert!(
        syn_002
            .lexemes
            .iter()
            .zip(&syn_002.kinds)
            .any(|(lexeme, kind)| *kind == "HierNum" && lexeme == "5.1"),
        "syn-002 must pin the in-sentence HierNum 5.1"
    );
    assert!(
        syn_002.abbrev_ids.iter().all(|id| id.is_none()),
        "synthetic fixtures must not smuggle Abbrev ids"
    );
}

#[test]
fn hostile_synthetic_bucket_pairing_fails_closed() {
    let fragment_json = |bucket: &str, note_kind: &str| {
        format!(
            r#"[{{"id": "hostile-001", "file": "{HOSTILE_FILE}", "source_block_index": 0, "bucket": "{bucket}", "note_kind": "{note_kind}", "tokens": [{{"kind": "Punct", "id": null, "start": 0, "end": 1}}]}}]"#
        )
    };
    let run = |bucket: &str, note_kind: &str| {
        let mut files = BTreeMap::new();
        files.insert(HOSTILE_FILE.to_string(), ".".to_string());
        let manifest = hostile_manifest(&fragment_json(bucket, note_kind));
        validate_fixture_set(&manifest, &files, None)
            .expect_err("bucket/note_kind pairing must fail closed")
    };

    let error = run("abbrev-hier", "synthetic");
    assert!(
        error.contains("synthetic fragment must use bucket"),
        "expected synthetic-bucket rejection, got: {error}"
    );

    let error = run(SYNTHETIC_BUCKET, "enacting");
    assert!(
        error.contains("must not claim the synthetic bucket"),
        "expected corpus-bucket rejection, got: {error}"
    );
}

// ---------------------------------------------------------------------------
// T03 optional harvest audit (#[ignore]: decodes the 5.2 MB tracked XML —
// never runs in default CI). Every corpus fragment must be an exact substring
// of some decoded `ParsedBlock::text()`; synthetic fixtures are exempt.
// ---------------------------------------------------------------------------

#[test]
#[ignore = "decodes the 5.2 MB tracked 44-ФЗ XML on demand; not a CI test"]
fn ignored_harvest_audit_corpus_fragments_are_block_substrings() {
    let xml = repo_root().join(SOURCE_RELATIVE_PATH);
    let metadata = fs::metadata(&xml).expect("pinned corpus XML");
    assert_eq!(
        metadata.len(),
        SOURCE_BYTES,
        "pinned corpus XML length drifted"
    );
    let bytes = fs::read(&xml).expect("read pinned corpus XML");

    let request = DecodeRequest::new(
        PayloadRef::parse("payload:m197-s01-harvest-audit").expect("payload ref"),
        FamilyFormat::parse("family:consultant-wordml").expect("family format"),
        &bytes,
    );
    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("pinned corpus must decode");
    assert!(!blocks.is_empty(), "decoded corpus must emit blocks");

    let fragments = load_golden_fixtures(&fixtures_dir(), &repo_root())
        .expect("NPA golden fixtures must load fail-closed");
    let mut audited = 0usize;
    for fragment in &fragments {
        if fragment.note_kind == "synthetic" {
            continue;
        }
        assert!(
            blocks
                .iter()
                .any(|block| block.text().contains(&fragment.text)),
            "{} must be an exact substring of a decoded ParsedBlock",
            fragment.id
        );
        audited += 1;
    }
    assert!(
        audited >= 40,
        "harvest audit must cover the whole corpus (got {audited})"
    );
    eprintln!(
        "harvest audit: {audited} corpus fragments are block substrings; blocks={}",
        blocks.len()
    );
}

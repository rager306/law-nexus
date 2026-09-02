//! Contract tests for the C1 corpus-sweep harness
//! (M198-das7v8 S01, ADR-0028 step 2).
//!
//! T01 proofs cover the `npa_sweep` domain contract — lexer-driven
//! histogram, abbrev/D329/shapes census, D352 unknown tail, D353 hand-rolled
//! closed-schema JSONL, and the closed-key reader. T02 adds the measurement
//! plumbing: deterministic XML walker, bounded payload refs, per-file
//! decode+ingest, the library-level runner, and one thin-binary smoke.
//! Everything stays hermetic: temp dirs and inline WordML fixtures only —
//! the live `consru_export` corpus is never read by `cargo test` (the full
//! sweep is T03).

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use ln_decode::adapters::ConsultantWordMlBlockDecoder;
use ln_decode::domain::{
    DecodeRequest, FamilyFormat, ParagraphStyle, ParsedBlock, PayloadRef, SourceFormatId,
    SourceLocation, SourceSpan, SourceStreamId,
};
use ln_decode::lexer::{self, TokenKind};
use ln_decode::npa_sweep::{
    self, parse_args, run_sweep, walk_xml_files, SweepAcc, SweepCli, EXIT_OK, EXIT_OUT_UNWRITABLE,
    EXIT_ROOT_MISSING,
};
use ln_decode::ports::BlockDecoderPort;

/// Closed kind set in `npa_support::TOKEN_KINDS` order (S01 canon).
const KINDS: [TokenKind; 9] = [
    TokenKind::Word,
    TokenKind::Abbrev,
    TokenKind::HierNum,
    TokenKind::Date,
    TokenKind::DocNo,
    TokenKind::EnumMarker,
    TokenKind::LawCode,
    TokenKind::Punct,
    TokenKind::Space,
];

/// The single sanctioned `ParsedBlock` constructor, exactly as the plan pins
/// it: owned text, no provider style id, synthetic whole-artifact location,
/// Consultant WordML format. `n = text.len()` keeps the span non-empty.
fn block(text: &str, style: ParagraphStyle) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse("artifact:whole").unwrap(),
            SourceSpan::try_new(0, text.len()).unwrap(),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .unwrap()
}

fn tail_lexemes(acc: &SweepAcc) -> Vec<String> {
    acc.unknown_tail_ranked()
        .into_iter()
        .map(|entry| entry.lexeme)
        .collect()
}

/// Proof 1: `Ч.` is an unknown-tail candidate (not the Abbrev `ch`), `ст.`
/// is the Abbrev `st` (never a tail entry), `1.1` is one HierNum, and the
/// D329-nine stays at zero for this draft-only sentence. Capitalized `Гл.`
/// lands in the tail while lowercase `гл.` is the Abbrev `gl` (D354 ids).
#[test]
fn proof1_abbrev_hiernum_and_unknown_tail_discrimination() {
    let mut acc = SweepAcc::new("t01/proof1");
    acc.ingest_text("Ч. 1.1 ст. 33");

    assert_eq!(acc.abbrev_hit("st"), 1, "ст. must count as Abbrev `st`");
    assert_eq!(acc.kind_count(TokenKind::HierNum), 1, "1.1 is one HierNum");
    for id in npa_sweep::D329_NINE_IDS {
        assert_eq!(acc.d329_hit(id), 0, "D329 id `{id}` must stay zero");
    }
    let tail = tail_lexemes(&acc);
    assert!(
        tail.contains(&"Ч".to_string()),
        "capital `Ч` must be an unknown-tail candidate, got {tail:?}"
    );
    assert!(
        !tail.iter().any(|lexeme| lexeme == "ч"),
        "lowercase `ч` was never ingested"
    );
    assert!(
        !tail.iter().any(|lexeme| lexeme.starts_with("ст")),
        "Abbrev `ст.` must never enter the unknown tail, got {tail:?}"
    );

    // Same discriminator on the `Гл.` / `гл.` pair, isolated accumulator so
    // the D329-zero assertion above stays independent.
    let mut acc = SweepAcc::new("t01/proof1-gl");
    acc.ingest_text("Гл. 2 гл. 3");
    let tail = tail_lexemes(&acc);
    assert!(
        tail.contains(&"Гл".to_string()),
        "capital `Гл.` must be a tail candidate (no capitalized lexeme exists), got {tail:?}"
    );
    assert!(
        !tail.iter().any(|lexeme| lexeme == "гл"),
        "Abbrev `гл.` must never enter the tail, got {tail:?}"
    );
    assert_eq!(acc.abbrev_hit("gl"), 1);
    assert_eq!(acc.d329_hit("gl"), 1, "gl is one of the D329-nine");
}

/// Proof 2: the histogram over the tracked `syn-001.txt` golden equals a
/// reference histogram computed by calling `lex()` on the very same text.
#[test]
fn proof2_histogram_matches_reference_lex_on_syn001() {
    let golden = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa/syn-001.txt");
    let text = fs::read_to_string(&golden).expect("tracked syn-001.txt golden must be readable");

    let mut reference: BTreeMap<&'static str, u64> = BTreeMap::new();
    for token in lexer::lex(&text) {
        *reference.entry(token.kind.as_str()).or_insert(0) += 1;
    }

    let mut acc = SweepAcc::new("t01/proof2");
    acc.ingest_text(&text);
    for kind in KINDS {
        let expected = reference.get(kind.as_str()).copied().unwrap_or(0);
        assert_eq!(
            acc.kind_count(kind),
            expected,
            "kind {} diverges from the reference `lex()` histogram",
            kind.as_str()
        );
    }
    assert_eq!(
        acc.word_tokens(),
        reference.get("Word").copied().unwrap_or(0)
    );

    let rendered = acc.render_jsonl();
    npa_sweep::validate_jsonl(&rendered).expect("render over syn-001 must validate closed");
}

/// Proof 3: no raw legal sentence survives into the JSONL as a string value
/// — the only human-readable lexemes are 1..=6-letter tail candidates, and
/// none of the syn-001 words qualify (each is followed by Space, not `.`).
#[test]
fn proof3_no_raw_sentence_in_rendered_jsonl() {
    let sentence = "Синтетическая коллизия: пункт 15.1 действует до 01.01.2028.";
    let mut acc = SweepAcc::new("t01/proof3");
    acc.ingest_text(sentence);
    assert!(acc.unknown_tail_ranked().is_empty());
    let rendered = acc.render_jsonl();
    for fragment in [
        "Синтетическая",
        "коллизия",
        "пункт",
        "действует",
        "01.01.2028",
    ] {
        assert!(
            !rendered.contains(fragment),
            "raw legal text `{fragment}` leaked into the aggregate JSONL"
        );
    }
}

/// Proof 4: empty input renders eight closed-schema records of zeros
/// without panicking (empty text goes through `ingest_text`; `ParsedBlock`
/// rejects empty text by contract, so no block path is exercised here).
#[test]
fn proof4_empty_input_renders_zeroed_valid_jsonl() {
    let mut acc = SweepAcc::new("t01/proof4");
    acc.ingest_text("");
    assert_eq!(acc.word_tokens(), 0);
    assert_eq!(acc.marker_hits(), 0);
    assert_eq!(acc.marker_coverage_ppm(), 0);
    let rendered = acc.render_jsonl();
    assert_eq!(
        rendered.lines().count(),
        8,
        "exactly eight record_kind objects, one per line"
    );
    npa_sweep::validate_jsonl(&rendered)
        .expect("zeroed aggregate must still be closed-schema valid JSONL");
    assert!(rendered.contains("\"record_kind\":\"abbrev_hits\",\"st\":0"));
    assert!(rendered.contains("\"record_kind\":\"d329\",\"gl\":0"));
}

/// Proof 5: the closed-key reader fails on an unexpected key and on an
/// unknown record_kind — the aggregate reader never grows by accident.
#[test]
fn proof5_closed_key_reader_fails_on_extra_key() {
    let mut acc = SweepAcc::new("t01/proof5");
    acc.ingest_text("Ч. 1");
    let rendered = acc.render_jsonl();
    npa_sweep::validate_jsonl(&rendered).expect("baseline render must validate");

    let poisoned = rendered.replace(
        "\"record_kind\":\"totals\",\"files_seen\"",
        "\"record_kind\":\"totals\",\"rogue_key\":1,\"files_seen\"",
    );
    assert_ne!(poisoned, rendered, "mutation must actually apply");
    assert!(
        npa_sweep::validate_jsonl(&poisoned).is_err(),
        "an extra totals key must fail closed"
    );

    let unknown_kind = rendered.replace("\"record_kind\":\"d329\"", "\"record_kind\":\"d330\"");
    assert!(
        npa_sweep::validate_jsonl(&unknown_kind).is_err(),
        "an unknown record_kind must fail closed"
    );
}

/// Proof 6: `ProviderComment` blocks still feed kind/abbrev/shape/markers
/// counting but never mint unknown-tail candidates (the `rank_unknown_forms`
/// suppression pattern); the same text under `BodyText` does.
#[test]
fn proof6_provider_comment_suppresses_unknown_tail_only() {
    let mut acc = SweepAcc::new("t01/proof6-pc");
    acc.ingest_blocks("npa", &[block("Ч. 1", ParagraphStyle::ProviderComment)]);
    assert!(
        tail_lexemes(&acc).is_empty(),
        "ProviderComment must not mint tail candidates"
    );
    assert_eq!(
        acc.word_tokens(),
        2,
        "ProviderComment still feeds kind counting: `Ч` and `1` are both Word tokens"
    );
    assert_eq!(acc.kind_count(TokenKind::Punct), 1, "kinds still count");

    let mut acc = SweepAcc::new("t01/proof6-mix");
    acc.ingest_blocks(
        "npa",
        &[
            block("Ч. 1", ParagraphStyle::ProviderComment),
            block("Ч. 1", ParagraphStyle::BodyText),
        ],
    );
    let tail = acc.unknown_tail_ranked();
    assert_eq!(tail.len(), 1, "only the BodyText copy may enter the tail");
    assert_eq!(tail[0].lexeme, "Ч");
    assert_eq!(tail[0].count, 1);
}

/// File accounting and the pure family router: `note_file` feeds the totals
/// triple and `family_split`, and `family_from_path` resolves the component
/// under `exports/` without touching the filesystem.
#[test]
fn note_file_family_split_and_path_family() {
    let mut acc = SweepAcc::new("t01/files");
    acc.note_file("npa", true);
    acc.note_file("npa", false);
    acc.note_file("courts", true);
    assert_eq!(acc.files_seen(), 3);
    assert_eq!(acc.files_decoded(), 2);
    assert_eq!(acc.files_failed(), 1);

    let rendered = acc.render_jsonl();
    npa_sweep::validate_jsonl(&rendered).expect("family accounting must render valid JSONL");
    assert!(rendered.contains("\"files_seen\":3,\"files_decoded\":2,\"files_failed\":1"));
    assert!(rendered.contains("\"npa\":{\"seen\":2,\"decoded\":1,\"failed\":1}"));
    assert!(rendered.contains("\"courts\":{\"seen\":1,\"decoded\":1,\"failed\":0}"));

    for (path, family) in [
        ("consru_export/consru_export/exports/npa/a.xml", "npa"),
        ("exports/xml/b.xml", "xml"),
        ("/data/exports/courts/c.xml", "courts"),
        ("exports/fas/d.xml", "fas"),
        ("exports/e.xml", "other"),
        ("elsewhere/npa/f.xml", "other"),
        ("exports/garant/g.xml", "other"),
    ] {
        assert_eq!(
            npa_sweep::family_from_path(Path::new(path)),
            family,
            "family routing for `{path}`"
        );
    }
}

// ---------------------------------------------------------------------------
// T02: walker, payload identity, per-file decode+ingest, library-level
// runner, and one thin-binary smoke. Hermetic: temp dirs + inline WordML
// only; the live `consru_export` corpus is never read by `cargo test`.
// ---------------------------------------------------------------------------

/// Minimal inline WordML fixture, same shape as the decoder contract tests.
fn wordml_document(text: &str) -> String {
    format!(
        r#"<w:wordDocument xmlns:w="urn:word"><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:wordDocument>"#
    )
}

/// Unique per-test temp root; pre-cleaned so reruns start empty.
fn temp_root(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("npa-sweep-t02-{}-{tag}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("temp sweep root must be creatable");
    dir
}

fn write_xml(root: &Path, relative: &str, text: &str) -> PathBuf {
    let path = root.join(relative);
    fs::create_dir_all(path.parent().expect("relative parent exists")).expect("fixture dir");
    fs::write(&path, wordml_document(text)).expect("fixture xml");
    path
}

const ABSENT: &str = "/npa-sweep-t02-absent-root";

/// T02: decoded Consultant WordML feeds the covering M197 lexer — `ст.` is
/// the Abbrev `st`, `15.1` is one HierNum, a Space is present, and no raw
/// block text reaches the rendered aggregate (Q3).
#[test]
fn t02_inline_wordml_decode_feeds_lexer_census() {
    let xml = wordml_document("ст. 15.1");
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:t02-inline").unwrap(),
        FamilyFormat::parse("family:consultant-wordml").unwrap(),
        xml.as_bytes(),
    );
    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("inline WordML must decode");

    let mut acc = SweepAcc::new("t02/inline");
    acc.ingest_blocks("npa", &blocks);
    assert_eq!(acc.abbrev_hit("st"), 1, "ст. must be the Abbrev `st`");
    assert_eq!(acc.kind_count(TokenKind::HierNum), 1, "15.1 is one HierNum");
    assert!(
        acc.kind_count(TokenKind::Space) >= 1,
        "a Space token is lexed"
    );
    assert_eq!(
        acc.kind_count(TokenKind::Word),
        0,
        "no Word tokens in this text"
    );

    let rendered = acc.render_jsonl();
    npa_sweep::validate_jsonl(&rendered).expect("decoded blocks render closed JSONL");
    assert!(!rendered.contains("ст."), "block text must never leak");
}

/// T02: truncated WordML fails atomically per file — `files_failed` counts
/// it, the walk continues, and neither block text nor payload identity
/// reaches the rendered JSONL (Q7).
#[test]
fn t02_truncated_xml_counts_failed_and_leaks_nothing() {
    let root = temp_root("truncated");
    let dir = root.join("exports/xml");
    fs::create_dir_all(&dir).expect("exports/xml dir");
    let path = dir.join("broken.xml");
    fs::write(
        &path,
        r#"<w:wordDocument xmlns:w="urn:word"><w:p><w:r><w:t>Сломан"#,
    )
    .expect("truncated fixture");

    let mut acc = SweepAcc::new("t02/truncated");
    npa_sweep::ingest_file(&mut acc, &path);

    assert_eq!(acc.files_seen(), 1);
    assert_eq!(acc.files_decoded(), 0);
    assert_eq!(acc.files_failed(), 1);
    assert_eq!(acc.word_tokens(), 0, "failed files ingest no tokens");
    let rendered = acc.render_jsonl();
    npa_sweep::validate_jsonl(&rendered).expect("failed files still render closed JSONL");
    assert!(
        rendered.contains("\"xml\":{\"seen\":1,\"decoded\":0,\"failed\":1}"),
        "family still routed from the path on failure"
    );
    assert!(!rendered.contains("Сломан"), "block text must never leak");
    assert!(
        !rendered.contains("broken"),
        "raw file names must never leak"
    );
    assert!(
        !rendered.contains("payload:"),
        "payload refs must never leak"
    );

    fs::remove_dir_all(&root).ok();
}

/// T02: the walker sees exactly the `*.xml` leaves (case-insensitive), in
/// deterministic full-path sorted order with `.txt` skipped;
/// `family_from_path` routes both families into `family_split`; `--limit`
/// cuts after the sort.
#[test]
fn t02_walker_deterministic_xml_only_and_family_split() {
    let root = temp_root("walker");
    let npa_path = write_xml(&root, "exports/npa/a.xml", "ст. 1");
    let fas_path = write_xml(&root, "exports/fas/b.XML", "ст. 2");
    fs::write(root.join("notes.txt"), b"not xml").expect("txt fixture");

    let found = walk_xml_files(&root, None).expect("walk must succeed");
    assert_eq!(
        found,
        vec![fas_path.clone(), npa_path],
        "full-path sorted, `.txt` skipped, `.XML` kept"
    );

    let mut acc = SweepAcc::new("t02/walker");
    for path in &found {
        npa_sweep::ingest_file(&mut acc, path);
    }
    assert_eq!(acc.files_seen(), 2);
    assert_eq!(acc.files_decoded(), 2);
    assert_eq!(acc.files_failed(), 0);
    assert_eq!(acc.abbrev_hit("st"), 2, "one `ст.` per decoded act");
    assert_eq!(acc.word_tokens(), 2, "the trailing `1`/`2` are Word tokens");
    let rendered = acc.render_jsonl();
    npa_sweep::validate_jsonl(&rendered).expect("closed schema");
    assert!(rendered.contains("\"npa\":{\"seen\":1,\"decoded\":1,\"failed\":0}"));
    assert!(rendered.contains("\"fas\":{\"seen\":1,\"decoded\":1,\"failed\":0}"));
    assert!(!rendered.contains("txt"), "non-xml files are never seen");

    let limited = walk_xml_files(&root, Some(1)).expect("walk must succeed");
    assert_eq!(limited, vec![fas_path], "the limit cuts after the sort");

    fs::remove_dir_all(&root).ok();
}

/// T02: payload identity stays bounded (Q3) — short ASCII stems keep
/// `payload:<stem>`; long or non-ASCII stems fall back to the 19-char
/// `sw:`+hex FNV-1a tail, deterministically.
#[test]
fn t02_payload_ref_bounded_short_stem_and_fallback() {
    let short =
        npa_sweep::payload_ref_for_path(Path::new("/data/exports/npa/law_2013-04-05_44-fz.xml"));
    assert_eq!(short.as_str(), "payload:law_2013-04-05_44-fz");

    let long_stem =
        "federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii";
    let long_path = Path::new("/data/exports/npa").join(format!("{long_stem}.xml"));
    let long = npa_sweep::payload_ref_for_path(&long_path);
    assert!(
        long.as_str().starts_with("sw:"),
        "long stems fall back, got {}",
        long.as_str()
    );
    assert!(
        long.as_str().len() <= 64,
        "Q3: payload refs stay inside the 64 cap"
    );
    assert_eq!(
        long,
        npa_sweep::payload_ref_for_path(&long_path),
        "fallback identity is deterministic"
    );

    let cyrillic = npa_sweep::payload_ref_for_path(Path::new("/data/exports/xml/закон.xml"));
    assert!(cyrillic.as_str().starts_with("sw:"));
    assert_ne!(cyrillic, long, "different paths hash to different ids");
}

/// T02: strict stdlib argv parse — full flag set, defaults, and the
/// negative surface (garbled/negative limit, missing value, positional,
/// unknown flag).
#[test]
fn t02_parse_args_contract() {
    let cli = parse_args(
        [
            "--root", "/r", "--out", "/o", "--limit", "7", "--cycle", "cycle-x",
        ]
        .into_iter()
        .map(String::from),
    )
    .expect("full flag set parses");
    assert_eq!(
        cli,
        SweepCli {
            root: Some("/r".to_owned()),
            out: Some("/o".to_owned()),
            limit: Some(7),
            cycle: "cycle-x".to_owned(),
        }
    );

    let cli = parse_args(std::iter::empty::<String>()).expect("no args is the default run");
    assert_eq!(cli, SweepCli::default());
    assert_eq!(cli.cycle, "C1");
    assert_eq!(cli.limit, None);

    for bad in [
        vec!["--limit", "x"],
        vec!["--limit", "-1"],
        vec!["--root"],
        vec!["stray"],
        vec!["--waldo"],
    ] {
        assert!(
            parse_args(bad.into_iter().map(String::from)).is_err(),
            "usage error expected"
        );
    }
}

/// T02: `CONSULTANT_EXPORT_DIR` is empty-as-unset (M185 S03 pattern),
/// pinned purely without touching process env.
#[test]
fn t02_export_dir_empty_as_unset() {
    assert_eq!(npa_sweep::resolve_export_dir(None), "consru_export");
    assert_eq!(npa_sweep::resolve_export_dir(Some("")), "consru_export");
    assert_eq!(npa_sweep::resolve_export_dir(Some("   ")), "consru_export");
    assert_eq!(
        npa_sweep::resolve_export_dir(Some("/data/consultant-export")),
        "/data/consultant-export"
    );
}

/// T02: `--limit 0` over an existing root is a valid empty walk (exit 0,
/// header + zeros, `files_seen` 0); an explicit missing `--root` is a
/// definite non-zero exit outside skip-mode.
#[test]
fn t02_run_sweep_limit_zero_and_explicit_missing_root() {
    let root = temp_root("limit0");
    write_xml(&root, "exports/npa/a.xml", "ст. 3");
    let cli = SweepCli {
        root: Some(root.to_string_lossy().into_owned()),
        limit: Some(0),
        ..SweepCli::default()
    };
    let run = run_sweep(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    let jsonl = run.jsonl.expect("empty walk still renders the aggregate");
    assert!(jsonl.contains("\"record_kind\":\"header\""));
    assert!(jsonl.contains("\"files_seen\":0"));
    npa_sweep::validate_jsonl(&jsonl).expect("zeroed aggregate stays closed");
    assert!(run.stderr.contains("files_seen=0"));

    let cli = SweepCli {
        root: Some("/npa-sweep-t02-missing-explicit-root".to_owned()),
        ..SweepCli::default()
    };
    let run = run_sweep(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_ROOT_MISSING, "definite non-zero exit");
    assert!(run.jsonl.is_none());

    fs::remove_dir_all(&root).ok();
}

/// T02: a missing DEFAULT root is skip-mode — exit 0, zeroed aggregate, and
/// a stderr skip note; never a corpus abort.
#[test]
fn t02_run_sweep_default_root_absent_is_skip_mode() {
    let run = run_sweep(&SweepCli::default(), Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    let jsonl = run.jsonl.expect("skip-mode still renders the aggregate");
    assert!(jsonl.contains("\"files_seen\":0"));
    npa_sweep::validate_jsonl(&jsonl).expect("zeroed aggregate stays closed");
    assert!(
        run.stderr.contains("skip"),
        "skip note on stderr: {}",
        run.stderr
    );
    assert!(run.to_stdout);
}

/// T02: `--out` receives `render_jsonl` (nothing on stdout); an unwritable
/// `--out` is a definite non-zero exit with no aggregate.
#[test]
fn t02_run_sweep_out_write_and_open_failure() {
    let root = temp_root("out");
    write_xml(&root, "exports/npa/a.xml", "ст. 9");
    let out_path = root.join("aggregate.jsonl");

    let cli = SweepCli {
        root: Some(root.to_string_lossy().into_owned()),
        out: Some(out_path.to_string_lossy().into_owned()),
        ..SweepCli::default()
    };
    let run = run_sweep(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    assert!(
        run.jsonl.is_none() && !run.to_stdout,
        "file mode prints no stdout JSONL"
    );
    assert!(run.stderr.contains("files_seen=1"));
    let written = fs::read_to_string(&out_path).expect("aggregate file written");
    npa_sweep::validate_jsonl(&written).expect("file aggregate stays closed");
    assert!(written.contains("\"files_seen\":1"));

    let cli = SweepCli {
        root: Some(root.to_string_lossy().into_owned()),
        out: Some(
            root.join("missing-dir/aggregate.jsonl")
                .to_string_lossy()
                .into_owned(),
        ),
        ..SweepCli::default()
    };
    let run = run_sweep(&cli, Path::new(ABSENT));
    assert_eq!(
        run.exit_code, EXIT_OUT_UNWRITABLE,
        "unopenable --out is fatal"
    );
    assert!(run.jsonl.is_none());

    fs::remove_dir_all(&root).ok();
}

/// T02: the single sanctioned `Command` smoke — the real thin binary on
/// `--limit 0` (valid empty walk, exit 0, header on stdout, counts on
/// stderr). The main contract stays library-level.
#[test]
fn t02_bin_smoke_limit_zero() {
    let root = temp_root("smoke");
    let output = Command::new(env!("CARGO_BIN_EXE_npa-corpus-sweep"))
        .arg("--limit")
        .arg("0")
        .arg("--root")
        .arg(&root)
        .output()
        .expect("binary must run");
    assert!(output.status.success(), "--limit 0 is a valid empty walk");
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        stdout.contains("\"record_kind\":\"header\""),
        "header on stdout"
    );
    assert!(stdout.contains("\"files_seen\":0"));
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("files_seen=0"),
        "counts on stderr"
    );
    fs::remove_dir_all(&root).ok();
}

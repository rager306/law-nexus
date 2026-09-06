//! T03 contract (M200-8s4kwq S01): the `npa-bounds-scan/v1` sibling
//! measurement profile accumulated over the T02 observation seam.
//!
//! T04 (S02) pins the tracked full-corpus artifact: the persisted
//! `npa-bounds-scan/v1` JSONL must keep validating against the closed
//! schema reader with terminal completeness against the independent walk,
//! direct/proxy separation, deterministic hashes, ASCII-only redaction,
//! honest clock/progress metadata, bounded top-K anchors, and
//! diagnostic-only non-claims (tests never open consru_export).
//!
//! Pinned here (profile `fixture_acceptance`): production-API reuse through
//! the seam (decoder / lexer / capture oracles), span-relation oracle
//! equality, malformed atomicity with zero partial measurement, the
//! unreadable/malformed split, byte-identical repeated normalized output,
//! closed-key schema validation, `proxy_*` namespace separation, absence of
//! raw legal text, explicit unavailability of runtime-declared metrics
//! drift-pinned against the tracked profile, the bounded top-K scaffold,
//! and the deterministic skip-mode / limit-0 / missing-root runner
//! behavior.

use std::fs;
use std::path::{Path, PathBuf};

use ln_decode::adapters::ConsultantWordMlBlockDecoder;
use ln_decode::domain::{DecodeRequest, FamilyFormat};
use ln_decode::lawref::capture_lawrefs;
use ln_decode::lexer::{self, TokenKind};
use ln_decode::npa_bounds::{
    block_opens_list_surface, block_opens_with_date_docno, count_date_docno_pairs,
    count_word_surfaces, normalized_pattern_label, run_bounds_scan, span_relation,
    tracked_profile_hash, validate_bounds_jsonl, BoundsAcc, BoundsCli, BoundsRunMeta, MetricStat,
    SpanRelation, ALIAS_SURFACE_WORD, DEFERRED_PROXY_SUBMETRICS, PATTERN_LABELS,
    TOP_K_SCAFFOLD_CAP, UNAVAILABLE_METRICS,
};
use ln_decode::npa_sweep::{payload_ref_for_path, walk_and_observe, EXIT_OK, EXIT_ROOT_MISSING};
use ln_decode::ports::BlockDecoderPort;

const ABSENT: &str = "/npa-bounds-t03-absent-root";

/// Minimal Consultant WordML fixture: one paragraph per `&str` entry.
fn wordml_document(paragraphs: &[&str]) -> String {
    let body = paragraphs
        .iter()
        .map(|text| format!("<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"))
        .collect::<String>();
    format!("<w:wordDocument xmlns:w=\"urn:word\">{body}</w:wordDocument>")
}

/// Unique per-test temp root; pre-cleaned so reruns start empty.
fn temp_root(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("npa-bounds-t03-{}-{tag}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("temp bounds root must be creatable");
    dir
}

fn write_xml(root: &Path, relative: &str, paragraphs: &[&str]) -> PathBuf {
    let path = root.join(relative);
    fs::create_dir_all(path.parent().expect("relative parent exists")).expect("fixture dir");
    fs::write(&path, wordml_document(paragraphs)).expect("fixture xml");
    path
}

/// Deterministic run metadata: fixed clock + revision so renders are
/// byte-stable across repeated runs in the same tree.
fn test_meta(root: &Path) -> BoundsRunMeta {
    let mut meta = BoundsRunMeta::new(root.to_string_lossy().into_owned());
    meta.started_at = Some("2026-09-05T00:00:00Z".to_owned());
    meta.ended_at = Some("2026-09-05T00:00:01Z".to_owned());
    meta.source_revision = Some("sha256:t03-fixture".to_owned());
    meta.rust_toolchain = Some("rustc 1.00.0-t03-fixture".to_owned());
    meta
}

/// Full seam walk into a fresh accumulator (the production path the thin
/// CLI drives).
fn scan_root(root: &Path) -> BoundsAcc {
    let mut acc = BoundsAcc::new(root, test_meta(root));
    walk_and_observe(root, None, &mut acc).expect("walk must succeed");
    acc
}

/// Production-decoder oracle over the same fixture bytes.
fn oracle_block_texts(path: &Path) -> Vec<String> {
    let bytes = fs::read(path).expect("oracle reads the same fixture");
    let request = DecodeRequest::new(
        payload_ref_for_path(path),
        FamilyFormat::parse("family:consultant-wordml").expect("static family format"),
        &bytes,
    );
    ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("fixture decodes through the production decoder")
        .iter()
        .map(|block| block.text().to_owned())
        .collect()
}

/// Test-local fixed kind order (independent oracle ordering).
fn kind_slot(kind: TokenKind) -> usize {
    match kind {
        TokenKind::Word => 0,
        TokenKind::Abbrev => 1,
        TokenKind::HierNum => 2,
        TokenKind::Date => 3,
        TokenKind::DocNo => 4,
        TokenKind::EnumMarker => 5,
        TokenKind::LawCode => 6,
        TokenKind::Punct => 7,
        TokenKind::Space => 8,
    }
}

fn span_slot(relation: SpanRelation) -> usize {
    match relation {
        SpanRelation::Exact => 0,
        SpanRelation::Containment => 1,
        SpanRelation::PartialOverlap => 2,
        SpanRelation::Disjoint => 3,
    }
}

fn all_kinds() -> [TokenKind; 9] {
    [
        TokenKind::Word,
        TokenKind::Abbrev,
        TokenKind::HierNum,
        TokenKind::Date,
        TokenKind::DocNo,
        TokenKind::EnumMarker,
        TokenKind::LawCode,
        TokenKind::Punct,
        TokenKind::Space,
    ]
}

/// T03: direct metrics equal direct production calls — the accumulated
/// decode accounting, covering-lexer census, and capture volume match an
/// independent decode + `lexer::lex` + `capture_lawrefs` oracle.
#[test]
fn t03_direct_metrics_match_production_oracle() {
    let root = temp_root("oracle");
    let a = write_xml(
        &root,
        "exports/npa/a.xml",
        &["ст. 15.1", "01.02.2003 65-ФЗ"],
    );
    let b = write_xml(
        &root,
        "exports/npa/b.xml",
        &["в ред. от 03.04.1999 77-ФЗ и «а»"],
    );

    let acc = scan_root(&root);
    assert_eq!(acc.files_attempted(), 2);
    assert_eq!(acc.files_decoded(), 2);
    assert_eq!(acc.malformed_count(), 0);
    assert_eq!(acc.unreadable_count(), 0);
    assert_eq!(acc.documents_total(), 2);

    let mut blocks = 0u64;
    let mut exp_tokens = 0u64;
    let mut exp_candidates = 0u64;
    let mut kind_totals = [0u64; 9];
    for path in [&a, &b] {
        for text in oracle_block_texts(path) {
            blocks += 1;
            let tokens = lexer::lex(&text);
            exp_tokens += tokens.len() as u64;
            for token in &tokens {
                kind_totals[kind_slot(token.kind)] += 1;
            }
            exp_candidates += capture_lawrefs(&text).len() as u64;
        }
    }
    assert_eq!(acc.blocks_total(), blocks);
    assert_eq!(acc.tokens_total(), exp_tokens);
    assert_eq!(acc.candidates_total(), exp_candidates);
    assert_eq!(
        acc.coverage_failures(),
        0,
        "covering token concatenation equals every decoded block text"
    );
    for kind in all_kinds() {
        assert_eq!(
            acc.kind_count(kind),
            kind_totals[kind_slot(kind)],
            "token kind {kind:?}"
        );
    }

    let token_stat = acc
        .metric_stat("tokens_per_block")
        .expect("tokens_per_block observed");
    assert_eq!(token_stat.count, blocks);
    assert!(
        token_stat.min >= 1,
        "every decoded block lexes to >= 1 token"
    );
    let doc_blocks = acc
        .metric_stat("blocks_per_document")
        .expect("blocks_per_document observed");
    assert_eq!(doc_blocks.count, 2);
    let doc_candidates = acc
        .metric_stat("candidates_per_document")
        .expect("candidates_per_document observed");
    assert_eq!(doc_candidates.count, 2);

    let output = acc.render_jsonl();
    validate_bounds_jsonl(&output).expect("the aggregate stays inside the closed schema");
    assert!(output.contains("\"coverage_failures\":0"));

    fs::remove_dir_all(&root).ok();
}

/// T03: span-pair relation counters equal a brute-force pairwise oracle
/// over the same production captures; the pure classifier is pinned on all
/// four relations (exact, containment both directions, partial overlap,
/// disjoint).
#[test]
fn t03_span_relations_match_pairwise_oracle() {
    assert_eq!(span_relation((0, 5), (0, 5)), SpanRelation::Exact);
    assert_eq!(span_relation((0, 10), (2, 5)), SpanRelation::Containment);
    assert_eq!(span_relation((2, 5), (0, 10)), SpanRelation::Containment);
    assert_eq!(span_relation((0, 5), (3, 8)), SpanRelation::PartialOverlap);
    assert_eq!(span_relation((0, 3), (4, 8)), SpanRelation::Disjoint);

    let root = temp_root("spans");
    let a = write_xml(
        &root,
        "exports/npa/a.xml",
        &[
            // date-docno-window + abbrev-hier-chain: two disjoint captures.
            "от 01.02.2003 65-ФЗ и ст. 15.1",
            // One collapsed chain candidate: no pair from this block.
            "ст. 15.1 ст. 16",
            // amendment window (when "ред" is allowlisted) swallows the
            // inner date-docno by the layer-B containment policy — the
            // oracle recomputes whichever candidates survive.
            "в ред. от 01.02.2003 65-ФЗ",
        ],
    );

    let acc = scan_root(&root);
    let mut expected = [0u64; 4];
    for text in oracle_block_texts(&a) {
        let candidates = capture_lawrefs(&text);
        for left in 0..candidates.len() {
            for right in (left + 1)..candidates.len() {
                let l = candidates[left].span;
                let r = candidates[right].span;
                expected[span_slot(span_relation((l.start(), l.end()), (r.start(), r.end())))] += 1;
            }
        }
    }
    let total_pairs: u64 = expected.iter().sum();
    assert!(total_pairs >= 1, "fixture must produce candidate pairs");

    for (slot, relation) in [
        (0usize, SpanRelation::Exact),
        (1, SpanRelation::Containment),
        (2, SpanRelation::PartialOverlap),
        (3, SpanRelation::Disjoint),
    ] {
        assert_eq!(
            acc.span_total(relation),
            expected[slot],
            "span relation {relation:?}"
        );
    }

    fs::remove_dir_all(&root).ok();
}

/// T03: `candidates_by_pattern` counts equal the oracle sum over the seven
/// normalized labels mapped from production pattern ids; the mapping table
/// is closed and nothing is unmapped on production captures.
#[test]
fn t03_candidates_by_pattern_match_oracle() {
    let labels: Vec<&str> = PATTERN_LABELS.iter().map(|(label, _)| *label).collect();
    assert_eq!(
        labels,
        [
            "abbrev-hier-chain",
            "amendment-window",
            "date-docno",
            "fullword",
            "quoted-enum",
            "range",
            "anaphora"
        ]
    );
    assert_eq!(
        normalized_pattern_label("abbrev-hier-chain"),
        Some("abbrev-hier-chain")
    );
    assert_eq!(
        normalized_pattern_label("date-docno-window"),
        Some("date-docno")
    );
    assert_eq!(normalized_pattern_label("range_candidate"), Some("range"));
    assert_eq!(
        normalized_pattern_label("anaphora_candidate"),
        Some("anaphora")
    );
    assert_eq!(normalized_pattern_label("unknown-pattern"), None);

    let root = temp_root("patterns");
    let a = write_xml(
        &root,
        "exports/npa/a.xml",
        &["ст. 15.1", "01.02.2003 65-ФЗ", "от 1.1 до 4.1"],
    );

    let acc = scan_root(&root);
    let texts = oracle_block_texts(&a);
    let mut labels_with_hits = 0usize;
    for (label, _) in PATTERN_LABELS {
        let mut expected = 0u64;
        for text in &texts {
            expected += capture_lawrefs(text)
                .iter()
                .filter(|candidate| normalized_pattern_label(&candidate.pattern_id) == Some(label))
                .count() as u64;
        }
        assert_eq!(acc.pattern_total(label), expected, "pattern label {label}");
        if expected > 0 {
            labels_with_hits += 1;
        }
    }
    assert!(
        labels_with_hits >= 2,
        "fixture must fire at least two production patterns"
    );
    assert_eq!(acc.pattern_unmapped(), 0, "production captures are mapped");

    fs::remove_dir_all(&root).ok();
}

/// T03: every lexical proxy equals a recomputation through the pure,
/// published helper predicates over the same production lexes and captures.
#[test]
fn t03_lexical_proxies_measure_declared_surfaces() {
    let root = temp_root("proxies");
    let a = write_xml(
        &root,
        "exports/npa/a.xml",
        &["ст. 15.1", "01.02.2003 65-ФЗ далее"],
    );
    let b = write_xml(&root, "exports/npa/b.xml", &["01.02.2003 65-ФЗ"]);

    let acc = scan_root(&root);

    let mut pair_values = Vec::new();
    let mut range_values = Vec::new();
    let mut alias_per_doc = Vec::new();
    let mut tails_per_doc = Vec::new();
    for path in [&a, &b] {
        let texts = oracle_block_texts(path);
        let mut doc_alias = 0u64;
        let mut doc_tails = 0u64;
        let mut prev_opens_list = false;
        for text in &texts {
            let tokens = lexer::lex(text);
            let candidates = capture_lawrefs(text);
            pair_values.push(count_date_docno_pairs(&tokens));
            range_values.push(u64::from(
                candidates
                    .iter()
                    .any(|candidate| candidate.pattern_id == "range_candidate"),
            ));
            doc_alias += count_word_surfaces(&tokens, text, ALIAS_SURFACE_WORD);
            if prev_opens_list && block_opens_with_date_docno(&tokens) {
                doc_tails += 1;
            }
            prev_opens_list = block_opens_list_surface(&candidates);
        }
        alias_per_doc.push(doc_alias);
        tails_per_doc.push(doc_tails);
    }
    let expected_stat = |values: &[u64]| MetricStat {
        count: values.len() as u64,
        min: *values.iter().min().expect("non-empty values"),
        max: *values.iter().max().expect("non-empty values"),
    };
    assert_eq!(
        acc.metric_stat("proxy_date_docno_members_per_block"),
        Some(expected_stat(&pair_values))
    );
    assert_eq!(
        acc.metric_stat("proxy_structural_range_blocks_per_block"),
        Some(expected_stat(&range_values))
    );
    assert_eq!(
        acc.metric_stat("proxy_alias_surfaces_per_document"),
        Some(expected_stat(&alias_per_doc))
    );
    assert_eq!(
        acc.metric_stat("proxy_cross_block_tails_per_document"),
        Some(expected_stat(&tails_per_doc))
    );
    assert!(
        tails_per_doc.contains(&1),
        "fixture must produce one adjacent-block tail"
    );

    fs::remove_dir_all(&root).ok();
}

/// T03: malformed atomic failure — a truncated file is `malformed`, adds
/// zero blocks / candidates / metric observations, and its decoded sibling
/// is unaffected.
#[test]
fn t03_malformed_file_adds_zero_partial_measurement() {
    let root = temp_root("malformed");
    let ok = write_xml(&root, "exports/npa/ok.xml", &["ст. 15.1", "ст. 16.2"]);
    let broken = root.join("exports/npa/broken.xml");
    fs::write(
        &broken,
        "<w:wordDocument xmlns:w=\"urn:word\"><w:p><w:r><w:t>Сломан",
    )
    .expect("truncated fixture");

    let acc = scan_root(&root);
    assert_eq!(acc.files_attempted(), 2);
    assert_eq!(acc.files_decoded(), 1);
    assert_eq!(acc.malformed_count(), 1);
    assert_eq!(acc.unreadable_count(), 0);

    let expected_blocks = oracle_block_texts(&ok).len() as u64;
    let expected_candidates: u64 = oracle_block_texts(&ok)
        .iter()
        .map(|text| capture_lawrefs(text).len() as u64)
        .sum();
    assert_eq!(
        acc.blocks_total(),
        expected_blocks,
        "atomic failure contributes no blocks"
    );
    assert_eq!(acc.candidates_total(), expected_candidates);
    assert_eq!(
        acc.metric_stat("blocks_per_document")
            .map(|stat| stat.count),
        Some(1),
        "only the decoded document is observed"
    );

    let output = acc.render_jsonl();
    assert!(output.contains("\"malformed\":1"));
    assert!(output.contains("\"success_count\":1"));

    fs::remove_dir_all(&root).ok();
}

/// T03: the seam merges read and decode failures, so the accumulator
/// classifies them with a bounded probe read — a dangling symlink is
/// `unreadable`, a readable-but-undecodable file is `malformed`, and
/// success + malformed + unreadable equals files attempted.
#[test]
#[cfg(unix)]
fn t03_unreadable_and_malformed_are_distinguished() {
    let root = temp_root("unreadable");
    let dir = root.join("exports/xml");
    fs::create_dir_all(&dir).expect("exports/xml dir");
    let dead = dir.join("dead.xml");
    std::os::unix::fs::symlink("/npa-bounds-t03-no-such-target", &dead)
        .expect("dangling symlink fixture");
    let broken = root.join("exports/npa/broken.xml");
    fs::create_dir_all(broken.parent().expect("fixture dir")).expect("fixture dir");
    fs::write(&broken, "<w:wordDocument xmlns:w=\"urn:word\"><w:p>").expect("truncated fixture");

    let acc = scan_root(&root);
    assert_eq!(acc.files_attempted(), 2);
    assert_eq!(acc.files_decoded(), 0);
    assert_eq!(
        acc.malformed_count(),
        1,
        "readable-but-undecodable file is malformed"
    );
    assert_eq!(acc.unreadable_count(), 1, "unreadable file is unreadable");
    assert_eq!(acc.blocks_total(), 0);
    assert_eq!(
        acc.metric_stat("tokens_per_block"),
        None,
        "no observations without decoded blocks"
    );

    fs::remove_dir_all(&root).ok();
}

/// T03: repeated fixture runs produce byte-identical normalized JSON —
/// both for two fresh accumulator runs through the seam and for two thin
/// runner invocations with fixed clock metadata.
#[test]
fn t03_repeated_fixture_run_is_byte_identical() {
    let root = temp_root("identical");
    write_xml(
        &root,
        "exports/npa/a.xml",
        &["ст. 15.1", "01.02.2003 65-ФЗ"],
    );
    write_xml(&root, "exports/npa/b.xml", &["от 1.1 до 4.1"]);

    let first = scan_root(&root).render_jsonl();
    let second = scan_root(&root).render_jsonl();
    assert_eq!(
        first, second,
        "repeated accumulator runs are byte-identical"
    );

    let cli = BoundsCli {
        root: Some(root.to_string_lossy().into_owned()),
        started_at: Some("2026-09-05T00:00:00Z".to_owned()),
        ended_at: Some("2026-09-05T00:00:01Z".to_owned()),
        ..BoundsCli::default()
    };
    let run_one = run_bounds_scan(&cli, Path::new(ABSENT));
    let run_two = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run_one.exit_code, EXIT_OK);
    assert_eq!(
        run_one.jsonl, run_two.jsonl,
        "repeated runner runs are byte-identical"
    );

    fs::remove_dir_all(&root).ok();
}

/// T03: the closed-key reader accepts the aggregate and rejects unknown
/// record kinds and unknown keys on known records.
#[test]
fn t03_output_stays_closed_schema() {
    let root = temp_root("schema");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);
    let output = scan_root(&root).render_jsonl();
    validate_bounds_jsonl(&output).expect("the aggregate stays inside the closed schema");

    assert!(
        validate_bounds_jsonl("{\"record_kind\":\"header\",\"rogue\":1}").is_err(),
        "unknown key on a known record fails closed"
    );
    assert!(
        validate_bounds_jsonl("{\"record_kind\":\"not-a-record\"}").is_err(),
        "unknown record_kind fails closed"
    );
    assert!(
        validate_bounds_jsonl("{\"record_kind\":\"metric\",\"rogue\":1}").is_err(),
        "unknown key on a metric record fails closed"
    );

    fs::remove_dir_all(&root).ok();
}

/// T03: the aggregate carries hashes, relative paths, and byte spans only —
/// no raw legal text and no decoded block text survives into the output.
#[test]
fn t03_output_contains_no_raw_legal_text() {
    let root = temp_root("no-raw");
    let secret = "ТокенСекрета-42 подпункт «я»";
    write_xml(&root, "exports/npa/doc.xml", &["ст. 15.1", secret]);

    let output = scan_root(&root).render_jsonl();
    assert!(
        !output.contains("ТокенСекрета"),
        "no raw legal text in the aggregate"
    );
    assert!(!output.contains(secret));
    for text in oracle_block_texts(&root.join("exports/npa/doc.xml")) {
        let probe = text.trim();
        if probe.chars().count() >= 8 {
            assert!(
                !output.contains(probe),
                "decoded block text leaked into the aggregate"
            );
        }
    }

    fs::remove_dir_all(&root).ok();
}

/// T03: direct and proxy metrics are separated in schema — fixed metric
/// slots, `proxy_*` kinds namespaced `proxy`, direct kinds namespaced
/// `direct`, and the non-claims record repeated in the header.
#[test]
fn t03_proxy_metrics_namespaced_and_separated() {
    let root = temp_root("namespace");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);
    let output = scan_root(&root).render_jsonl();

    const METRIC_SLOTS: [(&str, &str); 8] = [
        ("blocks_per_document", "direct"),
        ("tokens_per_block", "direct"),
        ("candidates_per_block", "direct"),
        ("candidates_per_document", "direct"),
        ("proxy_date_docno_members_per_block", "proxy"),
        ("proxy_structural_range_blocks_per_block", "proxy"),
        ("proxy_alias_surfaces_per_document", "proxy"),
        ("proxy_cross_block_tails_per_document", "proxy"),
    ];
    for (kind, namespace) in METRIC_SLOTS {
        let marker = format!("\"metric_kind\":\"{kind}\",\"namespace\":\"{namespace}\"");
        assert!(output.contains(&marker), "missing {marker}");
    }
    assert!(
        output.contains(
            "\"non_claims\":[\"official-publication\",\"R070\",\"LawRef\",\"N2-gate\",\"semantic-frame\",\"bound-decision\"]"
        ),
        "proxies never count as semantic frames or bound decisions"
    );

    fs::remove_dir_all(&root).ok();
}

/// T03: the unavailable-until-runtime metrics, the deferred proxy
/// sub-metrics, and the deferred-undefined top-K row are pinned against the
/// tracked profile (drift fails the build) and are rendered explicitly.
#[test]
fn t03_unavailable_metrics_drift_pinned_to_profile() {
    let profile_path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("prd")
        .join("architecture")
        .join("npa-bounds-scanner-profile.yaml");
    let profile =
        fs::read_to_string(&profile_path).expect("tracked profile readable from the crate dir");
    for item in UNAVAILABLE_METRICS {
        assert!(
            profile.contains(item),
            "profile lost unavailable item: {item}"
        );
    }
    for item in DEFERRED_PROXY_SUBMETRICS {
        assert!(
            profile.contains(item),
            "profile lost deferred proxy sub-metric: {item}"
        );
    }
    assert!(profile.contains("top_k: deferred-undefined"));

    let root = temp_root("unavailable");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);
    let output = scan_root(&root).render_jsonl();
    for item in UNAVAILABLE_METRICS {
        assert!(
            output.contains(&format!("\"{item}\"")),
            "unavailable item not rendered: {item}"
        );
    }
    for item in DEFERRED_PROXY_SUBMETRICS {
        assert!(
            output.contains(&format!("\"{item}\"")),
            "deferred proxy sub-metric not rendered: {item}"
        );
    }
    assert!(output.contains("\"top_k\":\"deferred-undefined\""));

    fs::remove_dir_all(&root).ok();
}

/// T03: a missing default root is skip-mode — exit 0, zeroed closed
/// aggregate with a complete terminal manifest and source/profile hashes.
#[test]
fn t03_skip_mode_zeroed_manifest_complete() {
    let cli = BoundsCli {
        started_at: Some("2026-09-05T00:00:00Z".to_owned()),
        ended_at: Some("2026-09-05T00:00:01Z".to_owned()),
        ..BoundsCli::default()
    };
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    assert!(run.to_stdout);
    assert!(run.stderr.starts_with("skip:"));

    let jsonl = run.jsonl.expect("skip-mode still renders the aggregate");
    validate_bounds_jsonl(&jsonl).expect("zeroed aggregate stays closed");
    assert!(jsonl.contains("\"files_attempted\":0"));
    assert!(
        jsonl.contains("\"metric_kind\":\"tokens_per_block\",\"namespace\":\"direct\",\"count\":0")
    );
    assert!(jsonl.contains("\"observed_file_count\":0"));
    assert!(jsonl.contains("\"measurement_definitions_hash\":\"fnv1a64:"));
    assert!(jsonl.contains("\"scanner_source_hash\":\"fnv1a64:"));
    assert!(jsonl.contains("\"profile_hash\":\"fnv1a64:"));

    fs::remove_dir_all(ABSENT).ok();
}

/// T03: an explicit missing root is a hard root-missing exit with no
/// aggregate.
#[test]
fn t03_missing_explicit_root_exits_root_missing() {
    let cli = BoundsCli {
        root: Some(ABSENT.to_owned()),
        ..BoundsCli::default()
    };
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_ROOT_MISSING);
    assert!(run.jsonl.is_none());
    assert!(run.stderr.contains("root not found"));
}

/// T03: `limit = 0` is a valid empty scan — nothing is observed, totals
/// stay zero, and the aggregate still closes its schema.
#[test]
fn t03_limit_zero_walks_nothing() {
    let root = temp_root("limit0");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);
    let cli = BoundsCli {
        root: Some(root.to_string_lossy().into_owned()),
        limit: Some(0),
        ..BoundsCli::default()
    };
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    assert!(run.stderr.contains("files_attempted=0"));
    let jsonl = run.jsonl.expect("limit-0 run renders the aggregate");
    validate_bounds_jsonl(&jsonl).expect("closed schema");
    assert!(jsonl.contains("\"files_attempted\":0"));

    fs::remove_dir_all(&root).ok();
}

/// T03: the top-K outlier scaffold is bounded by its cap and the running
/// maximum is retained as an anchor value.
#[test]
fn t03_topk_scaffold_bounded() {
    let root = temp_root("topk");
    for index in 0..12u32 {
        let text = "слово ".repeat(index as usize + 1);
        let text = text.trim_end().to_owned();
        write_xml(
            &root,
            &format!("exports/npa/f{index:02}.xml"),
            &[text.as_str()],
        );
    }

    let acc = scan_root(&root);
    let stat = acc
        .metric_stat("tokens_per_block")
        .expect("tokens_per_block observed");
    assert_eq!(stat.count, 12);
    assert_eq!(
        acc.metric_anchor_len("tokens_per_block"),
        Some(TOP_K_SCAFFOLD_CAP),
        "scaffold retains at most the top-K cap"
    );
    assert_eq!(stat.max, 23, "the largest block is retained as the maximum");

    fs::remove_dir_all(&root).ok();
}

/// T01 (S02): `run_status` closes the manifest honestly — the terminal
/// render is `complete`, the interruption diagnostic renders `incomplete`
/// without a fabricated ended_at, and the manifest reader stays closed
/// against unknown keys.
#[test]
fn t01_run_status_complete_and_incomplete_stay_closed() {
    let root = temp_root("t01-run-status");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);

    // Terminal render: complete, closed, injected clock preserved verbatim.
    let complete = scan_root(&root).render_jsonl();
    validate_bounds_jsonl(&complete).expect("terminal render stays closed");
    assert!(complete.contains("\"run_status\":\"complete\""));
    assert!(complete.contains("\"ended_at\":\"2026-09-05T00:00:01Z\""));

    // Interruption diagnostic: incomplete, no fabricated clock, closed.
    let partial_acc = BoundsAcc::new(
        &root,
        BoundsRunMeta::new(root.to_string_lossy().into_owned()),
    );
    let partial = partial_acc.render_jsonl_incomplete();
    validate_bounds_jsonl(&partial).expect("incomplete diagnostic stays closed");
    assert!(partial.contains("\"run_status\":\"incomplete\""));
    assert!(partial.contains("\"ended_at\":null"));
    assert!(partial.contains("\"observed_file_count\":0"));

    // The manifest reader still rejects unknown keys (closed schema).
    let tampered = partial.replace(
        "\"run_status\":\"incomplete\"",
        "\"run_status\":\"incomplete\",\"bogus_key\":1",
    );
    let err = validate_bounds_jsonl(&tampered).expect_err("unknown manifest key fails closed");
    assert!(
        err.contains("bogus_key"),
        "the failure names the key: {err}"
    );

    fs::remove_dir_all(&root).ok();
}

/// T04 (S02): path of the tracked full-corpus artifact (persisted by the
/// T03 operator run and tracked in git; contract tests never open
/// consru_export).
fn tracked_corpus_artifact_path() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("prd")
        .join("migration")
        .join("rust-evidence")
        .join("m200-s02-npa-bounds-scan.jsonl")
}

fn tracked_corpus_artifact() -> String {
    fs::read_to_string(tracked_corpus_artifact_path())
        .expect("tracked full-corpus artifact readable")
}

/// T04: the tracked corpus artifact validates against the closed schema
/// reader and keeps its exact 15-record canonical order.
#[test]
fn t04_tracked_corpus_artifact_validates_closed_schema() {
    let jsonl = tracked_corpus_artifact();
    validate_bounds_jsonl(&jsonl)
        .expect("the tracked full-corpus artifact validates against the closed schema");

    assert_eq!(
        jsonl.lines().count(),
        15,
        "the closed schema stays exactly 15 records"
    );
    const RECORD_ORDER: [&str; 15] = [
        "header",
        "totals",
        "token_kind_histogram",
        "candidates_by_pattern",
        "span_relations",
        "metric",
        "metric",
        "metric",
        "metric",
        "metric",
        "metric",
        "metric",
        "metric",
        "unavailable",
        "run_manifest",
    ];
    for (line, kind) in jsonl.lines().zip(RECORD_ORDER) {
        let marker = format!("\"record_kind\":\"{kind}\"");
        assert!(
            line.contains(&marker),
            "record order drifted: expected {marker}"
        );
    }
    assert!(jsonl.contains("\"label\":\"corpus-scan\""));
    assert!(jsonl.contains("\"corpus_root\":\"consru_export/consru_export/exports\""));
    assert!(jsonl.contains(
        "\"output_artifact\":\"prd/migration/rust-evidence/m200-s02-npa-bounds-scan.jsonl\""
    ));
}

/// T04: terminal completeness — every discovered XML was attempted exactly
/// once and classified (pins the accepted observed inventory 43785 that the
/// companion corpus-acceptance evidence reconciled against an independent
/// walk).
#[test]
fn t04_tracked_corpus_terminal_completeness_reconciles_walk() {
    let jsonl = tracked_corpus_artifact();
    assert!(jsonl.contains(
        "\"record_kind\":\"totals\",\"files_attempted\":43785,\"files_decoded\":43785,\"malformed\":0,\"unreadable\":0,\"bytes_observed\":3789431364,\"documents\":43785"
    ));
    assert!(jsonl.contains(
        "\"observed_file_count\":43785,\"observed_bytes\":3789431364,\"success_count\":43785,\"malformed_count\":0,\"unreadable_count\":0"
    ));
    assert!(jsonl.contains("\"coverage_failures\":0,\"pattern_unmapped\":0"));
    assert!(jsonl.contains("\"run_status\":\"complete\""));
    // 43785 success + 0 malformed + 0 unreadable == 43785 attempted == the
    // independent walk count; both sides of the identity are pinned by the
    // contains assertions above, so any drift breaks this test.
}

/// T04: direct and proxy metrics stay separated in the tracked artifact —
/// exactly four `direct` and four `proxy` metric records in fixed slots,
/// and the non-claims array is intact.
#[test]
fn t04_tracked_corpus_direct_proxy_separation() {
    let jsonl = tracked_corpus_artifact();
    const METRIC_SLOTS: [(&str, &str); 8] = [
        ("blocks_per_document", "direct"),
        ("tokens_per_block", "direct"),
        ("candidates_per_block", "direct"),
        ("candidates_per_document", "direct"),
        ("proxy_date_docno_members_per_block", "proxy"),
        ("proxy_structural_range_blocks_per_block", "proxy"),
        ("proxy_alias_surfaces_per_document", "proxy"),
        ("proxy_cross_block_tails_per_document", "proxy"),
    ];
    for (kind, namespace) in METRIC_SLOTS {
        let marker = format!("\"metric_kind\":\"{kind}\",\"namespace\":\"{namespace}\"");
        assert!(jsonl.contains(&marker), "missing {marker}");
    }
    assert_eq!(
        jsonl.matches("\"namespace\":\"direct\"").count(),
        4,
        "exactly four direct metric records"
    );
    assert_eq!(
        jsonl.matches("\"namespace\":\"proxy\"").count(),
        4,
        "exactly four proxy metric records"
    );
    assert!(jsonl.contains(
        "\"non_claims\":[\"official-publication\",\"R070\",\"LawRef\",\"N2-gate\",\"semantic-frame\",\"bound-decision\"]"
    ));
}

/// T04: the accepted run's hashes are pinned — scanner source, measurement
/// definitions, and the scan-time profile fingerprint — and the tracked
/// profile stays fingerprintable. The T04 runtime-note edit moves the live
/// fingerprint by design (documentation only), so the exact live value is
/// also pinned as a conscious-update drift guard.
#[test]
fn t04_tracked_corpus_hashes_are_deterministic() {
    let jsonl = tracked_corpus_artifact();
    assert!(
        jsonl.contains("\"profile_hash\":\"fnv1a64:bcf61bc0940f3cb9\""),
        "the artifact pins the profile bytes it read at scan time"
    );
    assert!(
        jsonl.contains("\"scanner_source_hash\":\"fnv1a64:ee015b5f2f79c4e3\""),
        "scanner source unchanged since the accepted run"
    );
    assert!(
        jsonl.contains("\"measurement_definitions_hash\":\"fnv1a64:6fa01374f8c3ad65\""),
        "measurement definitions unchanged since the accepted run"
    );
    assert_eq!(
        tracked_profile_hash(),
        "fnv1a64:f59afde9715ad05b",
        "the live tracked profile fingerprint moved only by the T04 runtime-note edit; \
         any further profile change is a conscious acceptance update"
    );
}

/// T04: redaction on the accepted artifact — the tracked bytes are pure
/// ASCII, so no Cyrillic legal text can be present, and anchors stay
/// metadata-only (relative paths, FNV content hashes, byte spans).
#[test]
fn t04_tracked_corpus_redaction_is_pure_ascii() {
    let bytes = fs::read(tracked_corpus_artifact_path()).expect("tracked artifact readable");
    assert!(
        bytes.iter().all(|byte| byte.is_ascii()),
        "pure-ASCII artifact: no raw Cyrillic legal text can be present"
    );
    let jsonl = tracked_corpus_artifact();
    assert!(jsonl.contains("\"document_content_hash\":\"fnv1a64:"));
    assert!(jsonl.contains("\"compact_shape\":\"document-block-count\""));
    assert!(jsonl.contains(
        "document_content_hash anchors are fingerprinted at render time with a bounded probe read of anchor files"
    ));
}

/// T04: clock honesty on the accepted run — ended_at is after started_at
/// (captured after the walk, 678 s wall), the count-only progress policy is
/// recorded, and the incomplete-diagnostic contract is declared on the
/// artifact itself (fixture behavior pinned by the t01 tests here and in
/// the CLI contract suite).
#[test]
fn t04_tracked_corpus_clock_and_progress_are_honest() {
    let jsonl = tracked_corpus_artifact();
    assert!(jsonl.contains("\"run_status\":\"complete\""));
    assert!(
        jsonl.contains(
            "\"started_at\":\"2026-09-05T13:21:35Z\",\"ended_at\":\"2026-09-05T13:32:53Z\""
        ),
        "ended_at is a real post-walk timestamp, not the injected started_at constant"
    );
    assert!(jsonl.contains(
        "ended_at is captured after the walk completes; periodic --out rewrites during a run carry run_status incomplete"
    ));
    assert!(
        jsonl.contains("--progress 500"),
        "the accepted run used count-only heartbeats every 500 files"
    );
}

/// T04: the top-K scaffold stays bounded on the full corpus — at most the
/// cap anchors per metric record, every anchor bound to its record's metric
/// kind, and top-K selection still deferred-undefined.
#[test]
fn t04_tracked_corpus_topk_bounded_and_anchored() {
    let jsonl = tracked_corpus_artifact();
    let mut metric_records = 0usize;
    let mut anchors_total = 0usize;
    for line in jsonl
        .lines()
        .filter(|line| line.contains("\"record_kind\":\"metric\""))
    {
        metric_records += 1;
        let kind = line
            .split("\"metric_kind\":\"")
            .nth(1)
            .and_then(|rest| rest.split('"').next())
            .expect("metric record carries its kind");
        let anchors = line.matches("\"document_relative_path\"").count();
        anchors_total += anchors;
        assert!(
            anchors <= TOP_K_SCAFFOLD_CAP,
            "top-K cap exceeded for {kind}: {anchors} anchors"
        );
        let bound_backs = line.matches(&format!("\"metric_kind\":\"{kind}\"")).count();
        assert_eq!(
            bound_backs,
            anchors + 1,
            "every anchor in {kind} binds back to the record's metric kind"
        );
    }
    assert_eq!(
        metric_records, 8,
        "closed schema: exactly eight metric records"
    );
    assert_eq!(
        anchors_total,
        8 * TOP_K_SCAFFOLD_CAP,
        "the full corpus retained the cap on every metric"
    );
    assert!(jsonl.contains("\"top_k\":\"deferred-undefined\""));
}

/// T04: the accepted artifact stays diagnostic-only — both lifecycle
/// records are `[diagnostic]`, no `[bounded]` promotion happened, the
/// scaffold's `[proposed]` status is declared, and top-K selection stays
/// deferred-undefined.
#[test]
fn t04_tracked_corpus_stays_diagnostic_with_non_claims() {
    let jsonl = tracked_corpus_artifact();
    assert_eq!(
        jsonl.matches("\"lifecycle\":\"[diagnostic]\"").count(),
        2,
        "header and run_manifest stay [diagnostic]"
    );
    assert!(
        !jsonl.contains("[bounded]"),
        "no bounded promotion without the S03 outlier review"
    );
    assert!(jsonl.contains(
        "\"npa-bounds-scan/v1 is a [proposed] scaffold (D388): numeric bounds decisions are deferred-undefined\""
    ));
    assert!(jsonl.contains("\"top_k\":\"deferred-undefined\""));
    assert!(jsonl.contains("\"semantic-frame\""));
    assert!(jsonl.contains("\"bound-decision\""));
}

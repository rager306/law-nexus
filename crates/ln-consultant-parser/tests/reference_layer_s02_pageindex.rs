//! D5 contents-ladder pin for 44-FZ edition 50 (ADR-0031 D5/D8).
//!
//! The Python reference commits the ed-50 D5 ladder
//! (`prd/migration/rust-evidence/m217-reference-pageindex.json`); this suite
//! pins that the Rust port reproduces it byte for byte, that the public counts
//! match the oracle (8 chapters / 9 § / 141 articles / 1164 parts / 904 punkts
//! / 108 subpoints / 669 blocks, 3003 nodes, depth 7, 848535 chars), and that
//! the four ADR-0031 D5 invariants hold when recomputed independently from the
//! published nodes (not from the derivation that produced them).
//!
//! Negative surfaces: a corpus without edition 50 stays exit 0 under the
//! measurement gate, a tampered *or missing* pageindex artifact fails closed
//! with `EXIT_DRIFT` (6) while the other five artifacts stay correct, and
//! `pageindex_document` bubbles `RefError` (exit 3) for unreadable inputs.
//! The hand-built ladder test is hermetic and pins levels/ids/parents/offsets.
//!
//! The corpus is gitignored, so corpus-dependent tests are gated: without
//! `consru_export/` they print `SKIP:` and return (exit 0). Set
//! `M225_S01_REPO_ROOT=<dir>` to point at another checkout; point it at a
//! nonexistent directory to force the skip path locally (the same knob the S01
//! and T04 suites use).

use ln_consultant_parser::reference_layer::{
    DeriveOptions, EXIT_DRIFT, EXIT_INPUT, EXIT_OK, MEASUREMENT_EDITION, artifact_paths,
    build_pageindex, measurement_applicable, measurement_artifact_paths, pageindex_document,
    run_check, scan_wordml_paragraphs, try_derive,
};
use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

/// Repository root. `M225_S01_REPO_ROOT` wins when set (it may be a
/// nonexistent path, which is the documented way to exercise the skip path).
fn repo_root() -> PathBuf {
    if let Some(root) = std::env::var_os("M225_S01_REPO_ROOT") {
        return PathBuf::from(root);
    }
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .canonicalize()
        .expect("repo root")
}

fn corpus_dir() -> PathBuf {
    repo_root()
        .join("consru_export")
        .join("consru_export")
        .join("exports")
        .join("npa")
        .join("law_2013-04-05_44-fz")
}

fn catalog() -> PathBuf {
    repo_root()
        .join("consru_export")
        .join("consru_export")
        .join("catalog.sqlite")
}

fn committed_dir() -> PathBuf {
    repo_root()
        .join("prd")
        .join("migration")
        .join("rust-evidence")
}

fn committed(name: &str) -> String {
    let path = committed_dir().join(name);
    std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("committed artifact {} unreadable: {e}", path.display()))
}

fn fixtures() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/reference-layer")
}

/// Corpus-gated hermeticity guard. Must run before any corpus read.
fn skip_without_corpus() -> bool {
    if corpus_dir().is_dir() && catalog().is_file() {
        return false;
    }
    eprintln!(
        "SKIP: consru_export 44-FZ corpus not available (set M225_S01_REPO_ROOT to a full checkout, or to a nonexistent dir to force this skip)"
    );
    true
}

fn opts(corpus: PathBuf, catalog: PathBuf) -> DeriveOptions {
    DeriveOptions {
        limit_editions: None,
        corpus_dir: corpus,
        catalog,
    }
}

/// The ed-50 edition file of the real corpus (the D5 measurement input).
fn ed50_path() -> PathBuf {
    let mut files: Vec<PathBuf> = std::fs::read_dir(corpus_dir())
        .expect("corpus dir")
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.file_name()
                .and_then(|n| n.to_str())
                .is_some_and(|n| n.starts_with("edition-0050"))
        })
        .collect();
    files.sort();
    files.into_iter().next().expect("edition 50 present")
}

fn paragraphs_of_ed50() -> Vec<String> {
    let bytes = std::fs::read(ed50_path()).expect("read ed-50");
    scan_wordml_paragraphs(&bytes).expect("scan ed-50 paragraphs")
}

/// Test-local article-heading spine: `Статья <n>[.<m>]` at the start of a
/// paragraph, recomputed from the paragraphs without the module's private
/// `article_heading` (independent of the derivation under test).
fn heading_spine(paras: &[String]) -> BTreeSet<String> {
    let mut spine = BTreeSet::new();
    for text in paras {
        let Some(rest) = text.strip_prefix("Статья ") else {
            continue;
        };
        let bytes = rest.as_bytes();
        let d = bytes.iter().take_while(|b| b.is_ascii_digit()).count();
        if d == 0 {
            continue;
        }
        let mut end = d;
        if bytes.get(d) == Some(&b'.') {
            let d2 = bytes[d + 1..]
                .iter()
                .take_while(|b| b.is_ascii_digit())
                .count();
            if d2 > 0 {
                end = d + 1 + d2;
            }
        }
        spine.insert(format!("statya-{}", &rest[..end]));
    }
    spine
}

const COMMITTED_ARTIFACTS: [&str; 4] = [
    "m217-reference-timeline.json",
    "m217-reference-digests.jsonl",
    "m217-reference-named-graphs.json",
    "m217-reference-amend-provenance.json",
];

#[test]
fn pageindex_document_is_byte_identical_to_the_python_reference() {
    if skip_without_corpus() {
        return;
    }
    let derived = pageindex_document(&corpus_dir(), MEASUREMENT_EDITION)
        .expect("ed-50 pageindex ladder must derive");
    let oracle = committed("m217-reference-pageindex.json");
    assert_eq!(
        derived.len(),
        oracle.len(),
        "the D5 ladder must have the byte length of the committed Python reference"
    );
    assert_eq!(
        derived, oracle,
        "the D5 ladder must be byte-identical to the committed Python reference"
    );

    // The public counts are pinned on the derived document (not on the file).
    let doc: serde_json::Value = serde_json::from_str(&derived).expect("derived document parses");
    assert_eq!(doc["schema_version"], "m217-reference-pageindex/v1");
    assert_eq!(doc["scope"]["edition_no"], MEASUREMENT_EDITION);
    assert_eq!(doc["scope"]["act_dir"], "law_2013-04-05_44-fz");
    let counts = &doc["counts"];
    assert_eq!(counts["total_nodes"], 3003);
    assert_eq!(counts["sections"], 0);
    assert_eq!(counts["chapters"], 8);
    assert_eq!(counts["paragraphs"], 9);
    assert_eq!(counts["articles"], 141);
    assert_eq!(counts["parts"], 1164);
    assert_eq!(counts["punkts"], 904);
    assert_eq!(counts["subpoints"], 108);
    assert_eq!(counts["blocks"], 669);
    assert_eq!(counts["max_depth"], 7);
    assert_eq!(counts["chars"], 848535);
    // The ladder is complete: the per-kind counts partition the node list.
    let sum = [
        "sections",
        "chapters",
        "paragraphs",
        "articles",
        "parts",
        "punkts",
        "subpoints",
        "blocks",
    ]
    .iter()
    .map(|k| counts[k].as_u64().unwrap_or(0))
    .sum::<u64>();
    assert_eq!(sum, counts["total_nodes"].as_u64().unwrap_or(0));
    assert_eq!(doc["nodes"].as_array().map(|n| n.len()).unwrap_or(0), 3003);
    eprintln!(
        "rust D5 ed-50: total_nodes={} sections={} chapters={} paragraphs={} articles={} parts={} punkts={} subpoints={} blocks={} max_depth={} chars={}",
        counts["total_nodes"],
        counts["sections"],
        counts["chapters"],
        counts["paragraphs"],
        counts["articles"],
        counts["parts"],
        counts["punkts"],
        counts["subpoints"],
        counts["blocks"],
        counts["max_depth"],
        counts["chars"],
    );
}

#[test]
fn pinned_ladder_recomputes_the_four_d5_invariants() {
    if skip_without_corpus() {
        return;
    }
    let paras = paragraphs_of_ed50();
    let oracle = committed("m217-reference-pageindex.json");
    let doc: serde_json::Value = serde_json::from_str(&oracle).expect("oracle parses");
    let nodes = doc["nodes"].as_array().expect("nodes array");

    // (b) single assignment: every non-empty paragraph is in exactly one node.
    let owned: Vec<u64> = nodes
        .iter()
        .map(|n| n["p_start"].as_u64().expect("p_start"))
        .collect();
    let expected: Vec<u64> = paras
        .iter()
        .enumerate()
        .filter(|(_, text)| !text.is_empty())
        .map(|(idx, _)| idx as u64)
        .collect();
    assert_eq!(
        owned, expected,
        "every non-empty paragraph must belong to exactly one node, in order"
    );
    for node in nodes {
        assert_eq!(
            node["p_start"], node["p_end"],
            "a node owns exactly one paragraph: {}",
            node["id"]
        );
    }

    // (a) char conservation over the non-empty paragraphs.
    let node_chars: u64 = nodes
        .iter()
        .map(|n| n["chars"].as_u64().expect("chars"))
        .sum();
    let para_chars: u64 = paras
        .iter()
        .filter(|text| !text.is_empty())
        .map(|text| text.chars().count() as u64)
        .sum();
    assert_eq!(node_chars, para_chars, "char conservation");
    assert_eq!(node_chars, doc["counts"]["chars"].as_u64().unwrap());

    // Offsets are cumulative over "\n".join(paras): offset i = Σ(len+1).
    let mut offsets: Vec<u64> = Vec::with_capacity(paras.len());
    let mut offset = 0u64;
    for text in &paras {
        offsets.push(offset);
        offset += text.chars().count() as u64 + 1;
    }
    for node in nodes {
        let idx = node["p_start"].as_u64().expect("p_start") as usize;
        assert_eq!(node["char_start"].as_u64().unwrap(), offsets[idx]);
        assert_eq!(
            node["char_end"].as_u64().unwrap(),
            offsets[idx] + node["chars"].as_u64().unwrap()
        );
    }

    // (c) no article outside the ladder: the statya path ids are the digest spine.
    let ladder: BTreeSet<String> = nodes
        .iter()
        .filter(|n| n["kind"] == "statya")
        .map(|n| {
            n["id"]
                .as_str()
                .expect("id")
                .rsplit('/')
                .next()
                .unwrap()
                .to_string()
        })
        .collect();
    let spine = heading_spine(&paras);
    assert_eq!(ladder, spine, "the ladder carries exactly the digest spine");
    assert_eq!(ladder.len(), 141);

    // (d) id uniqueness.
    let ids: BTreeSet<&str> = nodes.iter().map(|n| n["id"].as_str().unwrap()).collect();
    assert_eq!(ids.len(), nodes.len(), "path ids must not collide");

    // The parent chain of every node is itself a published node id.
    for node in nodes {
        if let Some(parent) = node["parent"].as_str() {
            assert!(ids.contains(parent), "parent {parent} must be a node");
        }
    }
    eprintln!(
        "rust D5 invariants recomputed: nodes={} spine={} chars={}",
        nodes.len(),
        spine.len(),
        node_chars
    );
}

/// Hermetic ladder semantics: recognized levels 1..7, path ids, parents, and
/// character offsets — no corpus needed.
#[test]
fn hand_built_ladder_pins_levels_ids_parents_and_offsets() {
    let paras: Vec<String> = [
        "",
        "Преамбула без заголовка.",
        "Раздел I. Общие положения",
        "Глава 1. Общие положения",
        "Статья 1. Предмет",
        "1. Первая часть.",
        "1) пункт",
        "а) подпункт",
        "обычный абзац",
        "Глава 2. Вторая",
    ]
    .iter()
    .map(|s| s.to_string())
    .collect();
    let nodes = build_pageindex(&paras).expect("hand-built ladder derives");
    let got: Vec<(String, u8, String, Option<String>)> = nodes
        .iter()
        .map(|n| (n.id.clone(), n.level, n.kind.clone(), n.parent.clone()))
        .collect();
    assert_eq!(
        got,
        vec![
            ("block-1".to_string(), 7, "block".to_string(), None),
            ("section-I".to_string(), 1, "section".to_string(), None),
            (
                "section-I/chapter-1".to_string(),
                2,
                "chapter".to_string(),
                Some("section-I".to_string())
            ),
            (
                "section-I/chapter-1/statya-1".to_string(),
                3,
                "statya".to_string(),
                Some("section-I/chapter-1".to_string())
            ),
            (
                "section-I/chapter-1/statya-1/part-1".to_string(),
                4,
                "part".to_string(),
                Some("section-I/chapter-1/statya-1".to_string())
            ),
            (
                "section-I/chapter-1/statya-1/part-1/punkt-1".to_string(),
                5,
                "punkt".to_string(),
                Some("section-I/chapter-1/statya-1/part-1".to_string())
            ),
            (
                "section-I/chapter-1/statya-1/part-1/punkt-1/subpunkt-а".to_string(),
                6,
                "subpunkt".to_string(),
                Some("section-I/chapter-1/statya-1/part-1/punkt-1".to_string())
            ),
            // A level-7 block closes every open node (level >= 7), so it hangs
            // off the last subpoint-level ancestor it did not close: here the
            // stack top is the subpunkt's parent chain — the previous block is
            // gone, and the nearest open node is level 6.
            (
                "section-I/chapter-1/statya-1/part-1/punkt-1/subpunkt-а/block-8".to_string(),
                7,
                "block".to_string(),
                Some("section-I/chapter-1/statya-1/part-1/punkt-1/subpunkt-а".to_string())
            ),
            // A chapter closes the article-level nodes it is nested under.
            (
                "section-I/chapter-2".to_string(),
                2,
                "chapter".to_string(),
                Some("section-I".to_string())
            ),
        ],
        "the ladder must be a tree with path ids"
    );
    // Offsets are cumulative over "\n".join(paras) and chars count code points.
    let mut offsets: Vec<usize> = Vec::with_capacity(paras.len());
    let mut offset = 0usize;
    for text in &paras {
        offsets.push(offset);
        offset += text.chars().count() + 1;
    }
    for node in &nodes {
        assert_eq!(node.p_start, node.p_end);
        assert_eq!(node.chars, paras[node.p_start].chars().count());
        assert_eq!(node.char_start, offsets[node.p_start]);
        assert_eq!(node.char_end, offsets[node.p_start] + node.chars);
    }
    assert_eq!(
        nodes.len(),
        9,
        "the empty paragraph stays out of the ladder"
    );
}

#[test]
fn pageindex_measurement_is_not_applicable_without_edition_50() {
    // Hermetic: no corpus needed. Fixture corpora carry editions 1 and 2 only.
    assert!(!measurement_applicable(&fixtures().join("basic")));
    assert!(!measurement_applicable(&fixtures().join("other-act")));
    assert!(!measurement_applicable(Path::new(
        "/nonexistent-lns02-pageindex"
    )));
}

#[test]
fn fixture_corpus_stays_exit_ok_under_the_measurement_gate() {
    // Hermetic: the applicability gate must not turn a fixture corpus into an
    // exit-3 or a drift failure (D782) now that two measurement artifacts are
    // wired into the same check.
    let tmp = std::env::temp_dir().join("ln-ref-s02-pageindex-gate");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");
    let catalog = empty_catalog(&tmp);
    let corpus = fixtures().join("basic");
    assert!(!measurement_applicable(&corpus));
    let out = tmp.join("out");
    std::fs::create_dir_all(&out).expect("out");

    let reference = try_derive(&opts(corpus.clone(), catalog.clone())).expect("basic derives");
    for (path, body) in artifact_paths(&out).iter().zip([
        &reference.timeline,
        &reference.digests,
        &reference.named_graphs,
        &reference.amend,
    ]) {
        std::fs::write(path, body).expect("seed artifact");
    }
    assert_eq!(
        run_check(&corpus, &catalog, &out),
        EXIT_OK,
        "a corpus without edition 50 must stay exit 0"
    );
    let _ = std::fs::remove_dir_all(&tmp);
}

fn empty_catalog(dir: &Path) -> PathBuf {
    let path = dir.join("cat-empty.sqlite");
    let _ = std::fs::remove_file(&path);
    let con = rusqlite::Connection::open(&path).expect("create catalog");
    con.execute(
        "create table editions (relative_path text, document_date text, number text)",
        [],
    )
    .expect("schema");
    drop(con);
    path
}

#[test]
fn pageindex_document_fails_closed_on_unreadable_inputs() {
    // Hermetic: hand-built corpora, no real corpus needed. Each path must
    // bubble a `RefError` (ADR-0031 D6 exit 3), never a panic and never exit 0.
    let tmp = std::env::temp_dir().join("ln-ref-s02-pageindex-failclosed");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");
    const ED50: &str = "edition-0050_rev-unknown_from-unknown_aaaaaaaa.xml";

    // (a) an ed-50 file without the WordML 2003 namespace -> exit 3.
    let notwordml = tmp.join("notwordml");
    std::fs::create_dir_all(&notwordml).expect("dir");
    std::fs::write(notwordml.join(ED50), "<x/>").expect("write");
    assert!(measurement_applicable(&notwordml));
    let err = pageindex_document(&notwordml, MEASUREMENT_EDITION)
        .expect_err("a non-WordML ed-50 file must not derive");
    assert_eq!(err.exit_code(), EXIT_INPUT);

    // (b) a corpus without edition 50 -> not applicable, and a direct call
    // fails closed rather than silently returning an empty ladder.
    let no50 = tmp.join("no50");
    std::fs::create_dir_all(&no50).expect("dir");
    std::fs::write(
        no50.join("edition-0049_rev-unknown_from-unknown_cccccccc.xml"),
        "<x/>",
    )
    .expect("write");
    assert!(!measurement_applicable(&no50));
    let err = pageindex_document(&no50, MEASUREMENT_EDITION)
        .expect_err("a corpus without edition 50 must not derive");
    assert_eq!(err.exit_code(), EXIT_INPUT);

    // (c) a missing corpus directory -> exit 3, no panic.
    let err = pageindex_document(&tmp.join("absent"), MEASUREMENT_EDITION)
        .expect_err("a missing corpus must not derive");
    assert_eq!(err.exit_code(), EXIT_INPUT);

    // (d) an ed-50 WordML file with a malformed paragraph -> exit 3.
    let broken = tmp.join("broken");
    std::fs::create_dir_all(&broken).expect("dir");
    std::fs::write(
        broken.join(ED50),
        "<?xml version=\"1.0\"?><w:wordDocument xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\"><w:p><w:r><w:t>Статья 1. Текст",
    )
    .expect("write");
    assert!(measurement_applicable(&broken));
    let err = pageindex_document(&broken, MEASUREMENT_EDITION)
        .expect_err("an unclosed <w:p> must not derive");
    assert_eq!(err.exit_code(), EXIT_INPUT);
    let _ = std::fs::remove_dir_all(&tmp);
}

#[test]
fn measurement_artifact_paths_covers_both_ed50_documents() {
    // Hermetic: the two measurement artifacts the D4/D5 layers publish.
    let paths = measurement_artifact_paths(Path::new("/tmp/out"));
    assert_eq!(paths.len(), 2);
    assert!(paths[0].ends_with("m217-reference-references.json"));
    assert!(paths[1].ends_with("m217-reference-pageindex.json"));
    assert_eq!(
        artifact_paths(Path::new("/tmp/out")).len(),
        4,
        "the four full-corpus artifacts stay separate"
    );
}

#[test]
fn all_six_artifacts_check_clean_and_pageindex_tamper_fails_closed() {
    if skip_without_corpus() {
        return;
    }
    let tmp = std::env::temp_dir().join("ln-ref-s02-pageindex-drift");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");
    // Seed all six derived artifacts from the committed oracle: the check must
    // come back clean, which pins the Rust derivation byte for byte on both
    // measurement documents as well (not only on the four full-corpus ones).
    for name in COMMITTED_ARTIFACTS {
        std::fs::write(tmp.join(name), committed(name)).expect("seed artifact");
    }
    std::fs::write(
        tmp.join("m217-reference-references.json"),
        committed("m217-reference-references.json"),
    )
    .expect("seed references");
    std::fs::write(
        tmp.join("m217-reference-pageindex.json"),
        committed("m217-reference-pageindex.json"),
    )
    .expect("seed pageindex");
    assert_eq!(
        run_check(&corpus_dir(), &catalog(), &tmp),
        EXIT_OK,
        "all six correct artifacts must check clean"
    );

    // Corrupt only the ladder: the other five stay correct, so a clean exit
    // here would mean the pageindex comparison is not wired into run_check.
    std::fs::write(tmp.join("m217-reference-pageindex.json"), "{}\n").expect("tamper");
    assert_eq!(
        run_check(&corpus_dir(), &catalog(), &tmp),
        EXIT_DRIFT,
        "a tampered D5 ladder must fail closed with drift"
    );

    // A missing ladder is drift too, not a silent pass.
    std::fs::remove_file(tmp.join("m217-reference-pageindex.json")).expect("remove");
    assert_eq!(
        run_check(&corpus_dir(), &catalog(), &tmp),
        EXIT_DRIFT,
        "a missing D5 ladder must fail closed with drift"
    );
    let _ = std::fs::remove_dir_all(&tmp);
}

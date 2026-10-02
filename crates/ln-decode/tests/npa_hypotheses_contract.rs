//! M211 S02 T02: буфер TYPE-гипотез и provenance (RC28-F09).
//!
//! `attach_types` больше не молчит: победитель несёт `derivation`,
//! `type_evidence`, а конкурирующие выжившие чтения сохраняются в
//! `alternatives`. D607: intra-block date-crossing fallback сохранён
//! (parity 112/112), но переиспользование головы теперь явное — она
//! видна как `type_evidence` (byte-span головы), а не как молчаливый
//! `max_by_key`. Cross-block наследование — граница S03 и здесь отсутствует.

use ln_decode::npa_anchor;
use ln_decode::npa_typed::{self, TypeDerivation};

fn scan(para: &str) -> Vec<npa_typed::TypedMember> {
    npa_typed::scan_typed(std::slice::from_ref(&para.to_string()))
}

fn member_for<'a>(
    members: &'a [npa_typed::TypedMember],
    number: &str,
) -> &'a npa_typed::TypedMember {
    members
        .iter()
        .find(|m| m.number == number)
        .unwrap_or_else(|| panic!("member N {number} not found: {members:?}"))
}

/// Конкурирующие гипотезы сохраняются: «соглашение к контракту от … N 2»
/// даёт победителя `контракт` (ближайшая голова) и сохраняет `соглашение`
/// в `alternatives` вместе с его source-span.
#[test]
fn competing_type_hypotheses_are_retained() {
    let para = "дополнительное соглашение к контракту от 23.03.2023 N 2";
    let members = scan(para);
    let m = member_for(&members, "2");

    assert_eq!(m.type_name, "контракт", "closest written head wins");
    assert_eq!(m.derivation, TypeDerivation::WrittenHere);
    assert!(!m.unresolved, "a surviving winner cannot be unresolved");

    let alts: Vec<&str> = m.alternatives.iter().map(|h| h.canon.as_str()).collect();
    assert!(
        alts.contains(&"соглашение"),
        "loser must survive as an explicit hypothesis, not vanish: {alts:?}"
    );
}

/// `type_evidence` победителя — валидный локальный UTF-8 byte-span, равный
/// голове-победителю; у проигравших гипотез спаны тоже валидны.
#[test]
fn type_evidence_is_valid_local_span() {
    let para = "дополнительное соглашение к контракту от 23.03.2023 N 2";
    let members = scan(para);
    let m = member_for(&members, "2");

    let ev = m
        .type_evidence
        .expect("winner must carry its head source-span");
    assert_eq!(ev.block, m.span.block, "evidence stays in the member block");
    npa_anchor::check_span(para, ev).expect("type_evidence must be valid local UTF-8");
    assert_eq!(&para[ev.start..ev.end], "контракт");

    for h in &m.alternatives {
        npa_anchor::check_span(para, h.evidence)
            .expect("alternative evidence must be a valid local UTF-8 span");
        assert_eq!(h.evidence.block, m.span.block);
    }
}

/// Date-crossed кандидат исключается из буфера гипотез: «чужое
/// Постановление Правительства» пересечено промежуточной датой и не
/// попадает в `alternatives` второго (верного) Распоряжения.
#[test]
fn date_crossed_candidate_is_excluded_from_alternatives() {
    let para = "Постановление Правительства РФ от 01.01.2020 N 1 и \
                Распоряжение МТУ Росимущества в Челябинской и Курганской областях \
                от 15.08.2024 N 74-480-р";
    let members = scan(para);
    let m = member_for(&members, "74-480-р");

    assert!(
        m.type_name.starts_with("Распоряжение"),
        "nearest written head wins: {}",
        m.type_name
    );
    assert!(
        m.alternatives
            .iter()
            .all(|h| h.canon != "Постановление Правительства РФ"),
        "date-crossed candidate must not survive into the hypothesis buffer: {:?}",
        m.alternatives
    );
}

/// Явный unresolved вместо fallback к пересечённому/отсутствующему
/// кандидату: если до якоря в блоке нет ни одной TYPE-головы, член
/// помечается `Unresolved`, `type_name` пуст, `type_evidence` отсутствует.
#[test]
fn no_type_before_anchor_is_unresolved() {
    let para = "Правительство рассмотрело обращение от 01.01.2020 N 5";
    let members = scan(para);
    let m = member_for(&members, "5");

    assert!(m.unresolved, "no surviving hypothesis => unresolved");
    assert_eq!(m.derivation, TypeDerivation::Unresolved);
    assert_eq!(m.type_name, "");
    assert!(m.type_evidence.is_none());
    assert!(m.alternatives.is_empty());
}

/// Provenance не меняет identity: occurrences не сливаются, дата и номер
/// сохраняются, а derivation честно отражает, записан ли TYPE в блоке.
#[test]
fn provenance_does_not_merge_occurrences() {
    let para = "Федеральный закон от 01.01.2020 N 1-ФЗ и контракт от 02.02.2020 N 2";
    let members = scan(para);
    assert_eq!(
        members.len(),
        2,
        "two anchors => two occurrences: {members:?}"
    );

    let a = member_for(&members, "1-ФЗ");
    let b = member_for(&members, "2");
    assert_ne!(a.span, b.span, "identity is the source-local span");
    assert_eq!((a.date.as_str(), a.number.as_str()), ("01.01.2020", "1-ФЗ"));
    assert_eq!((b.date.as_str(), b.number.as_str()), ("02.02.2020", "2"));
    assert_eq!(a.type_name, "Федеральный закон");
    assert_eq!(a.derivation, TypeDerivation::WrittenHere);
    assert_eq!(b.derivation, TypeDerivation::WrittenHere);
}

/// D607: intra-block series head, пересéчённый первой датой списка,
/// сохраняется (parity 112/112 с дифференциальным эталоном), но теперь
/// переиспользование явное — голова видна как `type_evidence`.
#[test]
fn date_crossed_series_head_retained_with_explicit_evidence() {
    let para = "Федеральных законов от 01.07.2021 N 277-ФЗ, \
                от 29.05.2024 N 124-ФЗ, от 26.12.2024 N 484-ФЗ";
    let members = scan(para);

    let second = member_for(&members, "124-ФЗ");
    assert_eq!(second.derivation, TypeDerivation::WrittenHere);
    assert!(!second.unresolved);
    assert_eq!(second.type_name, "Федеральный закон");

    let ev = second
        .type_evidence
        .expect("series-head reuse must expose the head span");
    assert_eq!(ev.block, second.span.block);
    npa_anchor::check_span(para, ev).expect("head evidence must be valid UTF-8");
    assert!(
        para[ev.start..ev.end].starts_with("Федеральных законов"),
        "evidence must point at the written series head: {:?}",
        &para[ev.start..ev.end]
    );
}

/// D602: typed-поток остаётся serde-free и не читает fs/env.
#[test]
fn npa_typed_source_is_serde_free() {
    let src = std::fs::read_to_string(
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src/npa_typed.rs"),
    )
    .expect("npa_typed.rs must be readable");
    for forbidden in [
        "serde",
        "Deserialize",
        "Serialize",
        "serde_json",
        "std::fs",
        "std::env",
    ] {
        assert!(
            !src.contains(forbidden),
            "npa_typed.rs must stay serde/fs/env-free (D602): found {forbidden}"
        );
    }
}

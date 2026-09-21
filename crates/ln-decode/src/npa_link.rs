//! NPA linkers (M211 S03, ADR-0029).
//!
//! Линкер-проходы как чистые функции: approved_by, алиасы, this_ref,
//! head-family carry. Все проходы — Vec<TypedMember> → Vec<TypedMember>.

use crate::npa_typed::TypedMember;

/// Расстояние приклейки approved_by (окна ±) — из прототипа.
#[allow(dead_code)]
const APPROVE_WINDOW_FORWARD: usize = 450;
#[allow(dead_code)]
const APPROVE_WINDOW_BACKWARD: usize = 700;

/// Именованные annex-типы (могут иметь approved_by).
const ANNEX_TYPES: &[&str] = &[
    "правила",
    "положение",
    "перечень",
    "порядок",
    "требования",
    "методические рекомендации",
    "регламент",
    "конкурсная документация",
];

/// Linker 1: approved_by — annex получает цитату утверждающего акта.
/// Work ≠ утверждающий акт (ADR-0016).
pub fn link_approved_by(members: &mut [TypedMember], paragraphs: &[String]) {
    // для каждого параграфа: найти annex + ближайший dated act с глаголом
    let mut para_start = 0usize;
    for para in paragraphs {
        let para_len = para.chars().count();
        let para_end = para_start + para_len;
        let members_in_para: Vec<usize> = (0..members.len())
            .filter(|&i| {
                let m = &members[i];
                m.number != "—" || m.approved_by.is_empty()
            })
            .collect();

        // найти все якоря (дата+N) в этом параграфе
        let anchors: Vec<(usize, String, String, String)> = (0..members.len())
            .filter(|&i| members[i].number != "—")
            .map(|i| {
                (
                    para_start,
                    members[i].type_name.clone(),
                    members[i].date.clone(),
                    members[i].number.clone(),
                )
            })
            .collect();

        // для каждого annex (N=—, approved_by пуст) — найти dated act
        for &mi in &members_in_para {
            let m = &members[mi];
            if m.number != "—" || !m.approved_by.is_empty() {
                continue;
            }
            if !ANNEX_TYPES.contains(&m.type_name.to_lowercase().as_str()) {
                continue;
            }

            // глагол «утвержден» / «об утверждении» / «вместе с» в абзаце?
            let lower = para.to_lowercase();
            let has_verb = lower.contains("утвержденн")
                || lower.contains("об утверждении")
                || lower.contains("вместе с");
            if !has_verb {
                continue;
            }

            // найти ближайший dated act с government keyword
            let mut best: Option<(usize, String)> = None;
            for &(apos, ref tn, ref ad, ref an) in &anchors {
                let tnl = tn.to_lowercase();
                let is_gov =
                    tnl.contains("правительств") || tnl.contains("указ") || tnl.contains("приказ");
                let is_match = is_gov || tnl.contains("распоряжени");
                if !is_match {
                    continue;
                }
                let cite = format!("{} от {} N {}", tn, ad, an);
                match &best {
                    None => best = Some((apos + 1, cite)),
                    Some((bp, _)) if apos + 1 < *bp => best = Some((apos + 1, cite)),
                    _ => {}
                }
            }
            if let Some((_, cite)) = best {
                members[mi].approved_by = cite;
            }
        }
        para_start = para_end + 1;
    }
}

/// Linker 2: head-family carry — реквизиты-без-типа получают семейство
/// из шапки документа (правки ПП цитируют ПП).
pub fn carry_head_family(members: &mut [TypedMember], head_type: Option<&str>) {
    let hf = match head_type {
        Some(h)
            if [
                "Постановление Правительства РФ",
                "распоряжение Правительства РФ",
                "Указ Президента РФ",
                "Федеральный закон",
            ]
            .contains(&h) =>
        {
            h.to_string()
        }
        _ => return,
    };
    for m in members.iter_mut() {
        if m.type_name.is_empty() && m.number != "—" {
            m.type_name = hf.clone();
        }
    }
}

/// Linker 3: Letterhead-распознаватель — kind-words в первых абзацах.
/// Возвращает (kind, issuer) из шапки документа.
pub fn recognize_letterhead(paragraphs: &[String]) -> Option<(String, String)> {
    let head: String = paragraphs
        .iter()
        .take(3)
        .map(|s| s.as_str())
        .collect::<Vec<&str>>()
        .join("\n");
    let lower = head.to_lowercase();

    // ФАС/УФАС
    if lower.contains("антимонопольн") {
        let issuer = if lower.contains("управлен") {
            "УФАС России"
        } else {
            "ФАС России"
        };
        let kind = if lower.contains("решени") {
            "Решение"
        } else if lower.contains("предписани") {
            "Предписание"
        } else if lower.contains("определени") {
            "Определение"
        } else if lower.contains("постановлени") {
            "Постановление"
        } else {
            return None;
        };
        return Some((format!("{} {}", kind, issuer), issuer.to_string()));
    }
    // Международный договор
    if lower.contains("международн") && lower.contains("договор") {
        return Some(("Международный договор".into(), String::new()));
    }
    // Суд
    if lower.contains("верховн") && lower.contains("суд")
        || lower.contains("арбитражн") && lower.contains("суд")
        || lower.contains("кассационн") && lower.contains("суд")
    {
        return None; // суд-документы — fail-closed
    }
    None
}

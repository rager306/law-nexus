//! M209 S04 T05: the semantic boundary guard over the requirement acceptance
//! ledger (D561).
//!
//! The ledger `prd/migration/rust-evidence/m209-s04-requirement-acceptance.json`
//! is the single source-bound acceptance surface that milestone validation and
//! completion cite. D561 requires that surface to have a durable carrier in the
//! tracked code tree, and that the carrier be *semantic*: the ledger is compiled
//! in with `include_str!` and its invariants are re-derived from the parsed
//! document. No raw `sha256:` pin of this ledger is embedded anywhere in this
//! file — a digest freeze would fail on a legitimately regenerated artifact
//! while proving nothing about its meaning, and the byte-level freeze already
//! lives in `scripts/m209_s04_acceptance_contract.test.mjs`.
//!
//! What this boundary refuses (each refusal is exercised by an in-memory
//! mutation test below, not merely asserted in prose):
//! - a promoted R035 gate or R070 leg (`accepted-at-bounded-scope` where the
//!   T03/T04 disposition was a hold), because the declared partition would no
//!   longer match the recomputed one;
//! - a disposition outside the closed D558 vocabulary;
//! - a hold row whose precise debt was dropped;
//! - an eighth gate row or a fifth leg row;
//! - `authoritative: true` and any non-zero promotion counter;
//! - a minted punkt admission row, a mutated requirement status and a proof
//!   package attached to a gate row.
//!
//! Only `std` is used: `ln-kb-ontology` carries no JSON dev-dependency, and this
//! guard must not add one (ADR-0015 evidence contour, D561).

const ACCEPTANCE_JSON: &str =
    include_str!("../../../prd/migration/rust-evidence/m209-s04-requirement-acceptance.json");

const SCHEMA: &str = "law-nexus/m209-requirement-acceptance/v1";
const LIFECYCLE: &str = "[bounded]";

/// The closed acceptance vocabulary (D558). The ledger may not introduce a
/// fifth disposition and may not narrow the set.
const DISPOSITIONS: [&str; 4] = [
    "accepted-at-bounded-scope",
    "hold-requires-owner-decision",
    "hold-with-precise-debt",
    "rejected-as-stated",
];

/// Values that must never appear as a *string value* anywhere in the ledger.
/// Keys may carry them (`"authoritative": false`); values may not.
const FORBIDDEN_VALUES: [&str; 6] = [
    "validated",
    "complete",
    "authoritative",
    "satisfied",
    "proven",
    "promoted",
];

/// The seven R035 gate ids in the T03 adjudication order.
const GATE_IDS: [&str; 7] = [
    "GATE-AKOMA-FRBR-NORMALIZATION",
    "GATE-BFO-GOST-ALIGNMENT",
    "GATE-G015",
    "GATE-LKIF-DEONTIC-BENCHMARK",
    "GATE-ONTOLOGY-GRAPHRAG-INTEGRATION",
    "GATE-PILOT-SCALE-READINESS",
    "GATE-RUSLEGALCORE-SCOPE",
];

/// The four R070 leg ids in the T04 adjudication order.
const LEG_IDS: [&str; 4] = [
    "amending-acts",
    "affected-provisions",
    "commencement-and-transitional",
    "edition-delta",
];

// ---------------------------------------------------------------------------
// minimal std-only JSON reader
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
enum Json {
    Null,
    Bool(bool),
    Num(i64),
    Str(String),
    Arr(Vec<Json>),
    Obj(Vec<(String, Json)>),
}

impl Json {
    fn get(&self, key: &str) -> Option<&Json> {
        match self {
            Json::Obj(entries) => entries
                .iter()
                .find(|(name, _)| name == key)
                .map(|(_, value)| value),
            _ => None,
        }
    }

    fn get_mut(&mut self, key: &str) -> Option<&mut Json> {
        match self {
            Json::Obj(entries) => entries
                .iter_mut()
                .find(|(name, _)| name == key)
                .map(|(_, value)| value),
            _ => None,
        }
    }

    /// Replace an existing field. Returns `false` when the field is absent: a
    /// mutation test must never silently invent a field it meant to flip.
    fn set(&mut self, key: &str, value: Json) -> bool {
        match self.get_mut(key) {
            Some(slot) => {
                *slot = value;
                true
            }
            None => false,
        }
    }

    fn as_str(&self) -> Option<&str> {
        if let Json::Str(text) = self {
            Some(text)
        } else {
            None
        }
    }

    fn as_arr(&self) -> Option<&[Json]> {
        if let Json::Arr(items) = self {
            Some(items)
        } else {
            None
        }
    }

    fn as_arr_mut(&mut self) -> Option<&mut Vec<Json>> {
        if let Json::Arr(items) = self {
            Some(items)
        } else {
            None
        }
    }

    fn as_int(&self) -> Option<i64> {
        if let Json::Num(number) = self {
            Some(*number)
        } else {
            None
        }
    }

    fn as_bool(&self) -> Option<bool> {
        if let Json::Bool(flag) = self {
            Some(*flag)
        } else {
            None
        }
    }

    fn str_at(&self, key: &str) -> Option<&str> {
        self.get(key).and_then(Json::as_str)
    }

    fn int_at(&self, key: &str) -> Option<i64> {
        self.get(key).and_then(Json::as_int)
    }

    fn arr_at(&self, key: &str) -> Option<&[Json]> {
        self.get(key).and_then(Json::as_arr)
    }
}

struct JsonParser<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl<'a> JsonParser<'a> {
    fn parse(text: &'a str) -> Result<Json, String> {
        let mut parser = Self {
            bytes: text.as_bytes(),
            pos: 0,
        };
        parser.skip_ws();
        let value = parser.value()?;
        parser.skip_ws();
        if parser.pos != parser.bytes.len() {
            let pos = parser.pos;
            return Err(format!("trailing bytes at {pos}"));
        }
        Ok(value)
    }

    fn skip_ws(&mut self) {
        while matches!(
            self.bytes.get(self.pos).copied(),
            Some(b' ' | b'\n' | b'\t' | b'\r')
        ) {
            self.pos += 1;
        }
    }

    fn value(&mut self) -> Result<Json, String> {
        match self.bytes.get(self.pos).copied() {
            Some(b'{') => self.object(),
            Some(b'[') => self.array(),
            Some(b'"') => Ok(Json::Str(self.string()?)),
            Some(b't') => {
                self.literal("true")?;
                Ok(Json::Bool(true))
            }
            Some(b'f') => {
                self.literal("false")?;
                Ok(Json::Bool(false))
            }
            Some(b'n') => {
                self.literal("null")?;
                Ok(Json::Null)
            }
            Some(b'-' | b'0'..=b'9') => self.number(),
            other => {
                let pos = self.pos;
                Err(format!("unexpected byte at {pos}: {other:?}"))
            }
        }
    }

    fn literal(&mut self, word: &str) -> Result<(), String> {
        let end = self.pos + word.len();
        if self.bytes.get(self.pos..end) == Some(word.as_bytes()) {
            self.pos = end;
            Ok(())
        } else {
            Err(format!("expected literal {word}"))
        }
    }

    fn number(&mut self) -> Result<Json, String> {
        let start = self.pos;
        if self.bytes.get(self.pos).copied() == Some(b'-') {
            self.pos += 1;
        }
        while matches!(self.bytes.get(self.pos).copied(), Some(b'0'..=b'9')) {
            self.pos += 1;
        }
        let text =
            std::str::from_utf8(&self.bytes[start..self.pos]).map_err(|_| "invalid number")?;
        text.parse::<i64>()
            .map(Json::Num)
            .map_err(|error| format!("invalid integer {text}: {error}"))
    }

    fn string(&mut self) -> Result<String, String> {
        if self.bytes.get(self.pos).copied() != Some(b'"') {
            return Err("expected string".to_string());
        }
        self.pos += 1;
        let mut out = String::new();
        loop {
            let byte = self
                .bytes
                .get(self.pos)
                .copied()
                .ok_or("unterminated string")?;
            self.pos += 1;
            match byte {
                b'"' => return Ok(out),
                b'\\' => {
                    let escape = self
                        .bytes
                        .get(self.pos)
                        .copied()
                        .ok_or("unterminated escape")?;
                    self.pos += 1;
                    match escape {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{8}'),
                        b'f' => out.push('\u{c}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            let hex = self
                                .bytes
                                .get(self.pos..self.pos + 4)
                                .ok_or("short unicode escape")?;
                            let digits = std::str::from_utf8(hex).map_err(|_| "invalid escape")?;
                            let code =
                                u32::from_str_radix(digits, 16).map_err(|_| "invalid escape")?;
                            self.pos += 4;
                            out.push(char::from_u32(code).unwrap_or('\u{FFFD}'));
                        }
                        other => return Err(format!("unknown escape {other:?}")),
                    }
                }
                other if other < 0x80 => out.push(other as char),
                _ => return Err("raw non-ascii byte in string".to_string()),
            }
        }
    }

    fn array(&mut self) -> Result<Json, String> {
        self.pos += 1; // '['
        let mut items = Vec::new();
        self.skip_ws();
        if self.bytes.get(self.pos).copied() == Some(b']') {
            self.pos += 1;
            return Ok(Json::Arr(items));
        }
        loop {
            self.skip_ws();
            items.push(self.value()?);
            self.skip_ws();
            match self.bytes.get(self.pos).copied() {
                Some(b',') => self.pos += 1,
                Some(b']') => {
                    self.pos += 1;
                    return Ok(Json::Arr(items));
                }
                other => {
                    let pos = self.pos;
                    return Err(format!("expected , or ] at {pos}, found {other:?}"));
                }
            }
        }
    }

    fn object(&mut self) -> Result<Json, String> {
        self.pos += 1; // '{'
        let mut entries = Vec::new();
        self.skip_ws();
        if self.bytes.get(self.pos).copied() == Some(b'}') {
            self.pos += 1;
            return Ok(Json::Obj(entries));
        }
        loop {
            self.skip_ws();
            let key = self.string()?;
            self.skip_ws();
            if self.bytes.get(self.pos).copied() != Some(b':') {
                let pos = self.pos;
                return Err(format!("expected : at {pos}"));
            }
            self.pos += 1;
            self.skip_ws();
            entries.push((key, self.value()?));
            self.skip_ws();
            match self.bytes.get(self.pos).copied() {
                Some(b',') => self.pos += 1,
                Some(b'}') => {
                    self.pos += 1;
                    return Ok(Json::Obj(entries));
                }
                other => {
                    let pos = self.pos;
                    return Err(format!("expected , or }} at {pos}, found {other:?}"));
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// semantic boundary
// ---------------------------------------------------------------------------

#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
struct RowTally {
    total: i64,
    accepted: i64,
    hold: i64,
    owner_decision: i64,
    rejected: i64,
    debt: i64,
}

impl RowTally {
    fn partition(self) -> i64 {
        self.accepted + self.hold + self.owner_decision + self.rejected
    }
}

/// Recompute one row family from the document itself. A disposition outside the
/// closed vocabulary, or a row that dropped its debt, fails here — no stored
/// total is trusted.
fn tally(idx_key: &str, disposition_key: &str, rows: &[Json]) -> Result<RowTally, String> {
    let mut tally = RowTally::default();
    for row in rows {
        tally.total += 1;
        let row_id = row.str_at(idx_key).ok_or("row without id")?;
        let disposition = row
            .str_at(disposition_key)
            .ok_or_else(|| format!("unsupported_disposition: {row_id} carries no disposition"))?;
        if !DISPOSITIONS.contains(&disposition) {
            return Err(format!("unsupported_disposition: {row_id}={disposition}"));
        }
        match disposition {
            "accepted-at-bounded-scope" => tally.accepted += 1,
            "hold-with-precise-debt" => tally.hold += 1,
            "hold-requires-owner-decision" => tally.owner_decision += 1,
            _ => tally.rejected += 1,
        }
        let debt = row
            .arr_at("debt")
            .ok_or_else(|| format!("debt_dropped: {row_id} carries no debt array"))?;
        if debt.is_empty() {
            return Err(format!("debt_dropped: {row_id} carries no debt record"));
        }
        tally.debt += debt.len() as i64;
    }
    Ok(tally)
}

fn requirement<'a>(root: &'a Json, id: &str) -> Result<&'a Json, String> {
    let rows = root.arr_at("requirements").ok_or("requirements_absent")?;
    rows.iter()
        .find(|row| row.str_at("requirement_id") == Some(id))
        .ok_or_else(|| format!("requirement {id} is absent"))
}

/// Reject promoted, mutated or non-count-only ledger documents. `Ok(())` means
/// the document still is what D558/D561 permit it to be.
fn check_boundary(root: &Json) -> Result<(), String> {
    if root.str_at("schema") != Some(SCHEMA) {
        return Err("schema_drift".to_string());
    }
    if root.str_at("lifecycle") != Some(LIFECYCLE) {
        return Err(format!(
            "promotion_claimed: lifecycle={:?}",
            root.str_at("lifecycle")
        ));
    }
    if root.get("authoritative").and_then(Json::as_bool) != Some(false) {
        return Err("promotion_claimed: authoritative is not false".to_string());
    }
    for counter in [
        "gates_promoted",
        "legs_promoted",
        "proof_packages_attached",
        "requirement_records_mutated",
    ] {
        if root.int_at(counter) != Some(0) {
            return Err(format!(
                "promotion_claimed: {counter}={:?}",
                root.int_at(counter)
            ));
        }
    }

    let gates = root.arr_at("gates").ok_or("gates_absent")?;
    let legs = root.arr_at("legs").ok_or("legs_absent")?;
    if gates.len() != GATE_IDS.len() {
        return Err(format!("row_count: gates={}", gates.len()));
    }
    if legs.len() != LEG_IDS.len() {
        return Err(format!("row_count: legs={}", legs.len()));
    }

    let gate_tally = tally("gate_id", "disposition", gates)?;
    let leg_tally = tally("leg_id", "scope_disposition", legs)?;

    let r035 = requirement(root, "R035")?;
    let r070 = requirement(root, "R070")?;
    if r035.str_at("status") != Some("active") {
        return Err(format!(
            "requirement_status_changed: R035={:?}",
            r035.str_at("status")
        ));
    }
    if r070.str_at("status") != Some("active") {
        return Err(format!(
            "requirement_status_changed: R070={:?}",
            r070.str_at("status")
        ));
    }
    if r035.str_at("disposition_decision") != Some("D430") {
        return Err("requirement_status_changed: R035 decision is not D430".to_string());
    }
    if r070.str_at("disposition_decision") != Some("D416") {
        return Err("requirement_status_changed: R070 decision is not D416".to_string());
    }
    for row in [r035, r070] {
        if row.str_at("promotion") != Some("none") {
            return Err(format!(
                "promotion_claimed: {:?}",
                row.str_at("requirement_id")
            ));
        }
    }

    let declared: [(&str, Option<i64>); 13] = [
        ("gate_count", root.int_at("gate_count")),
        ("gates_total", r035.int_at("gates_total")),
        ("gates_accepted", r035.int_at("gates_accepted")),
        ("gates_hold", r035.int_at("gates_hold")),
        ("gates_owner_decision", r035.int_at("gates_owner_decision")),
        ("gates_rejected", r035.int_at("gates_rejected")),
        ("leg_count", root.int_at("leg_count")),
        ("legs_total", r070.int_at("legs_total")),
        (
            "accepted_at_bounded_scope",
            r070.int_at("accepted_at_bounded_scope"),
        ),
        ("hold", r070.int_at("hold")),
        ("legs_owner_decision", r070.int_at("legs_owner_decision")),
        ("legs_rejected", r070.int_at("legs_rejected")),
        ("debt_total", root.int_at("debt_total")),
    ];
    let recomputed = [
        ("gate_count", gate_tally.total),
        ("gates_total", gate_tally.total),
        ("gates_accepted", gate_tally.accepted),
        ("gates_hold", gate_tally.hold),
        ("gates_owner_decision", gate_tally.owner_decision),
        ("gates_rejected", gate_tally.rejected),
        ("leg_count", leg_tally.total),
        ("legs_total", leg_tally.total),
        ("accepted_at_bounded_scope", leg_tally.accepted),
        ("hold", leg_tally.hold),
        ("legs_owner_decision", leg_tally.owner_decision),
        ("legs_rejected", leg_tally.rejected),
        ("debt_total", gate_tally.debt + leg_tally.debt),
    ];
    for ((label, declared), (_, live)) in declared.iter().zip(recomputed.iter()) {
        if *declared != Some(*live) {
            return Err(format!(
                "aggregate_mismatch: {label} declared={declared:?} live={live}"
            ));
        }
    }
    if gate_tally.partition() != gate_tally.total || leg_tally.partition() != leg_tally.total {
        return Err("aggregate_mismatch: disposition partition".to_string());
    }

    for row in gates {
        if row.get("proof_package") != Some(&Json::Null) {
            return Err(format!(
                "proof_package_claimed: {:?}",
                row.str_at("gate_id")
            ));
        }
    }

    let punkt = root.get("punkt").ok_or("punkt_absent")?;
    for key in ["admission", "punkt_admission"] {
        if punkt.str_at(key) != Some("not-adopted") {
            return Err(format!("punkt_admission_upgraded: {key}"));
        }
    }
    for key in ["punkt_rows_admitted", "live_punkt_rows_admitted"] {
        if punkt.int_at(key) != Some(0) {
            return Err(format!("punkt_row_minted: {key}={:?}", punkt.int_at(key)));
        }
    }
    if punkt.str_at("owner_admission_ref") != Some("none") {
        return Err("punkt_admission_upgraded: owner_admission_ref".to_string());
    }
    if punkt.str_at("decision") != Some("D540") || punkt.str_at("status") != Some("unchanged") {
        return Err("punkt_admission_upgraded: decision or status".to_string());
    }

    scan_values(root)
}

/// Every string value must stay ASCII and must never be one of the promotion
/// words this ledger is forbidden to carry as a status (D430/D416/D558).
fn scan_values(value: &Json) -> Result<(), String> {
    match value {
        Json::Str(text) => {
            if !text.is_ascii() {
                return Err(format!("non_ascii_value: {text}"));
            }
            if FORBIDDEN_VALUES.contains(&text.as_str()) {
                return Err(format!("forbidden_value: {text}"));
            }
        }
        Json::Arr(items) => {
            for item in items {
                scan_values(item)?;
            }
        }
        Json::Obj(entries) => {
            for (_, entry) in entries {
                scan_values(entry)?;
            }
        }
        Json::Null | Json::Bool(_) | Json::Num(_) => {}
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// fixtures and mutations
// ---------------------------------------------------------------------------

fn ledger() -> Json {
    JsonParser::parse(ACCEPTANCE_JSON).expect("the acceptance ledger parses")
}

fn gate_index(root: &Json, id: &str) -> usize {
    root.arr_at("gates")
        .expect("gates array")
        .iter()
        .position(|row| row.str_at("gate_id") == Some(id))
        .expect("gate id present")
}

fn leg_index(root: &Json, id: &str) -> usize {
    root.arr_at("legs")
        .expect("legs array")
        .iter()
        .position(|row| row.str_at("leg_id") == Some(id))
        .expect("leg id present")
}

fn gate_row<'a>(root: &'a mut Json, id: &str) -> &'a mut Json {
    let index = gate_index(root, id);
    root.get_mut("gates")
        .and_then(Json::as_arr_mut)
        .expect("gates array")
        .get_mut(index)
        .expect("gate row")
}

fn leg_row<'a>(root: &'a mut Json, id: &str) -> &'a mut Json {
    let index = leg_index(root, id);
    root.get_mut("legs")
        .and_then(Json::as_arr_mut)
        .expect("legs array")
        .get_mut(index)
        .expect("leg row")
}

fn rejection(root: &Json) -> String {
    check_boundary(root).expect_err("the mutated ledger must be rejected")
}

// ---------------------------------------------------------------------------
// pinned document facts
// ---------------------------------------------------------------------------

#[test]
fn ledger_parses_and_is_canonical_ascii_count_only_evidence() {
    assert!(ACCEPTANCE_JSON.is_ascii(), "the ledger stays ASCII-only");
    assert!(
        ACCEPTANCE_JSON.ends_with('\n'),
        "the ledger ends with one newline"
    );
    assert!(
        !ACCEPTANCE_JSON.trim_end_matches('\n').contains('\n'),
        "the ledger is canonical one-line JSON"
    );
    let root = ledger();
    assert_eq!(root.str_at("schema"), Some(SCHEMA));
    assert_eq!(root.str_at("lifecycle"), Some(LIFECYCLE));
    assert_eq!(
        root.get("authoritative").and_then(Json::as_bool),
        Some(false)
    );
    assert_eq!(root.get("count_only").and_then(Json::as_bool), Some(true));
    assert!(
        check_boundary(&root).is_ok(),
        "the committed ledger satisfies its own boundary"
    );
}

#[test]
fn seven_gates_and_four_legs_carry_only_the_d558_vocabulary() {
    let root = ledger();
    let gates = root.arr_at("gates").expect("gates array");
    let legs = root.arr_at("legs").expect("legs array");
    assert_eq!(gates.len(), GATE_IDS.len(), "exactly seven gate rows");
    assert_eq!(legs.len(), LEG_IDS.len(), "exactly four leg rows");
    for (index, id) in GATE_IDS.iter().enumerate() {
        assert_eq!(gates[index].str_at("gate_id"), Some(*id));
        let disposition = gates[index]
            .str_at("disposition")
            .expect("gate disposition");
        assert!(
            DISPOSITIONS.contains(&disposition),
            "gate {id} disposition {disposition} is outside D558"
        );
        assert!(
            !gates[index].arr_at("debt").expect("gate debt").is_empty(),
            "gate {id} carries its debt"
        );
    }
    for (index, id) in LEG_IDS.iter().enumerate() {
        assert_eq!(legs[index].str_at("leg_id"), Some(*id));
        let disposition = legs[index]
            .str_at("scope_disposition")
            .expect("leg disposition");
        assert!(
            DISPOSITIONS.contains(&disposition),
            "leg {id} disposition {disposition} is outside D558"
        );
        assert!(
            !legs[index].arr_at("debt").expect("leg debt").is_empty(),
            "leg {id} carries its debt"
        );
    }
}

#[test]
fn counters_and_requirement_dispositions_are_unpromoted() {
    let root = ledger();
    for counter in [
        "gates_promoted",
        "legs_promoted",
        "proof_packages_attached",
        "requirement_records_mutated",
    ] {
        assert_eq!(root.int_at(counter), Some(0), "{counter} stays at zero");
    }
    let r035 = requirement(&root, "R035").expect("R035 row");
    assert_eq!(r035.str_at("status"), Some("active"));
    assert_eq!(r035.str_at("disposition_decision"), Some("D430"));
    assert_eq!(r035.int_at("gates_total"), Some(7));
    assert_eq!(r035.int_at("gates_accepted"), Some(0));
    assert_eq!(r035.str_at("promotion"), Some("none"));
    let r070 = requirement(&root, "R070").expect("R070 row");
    assert_eq!(r070.str_at("status"), Some("active"));
    assert_eq!(r070.str_at("disposition_decision"), Some("D416"));
    assert_eq!(r070.int_at("legs_total"), Some(4));
    assert_eq!(r070.int_at("accepted_at_bounded_scope"), Some(3));
    assert_eq!(
        r070.str_at("coverage_verdict"),
        Some("incomplete-because-not-every-edition")
    );
    assert_eq!(r070.str_at("promotion"), Some("none"));
}

#[test]
fn punkt_is_not_admitted_and_mints_no_rows() {
    let root = ledger();
    let punkt = root.get("punkt").expect("punkt section");
    assert_eq!(punkt.str_at("admission"), Some("not-adopted"));
    assert_eq!(punkt.str_at("punkt_admission"), Some("not-adopted"));
    assert_eq!(punkt.int_at("punkt_rows_admitted"), Some(0));
    assert_eq!(punkt.int_at("live_punkt_rows_admitted"), Some(0));
    assert_eq!(punkt.str_at("owner_admission_ref"), Some("none"));
    assert_eq!(punkt.str_at("decision"), Some("D540"));
    assert_eq!(punkt.str_at("status"), Some("unchanged"));
    assert_eq!(
        punkt.str_at("checkpoint_path"),
        Some("prd/architecture/m209-s01-punkt-decision.md")
    );
    assert_eq!(
        punkt.arr_at("required_grant_fields").map(<[Json]>::len),
        Some(12),
        "the twelve mandatory grant fields stay named"
    );
}

#[test]
fn no_gate_row_attaches_a_proof_package() {
    let root = ledger();
    for row in root.arr_at("gates").expect("gates array") {
        assert_eq!(
            row.get("proof_package"),
            Some(&Json::Null),
            "gate {row_id:?} attaches no proof package",
            row_id = row.str_at("gate_id")
        );
    }
}

// ---------------------------------------------------------------------------
// in-memory mutation refusals
// ---------------------------------------------------------------------------

#[test]
fn boundary_rejects_a_promoted_r035_gate() {
    let mut root = ledger();
    let mut promoted = false;
    let hold_id = root
        .arr_at("gates")
        .expect("gates array")
        .iter()
        .find(|row| row.str_at("disposition") == Some("hold-with-precise-debt"))
        .and_then(|row| row.str_at("gate_id"))
        .expect("a hold gate exists")
        .to_string();
    promoted |= gate_row(&mut root, &hold_id).set(
        "disposition",
        Json::Str("accepted-at-bounded-scope".to_string()),
    );
    assert!(promoted, "the promotion mutation landed");
    let error = rejection(&root);
    assert!(error.contains("aggregate_mismatch"), "{error}");
}

#[test]
fn boundary_rejects_a_promoted_r070_leg() {
    let mut root = ledger();
    let hold_id = root
        .arr_at("legs")
        .expect("legs array")
        .iter()
        .find(|row| row.str_at("scope_disposition") == Some("hold-with-precise-debt"))
        .and_then(|row| row.str_at("leg_id"))
        .expect("a hold leg exists")
        .to_string();
    let promoted = leg_row(&mut root, &hold_id).set(
        "scope_disposition",
        Json::Str("accepted-at-bounded-scope".to_string()),
    );
    assert!(promoted, "the promotion mutation landed");
    let error = rejection(&root);
    assert!(error.contains("aggregate_mismatch"), "{error}");
}

#[test]
fn boundary_rejects_an_unknown_disposition() {
    let mut root = ledger();
    let gate_id = GATE_IDS[0];
    let swapped =
        gate_row(&mut root, gate_id).set("disposition", Json::Str("validated".to_string()));
    assert!(swapped, "the disposition mutation landed");
    let error = rejection(&root);
    assert!(error.contains("unsupported_disposition"), "{error}");
    assert!(error.contains(gate_id), "{error}");
}

#[test]
fn boundary_rejects_a_hold_row_that_dropped_its_debt() {
    let mut root = ledger();
    let hold_id = root
        .arr_at("gates")
        .expect("gates array")
        .iter()
        .find(|row| row.str_at("disposition") == Some("hold-with-precise-debt"))
        .and_then(|row| row.str_at("gate_id"))
        .expect("a hold gate exists")
        .to_string();
    let dropped = gate_row(&mut root, &hold_id).set("debt", Json::Arr(Vec::new()));
    assert!(dropped, "the debt mutation landed");
    let error = rejection(&root);
    assert!(error.contains("debt_dropped"), "{error}");
    assert!(error.contains(&hold_id), "{error}");
}

#[test]
fn boundary_rejects_authoritative_true() {
    let mut root = ledger();
    let flipped = root.set("authoritative", Json::Bool(true));
    assert!(flipped, "the authoritative flag exists and was mutated");
    let error = rejection(&root);
    assert!(error.contains("promotion_claimed"), "{error}");
}

#[test]
fn boundary_rejects_an_eighth_gate_row() {
    let mut root = ledger();
    let extra = root
        .arr_at("gates")
        .expect("gates array")
        .last()
        .expect("a gate row exists")
        .clone();
    let pushed = root
        .get_mut("gates")
        .and_then(Json::as_arr_mut)
        .map(|rows| {
            rows.push(extra);
            rows.len()
        });
    assert_eq!(pushed, Some(GATE_IDS.len() + 1), "the eighth row landed");
    let error = rejection(&root);
    assert!(error.contains("row_count"), "{error}");
}

#[test]
fn boundary_rejects_a_minted_punkt_row() {
    let mut root = ledger();
    let minted = root
        .get_mut("punkt")
        .map(|punkt| punkt.set("punkt_rows_admitted", Json::Num(1)));
    assert_eq!(minted, Some(true), "the punkt mutation landed");
    let error = rejection(&root);
    assert!(error.contains("punkt_row_minted"), "{error}");
}

#[test]
fn boundary_rejects_a_changed_requirement_status() {
    let mut root = ledger();
    let changed = root
        .arr_at("requirements")
        .expect("requirements array")
        .iter()
        .position(|row| row.str_at("requirement_id") == Some("R035"));
    let index = changed.expect("R035 row exists");
    let mutated = root
        .get_mut("requirements")
        .and_then(Json::as_arr_mut)
        .and_then(|rows| rows.get_mut(index))
        .map(|row| row.set("status", Json::Str("validated".to_string())));
    assert_eq!(mutated, Some(true), "the status mutation landed");
    let error = rejection(&root);
    assert!(error.contains("requirement_status_changed"), "{error}");
}

#[test]
fn boundary_rejects_a_requirement_promotion_marker() {
    let mut root = ledger();
    let index = root
        .arr_at("requirements")
        .expect("requirements array")
        .iter()
        .position(|row| row.str_at("requirement_id") == Some("R070"))
        .expect("R070 row exists");
    let mutated = root
        .get_mut("requirements")
        .and_then(Json::as_arr_mut)
        .and_then(|rows| rows.get_mut(index))
        .map(|row| row.set("promotion", Json::Str("promoted".to_string())));
    assert_eq!(mutated, Some(true), "the promotion mutation landed");
    let error = rejection(&root);
    assert!(error.contains("promotion_claimed"), "{error}");
}

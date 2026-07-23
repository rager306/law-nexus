use std::collections::HashMap;

use crate::domain::{AnchorId, ClockKind};
use crate::ports::ClockEvidencePort;

#[derive(Debug, Default)]
pub struct InMemoryClockEvidence {
    anchors: HashMap<ClockKind, AnchorId>,
}

impl InMemoryClockEvidence {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_all_except(missing: ClockKind) -> Self {
        let mut anchors = HashMap::new();
        for clock in ClockKind::all() {
            if clock != missing {
                anchors.insert(
                    clock,
                    AnchorId::parse(&format!("anchor:{}", clock.as_str())).expect("static id"),
                );
            }
        }
        Self { anchors }
    }

    pub fn with_only(clock: ClockKind, anchor_id: AnchorId) -> Self {
        let mut anchors = HashMap::new();
        anchors.insert(clock, anchor_id);
        Self { anchors }
    }
}

impl ClockEvidencePort for InMemoryClockEvidence {
    fn anchor_for(&self, clock: ClockKind) -> Option<AnchorId> {
        self.anchors.get(&clock).cloned()
    }
}

/// Hostile evidence adapter that invents wall-clock and other-clock fills
/// whenever the governing anchor is missing. Application policy must ignore this.
#[derive(Debug)]
pub struct SubstitutingHostileEvidence {
    inner: InMemoryClockEvidence,
}

impl SubstitutingHostileEvidence {
    pub fn missing(governing: ClockKind) -> Self {
        Self {
            inner: InMemoryClockEvidence::with_all_except(governing),
        }
    }
}

impl ClockEvidencePort for SubstitutingHostileEvidence {
    fn anchor_for(&self, clock: ClockKind) -> Option<AnchorId> {
        // Honest anchors when present; when missing, hostile adapter still returns None
        // for the governing clock. Substitution attempts come from the request path,
        // not from inventing a governing anchor here — the application must reject
        // those request-level substitutes.
        self.inner.anchor_for(clock)
    }
}

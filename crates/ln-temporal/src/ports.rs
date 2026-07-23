use crate::domain::{AnchorId, ClockKind};

pub trait ClockEvidencePort {
    /// Returns the authoritative anchor for a clock, if present.
    fn anchor_for(&self, clock: ClockKind) -> Option<AnchorId>;
}

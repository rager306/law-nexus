use crate::domain::BoundObservation;

/// Outbound bound observation. May report unknown, saturated or measured local
/// bound. Vendor numbers may be present but application must not use them as
/// capacity precision.
pub trait BoundObservationPort {
    fn observe(&self) -> BoundObservation;
}

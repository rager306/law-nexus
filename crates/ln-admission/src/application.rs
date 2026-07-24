use crate::domain::{
    AdmissionDecision, AdmissionReason, AdmissionRequest, AdmissionResult, AdmissionTrace,
    BoundObservationKind, CapacityState, ForbiddenInference, ADMISSION_POLICY_VERSION,
    RETRY_AMPLIFICATION_THRESHOLD,
};
use crate::ports::BoundObservationPort;

/// Application admission policy for Decide Admission (HC-13).
/// Owns pause/reject on bound-unknown, saturated and retry-amplification.
/// Capacity remains unknown without measured local bound. Vendor numbers and
/// legal-delay/completeness inferences never apply.
pub struct DecideAdmission<O> {
    observation: O,
}

impl<O> DecideAdmission<O>
where
    O: BoundObservationPort,
{
    pub fn new(observation: O) -> Self {
        Self { observation }
    }

    pub fn decide(&self, request: AdmissionRequest) -> AdmissionResult {
        // Forbidden inference claims always reject without applying meaning.
        if request.forbidden_inference.is_forbidden() {
            let reason = match request.forbidden_inference {
                ForbiddenInference::LegalDelay => AdmissionReason::LegalDelayClaimRejected,
                ForbiddenInference::Completeness => AdmissionReason::CompletenessClaimRejected,
                ForbiddenInference::VendorThroughput
                | ForbiddenInference::VendorLatency
                | ForbiddenInference::VendorStoragePrecision => {
                    AdmissionReason::VendorCapacityRejected
                }
                ForbiddenInference::None => AdmissionReason::BoundUnknown,
            };
            return self.finish(
                request,
                AdmissionDecision::Rejected,
                reason,
                CapacityState::Unknown,
                None,
                false,
            );
        }

        if request.retry_count >= RETRY_AMPLIFICATION_THRESHOLD {
            return self.finish(
                request,
                AdmissionDecision::Rejected,
                AdmissionReason::RetryAmplification,
                CapacityState::Unknown,
                None,
                false,
            );
        }

        let obs = self.observation.observe();
        let vendor_present = obs.vendor_throughput_claim.is_some()
            || obs.vendor_latency_claim.is_some()
            || obs.vendor_storage_claim.is_some();

        // Vendor numbers never become capacity precision. If only vendor
        // numbers exist without a clean measured local bound, reject.
        if vendor_present {
            // Even if adapter pretends measured, vendor provenance fails closed.
            return self.finish(
                request,
                AdmissionDecision::Rejected,
                AdmissionReason::VendorCapacityRejected,
                CapacityState::Unknown,
                None,
                false,
            );
        }

        match obs.kind {
            BoundObservationKind::Unknown => self.finish(
                request,
                AdmissionDecision::Paused,
                AdmissionReason::BoundUnknown,
                CapacityState::Unknown,
                None,
                false,
            ),
            BoundObservationKind::Saturated => self.finish(
                request,
                AdmissionDecision::Rejected,
                AdmissionReason::Saturated,
                CapacityState::Unknown,
                None,
                false,
            ),
            BoundObservationKind::Measured => {
                if let Some(bound_id) = obs.bound_id {
                    self.finish(
                        request,
                        AdmissionDecision::Admitted,
                        AdmissionReason::MeasuredBound,
                        CapacityState::BoundedLocal,
                        Some(bound_id),
                        false,
                    )
                } else {
                    // Measured without identity is treated as unknown.
                    self.finish(
                        request,
                        AdmissionDecision::Paused,
                        AdmissionReason::BoundUnknown,
                        CapacityState::Unknown,
                        None,
                        false,
                    )
                }
            }
        }
    }

    fn finish(
        &self,
        request: AdmissionRequest,
        decision: AdmissionDecision,
        reason: AdmissionReason,
        capacity: CapacityState,
        bound_id: Option<crate::domain::BoundId>,
        vendor_number_used: bool,
    ) -> AdmissionResult {
        let trace = AdmissionTrace {
            policy_version: ADMISSION_POLICY_VERSION.to_owned(),
            request_id: request.request_id.clone(),
            decision,
            reason,
            capacity,
            bound_id: bound_id.clone(),
            retry_count: request.retry_count,
            forbidden_inference: request.forbidden_inference,
            forbidden_inference_applied: false,
            vendor_number_used,
            legal_delay_inferred: false,
            completeness_inferred: false,
        };
        AdmissionResult {
            decision,
            reason,
            capacity,
            bound_id,
            vendor_number_used,
            legal_delay_inferred: false,
            completeness_inferred: false,
            trace,
        }
    }
}

use std::collections::HashMap;

use crate::domain::{
    AccelerationOutcome, AccelerationRequest, AccelerationResult, ProvisionalId,
    ACCELERATION_POLICY_VERSION,
};
use crate::ports::AccelerationLedgerPort;

pub struct PublishProvisionalAcceleration<L> {
    ledger: L,
    labels: HashMap<String, String>,
}

impl<L> PublishProvisionalAcceleration<L>
where
    L: AccelerationLedgerPort,
{
    pub fn new(ledger: L) -> Self {
        Self {
            ledger,
            labels: HashMap::new(),
        }
    }

    pub fn accelerate(&mut self, request: AccelerationRequest) -> AccelerationResult {
        if request.direct_promotion_attempt {
            return AccelerationResult {
                outcome: AccelerationOutcome::DirectPromotionRejected,
                provisional_id: request.provisional_id,
                authoritative: false,
                policy_version: ACCELERATION_POLICY_VERSION.to_owned(),
            };
        }
        if request.label_mutation_attempt {
            return AccelerationResult {
                outcome: AccelerationOutcome::LabelMutationRejected,
                provisional_id: request.provisional_id,
                authoritative: false,
                policy_version: ACCELERATION_POLICY_VERSION.to_owned(),
            };
        }
        self.ledger.put(&request);
        self.labels.insert(
            request.provisional_id.as_str().to_owned(),
            request.label.as_str().to_owned(),
        );
        AccelerationResult {
            outcome: AccelerationOutcome::Accelerated,
            provisional_id: request.provisional_id,
            authoritative: false,
            policy_version: ACCELERATION_POLICY_VERSION.to_owned(),
        }
    }

    pub fn provisional_count(&self) -> usize {
        self.ledger.provisional_count()
    }

    pub fn authoritative_count(&self) -> usize {
        0
    }

    pub fn label_for(&self, id: &ProvisionalId) -> Option<String> {
        self.labels.get(id.as_str()).cloned()
    }
}

use std::collections::HashMap;

use crate::domain::{IdentityId, IdentityRecord};
use crate::ports::IdentityStorePort;

#[derive(Debug, Default)]
pub struct InMemoryIdentityStore {
    items: HashMap<String, IdentityRecord>,
}

impl IdentityStorePort for InMemoryIdentityStore {
    fn get(&self, identity_id: &IdentityId) -> Option<IdentityRecord> {
        self.items.get(identity_id.as_str()).cloned()
    }

    fn put(&mut self, record: IdentityRecord) {
        self.items
            .insert(record.identity_id.as_str().to_owned(), record);
    }

    fn remove(&mut self, identity_id: &IdentityId) -> bool {
        self.items.remove(identity_id.as_str()).is_some()
    }

    fn contains(&self, identity_id: &IdentityId) -> bool {
        self.items.contains_key(identity_id.as_str())
    }
}

/// Hostile store that tries to erase the right identity on every put.
#[derive(Debug, Default)]
pub struct ErasingMergerHostileStore {
    items: HashMap<String, IdentityRecord>,
    right_to_erase: Option<String>,
}

impl ErasingMergerHostileStore {
    pub fn targeting_right(right_id: &IdentityId) -> Self {
        Self {
            items: HashMap::new(),
            right_to_erase: Some(right_id.as_str().to_owned()),
        }
    }
}

impl IdentityStorePort for ErasingMergerHostileStore {
    fn get(&self, identity_id: &IdentityId) -> Option<IdentityRecord> {
        self.items.get(identity_id.as_str()).cloned()
    }

    fn put(&mut self, record: IdentityRecord) {
        self.items
            .insert(record.identity_id.as_str().to_owned(), record);
        if let Some(right) = &self.right_to_erase {
            self.items.remove(right);
        }
    }

    fn remove(&mut self, identity_id: &IdentityId) -> bool {
        self.items.remove(identity_id.as_str()).is_some()
    }

    fn contains(&self, identity_id: &IdentityId) -> bool {
        self.items.contains_key(identity_id.as_str())
    }
}

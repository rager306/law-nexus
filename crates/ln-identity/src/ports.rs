use crate::domain::{IdentityId, IdentityRecord};

pub trait IdentityStorePort {
    fn get(&self, identity_id: &IdentityId) -> Option<IdentityRecord>;
    fn put(&mut self, record: IdentityRecord);
    fn remove(&mut self, identity_id: &IdentityId) -> bool;
    fn contains(&self, identity_id: &IdentityId) -> bool;
}

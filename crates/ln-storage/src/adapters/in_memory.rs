use std::cell::RefCell;
use std::collections::BTreeMap;

use crate::{
    GraphEdge, GraphNode, GraphStorePort, StorageError, VectorQuery, VectorRecord, VectorStorePort,
};

/// Operation journal event for deterministic replay.
#[derive(Debug, Clone, PartialEq)]
pub enum OperationEvent {
    VectorStored { record: VectorRecord },
    VectorQueried { top_k: usize },
    GraphNodeUpserted { node: GraphNode },
    GraphEdgeUpserted { edge: GraphEdge },
    GraphNodesQueried { label: String },
}

/// Deterministic operation journal.
#[derive(Debug, Clone, Default)]
pub struct OperationJournal {
    events: Vec<OperationEvent>,
}

impl OperationJournal {
    pub fn events(&self) -> &[OperationEvent] {
        &self.events
    }

    fn push(&mut self, event: OperationEvent) {
        self.events.push(event);
    }
}

/// In-memory vector store implementing VectorStorePort.
pub struct InMemoryVectorStore {
    records: BTreeMap<String, VectorRecord>,
    journal: RefCell<OperationJournal>,
}

impl InMemoryVectorStore {
    pub fn new() -> Self {
        Self {
            records: BTreeMap::new(),
            journal: RefCell::new(OperationJournal::default()),
        }
    }

    pub fn journal(&self) -> OperationJournal {
        self.journal.borrow().clone()
    }

    pub fn replay(&mut self, journal: &OperationJournal) -> Result<(), StorageError> {
        self.records.clear();
        self.journal.replace(OperationJournal::default());
        for event in journal.events() {
            if let OperationEvent::VectorStored { record } = event {
                self.store(record)?;
            }
        }
        Ok(())
    }
}

impl Default for InMemoryVectorStore {
    fn default() -> Self {
        Self::new()
    }
}

impl crate::VectorStorePort for InMemoryVectorStore {
    fn store(&mut self, record: &VectorRecord) -> Result<(), StorageError> {
        if record.id().trim().is_empty() {
            return Err(StorageError::EmptyInput);
        }
        self.records.insert(record.id().to_owned(), record.clone());
        self.journal
            .borrow_mut()
            .push(OperationEvent::VectorStored {
                record: record.clone(),
            });
        Ok(())
    }

    fn query(&self, query: &VectorQuery) -> Result<Vec<VectorRecord>, StorageError> {
        if query.top_k() == 0 {
            return Err(StorageError::EmptyInput);
        }
        // Rank by real cosine similarity to the query vector, then take the
        // top_k most similar. This replaces the prior truncate-by-key-order path
        // that ignored the query vector entirely (M161).
        let mut scored: Vec<(f64, VectorRecord)> = self
            .records
            .values()
            .map(|record| {
                let score = crate::cosine_similarity(query.vector(), record.vector())?;
                Ok((score, record.clone()))
            })
            .collect::<Result<Vec<_>, _>>()?;
        // Stable sort by score descending; ties keep insertion (key) order so
        // ranking is deterministic.
        scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
        let results: Vec<VectorRecord> = scored
            .into_iter()
            .take(query.top_k())
            .map(|(_, record)| record)
            .collect();
        self.journal
            .borrow_mut()
            .push(OperationEvent::VectorQueried {
                top_k: query.top_k(),
            });
        Ok(results)
    }
}

/// In-memory graph store implementing GraphStorePort.
pub struct InMemoryGraphStore {
    nodes: BTreeMap<String, GraphNode>,
    edges: Vec<GraphEdge>,
    journal: RefCell<OperationJournal>,
}

impl InMemoryGraphStore {
    pub fn new() -> Self {
        Self {
            nodes: BTreeMap::new(),
            edges: Vec::new(),
            journal: RefCell::new(OperationJournal::default()),
        }
    }

    pub fn journal(&self) -> OperationJournal {
        self.journal.borrow().clone()
    }

    pub fn replay(&mut self, journal: &OperationJournal) -> Result<(), StorageError> {
        self.nodes.clear();
        self.edges.clear();
        self.journal.replace(OperationJournal::default());
        for event in journal.events() {
            match event {
                OperationEvent::GraphNodeUpserted { node } => self.upsert_node(node)?,
                OperationEvent::GraphEdgeUpserted { edge } => self.upsert_edge(edge)?,
                _ => {}
            }
        }
        Ok(())
    }
}

impl Default for InMemoryGraphStore {
    fn default() -> Self {
        Self::new()
    }
}

impl crate::GraphStorePort for InMemoryGraphStore {
    fn upsert_node(&mut self, node: &GraphNode) -> Result<(), StorageError> {
        self.nodes.insert(node.id().to_owned(), node.clone());
        self.journal
            .borrow_mut()
            .push(OperationEvent::GraphNodeUpserted { node: node.clone() });
        Ok(())
    }

    fn upsert_edge(&mut self, edge: &GraphEdge) -> Result<(), StorageError> {
        self.edges.retain(|existing| {
            !(existing.source() == edge.source() && existing.target() == edge.target())
        });
        self.edges.push(edge.clone());
        self.journal
            .borrow_mut()
            .push(OperationEvent::GraphEdgeUpserted { edge: edge.clone() });
        Ok(())
    }

    fn query_nodes(&self, label: &str) -> Result<Vec<GraphNode>, StorageError> {
        let results: Vec<GraphNode> = self
            .nodes
            .values()
            .filter(|node| node.label() == label)
            .cloned()
            .collect();
        self.journal
            .borrow_mut()
            .push(OperationEvent::GraphNodesQueried {
                label: label.to_owned(),
            });
        Ok(results)
    }
}

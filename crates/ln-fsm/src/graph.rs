//! Declarative transition-graph specification, structural validator, and
//! Mermaid `stateDiagram-v2` generator.
//!
//! Closes the Rust `_ => None` match blind spot by checking reachability,
//! terminal isolation, non-terminal dead ends, self-loop traps, duplicate
//! edges/terminals, determinism, and explicit forbidden direct edges over a
//! machine's declared transition graph.

use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::fmt::Write as _;

/// One declared edge in an FSM transition graph.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct EdgeSpec {
    pub from: &'static str,
    pub event: &'static str,
    pub to: &'static str,
}

/// An explicit direct transition that MUST NOT exist in the graph
/// (for example `Proposed -> AuthoritativeInternal` in assertion lifecycle).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct ForbiddenEdge {
    pub from: &'static str,
    pub to: &'static str,
    pub rationale: &'static str,
}

/// Declarative structural specification of a finite state machine.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GraphSpec {
    pub name: &'static str,
    pub initial: &'static str,
    pub states: &'static [&'static str],
    pub terminals: &'static [&'static str],
    pub transitions: &'static [EdgeSpec],
    pub forbidden_direct_edges: &'static [ForbiddenEdge],
    /// When `false`, the same `(from, event)` pair targeting two distinct `to`
    /// states is reported as [`GraphDefect::NonDeterministicEdge`].
    pub allow_guarded_branching: bool,
}

/// Summary produced when [`validate_graph`] succeeds with zero defects.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GraphReport {
    pub name: &'static str,
    pub state_count: usize,
    pub terminal_count: usize,
    pub edge_count: usize,
    pub reachable_count: usize,
}

/// Structural defect detected in a [`GraphSpec`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GraphDefect {
    EmptyStates,
    DuplicateState(&'static str),
    UnknownInitialState(&'static str),
    InitialStateIsTerminal(&'static str),
    UnknownTerminalState(&'static str),
    DuplicateTerminalState(&'static str),
    UnknownTransitionEndpoint {
        from: &'static str,
        event: &'static str,
        to: &'static str,
        unknown: &'static str,
    },
    DuplicateEdge {
        from: &'static str,
        event: &'static str,
        to: &'static str,
    },
    OutgoingFromTerminal {
        from: &'static str,
        event: &'static str,
        to: &'static str,
    },
    UnreachableState(&'static str),
    NonTerminalDeadEnd(&'static str),
    NonTerminalSelfLoopTrap(&'static str),
    UnknownForbiddenEdgeEndpoint {
        from: &'static str,
        to: &'static str,
        unknown: &'static str,
    },
    ForbiddenDirectEdgePresent {
        from: &'static str,
        to: &'static str,
        event: &'static str,
        rationale: &'static str,
    },
    NonDeterministicEdge {
        from: &'static str,
        event: &'static str,
        first_to: &'static str,
        second_to: &'static str,
    },
}

/// Validate a declarative [`GraphSpec`].
///
/// Checks are deterministic and collect every defect instead of stopping at the first.
pub fn validate_graph(spec: &GraphSpec) -> Result<GraphReport, Vec<GraphDefect>> {
    let mut defects = Vec::new();

    if spec.states.is_empty() {
        defects.push(GraphDefect::EmptyStates);
        return Err(defects);
    }

    let mut known_states = BTreeSet::new();
    for &state in spec.states {
        if !known_states.insert(state) {
            defects.push(GraphDefect::DuplicateState(state));
        }
    }

    if !known_states.contains(spec.initial) {
        defects.push(GraphDefect::UnknownInitialState(spec.initial));
    }

    let mut terminal_set = BTreeSet::new();
    for &term in spec.terminals {
        if !known_states.contains(term) {
            defects.push(GraphDefect::UnknownTerminalState(term));
        } else if !terminal_set.insert(term) {
            defects.push(GraphDefect::DuplicateTerminalState(term));
        }
    }

    if terminal_set.contains(spec.initial) {
        defects.push(GraphDefect::InitialStateIsTerminal(spec.initial));
    }

    for forbidden in spec.forbidden_direct_edges {
        if !known_states.contains(forbidden.from) {
            defects.push(GraphDefect::UnknownForbiddenEdgeEndpoint {
                from: forbidden.from,
                to: forbidden.to,
                unknown: forbidden.from,
            });
        }
        if !known_states.contains(forbidden.to) {
            defects.push(GraphDefect::UnknownForbiddenEdgeEndpoint {
                from: forbidden.from,
                to: forbidden.to,
                unknown: forbidden.to,
            });
        }
    }

    let mut adjacency: BTreeMap<&'static str, Vec<&'static str>> = BTreeMap::new();
    let mut seen_edges: BTreeSet<(&'static str, &'static str, &'static str)> = BTreeSet::new();
    let mut seen_from_event: BTreeMap<(&'static str, &'static str), &'static str> = BTreeMap::new();

    for edge in spec.transitions {
        let mut valid_endpoints = true;
        if !known_states.contains(edge.from) {
            defects.push(GraphDefect::UnknownTransitionEndpoint {
                from: edge.from,
                event: edge.event,
                to: edge.to,
                unknown: edge.from,
            });
            valid_endpoints = false;
        }
        if !known_states.contains(edge.to) {
            defects.push(GraphDefect::UnknownTransitionEndpoint {
                from: edge.from,
                event: edge.event,
                to: edge.to,
                unknown: edge.to,
            });
            valid_endpoints = false;
        }

        if !seen_edges.insert((edge.from, edge.event, edge.to)) {
            defects.push(GraphDefect::DuplicateEdge {
                from: edge.from,
                event: edge.event,
                to: edge.to,
            });
        }

        if terminal_set.contains(edge.from) {
            defects.push(GraphDefect::OutgoingFromTerminal {
                from: edge.from,
                event: edge.event,
                to: edge.to,
            });
        }

        if !spec.allow_guarded_branching {
            if let Some(&first_to) = seen_from_event.get(&(edge.from, edge.event)) {
                if first_to != edge.to {
                    defects.push(GraphDefect::NonDeterministicEdge {
                        from: edge.from,
                        event: edge.event,
                        first_to,
                        second_to: edge.to,
                    });
                }
            } else {
                seen_from_event.insert((edge.from, edge.event), edge.to);
            }
        }

        for forbidden in spec.forbidden_direct_edges {
            if edge.from == forbidden.from && edge.to == forbidden.to {
                defects.push(GraphDefect::ForbiddenDirectEdgePresent {
                    from: edge.from,
                    to: edge.to,
                    event: edge.event,
                    rationale: forbidden.rationale,
                });
            }
        }

        if valid_endpoints {
            adjacency.entry(edge.from).or_default().push(edge.to);
        }
    }

    // BFS reachability from initial.
    let mut reachable = BTreeSet::new();
    if known_states.contains(spec.initial) {
        let mut queue = VecDeque::new();
        reachable.insert(spec.initial);
        queue.push_back(spec.initial);
        while let Some(state) = queue.pop_front() {
            if let Some(neighbors) = adjacency.get(state) {
                for &next in neighbors {
                    if reachable.insert(next) {
                        queue.push_back(next);
                    }
                }
            }
        }
    }

    for &state in &known_states {
        if !reachable.contains(state) {
            defects.push(GraphDefect::UnreachableState(state));
        }
        if !terminal_set.contains(state) {
            match adjacency.get(state) {
                None => defects.push(GraphDefect::NonTerminalDeadEnd(state)),
                Some(edges) if edges.is_empty() => {
                    defects.push(GraphDefect::NonTerminalDeadEnd(state));
                }
                Some(edges) if edges.iter().all(|&to| to == state) => {
                    defects.push(GraphDefect::NonTerminalSelfLoopTrap(state));
                }
                Some(_) => {}
            }
        }
    }

    if defects.is_empty() {
        Ok(GraphReport {
            name: spec.name,
            state_count: known_states.len(),
            terminal_count: terminal_set.len(),
            edge_count: seen_edges.len(),
            reachable_count: reachable.len(),
        })
    } else {
        Err(defects)
    }
}

/// Render a Mermaid `stateDiagram-v2` directly from a [`GraphSpec`].
pub fn to_mermaid_state_diagram(spec: &GraphSpec) -> String {
    let mut out = String::new();
    let _ = writeln!(out, "stateDiagram-v2");
    let _ = writeln!(out, "    [*] --> {}", spec.initial);
    for edge in spec.transitions {
        let _ = writeln!(out, "    {} --> {}: {}", edge.from, edge.to, edge.event);
    }
    for &terminal in spec.terminals {
        let _ = writeln!(out, "    {terminal} --> [*]");
    }
    out
}

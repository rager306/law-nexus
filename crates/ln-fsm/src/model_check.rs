//! Offline, zero-dependency deterministic model-based property checker for
//! [`DeterministicFsm`] implementations.
//!
//! Uses a deterministic SplitMix64 PRNG so every run is 100% reproducible
//! across 32-bit and 64-bit targets. Automatically shrinks any failing event
//! sequence to a 1-minimal reproducing subsequence without panicking even on
//! flaky/non-deterministic implementations.

use crate::{DeterministicFsm, RejectionKind, TransitionReceipt, TransitionRejection};

/// Configuration for [`run_deterministic_model_check`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ModelCheckConfig {
    pub seed: u64,
    pub sequences: usize,
    pub max_len: usize,
}

impl Default for ModelCheckConfig {
    fn default() -> Self {
        Self {
            seed: 0x4C41_574E_4558_5553, // "LAWNEXUS"
            sequences: 256,
            max_len: 32,
        }
    }
}

/// Summary returned when all explored sequences satisfy every invariant.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ModelCheckReport {
    pub sequences_run: usize,
    pub steps_executed: usize,
    pub accepted_steps: usize,
    pub rejected_steps: usize,
}

/// Shrunk counterexample when a property fails.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ModelCheckFailure<S, E> {
    pub reason: String,
    pub minimal_events: Vec<E>,
    pub failing_state: S,
    pub failing_event: E,
}

/// Deterministic SplitMix64 generator (zero external dependencies).
struct SplitMix64(u64);

impl SplitMix64 {
    fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    fn gen_range(&mut self, upper: usize) -> usize {
        if upper <= 1 {
            return 0;
        }
        (self.next_u64() % (upper as u64)) as usize
    }
}

type StepOutcome<'a, M> = Result<
    &'a TransitionReceipt<<M as DeterministicFsm>::State, <M as DeterministicFsm>::Event>,
    &'a TransitionRejection<
        <M as DeterministicFsm>::State,
        <M as DeterministicFsm>::Event,
        <M as DeterministicFsm>::RejectionReason,
    >,
>;

struct SequenceError<S, E> {
    reason: String,
    state: S,
    event: E,
}

type SequenceResult<S, E> = Result<(usize, usize), SequenceError<S, E>>;

fn check_sequence<M, F>(
    machine: &M,
    initial: &M::State,
    events: &[M::Event],
    invariant: &F,
) -> SequenceResult<M::State, M::Event>
where
    M: DeterministicFsm,
    F: Fn(&M::State, &M::Event, StepOutcome<'_, M>) -> Result<(), String>,
{
    let mut state = initial.clone();
    let mut accepted = 0usize;
    let mut rejected = 0usize;

    for event in events {
        let was_terminal = machine.is_terminal(&state);
        if was_terminal != machine.is_terminal(&state) {
            return Err(SequenceError {
                reason: "INV-01 violation: non-deterministic is_terminal result".to_owned(),
                state,
                event: event.clone(),
            });
        }

        let first = machine.apply(state.clone(), event.clone());
        let second = machine.apply(state.clone(), event.clone());

        // INV-01: repeated application on identical (state, event) must be identical.
        if first != second {
            return Err(SequenceError {
                reason: "INV-01 violation: non-deterministic transition outcome".to_owned(),
                state,
                event: event.clone(),
            });
        }

        if was_terminal {
            match &first {
                Ok(_) => {
                    return Err(SequenceError {
                        reason: "terminal-state violation: transition accepted from terminal state"
                            .to_owned(),
                        state,
                        event: event.clone(),
                    });
                }
                Err(rej) if rej.kind != RejectionKind::TerminalState => {
                    return Err(SequenceError {
                        reason: format!(
                            "terminal-state violation: expected RejectionKind::TerminalState, got {:?}",
                            rej.kind
                        ),
                        state,
                        event: event.clone(),
                    });
                }
                Err(_) => {}
            }
        } else if matches!(&first, Err(rej) if rej.kind == RejectionKind::TerminalState) {
            return Err(SequenceError {
                reason: "terminal-state violation: non-terminal state returned RejectionKind::TerminalState"
                    .to_owned(),
                state,
                event: event.clone(),
            });
        }

        let outcome_ref = match &first {
            Ok(receipt) => Ok(receipt),
            Err(rej) => Err(rej),
        };
        if let Err(reason) = invariant(&state, event, outcome_ref) {
            return Err(SequenceError {
                reason,
                state,
                event: event.clone(),
            });
        }

        match first {
            Ok(receipt) => {
                accepted += 1;
                state = receipt.next;
            }
            Err(rej) => {
                rejected += 1;
                // Fail-closed invariant: rejected transition never mutates state.
                if rej.state != state {
                    return Err(SequenceError {
                        reason: "INV-10 violation: rejection returned mutated state".to_owned(),
                        state,
                        event: event.clone(),
                    });
                }
            }
        }
    }

    Ok((accepted, rejected))
}

fn shrink_sequence<M, F>(
    machine: &M,
    initial: &M::State,
    mut candidate: Vec<M::Event>,
    initial_err: SequenceError<M::State, M::Event>,
    invariant: &F,
) -> ModelCheckFailure<M::State, M::Event>
where
    M: DeterministicFsm,
    F: Fn(&M::State, &M::Event, StepOutcome<'_, M>) -> Result<(), String>,
{
    let mut last_err = initial_err;

    // 1. Shrink to shortest failing prefix.
    for prefix_len in 1..candidate.len() {
        if let Err(err) = check_sequence(machine, initial, &candidate[..prefix_len], invariant) {
            candidate.truncate(prefix_len);
            last_err = err;
            break;
        }
    }

    // 2. Fixed-point deletion pass until 1-minimal (no single event can be removed).
    loop {
        let mut changed = false;
        let mut idx = 0;
        while idx < candidate.len() && candidate.len() > 1 {
            let mut shorter = Vec::with_capacity(candidate.len() - 1);
            shorter.extend_from_slice(&candidate[..idx]);
            shorter.extend_from_slice(&candidate[idx + 1..]);
            if let Err(err) = check_sequence(machine, initial, &shorter, invariant) {
                candidate = shorter;
                last_err = err;
                changed = true;
            } else {
                idx += 1;
            }
        }
        if !changed {
            break;
        }
    }

    ModelCheckFailure {
        reason: last_err.reason,
        minimal_events: candidate,
        failing_state: last_err.state,
        failing_event: last_err.event,
    }
}

/// Explore seeded event sequences over `machine`, checking:
/// 1. Determinism (`INV-01`) on both `is_terminal` and `apply`;
/// 2. Terminal state immutability (`RejectionKind::TerminalState`) and its converse;
/// 3. State preservation on every rejection (`INV-10`);
/// 4. Caller-supplied domain `invariant`.
///
/// On failure, returns a deterministically shrunk [`ModelCheckFailure`].
pub fn run_deterministic_model_check<M, F>(
    machine: &M,
    initial: M::State,
    alphabet: &[M::Event],
    config: ModelCheckConfig,
    invariant: F,
) -> Result<ModelCheckReport, ModelCheckFailure<M::State, M::Event>>
where
    M: DeterministicFsm,
    F: Fn(&M::State, &M::Event, StepOutcome<'_, M>) -> Result<(), String>,
{
    if alphabet.is_empty() || config.sequences == 0 || config.max_len == 0 {
        return Ok(ModelCheckReport {
            sequences_run: 0,
            steps_executed: 0,
            accepted_steps: 0,
            rejected_steps: 0,
        });
    }

    let mut rng = SplitMix64(config.seed);
    let mut steps_executed = 0usize;
    let mut accepted_steps = 0usize;
    let mut rejected_steps = 0usize;

    for _ in 0..config.sequences {
        let len = 1 + rng.gen_range(config.max_len);
        let mut events = Vec::with_capacity(len);
        for _ in 0..len {
            events.push(alphabet[rng.gen_range(alphabet.len())].clone());
        }

        match check_sequence(machine, &initial, &events, &invariant) {
            Ok((acc, rej)) => {
                steps_executed += acc + rej;
                accepted_steps += acc;
                rejected_steps += rej;
            }
            Err(err) => {
                return Err(shrink_sequence(machine, &initial, events, err, &invariant));
            }
        }
    }

    Ok(ModelCheckReport {
        sequences_run: config.sequences,
        steps_executed,
        accepted_steps,
        rejected_steps,
    })
}

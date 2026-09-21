"""
decision_trace.py  —  Pillar 2 (Explainability)

THE ASK TO MEMBER 1 (decision-engine):
-------------------------------------
Pillar 2's whole claim is that explanations are generated *inside* the decision
step, not reconstructed afterwards. That is only true if the agent hands over
what it actually computed. This file defines the minimum it must hand over.

Member 1 does not need to change how the DRL agent learns. They only need to
stop throwing away the intermediate values the forward pass already produces.

Nothing here imports torch / numpy / gymnasium, so Member 1's training code and
Pillar 2's explanation code stay independently testable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Callable, Sequence

# Type of the agent's forward function: a feature vector in, one score per
# action out (Q-values for DQN, logits or probabilities for a policy network).
# It must be side-effect free — the explainer calls it extra times for ablation.
ScoreFn = Callable[[Sequence[float]], Sequence[float]]


@dataclass(frozen=True)
class DecisionTrace:
    """Everything the agent knew at the instant it chose an action.

    Captured during the decision, never rebuilt later. If a field is None the
    explainer degrades gracefully and says so in the explanation rather than
    inventing a reason.
    """

    # --- what was being decided about ---
    alert_ids: list[str]
    feature_names: list[str]
    feature_values: list[float]

    # --- what the network actually output ---
    action_names: list[str]
    action_scores: list[float]          # one score per action, ALL actions
    chosen_action_index: int

    # --- attribution evidence (filled in by the explainer's ablation pass) ---
    # ablation_scores[i] = action_scores if feature i were replaced by its
    # neutral/baseline value. Same length as feature_names.
    ablation_scores: list[list[float]] | None = None

    # --- context from the other components ---
    matched_pattern_id: str | None = None        # from the local Knowledge Base
    matched_pattern_similarity: float | None = None
    shadow_deviation: dict[str, float] | None = None  # z-scores vs Behavioural Shadow
    peer_alert_ids: list[str] = field(default_factory=list)  # alerts that arrived from Pillar 4
    # Pillar 4 conflict-resolution result, if this decision went to a vote.
    # Keys used: overridden, label, score, peer_triggered, origin_peer, peer_voter_ids
    consensus: dict | None = None

    # --- provenance, so an explanation can be reproduced months later ---
    policy_version: str = "unversioned"
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if len(self.feature_names) != len(self.feature_values):
            raise ValueError("feature_names and feature_values must be the same length")
        if len(self.action_names) != len(self.action_scores):
            raise ValueError("action_names and action_scores must be the same length")
        if not 0 <= self.chosen_action_index < len(self.action_names):
            raise ValueError("chosen_action_index is out of range")
        if self.ablation_scores is not None and len(self.ablation_scores) != len(self.feature_names):
            raise ValueError("ablation_scores must have one entry per feature")

    @property
    def chosen_action(self) -> str:
        return self.action_names[self.chosen_action_index]

    def to_dict(self) -> dict:
        return asdict(self)


def neutral_baseline(feature_values: Sequence[float]) -> list[float]:
    """Default 'feature switched off' vector used for ablation.

    Zero is the right neutral value only if Member 3's features are normalised
    (z-scores, ratios-to-normal). If they are raw counts, replace this with the
    Behavioural Shadow's rolling mean for each feature — the explainer takes
    the baseline as an argument precisely so this can be swapped.
    """
    return [0.0] * len(feature_values)

"""
explainer.py  —  Pillar 2 (Explainability)

Produces an Explanation for every Decision, at the same instant, from values
the agent actually computed.

The public entry point is `decide_and_explain(...)`. Use it instead of calling
the agent's forward pass directly: it returns the Decision and the Explanation
together, so a decision without an explanation is not representable in the
pipeline. That structural guarantee is the pillar — not the prose quality of
the sentence at the end.

Attribution method: leave-one-out ablation on the action-score margin.
  contribution(f) = margin(full input) - margin(input with f neutralised)
  margin          = score(chosen action) - best score among the other actions

Why this and not SHAP/LIME:
  * it is computed from the live policy network during the decision, not from a
    surrogate model fitted afterwards;
  * it costs one extra forward pass per feature (≈10 for our state space), which
    an edge device can afford, where sampling-based SHAP cannot;
  * the sign is meaningful — positive means the feature pushed the agent
    *towards* the action it took;
  * it is directly testable (see test_faithfulness.py), so we can report a
    measured faithfulness number rather than asserting transparency.

Honest limitation to state in the report: leave-one-out misses interactions
between features that only matter jointly. It is a faithful account of each
feature's individual marginal effect on this decision, not a complete causal
account of the policy. That is still strictly stronger than the reference
system's post-hoc reconstruction, and we can show it.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Sequence

from decision_trace import DecisionTrace, ScoreFn, neutral_baseline

def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


# Actions ordered by how disruptive they are. Used only for wording.
ACTION_SEVERITY = {"ignore": 0, "monitor": 1, "rate_limit": 2, "block": 3, "quarantine": 3}


# ---------------------------------------------------------------- confidence

def softmax_confidence(scores: Sequence[float], chosen: int) -> float:
    """Confidence as the softmax probability of the chosen action.

    Reported honestly: for a DQN this is a monotone transform of the Q-value
    margin, not a calibrated probability of being correct. We call it
    'decision confidence' everywhere, never 'probability the alert is an attack'.
    """
    top = max(scores)
    exps = [math.exp(s - top) for s in scores]
    return exps[chosen] / sum(exps)


def score_margin(scores: Sequence[float], chosen: int) -> float:
    """How far ahead the chosen action was. 0 means a coin flip."""
    others = [s for i, s in enumerate(scores) if i != chosen]
    return scores[chosen] - max(others) if others else 0.0


# ---------------------------------------------------------------- attribution

def attribute(trace: DecisionTrace) -> dict[str, float]:
    """Signed contribution of each feature to the chosen action's margin."""
    if trace.ablation_scores is None:
        return {}
    full = score_margin(trace.action_scores, trace.chosen_action_index)
    out: dict[str, float] = {}
    for name, ablated in zip(trace.feature_names, trace.ablation_scores):
        out[name] = full - score_margin(ablated, trace.chosen_action_index)
    return out


def normalise(weights: dict[str, float]) -> dict[str, float]:
    """Scale to fractions of total absolute influence, keeping sign.

    Dashboard-friendly, and makes explanations comparable across decisions with
    very different Q-value scales.
    """
    total = sum(abs(v) for v in weights.values())
    if total == 0:
        return {k: 0.0 for k in weights}
    return {k: v / total for k, v in weights.items()}


# ---------------------------------------------------------------- wording

def _describe(name: str, weight: float, trace: DecisionTrace) -> str:
    dev = (trace.shadow_deviation or {}).get(name)
    if dev is not None and abs(dev) >= 1.0:
        direction = "above" if dev > 0 else "below"
        return f"{name} was {abs(dev):.1f} sd {direction} this device's normal range"
    return f"{name} ({weight:+.0%} of influence)"


def plain_language(trace: DecisionTrace, weights: dict[str, float], confidence: float) -> str:
    """One sentence a non-expert can read, built only from recorded values."""
    action = trace.chosen_action
    ranked = sorted(weights.items(), key=lambda kv: abs(kv[1]), reverse=True)
    supporting = [(n, w) for n, w in ranked if w > 0][:2]

    if not supporting:
        reason = "no single input dominated; the agent's scores were close together"
    else:
        reason = " and ".join(_describe(n, w, trace) for n, w in supporting)

    parts = [f"Chose to {action.replace('_', ' ')} because {reason}."]

    if trace.matched_pattern_id:
        sim = trace.matched_pattern_similarity
        sim_txt = f" ({sim:.0%} match)" if sim is not None else ""
        parts.append(f"This resembled known pattern {trace.matched_pattern_id}{sim_txt}.")

    if trace.peer_alert_ids:
        n = len(trace.peer_alert_ids)
        parts.append(f"{n} corroborating alert{'s' if n > 1 else ''} arrived from peer devices.")

    parts.append(f"Confidence {confidence:.0%}.")

    if confidence < 0.55 and ACTION_SEVERITY.get(action, 0) >= 2:
        parts.append("This was a close call — worth a human review.")

    return " ".join(parts)


# ---------------------------------------------------------------- main entry

def _consensus_sentence(c: dict) -> str:
    n = len(c.get("peer_voter_ids") or [])
    if c.get("overridden"):
        return (f"This device's own assessment was overridden by peer consensus "
                f"({n} peer{'s' if n != 1 else ''} voting). The factors below are "
                f"this device's local reading, shown for audit — they are not what "
                f"drove the action.")
    if c.get("peer_triggered"):
        origin = c.get("origin_peer") or "a peer"
        return f"First reported by {origin}; {n} peer{'s' if n != 1 else ''} agreed."
    return ""


def explain(trace: DecisionTrace, decision_id: str, explanation_id: str | None = None) -> dict:
    """Build the Explanation record from a trace. Never raises on missing context."""
    confidence = softmax_confidence(trace.action_scores, trace.chosen_action_index)
    weights = normalise(attribute(trace))
    summary = plain_language(trace, weights, confidence)
    extra = _consensus_sentence(trace.consensus) if trace.consensus else ""
    if extra:
        summary = (extra + " " + summary) if trace.consensus.get("overridden") else (summary + " " + extra)
    return {
        "explanation_id": explanation_id or f"exp-{decision_id}",
        "decision_id": decision_id,
        "factor_weights": weights,
        "matched_pattern_or_rule": trace.matched_pattern_id,
        "plain_language_summary": summary,
        "decision_origin": ("peer_override" if (trace.consensus or {}).get("overridden")
                            else "peer_corroborated" if (trace.consensus or {}).get("peer_triggered")
                            else "local"),
        # --- evidence fields, beyond the minimum contract ---
        "confidence_score": confidence,
        "score_margin": score_margin(trace.action_scores, trace.chosen_action_index),
        "action_scores": dict(zip(trace.action_names, trace.action_scores)),
        "attribution_method": "leave_one_out_margin_ablation",
        "policy_version": trace.policy_version,
        "timestamp": _iso(trace.timestamp),
    }


def decide_and_explain(
    score_fn: ScoreFn,
    feature_names: Sequence[str],
    feature_values: Sequence[float],
    action_names: Sequence[str],
    alert_ids: Sequence[str],
    *,
    decision_id: str,
    baseline: Sequence[float] | None = None,
    matched_pattern_id: str | None = None,
    matched_pattern_similarity: float | None = None,
    shadow_deviation: dict[str, float] | None = None,
    peer_alert_ids: Sequence[str] = (),
    consensus: dict | None = None,
    policy_version: str = "unversioned",
) -> tuple[dict, dict, DecisionTrace]:
    """Run one decision and its explanation as a single atomic step.

    Returns (decision, explanation, trace). Member 1 calls this instead of
    calling the policy network directly, so there is no code path that produces
    a Decision without an Explanation.

    Cost: len(features) + 1 forward passes. Measure this on the target hardware
    and report it — the latency overhead of transparency is a result, not a
    footnote.
    """
    values = [float(v) for v in feature_values]
    base = list(baseline) if baseline is not None else neutral_baseline(values)

    scores = [float(s) for s in score_fn(values)]
    chosen = max(range(len(scores)), key=lambda i: scores[i])

    # Pillar 4 override: the action taken was the peer aggregate, not the local
    # argmax. Explain the action that was ACTUALLY taken, and say so.
    if consensus and consensus.get("overridden") and consensus.get("label") in action_names:
        chosen = list(action_names).index(consensus["label"])

    ablation_scores = []
    for i in range(len(values)):
        perturbed = list(values)
        perturbed[i] = base[i]
        ablation_scores.append(list(score_fn(perturbed)))

    trace = DecisionTrace(
        alert_ids=list(alert_ids),
        feature_names=list(feature_names),
        feature_values=values,
        action_names=list(action_names),
        action_scores=scores,
        chosen_action_index=chosen,
        ablation_scores=ablation_scores,
        matched_pattern_id=matched_pattern_id,
        matched_pattern_similarity=matched_pattern_similarity,
        shadow_deviation=shadow_deviation,
        peer_alert_ids=list(peer_alert_ids),
        consensus=consensus,
        policy_version=policy_version,
    )

    explanation = explain(trace, decision_id)
    decision = {
        "decision_id": decision_id,
        "alert_ids": list(alert_ids),
        "chosen_action": trace.chosen_action,
        "confidence_score": explanation["confidence_score"],
        "timestamp": _iso(trace.timestamp),
        "contributing_factors": [
            n for n, _ in sorted(
                explanation["factor_weights"].items(),
                key=lambda kv: abs(kv[1]),
                reverse=True,
            )[:3]
        ],
    }
    return decision, explanation, trace

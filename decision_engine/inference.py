"""
Inference helpers for Member 2 (explainability pillar).
"""
import torch
import numpy as np
from stable_baselines3 import PPO

from .soar_env import ALERT_TYPES, FEATURE_KEYS, ACTIONS

# Stable, human-readable feature names, in the EXACT order they appear
# in the observation vector (see SoarEnv._alert_to_state):
FEATURE_NAMES = (
    ["observed_severity"]
    + [f"alert_type_{t.value}" for t in ALERT_TYPES]
    + list(FEATURE_KEYS)
)

_model = PPO.load("ppo_soar_agent")


def score_fn(features: np.ndarray) -> list[float]:
    """
    Side-effect-free. Returns raw logits, one per action (5 total),
    in ACTIONS order. Does NOT mutate model/env state — safe to call
    repeatedly for ablation.
    """
    obs = torch.as_tensor(features, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        dist = _model.policy.get_distribution(obs)
        logits = dist.distribution.logits.squeeze(0)
    return logits.tolist()


def softmax_confidence(logits: list[float], chosen_idx: int) -> float:
    """Matches your softmax approach — use this for Decision.confidence_score."""
    exp = np.exp(np.array(logits) - np.max(logits))
    probs = exp / exp.sum()
    return float(probs[chosen_idx])

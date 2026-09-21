"""
SOAR Decision Engine — Gym environment (Pillar 1)
Built against the REAL shared/contracts.py: Alert, ActionType, Decision.

UNRESOLVED TEAM ISSUE (raise this before relying on this file):
Alert.raw_features is an open-ended Dict[str, float] with no fixed keys.
RL needs a fixed-size numeric vector every step. FEATURE_KEYS below is a
placeholder guess — get Member 3 (domain-integration) to commit to an
agreed, fixed feature schema, then replace FEATURE_KEYS with the real list.

Install: pip install stable-baselines3 gymnasium
"""

import uuid
import json
import os
import time
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from datetime import datetime, timezone

from shared.contracts import Alert, AlertType, ActionType, Decision
# TODO: also import `from shared.fake_data_generator import generate_fake_alert`
#       once you swap _fake_alert_stub() for the real generator.


# ---------------------------------------------------------------------------
# PLACEHOLDER — replace once the team agrees on a fixed raw_features schema.
# These are guesses at plausible signal names based on the alert types
# already defined in AlertType (traffic_spike, sensor_anomaly, etc.)
# ---------------------------------------------------------------------------
FEATURE_KEYS = [
    "connections_per_min", "power_draw_watts", "power_draw_anomaly_score",  # plug
    "motion_events_per_min", "stream_integrity_score",                      # camera
    "temp_delta_c", "commanded_vs_actual_mismatch",                        # thermostat
    "failed_attempts_last_min", "unrecognized_credential",                 # lock
]
# Union across all 4 device types (plug/camera/thermostat/lock). Missing
# keys default to 0.0 per-device (see _alert_to_state). Simple but wastes
# capacity — most features are 0 for any given alert. Fine for now; revisit
# with a device_type field in state if accuracy suffers.

ALERT_TYPES = list(AlertType)          # fixed order for one-hot encoding
ACTIONS = list(ActionType)             # fixed order: index <-> ActionType

# Rough escalation order used ONLY for the naive baseline reward below.
# This ordering is a design decision worth defending in your written report,
# not a fact from the contract — quarantine is the most severe response.
ESCALATION_ORDER = [
    ActionType.IGNORE,
    ActionType.MONITOR,
    ActionType.RATE_LIMIT,
    ActionType.BLOCK,
    ActionType.QUARANTINE,
]


class SoarEnv(gym.Env):
    """
    One episode = one Alert. Agent observes the alert, picks an ActionType,
    gets a reward. Single-step episodes — good enough for a first working
    baseline; extend to multi-step if your evaluation design needs it.
    """

    metadata = {"render_modes": []}

    def __init__(self, live=False, live_alerts_path="shared/live_alerts.jsonl"):
        super().__init__()

        # State = severity_hint (1) + alert_type one-hot (len(ALERT_TYPES))
        #         + raw_features vector (len(FEATURE_KEYS))
        obs_dim = 1 + len(ALERT_TYPES) + len(FEATURE_KEYS)
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(obs_dim,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(len(ACTIONS))

        self.live = live                        # True = pull real Alerts
        self._live_path = live_alerts_path       # shared/live_alerts.jsonl
        self._live_pos = 0                       # byte offset already consumed
        self._current_alert = None
        self._true_severity = None  # ground truth, used only for reward

    # -------------------------------------------------------------------
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._current_alert = self._next_live_alert() if self.live else self._fake_alert_stub()
        self._true_severity = self._current_alert.severity_hint
        state = self._alert_to_state(self._current_alert)
        return state, {"alert": self._current_alert}

    # -------------------------------------------------------------------
    def step(self, action: int):
        alert = self._current_alert
        chosen_action = ACTIONS[action]
        # reward uses TRUE severity — agent only ever saw the noisy one
        reward = self._compute_reward(alert, chosen_action, self._true_severity)

        decision = Decision(
            decision_id=str(uuid.uuid4()),
            alert_ids=[alert.alert_id],
            chosen_action=chosen_action,
            confidence_score=1.0,  # TODO: derive from policy's action probability if you want this real
            contributing_factors=[],  # this is Member 2's job to populate, not yours
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        terminated = True
        truncated = False
        info = {"decision": decision, "alert": alert}
        return self._alert_to_state(alert), reward, terminated, truncated, info

    # -------------------------------------------------------------------
    def _alert_to_state(self, alert):
        # NOISE (v3): severity_hint is, per contracts.py's own docstring,
        # "a rough 0.0-1.0 first guess, not final" — so the agent only ever
        # SEES a noisy version of it. Reward still uses true severity (see
        # step()). This gives the agent's raw_features a real job: help
        # compensate for an imperfect severity reading, something a
        # single-threshold rule on observed_severity alone can't do.
        noisy_severity = float(
            np.clip(alert.severity_hint + np.random.normal(0, 0.12), 0.0, 1.0)
        )
        one_hot = [1.0 if alert.alert_type == t else 0.0 for t in ALERT_TYPES]
        features = [alert.raw_features.get(k, 0.0) for k in FEATURE_KEYS]
        return np.array([noisy_severity] + one_hot + features, dtype=np.float32)

    # -------------------------------------------------------------------
    def _compute_reward(self, alert, chosen_action, true_severity) -> float:
        """
        THIS FUNCTION IS YOUR ACTUAL PILLAR CONTRIBUTION.

        v3 — alert-type-aware thresholds, scored against TRUE severity
        (agent only observes a noisy version, see _alert_to_state). This
        is what makes the DRL-vs-rule-based-baseline comparison meaningful:
        a baseline that only checks its own noisy severity reading against
        fixed thresholds will misfire near the boundaries; an agent with
        access to the correlated raw_features may partially compensate.

        Alert-type rationale (defend this to the panel): data_tampering
        and false_data_injection mean the incoming data itself can't be
        trusted, so these get lower/earlier escalation thresholds than a
        generic anomaly/spike. Thresholds are a first-pass design choice,
        not validated against real attack data yet.
        """
        severity = true_severity

        if alert.alert_type in (AlertType.DATA_TAMPERING, AlertType.FALSE_DATA_INJECTION):
            thresholds = (0.15, 0.35, 0.55, 0.75)  # escalate earlier
        else:
            thresholds = (0.25, 0.5, 0.7, 0.9)     # original baseline

        t_ignore, t_monitor, t_ratelimit, t_block = thresholds
        if severity < t_ignore:
            ideal = ActionType.IGNORE
        elif severity < t_monitor:
            ideal = ActionType.MONITOR
        elif severity < t_ratelimit:
            ideal = ActionType.RATE_LIMIT
        elif severity < t_block:
            ideal = ActionType.BLOCK
        else:
            ideal = ActionType.QUARANTINE

        if chosen_action == ideal:
            return 1.0

        distance = abs(
            ESCALATION_ORDER.index(chosen_action) - ESCALATION_ORDER.index(ideal)
        )
        return -0.5 * distance

    # -------------------------------------------------------------------
    def _next_live_alert(self, poll_interval=0.5):
        """
        Blocks until a new line appears in live_alerts.jsonl, parses it
        into an Alert. Tracks byte offset (self._live_pos) so it only
        reads NEW lines appended since last call, not from the start.
        """
        while True:
            if os.path.exists(self._live_path):
                with open(self._live_path, "r") as f:
                    f.seek(self._live_pos)
                    line = f.readline()
                    if line and line.endswith("\n"):
                        self._live_pos = f.tell()
                        return self._json_to_alert(line)
            time.sleep(poll_interval)

    def _json_to_alert(self, line: str) -> Alert:
        """
        Assumes adapters serialize Alert with the same field names as
        contracts.py. If alert_emitter.py uses different key names,
        this mapping needs updating to match.
        """
        d = json.loads(line)
        return Alert(
            alert_id=d["alert_id"],
            source_device_id=d["source_device_id"],
            timestamp=d["timestamp"],
            alert_type=AlertType(d["alert_type"]),
            raw_features=d["raw_features"],
            severity_hint=float(d["severity_hint"]),
        )

    # -------------------------------------------------------------------
    def _fake_alert_stub(self):
        """Temporary stand-in for shared/fake_data_generator.py."""
        rng = np.random.default_rng()
        alert_type = ALERT_TYPES[rng.integers(0, len(ALERT_TYPES))]
        raw_features = {k: float(rng.uniform()) for k in FEATURE_KEYS}
        return Alert(
            alert_id=str(uuid.uuid4()),
            source_device_id=f"device_{rng.integers(0, 20)}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            alert_type=alert_type,
            raw_features=raw_features,
            severity_hint=float(rng.uniform()),
        )


def rule_based_action(obs: np.ndarray) -> int:
    """
    Non-adaptive baseline: reads ONLY the noisy observed severity
    (obs[0]) against fixed thresholds — no alert-type awareness, no use
    of raw_features. This is your comparison point for the report.
    """
    observed_severity = obs[0]
    if observed_severity < 0.25:
        ideal = ActionType.IGNORE
    elif observed_severity < 0.5:
        ideal = ActionType.MONITOR
    elif observed_severity < 0.7:
        ideal = ActionType.RATE_LIMIT
    elif observed_severity < 0.9:
        ideal = ActionType.BLOCK
    else:
        ideal = ActionType.QUARANTINE
    return ACTIONS.index(ideal)


if __name__ == "__main__":
    env = SoarEnv()
    obs, info = env.reset()
    for _ in range(5):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        a = info["alert"]
        print(
            f"type={a.alert_type.value:<20} severity={a.severity_hint:.2f} "
            f"action={ACTIONS[action].value:<12} reward={reward:+.2f}"
        )
        obs, info = env.reset()

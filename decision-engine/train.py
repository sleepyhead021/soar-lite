"""
Minimal PPO training script — Pillar 1 baseline.

Run this ONLY after confirming soar_env.py's random rollout (python soar_env.py)
produces sane rewards. Training on a broken environment just wastes time.

Install: pip install stable-baselines3 gymnasium
"""

from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
import csv

from .soar_env import SoarEnv, rule_based_action

env = SoarEnv()
check_env(env, warn=True)

N_EVAL = 200  # bigger sample so noise averages out, not just 20


def evaluate(policy_fn, label, log_path):
    obs, info = env.reset()
    total = 0.0
    with open(log_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "alert_id", "source_device_id", "alert_timestamp", "alert_type",
            "severity_hint", "raw_features",
            "decision_id", "chosen_action", "confidence_score",
            "decision_timestamp", "reward",
        ])
        for _ in range(N_EVAL):
            action = policy_fn(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            a, d = info["alert"], info["decision"]
            writer.writerow([
                a.alert_id, a.source_device_id, a.timestamp, a.alert_type.value,
                a.severity_hint, a.raw_features,
                d.decision_id, d.chosen_action.value, d.confidence_score,
                d.timestamp, reward,
            ])
            total += reward
            obs, info = env.reset()
    avg = total / N_EVAL
    print(f"{label}: avg reward over {N_EVAL} episodes = {avg:.3f}  (log: {log_path})")
    return avg


# --- Baseline (non-adaptive rule, reads only noisy severity) -----------
baseline_avg = evaluate(lambda obs: rule_based_action(obs), "Rule-based baseline", "baseline_log.csv")

# --- DRL agent -----------------------------------------------------------
model = PPO("MlpPolicy", env, verbose=0)
model.learn(total_timesteps=20_000)
model.save("ppo_soar_agent")

drl_avg = evaluate(lambda obs: model.predict(obs, deterministic=True)[0], "DRL agent", "drl_agent_log.csv")

print(f"\nGap (DRL - baseline): {drl_avg - baseline_avg:+.3f}")
print("If this gap is ~0, the raw_features aren't correlated enough with")
print("true severity for the agent to compensate for observation noise —")
print("that's a real finding, not a failure; report it as such.")

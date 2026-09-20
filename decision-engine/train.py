"""
Minimal PPO training script — Pillar 1 baseline.

Run this ONLY after confirming soar_env.py's random rollout (python soar_env.py)
produces sane rewards. Training on a broken environment just wastes time.

Install: pip install stable-baselines3 gymnasium
"""

from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env

from .soar_env import SoarEnv, rule_based_action

env = SoarEnv()
check_env(env, warn=True)

N_EVAL = 200  # bigger sample so noise averages out, not just 20


def evaluate(policy_fn, label):
    obs, info = env.reset()
    total = 0.0
    for _ in range(N_EVAL):
        action = policy_fn(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        total += reward
        obs, info = env.reset()
    avg = total / N_EVAL
    print(f"{label}: avg reward over {N_EVAL} episodes = {avg:.3f}")
    return avg


# --- Baseline (non-adaptive rule, reads only noisy severity) -----------
baseline_avg = evaluate(lambda obs: rule_based_action(obs), "Rule-based baseline")

# --- DRL agent -----------------------------------------------------------
model = PPO("MlpPolicy", env, verbose=0)
model.learn(total_timesteps=20_000)
model.save("ppo_soar_agent")

drl_avg = evaluate(lambda obs: model.predict(obs, deterministic=True)[0], "DRL agent")

print(f"\nGap (DRL - baseline): {drl_avg - baseline_avg:+.3f}")
print("If this gap is ~0, the raw_features aren't correlated enough with")
print("true severity for the agent to compensate for observation noise —")
print("that's a real finding, not a failure; report it as such.")

"""Multi-seed PPO vs threshold baseline. Run from repo root:
   python run_eval.py [n_seeds=5] [n_eval=1000] [timesteps=20000]"""
import csv, os, sys
import numpy as np
from stable_baselines3 import PPO
from shared.contracts import AlertType
from decision_engine.soar_env import SoarEnv, rule_based_action

TYPE_AWARE = (AlertType.DATA_TAMPERING, AlertType.FALSE_DATA_INJECTION)

def make_stream(env, n):
    """Fixed (alert, noisy_obs) list so both policies see identical inputs."""
    out = []
    for _ in range(n):
        a = env._fake_alert_stub()
        env._current_alert, env._true_severity = a, a.severity_hint
        out.append((a, env._alert_to_state(a)))
    return out

def score(env, stream, policy):
    tot, ta_tot, ta_n = [], [], 0
    for a, obs in stream:
        env._current_alert, env._true_severity = a, a.severity_hint
        r = env.step(int(policy(obs)))[1]
        tot.append(r)
        if a.alert_type in TYPE_AWARE:
            ta_tot.append(r)
    return float(np.mean(tot)), float(np.mean(ta_tot))

def main(n_seeds=5, n_eval=1000, steps=20_000):
    os.makedirs("out", exist_ok=True)
    rows = []
    for seed in range(n_seeds):
        np.random.seed(seed)
        env = SoarEnv()
        model = PPO("MlpPolicy", env, seed=seed, verbose=0)
        model.learn(total_timesteps=steps)
        stream = make_stream(env, n_eval)
        b_all, b_ta = score(env, stream, rule_based_action)
        d_all, d_ta = score(env, stream, lambda o: model.predict(o, deterministic=True)[0])
        rows.append((seed, b_all, d_all, d_all - b_all, b_ta, d_ta))
        print(f"seed {seed}: baseline={b_all:.3f} drl={d_all:.3f} gap={d_all-b_all:+.3f} "
              f"| tampering/FDI only: baseline={b_ta:.3f} drl={d_ta:.3f}")
    a = np.array(rows)
    gap = a[:, 3]
    print(f"\nOverall  baseline {a[:,1].mean():.3f}±{a[:,1].std():.3f}  "
          f"DRL {a[:,2].mean():.3f}±{a[:,2].std():.3f}")
    print(f"Gap      {gap.mean():+.3f}±{gap.std():.3f}  (DRL wins {(gap>0).sum()}/{len(gap)} seeds)")
    print(f"Tampering/FDI only  baseline {a[:,4].mean():.3f}  DRL {a[:,5].mean():.3f}")
    with open("out/eval_multiseed.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seed", "baseline", "drl", "gap", "baseline_tamper_fdi", "drl_tamper_fdi"])
        w.writerows(rows)

if __name__ == "__main__":
    args = [int(x) for x in sys.argv[1:]]
    main(*args)
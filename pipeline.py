"""
pipeline.py (repo root) -- end-to-end offline run:
  alert -> local action -> simulated peer vote -> apply_consensus
        -> decide_and_explain -> ActionResult -> CSV + attack log -> metrics

Run from repo root, after training (python3 -m decision_engine.train):
  export PYTHONPATH="$PWD/shared:$PWD"      (Windows cmd: set PYTHONPATH=%CD%\\shared;%CD%)
  python3 pipeline.py [n_alerts] [seed]

Peers are simulated in-process (jittered votes, same rule as
conflict_resolution._evaluate_locally) so this needs no UDP / extra terminals.
Alerts come from the env's training stub, so the agent sees in-distribution
inputs. Ground truth: an alert is an "attack" if severity_hint >= 0.5.
"""
import csv, json, os, random, sys, time, uuid
from datetime import datetime, timedelta, timezone

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
for sub in ("explainability", "p2p_coordination", "testbed"):
    sys.path.insert(0, os.path.join(ROOT, sub))

from contracts import ActionResult, ActionType                      # noqa: E402
from behavioral_shadow import BehavioralShadow                      # noqa: E402
from consensus import apply_consensus                               # noqa: E402        # noqa: E402
from conflict_resolution import compute_tally                       # noqa: E402
from decision_engine.soar_env import SoarEnv, ACTIONS               # noqa: E402
from decision_engine.inference import score_fn, FEATURE_NAMES       # noqa: E402
import metrics                                                      # noqa: E402
from explainability.explainer import decide_and_explain, softmax_confidence

decision, explanation, trace = decide_and_explain(
    score_fn, FEATURE_NAMES, obs.tolist(),
    [a.value for a in ACTIONS], [alert.alert_id],
    decision_id=str(uuid.uuid4()),
)
# decision["confidence_score"] and decision["contributing_factors"] are now real

OUT = os.path.join(ROOT, "out")
ACTION_NAMES = [a.value for a in ACTIONS]
PEERS = ["peer_1", "peer_2"]
SPACING = 0.05          # seconds between alerts
ATTACK_SEV = 0.5

CSV_COLS = ["alert_id", "source_device_id", "alert_timestamp", "alert_type",
            "severity_hint", "raw_features", "decision_id", "chosen_action",
            "confidence_score", "decision_timestamp", "reward"]


def peer_vote(sev):
    conf = max(0.0, min(1.0, sev + random.uniform(-0.15, 0.15)))
    return conf, conf > 0.5


def execute(decision):
    """Action Automation stub: records an ActionResult (no real enforcement)."""
    act = decision["chosen_action"]
    exp = None
    if act == "rate_limit":
        exp = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
    return ActionResult(decision["decision_id"], ActionType(act), True, exp,
                        notes="simulated")


def main(n=200, seed=0):
    random.seed(seed); np.random.seed(seed)
    os.makedirs(OUT, exist_ok=True)
    env = SoarEnv()
    shadows = {}
    stats = {"overridden": 0, "results": 0}
    attack_events = []

    with open(os.path.join(OUT, "pipeline_log.csv"), "w", newline="") as fcsv, \
         open(os.path.join(OUT, "explanations.jsonl"), "w") as fexp:
        w = csv.writer(fcsv); w.writerow(CSV_COLS)

        for _ in range(n):
            alert = env._fake_alert_stub()
            env._current_alert = alert
            state = [float(x) for x in env._alert_to_state(alert)]
            t_alert = time.time()
            is_attack = alert.severity_hint >= ATTACK_SEV
            if is_attack:
                attack_events += [
                    {"scenario": alert.alert_type.value, "event": "attack_start", "ts": t_alert - 0.001},
                    {"scenario": alert.alert_type.value, "event": "attack_end", "ts": t_alert + SPACING * 0.8}]

            # 1. local decision + vote
            scores = [float(s) for s in score_fn(state)]
            idx = int(np.argmax(scores))
            local_action = ACTION_NAMES[idx]
            local_conf = softmax_confidence(scores, idx)
            local_agrees = local_action not in ("ignore", "monitor")
            votes = {alert.source_device_id: (local_conf, local_agrees)}
            for p in PEERS:
                votes[p] = peer_vote(alert.severity_hint)

            # 2. tally -> consensus -> final action
            label, score, _ = compute_tally(votes)
            result = {"alert_id": alert.alert_id, "label": label, "score": score,
                      "peer_triggered": False, "origin_peer": alert.source_device_id,
                      "peer_voter_ids": PEERS, "local_confidence": local_conf,
                      "local_agrees": local_agrees, "overridden": False}
            result = apply_consensus(local_action, result)
            stats["results"] += 1; stats["overridden"] += int(result["overridden"])

            # 3. decide + explain (atomic)
            sh = shadows.setdefault(alert.source_device_id,
                                    BehavioralShadow(alert.source_device_id))
            feats = dict(zip(FEATURE_NAMES, state))
            decision, expl, _ = decide_and_explain(
                score_fn, FEATURE_NAMES, state, ACTION_NAMES, [alert.alert_id],
                decision_id=str(uuid.uuid4()),
                baseline=sh.baseline(FEATURE_NAMES),
                shadow_deviation=sh.z_scores(feats),
                consensus=result, policy_version="ppo_soar_agent")

            # 4. execute, learn "normal" only from benign outcomes
            execute(decision)
            if decision["chosen_action"] == "ignore":
                sh.observe(feats)

            # 5. log
            w.writerow([alert.alert_id, alert.source_device_id, alert.timestamp,
                        alert.alert_type.value, alert.severity_hint, alert.raw_features,
                        decision["decision_id"], decision["chosen_action"],
                        decision["confidence_score"], decision["timestamp"], ""])
            fexp.write(json.dumps(expl) + "\n")
            time.sleep(SPACING)

    with open(os.path.join(OUT, "attack_log.jsonl"), "w") as f:
        for e in attack_events:
            f.write(json.dumps(e) + "\n")

    print(f"\n{n} alerts, consensus overrode the local action {stats['overridden']} times")
    print("--- metrics ---")
    dec = metrics.load_decisions(os.path.join(OUT, "pipeline_log.csv"))
    metrics.windowed_metrics(
        dec, metrics.load_attack_windows(os.path.join(OUT, "attack_log.jsonl")))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200,
         int(sys.argv[2]) if len(sys.argv) > 2 else 0)

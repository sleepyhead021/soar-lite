import numpy as np
from decision_engine.inference import score_fn, FEATURE_NAMES
from explainability.explainer import decide_and_explain, score_margin

def run(n=200):
    rng = np.random.default_rng(0)
    top_drops, low_drops = [], []
    for _ in range(n):
        x = rng.uniform(0, 1, len(FEATURE_NAMES)).tolist()
        _, exp, trace = decide_and_explain(
            score_fn, FEATURE_NAMES, x, ["ignore","monitor","rate_limit","block","quarantine"],
            ["t"], decision_id="t")
        w = exp["factor_weights"]
        order = sorted(w, key=lambda k: abs(w[k]), reverse=True)
        c = trace.chosen_action_index
        full = score_margin(trace.action_scores, c)
        def drop(name):
            y = list(x); y[FEATURE_NAMES.index(name)] = 0.0
            return full - score_margin(score_fn(y), c)
        top_drops.append(drop(order[0])); low_drops.append(drop(order[-1]))
    print(f"mean margin drop, top feature:    {np.mean(top_drops):.3f}")
    print(f"mean margin drop, bottom feature: {np.mean(low_drops):.3f}")
    print(f"faithful in {np.mean(np.array(top_drops) > np.array(low_drops)):.0%} of cases")

if __name__ == "__main__":
    run()
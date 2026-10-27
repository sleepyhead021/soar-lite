import json, math
PATH = "patterns.json"

def load(): return json.load(open(PATH))

def match_pattern(alert, threshold=0.8):
    best, best_sim = None, 0.0
    for pid, p in load().items():
        if p["alert_type"] != alert.alert_type.value: continue
        d = math.sqrt(sum((alert.raw_features.get(k, 0) - v) ** 2 for k, v in p["features"].items()))
        sim = 1 / (1 + d)
        if sim > best_sim: best, best_sim = pid, sim
    return (best, best_sim) if best_sim >= threshold else (None, None)

def add_pattern(pid, pattern):
    kb = load(); kb[pid] = pattern
    json.dump(kb, open(PATH, "w"), indent=1)
"""
Evaluation Metrics
==================
Compares ground-truth attack windows (testbed/attack_log.jsonl) against
Alert/Decision logs (Pillar 1's CSV format) to compute:
  - detection rate       (% attack windows with a non-'ignore' decision inside)
  - false positive rate  (% non-'ignore' decisions outside any attack window)
  - time-to-detection    (decision_timestamp - attack_start, per caught window)

If attack_log.jsonl doesn't exist yet (no real testbed run performed),
falls back to summary stats only — useful as a dry run against fake data.

Usage: python3 metrics.py <decision_log.csv> [attack_log.jsonl]
"""
import sys
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

NON_ACTIONABLE = {"ignore"}


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_decisions(csv_path):
    rows = []
    with open(csv_path, newline="") as f:
        for r in csv.DictReader(f):
            r["decision_timestamp"] = parse_ts(r["decision_timestamp"])
            rows.append(r)
    return rows


def load_attack_windows(jsonl_path):
    """Pair attack_start/attack_end per scenario, in time order.
    Returns [(scenario, start_dt, end_dt)]. Unmatched starts get a zero-length
    window and a warning, so a crashed run is visible rather than silently dropped."""
    with open(jsonl_path) as f:
        events = sorted((json.loads(l) for l in f if l.strip()), key=lambda e: e["ts"])

    open_starts = {}   # scenario -> list of start timestamps (FIFO)
    windows = []
    to_dt = lambda t: datetime.fromtimestamp(t, tz=timezone.utc)

    for e in events:
        sc = e["scenario"]
        if e["event"] == "attack_start":
            open_starts.setdefault(sc, []).append(e["ts"])
        elif e["event"] == "attack_end":
            if open_starts.get(sc):
                windows.append((sc, to_dt(open_starts[sc].pop(0)), to_dt(e["ts"])))
            else:
                print(f"WARN: {sc} attack_end with no matching start, ignored")

    for sc, starts in open_starts.items():
        for t in starts:
            print(f"WARN: {sc} attack_start at {t} has no end; zero-length window")
            windows.append((sc, to_dt(t), to_dt(t)))

    return sorted(windows, key=lambda w: w[1])


def summary_stats(decisions):
    total = len(decisions)
    actionable = [d for d in decisions if d["chosen_action"] not in NON_ACTIONABLE]
    print(f"Total decisions: {total}")
    print(f"Actionable (non-ignore): {len(actionable)} ({len(actionable)/total:.1%})")
    print("Note: no attack_log.jsonl found — this is a dry run against "
          "fake data, not real detection/false-positive rates.")


def windowed_metrics(decisions, windows):
    caught, missed, times = 0, 0, []
    for scenario, start, end in windows:
        hit = next((d for d in decisions
                    if start <= d["decision_timestamp"] <= end
                    and d["chosen_action"] not in NON_ACTIONABLE), None)
        if hit:
            caught += 1
            times.append((hit["decision_timestamp"] - start).total_seconds())
        else:
            missed += 1
        print(f"{scenario}: {'CAUGHT' if hit else 'MISSED'} "
              f"({start.isoformat()} - {end.isoformat()})")

    fp = sum(1 for d in decisions
             if d["chosen_action"] not in NON_ACTIONABLE
             and not any(s <= d["decision_timestamp"] <= e for _, s, e in windows))

    total_windows = caught + missed
    print(f"\nDetection rate: {caught}/{total_windows} "
          f"({caught/total_windows:.1%})" if total_windows else "No windows found.")
    print(f"False positives: {fp}")
    if times:
        print(f"Avg time-to-detection: {sum(times)/len(times):.3f}s")


if __name__ == "__main__":
    decisions = load_decisions(sys.argv[1])
    log_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("attack_log.jsonl")
    if log_path.exists():
        windowed_metrics(decisions, load_attack_windows(log_path))
    else:
        summary_stats(decisions)

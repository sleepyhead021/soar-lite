"""Shared logger for testbed scripts — writes ground-truth attack windows
so evaluation can compute detection rate / time-to-detection later."""
import json
import time
from pathlib import Path

LOG_PATH = Path(__file__).parent / "attack_log.jsonl"


def log_event(scenario: str, event: str, **extra):
    """event: 'attack_start' or 'attack_end'"""
    record = {
        "scenario": scenario,
        "event": event,
        "ts": time.time(),
        **extra,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"[{scenario}] {event} logged at {record['ts']}")

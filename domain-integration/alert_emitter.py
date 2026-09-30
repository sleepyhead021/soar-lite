"""Appends an Alert as one JSON line to shared/live_alerts.jsonl,
which soar_env.py reads in live mode."""
import json
import dataclasses
from pathlib import Path

LIVE_ALERTS_PATH = Path(__file__).resolve().parent.parent / "shared" / "live_alerts.jsonl"


def emit_alert(alert):
    if alert is None:
        return
    record = dataclasses.asdict(alert)
    record["alert_type"] = alert.alert_type.value
    LIVE_ALERTS_PATH.parent.mkdir(exist_ok=True)
    with open(LIVE_ALERTS_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

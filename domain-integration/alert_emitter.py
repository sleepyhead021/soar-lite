"""Shared alert emitter — appends an Alert as one JSON line to
shared/live_alerts.jsonl, which soar_env.py's reset() reads from
instead of generating fake data."""
import json
import dataclasses
from pathlib import Path

LIVE_ALERTS_PATH = Path(__file__).parent / "live_alerts.jsonl"


def emit_alert(alert):
    """alert: an Alert dataclass instance (or None — no-op if None)."""
    if alert is None:
        return
    record = dataclasses.asdict(alert)
    record["alert_type"] = alert.alert_type.value  # enum -> str for JSON
    with open(LIVE_ALERTS_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

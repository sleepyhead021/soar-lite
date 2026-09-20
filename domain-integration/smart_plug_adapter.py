"""
Smart Plug Adapter
==================
Converts raw smart-plug telemetry into the shared `Alert` contract.
Run standalone to test against fake_data_generator-style input.
"""

import uuid
from datetime import datetime, timezone
from contracts import Alert, AlertType

# Simple thresholds — tune these once you have real/fake traffic to look at.
CONN_PER_MIN_SPIKE_THRESHOLD = 300.0
POWER_DRAW_ANOMALY_THRESHOLD = 0.85  # normalized 0-1 "how far from baseline"


def smart_plug_to_alert(raw: dict) -> Alert | None:
    """
    raw is expected to look like:
    {
        "device_id": "plug-01",
        "timestamp": "2026-09-20T12:00:00Z",
        "connections_per_min": 480.0,
        "power_draw_watts": 1500.0,
        "power_draw_anomaly_score": 0.9,   # 0-1, how unusual vs baseline
    }
    Returns None if nothing suspicious — not every reading is an Alert.
    """
    conn_rate = raw.get("connections_per_min", 0.0)
    power_anomaly = raw.get("power_draw_anomaly_score", 0.0)

    alert_type = None
    severity = 0.0

    if conn_rate > CONN_PER_MIN_SPIKE_THRESHOLD:
        alert_type = AlertType.TRAFFIC_SPIKE
        severity = min(conn_rate / (CONN_PER_MIN_SPIKE_THRESHOLD * 2), 1.0)
    elif power_anomaly > POWER_DRAW_ANOMALY_THRESHOLD:
        alert_type = AlertType.SENSOR_ANOMALY
        severity = power_anomaly

    if alert_type is None:
        return None  # nothing worth raising

    return Alert(
        alert_id=str(uuid.uuid4()),
        source_device_id=raw.get("device_id", "unknown-plug"),
        timestamp=raw.get("timestamp", datetime.now(timezone.utc).isoformat()),
        alert_type=alert_type,
        raw_features={
            "connections_per_min": conn_rate,
            "power_draw_watts": raw.get("power_draw_watts", 0.0),
            "power_draw_anomaly_score": power_anomaly,
        },
        severity_hint=round(severity, 2),
    )


if __name__ == "__main__":
    sample = {
        "device_id": "plug-01",
        "timestamp": "2026-09-20T12:00:00Z",
        "connections_per_min": 480.0,
        "power_draw_watts": 1500.0,
        "power_draw_anomaly_score": 0.4,
    }
    alert = smart_plug_to_alert(sample)
    print(alert)

"""Camera Adapter — converts raw camera telemetry into shared Alert."""
import uuid
from datetime import datetime, timezone
from contracts import Alert, AlertType
from alert_emitter import emit_alert

MOTION_RATE_SPIKE_THRESHOLD = 10.0       # events/min, unusually frequent
STREAM_INTEGRITY_THRESHOLD = 0.7         # 0-1, how corrupted/tampered feed looks


def camera_to_alert(raw: dict) -> Alert | None:
    """
    raw example:
    {
        "device_id": "cam-01",
        "timestamp": "2026-09-20T12:00:00Z",
        "motion_events_per_min": 15.0,
        "stream_integrity_score": 0.9,   # 0=corrupted/tampered, 1=clean
    }
    """
    motion_rate = raw.get("motion_events_per_min", 0.0)
    integrity = raw.get("stream_integrity_score", 1.0)

    alert_type, severity = None, 0.0
    if integrity < (1 - STREAM_INTEGRITY_THRESHOLD):
        alert_type = AlertType.DATA_TAMPERING
        severity = 1 - integrity
    elif motion_rate > MOTION_RATE_SPIKE_THRESHOLD:
        alert_type = AlertType.SENSOR_ANOMALY
        severity = min(motion_rate / (MOTION_RATE_SPIKE_THRESHOLD * 2), 1.0)

    if alert_type is None:
        return None

    alert = Alert(
        alert_id=str(uuid.uuid4()),
        source_device_id=raw.get("device_id", "unknown-camera"),
        timestamp=raw.get("timestamp", datetime.now(timezone.utc).isoformat()),
        alert_type=alert_type,
        raw_features={
            "motion_events_per_min": motion_rate,
            "stream_integrity_score": integrity,
        },
        severity_hint=round(severity, 2),
    )
    emit_alert(alert)
    return alert

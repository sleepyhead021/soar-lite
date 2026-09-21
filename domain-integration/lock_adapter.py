"""Smart Lock Adapter — converts raw lock telemetry into shared Alert."""
import uuid
from datetime import datetime, timezone
from contracts import Alert, AlertType
from alert_emitter import emit_alert

FAILED_ATTEMPTS_THRESHOLD = 3      # failed unlock attempts in short window
UNRECOGNIZED_CREDENTIAL = 1        # 1 = credential not in known list


def lock_to_alert(raw: dict) -> Alert | None:
    """
    raw example:
    {
        "device_id": "lock-01",
        "timestamp": "2026-09-20T12:00:00Z",
        "failed_attempts_last_min": 5,
        "unrecognized_credential": 1,   # 1 if unlock used unknown key/code
    }
    """
    failed = raw.get("failed_attempts_last_min", 0)
    unrecognized = raw.get("unrecognized_credential", 0)

    alert_type, severity = None, 0.0
    if unrecognized >= UNRECOGNIZED_CREDENTIAL:
        alert_type = AlertType.UNKNOWN_PEER
        severity = 0.9
    elif failed > FAILED_ATTEMPTS_THRESHOLD:
        alert_type = AlertType.SENSOR_ANOMALY
        severity = min(failed / (FAILED_ATTEMPTS_THRESHOLD * 3), 1.0)

    if alert_type is None:
        return None

    alert = Alert(
        alert_id=str(uuid.uuid4()),
        source_device_id=raw.get("device_id", "unknown-lock"),
        timestamp=raw.get("timestamp", datetime.now(timezone.utc).isoformat()),
        alert_type=alert_type,
        raw_features={
            "failed_attempts_last_min": failed,
            "unrecognized_credential": unrecognized,
        },
        severity_hint=round(severity, 2),
    )
    emit_alert(alert)
    return alert

"""Thermostat Adapter — converts raw thermostat telemetry into shared Alert."""
import uuid
from datetime import datetime, timezone
from contracts import Alert, AlertType
from alert_emitter import emit_alert

TEMP_JUMP_THRESHOLD_C = 8.0     # degrees change between consecutive readings
COMMAND_MISMATCH_THRESHOLD = 1  # any mismatch counts as suspicious


def thermostat_to_alert(raw: dict) -> Alert | None:
    """
    raw example:
    {
        "device_id": "therm-01",
        "timestamp": "2026-09-20T12:00:00Z",
        "temp_delta_c": 12.0,          # change since last reading
        "commanded_vs_actual_mismatch": 0,  # 1 if setpoint doesn't match actuator state
    }
    """
    temp_delta = abs(raw.get("temp_delta_c", 0.0))
    mismatch = raw.get("commanded_vs_actual_mismatch", 0)

    alert_type, severity = None, 0.0
    if mismatch >= COMMAND_MISMATCH_THRESHOLD:
        alert_type = AlertType.DATA_TAMPERING
        severity = 0.8
    elif temp_delta > TEMP_JUMP_THRESHOLD_C:
        alert_type = AlertType.SENSOR_ANOMALY
        severity = min(temp_delta / (TEMP_JUMP_THRESHOLD_C * 2), 1.0)

    if alert_type is None:
        return None

    alert = Alert(
        alert_id=str(uuid.uuid4()),
        source_device_id=raw.get("device_id", "unknown-thermostat"),
        timestamp=raw.get("timestamp", datetime.now(timezone.utc).isoformat()),
        alert_type=alert_type,
        raw_features={
            "temp_delta_c": temp_delta,
            "commanded_vs_actual_mismatch": mismatch,
        },
        severity_hint=round(severity, 2),
    )
    emit_alert(alert)
    return alert

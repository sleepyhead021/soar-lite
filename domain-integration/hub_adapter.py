"""Hub Adapter — converts raw hub telemetry into shared Alert.
Hub sees aggregate/network-level signals other devices don't: peer counts,
sync gaps, and unknown device join attempts."""
import uuid
from datetime import datetime, timezone
from contracts import Alert, AlertType
from alert_emitter import emit_alert

PEER_DROP_THRESHOLD = 1          # any expected peer going silent
UNKNOWN_JOIN_THRESHOLD = 1       # any unrecognized device attempting to join


def hub_to_alert(raw: dict) -> Alert | None:
    """
    raw example:
    {
        "device_id": "hub-01",
        "timestamp": "2026-09-20T12:00:00Z",
        "peers_gone_silent": 1,       # count of known peers missing heartbeats
        "unknown_join_attempts": 0,   # count of unrecognized devices trying to join
    }
    """
    peers_silent = raw.get("peers_gone_silent", 0)
    unknown_joins = raw.get("unknown_join_attempts", 0)

    alert_type, severity = None, 0.0
    if unknown_joins >= UNKNOWN_JOIN_THRESHOLD:
        alert_type = AlertType.UNKNOWN_PEER
        severity = min(unknown_joins / 3, 1.0)
    elif peers_silent >= PEER_DROP_THRESHOLD:
        alert_type = AlertType.PEER_SILENT
        severity = min(peers_silent / 3, 1.0)

    if alert_type is None:
        return None

    alert = Alert(
        alert_id=str(uuid.uuid4()),
        source_device_id=raw.get("device_id", "hub"),
        timestamp=raw.get("timestamp", datetime.now(timezone.utc).isoformat()),
        alert_type=alert_type,
        raw_features={
            "peers_gone_silent": peers_silent,
            "unknown_join_attempts": unknown_joins,
        },
        severity_hint=round(severity, 2),
    )
    emit_alert(alert)
    return alert

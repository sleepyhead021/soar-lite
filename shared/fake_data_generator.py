"""Fake alert generator (prefixed feature schema). Run: python fake_data_generator.py"""
import random
import uuid
from datetime import datetime, timezone

from contracts import Alert, AlertType


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _alert(dev, atype, feats, sev) -> Alert:
    return Alert(str(uuid.uuid4()), dev, _now(), atype, feats, sev)


def generate_normal_alert() -> Alert:
    return _alert("plug-01", AlertType.OTHER,
                  {"plug_connections_per_min": random.uniform(1, 8),
                   "plug_power_draw_watts": random.uniform(5, 60),
                   "plug_power_draw_anomaly_score": random.uniform(0, 0.2)}, 0.05)


def generate_ddos_alert() -> Alert:
    return _alert("plug-01", AlertType.TRAFFIC_SPIKE,
                  {"plug_connections_per_min": random.uniform(300, 600),
                   "plug_power_draw_watts": random.uniform(5, 60),
                   "plug_power_draw_anomaly_score": random.uniform(0, 0.3)}, 0.9)


def generate_data_tampering_alert() -> Alert:
    return _alert("therm-01", AlertType.DATA_TAMPERING,
                  {"therm_temp_delta_c": random.uniform(30, 90),
                   "therm_command_mismatch": 1.0}, 0.8)


def generate_false_data_injection_alert() -> Alert:
    return _alert("cam-01", AlertType.FALSE_DATA_INJECTION,
                  {"cam_motion_events_per_min": random.uniform(12, 25),
                   "cam_stream_tamper_score": random.uniform(0.4, 0.8)}, 0.6)


def generate_unknown_peer_alert() -> Alert:
    if random.random() < 0.5:
        return _alert("hub-01", AlertType.UNKNOWN_PEER,
                      {"hub_peers_gone_silent": 0.0,
                       "hub_unknown_join_attempts": float(random.randint(1, 3))}, 0.7)
    return _alert("lock-01", AlertType.UNKNOWN_PEER,
                  {"lock_failed_attempts_last_min": float(random.randint(0, 6)),
                   "lock_unrecognized_credential": 1.0}, 0.9)


def generate_peer_silent_alert() -> Alert:
    n = random.randint(1, 3)
    return _alert("hub-01", AlertType.PEER_SILENT,
                  {"hub_peers_gone_silent": float(n),
                   "hub_unknown_join_attempts": 0.0}, round(min(n / 3, 1.0), 2))


def generate_stream(n: int = 20, attack_ratio: float = 0.2):
    attacks = [generate_ddos_alert, generate_data_tampering_alert,
               generate_false_data_injection_alert, generate_unknown_peer_alert,
               generate_peer_silent_alert]
    for _ in range(n):
        yield random.choice(attacks)() if random.random() < attack_ratio else generate_normal_alert()


if __name__ == "__main__":
    for a in generate_stream(10):
        print(a)

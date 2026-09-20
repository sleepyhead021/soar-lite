"""
Partition Detection & Fallback (Pillar 4, Step 4)
====================================================
Watches this device's set of known active peers (from PeerDiscovery)
and reacts explicitly the moment the device becomes isolated from all
its peers ("partitioned"), and again the moment it reconnects.

The concrete fallback implemented here: while partitioned, the
ConflictResolver's voting window is shortened dramatically (from 3
seconds down to 0.5), so the device doesn't sit around waiting for
votes that physically cannot arrive — it commits to its own local
judgment almost immediately instead. This is a deliberate choice:
act slower-but-together when peers are reachable, and act
alone-but-promptly when they're not — never freeze either way.

Run this instead of conflict_resolution.py directly (it wires
everything together). Start two or three, then kill one process and
watch the survivors print a partition message; restart it and watch
the reconnect message.
"""

import sys
import os
import threading
import time
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))

from peer_discovery import PeerDiscovery  # noqa: E402
from conflict_resolution import ConflictResolver  # noqa: E402
from alert_sharing import AlertSharer, _make_demo_alert  # noqa: E402


CHECK_INTERVAL_SECONDS = 1
PARTITIONED_VOTING_WINDOW_SECONDS = 0.5   # act almost immediately when alone
NORMAL_VOTING_WINDOW_SECONDS = 3          # wait for peers when connected


class PartitionManager:
    def __init__(self, device_id: str, discovery: PeerDiscovery, resolver: ConflictResolver):
        self.device_id = device_id
        self.discovery = discovery
        self.resolver = resolver
        self._partitioned = True  # assume isolated until we've actually heard from someone
        self._running = False

    def start(self):
        self._running = True
        threading.Thread(target=self._monitor, daemon=True).start()
        print(f"[{self.device_id}] Partition monitor started "
              f"(starting isolated until a peer is found).")

    def stop(self):
        self._running = False

    def is_partitioned(self) -> bool:
        return self._partitioned

    def _monitor(self):
        while self._running:
            has_peers = len(self.discovery.get_active_peers()) > 0

            if has_peers and self._partitioned:
                self._partitioned = False
                self.resolver.voting_window_seconds = NORMAL_VOTING_WINDOW_SECONDS
                print(f"[{self.device_id}] Peer(s) reconnected — resuming normal "
                      f"coordination (voting window back to {NORMAL_VOTING_WINDOW_SECONDS}s). "
                      f"[Knowledge re-sync will trigger here once Step 5 is built.]")

            elif not has_peers and not self._partitioned:
                self._partitioned = True
                self.resolver.voting_window_seconds = PARTITIONED_VOTING_WINDOW_SECONDS
                print(f"[{self.device_id}] Lost contact with all peers — entering "
                      f"partitioned mode. Deciding alone from now on "
                      f"(voting window shortened to {PARTITIONED_VOTING_WINDOW_SECONDS}s).")

            time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    device_id = sys.argv[1] if len(sys.argv) > 1 else f"device_{uuid.uuid4().hex[:6]}"

    discovery = PeerDiscovery(device_id)
    discovery.start()

    resolver = ConflictResolver(device_id, discovery)
    resolver.voting_window_seconds = PARTITIONED_VOTING_WINDOW_SECONDS  # matches initial isolated assumption
    resolver.start()

    partition_mgr = PartitionManager(device_id, discovery, resolver)
    partition_mgr.start()

    sharer = AlertSharer(device_id, discovery, on_alert_received=resolver.handle_alert)
    sharer.start()

    try:
        while True:
            time.sleep(8)
            alert = _make_demo_alert(device_id)
            sharer.share_alert(alert)
            resolver.handle_alert(alert, from_peer=device_id)
    except KeyboardInterrupt:
        sharer.stop()
        partition_mgr.stop()
        resolver.stop()
        discovery.stop()

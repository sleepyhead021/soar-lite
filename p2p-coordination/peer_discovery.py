"""
Peer Discovery (Pillar 4, Step 1)
==================================
The simplest working version of "how do devices find each other without
a central server?" — each device periodically broadcasts a heartbeat on
the local network, and listens for heartbeats from others. Any device
that's heard from recently is considered a known, reachable peer.

This uses UDP broadcast, which works well on a single local network
(like a home Wi-Fi network or a Mininet/Docker simulated network) and
needs no central registry anywhere.

Run two or more copies of this file (with different DEVICE_ID values)
on the same machine or network to see them discover each other.
"""

import json
import socket
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from contracts import SyncMessage, SyncMessageType  # noqa: E402


BROADCAST_PORT = 50000
HEARTBEAT_INTERVAL_SECONDS = 2
PEER_TIMEOUT_SECONDS = 6  # if we haven't heard from a peer in this long, consider it gone


class PeerDiscovery:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.known_peers: Dict[str, datetime] = {}  # device_id -> last_heard_from
        self._lock = threading.Lock()
        self._running = False

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.bind(("", BROADCAST_PORT))

    def start(self):
        self._running = True
        threading.Thread(target=self._send_heartbeats, daemon=True).start()
        threading.Thread(target=self._listen, daemon=True).start()
        threading.Thread(target=self._expire_stale_peers, daemon=True).start()
        print(f"[{self.device_id}] Peer discovery started.")

    def stop(self):
        self._running = False
        self._sock.close()

    def get_active_peers(self):
        """Returns device_ids of peers heard from within PEER_TIMEOUT_SECONDS."""
        with self._lock:
            return list(self.known_peers.keys())

    def _send_heartbeats(self):
        while self._running:
            msg = SyncMessage(
                message_id=str(uuid.uuid4()),
                sender_device_id=self.device_id,
                message_type=SyncMessageType.HEARTBEAT,
                payload={},
                timestamp=datetime.utcnow().isoformat(),
            )
            data = json.dumps(
                {
                    "message_id": msg.message_id,
                    "sender_device_id": msg.sender_device_id,
                    "message_type": msg.message_type.value,
                    "payload": msg.payload,
                    "timestamp": msg.timestamp,
                }
            ).encode("utf-8")
            self._sock.sendto(data, ("<broadcast>", BROADCAST_PORT))
            time.sleep(HEARTBEAT_INTERVAL_SECONDS)

    def _listen(self):
        while self._running:
            try:
                data, _addr = self._sock.recvfrom(4096)
            except OSError:
                break  # socket closed on stop()
            try:
                parsed = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                continue

            sender = parsed.get("sender_device_id")
            if sender and sender != self.device_id:
                with self._lock:
                    is_new = sender not in self.known_peers
                    self.known_peers[sender] = datetime.utcnow()
                if is_new:
                    print(f"[{self.device_id}] Discovered new peer: {sender}")

    def _expire_stale_peers(self):
        while self._running:
            time.sleep(HEARTBEAT_INTERVAL_SECONDS)
            cutoff = datetime.utcnow() - timedelta(seconds=PEER_TIMEOUT_SECONDS)
            with self._lock:
                gone = [d for d, last_seen in self.known_peers.items() if last_seen < cutoff]
                for d in gone:
                    del self.known_peers[d]
            for d in gone:
                # This is exactly the "partition detected" moment — Step 4 of
                # your pillar builds real fallback behavior off this signal.
                print(f"[{self.device_id}] Peer went silent (possible partition): {d}")


if __name__ == "__main__":
    device_id = sys.argv[1] if len(sys.argv) > 1 else f"device_{uuid.uuid4().hex[:6]}"
    discovery = PeerDiscovery(device_id)
    discovery.start()

    try:
        while True:
            time.sleep(3)
            print(f"[{device_id}] Active peers: {discovery.get_active_peers()}")
    except KeyboardInterrupt:
        discovery.stop()

"""
Alert Sharing (Pillar 4, Step 2)
=================================
Builds directly on peer_discovery.py. Where discovery only exchanges
heartbeats, this module lets a device broadcast a real Alert to its
peers, and listens for Alerts broadcast by others.

This is still deliberately simple — plain UDP broadcast, no targeted
unicast, no reliability guarantees (a lost packet is just lost). That's
fine for now: reliability and conflict resolution when peers disagree
about an alert come in later steps of this pillar.

Run two or more copies with different device IDs to see them share
alerts with each other in real time:
    python3 alert_sharing.py device_A
    python3 alert_sharing.py device_B
"""

import json
import socket
import sys
import os
import threading
import time
import uuid
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from contracts import Alert, AlertType, SyncMessage, SyncMessageType  # noqa: E402
from serialization import to_json, sync_message_from_dict, alert_from_dict  # noqa: E402
from sync_logger import log_sync  # noqa: E402

from peer_discovery import PeerDiscovery  # noqa: E402


ALERT_PORT = 50001


class AlertSharer:
    def __init__(self, device_id: str, discovery: PeerDiscovery, on_alert_received=None):
        self.device_id = device_id
        self.discovery = discovery
        self.on_alert_received = on_alert_received or self._default_handler
        self._seen_alert_ids = set()
        self._running = False

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.bind(("", ALERT_PORT))

    def start(self):
        self._running = True
        threading.Thread(target=self._listen, daemon=True).start()
        print(f"[{self.device_id}] Alert sharing started.")

    def stop(self):
        self._running = False
        self._sock.close()

    def share_alert(self, alert: Alert):
        """Broadcasts an Alert to every peer on the local network."""
        msg = SyncMessage(
            message_id=str(uuid.uuid4()),
            sender_device_id=self.device_id,
            message_type=SyncMessageType.NEW_ALERT,
            payload=json.loads(to_json(alert)),  # plain JSON-safe dict
            timestamp=datetime.utcnow().isoformat(),
        )
        peers = self.discovery.get_active_peers()
        print(f"[{self.device_id}] Sharing alert {alert.alert_id} "
              f"({alert.alert_type.value}) with known peers: {peers}")
        self._sock.sendto(to_json(msg).encode("utf-8"), ("<broadcast>", ALERT_PORT))
        log_sync("SEND", "new_alert", "broadcast")

    def _listen(self):
        while self._running:
            try:
                data, _addr = self._sock.recvfrom(8192)
            except OSError:
                break  # socket closed on stop()
            try:
                parsed = json.loads(data.decode("utf-8"))
                msg = sync_message_from_dict(parsed)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

            if msg.sender_device_id == self.device_id:
                continue  # ignore our own broadcast
            if msg.message_type != SyncMessageType.NEW_ALERT:
                continue
            if msg.message_id in self._seen_alert_ids:
                continue  # avoid double-processing
            self._seen_alert_ids.add(msg.message_id)
            log_sync("RECV", "new_alert", msg.sender_device_id)

            alert = alert_from_dict(msg.payload)
            self.on_alert_received(alert, from_peer=msg.sender_device_id)

    def _default_handler(self, alert: Alert, from_peer: str):
        print(f"[{self.device_id}] Received alert from {from_peer}: "
              f"{alert.alert_type.value} (severity_hint={alert.severity_hint})")


def _make_demo_alert(device_id: str) -> Alert:
    """A stand-in for a real detection — replace with Tools Integration output later."""
    return Alert(
        alert_id=str(uuid.uuid4()),
        source_device_id=device_id,
        timestamp=datetime.utcnow().isoformat(),
        alert_type=AlertType.TRAFFIC_SPIKE,
        raw_features={"connections_per_min": 420.0},
        severity_hint=0.85,
    )


if __name__ == "__main__":
    device_id = sys.argv[1] if len(sys.argv) > 1 else f"device_{uuid.uuid4().hex[:6]}"

    discovery = PeerDiscovery(device_id)
    discovery.start()

    sharer = AlertSharer(device_id, discovery)
    sharer.start()

    try:
        while True:
            time.sleep(8)
            # Every 8 seconds, pretend this device detected something,
            # and share it with whoever's listening.
            sharer.share_alert(_make_demo_alert(device_id))
    except KeyboardInterrupt:
        sharer.stop()
        discovery.stop()

"""
Conflict Resolution (Pillar 4, Step 3)
========================================
When a device sees an Alert (its own, or one shared by a peer), it
evaluates that alert against its OWN local context and casts a vote:
does it agree this looks like a real threat, and how confident is it?

Every device broadcasts its vote. After a short voting window, each
device independently tallies all the votes it has seen (its own plus
any peers') using confidence-weighted voting, and reaches a decision.

Important design point: there is no permanent "leader" device here.
Every device does its own tally, and because they're all working from
the same shared votes, they reach the same conclusion independently.
This is deliberately simpler than a full leader-election scheme, and
is one of the two approaches suggested in the project document for
conflict resolution.

NOTE: the "local evaluation" here is a simple placeholder (a small
heuristic with random jitter) standing in for what a real device would
compute from its own Local Behavioral Shadow and Knowledge Base. Wire
those in once they exist — the voting and tallying logic doesn't change.

Run three copies to see a real quorum (two peers is the minimum to see
disagreement at all; three shows the weighting matter more clearly):
    python3 conflict_resolution.py device_A
    python3 conflict_resolution.py device_B
    python3 conflict_resolution.py device_C
"""

import json
import random
import socket
import sys
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Tuple

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from contracts import Alert, SyncMessage, SyncMessageType  # noqa: E402
from serialization import to_json, sync_message_from_dict  # noqa: E402

from peer_discovery import PeerDiscovery  # noqa: E402
from alert_sharing import AlertSharer, _make_demo_alert  # noqa: E402


VOTE_PORT = 50002
VOTING_WINDOW_SECONDS = 3


def compute_tally(votes: Dict[str, Tuple[float, bool]]) -> Tuple[str, float, int]:
    """
    Pure function, kept separate from networking so it's easy to test
    on its own. votes: {device_id: (confidence, agrees)}.
    Returns (label, score, participant_count).
    """
    if not votes:
        return "NO_VOTES", 0.0, 0
    score = sum(c if agrees else -c for c, agrees in votes.values())
    label = "CONFIRMED" if score > 0 else "DISMISSED" if score < 0 else "INCONCLUSIVE"
    return label, score, len(votes)


class ConflictResolver:
    def __init__(self, device_id: str, discovery: PeerDiscovery):
        self.device_id = device_id
        self.discovery = discovery
        self._votes: Dict[str, Dict[str, Tuple[float, bool]]] = {}
        self._lock = threading.Lock()
        self._running = False
        # Mutable on purpose: PartitionManager (Step 4) shortens this when
        # this device loses contact with all peers, so it doesn't sit
        # around waiting for votes that can no longer arrive.
        self.voting_window_seconds = VOTING_WINDOW_SECONDS

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.bind(("", VOTE_PORT))

    def start(self):
        self._running = True
        threading.Thread(target=self._listen, daemon=True).start()
        print(f"[{self.device_id}] Conflict resolution started.")

    def stop(self):
        self._running = False
        self._sock.close()

    def handle_alert(self, alert: Alert, from_peer: str):
        """
        Called whenever this device becomes aware of an alert — either
        one it generated itself, or one shared by a peer. Casts this
        device's own vote and schedules a tally after the voting window.
        """
        confidence, agrees = self._evaluate_locally(alert)
        with self._lock:
            self._votes.setdefault(alert.alert_id, {})[self.device_id] = (confidence, agrees)
        self._broadcast_vote(alert.alert_id, confidence, agrees)

        # Only the device that first sees an alert needs to schedule the
        # tally — peers will schedule their own when they first see it too,
        # but scheduling per-device-per-alert is harmless and simpler than
        # coordinating who's "responsible" for it.
        threading.Timer(self.voting_window_seconds, self._tally, args=(alert,)).start()

    def _evaluate_locally(self, alert: Alert) -> Tuple[float, bool]:
        """
        PLACEHOLDER local judgment. Replace with a real check against
        this device's Local Behavioral Shadow / Knowledge Base once
        those exist. For now: agree if severity_hint is high, with a
        little random jitter so devices don't always agree identically.
        """
        jitter = random.uniform(-0.15, 0.15)
        confidence = max(0.0, min(1.0, alert.severity_hint + jitter))
        agrees = confidence > 0.5
        return confidence, agrees

    def _broadcast_vote(self, alert_id: str, confidence: float, agrees: bool):
        msg = SyncMessage(
            message_id=str(uuid.uuid4()),
            sender_device_id=self.device_id,
            message_type=SyncMessageType.VOTE,
            payload={"alert_id": alert_id, "confidence": confidence, "agrees": agrees},
            timestamp=datetime.utcnow().isoformat(),
        )
        self._sock.sendto(to_json(msg).encode("utf-8"), ("<broadcast>", VOTE_PORT))

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
                continue
            if msg.message_type != SyncMessageType.VOTE:
                continue

            alert_id = msg.payload["alert_id"]
            confidence = msg.payload["confidence"]
            agrees = msg.payload["agrees"]
            with self._lock:
                self._votes.setdefault(alert_id, {})[msg.sender_device_id] = (confidence, agrees)

    def _tally(self, alert: Alert):
        with self._lock:
            votes = dict(self._votes.get(alert.alert_id, {}))
            # Clean up so this dict doesn't grow forever during a long run.
            self._votes.pop(alert.alert_id, None)

        label, score, participants = compute_tally(votes)
        peers_known = len(self.discovery.get_active_peers())

        if participants <= 1 and peers_known > 0:
            print(f"[{self.device_id}] Tally for {alert.alert_id}: only got my own vote "
                  f"even though {peers_known} peer(s) are known — possible partition or "
                  f"slow network. Falling back to my own judgment: {label} (score={score:.2f}).")
        else:
            print(f"[{self.device_id}] Tally for {alert.alert_id}: {label} "
                  f"(score={score:.2f}, {participants} vote(s) counted).")


if __name__ == "__main__":
    device_id = sys.argv[1] if len(sys.argv) > 1 else f"device_{uuid.uuid4().hex[:6]}"

    discovery = PeerDiscovery(device_id)
    discovery.start()

    resolver = ConflictResolver(device_id, discovery)
    resolver.start()

    sharer = AlertSharer(device_id, discovery, on_alert_received=resolver.handle_alert)
    sharer.start()

    try:
        while True:
            time.sleep(8)
            alert = _make_demo_alert(device_id)
            sharer.share_alert(alert)
            # This device also evaluates and votes on its own alert,
            # not just ones received from peers.
            resolver.handle_alert(alert, from_peer=device_id)
    except KeyboardInterrupt:
        sharer.stop()
        resolver.stop()
        discovery.stop()

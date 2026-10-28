"""Gossip-style pattern sync (Pillar 4, Step 5). UDP broadcast, no coordinator."""
import json, socket, threading, time, uuid
from datetime import datetime
from shared.contracts import SyncMessage, SyncMessageType
from shared.serialization import to_json, sync_message_from_dict
from shared.sync_logger import log_sync
import knowledge_base as kb

PORT, INTERVAL = 50003, 10

class PatternSync:
    def __init__(self, device_id):
        self.device_id, self._running = device_id, False
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.bind(("", PORT))

    def start(self):
        self._running = True
        threading.Thread(target=self._gossip, daemon=True).start()
        threading.Thread(target=self._listen, daemon=True).start()

    def stop(self):
        self._running = False
        self._sock.close()

    def _gossip(self):
        while self._running:
            msg = SyncMessage(str(uuid.uuid4()), self.device_id,
                              SyncMessageType.PATTERN_UPDATE,
                              {"patterns": kb.load()}, datetime.utcnow().isoformat())
            self._sock.sendto(to_json(msg).encode(), ("<broadcast>", PORT))
            log_sync("SEND", "pattern_update", "broadcast")
            time.sleep(INTERVAL)

    def _listen(self):
        while self._running:
            try:
                data, _ = self._sock.recvfrom(65535)
                msg = sync_message_from_dict(json.loads(data))
            except OSError:
                break
            except (ValueError, KeyError):
                continue
            if msg.sender_device_id == self.device_id or msg.message_type != SyncMessageType.PATTERN_UPDATE:
                continue
            known = kb.load()
            for pid, p in msg.payload.get("patterns", {}).items():
                if pid not in known:          # merge only unseen patterns
                    kb.add_pattern(pid, p)
                    log_sync("RECV", f"new_pattern:{pid}", msg.sender_device_id)
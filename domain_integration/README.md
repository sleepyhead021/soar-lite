# Pillar 3 — Domain & Evaluation (Member 3)

Owns: connecting real domain data into the pipeline, designing the attack
scenarios, and running the full evaluation.

## Your first steps (Stage B, Member 3)

1. Confirm the target domain with the team (the project document proposes a
   smart home ecosystem — cameras, plugs, thermostats, locks, a hub). List the
   exact devices/data sources you'll actually use.
2. Build adapters that convert whatever raw data your chosen devices produce
   into the shared `Alert` format from `shared/contracts.py`. Until real
   devices are available, test this against `shared/fake_data_generator.py`.
3. Write out each of the five attack scenarios in enough detail that they
   could be handed to someone else to run:
   - Data tampering
   - False data injection
   - DDoS/DoS
   - Node impersonation
   - Network partition exploitation
4. Set up your attack simulation tools (`hping3`, `Scapy`, `tc netem`) in the
   `testbed/` folder, one script per scenario.
5. Decide exactly how you'll measure each metric from the project document's
   evaluation section (detection rate, false positive rate, time-to-detection,
   time-to-containment, etc.) and build the logging to capture it automatically.

## What you owe the team

- The exact device/domain decision affects what Member 4's peer-to-peer layer
  needs to handle (how many devices, what kind of network) — confirm this
  early so it isn't a late surprise.
- Your evaluation results are the evidence the whole team's committee
  presentation rests on — document methodology clearly, not just final numbers.

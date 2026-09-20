# Pillar 1 — Adaptive Decision-Making (Member 1)

Owns: turning Alerts into Decisions, using an improved DRL agent.

## Your first steps (Stage B, Member 1)

1. Formally write down (in a `design.md` in this folder):
   - **State**: exactly what the agent observes (e.g. alert type, severity_hint,
     raw_features, recent history for this device).
   - **Action space**: use `ActionType` from `shared/contracts.py` — don't invent
     a separate set of actions.
   - **Reward function (first draft)**: what should be rewarded and punished?
     Start simple, e.g.: correctly blocking a real attack = +1, wrongly blocking
     normal activity = -1, missing a real attack = -2.
2. Build a simulated training loop that consumes alerts from
   `shared/fake_data_generator.py` and lets your agent try actions and receive
   reward, entirely offline — no live traffic yet.
3. Train a first version and sanity-check it: does it block obvious DDoS/tampering
   alerts and leave normal ones alone, at least most of the time?
4. Once that works, implement your specific improvement (see the main project
   document, Pillar 1) and retrain.
5. Build a simple non-adaptive baseline (fixed thresholds on `severity_hint`)
   to compare against later in evaluation.

## What you owe the team

- The `Decision` objects you produce must always include `contributing_factors`
  and a real `confidence_score` — Member 2 builds the explanation layer directly
  from these, so don't leave them as placeholders.
- Let Member 4 know what a "peer-originated alert" needs to look like so your
  agent can be triggered from either local or peer alerts during integration.

## Suggested libraries

`gymnasium` (to define your environment formally), `stable-baselines3` or plain
`PyTorch` (for the agent itself).

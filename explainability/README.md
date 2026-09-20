# Pillar 2 — Explainability (Member 2)

Owns: producing an accurate `Explanation` for every single `Decision`, generated
at the same moment the decision is made — never reconstructed afterward.

## Your first steps (Stage B, Member 2)

1. Sit down with Member 1 and understand exactly what data their agent has
   access to at decision time (confidence score, which factors mattered,
   any internal weighting). You cannot explain a decision well if you're
   guessing from the outside.
2. Confirm the `Explanation` shape in `shared/contracts.py` actually captures
   what you need — flag any gaps to the team early.
3. Build a function that takes a `Decision` (plus whatever raw internal data
   Member 1 exposes) and produces:
   - `factor_weights`: which inputs mattered and by how much
   - `matched_pattern_or_rule`: if this matched something known
   - `plain_language_summary`: one readable sentence, e.g.
     "Blocked because connection rate was 40x normal and matched a known
     DDoS pattern with high confidence."
4. Build a small test set of hand-crafted example decisions (you can fabricate
   these before Member 1's agent is ready) and manually verify your generated
   explanations would make sense to a non-technical reader.

## What you owe the team

- Never produce an explanation that isn't tied to real decision data — a
  plausible-sounding guess defeats the entire point of this pillar.
- Coordinate with whoever builds the dashboard (Stage D) so explanations are
  displayed clearly next to each decision, not buried or abbreviated.

## Suggested approach

No heavyweight ML explainability library is needed here — this is closer to
structured logging than research-grade XAI. Keep it simple and transparent.

"""Maps a Pillar 4 vote result onto an ActionType. Pure, so it's testable alone."""
ACTIVE = ("rate_limit", "block", "quarantine")

def apply_consensus(local_action: str, result: dict) -> dict:
    """local_action: what the DRL agent chose. result: dict from ConflictResolver.on_result.
    Returns a copy of result with 'action' (final) and 'overridden' recomputed."""
    label = result.get("label")
    final = local_action
    if label == "CONFIRMED" and local_action not in ACTIVE:
        final = "rate_limit"      # peers confirm a threat: floor at a mild response
    elif label == "DISMISSED" and local_action in ACTIVE:
        final = "monitor"         # peers dismiss it: de-escalate, keep watching
    # INCONCLUSIVE / NO_VOTES: keep the local decision
    return {**result, "action": final, "overridden": final != local_action}

from datetime import datetime, timedelta, timezone
from shared.contracts import ActionResult, ActionType

TTL = {"rate_limit": 300, "block": 900}  # seconds, temporary actions

def execute(decision) -> ActionResult:
    a = decision["chosen_action"]
    exp = None
    if a in TTL:
        exp = (datetime.now(timezone.utc) + timedelta(seconds=TTL[a])).isoformat()
    # Simulated: real version would call iptables/tc here
    print(f"[ACTION] {a} for alerts {decision['alert_ids']}")
    return ActionResult(decision["decision_id"], ActionType(a), True, exp, "simulated")
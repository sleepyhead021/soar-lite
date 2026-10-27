# Interfaces
- Alert: adapters -> coordination, decision engine (alert_id, source_device_id, timestamp, alert_type, raw_features, severity_hint)
- Decision: decision engine -> action unit, dashboard (decision_id, alert_ids, chosen_action, confidence_score, contributing_factors, timestamp)
- Explanation: explainer -> dashboard (explanation_id, decision_id, factor_weights, matched_pattern_or_rule, plain_language_summary)
- SyncMessage: peer layer -> peers (message_id, sender_device_id, message_type, payload, timestamp)
- ActionResult: action unit -> feedback, metrics (decision_id, action_taken, success, expires_at, notes)
- Entry point: `decide_and_explain(score_fn, feature_names, values, action_names, alert_ids, decision_id=..., baseline=..., shadow_deviation=..., consensus=...)` returns (decision, explanation, trace). Local and peer alerts use the same path.
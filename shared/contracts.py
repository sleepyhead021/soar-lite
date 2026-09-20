"""
Shared Data Contracts
=====================
These are the agreed-upon shapes of information passed between every
component of the project. Every team member's module should import
and use these classes rather than inventing their own versions —
this is what lets four independently-built pieces fit together later.

If a field needs to change, it must be discussed and agreed on by
the whole team first, since every pillar depends on these shapes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class ActionType(str, Enum):
    """The full set of choices the AI decision-maker is allowed to make."""
    IGNORE = "ignore"
    MONITOR = "monitor"
    RATE_LIMIT = "rate_limit"
    BLOCK = "block"
    QUARANTINE = "quarantine"


class AlertType(str, Enum):
    """Known categories of suspicious activity the system can raise."""
    TRAFFIC_SPIKE = "traffic_spike"
    SENSOR_ANOMALY = "sensor_anomaly"
    DATA_TAMPERING = "data_tampering"
    FALSE_DATA_INJECTION = "false_data_injection"
    UNKNOWN_PEER = "unknown_peer"          # possible node impersonation
    PEER_SILENT = "peer_silent"            # possible network partition
    OTHER = "other"


class SyncMessageType(str, Enum):
    NEW_ALERT = "new_alert"
    PATTERN_UPDATE = "pattern_update"
    HEARTBEAT = "heartbeat"
    VOTE = "vote"                          # used during conflict resolution


@dataclass
class Alert:
    """
    Produced whenever a device notices something suspicious.
    Built by: Tools Integration Unit (Member 3's domain-integration module,
    or the shared fake-data generator during early development).
    """
    alert_id: str
    source_device_id: str
    timestamp: str                          # ISO 8601 string, e.g. datetime.utcnow().isoformat()
    alert_type: AlertType
    raw_features: Dict[str, float]          # e.g. {"connections_per_min": 480.0}
    severity_hint: float                    # rough 0.0-1.0 first guess, not final


@dataclass
class Decision:
    """
    Produced by the AI Decision-Maker (Member 1's pillar) in response
    to one or more alerts.
    """
    decision_id: str
    alert_ids: List[str]                    # which alert(s) this responds to
    chosen_action: ActionType
    confidence_score: float                 # 0.0 - 1.0
    contributing_factors: List[str]         # short labels, e.g. ["rate_40x_normal", "matched_pattern_DDOS_01"]
    timestamp: str


@dataclass
class Explanation:
    """
    Produced by Member 2's pillar at the exact same moment as a Decision.
    Never reconstructed after the fact.
    """
    explanation_id: str
    decision_id: str
    factor_weights: Dict[str, float]        # e.g. {"connection_rate": 0.7, "known_pattern_match": 0.3}
    matched_pattern_or_rule: Optional[str]
    plain_language_summary: str


@dataclass
class SyncMessage:
    """
    Used by Member 4's peer-to-peer layer to share alerts, pattern
    updates, heartbeats, or conflict-resolution votes between devices.
    """
    message_id: str
    sender_device_id: str
    message_type: SyncMessageType
    payload: Dict[str, Any]
    timestamp: str


@dataclass
class ActionResult:
    """
    Produced by the Action Automation Unit after actually carrying
    out a Decision. Useful for evaluation (Member 3) and for the
    AI's learning feedback loop (Member 1).
    """
    decision_id: str
    action_taken: ActionType
    success: bool
    expires_at: Optional[str] = None        # for temporary actions like rate-limits
    notes: str = ""

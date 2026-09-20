"""
Serialization helpers for the shared data contracts.
=====================================================
Converts Alert / Decision / Explanation / SyncMessage / ActionResult
to and from JSON, handling the Enum fields correctly (e.g. AlertType,
ActionType, SyncMessageType).

Any pillar sending these objects over a network, writing them to a
file, or storing them in SQLite should use these functions rather
than each writing its own ad hoc JSON conversion — that's exactly the
kind of small inconsistency that causes integration bugs later.
"""

import json
from dataclasses import asdict
from enum import Enum

from contracts import (
    Alert, AlertType,
    Decision, ActionType,
    Explanation,
    SyncMessage, SyncMessageType,
    ActionResult,
)


class ContractJSONEncoder(json.JSONEncoder):
    """Lets json.dumps handle our Enum fields automatically."""
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


def to_json(obj) -> str:
    """Serialize any of the shared dataclasses to a JSON string."""
    return json.dumps(asdict(obj), cls=ContractJSONEncoder)


def alert_from_dict(d: dict) -> Alert:
    d = dict(d)
    d["alert_type"] = AlertType(d["alert_type"])
    return Alert(**d)


def decision_from_dict(d: dict) -> Decision:
    d = dict(d)
    d["chosen_action"] = ActionType(d["chosen_action"])
    return Decision(**d)


def explanation_from_dict(d: dict) -> Explanation:
    return Explanation(**d)


def sync_message_from_dict(d: dict) -> SyncMessage:
    d = dict(d)
    d["message_type"] = SyncMessageType(d["message_type"])
    return SyncMessage(**d)


def action_result_from_dict(d: dict) -> ActionResult:
    d = dict(d)
    d["action_taken"] = ActionType(d["action_taken"])
    return ActionResult(**d)

"""
behavioral_shadow.py  —  shared/ (Component 1: Local Behavioural Shadow)

Nobody owned this, and two pillars are blocked on it:
  * Pillar 2 needs per-feature means as the ablation baseline (zero is wrong
    for raw units like connections_per_min).
  * Pillar 3 needs per-feature z-scores for readable explanations.

So it lives in shared/, not in either pillar. One rolling per-device, per-feature
summary. No cloud, no numpy, O(1) memory per feature.

Welford's online algorithm with exponential decay, so old behaviour fades and a
device that legitimately changes habits stops being flagged forever.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field


@dataclass
class _Stat:
    n: float = 0.0
    mean: float = 0.0
    m2: float = 0.0

    def update(self, x: float, decay: float) -> None:
        self.n = self.n * decay + 1.0
        d = x - self.mean
        self.mean += d / self.n
        self.m2 = self.m2 * decay + d * (x - self.mean)

    @property
    def std(self) -> float:
        return math.sqrt(self.m2 / self.n) if self.n > 1 else 0.0


@dataclass
class BehavioralShadow:
    """What 'normal' looks like for ONE device.

    decay=0.999 ≈ a half-life of ~700 observations. Tune per feature rate.
    warmup = observations needed before z-scores are trusted; below it we
    report 0.0 rather than a confident-looking number from three samples.
    """
    device_id: str
    decay: float = 0.999
    warmup: int = 30
    _stats: dict[str, _Stat] = field(default_factory=dict)

    def observe(self, features: dict[str, float]) -> None:
        """Call on every benign/unlabelled reading. Do NOT call during a
        confirmed attack, or the attack becomes 'normal'."""
        for k, v in features.items():
            self._stats.setdefault(k, _Stat()).update(float(v), self.decay)

    def is_ready(self, key: str) -> bool:
        s = self._stats.get(key)
        return bool(s and s.n >= self.warmup)

    def mean(self, key: str, default: float = 0.0) -> float:
        s = self._stats.get(key)
        return s.mean if s and s.n > 0 else default

    def baseline(self, feature_names) -> list[float]:
        """Ablation baseline for Pillar 2: 'this feature at its normal value'."""
        return [self.mean(n) for n in feature_names]

    def z_scores(self, features: dict[str, float]) -> dict[str, float]:
        """Deviation from normal for Pillar 3 / explanation wording."""
        out = {}
        for k, v in features.items():
            s = self._stats.get(k)
            if not s or s.n < self.warmup or s.std == 0:
                out[k] = 0.0
            else:
                out[k] = (float(v) - s.mean) / s.std
        return out

    # --- persistence: survives a device reboot, a few KB on disk ---
    def to_json(self) -> str:
        return json.dumps({"device_id": self.device_id, "decay": self.decay,
                           "warmup": self.warmup,
                           "stats": {k: vars(v) for k, v in self._stats.items()}})

    @classmethod
    def from_json(cls, s: str) -> "BehavioralShadow":
        d = json.loads(s)
        sh = cls(d["device_id"], d["decay"], d["warmup"])
        sh._stats = {k: _Stat(**v) for k, v in d["stats"].items()}
        return sh

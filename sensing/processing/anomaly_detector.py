"""
anomaly_detector — lightweight rolling-baseline outlier flagger.

Designed to run on a Pi Zero. No numpy dependency: pure Python,
constant-time per update via Welford's online algorithm and an
exponentially-weighted moving average (EWMA).

Each detector tracks one named scalar value. Feed it readings via
``observe(value)``; ask whether the latest sample is anomalous via
``is_anomaly(value)`` or ``score(value)``. The default threshold is
3.0 standard deviations from the EWMA; tune per-channel.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RollingBaseline:
    """
    Maintains an EWMA + Welford variance for one scalar series.

    Attributes
    ----------
    alpha
        EWMA smoothing factor in (0, 1]. 0.05 ~ 1/20 sample memory.
        Higher → faster baseline drift, lower → more inertia.
    sigma_threshold
        Number of standard deviations from EWMA at which a sample
        is flagged as anomalous.
    warmup
        Number of samples to ingest before flagging. Avoids spurious
        anomalies while the baseline is still settling.
    """

    alpha: float = 0.05
    sigma_threshold: float = 3.0
    warmup: int = 8

    n: int = 0
    mean: float = 0.0
    m2: float = 0.0          # Welford running sum of squared deviations
    ewma: Optional[float] = None
    last_value: Optional[float] = None
    last_score: Optional[float] = None

    def observe(self, value: float) -> None:
        """Ingest a sample into the baseline."""
        value = float(value)
        # Welford for unbiased variance.
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        delta2 = value - self.mean
        self.m2 += delta * delta2
        # EWMA tracks the slow trend.
        if self.ewma is None:
            self.ewma = value
        else:
            self.ewma = self.alpha * value + (1.0 - self.alpha) * self.ewma
        self.last_value = value

    @property
    def variance(self) -> float:
        if self.n < 2:
            return 0.0
        return self.m2 / (self.n - 1)

    @property
    def stddev(self) -> float:
        return math.sqrt(self.variance)

    def score(self, value: float) -> float:
        """
        Z-like score: deviations from EWMA in units of stddev.

        Returns 0.0 during warmup or if stddev is zero (degenerate
        baseline — every sample so far has been identical).
        """
        if self.n < self.warmup or self.ewma is None:
            return 0.0
        sd = self.stddev
        if sd == 0.0:
            return 0.0
        return (float(value) - self.ewma) / sd

    def is_anomaly(self, value: float) -> bool:
        s = self.score(value)
        self.last_score = s
        return abs(s) >= self.sigma_threshold


@dataclass
class AnomalySummary:
    """Compact result of evaluating one reading against a baseline."""

    channel: str
    value: float
    ewma: Optional[float]
    stddev: float
    score: float
    is_anomaly: bool
    samples_seen: int


class AnomalyTracker:
    """
    Multi-channel detector. One :class:`RollingBaseline` per channel.

    The set of tracked channels is bounded by ``max_channels`` to
    prevent unbounded memory growth on nodes that see new sensor
    identifiers over their lifetime (mesh peers, hot-swap probes,
    timestamp-suffixed channel names). When the cap is hit, the
    least-recently-evaluated channel is evicted — so the active
    set always holds the most-recently-active channels.

    Typical use::

        tracker = AnomalyTracker()
        for reading in driver.read_loop():
            for chan, val in reading.values.items():
                summary = tracker.evaluate(reading.sensor_id + "/" + chan, val)
                if summary.is_anomaly:
                    primitive = build_primitive(...)  # escalate
    """

    DEFAULT_MAX_CHANNELS = 1024

    def __init__(
        self,
        alpha: float = 0.05,
        sigma_threshold: float = 3.0,
        warmup: int = 8,
        max_channels: Optional[int] = None,
    ) -> None:
        self._defaults = dict(
            alpha=alpha, sigma_threshold=sigma_threshold, warmup=warmup,
        )
        # Use OrderedDict so we can move-to-end on access for the
        # LRU eviction policy without a separate timestamp field.
        from collections import OrderedDict
        self._baselines: "OrderedDict[str, RollingBaseline]" = OrderedDict()
        self._max_channels = (
            max_channels if max_channels is not None
            else self.DEFAULT_MAX_CHANNELS
        )

    def baseline_for(self, channel: str) -> RollingBaseline:
        if channel in self._baselines:
            self._baselines.move_to_end(channel)
            return self._baselines[channel]

        baseline = RollingBaseline(**self._defaults)
        self._baselines[channel] = baseline
        # Evict the oldest entry if we just exceeded the cap.
        while len(self._baselines) > self._max_channels:
            self._baselines.popitem(last=False)
        return baseline

    def evaluate(self, channel: str, value: float) -> AnomalySummary:
        baseline = self.baseline_for(channel)
        score = baseline.score(value)
        is_anom = baseline.is_anomaly(value)
        baseline.observe(value)  # observe AFTER scoring so the
                                  # score reflects pre-update state
        return AnomalySummary(
            channel=channel,
            value=float(value),
            ewma=baseline.ewma,
            stddev=baseline.stddev,
            score=score,
            is_anomaly=is_anom,
            samples_seen=baseline.n,
        )

    def channels(self) -> list[str]:
        return sorted(self._baselines.keys())


__all__ = [
    "RollingBaseline",
    "AnomalySummary",
    "AnomalyTracker",
]

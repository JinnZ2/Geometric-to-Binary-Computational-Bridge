"""
local_logger — bind a set of sensors + processing + transmission into
one tickable callback.

This is the field-deployable orchestrator. Hand it a list of sensors
plus a Primitive recipe (which sensors map to which concept_id +
bounds + couplings), and it produces and ships one Primitive per
tick. If transmission is unavailable, the queue manager persists
the Primitive and the next-online tick flushes the backlog.

A typical wiring::

    drivers = [DS18B20Driver("surface", mock=True),
               CapacitiveSoilMoistureDriver("primary", mock=True)]
    recipe = PrimitiveRecipe(
        concept_id="soil_regime",
        domain="measured_kinesthetic",
        role="direct_observation",
        couplings=("temperature", "moisture"),
        bounds=("Superior_MN", "2026_ongoing", "0-50cm"),
    )
    logger = LocalLogger(drivers, recipe, obs_path=Path("./node.obs"))
    Scheduler(interval_seconds=300).run_forever(logger.tick)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from sensing.firmware.sensor_drivers.base import SensorDriver, SensorReading
from sensing.processing.anomaly_detector import AnomalyTracker
from sensing.processing.primitives_encoder import (
    Primitive,
    append_obs,
    build_primitive,
)

LOG = logging.getLogger(__name__)


@dataclass
class PrimitiveRecipe:
    """
    Static metadata that turns a set of readings into a Primitive.

    Held separately from the driver list so the same set of drivers
    can be used to emit Primitives under different concept_ids
    (e.g. an MLX90614 emits ``canopy_thermal`` during the day and
    ``warm_pass_event`` when its anomaly tracker flags a hot frame).
    """

    concept_id: str
    domain: str = "measured_kinesthetic"
    role: str = "direct_observation"
    couplings: Tuple[str, ...] = ()
    bounds: Tuple[str, str, str] = ("unknown", "unknown", "unknown")
    claim_ref: Optional[str] = None
    is_calibrated: bool = True


@dataclass
class LocalLogger:
    """Bind drivers + recipe + processing + storage into one callable."""

    drivers: Sequence[SensorDriver]
    recipe: PrimitiveRecipe
    obs_path: Path
    transmit: Optional[Callable[[Primitive], bool]] = None
    anomaly_tracker: Optional[AnomalyTracker] = None
    anomaly_role: str = "anomaly_signal"

    _primitives_emitted: int = field(default=0, init=False, repr=False)
    _anomalies_flagged: int = field(default=0, init=False, repr=False)
    _transmissions_queued: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self.obs_path = Path(self.obs_path)
        self.obs_path.parent.mkdir(parents=True, exist_ok=True)
        if self.anomaly_tracker is None:
            self.anomaly_tracker = AnomalyTracker()

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self, tick_number: int) -> Primitive:
        """Run one read + encode + log + transmit cycle."""
        readings: List[SensorReading] = []
        grades: List[float] = []
        for driver in self.drivers:
            readings.append(driver.read())
            grades.append(getattr(driver, "confidence_grade", 0.5))

        # Detect anomalies on a per-channel basis. Note that the
        # tracker observes the value AFTER scoring, so the score on
        # tick N reflects the baseline as of tick N-1 (correct).
        any_anomaly = False
        if self.anomaly_tracker is not None:
            for r in readings:
                for chan, val in r.values.items():
                    summary = self.anomaly_tracker.evaluate(
                        f"{r.sensor_id}/{chan}", float(val),
                    )
                    if summary.is_anomaly:
                        any_anomaly = True

        primitive = build_primitive(
            concept_id=self.recipe.concept_id,
            domain=self.recipe.domain,
            role=self.anomaly_role if any_anomaly else self.recipe.role,
            couplings=self.recipe.couplings,
            bounds=self.recipe.bounds,
            readings=readings,
            base_confidence_grades=grades,
            claim_ref=self.recipe.claim_ref,
            is_calibrated=self.recipe.is_calibrated,
        )

        append_obs(self.obs_path, primitive)
        self._primitives_emitted += 1
        if any_anomaly:
            self._anomalies_flagged += 1

        if self.transmit is not None:
            try:
                ok = bool(self.transmit(primitive))
            except Exception as exc:  # noqa: BLE001
                LOG.warning(
                    "transmit raised %s on tick %d — primitive saved "
                    "to %s", exc, tick_number, self.obs_path,
                )
                ok = False
            if not ok:
                self._transmissions_queued += 1

        return primitive

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        return {
            "primitives_emitted":   self._primitives_emitted,
            "anomalies_flagged":    self._anomalies_flagged,
            "transmissions_queued": self._transmissions_queued,
        }

    def close(self) -> None:
        for driver in self.drivers:
            try:
                driver.close()
            except Exception as exc:  # noqa: BLE001
                LOG.debug("close raised on %s: %s", driver, exc)


__all__ = ["LocalLogger", "PrimitiveRecipe"]

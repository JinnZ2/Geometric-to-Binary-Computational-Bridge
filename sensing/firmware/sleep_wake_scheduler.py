"""
sleep_wake_scheduler — sample-then-sleep loop for power-constrained nodes.

Sensors sleep 99% of the time. The scheduler wakes them on a fixed
interval, runs one read cycle, and goes back to sleep. The Pi itself
can be put into deeper sleep (rtcwake / cron + halt) but that
configuration is OS-specific and lives in the deployment guide
(``hardware/tier1_minimal.md``); this module covers the in-process
scheduling.

Two modes:

* ``run_forever`` — block until interrupted, dispatching a callback
  on every tick. Most field deployments use this.
* ``next_tick`` — single-step variant for tests and dry runs.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

LOG = logging.getLogger(__name__)


@dataclass
class Scheduler:
    """Fixed-interval ticker.

    Attributes
    ----------
    interval_seconds
        Time between cycle starts. The actual sleep is
        ``interval_seconds - cycle_duration`` so the period stays
        constant even if reads take variable time.
    jitter_seconds
        Optional random offset added to each sleep to spread network
        traffic across many nodes. Defaults to 0.
    minimum_sleep
        Floor on the actual sleep time, in case a cycle overruns the
        interval. Prevents tight-looping with no recovery time.
    """

    interval_seconds: float = 300.0
    jitter_seconds: float = 0.0
    minimum_sleep: float = 0.5

    _stop_requested: bool = field(default=False, init=False, repr=False)
    _ticks: int = field(default=0, init=False, repr=False)

    def request_stop(self) -> None:
        """Ask the scheduler to exit at the next opportunity."""
        self._stop_requested = True

    @property
    def ticks(self) -> int:
        return self._ticks

    def next_tick(
        self,
        callback: Callable[[int], None],
        sleep_fn: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> float:
        """
        Run one cycle.

        Returns the actual sleep duration that follows the callback.
        Useful for tests that want to advance through several ticks
        without sleeping.
        """
        start = clock()
        try:
            callback(self._ticks)
        except Exception as exc:  # noqa: BLE001
            # Field rule: never crash the scheduler. Log and recover.
            LOG.exception(
                "tick %d: callback raised %s — continuing",
                self._ticks, exc,
            )
        elapsed = clock() - start
        self._ticks += 1

        sleep_for = self.interval_seconds - elapsed
        if self.jitter_seconds:
            import random
            sleep_for += random.uniform(0.0, self.jitter_seconds)
        sleep_for = max(self.minimum_sleep, sleep_for)

        sleep_fn(sleep_for)
        return sleep_for

    def run_forever(
        self,
        callback: Callable[[int], None],
        max_ticks: Optional[int] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> int:
        """
        Block forever, dispatching ``callback(tick_number)`` on each
        tick. Returns the number of ticks completed when the loop
        exits (via :meth:`request_stop` or ``max_ticks``).
        """
        while not self._stop_requested:
            if max_ticks is not None and self._ticks >= max_ticks:
                break
            self.next_tick(callback, sleep_fn=sleep_fn, clock=clock)
        return self._ticks


__all__ = ["Scheduler"]

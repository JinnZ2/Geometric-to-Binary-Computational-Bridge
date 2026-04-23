"""
Event-driven scheduler with zero-crossing interrupt generation.

The binary encoder treats ``I > 0`` as "flowing" and everything else
as "not flowing," erasing the zero-crossing structure that defines
AC behaviour. This module recovers that structure by treating every
zero crossing of a signal as a scheduler *event* — something the
system can react to, not something that is averaged away.

Usage
-----
>>> import math
>>> sched = EventScheduler()
>>> crossings = []
>>> def on_cross(t, scheduler):
...     crossings.append(t)
>>> detect_zero_crossings(
...     signal_fn=lambda t: math.sin(2 * math.pi * 60 * t),
...     t0=0.0, t1=0.05, dt=1e-4,
...     scheduler=sched,
...     handler=on_cross,
... )
>>> sched.run(t_end=0.05)
>>> len(crossings) >= 5
True
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


@dataclass(order=True)
class Event:
    """One scheduled callable ordered by ``(time, priority)``."""

    time: float
    priority: int = field(default=0)
    fn: Callable[..., Any] = field(default=lambda *a, **k: None, compare=False)
    args: tuple = field(default=(), compare=False)


class EventScheduler:
    """
    A priority-queue event loop.

    The scheduler maintains a single ``time`` cursor. Each pop advances
    the cursor to the event's scheduled time, then calls
    ``event.fn(*event.args, self)`` — the scheduler is always passed
    as the last argument so handlers can schedule follow-up events.
    """

    def __init__(self) -> None:
        self.queue: List[Event] = []
        self.time: float = 0.0

    def schedule(
        self,
        time: float,
        fn: Callable[..., Any],
        args: tuple = (),
        priority: int = 0,
    ) -> None:
        heapq.heappush(self.queue, Event(time, priority, fn, args))

    def run(self, t_end: float) -> None:
        """Drain events whose scheduled time is ≤ ``t_end``."""
        while self.queue and self.queue[0].time <= t_end:
            event = heapq.heappop(self.queue)
            self.time = event.time
            event.fn(*event.args, self)

    def pending(self) -> int:
        """Number of events still queued."""
        return len(self.queue)


# ---------------------------------------------------------------------------
# Zero-crossing detection
# ---------------------------------------------------------------------------

def _default_handler(t: float, scheduler: EventScheduler) -> None:
    """Fallback handler that prints crossings. Replace in production."""
    # Intentionally side-effect free by default — test suites override
    # this via the ``handler`` argument of ``detect_zero_crossings``.
    pass


def detect_zero_crossings(
    signal_fn: Callable[[float], float],
    t0: float,
    t1: float,
    dt: float,
    scheduler: EventScheduler,
    handler: Optional[Callable[[float, EventScheduler], None]] = None,
    priority: int = 0,
) -> None:
    """
    Sweep a signal and enqueue one event per detected zero crossing.

    Detection rules:
      * a crossing is registered when ``prev_v * curr_v < 0`` (a sign
        flip between consecutive samples), or when either sample is
        exactly zero. The recorded time is ``t - dt/2`` — the midpoint
        between the sample and its predecessor.

    The handler must accept ``(crossing_time, scheduler)``. It defaults
    to a no-op so ``detect_zero_crossings`` is safe to call purely for
    its side-effect of populating the queue.
    """
    if handler is None:
        handler = _default_handler

    prev_t = t0
    prev_v = signal_fn(prev_t)
    t = t0 + dt

    while t <= t1 + 0.5 * dt:
        v = signal_fn(t)
        if prev_v == 0 or v == 0 or (prev_v * v < 0):
            crossing_time = t - dt / 2.0
            scheduler.schedule(
                crossing_time, handler, args=(crossing_time,), priority=priority
            )
        prev_t, prev_v = t, v
        t += dt


__all__ = [
    "Event",
    "EventScheduler",
    "detect_zero_crossings",
]

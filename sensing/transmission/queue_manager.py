"""
queue_manager — persistent FIFO for offline-tolerant transmission.

The field reality: solar-powered nodes spend long stretches
disconnected from any uplink. The queue is the buffer between
``LocalLogger`` and the radio: every Primitive lands here first,
the transmitter pops them off when it can, and a power-cycle does
not lose anything in flight.

Backing store: append-only ``.obs.queue`` file in the same format
as the main ``.obs`` log. Pops are tracked via a sibling
``.obs.queue.cursor`` file recording the byte offset of the next
unsent line. This avoids the cost of re-writing the queue on every
pop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from sensing.processing.primitives_encoder import (
    Primitive,
    obs_line_to_primitive,
    primitive_to_obs_line,
)

LOG = logging.getLogger(__name__)


@dataclass
class QueueManager:
    """
    Append-only persistent FIFO for Primitives.

    Parameters
    ----------
    queue_path
        Path to the queue file. A sibling ``<path>.cursor`` file
        tracks the next byte to send.
    """

    queue_path: Path

    def __post_init__(self) -> None:
        self.queue_path = Path(self.queue_path)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.queue_path.touch(exist_ok=True)
        self._cursor_path = self.queue_path.with_suffix(
            self.queue_path.suffix + ".cursor"
        )
        if not self._cursor_path.exists():
            self._cursor_path.write_text("0")

    # ------------------------------------------------------------------
    # Append
    # ------------------------------------------------------------------

    def push(self, primitive: Primitive) -> None:
        """Append a Primitive to the queue."""
        line = primitive_to_obs_line(primitive)
        with self.queue_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def push_many(self, primitives: Iterable[Primitive]) -> int:
        n = 0
        with self.queue_path.open("a", encoding="utf-8") as f:
            for p in primitives:
                f.write(primitive_to_obs_line(p) + "\n")
                n += 1
        return n

    # ------------------------------------------------------------------
    # Cursor read
    # ------------------------------------------------------------------

    def _cursor(self) -> int:
        try:
            return int(self._cursor_path.read_text().strip() or "0")
        except (OSError, ValueError):
            return 0

    def _set_cursor(self, offset: int) -> None:
        self._cursor_path.write_text(str(int(offset)))

    def pending_count(self) -> int:
        """Number of Primitives still waiting to be sent."""
        cursor = self._cursor()
        with self.queue_path.open("rb") as f:
            f.seek(cursor)
            return sum(1 for _ in f if _.strip())

    def peek(self, max_items: int = 1) -> List[Primitive]:
        """Return up to ``max_items`` Primitives without advancing cursor."""
        cursor = self._cursor()
        out: List[Primitive] = []
        # Explicit readline() avoids the iterator-buffering problem
        # that breaks tell() when using ``for line in f``.
        with self.queue_path.open("r", encoding="utf-8") as f:
            f.seek(cursor)
            while len(out) < max_items:
                line = f.readline()
                if not line:
                    break
                if line.strip():
                    out.append(obs_line_to_primitive(line))
        return out

    def pop_batch(self, max_items: int = 16) -> List[Primitive]:
        """
        Read up to ``max_items`` Primitives and advance cursor past them.

        Idempotent at the item level: if the process dies between
        reading and advancing the cursor, the next call returns the
        same items.
        """
        cursor = self._cursor()
        out: List[Primitive] = []
        new_cursor = cursor
        with self.queue_path.open("r", encoding="utf-8") as f:
            f.seek(cursor)
            while len(out) < max_items:
                line = f.readline()
                if not line:
                    break
                if line.strip():
                    out.append(obs_line_to_primitive(line))
                new_cursor = f.tell()
        if new_cursor != cursor:
            self._set_cursor(new_cursor)
        return out

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def compact(self) -> int:
        """
        Drop already-sent lines from the file. Returns bytes reclaimed.

        Safe to run when no transmitter is mid-pop. Useful after long
        offline stretches when the queue grows large.
        """
        cursor = self._cursor()
        if cursor == 0:
            return 0
        with self.queue_path.open("rb") as f:
            f.seek(cursor)
            tail = f.read()
        size_before = self.queue_path.stat().st_size
        self.queue_path.write_bytes(tail)
        self._set_cursor(0)
        return size_before - len(tail)

    def reset(self) -> None:
        """Truncate the queue and reset the cursor. Destructive."""
        self.queue_path.write_text("")
        self._set_cursor(0)


__all__ = ["QueueManager"]

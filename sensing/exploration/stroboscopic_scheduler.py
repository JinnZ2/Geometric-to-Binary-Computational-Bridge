#!/usr/bin/env python3
"""
stroboscopic_scheduler.py — Heavy frame scheduler.

Runs heavy frames (Diffusion, Ensemble) only on certain ticks,
while lightweight frames run every tick.
"""

from typing import Dict, List, Set, Optional, Callable
from enum import Enum
from .exploration_engine import FrameID, FrameContext, ExplorationFrame

class SchedulerMode(Enum):
    SYNC = "sync"           # all frames run every tick
    STROBE = "strobe"       # heavy frames run periodically
    ASYNC = "async"         # heavy frames run in background (conceptually)

class StroboscopicScheduler:
    """
    Manages frame execution with a strobe mechanism.
    Heavy frames are marked as 'heavy' and are only executed on ticks
    where `current_tick % interval == 0`.
    Lightweight frames are executed every tick.
    """
    
    def __init__(self, heavy_frames: Set[FrameID], interval: int = 10):
        """
        Args:
            heavy_frames: set of FrameIDs that are computationally expensive.
            interval: execute heavy frames every N ticks.
        """
        self.heavy_frames = heavy_frames
        self.interval = interval
        self.current_tick = 0
        self.last_heavy_results = {}  # cache results from last heavy execution
    
    def should_run(self, frame_id: FrameID) -> bool:
        """Determine if a frame should run on this tick."""
        if frame_id in self.heavy_frames:
            return (self.current_tick % self.interval) == 0
        return True  # lightweight frames always run
    
    def run_frame(self, frame: ExplorationFrame, context: FrameContext, binary_vec: np.ndarray) -> Dict:
        """
        Execute a frame, returning its result.
        If it's a heavy frame and we're not on a heavy tick, return the cached result.
        """
        if frame.id in self.heavy_frames:
            if self.should_run(frame.id):
                # Run heavy frame
                result = {
                    "metrics": frame.process_primitive(context, binary_vec),
                    "trial_results": frame.evaluate_claims(context),
                    "narrative": frame.generate_narrative(context, "Frame state")
                }
                # Cache the result
                self.last_heavy_results[frame.id] = result
                # Update the frame (training) only on heavy ticks
                frame.update(context)
                return result
            else:
                # Return cached result (may be None if never run)
                return self.last_heavy_results.get(frame.id, {
                    "metrics": {"cached": True, "reason": "stroboscopic"},
                    "trial_results": [],
                    "narrative": "[Cached heavy frame]"
                })
        else:
            # Lightweight frame: run every tick
            result = {
                "metrics": frame.process_primitive(context, binary_vec),
                "trial_results": frame.evaluate_claims(context),
                "narrative": frame.generate_narrative(context, "Frame state")
            }
            frame.update(context)  # lightweight frames still train every tick
            return result
    
    def tick(self):
        """Advance the tick counter."""
        self.current_tick += 1
    
    def get_heavy_ticks(self) -> List[int]:
        """Return the tick numbers where heavy frames will run."""
        heavy_ticks = []
        for t in range(self.current_tick, self.current_tick + 5 * self.interval, self.interval):
            heavy_ticks.append(t)
        return heavy_ticks

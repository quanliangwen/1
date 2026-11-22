"""Confirm an outbound sensor-outage crossing before enabling red viewpoints."""
from dataclasses import dataclass

import numpy as np


@dataclass
class EgressGate:
    origin: np.ndarray | None = None
    last_fix: np.ndarray | None = None
    entry: np.ndarray | None = None
    axis: np.ndarray | None = None
    outage_since: int | None = None
    fix_since: int | None = None
    released: int | None = None

    def update(self, step, pose, fixed, outage):
        if self.released is not None:
            return None
        if pose is None:
            return None
        pose = np.asarray(pose, dtype=float)
        if not np.isfinite(pose).all():
            return None
        if outage:
            if self.outage_since is None and self.last_fix is not None:
                self.outage_since = step
                self.entry = self.last_fix.copy()
                axis = self.entry-self.origin
                length = float(np.linalg.norm(axis))
                self.axis = axis/length if length >= 120. else None
                return "outage_entry", None
            self.fix_since = None
            return None
        if not fixed:
            self.fix_since = None
            return None
        if self.origin is None:
            self.origin = pose.copy()
        self.last_fix = pose.copy()
        if self.outage_since is None:
            return None
        if self.fix_since is None:
            self.fix_since = step
        if step-self.fix_since < 12:
            return None
        forward = None if self.axis is None else float((pose-self.entry) @ self.axis)
        crossed = self.fix_since-self.outage_since >= 20 and forward is not None and forward >= 140.
        self.entry = self.axis = None
        self.outage_since = self.fix_since = None
        if crossed:
            self.released = step
        return ("released" if crossed else "returned_or_unconfirmed"), forward

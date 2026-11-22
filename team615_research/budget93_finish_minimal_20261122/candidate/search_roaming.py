"""Keep search work outside the launch area after departure."""
from dataclasses import dataclass
import math

import numpy as np


@dataclass
class SearchRoaming:
    origin: tuple | None = None
    departed: bool = False
    radius: float = 140.
    target: tuple | None = None

    def observe(self, origin, pose):
        if self.origin is None and origin is not None:
            self.origin = tuple(origin)
        if self.origin is not None and math.dist(self.origin, pose) >= 180.:
            self.departed = True

    def allows(self, pose, target, route):
        if not self.departed:
            return True
        if not route or math.dist(self.origin, target) < self.radius:
            return False
        origin = np.asarray(self.origin)
        start = np.asarray(pose) - origin
        for waypoint in route:
            end = np.asarray(waypoint) - origin
            delta = end - start
            norm2 = float(delta @ delta)
            if norm2 > 0.:
                near = start + np.clip(-(start @ delta) / norm2, 0., 1.) * delta
                if near @ near < min(self.radius ** 2, start @ start) - 1e-6:
                    return False
            start = end
        return True

    def idle_waypoint(self, grid, pose, costs, peers, comm_range, search_route):
        """Prefer low-visit known cells and nearby live radio contacts."""
        if self.target is not None and math.dist(pose, self.target) > 24.:
            route = search_route(self.target)
            if route:
                return self.target, list(route)
        candidates = []
        for cell, cost in costs.items():
            if not 40. <= cost <= 240. or grid.evidence[cell] >= 0 or grid.clearance[cell] < 23.:
                continue
            point = tuple(grid.point(cell))
            contacts = sum(45. <= math.dist(point, peer) <= .8 * comm_range for peer in peers)
            candidates.append((float(grid.visits[cell]) - 2. * contacts + .015 * cost, point))
        self.target = None
        for _, point in sorted(candidates):
            route = search_route(point)
            if route:
                self.target = point
                return point, list(route)
        return tuple(pose), []


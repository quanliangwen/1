"""Recognize entry into a new search block from a route and the aircraft's own scans."""
from dataclasses import dataclass
import math

import numpy as np

from swarm_rescue.solutions.passage_ledger import PassageLedger


@dataclass
class Passage:
    step: int
    point: tuple
    direction: tuple
    visited: frozenset
    scans: int = 1


class DeepPlacement:
    MAX_WIDTH = 145.
    PROGRESS = 52.
    BLOCK_REACH = 90.

    def __init__(self):
        self.previous = None
        self.path_length = 0.
        self.visited = set()
        self.passage = None
        self.last_narrow = None
        self.zone = None
        self.active_block = None
        self.passages = PassageLedger()

    def near_neck(self, point, step):
        return (self.last_narrow is not None and step - self.last_narrow[0] <= 24
                and math.dist(point, self.last_narrow[1]) <= 26.)

    def here(self, point, radius):
        return self.zone is not None and math.dist(self.zone[1], point) <= radius

    @classmethod
    def narrow(cls, ranges, angles, course, movable):
        """Measure facing walls on both sides of the actual direction of travel."""
        relative = angles - course
        fwd = ranges * np.cos(relative)
        side = ranges * np.sin(relative)
        wall = ~movable & np.isfinite(ranges) & (ranges > 8.) & (ranges <= 100.) & (np.abs(fwd) <= 24.)
        left = -side[wall & (side < -8.)]
        right = side[wall & (side > 8.)]
        return left.size >= 2 and right.size >= 2 and np.median(left) + np.median(right) <= cls.MAX_WIDTH

    @staticmethod
    def wall_cells(drone, ranges, angles, movable, semantic):
        usable = ~movable & np.isfinite(ranges) & (ranges > 8.) & (ranges <= drone.blast_radius)
        yaw = drone.heading + angles[usable]
        hits = drone.pose + ranges[usable, None] * np.column_stack((np.cos(yaw), np.sin(yaw)))
        bombs = drone._known_bomb_positions(semantic)
        return {drone.memory.world_to_cell(point) for point in hits
                if all(math.dist(point, bomb) > drone.blast_radius for bomb in bombs)}

    def _observe_crossing(self, step, pose, course, narrow):
        gate = self.passage
        if gate is not None and (step - gate.step > 210 or math.dist(pose, gate.point) > 150.):
            self.passage = gate = None
        if narrow:
            if gate is None or math.dist(pose, gate.point) > 70.:
                self.passage = Passage(step, tuple(pose), tuple(course), frozenset(self.visited))
            elif gate.scans < 2:
                gate.scans += 1
        elif gate is not None and gate.scans >= 2:
            delta = pose - gate.point
            dx, dy = gate.direction
            if float(delta @ (dx, dy)) >= self.PROGRESS and abs(delta[0]*dy-delta[1]*dx) <= 80.:
                return gate
        return None

    def observe(self, drone, step, ranges, angles, semantic, audit):
        if ranges is None or step % 8 != drone.identifier % 8:
            return
        pose = np.asarray(drone.pose, dtype=float)
        prev, self.previous = self.previous, pose.copy()
        if prev is None:
            return
        delta = pose - prev
        distance = float(np.linalg.norm(delta))
        if not 3. <= distance <= 45.:
            return
        self.path_length += distance
        if not drone.search_roaming.departed:
            return
        task = drone.search_task
        near_task = task is not None and (math.dist(pose, task.point) <= self.BLOCK_REACH
                                         or drone.grid.cell(pose) in task.cells)
        # Observe passages during the established search. The opening corridor
        # itself does not release the reservation for a later search block.
        course = delta / distance
        relative = math.atan2(course[1], course[0]) - drone.heading
        movable = drone.memory.semantic_mask(ranges, angles, semantic)
        narrow = self.narrow(ranges, angles, relative, movable)
        before = len(self.passages.local)
        self.passages.observe(drone.identifier, step, pose, course, narrow)
        if len(self.passages.local) > before:
            audit.append((step, 'passage_crossed', self.passages.local[-1]))
        if not drone.route:
            return
        if narrow:
            self.last_narrow = (step, tuple(pose))
        if self.path_length >= 6. * drone.blast_radius:
            gate = self._observe_crossing(step, pose, course, narrow)
            if gate is not None and near_task and task.started not in gate.visited:
                cells = self.wall_cells(drone, ranges, angles, movable, semantic)
                if len(cells) >= 2 and self.active_block != task.started:
                    self.active_block = task.started
                    self.zone = step, tuple(pose)
                    self.passage = None
                    audit.append((step, "deep_zone", gate.step, gate.point, tuple(pose), int(task.started), len(cells)))
        if near_task:
            self.visited.add(task.started)


class RejectedPatch:
    def __init__(self):
        self.first = None
        self.skip = None

    def reject(self, point, step):
        if self.first is not None and step - self.first[0] <= 35 and math.dist(point, self.first[1]) < 38.:
            self.skip = (step + 100, self.first[1])
            self.first = None
            return True
        self.first = step, tuple(point)
        return False

    def blocked(self, point, step):
        return self.skip is not None and step <= self.skip[0] and math.dist(point, self.skip[1]) < 38.

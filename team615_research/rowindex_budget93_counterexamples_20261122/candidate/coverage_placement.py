"""Sensor-only red-team placement with marginal wall-coverage scoring.

Blast geometry is a public task constant, not simulator state. Positions and
wall evidence come exclusively from onboard sensors and received messages.
Placement is confirmed by inventory changes; requests never count as success.
"""

from __future__ import annotations

import math

import cv2
import numpy as np

from swarm_rescue.solutions.greedy_mapping import GreedyMappingDrone, MapMemory


def marginal_coverage(memory, bombs, radius):
    """Estimated uncovered wall area in a blast disk at each coarse cell."""
    stable = (memory.hits >= 3).astype(np.float32)
    wall = cv2.resize(stable, (memory.shape[1], memory.shape[0]),
                      interpolation=cv2.INTER_AREA)
    # Cap dense noisy hit clouds rather than rewarding repeated observations.
    wall = np.minimum(wall, 0.20)
    rr, cc = np.indices(memory.shape)
    xx = (cc + 0.5) * memory.CELL - memory.width / 2
    yy = memory.height / 2 - (rr + 0.5) * memory.CELL
    boundary = ((np.abs(xx) > memory.width / 2 - memory.CELL) |
                (np.abs(yy) > memory.height / 2 - memory.CELL))
    wall[boundary] *= 0.5
    for point in bombs:
        wall[(xx - point[0]) ** 2 + (yy - point[1]) ** 2 <= radius ** 2] = 0
    cells = int(math.ceil(radius / memory.CELL))
    ky, kx = np.mgrid[-cells:cells + 1, -cells:cells + 1]
    disk = ((kx * memory.CELL) ** 2 + (ky * memory.CELL) ** 2 <= radius ** 2).astype(np.float32)
    return cv2.filter2D(wall, -1, disk, borderType=cv2.BORDER_CONSTANT)


class CoveragePlacementDrone(GreedyMappingDrone):
    def __init__(self, identifier=None, misc_data=None, **kwargs):
        super().__init__(identifier=identifier, misc_data=misc_data, **kwargs)
        self.team_size = int(getattr(misc_data, 'number_drones', None) or 1)
        self.blast_radius = float(round(0.12 * min(self.size_area)))
        self.initial_inventory = None
        self.previous_inventory = None
        self.pending_drop = None
        self.last_attempt_step = -100
        self.drop_records = {}
        self.inventory_records = {}
        self.coverage = None
        self.last_coverage_step = -100
        self.placement_goal = None
        self.peer_placement_goals = {}

    @staticmethod
    def _empty_command():
        return {'forward': 0.0, 'lateral': 0.0, 'rotation': 0.0,
                'grasper': 0, 'place_bomb': 0}

    def define_message_for_all(self):
        message = super().define_message_for_all()
        message['drops'] = {key: value.copy() for key, value in self.drop_records.items()}
        records = dict(self.inventory_records)
        records[int(self.identifier or 0)] = (int(self.elapsed_timestep), int(self.carried_bombs_count()))
        message['inventories'] = records
        message['placement_goal'] = self.placement_goal
        return message

    def _messages(self):
        super()._messages()
        for _, message in self.communicator.received_messages:
            if not isinstance(message, dict) or message.get('kind') != 'greedy-map-v1':
                continue
            peer, ts = int(message['id']), int(message['step'])
            if ts > self.peer_placement_goals.get(peer, (-1, None))[0]:
                goal = message.get('placement_goal')
                self.peer_placement_goals[peer] = (ts, None if goal is None else np.asarray(goal, dtype=float).copy())
            for key, value in message.get('drops', {}).items():
                point = np.asarray(value, dtype=float)
                if isinstance(key, tuple) and len(key) == 2 and point.shape == (2,) and np.isfinite(point).all():
                    if key not in self.drop_records:
                        self.drop_records[key] = point.copy()
                        self.last_coverage_step = -100
            for peer, record in message.get('inventories', {}).items():
                ts, inventory = record
                old = self.inventory_records.get(int(peer), (-1, 0))
                if int(ts) > old[0] and int(inventory) >= 0:
                    self.inventory_records[int(peer)] = (int(ts), int(inventory))

    def _sync_placement(self, step):
        inventory = int(self.carried_bombs_count())
        if self.initial_inventory is None:
            self.initial_inventory = inventory
        if self.pending_drop is not None:
            before, point, attempt_step = self.pending_drop
            if inventory < before:
                key = (int(self.identifier or 0), self.initial_inventory - inventory)
                self.drop_records[key] = point.copy()
                self.last_coverage_step = -100
                print(f'[placement] drone={self.identifier} step={step} inventory={inventory} '
                      f'position=({point[0]:.1f},{point[1]:.1f})', flush=True)
                self.pending_drop = None
                self.placement_goal = None
                self.waypoints = []
                self.last_plan_step = -100
            elif step > attempt_step:
                # A silent rejection is retried only after another zero pulse.
                self.pending_drop = None
                self.placement_goal = None
                self.waypoints = []
                self.last_plan_step = -100
        self.previous_inventory = inventory
        self.inventory_records[int(self.identifier or 0)] = (step, inventory)

    def _all_inventory_empty(self):
        return all(peer in self.inventory_records and self.inventory_records[peer][1] == 0
                   for peer in range(self.team_size))

    def _is_returning(self, step):
        return int(self.carried_bombs_count()) == 0 and super()._is_returning(step)

    def _submission_due(self, step):
        if self._all_inventory_empty():
            return super()._submission_due(step)
        leader = int(self.identifier or 0) == 0
        # Missing/outdated peer reports never mean that all bombs were placed.
        return (step >= int((0.97 if leader else 0.985) * self.limit) or
                float(self.elapsed_walltime) >= (0.90 if leader else 0.95) * self.walltime_limit)

    def _known_bomb_positions(self, semantic):
        points = list(self.drop_records.values())
        for obj in semantic or ():
            if getattr(getattr(obj, 'entity_type', None), 'name', '') == 'BOMB':
                angle = self.heading + float(obj.angle)
                point = self.pose + float(obj.distance) * np.array([math.cos(angle), math.sin(angle)])
                points.append(point)
        return points

    def _placement_spacing(self, step):
        if step >= 0.88 * self.limit:
            # The actuator still enforces its exact 24-pixel safety constraint.
            return 0.0
        if step >= 0.72 * self.limit or float(self.elapsed_walltime) >= 0.74 * self.walltime_limit:
            return 32.0
        return 0.85 * self.blast_radius

    def _placement_allowed(self, step, semantic):
        spacing = self._placement_spacing(step)
        return all(np.linalg.norm(self.pose - point) >= spacing
                   for point in self._known_bomb_positions(semantic))

    def _plan_route(self, step, returning, peer_goals):
        self.placement_goal = None
        if int(self.carried_bombs_count()) > 0 and step >= 0.18 * self.limit:
            gain = marginal_coverage(self.memory, list(self.drop_records.values()), self.blast_radius)
            self.coverage, self.last_coverage_step = gain, step
            rr, cc = np.indices(self.memory.shape)
            xx = (cc + 0.5) * self.memory.CELL - self.memory.width / 2
            yy = self.memory.height / 2 - (rr + 0.5) * self.memory.CELL
            utility = gain.astype(float).copy()
            urgent = step >= 0.72 * self.limit
            if urgent:
                utility = np.maximum(utility, 0.30)
            spacing = max(24.0, self._placement_spacing(step)) + 32.0
            for point in self._known_bomb_positions(self.semantic_values()):
                utility[(xx - point[0]) ** 2 + (yy - point[1]) ** 2 < spacing ** 2] = -np.inf
            for ts, point in self.peer_placement_goals.values():
                if point is not None and step - ts < 80:
                    utility *= 1.0 - 0.85 * np.exp(-((xx - point[0]) ** 2 + (yy - point[1]) ** 2) /
                                                  self.blast_radius ** 2)
            if not urgent:
                utility[gain < 0.30] = -np.inf
            route, goal = self.memory.route(self.pose, utility=utility)
            if goal is not None:
                self.placement_goal = goal
                return route, goal
        return super()._plan_route(step, returning, peer_goals)

    def _drive(self, distances, angles, semantic=()):
        if int(self.elapsed_timestep) < self.escape_until:
            return super()._drive(distances, angles, semantic)
        if (self.placement_goal is not None and np.linalg.norm(self.pose - self.placement_goal) < 20
                and self._placement_allowed(int(self.elapsed_timestep), semantic)):
            return self._empty_command()
        return super()._drive(distances, angles, semantic)

    def _maybe_place(self, command, step, semantic):
        inventory = int(self.carried_bombs_count())
        retry_interval = 2 if step >= 0.72 * self.limit else 8
        if (self.submitted or self.pose is None or inventory <= 0 or
                self.pending_drop is not None or step - self.last_attempt_step < retry_interval):
            return
        if step < int(0.10 * self.limit) + 6 * int(self.identifier or 0):
            return
        placed = self.initial_inventory - inventory
        quota_deadline = (0.34 + 0.30 * placed / max(1, self.initial_inventory - 1)) * self.limit
        urgent = step >= int(0.72 * self.limit) or float(self.elapsed_walltime) >= 0.74 * self.walltime_limit
        if not self._placement_allowed(step, semantic):
            return
        if not urgent:
            if self.placement_goal is not None:
                if np.linalg.norm(self.pose - self.placement_goal) >= 20 and step < quota_deadline:
                    return
            if self.coverage is None or step - self.last_coverage_step >= 24:
                self.coverage = marginal_coverage(self.memory, list(self.drop_records.values()), self.blast_radius)
                self.last_coverage_step = step
            cell = self.memory.world_to_cell(self.pose)
            gain = float(self.coverage[cell])
            rr, cc = np.indices(self.memory.shape)
            local = self.memory.free & ((rr - cell[0]) ** 2 + (cc - cell[1]) ** 2 <=
                                        (0.8 * self.blast_radius / self.memory.CELL) ** 2)
            best = float(self.coverage[local].max()) if local.any() else gain
            if gain < 0.30:
                return
            if self.placement_goal is None and step < quota_deadline and gain < 0.70 * best:
                return
        command.update(forward=0.0, lateral=0.0, rotation=0.0, grasper=0, place_bomb=1)
        self.pending_drop = (inventory, self.pose.copy(), step)
        self.last_attempt_step = step

    def control(self):
        step = int(self.elapsed_timestep)
        self._sync_placement(step)
        command = super().control()
        self._maybe_place(command, step, self.semantic_values())
        return command

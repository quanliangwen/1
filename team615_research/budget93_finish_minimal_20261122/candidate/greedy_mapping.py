"""Sensor-only greedy exploration. No placement or explosive optimization.

Each drone has its own memory. Maps are merged only through received messages.
Coarse free-space cells support frontier planning; fine repeated lidar hits
support the final wall image. No simulator truth, map files or shared globals
are used by the controller.
"""

from __future__ import annotations

from swarm_rescue.solutions.exploration_phase import early_exploration_due

import heapq
import math
from typing import Optional

import cv2
import numpy as np

from swarm_rescue.simulation.drone.drone_abstract import DroneAbstract


def wrap_angle(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


class MapMemory:
    CELL = 16
    FINE = 2

    def __init__(self, width: int, height: int):
        self.width, self.height = int(width), int(height)
        self.shape = (math.ceil(height / self.CELL), math.ceil(width / self.CELL))
        self.hit_shape = (math.ceil(height / self.FINE), math.ceil(width / self.FINE))
        self.hits = np.zeros(self.hit_shape, dtype=np.uint8)
        self.free = np.zeros(self.shape, dtype=bool)
        self.visits = np.zeros(self.shape, dtype=np.uint8)

    def world_to_cell(self, point):
        x, y = point
        return (int(np.clip((self.height / 2 - y) // self.CELL, 0, self.shape[0] - 1)),
                int(np.clip((self.width / 2 + x) // self.CELL, 0, self.shape[1] - 1)))

    def cell_to_world(self, cell):
        row, col = cell
        return np.array([(col + 0.5) * self.CELL - self.width / 2,
                         self.height / 2 - (row + 0.5) * self.CELL])

    @staticmethod
    def semantic_mask(distances, angles, semantic, kinds=("DRONE", "DISPOSAL_CENTER", "BOMB")):
        mask = np.zeros(len(distances), dtype=bool)
        for obj in semantic or ():
            if getattr(getattr(obj, "entity_type", None), "name", "") in kinds:
                diff = np.abs((angles - float(obj.angle) + math.pi) % (2 * math.pi) - math.pi)
                mask |= (diff < 0.10) & (np.abs(distances - float(obj.distance)) < 24)
        return mask

    def observe(self, position, heading, distances, ray_angles, semantic=()):
        d = np.asarray(distances, dtype=float)
        a = np.asarray(ray_angles, dtype=float)
        usable = np.isfinite(d) & (d > 8) & (d < 302)
        # Teammates and the disposal center are not wall entities.
        movable = self.semantic_mask(d, a, semantic)

        hit = usable & ~movable & (d < 220)
        theta = heading + a
        xs = position[0] + d[hit] * np.cos(theta[hit])
        ys = position[1] + d[hit] * np.sin(theta[hit])
        cols = np.floor((xs + self.width / 2) / self.FINE).astype(int)
        rows = np.floor((self.height / 2 - ys) / self.FINE).astype(int)
        valid = (rows >= 0) & (cols >= 0) & (rows < self.hit_shape[0]) & (cols < self.hit_shape[1])
        indices, counts = np.unique(rows[valid] * self.hit_shape[1] + cols[valid], return_counts=True)
        flat = self.hits.ravel()
        flat[indices] = np.minimum(32, flat[indices].astype(np.int16) + counts).astype(np.uint8)

        # Ray interiors are observed free space, stopping before the obstacle.
        selected = np.flatnonzero(usable)[::2]
        if len(selected):
            samples = np.arange(8, 285, self.CELL, dtype=float)
            rr = np.broadcast_to(samples, (len(selected), len(samples)))
            good = rr < np.maximum(0, d[selected, None] - 24)
            xx = position[0] + rr * np.cos(theta[selected, None])
            yy = position[1] + rr * np.sin(theta[selected, None])
            cc = np.floor((xx + self.width / 2) / self.CELL).astype(int)
            rc = np.floor((self.height / 2 - yy) / self.CELL).astype(int)
            good &= (rc >= 0) & (cc >= 0) & (rc < self.shape[0]) & (cc < self.shape[1])
            self.free[rc[good], cc[good]] = True
        current = self.world_to_cell(position)
        self.free[current] = True
        self.visits[current] = min(255, int(self.visits[current]) + 1)
        return indices, counts

    def packet(self):
        ids = np.flatnonzero(self.hits.ravel() >= 2).astype(np.int32)
        return (ids, self.hits.ravel()[ids].copy(), np.packbits(self.free.ravel()), self.visits.copy())

    def merge(self, packet):
        ids, values, packed_free, visits = packet
        ids = np.asarray(ids)
        values = np.asarray(values)
        if ids.ndim != 1 or values.shape != ids.shape or np.asarray(visits).shape != self.shape:
            return
        if len(ids) and (int(ids.min()) < 0 or int(ids.max()) >= self.hits.size):
            return
        free = np.unpackbits(np.asarray(packed_free, dtype=np.uint8))
        if len(free) < self.free.size:
            return
        # Idempotent max-union avoids inventing evidence through repeated gossip.
        flat = self.hits.ravel()
        flat[ids] = np.maximum(flat[ids], values)
        self.free |= free[:self.free.size].reshape(self.shape).astype(bool)
        self.visits = np.maximum(self.visits, np.asarray(visits, dtype=np.uint8))

    def blocked(self):
        stable = (self.hits >= 3).astype(np.float32)
        density = cv2.resize(stable, (self.shape[1], self.shape[0]), interpolation=cv2.INTER_AREA)
        occupied = (density > 0.10).astype(np.uint8)
        return cv2.dilate(occupied, np.ones((3, 3), dtype=np.uint8)).astype(bool)

    def render(self):
        support = cv2.GaussianBlur(self.hits.astype(np.float32), (0, 0), 1.2)
        mask = (support >= 0.7).astype(np.uint8)
        mask = cv2.dilate(mask, np.ones((3, 3), dtype=np.uint8))
        grid = np.repeat(np.repeat(mask, self.FINE, axis=0), self.FINE, axis=1)
        return grid[:self.height, :self.width].copy()

    def route(self, position, identifier=0, peers=(), destination=None, utility=None):
        start = self.world_to_cell(position)
        blocked = self.blocked()
        walkable = self.free & ~blocked
        # Noisy hit clouds can touch the drone's current coarse cell.
        walkable[start] = True
        cost = np.full(self.shape, np.inf)
        parent = {}
        cost[start] = 0
        queue = [(0.0, start)]
        moves = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
        while queue:
            dist, cell = heapq.heappop(queue)
            if dist > cost[cell]:
                continue
            r, c = cell
            for dr, dc in moves:
                nr, nc = r + dr, c + dc
                if not (0 <= nr < self.shape[0] and 0 <= nc < self.shape[1]) or not walkable[nr, nc]:
                    continue
                if dr and dc and (not walkable[r + dr, c] or not walkable[r, c + dc]):
                    continue
                nd = dist + (1.414 if dr and dc else 1.0)
                if nd < cost[nr, nc]:
                    cost[nr, nc] = nd
                    parent[(nr, nc)] = cell
                    heapq.heappush(queue, (nd, (nr, nc)))

        reachable = np.isfinite(cost)
        if utility is not None:
            score = np.full(self.shape, -np.inf)
            values = np.asarray(utility, dtype=float)
            score[reachable] = values[reachable] / (1.0 + 0.04 * cost[reachable])
        elif destination is not None:
            wanted = self.world_to_cell(destination)
            rr, cc = np.indices(self.shape)
            score = -((rr - wanted[0]) ** 2 + (cc - wanted[1]) ** 2) - 0.05 * cost
        else:
            unknown = (~self.free & ~blocked).astype(np.float32)
            gain = cv2.boxFilter(unknown, -1, (9, 9), normalize=False, borderType=cv2.BORDER_CONSTANT)
            adjacent = cv2.dilate(unknown.astype(np.uint8), np.ones((3, 3), dtype=np.uint8)) > 0
            frontier = reachable & adjacent
            score = 5.0 * gain / (4.0 + cost) - 0.02 * self.visits
            # Weak deterministic preference spreads agents without fixed map knowledge.
            rr, cc = np.indices(self.shape)
            angle = np.arctan2(start[0] - rr, cc - start[1])
            preference = identifier * 2.399963
            score += 0.10 * np.cos(angle - preference)
            for peer in peers:
                if peer is None:
                    continue
                pr, pc = self.world_to_cell(peer)
                score -= 2.0 * np.exp(-((rr - pr) ** 2 + (cc - pc) ** 2) / 24.0)
            if frontier.any():
                reachable &= frontier
        score[~reachable] = -np.inf
        if utility is None:
            score[start] = -np.inf
        if not np.isfinite(score).any():
            return [], None
        goal = tuple(int(v) for v in np.unravel_index(np.argmax(score), self.shape))
        cells = [goal]
        while cells[-1] != start:
            cells.append(parent[cells[-1]])
        cells.reverse()
        return [self.cell_to_world(c) for c in cells[1:]], self.cell_to_world(goal)


class GreedyMappingDrone(DroneAbstract):
    def __init__(self, identifier=None, misc_data=None, **kwargs):
        super().__init__(identifier=identifier, misc_data=misc_data, **kwargs)
        width, height = self.size_area
        self.memory = MapMemory(width, height)
        self.limit = int(getattr(misc_data, "max_timestep_limit", None) or 2000)
        self.walltime_limit = float(getattr(misc_data, "max_walltime_limit", None) or 90)
        self.pose: Optional[np.ndarray] = None
        self.heading = 0.0
        self.heading_initialized = False
        self.rally = None
        self.peers = {}
        self.last_peer_step = {}
        self.waypoints = []
        self.goal = None
        self.cached_packet = None
        self.last_packet_step = -100
        self.last_plan_step = -100
        self.stuck_steps = 0
        self.progress_anchor = None
        self.escape_until = -1
        self.escape_sign = 1
        self.submitted = False

    def define_message_for_all(self):
        step = int(self.elapsed_timestep)
        if self.cached_packet is None or step - self.last_packet_step >= 20:
            self.cached_packet = self.memory.packet()
            self.last_packet_step = step
        return {"kind": "greedy-map-v1", "id": int(self.identifier or 0), "step": step,
                "map": self.cached_packet, "pos": None if self.pose is None else self.pose.copy(),
                "goal": self.goal, "rally": self.rally}

    def _messages(self):
        for _, msg in self.communicator.received_messages:
            if not isinstance(msg, dict) or msg.get("kind") != "greedy-map-v1":
                continue
            peer_id, step = int(msg["id"]), int(msg["step"])
            if step <= self.last_peer_step.get(peer_id, -1):
                continue
            self.last_peer_step[peer_id] = step
            self.memory.merge(msg["map"])
            self.peers[peer_id] = (step, msg.get("pos"), msg.get("goal"))
            if peer_id == 0 and msg.get("rally") is not None:
                self.rally = np.asarray(msg["rally"], dtype=float).copy()

    def _update_pose(self):
        gps = self.measured_gps_position()
        compass = self.measured_compass_angle()
        odom = self.odometer_values()
        if odom is not None and np.isfinite(odom).all() and self.pose is not None:
            distance, alpha, rotation = (float(v) for v in odom)
            self.pose += distance * np.array([math.cos(self.heading + alpha), math.sin(self.heading + alpha)])
            self.heading = wrap_angle(self.heading + rotation)
        if gps is not None and np.isfinite(gps).all():
            gps = np.asarray(gps, dtype=float)
            self.pose = gps.copy() if self.pose is None else self.pose + 0.25 * (gps - self.pose)
        if compass is not None and math.isfinite(float(compass)):
            if not self.heading_initialized:
                self.heading = float(compass)
                self.heading_initialized = True
            else:
                self.heading = wrap_angle(self.heading + 0.30 * wrap_angle(float(compass) - self.heading))
        if self.pose is not None and self.rally is None:
            self.rally = self.pose.copy()

    @staticmethod
    def _empty_command():
        return {"forward": 0.0, "lateral": 0.0, "rotation": 0.0, "grasper": 0}

    def _drive(self, distances, angles, semantic=()):
        cmd = self._empty_command()
        # Placed bombs have drone collision disabled. The disposal center
        # remains visible to the motion controller.
        distances = distances.copy()
        zone = MapMemory.semantic_mask(distances, angles, semantic, ("BOMB",))
        distances[zone] = 300.0
        finite = np.isfinite(distances)
        if not finite.any():
            return cmd
        if self.waypoints:
            while len(self.waypoints) > 1 and np.linalg.norm(self.waypoints[0] - self.pose) < 24:
                self.waypoints.pop(0)
            target_angle = math.atan2(*(self.waypoints[0] - self.pose)[::-1])
        else:
            # Greedy local fallback: favor clear directions with fewer visits.
            candidate = np.arange(-math.pi, math.pi, math.pi / 6)
            scores = []
            for angle in candidate:
                delta = np.abs((angles - angle + math.pi) % (2 * math.pi) - math.pi)
                sector = finite & (delta < 0.22)
                clearance = float(np.percentile(distances[sector], 25)) if sector.any() else 0
                absolute = self.heading + angle
                ahead = self.pose + min(100, clearance) * np.array([math.cos(absolute), math.sin(absolute)])
                cell = self.memory.world_to_cell(ahead)
                scores.append(min(clearance, 180) - 2.0 * self.memory.visits[cell] - 8 * abs(angle))
            target_angle = self.heading + candidate[int(np.argmax(scores))]
        error = wrap_angle(target_angle - self.heading)

        front = finite & (np.abs(angles) < 0.45)
        front_distance = float(np.min(distances[front])) if front.any() else 0
        left = finite & (angles > 0.20) & (angles < 1.2)
        right = finite & (angles < -0.20) & (angles > -1.2)
        l_clear = float(np.median(distances[left])) if left.any() else 0
        r_clear = float(np.median(distances[right])) if right.any() else 0

        if int(self.elapsed_timestep) < self.escape_until:
            rear = finite & (np.abs(angles) > 2.7)
            rear_clear = float(np.min(distances[rear])) if rear.any() else 0
            cmd["forward"] = -0.30 if rear_clear > 38 else 0
            cmd["rotation"] = 0.65 * self.escape_sign
            return cmd

        cmd["rotation"] = float(np.clip(1.4 * error, -0.7, 0.7))
        if front_distance < 48:
            sign = 1 if l_clear >= r_clear else -1
            cmd["rotation"] = 0.7 * sign
        else:
            alignment = max(0, math.cos(error))
            cmd["forward"] = float(0.65 * alignment * np.clip((front_distance - 48) / 55, 0, 1))
        # Do not push laterally into a wall while avoiding another drone.
        close_left = finite & (angles > 0.8) & (angles < 2.3)
        close_right = finite & (angles < -0.8) & (angles > -2.3)
        if close_left.any() and float(np.min(distances[close_left])) < 24 and r_clear > 55:
            # The engine applies lateral force along local +y (left).
            cmd["lateral"] = -0.15
        elif close_right.any() and float(np.min(distances[close_right])) < 24 and l_clear > 55:
            cmd["lateral"] = 0.15
        return cmd

    def _is_returning(self, step):
        return step >= int(0.72 * self.limit)

    def _plan_route(self, step, returning, peer_goals):
        memory = self.memory
        budget = 0.
        if (not returning and hasattr(self, 'coverage_model') and self.carried_bombs_count() > 0
                and self.placement_goal is None
                and self.assignment_goal is None and not self._seeking_fusion
                and self.pending_drop is None and not self.coverage_ready
                and step >= self.escape_until and not self.gps_is_disabled()
                and not self.compass_is_disabled()):
            execution = float(self.coverage_model.get('execution_steps', 0.))
            if execution > 0:
                slack = self._remaining_steps() - (self.INVENTORY_WORK_FACTOR * execution + 48.)
                budget = min(320., 2. * max(0., slack))
        memory._forward_budget = budget
        try:
            return memory.route(self.pose, int(self.identifier or 0), peer_goals,
                                self.rally if returning else None)
        finally:
            memory._forward_budget = 0.
            memory._forward_graph = None

    def _submission_due(self, step):
        deadline = (0.90 if int(self.identifier or 0) == 0 else
                    0.94 + 0.004 * min(10, int(self.identifier)))
        wall_deadline = 0.82 if int(self.identifier or 0) == 0 else 0.89
        return (step >= int(deadline * self.limit) or
                float(self.elapsed_walltime) >= wall_deadline * self.walltime_limit)

    def _submit_before_planning(self, step):
        return False

    def _submit_current_map(self):
        self.submit_exploration_map(self.memory.render())
        self.submitted = True

    def control(self):
        step = int(self.elapsed_timestep)
        self._update_pose()
        self._messages()
        if not self.submitted and self._submit_before_planning(step):
            return self._empty_command()
        if self.pose is None:
            return self._empty_command()
        lidar = self.lidar_values()
        angles = np.asarray(self.lidar_rays_angles(), dtype=float)
        if lidar is not None and step % 4 == 0:
            self.memory.observe(self.pose, self.heading, lidar, angles, self.semantic_values())

        returning = self._is_returning(step)
        if step - self.last_plan_step >= 24 or early_exploration_due(self, step, returning):
            peer_goals = [goal for ts, _, goal in self.peers.values() if step - ts < 100]
            self.waypoints, self.goal = self._plan_route(step, returning, peer_goals)
            self.last_plan_step = step

        if not self.submitted and self._submission_due(step):
            self._submit_current_map()
            return self._empty_command()

        if step % 30 == 0:
            if self.progress_anchor is not None and np.linalg.norm(self.pose - self.progress_anchor) < 8:
                self.stuck_steps += 30
            else:
                self.stuck_steps = 0
            self.progress_anchor = self.pose.copy()
            if self.stuck_steps >= 60:
                self.escape_until = step + 16
                self.escape_sign = 1 if (int(self.identifier or 0) + step // 30) % 2 else -1
                self.stuck_steps = 0
                self.waypoints = []
                self.last_plan_step = step
        if lidar is None:
            return self._empty_command()
        return self._drive(np.asarray(lidar, dtype=float), angles, self.semantic_values())

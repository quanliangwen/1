"""One bounded reconnection attempt by a late finisher, using live match messages."""

import math

import numpy as np

from swarm_rescue.solutions.deadline_submission import DeadlineSubmission


class FinalMapReconnect:
    CONTACT_AGE = 480
    LIVE_CONTACT = 12
    MAX_STEPS = 200
    MAX_DISTANCE = 280.
    SEND_MARGIN = 12
    RADIO_INTERIOR = 160.
    MIN_WALL_SECONDS = 8.

    def __init__(self):
        self.contacts = {}
        self.next_plan = 0
        self.route = []
        self.attempted = False
        self.first_window = None
        self.until = 0
        self.audit = []

    def record(self, drone, message, step):
        sender = message.get("id")
        if (type(sender) is not int or not 0 <= sender < drone.team_size or sender == drone.identifier
                or drone.pose is None or not drone.grid.pose_fixed):
            return
        for state in message.get("states", ()):
            if state["id"] != sender or not 0 <= step - state["step"] <= 3:
                continue
            point = state.get("point")
            if isinstance(point, (tuple, list)) and drone._inside_team_point(point):
                self.contacts[sender] = (step, tuple(point), tuple(map(float, drone.pose)))
            break

    def budget(self, step, deadline_start):
        steps = min(self.MAX_STEPS, deadline_start - step - self.SEND_MARGIN)
        return min(self.MAX_DISTANCE, max(0., steps * 1.45)), steps

    def eligible(self, drone, step):
        own = int(drone.identifier)
        snapshot = drone.final_maps.snapshots.get(own)
        last_drop = drone.last_confirmed_drop_step
        return (snapshot is not None and last_drop is not None and 0 <= snapshot[1] - last_drop <= 8
                and drone.previous_inventory == 0 and drone.pending_drop is None
                and not drone.submitted and drone.grid.pose_fixed and drone.mode in ("search", "explore")
                and drone.gap_probe is None and drone.local_escape.active is None
                and step >= drone.recovery_until and
                not drone.blocked_prefix.active(drone) and
                drone.walltime_limit - drone.elapsed_walltime > self.MIN_WALL_SECONDS)

    def acknowledged(self, drone):
        bit = 1 << int(drone.identifier)
        return any(stamp >= drone.final_maps.snapshots[int(drone.identifier)][1] and mask & bit
                   for stamp, mask in drone.final_maps.peers.values())

    @staticmethod
    def known(drone, route):
        for start, finish in zip([drone.pose, *route[:-1]], route):
            length = math.dist(start, finish)
            for sample in np.linspace(start, finish, max(2, 1 + math.ceil(length / 5))):
                cell = drone.grid.cell(sample)
                if drone.grid.evidence[cell] >= 0 or drone.grid.clearance[cell] < 23:
                    return False
        return bool(drone.blocked_prefix.view.guarded_route(drone, route, drone.blocked_prefix.outside))

    def select(self, drone, step, distance_limit):
        grid = drone.grid
        here = grid.cell(drone.pose)
        contacts = [(step - stamp, peer, point, received_at) for peer, (stamp, point, received_at)
                    in self.contacts.items() if self.LIVE_CONTACT < step - stamp <= self.CONTACT_AGE]
        if not contacts:
            return None, "no_recent_anchor"
        costs, _ = grid.tree(drone.pose)
        candidates = []
        for age, peer, point, received_at in sorted(contacts)[:2]:
            for cell, cost in costs.items():
                if not 20 <= cost <= distance_limit or grid.evidence[cell] >= 0 or grid.clearance[cell] < 23:
                    continue
                goal = tuple(map(float, grid.point(cell)))
                peer_distance = math.dist(goal, point)
                if peer_distance <= self.RADIO_INTERIOR and math.dist(goal, drone.pose) > 18:
                    rank = cost + .45 * peer_distance + .08 * math.dist(goal, received_at) + .08 * age
                    candidates.append((rank, peer, goal, age, cost))
        for _, peer, goal, age, cost in sorted(candidates)[:12]:
            route = list(grid.route(drone.pose, goal))
            if route and grid.cell(route[0]) == here:
                route.pop(0)
            if (route and drone.search_roaming.allows(drone.pose, goal, route)
                    and self.known(drone, route)):
                return (peer, goal, age, float(cost), route), None
        return None, "no_safe_route_in_budget"

    @staticmethod
    def live_clear(drone, target):
        ranges = drone.lidar_values()
        if ranges is None:
            return False
        ranges = np.asarray(ranges, dtype=float)
        angles = np.asarray(drone.lidar_rays_angles(), dtype=float)
        obstacles, _ = drone.blocked_prefix.hits(drone, ranges, angles)
        dx, dy = np.asarray(target) - drone.pose
        return drone.local_escape.clearance(math.atan2(dy, dx) - drone.heading, angles, ranges,
                                            math.hypot(dx, dy), obstacles)

    def finish(self, step, reason):
        self.audit.append((step, reason))
        self.route.clear()

    def waypoint(self, drone, original):
        step = int(drone.elapsed_timestep)
        deadline_start = DeadlineSubmission.window_start(drone.limit)
        if self.route:
            if self.acknowledged(drone):
                self.finish(step, "acknowledged")
            elif step >= self.until or not self.eligible(drone, step):
                self.finish(step, "cutoff_or_safety")
            elif any(0 <= step - stamp <= self.LIVE_CONTACT for stamp, _ in drone.final_maps.peers.values()):
                # Exchange while passing within radio range and release the detour.
                self.finish(step, "contact")
            else:
                while self.route and math.dist(drone.pose, self.route[0]) <= 8:
                    self.route.pop(0)
                if not self.route:
                    self.finish(step, "anchor_reached")
                elif self.known(drone, self.route[:2]) and self.live_clear(drone, self.route[0]):
                    return self.route[0]
                else:
                    self.finish(step, "live_safety_veto")
        snapshot = drone.final_maps.snapshots.get(int(drone.identifier))
        last_drop = drone.last_confirmed_drop_step
        if (self.first_window is None and snapshot is not None and last_drop is not None
                and 0 <= snapshot[1] - last_drop <= 8):
            self.first_window = step
            self.audit.append((step, "late_finisher", bool(drone.grid.pose_fixed),
                               sorted((peer, contact[0]) for peer, contact in self.contacts.items())))
        if self.attempted or step < self.next_plan or not self.eligible(drone, step):
            return original
        self.next_plan = step + 16
        if self.acknowledged(drone) or any(0 <= step - stamp <= self.LIVE_CONTACT
                                         for stamp, _ in drone.final_maps.peers.values()):
            return original
        distance, steps = self.budget(step, deadline_start)
        if distance < 30:
            return original
        plan, reason = self.select(drone, step, distance)
        if plan is None:
            self.audit.append((step, reason, round(distance, 1)))
            return original
        peer, goal, age, cost, route = plan
        if not self.live_clear(drone, route[0]):
            self.audit.append((step, "first_segment_veto", peer, goal, cost))
            return original
        self.route, self.attempted, self.until = route, True, step + steps
        self.audit.append((step, "started", peer, goal, age, cost, self.until, route[:]))
        return route[0]

"""Temporarily route around a bomb that repeatedly blocks a search prefix."""
import math

import numpy as np

from swarm_rescue.solutions.wall_view import WallView


class BlockedPrefix:
    RADIUS = 35.
    KEEP = 180

    def __init__(self):
        self.key = None
        self.since = 0
        self.last = -1
        self.next_check = 0
        self.first = None
        self.avoid = None
        self.until = 0
        self.audit = []
        self.view = WallView()

    @staticmethod
    def hits(drone, ranges, angles):
        semantic = drone.semantic_values() or ()
        objects = [(h.distance * math.cos(h.angle), h.distance * math.sin(h.angle))
                   for h in semantic if h.entity_type.name in ("BOMB", "DRONE", "DISPOSAL_CENTER")]
        bomb_mask = drone.memory.semantic_mask(ranges, angles, semantic, ("BOMB",))
        return objects, bomb_mask

    @classmethod
    def outside(cls, start, end, center):
        start = np.asarray(start) - center
        delta = np.asarray(end) - center - start
        length2 = float(delta @ delta)
        near = start if not length2 else start + delta * np.clip(-(start @ delta) / length2, 0., 1.)
        minimum = min(cls.RADIUS, float(np.linalg.norm(start)))
        return float(near @ near) >= minimum * minimum - 1e-6

    def active(self, drone):
        if self.avoid is not None and drone.elapsed_timestep < self.until:
            if self.first is not None and math.dist(drone.pose, self.first) <= 8.:
                self.first = None
            return True
        self.avoid = self.first = None
        return False

    def allows_waypoint(self, drone, point):
        return not self.active(drone) or self.outside(drone.pose, point, self.avoid)

    def update(self, drone, waypoint):
        step = int(drone.elapsed_timestep)
        active = self.active(drone)
        if (not drone.route or drone.goal is None or not drone.grid.pose_fixed
                or drone.mode not in ("search", "explore") or drone.carried_bombs_count()
                or drone.gap_probe is not None or drone.local_escape.active is not None
                or step >= drone.limit-80 or drone.walltime_limit-drone.elapsed_walltime < 6.):
            return waypoint
        delta = np.asarray(waypoint) - drone.pose
        length = float(np.linalg.norm(delta))
        if not 12. <= length <= 90.:
            return waypoint
        if step < self.next_check:
            return waypoint
        ranges = drone.lidar_values()
        if ranges is None:
            return waypoint
        ranges = np.asarray(ranges, dtype=float)
        angles = np.asarray(drone.lidar_rays_angles())
        direction = math.atan2(delta[1], delta[0]) - drone.heading
        fore = ranges * np.cos(angles-direction)
        side = np.abs(ranges * np.sin(angles-direction))
        blocked = (fore > 0.) & (fore <= min(length + 23., 65.)) & (side < 23.)
        objects, bombs = self.hits(drone, ranges, angles)
        if not (blocked & bombs).any():
            return waypoint
        bearings = angles[blocked & bombs] + drone.heading
        rays = ranges[blocked & bombs, None] * np.column_stack((np.cos(bearings), np.sin(bearings))) + drone.pose
        confirmed = [tuple(p) for p in drone.drop_records.values()
                     if not self.outside(drone.pose, waypoint, p)
                     and np.any(np.linalg.norm(rays-p, axis=1) < 24.)]
        if not confirmed:
            return waypoint
        center = min(confirmed, key=lambda p: math.dist(drone.pose,p))
        if self.key != center or step-self.last > 150:
            self.key, self.since = center, step
        self.last = step
        if step-self.since < 50 and not active:
            return waypoint
        self.next_check = step+24
        avoid = ((center,self.RADIUS),)
        if drone.search_roaming.departed:
            avoid += ((drone.search_roaming.origin,drone.search_roaming.radius),)
        route = list(drone.grid.route(drone.pose,drone.goal,avoid=avoid))
        # The start cell may be forced open by the planner. Only move out
        # from an initially occupied margin, and never cut back into it.
        if route and drone.grid.cell(route[0]) == drone.grid.cell(drone.pose):
            route.pop(0)
        if not route or not drone.search_roaming.allows(drone.pose,drone.goal,route):
            self.audit.append((step,"no_route",center,tuple(waypoint)))
            return self.view.try_view(self,drone,waypoint,avoid,angles,ranges,objects)
        first = np.asarray(route[0])-drone.pose
        first_length = float(np.linalg.norm(first))
        segments = list(zip([drone.pose,*route],route))
        if (not 8. <= first_length <= 40.
                or any(not self.outside(a,b,center) for a,b in segments)
                or any(drone.grid.evidence[c] >= 0 or drone.grid.clearance[c] < 23.
                       for a,b in segments
                       for p in np.linspace(a,b,math.ceil(math.dist(a,b)/5)+1)
                       if (c := drone.grid.cell(p)) != drone.grid.cell(drone.pose))):
            self.audit.append((step,"grid_rejected",center,tuple(waypoint),route[:3]))
            return waypoint
        first_direction = math.atan2(first[1],first[0])-drone.heading
        if not drone.local_escape.clearance(first_direction,angles,ranges,first_length,objects):
            self.audit.append((step,"live_rejected",center,tuple(waypoint),route[:3]))
            return waypoint
        self.avoid, self.first, self.until = center, tuple(route[0]), step+self.KEEP
        drone.route = route
        self.audit.append((step,"detour",center,tuple(waypoint),route[:3]))
        return route[0]

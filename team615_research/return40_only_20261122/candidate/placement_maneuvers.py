"""Sensor-only exceptions for a carried bomb and a short wall approach."""
from collections import deque
from dataclasses import dataclass
import math

import numpy as np

from swarm_rescue.solutions.passage_ledger import PassageLedger
from swarm_rescue.solutions.scan_geometry import project


def speed_and_velocity(drone):
    odom = drone.odometer_values()
    if odom is None or not np.all(np.isfinite(odom)):
        return None
    speed, bearing, turn = map(float, odom)
    yaw = drone.heading - turn + bearing
    return speed, speed * np.array((math.cos(yaw), math.sin(yaw)))


def laser_points(drone, ranges, angles, semantic):
    valid = np.isfinite(ranges) & (ranges > 5.)
    static = valid & ~drone.memory.semantic_mask(ranges, angles, semantic)
    headings = drone.heading + angles
    rays = np.column_stack((np.cos(headings), np.sin(headings)))
    return valid, rays, rays[static] * ranges[static, None]


def traffic_clear(drone, start, finish, semantic, step):
    """Reject traffic observed in the monitored corridor and received plans."""
    if any(hit.entity_type.name == "DRONE" and 0 < hit.distance <= 110. for hit in semantic):
        return False
    for owner, state in drone.states.items():
        if owner == drone.identifier or state.get("health", 0) <= 0:
            continue
        age = step - state["step"]
        point = state.get("point")
        if point is None or not 0 <= age <= 45:
            continue
        if PassageLedger._segment_distance(point, start, finish) <= 48.:
            return False
        goal = state.get("motion_goal")
        if goal is None:
            goal = state.get("goal")
        if goal is not None and any(
                PassageLedger._segment_distance(probe, point, goal) <= 48.
                for probe in np.linspace(start, finish, 5)):
            return False
    return True


def visible_lane(ranges, valid, rays, axis, span):
    # At least three central rays must reach the proposed exit. Side wall
    # returns outside this central tube do not constitute traffic clearance.
    projection = rays @ axis
    center = projection > math.cos(math.radians(5.))
    if not np.any(center) or np.count_nonzero(valid & center) < 3:
        return False
    return bool(np.all(valid[center]) and np.all(ranges[center] * projection[center] >= span + 2.))


@dataclass
class WallApproach:
    start: int
    point: tuple
    wall: tuple
    gain: float
    health: float
    confirmed_scans: int = 1
    count: int = 0


class PlacementManeuvers:
    def __init__(self):
        self.path = deque(maxlen=42)
        self.previous = None
        self.narrow_evidence = None
        self.narrow_used = False
        self.waiting_exit = None
        self.exit = None
        self.approach = None
        self.next_wall_attempt = 0
        self.audit = []

    def remember(self, drone, step):
        point = tuple(map(float, drone.pose))
        if (not drone.grid.pose_fixed or drone._odometry_only
                or self.previous is not None and math.dist(self.previous, point) > 14.):
            self.path.clear()
            self.narrow_evidence = None
            self.previous = None
            return
        self.previous = point
        if not self.path or math.dist(self.path[-1][1], point) >= 5.:
            self.path.append((step, point))
        while self.path and step - self.path[0][0] > 460:
            self.path.popleft()

    def prior_exit(self, drone):
        """Use a straight prefix along our own already observed flight."""
        origin = np.asarray(drone.pose)
        for stamp, exit_point in reversed(self.path):
            vector = np.subtract(exit_point, origin)
            length = float(np.linalg.norm(vector))
            cell = drone.grid.cell(exit_point)
            if not (26. <= length <= 102. and drone.grid.evidence[cell] < 0
                    and drone.grid.clearance[cell] >= 23.):
                continue
            same_trace = all(PassageLedger._segment_distance(point, origin, exit_point) <= 10.
                             for tick, point in self.path if tick >= stamp)
            if same_trace:
                return exit_point, vector / length, length
        return None

    def drop_in_lane(self, placement, drone, command, step, ranges, angles, semantic, count):
        if (self.narrow_used or count != 1 or ranges is None or not drone.grid.pose_fixed
                or drone._odometry_only or drone.pending_drop is not None or not self.path
                or drone.fast_closeout.phase(step) is not None
                or step >= drone.limit - 110 or drone.walltime_limit - drone.elapsed_walltime < 7.):
            return False
        exit_data = self.prior_exit(drone)
        if exit_data is None:
            self.note(step, "narrow_block", "history")
            return False
        point, axis, distance = exit_data
        if not traffic_clear(drone, drone.pose, point, semantic, step):
            self.note(step, "narrow_block", "traffic")
            return False
        valid, rays, points = laser_points(drone, ranges, angles, semantic)
        fit = drone.corridor_walls(axis, points)
        if (fit is None or fit[1] / 2 - abs(fit[2]) < drone.grid.HULL_CLEARANCE
                or not visible_lane(ranges, valid, rays, axis, distance)):
            self.note(step, "narrow_block", "live_exit")
            return False
        seen = self.narrow_evidence
        self.narrow_evidence = step, point, tuple(axis)
        if seen is None or not 0 < step - seen[0] <= 14 or math.dist(seen[1], point) > 12. or axis @ seen[2] < .96:
            self.note(step, "narrow_block", "one_scan")
            return False
        block = drone.second_drop._site_block(drone, drone.pose, step, semantic, stationary=True)
        motion = speed_and_velocity(drone)
        if block or motion is None or motion[0] > 1.3:
            self.note(step, "narrow_block", block or "speed")
            return False
        if not placement._spaced_from_bombs(drone, semantic, False) or not placement._patch_open(drone, semantic, step):
            self.note(step, "narrow_block", "spacing_or_density")
            return False
        gain = drone.team_wall.query(drone, semantic, step)(drone.pose)[0]
        floor = drone.second_drop.opportunity_floor(placement._coverage_minimum(step, drone.limit))
        if gain < floor:
            self.note(step, "narrow_block", "coverage")
            return False
        self.waiting_exit = point
        self.audit.append((step, "narrow_request", tuple(drone.pose), point, float(fit[1]), gain))
        placement.place(drone, command, step, "narrow_short_drop", count)
        return True

    def confirmed(self, step, accepted):
        if self.waiting_exit is None:
            return
        if accepted:
            self.narrow_used = True
            self.exit = step, self.waiting_exit
        self.waiting_exit = None

    def note(self, step, event, result):
        # Record transitions and periodically witness a repeated veto.
        if not self.audit or self.audit[-1][1:3] != (event, result) or step-self.audit[-1][0] >= 40:
            self.audit.append((step, event, result))

    @staticmethod
    def wall_lines(placement, drone, ranges, angles, semantic):
        points = np.asarray(placement.lidar_lines(drone,ranges,angles,semantic), dtype=float)
        return project(points.reshape(-1,2), drone.pose, drone.heading).reshape(-1,2,2)

    def start_approach(self, placement, drone, step, ranges, angles, semantic, current, estimate, count):
        if (self.approach is not None or step < self.next_wall_attempt or ranges is None
                or not drone.grid.pose_fixed or drone._odometry_only
                or drone.limit-step < 140 or drone.walltime_limit-drone.elapsed_walltime < 7.):
            return False
        self.next_wall_attempt = step + 95
        best = None
        for a, b in self.wall_lines(placement,drone,ranges,angles,semantic):
            tangent = b - a
            span = float(np.linalg.norm(tangent))
            if span < 22.:
                continue
            tangent /= span
            along = float((drone.pose - a) @ tangent)
            if not 0. <= along <= span:
                continue
            wall = a + along * tangent
            normal = drone.pose - wall
            distance = float(np.linalg.norm(normal))
            if distance < 42.:
                continue
            normal /= distance
            for offset in (28.,36.,48.):
                point = tuple(wall + offset * normal)
                travel = math.dist(drone.pose, point)
                if (not 12. <= travel <= 60. or not drone._inside_team_point(point)
                        or not drone.search_roaming.allows(drone.pose,point,[point])
                        or drone._placement_block(point,step,semantic,stationary=False)
                        or not drone.team_wall.corridor_clear(drone,point,ranges,angles,semantic)):
                    continue
                gain = estimate(point)[0]
                if not drone.second_drop.worthwhile(gain,current):
                    continue
                rank = gain, -offset, -travel
                if best is None or rank > best[0]:
                    best = rank, point, tuple(wall)
        if best is None:
            return False
        rank, point, wall = best
        self.approach = WallApproach(step,point,wall,current,drone.drone_health,count=count)
        self.audit.append((step,"wall_approach_started",tuple(drone.pose),point,current,rank[0]))
        placement.wall_approach = True
        return True

    def _cancel_wall(self, placement, step, why):
        self.approach = None
        placement.wall_approach = None
        self.audit.append((step,"wall_approach_stopped",why))

    def advance(self, placement, drone, command, step, ranges, semantic):
        if self.exit is not None:
            start, point = self.exit
            if math.dist(drone.pose,point) <= 10. and drone.grid.clearance[drone.grid.cell(drone.pose)] >= 23.:
                self.exit = None
                self.audit.append((step,"narrow_exit_reached",tuple(drone.pose)))
                return False
            motion = speed_and_velocity(drone)
            if step-start >= 135 or ranges is None or motion is None or not drone.grid.pose_fixed:
                self.exit = None
                self.audit.append((step,"narrow_exit_stopped","timeout_or_sensors"))
                return False
            if not traffic_clear(drone,drone.pose,point,semantic,step):
                command.update(forward=0.,lateral=0.,rotation=0.)
                self.note(step,"narrow_exit_wait","traffic")
                return True
            command.update(drone.drive(point,motion[1],backout=True))
            return True
        plan = self.approach
        if plan is None:
            return False
        if drone.drone_health < plan.health:
            self._cancel_wall(placement,step,"health")
            return False
        motion = speed_and_velocity(drone)
        if (ranges is None or motion is None or step-plan.start >= 40 or drone.limit-step < 60
                or drone.walltime_limit-drone.elapsed_walltime < 4. or drone.previous_inventory!=plan.count):
            self._cancel_wall(placement,step,"budget_or_sensors")
            return False
        angles = np.asarray(drone.lidar_rays_angles())
        ranges = np.asarray(ranges)
        if (drone._placement_block(plan.point,step,semantic,stationary=False)
                or not drone.team_wall.corridor_clear(drone,plan.point,ranges,angles,semantic)):
            self._cancel_wall(placement,step,"clearance")
            return False
        if plan.confirmed_scans < 3:
            if not any(PassageLedger._segment_distance(plan.wall,a,b)<=8.
                       for a,b in self.wall_lines(placement,drone,ranges,angles,semantic)):
                self._cancel_wall(placement,step,"wall_unconfirmed")
                return False
            plan.confirmed_scans += 1
        if math.dist(drone.pose,plan.point) > 6.:
            command.update(drone.drive(plan.point,motion[1]))
            for axis in ("forward","lateral"):
                command[axis] = float(np.clip(command[axis],-.3,.3))
            return True
        command.update(drone.drive(drone.pose,motion[1]))
        if motion[0] > 1.0:
            return True
        gain = drone.team_wall.query(drone,semantic,step)(drone.pose)[0]
        if (not drone.second_drop.worthwhile(gain,plan.gain)
                or drone._placement_block(drone.pose,step,semantic,stationary=True)
                or not placement._first_drop_exit_clear(drone,ranges,semantic)
                or not placement._patch_open(drone,semantic,step)):
            self._cancel_wall(placement,step,"arrival")
            return False
        self.approach = None
        placement.wall_approach = None
        self.audit.append((step,"wall_approach_drop",tuple(drone.pose),gain))
        placement.place(drone,command,step,"short_wall_approach",plan.count)
        return True


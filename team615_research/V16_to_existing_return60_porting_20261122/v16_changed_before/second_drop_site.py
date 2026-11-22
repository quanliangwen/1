"""A short reservation binds a coverage improvement to the second drop site."""
from copy import copy
import math

import numpy as np


class SecondDropSite:
    SITE_CLEARANCE = 6.
    MAX_STEPS = 30
    ARRIVAL = 8.
    FAST_RETRY_AFTER = 8
    OBSERVE_INTERVAL = 16
    CACHE_STEPS = 72
    MAX_CACHED = 12
    REACH = 36.

    def __init__(self):
        self.plan = None
        self.used = False
        self.retry_at = 0
        self.audit = []
        self.backups = []
        self.survey_coverage = None

    @staticmethod
    def worthwhile(gain, current):
        return gain >= max(current + .25, 1.25 * current)

    def packet(self, step):
        if self.plan is None:
            return None
        start, point, _, _ = self.plan
        return (step, point) if step-start < self.MAX_STEPS else None

    def gate(self, drone, step, ranges):
        if drone.initial_inventory != 2 or drone.previous_inventory != 1:
            return "inventory"
        if drone.pending_drop is not None or drone.drop_departure.started is not None:
            return "first_drop_not_clear"
        if not drone.grid.pose_fixed or drone._odometry_only or not drone.search_roaming.departed:
            return "position"
        if step >= drone.limit-30 or drone.walltime_limit-drone.elapsed_walltime <= 4.:
            return "budget"
        if ranges is None:
            return "no_lidar"
        if not drone.route:
            return "no_route"
        return None

    def eligible(self, drone, step):
        return (drone.initial_inventory == 2 and drone.previous_inventory == 1
                and drone.pending_drop is None and drone.drop_departure.started is None
                and drone.grid.pose_fixed and not drone._odometry_only
                and step < drone.limit-30 and drone.walltime_limit-drone.elapsed_walltime > 4.)

    @classmethod
    def route_sites(cls, pose, route):
        previous = np.asarray(pose,dtype=float)
        knots = iter((12.,24.,cls.REACH))
        sample = next(knots)
        covered = 0.
        for node in list(route)[:4]:
            point = np.asarray(node,dtype=float)
            delta = point-previous
            length = float(np.linalg.norm(delta))
            if length <= 1.e-6:
                continue
            while sample <= covered+length:
                yield tuple(map(float,previous+delta*((sample-covered)/length)))
                sample = next(knots,None)
                if sample is None:
                    return
            covered += length
            previous = point

    def keep_backup(self, step, point, gain):
        # Refresh a nearby site with the newer observation. Keep spatially
        # distinct choices within the same small, expiring list.
        self.backups = [row for row in self.backups if step-row[0] <= self.CACHE_STEPS
                        and math.dist(point,row[1]) >= self.ARRIVAL]
        self.backups.append((step,point,gain))
        if len(self.backups) > self.MAX_CACHED:
            del self.backups[0]

    def _site_block(self, drone, point, step, semantic, *, stationary):
        return drone._placement_block(point, step, semantic, stationary=stationary,
                                      minimum_clearance=self.SITE_CLEARANCE)

    def checks(self, drone, step, point, ranges, angles, semantic, current, nominal, gain):
        failure = []
        if not drone._inside_team_point(point):
            return ["bounds"],{}
        # Keep the original combined validator authoritative. Record all
        # independent reasons as several can apply to the same candidate.
        block = self._site_block(drone, point, step, semantic, stationary=False)
        if block:
            failure.append(block)
        cell = drone.grid.cell(point)
        mapped = float(drone.grid.clearance[cell])
        evidence = int(drone.grid.evidence[cell])
        if "clearance" not in failure and (mapped < self.SITE_CLEARANCE or evidence >= 0):
            failure.append("clearance")
        if not drone.team_wall.corridor_clear(drone,point,ranges,angles,semantic):
            failure.append("live_corridor")
        if gain < nominal:
            failure.append("coverage_floor")
        if current is not None and not self.worthwhile(gain,current):
            failure.append("coverage_increment")
        return failure,dict(map_clearance=mapped if math.isfinite(mapped) else None,evidence=evidence)

    def assess(self, drone, step, ranges, semantic, sites, *, early):
        if self.survey_coverage is None:
            self.survey_coverage = copy(drone.fine_wall_coverage)
            self.survey_coverage._alignment_cache = {}
            self.survey_coverage._alignment_epoch = None
        coverage = self.survey_coverage
        angles = drone.lidar_rays_angles()
        bombs = drone._known_bomb_positions(semantic)
        claims = drone.team_wall.claims(drone,step)
        spacing = max(32.,drone._placement_spacing(step))
        radius = drone.blast_radius

        def measure(point, obstacles):
            return coverage.measure(drone.memory,point,obstacles,radius,step=step)[0]

        estimate = (lambda point: measure(point,bombs+claims)) if early else drone.team_wall.query(drone,semantic,step)
        baseline = None if early else estimate(drone.pose)[0]
        floor = float(drone.placement._coverage_minimum(step,drone.limit))
        origin = tuple(map(float,drone.pose))
        best = None
        best_rank = None
        original = None
        rows = []
        for source,point,recorded in sites:
            gain = estimate(point) if early else estimate(point)[0]
            all_walls = measure(point,())
            after_bombs = measure(point,bombs)
            failure,metrics = self.checks(drone,step,point,ranges,angles,semantic,baseline,floor,gain)
            distances = [math.dist(point,bomb) for bomb in bombs]
            nearest = min(distances,default=None)
            if nearest is not None and nearest < spacing and "spacing" not in failure:
                failure.append("spacing")
            metrics.update(distance=math.dist(origin,point),nearest_bomb=nearest,spacing=spacing,
                           gross=all_walls,after_bombs=after_bombs,gain=gain)
            rows.append((source,point,recorded,failure,metrics))
            if failure:
                continue
            if early:
                self.keep_backup(step,point,gain)
                continue
            legacy_rank = gain, -metrics["distance"]
            if original is None or legacy_rank > original[0]:
                original = legacy_rank, point
            rank = drone.team_wall.site_rank(point, gain, metrics["distance"], bombs + claims, radius)
            if best_rank is None or rank > best_rank:
                best_rank = rank
                best = legacy_rank, point, source, recorded
        if best is not None and best[1] != original[1]:
            self.audit.append((step, "site_rank_changed", original[1], best[1], len(bombs) + len(claims)))
        return origin,baseline,floor,rows,best

    def observe_route(self, drone, step, ranges, semantic):
        if (self.used or drone.previous_inventory != 1 or drone.fast_closeout.phase(step) is not None
                or step%self.OBSERVE_INTERVAL != drone.identifier%self.OBSERVE_INTERVAL):
            return
        gate = self.gate(drone,step,ranges)
        if gate:
            self.audit.append((step,"survey_gate",gate))
            return
        self.backups = [row for row in self.backups if step-row[0] <= self.CACHE_STEPS]
        pose = tuple(map(float,drone.pose))
        sites = [("passed",pose,step)]
        sites.extend(("route",point,step) for point in self.route_sites(pose,drone.route))
        origin,_,floor,rows,_ = self.assess(drone,step,ranges,semantic,sites,early=True)
        self.audit.append((step,"survey",origin,floor,rows,len(self.backups)))

    def reserve(self, drone, step, ranges, semantic):
        if self.used or step < self.retry_at or drone.previous_inventory != 1:
            return False
        self.retry_at = step+10
        phase = drone.fast_closeout.phase(step) or "ordinary"
        gate = self.gate(drone,step,ranges)
        if gate:
            self.audit.append((step,"reserve_gate",phase,gate))
            return False
        origin = tuple(map(float,drone.pose))
        self.backups = [row for row in self.backups if step-row[0] <= self.CACHE_STEPS]
        sites = [("backup",point,stamp) for stamp,point,_ in self.backups
                 if math.dist(origin,point) <= self.REACH]
        direction = next((np.subtract(point,origin) for point in list(drone.route)[:4]
                          if math.dist(point,origin) >= 10.),None)
        if direction is not None:
            heading = math.atan2(direction[1],direction[0])
            for length in (18.,27.,self.REACH):
                for offset in (0.,.37,-.37,.74,-.74):
                    yaw = heading+offset
                    point = origin[0]+length*math.cos(yaw),origin[1]+length*math.sin(yaw)
                    sites.append(("current_probe",point,step))
        origin,current,floor,rows,best = self.assess(drone,step,ranges,semantic,sites,early=False)
        self.audit.append((step,"reserve_review",phase,origin,current,floor,rows,len(self.backups)))
        if best is None:
            return False
        self.used = True
        self.plan = step,best[1],current,best[0][0]
        self.audit.append((step,"reserve",best[1],current,best[0][0],origin,best[2],best[3]))
        return True

    @staticmethod
    def opportunity_floor(floor):
        return max(2.,2.*floor)

    def recent_at(self, point, step):
        return any(0 <= step-stamp <= self.OBSERVE_INTERVAL
                   and math.dist(point,site) <= self.ARRIVAL
                   for stamp,site,_ in self.backups)

    def on_route_opportunity(self, drone, step, ranges, semantic):
        if (self.plan is not None or drone.fast_closeout.phase(step) is not None
                or self.gate(drone,step,ranges) or not self.recent_at(drone.pose,step)):
            return False
        # Recheck the exact current position and speed. This budget-free
        # option changes a placement decision, never the flight waypoint.
        block=self._site_block(drone, drone.pose, step, semantic, stationary=True)
        if block:
            self.audit.append((step,"opportunity_block",block))
            return False
        if not drone.placement._first_drop_exit_clear(drone,ranges,semantic):
            self.audit.append((step,"opportunity_block","live_exit"))
            return False
        gain=drone.team_wall.query(drone,semantic,step)(drone.pose)[0]
        floor=self.opportunity_floor(drone.placement._coverage_minimum(step,drone.limit))
        if gain < floor:
            self.audit.append((step,"opportunity_block","coverage",gain,floor))
            return False
        return True


    def clear(self, step, reason):
        if self.plan is not None:
            self.audit.append((step,reason,self.plan[1]))
            self.plan = None

    def control(self, drone, step, command, ranges, semantic):
        if self.plan is None:
            return None
        start, target, baseline, _ = self.plan
        if not self.eligible(drone,step) or step-start >= self.MAX_STEPS:
            self.clear(step,"stock_confirmed" if drone.previous_inventory == 0 else "expired")
            return None
        if self._site_block(drone, target, step, semantic, stationary=False):
            self.clear(step,"target_blocked")
            return None
        odom = drone.odometer_values()
        if odom is None or not np.all(np.isfinite(odom)) or ranges is None:
            self.clear(step,"sensor_unavailable")
            return None
        distance = math.dist(target,drone.pose)
        if distance <= self.ARRIVAL:
            gain = drone.team_wall.query(drone,semantic,step)(drone.pose)[0]
            if (not self.worthwhile(gain,baseline)
                    or gain < drone.placement._coverage_minimum(step,drone.limit)
                    or self._site_block(drone, drone.pose, step, semantic, stationary=False)):
                self.clear(step,"arrival_rejected")
                return None
            command.update(drone.drive(drone.pose,self._velocity_from_odometry(drone,odom)))
            if self._site_block(drone, drone.pose, step, semantic, stationary=True):
                return "approach"
            if not self.audit or self.audit[-1][1] != "arrived":
                self.audit.append((step,"arrived",target,tuple(map(float,drone.pose)),gain))
            return "ready"
        if not drone.team_wall.corridor_clear(drone,target,ranges,drone.lidar_rays_angles(),semantic):
            self.clear(step,"live_corridor_rejected")
            return None
        command.update(drone.drive(target,self._velocity_from_odometry(drone,odom)))
        return "approach"

    @staticmethod
    def _velocity_from_odometry(drone, odom):
        travel,relative,change = map(float,odom)
        yaw = drone.heading-change+relative
        return travel*np.array((math.cos(yaw),math.sin(yaw)))

    @classmethod
    def wait_for_site(cls, state, elapsed):
        return state == "approach" and elapsed < cls.FAST_RETRY_AFTER

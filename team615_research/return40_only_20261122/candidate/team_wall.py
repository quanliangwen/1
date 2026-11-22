"""Bounded marginal wall placement options, with public team reservations."""
import math

import numpy as np
from swarm_rescue.simulation.drone.bomb_deployer import MIN_BOMB_SEPARATION


class TeamWall:
    RESERVATION_STEPS = 40.
    REUSE_STEPS = 95

    def __init__(self):
        self.reservation = None
        self.peer = {}
        self.peer_version = {}
        self.attempted = -1000
        self.audit = []
        self.greedy_first_target = None
        self.greedy_first_attempted = -1000

    def packet(self, step):
        if self.reservation is None:
            return step,None
        started,point,count=self.reservation
        return step,point if step-started<self.RESERVATION_STEPS else None

    def receive(self, drone, msg):
        sender=msg["id"]
        raw=msg.get("red_wall_reservation")
        if (type(sender) is not int or sender==drone.identifier or not 0<=sender<drone.team_size
                or not isinstance(raw,tuple) or len(raw)!=2 or type(raw[0]) is not int):
            return
        step,point=raw
        if not self.peer_version.get(sender,-1)<step<=drone.elapsed_timestep:
            return
        if point is not None and (not isinstance(point,tuple) or not drone._inside_team_point(point)):
            return
        self.peer_version[sender]=step
        if point is None:
            self.peer.pop(sender,None)
        else:
            self.peer[sender]=step,point

    def claims(self, drone, step):
        return [point for owner,(stamp,point) in self.peer.items()
                if 0<=step-stamp<=self.RESERVATION_STEPS
                and (owner not in drone.inventory_records or drone.inventory_records[owner][1]>0)]

    def query(self, drone, semantic, step):
        actual=drone._known_bomb_positions(semantic)
        virtual=self.claims(drone,step)
        def estimate(point):
            return drone.fine_wall_coverage.measure(drone.memory,point,actual+virtual,
                                                    drone.blast_radius,step=step)
        return estimate

    @staticmethod
    def best_candidate(position, candidates, estimate):
        rank = lambda point: (estimate(point)[0],-math.dist(position,point))
        return max(candidates,key=rank,default=None)

    @staticmethod
    def site_rank(point, gain, distance, occupied, radius):
        # Prefer a separate blast footprint when marginal gains are close.
        # Only confirmed blasts and live reservations received over radio count.
        diameter = 2. * radius
        nearest = min((math.dist(point, center) for center in occupied), default=diameter)
        separation = min(1., nearest / diameter)
        travel_cost = 1. + distance / (2. * diameter)
        return gain * (.65 + .35 * separation) / travel_cost, gain, -distance

    def select_site(self, step, origin, candidates, occupied, radius):
        if not candidates:
            return None

        def rank(candidate):
            point, gain = candidate
            return self.site_rank(point, gain, math.dist(origin, point), occupied, radius)

        selected = max(candidates, key=rank)
        gains = {point: (gain,) for point, gain in candidates}
        original = self.best_candidate(origin, gains, gains.__getitem__)
        if selected[0] != original:
            self.audit.append((step, "site_rank_changed", original, selected[0], len(occupied)))
        return selected

    @staticmethod
    def corridor_clear(drone, target, ranges, angles, semantic):
        if ranges is None:
            return False
        delta=np.subtract(target,drone.pose)
        length=float(np.linalg.norm(delta))
        if length<8.:
            return True
        direction=math.atan2(delta[1],delta[0])-drone.heading
        obstacles=[(h.distance*math.cos(h.angle),h.distance*math.sin(h.angle))
                   for h in semantic if h.entity_type.name in ("DRONE","BOMB","DISPOSAL_CENTER")]
        return drone.local_escape.clearance(direction,np.asarray(angles),np.asarray(ranges),length,obstacles)

    def propose(self, drone, command, step, ranges, angles, semantic, current, estimate, count):
        if (self.reservation is not None or step-self.attempted<self.REUSE_STEPS
                or not drone.grid.pose_fixed or not drone.route or drone.limit-step<90
                or drone.walltime_limit-drone.elapsed_walltime<5.):
            return False
        first=np.asarray(drone.route[0])-drone.pose
        direction=math.atan2(first[1],first[0])
        bombs=drone._known_bomb_positions(semantic)+self.claims(drone,step)
        candidates=[]
        for angle in (0.,.42,-.42,.84,-.84):
            absolute=direction+angle
            point=drone.pose+42.*np.array((math.cos(absolute),math.sin(absolute)))
            if (drone._inside_team_point(point) and all(math.dist(point,b)>=MIN_BOMB_SEPARATION for b in bombs)
                    and self.corridor_clear(drone,point,ranges,angles,semantic)):
                candidates.append(tuple(map(float,point)))
        minimum = max(current + .25, current * 1.25)
        eligible = [(point, gain) for point in candidates if (gain := estimate(point)[0]) >= minimum]
        selected = self.select_site(step, drone.pose, eligible, bombs, drone.blast_radius)
        if selected is None:
            return False
        point, gain = selected
        self.attempted=step
        self.greedy_first_target = None
        self.reservation=step,point,count
        self.audit.append((step,"reserve",point,current,gain,len(bombs)))
        return self.steer(drone,command,step,ranges,semantic)

    def propose_greedy_first(self, drone, command, step, ranges, angles, semantic,
                             floor, estimate, count):
        if (self.reservation is not None or step-self.greedy_first_attempted < self.REUSE_STEPS
                or not drone.grid.pose_fixed or drone._odometry_only or ranges is None
                or not drone.route or drone.limit-step < 120
                or drone.walltime_limit-drone.elapsed_walltime < 7.):
            return False
        # Probe at most once per reuse interval, including unsuccessful searches.
        self.greedy_first_attempted = step
        advance = np.asarray(drone.route[0])-drone.pose
        if float(np.linalg.norm(advance)) < 8.:
            return False
        direction = math.atan2(advance[1],advance[0])
        origin = drone.pose
        here = drone.grid.cell(origin)
        passages = drone.placement.deep.passages
        opening_limit = int(.15 * drone.limit)
        claims = self.claims(drone,step)
        occupied = drone._known_bomb_positions(semantic) + claims
        eligible = []
        for distance in (36.,72.):
            for offset in (0.,.42,-.42,.84,-.84):
                yaw = direction+offset
                point = tuple(origin+distance*np.array((math.cos(yaw),math.sin(yaw))))
                if (not drone._inside_team_point(point)
                        or passages.nearby(point,opening_limit)
                        or passages.near_recent_narrow(point,opening_limit)
                        or drone._placement_block(point,step,semantic,stationary=False)
                        or any(math.dist(point,claim)<MIN_BOMB_SEPARATION for claim in claims)):
                    continue
                route = np.linspace(origin,point,math.ceil(distance/5.)+1)
                if any(drone.grid.evidence[cell]>=0 or drone.grid.clearance[cell]<23.
                       for sample in route
                       if (cell:=drone.grid.cell(sample))!=here):
                    continue
                if not self.corridor_clear(drone,point,ranges,angles,semantic):
                    continue
                gain = estimate(point)[0]
                if gain < max(floor+.5,1.5*floor):
                    continue
                eligible.append((point, gain))
        selected = self.select_site(step, origin, eligible, occupied, drone.blast_radius)
        if selected is None:
            return False
        point, gain = selected
        self.attempted = step
        self.reservation = step,point,count
        self.greedy_first_target = point
        self.audit.append((step,"greedy_first_reserve",point,floor,gain,math.dist(origin,point)))
        return self.steer(drone,command,step,ranges,semantic)

    def steer(self, drone, command, step, ranges, semantic):
        if self.reservation is None:
            return False
        start,point,count=self.reservation
        if (step-start>=self.RESERVATION_STEPS or not drone.grid.pose_fixed
                or drone.previous_inventory!=count or drone.limit-step<35):
            self.reservation=None
            return False
        if math.dist(point,drone.pose)<=10.:
            if (point == self.greedy_first_target
                    and not drone.placement._first_drop_exit_clear(drone,ranges,semantic)):
                self.reservation = None
                self.greedy_first_target = None
                self.audit.append((step,"greedy_first_cancelled","no_live_exit",point))
                return True
            # Keep the public reservation until the actual SDK receipt.
            return False
        if not self.corridor_clear(drone,point,ranges,drone.lidar_rays_angles(),semantic):
            self.reservation=None
            return False
        odom=drone.odometer_values()
        if odom is None or not np.all(np.isfinite(odom)):
            self.reservation=None
            return False
        yaw=drone.heading-float(odom[2])+float(odom[1])
        speed=float(odom[0])*np.array((math.cos(yaw),math.sin(yaw)))
        command.update(drone.drive(point,speed))
        return True

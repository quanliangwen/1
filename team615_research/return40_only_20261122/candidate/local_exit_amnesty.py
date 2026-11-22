"""Sensor-only placement exceptions for a terminal slot and a side alcove."""
from collections import Counter
from dataclasses import dataclass
import math

import numpy as np

from swarm_rescue.solutions.passage_ledger import PassageLedger
from swarm_rescue.solutions.scan_geometry import project, scan_lines


CLEARANCE = 23.
BOMB_RADIUS = 12.
PARTS = frozenset(("DRONE", "BOMB", "DISPOSAL_CENTER"))


def unit(vector):
    return vector / np.linalg.norm(vector)


def see(points, angles, ranges, margin=8.):
    """Both bracketing rays must see past each space to be certified."""
    bearings = np.arctan2(points[:, 1], points[:, 0])
    edge = np.clip(np.searchsorted(angles, bearings), 1, len(angles)-1)
    distance = np.linalg.norm(points, axis=1)
    left, right = ranges[edge-1], ranges[edge]
    return bool(np.all(np.isfinite(left) & np.isfinite(right)
                       & (np.minimum(left, right) > distance + margin)))


def static_lines(angles, ranges, semantic):
    objects = [h.distance*np.array((math.cos(h.angle), math.sin(h.angle)))
               for h in semantic if h.entity_type.name in PARTS
               and math.isfinite(h.distance) and math.isfinite(h.angle)]
    # Local overlapping windows prevent a long U shape from consuming
    # two corners in a single global line fit.
    raw = []
    for start in range(0, len(angles)-5, 18):
        stop=start+30
        raw.extend(scan_lines(ranges[start:stop],angles[start:stop],objects,218.))
    merged=[]
    for line in raw:
        direction=unit(line[1]-line[0])
        for index,other in enumerate(merged):
            axis=unit(other[1]-other[0])
            normal=np.array((-axis[1],axis[0]))
            if (abs(np.dot(axis,direction))<.96
                    or abs((line.mean(axis=0)-other.mean(axis=0)) @ normal)>7.):
                continue
            interval=(line-other[0]) @ axis
            if min(interval)>np.linalg.norm(other[1]-other[0])+18. or max(interval)<-18.:
                continue
            start=min(0.,min(interval))
            end=max(np.linalg.norm(other[1]-other[0]),max(interval))
            merged[index]=other[0]+np.array((start,end))[:,None]*axis
            break
        else:
            merged.append(line)
    return np.asarray(merged[:14]).reshape(-1,2,2)


def terminal_slot(lines, angles, ranges):
    """The two long banks and the end wall must belong to a visible U."""
    for i, a in enumerate(lines):
        axis = unit(a[1]-a[0])
        normal = np.array((-axis[1], axis[0]))
        a_side = float(a.mean(axis=0) @ normal)
        for b in lines[i+1:]:
            if abs(float(unit(b[1]-b[0]) @ axis)) < .92:
                continue
            b_side = float(b.mean(axis=0) @ normal)
            low, high = sorted((a_side,b_side))
            if not (low < -18. and high > 18. and 51. <= high-low <= 132.):
                continue
            for inward in (axis, -axis):
                aa, bb = a[a @ inward < (a @ inward).mean()][0], b[b @ inward < (b @ inward).mean()][0]
                gate = (aa+bb)/2
                near, far = float(gate @ inward), min(np.max(a @ inward), np.max(b @ inward))
                if not -145. <= near <= -20. or abs((aa-bb) @ inward)>27. or far-near<82.:
                    continue
                for end in lines:
                    q = end @ normal
                    depth = end @ inward
                    if (abs(float(unit(end[1]-end[0]) @ inward)) > .28
                            or abs(float(depth.mean())-far)>28.
                            or min(q)>low+25. or max(q)<high-25.
                            or np.linalg.norm(end[1]-end[0]) < .55*(high-low)):
                        continue
                    probe = np.array([gate - inward * d + normal * t for d in (8.,24.) for t in (0.,11.,-11.)])
                    if see(probe,angles,ranges):
                        return gate, -inward, np.array((aa,bb))
    return None


def side_alcove(lines, angles, ranges):
    """Certify a visible side opening bounded by a back wall and a through lane."""
    for i, left in enumerate(lines):
        axis = unit(left[1]-left[0])
        normal = np.array((-axis[1],axis[0]))
        if (left.mean(axis=0) @ normal) < 0.:
            normal = -normal
        near = float(left.mean(axis=0) @ normal)
        if not (20. <= near <= 115.):
            continue
        for right in lines[i+1:]:
            if (abs(float(unit(right[1]-right[0]) @ axis)) < .93
                    or abs(float(right.mean(axis=0) @ normal)-near)>9.):
                continue
            l, r = sorted((np.sort(left @ axis),np.sort(right @ axis)),key=lambda x:x[0])
            if not (l[1] < -8. and r[0] > 8. and 53. <= r[0]-l[1] <= 155.):
                continue
            # Certified path from one end of the opening to the other at
            # a 23px margin from both banks. Robot is behind the nearer bank.
            for bank in lines:
                side = float(bank.mean(axis=0) @ normal)
                if (abs(float(unit(bank[1]-bank[0]) @ axis)) < .93
                        or not 60. <= side-near <= 125.):
                    continue
                interval = bank @ axis
                if min(interval)>l[1]+12. or max(interval)<r[0]-12.:
                    continue
                for wall in lines:
                    if (abs(float(unit(wall[1]-wall[0]) @ axis)) < .9
                            or not -80. <= float(wall.mean(axis=0) @ normal) <= -29.
                            or not min(wall @ axis)<0.<max(wall @ axis)):
                        continue
                    lane=(near+side)/2
                    if lane<CLEARANCE+BOMB_RADIUS+9.:
                        continue
                    points=np.array([axis*x+normal*(lane+n)
                                     for x in np.linspace(l[1],r[0],5)
                                     for n in (-CLEARANCE,0.,CLEARANCE)])
                    if see(points,angles,ranges,4.):
                        return normal * near, axis, lane
    return None


@dataclass
class Transit:
    stamp: int
    gate: np.ndarray
    outward: np.ndarray
    tips: np.ndarray
    points: tuple
    votes: int = 1
    inside: bool = False
    exit_step: int | None = None
    match_step: int = -1000


class LocalExit:
    MAX_TRANSIT = 190
    MATCH_RADIUS = 70.
    ACK_AGE = 64

    def __init__(self):
        self.review = Counter()
        self.position = np.zeros(2)
        self.heading = 0.
        self.clock = -1
        self.transit = None
        self.history = ()
        self.rx = {}
        self.asked = {}
        self.confirmed_sites = {}
        self.pending = None

    @staticmethod
    def same(point, direction, packet):
        return (math.dist(point,packet[1:3])<=LocalExit.MATCH_RADIUS
                and float(np.dot(direction,packet[3:5]))>=.72)

    def moved(self, step, odometry):
        if (self.clock != step-1 or odometry is None or not np.all(np.isfinite(odometry))
                or not 0. <= odometry[0] <= 12. or abs(odometry[2])>.50):
            self.transit=None
            self.position[:]=0.
            self.heading=0.
            self.clock=step
            return False
        travel, sideways, turn = map(float,odometry)
        self.position += travel*np.array((math.cos(self.heading+sideways),
                                         math.sin(self.heading+sideways)))
        self.heading=(self.heading+turn+math.pi)%(2*math.pi)-math.pi
        self.clock=step
        return True

    def body_to_local(self, points):
        return project(points,self.position,self.heading)

    def world_gate(self, drone, record):
        offset=record.gate-self.position
        turn=drone.heading-self.heading
        gate=project(offset,drone.pose,turn)
        direction=project(record.outward,np.zeros(2),turn)
        return tuple(map(float,gate)),tuple(map(float,direction))

    def observe(self, drone, step, ranges, semantic, audit):
        if not self.moved(step,drone.odometer_values()) or ranges is None:
            return
        record=self.transit
        if record is not None and (step-record.stamp>self.MAX_TRANSIT
                                   or math.dist(self.position,record.gate)>225.):
            self.transit=record=None
        if step%8!=int(drone.identifier)%8:
            return
        angles=np.asarray(drone.lidar_rays_angles())
        ranges=np.asarray(ranges)
        lines=static_lines(angles,ranges,semantic)
        seen=terminal_slot(lines,angles,ranges)
        self.review["scan_checks"]+=1
        if seen is not None:
            gate, direction, tips=seen
            gate,tips=self.body_to_local(gate),self.body_to_local(tips)
            direction=project(direction,np.zeros(2),self.heading)
            if record is None:
                self.transit=Transit(step,gate,direction,tips,tuple(self.position))
                self.review["slot_first_sighting"]+=1
                return
            if (record.exit_step is None and math.dist(gate,record.gate)<=18.
                    and np.dot(record.outward,direction)>=.92):
                if record.votes==1 and math.dist(self.position,record.points)>=9.:
                    record.votes=2
                    record.inside=True
                    self.review["slot_confirmed_inside"]+=1
                    audit.append((step,"local_slot_inside",self.world_gate(drone,record)[0]))
                record.match_step=step
        if record is None or not record.inside:
            return
        depth=float(np.dot(self.position-record.gate,record.outward))
        if depth < -14.:
            record.exit_step=None
            return
        # Reobserve both old tips in the current scan. The odometer must
        # agree with the renewed scan at the exit, including across a GNSS outage.
        ends=self.body_to_local(lines).reshape(-1,2)
        if len(ends)<2:
            return
        dist=np.linalg.norm(ends[:,None,:]-record.tips,axis=2)
        nearest=np.argmin(dist,axis=0)
        if nearest[0]==nearest[1] or np.max(np.min(dist,axis=0))>14.:
            return
        record.match_step=step
        if record.exit_step is None and depth>=28.:
            record.exit_step=step
            gate,axis=self.world_gate(drone,record)
            self.history=(self.history+((step,*gate,*axis),))[-6:]
            self.review["slot_exit_matched"]+=1
            audit.append((step,"local_slot_exited",gate,depth))

    def packet(self, drone, step):
        r=self.transit
        query=None
        if r is not None and r.inside:
            point,axis=self.world_gate(drone,r)
            query=(r.stamp,*point,*axis,r.exit_step or 0)
        # A reply describes an agreed current slot, actual matched exit records,
        # and the replyer's current intention. No reply means no authorization.
        answers=[]
        for owner,(received,message) in tuple(self.asked.items()):
            if step-received>self.ACK_AGE:
                self.asked.pop(owner,None)
                continue
            token,*data=message
            point,axis=tuple(data[:2]),tuple(data[2:4])
            own_exit=max((v[0] for v in self.history if self.same(point,axis,v)),default=0)
            if query is not None and self.same(point,axis,query) and not query[-1]:
                continue
            if self.outside_plan(drone,point,axis):
                answers.append((owner,token,step,own_exit))
        return query,tuple(answers),tuple(self.confirmed_sites.values())

    @staticmethod
    def outside_plan(drone, point, axis):
        if drone.pose is None:
            return False
        if (not drone.grid.pose_fixed
                and (math.dist(drone.pose,point)<220. or drone.elapsed_timestep-drone.grid.last_pose_fix>120)):
            # A global plan after prolonged odometry cannot certify absence.
            return False
        points=[drone.pose,*drone.route]
        if drone.goal is not None:
            points.append(drone.goal)
        if any(PassageLedger._segment_distance(point,start,end)<115.
               for start,end in zip(points,points[1:])):
            return False
        return math.dist(drone.pose,point)>=115.

    def receive(self, drone, msg):
        wire=msg.get("red_local_exit")
        owner=msg["id"]
        if wire is None or type(owner) is not int or not 0<=owner<drone.team_size or owner==drone.identifier:
            return
        query,answers,used=wire
        step=int(drone.elapsed_timestep)
        if (isinstance(query,tuple) and len(query)==6 and type(query[0]) is int
                and 0<=step-query[0]<=self.MAX_TRANSIT and drone._inside_team_point(query[1:3])
                and .95<=math.hypot(*query[3:5])<=1.05):
            self.asked[owner]=step,query
        else:
            self.asked.pop(owner,None)
        self.rx.pop(owner,None)
        for target,token,tick,other_exit in answers:
            if (target==drone.identifier and 0<=step-tick<=self.ACK_AGE and 0<=other_exit<=tick
                    and self.transit is not None and token==self.transit.stamp):
                self.rx[owner]=(token,tick,other_exit)
        for k,xy in used:
            if (isinstance(k,tuple) and len(k)==2 and 0<=k[0]<drone.team_size
                    and 1<=k[1]<=drone.initial_inventory and drone._inside_team_point(xy)):
                self.confirmed_sites.setdefault(k,(k,xy))

    def candidate(self, drone, step, ranges, angles, semantic):
        if (ranges is None or not drone.route or step >= drone.limit-20
                or drone.walltime_limit-drone.elapsed_walltime<3. or self.pending is not None):
            return None
        valid=ranges[np.isfinite(ranges)&(ranges>0.)]
        if (len(valid)<.90*len(ranges) or np.min(valid)<CLEARANCE+6.
                or any(h.entity_type.name=="DRONE" and h.distance<85. for h in semantic)):
            self.review["live_clearance_or_traffic"]+=1
            return None
        record=self.transit
        if record is not None and record.exit_step is not None:
            depth=float(np.dot(self.position-record.gate,record.outward))
            offset=self.position-record.gate
            lateral=abs(offset[0]*record.outward[1]-offset[1]*record.outward[0])
            if 57.<=depth<=105. and lateral<=65. and step-record.match_step<=16:
                if any(not self.peer_clear(owner,record,step) for owner in range(drone.team_size)
                       if owner!=drone.identifier):
                    self.review["exit_waiting_for_peers"]+=1
                    return None
                gate,direction=self.world_gate(drone,record)
                if self.site_free(drone,gate):
                    delta=np.asarray(drone.route[0])-drone.pose
                    if np.dot(delta,direction)>8.:
                        return "local_slot_exit",gate
                return None
        spot=side_alcove(static_lines(angles,ranges,semantic),angles,ranges)
        self.review["side_geometry_checked"]+=1
        if spot is None:
            return None
        mouth,axis,lane=spot
        gate=tuple(map(float,project(mouth,drone.pose,drone.heading)))
        # Recheck that the original route can leave the alcove. The live range
        # query in the placement policy then checks the 23px departure tube.
        displacement=np.asarray(drone.route[0])-drone.pose
        c,s=math.cos(drone.heading),math.sin(drone.heading)
        body=displacement @ np.array(((c,-s),(s,c)))
        if np.dot(body,unit(mouth)) <= 8.:
            return None
        # A reserved branch from another actual message is off limits.
        if not self.site_free(drone,gate) or any(math.dist(q[1:3],gate)<90. for _,q in self.asked.values()):
            return None
        self.review["side_geometry_pass"]+=1
        return "side_alcove",gate

    def peer_clear(self, owner, record, step):
        token,tick,exited=self.rx.get(owner,(-1,-1000,0))
        # Two exits in the same tick are ambiguous; neither takes precedence.
        return (token==record.stamp and record.exit_step<=tick<=step
                and step-tick<=self.ACK_AGE and exited<record.exit_step)

    def site_free(self, drone, point):
        return all(math.dist(point,xy)>100. for _,xy in self.confirmed_sites.values())

    def finish(self, drone, accepted, left):
        if self.pending is None:
            return
        if accepted:
            key=(int(drone.identifier),int(drone.initial_inventory-left))
            self.confirmed_sites[key]=(key,self.pending)
        self.pending=None

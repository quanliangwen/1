"""Onboard contact history and an acknowledged common return region."""
import math
import numpy as np


def inside(drone, point):
    try:
        return len(point) == 2 and all(math.isfinite(float(x)) and abs(float(x)) < n/2
                                       for x, n in zip(point, drone.size_area))
    except (TypeError, ValueError):
        return False


def known_segment(drone, a, b):
    grid = drone.grid
    for p in np.linspace(a, b, max(2, 1+math.ceil(math.dist(a, b)/4))):
        c = grid.cell(p)
        if grid.evidence[c] >= 0 or (grid.clearance[c] < 23 and not
                (grid.tight[c] and grid.clearance[c] >= grid.HULL_CLEARANCE)):
            return False
    return True


class ExchangePlan:
    STABLE = 40

    def __init__(self, owner, team_size, limit):
        self.owner, self.team_size, self.limit = int(owner), team_size, limit
        self.epoch = ('group-return-v1', int(limit), int(team_size))
        self.root = None
        self.acks = set()
        self.launch = None
        self.trail = []
        self.trail_cells = {}
        self.edges = {}
        self.direct = {}
        self.branch_group = (self.owner,)
        self.local_region = None
        self.pending_group = None
        self.pending_since = None
        self.audit = []
        self.last_observed = -1
        self.root_tail = None

    def remember(self, drone):
        p = tuple(map(float, drone.pose))
        if self.trail and math.dist(p, self.trail[-1]) < 12:
            return
        key = tuple(round(x/8) for x in p)
        candidates = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                i = self.trail_cells.get((key[0]+dx, key[1]+dy))
                if i is not None and math.dist(p, self.trail[i]) <= 8 and known_segment(drone, p, self.trail[i]):
                    candidates.append(i)
        if candidates:
            self.trail = self.trail[:min(candidates)+1]
            self.trail_cells = {tuple(round(x/8) for x in q): i for i,q in enumerate(self.trail)}
        self.trail.append(p)
        self.trail_cells[key] = len(self.trail)-1

    def gate_index(self, point, radius=155):
        near = [i for i,p in enumerate(self.trail) if math.dist(p, point) <= radius]
        return min(near, key=lambda i: math.dist(self.trail[i], point)) if near else None

    def reachable_root(self):
        return self.root is not None and self.gate_index(self.root[1:]) is not None

    def committed(self):
        return self.root is not None and len(self.acks) == self.team_size and self.owner in self.acks

    def observe(self, drone, step, record_trail=True):
        if drone.pose is None or not inside(drone, drone.pose) or step == self.last_observed:
            return
        self.last_observed = step
        if self.launch is None:
            self.launch = tuple(map(float, drone.pose))
        if record_trail:
            self.remember(drone)
        # A small early metadata proposal, never a fixed collector/submitting role.
        if (self.owner == 0 and self.root is None and 30 <= step < self.limit*3//5
                and math.dist(self.launch, drone.pose) >= 80
                and drone.grid.pose_fixed and not drone._odometry_only
                and not drone.communicator_is_disabled()):
            c = drone.grid.cell(drone.pose)
            if drone.grid.evidence[c] < 0 and drone.grid.clearance[c] >= 23:
                self.root = (int(step), *map(float, drone.pose))
                self.audit.append((step, 'root_proposed', self.root))
        if self.owner not in self.acks and self.reachable_root():
            gate=self.trail[self.gate_index(self.root[1:])]
            root=self.root[1:]
            # A shared parent area must support mutual radio contact even when
            # drone 0 is not its courier. Aim within 80px, not opposite 155px edges.
            if math.dist(gate,root)<=80:
                tail=[]
            elif known_segment(drone,gate,root):
                tail=[tuple(root)]
            else:
                tail=list(drone.grid.route(gate,root))
                if not tail or math.dist(tail[-1],root)>80:tail=None
            if tail is not None:
                self.root_tail=list(map(tuple,tail));self.acks.add(self.owner)
                self.audit.append((step, 'root_accepted', self.root))
        # Remember the last stable connected branch while still exploring.
        if step < min(1600, self.limit*3//10):
            group = {self.owner}
            changed = True
            while changed:
                changed = False
                for (a,b), event in self.edges.items():
                    if 0 <= step-event[0] <= self.STABLE and (a in group or b in group):
                        before = len(group); group.update((a,b)); changed |= len(group) != before
            group = tuple(sorted(group))
            if group != self.pending_group:
                self.pending_group, self.pending_since = group, step
            if (1 < len(group) < self.team_size and step-self.pending_since >= self.STABLE):
                events = [(v[0],k,v[1]) for k,v in self.edges.items()
                          if set(k).issubset(group) and v[1] is not None]
                if events:
                    event = max(events)
                    region = event[2]
                    if group != self.branch_group or region != self.local_region:
                        self.branch_group, self.local_region = group, region
                        self.audit.append((step, 'local_branch', group, region))

    def receive(self, drone, message, body, step):
        peer = message.get('id')
        if type(peer) is not int or peer == self.owner or not 0 <= peer < self.team_size:
            return
        state = next((s for s in message.get('states', ()) if s.get('id') == peer), {})
        stamp = body.get('step', state.get('step'))
        if not isinstance(stamp, (int, np.integer)) or not 0 <= step-int(stamp) <= 12:
            return
        point = body.get('point', state.get('point'))
        if not inside(drone, point):
            return
        fixed = bool(body.get('fixed', False))
        self.direct[peer] = (step, tuple(map(float, point)))
        pair = tuple(sorted((self.owner, peer)))
        own_fixed = drone.grid.pose_fixed and not drone._odometry_only
        if self.owner < peer and own_fixed and drone.pose is not None:
            region = tuple(map(float, drone.pose))
        elif peer < self.owner and fixed:
            region = tuple(map(float, point))
        else:
            region = None
        self.edges[pair] = (int(stamp), region)
        if not body or tuple(body.get('epoch', ())) != self.epoch:
            return
        root = body.get('root')
        if (self.root is None and isinstance(root, (tuple,list)) and len(root) == 3
                and type(root[0]) is int and 0 <= root[0] <= step and inside(drone,root[1:])):
            self.root = tuple(root)
            self.audit.append((step, 'root_received', peer, self.root))
        if root is not None and self.root == tuple(root):
            for owner in body.get('acks', ()):
                if type(owner) is int and 0 <= owner < self.team_size:
                    self.acks.add(owner)
        for key, event in body.get('edges', {}).items():
            if (not isinstance(key,tuple) or len(key) != 2 or not all(type(i) is int and
                    0 <= i < self.team_size for i in key) or key[0] >= key[1]):
                continue
            if not isinstance(event,(tuple,list)) or len(event) != 2:
                continue
            ts, p = event
            if type(ts) is not int or not 0 <= ts <= step or (p is not None and not inside(drone,p)):
                continue
            if ts > self.edges.get(key,(-1,None))[0]:
                self.edges[key] = (ts, None if p is None else tuple(p))

    def message(self, drone):
        return dict(epoch=self.epoch,root=self.root,acks=tuple(sorted(self.acks)),
                    edges=dict(self.edges),step=int(drone.elapsed_timestep),
                    point=None if drone.pose is None else tuple(map(float,drone.pose)),
                    fixed=bool(drone.grid.pose_fixed and not drone._odometry_only))

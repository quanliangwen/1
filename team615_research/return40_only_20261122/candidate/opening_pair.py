"""Locate an opening gap from opposing wall tips and use the verified last passer."""
from collections import deque
import math

import numpy as np


class OpeningPair:
    def __init__(self):
        self.samples = deque(maxlen=45)
        self.targets = ()
        self.tried = False
        self.until = None
        self.last_request = None
        self.route = ()
        self.route_ordinal = None

    @staticmethod
    def between(position, lines):
        for i, first in enumerate(lines):
            for second in lines[i+1:]:
                for a, b in (first, first[::-1]):
                    for c, d in (second, second[::-1]):
                        u, v = b-a, d-c
                        lu, lv = np.linalg.norm(u), np.linalg.norm(v)
                        if min(lu,lv) < 22. or float(u @ v)/(lu*lv) > -.86:
                            continue
                        axis = c-a
                        width = float(np.linalg.norm(axis))
                        if not 55. <= width <= 155. or abs(float(axis @ u)/(width*lu)) > .72:
                            continue
                        delta = position-a
                        # An opening lies past both tips, away from each wall's continuation.
                        if float(delta @ u)/lu > 8. or float((position-c) @ v)/lv > 8.:
                            continue
                        along = float(delta @ axis) / (width*width)
                        across = abs(delta[0]*axis[1]-delta[1]*axis[0])/width
                        if .16 <= along <= .84 and across <= 37. and min(np.linalg.norm(position-a),np.linalg.norm(position-c)) >= 25.:
                            return True
        return False

    def record(self, drone, step, lines, audit):
        if step % 4 != drone.identifier % 4 or not self.between(np.zeros(2), lines):
            return
        point = tuple(map(float,drone.pose))
        if not self.samples or math.dist(point,self.samples[-1][1]) >= 8.:
            self.samples.append((step,point))
            if len(self.samples)<=3:
                audit.append((step, "gap_samples", point))

    def choose(self, drone, step, until, audit):
        options = [p for tick,p in reversed(self.samples) if step-tick <= 135 and math.dist(p,drone.pose)<=125.]
        for first in options:
            second = next((p for p in options if 28. <= math.dist(first,p) <= 60.),None)
            if second is None:
                continue
            self.targets = (first,second)
            self.until = until
            audit.append((step,"gap_pair_started",first,second))
            self.tried = True
            return True
        return False

    def move(self, drone, command, step, ranges, semantic, policy):
        count = drone.carried_bombs_count()
        ordinal = drone.initial_inventory-count
        if not self.targets or ordinal >= len(self.targets):
            self.targets = ()
            return
        if step>=self.until:
            policy.audit.append((step,"gap_pair_aborted","budget"))
            self.targets = ()
            return
        target = self.targets[ordinal]
        if math.dist(drone.pose,target) <= 9.:
            cell = drone.grid.cell(drone.pose)
            safe = drone.grid.evidence[cell] < 0 and drone.grid.clearance[cell] >= 23.
            if safe and self.last_request != step and policy.request is None and step >= policy.next_request:
                if policy._spaced_from_bombs(drone,semantic,ordinal==1) and policy._patch_open(drone,semantic,step):
                    policy.place(drone,command,step,"gap_pair_first" if ordinal==0 else "gap_pair_second",count)
                    self.last_request=step
            return
        route = drone.search_route(target) if step % 6 == drone.identifier % 6 or not self.route else self.route
        self.route = route
        if ordinal != self.route_ordinal:
            self.route_ordinal = ordinal
            route = self.route = drone.search_route(target)
        hits=drone._tail_live_hits()
        if hits is None or not drone._local_check_route(target,route,hits):
            policy.audit.append((step,"gap_pair_aborted","safe_route"))
            self.targets=()
            return
        point=drone._tail_prefix(route)
        vx=drone.odometer_values()
        if vx is None or not np.all(np.isfinite(vx)):
            self.targets=()
            return
        yaw=drone.heading-float(vx[2])+float(vx[1])
        velocity=float(vx[0])*np.array((math.cos(yaw),math.sin(yaw)))
        command.update(drone.drive(point,velocity))

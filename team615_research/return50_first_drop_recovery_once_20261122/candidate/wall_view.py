"""Observation fallback for a search goal cut off by a confirmed obstacle."""
import math

import numpy as np

from swarm_rescue.solutions.two_stage_exploration import SearchTask


def wall_frontier(grid, point, close):
    """Count unresolved wall edges visible across surveyed free space."""
    row, col = grid.cell(point)
    count = 0
    cells = set()
    rows, cols = grid.evidence.shape
    for r in range(max(1, row-4), min(rows-1, row+5)):
        for c in range(max(1, col-4), min(cols-1, col+5)):
            cell = (r,c)
            evidence = grid.evidence[cell]
            if evidence >= 3 or grid.searched[cell] > int(close[cell]):
                continue
            end = grid.point(cell)
            distance = math.dist(point,end)
            if distance < grid.CELL or distance > 90.:
                continue
            line = np.linspace(point,end,math.ceil(distance/8)+1)
            if any(grid.evidence[inner] >= 0 for q in line[:-1]
                   if (inner := grid.cell(q)) != cell):
                continue
            cells.add(cell)
            if 0 < evidence < 3 or any(grid.evidence[n]>=3 for n in
                                        ((r+1,c),(r-1,c),(r,c+1),(r,c-1))):
                count += 1
    return count, cells


def route_is_clear(grid, pose, route, center, outside):
    here = grid.cell(pose)
    for start, end in zip([pose,*route],route):
        if not outside(start,end,center):
            return False
        points = np.linspace(start,end,math.ceil(math.dist(start,end)/5)+1)
        if any(grid.evidence[c]>=0 or grid.clearance[c]<23. for q in points
               if (c := grid.cell(q)) != here):
            return False
    return True


class WallView:
    def __init__(self):
        self.task = None
        self.center = None
        self.failures = 0
        self.last_failure = -1
        self.until = 0
        self.cooldown = 0
        self.observed = None

    def active(self, drone, task):
        return self.task is task and drone.elapsed_timestep < self.until

    def guarded_route(self, drone, route, outside):
        step = int(drone.elapsed_timestep)
        point = self.observed if step >= .34*drone.limit else None
        if point is None and step >= self.cooldown or not route:
            return route
        center = point if point is not None else self.center
        return route if all(outside(a,b,center)
                            for a,b in zip([drone.pose,*route],route)) else ()

    def try_view(self, blocker, drone, waypoint, avoid, angles, ranges, objects):
        step = int(drone.elapsed_timestep)
        center = avoid[0][0]
        if (center != self.center or step-self.last_failure>160) and step >= self.cooldown:
            self.center, self.failures = center, 0
        if center != self.center:
            return waypoint
        self.last_failure = step
        self.failures += 1
        if self.failures < 3 or step < self.cooldown or drone.search_task is None:
            return waypoint
        grid = drone.grid
        current, target = grid.cell(drone.pose), grid.cell(drone.goal)
        costs, _ = grid.tree(drone.pose,avoid=avoid)
        if target in costs:
            blocker.audit.append((step,"view_original_connected",center,tuple(waypoint)))
            return waypoint
        if len(costs)==1:
            blocker.audit.append((step,"view_isolated_start",center,tuple(waypoint)))
            return waypoint
        close = grid.close_scan_cells()
        nearby = []
        for cell,cost in costs.items():
            if not 28. <= cost <= 220. or grid.clearance[cell] < 23. or grid.evidence[cell] >= 0:
                continue
            point = tuple(grid.point(cell))
            if math.dist(point,center)>=50. and not drone.reached_search_point(point):
                nearby.append((float(cost),point))
        ranked = []
        for cost,point in sorted(nearby)[:24]:
            novelty, cells = wall_frontier(grid,point,close)
            if novelty and len(cells)>=2:
                ranked.append((-novelty/(100.+cost),cost,point,novelty))
        for _, _, point, novelty in sorted(ranked)[:8]:
            route = list(grid.route(drone.pose,point,avoid=avoid))
            if route and grid.cell(route[0])==current:
                route.pop(0)
            if not route or not drone.search_roaming.allows(drone.pose,point,route):
                continue
            if not route_is_clear(grid,drone.pose,route,center,blocker.outside):
                continue
            first = np.asarray(route[0])-drone.pose
            length = float(np.linalg.norm(first))
            if not 8. <= length <= 40.:
                continue
            direction = math.atan2(first[1],first[0])-drone.heading
            if not drone.local_escape.clearance(direction,angles,ranges,length,objects):
                continue
            cell = grid.cell(point)
            task = SearchTask(frozenset((cell,)),point,step,drone.search_steps)
            drone.search_task = self.task = task
            drone.goal,drone.route = point,route
            blocker.avoid,blocker.first,blocker.until = center,tuple(route[0]),step+blocker.KEEP
            drone.recovery_until = step
            drone.progress_pose,drone.progress_step = tuple(drone.pose),step
            self.until,self.cooldown = step+160,step+blocker.KEEP
            self.failures = 0
            blocker.audit.append((step,"view_selected",center,tuple(waypoint),point,novelty,route[:5]))
            return route[0]
        blocker.audit.append((step,"view_no_safe_novelty",center,tuple(waypoint),len(nearby),len(ranked)))
        return waypoint

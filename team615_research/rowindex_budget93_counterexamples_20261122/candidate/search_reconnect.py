"""Resume actual radio contact after a blocked search was successfully diverted."""

from collections import deque
import math

import numpy as np

from swarm_rescue.solutions.two_stage_exploration import SearchTask
from swarm_rescue.solutions.wall_view import route_is_clear


class SearchReconnect:
    def __init__(self):
        self.contacts = deque(maxlen=48)
        self.last_contact = -1
        self.contact_step = -1
        self.task = None
        self.next_attempt = 0
        self.until = 0

    def record_contact(self, drone):
        step = int(drone.elapsed_timestep)
        self.last_contact = step
        if drone.pose is None or not drone.grid.pose_fixed or self.contact_step == step:
            return
        self.contact_step = step
        point = tuple(map(float, drone.pose))
        if all(math.dist(point, old) >= 25. for old in self.contacts):
            self.contacts.append(point)

    def waypoint(self, drone, blocker, original):
        step = int(drone.elapsed_timestep)
        view = blocker.view
        if (not view.observed or step < .34*drone.limit or step >= drone.limit-200
                or step < self.next_attempt or step-self.last_contact < 150
                or self.task is drone.search_task and self.task is not None
                or not drone.grid.pose_fixed or not drone.communicator_is_disabled()
                or drone.previous_inventory != 0 or drone.pending_drop is not None
                or view.task is drone.search_task and view.task is not None
                or drone.gap_probe is not None or drone.local_escape.active is not None
                or drone.mode not in ("search", "explore")
                or drone.walltime_limit-drone.elapsed_walltime < 12.):
            return original
        self.next_attempt = step+75
        grid = drone.grid
        center = view.observed
        avoid = ((center,blocker.RADIUS),)
        if drone.search_roaming.departed:
            avoid += ((drone.search_roaming.origin,drone.search_roaming.radius),)
        costs, _ = grid.tree(drone.pose,avoid=avoid)
        start = grid.cell(drone.pose)
        choices = []
        for old in self.contacts:
            cell = grid.cell(old)
            if cell in costs and 30. <= costs[cell] <= 750. and math.dist(old,center) >= 65.:
                choices.append((costs[cell], tuple(grid.point(cell))))
        ranges = drone.lidar_values()
        if ranges is None:
            return original
        ranges = np.asarray(ranges,dtype=float)
        angles = np.asarray(drone.lidar_rays_angles())
        objects,_ = blocker.hits(drone,ranges,angles)
        for cost,point in sorted(set(choices))[:8]:
            route = list(grid.route(drone.pose,point,avoid=avoid))
            if route and grid.cell(route[0]) == start:
                route.pop(0)
            if not route or not drone.search_roaming.allows(drone.pose,point,route):
                continue
            if not route_is_clear(grid,drone.pose,route,center,blocker.outside):
                continue
            delta = np.asarray(route[0])-drone.pose
            length = float(np.linalg.norm(delta))
            if not 8. <= length <= 40.:
                continue
            direction = math.atan2(delta[1],delta[0])-drone.heading
            if not drone.local_escape.clearance(direction,angles,ranges,length,objects):
                continue
            self.until = step+min(480,math.ceil(2.*cost+90))
            task = SearchTask(frozenset((grid.cell(point),)),point,step,drone.search_steps)
            drone.search_task = self.task = task
            drone.goal,drone.route = point,route
            drone.recovery_until = step
            drone.progress_pose,drone.progress_step = tuple(drone.pose),step
            blocker.avoid,blocker.first,blocker.until = center,tuple(route[0]),self.until
            blocker.audit.append((step,"reconnect_selected",center,tuple(original),point,float(cost),route[:4]))
            return route[0]
        blocker.audit.append((step,"reconnect_no_safe_route",center,tuple(original),len(self.contacts),len(choices)))
        return original

    def continue_task(self, drone, blocker, task):
        step=int(drone.elapsed_timestep)
        if self.last_contact >= task.started:
            blocker.audit.append((step,"reconnect_received",blocker.view.observed,task.point,self.last_contact))
            self.task = None
            return "completed"
        if step>=self.until or not drone.route or math.dist(drone.pose,task.point)<=10.:
            blocker.audit.append((step,"reconnect_ended",blocker.view.observed,task.point))
            self.task = None
            return "completed"
        if not route_is_clear(drone.grid,drone.pose,drone.route,blocker.view.observed,blocker.outside):
            self.task = None
            return "unavailable"
        return None

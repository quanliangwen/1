"""Sensor-only rolling assignment, frontier exploration and shortest-path rescue."""

import heapq
import math

import numpy as np

from swarm_rescue.simulation.utils.constants import MAX_RANGE_LIDAR_SENSOR
from scipy.ndimage import binary_dilation
from scipy.optimize import linear_sum_assignment

from swarm_rescue.simulation.drone.drone_abstract import DroneAbstract
from swarm_rescue.simulation.ray_sensors.drone_semantic_sensor import DroneSemanticSensor


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class SensorGrid:
    """20 px occupancy grid; unknown cells stay traversable with a small cost."""

    CELL = 20

    def __init__(self, size):
        self.size = np.asarray(size, dtype=float)
        shape = tuple(np.ceil(self.size[::-1] / self.CELL).astype(int))
        self.evidence = np.zeros(shape, dtype=np.int8)
        self.visits = np.zeros(shape, dtype=np.int32)
        self.blocked = np.zeros(shape, dtype=bool)

    def cell(self, point):
        col = int((point[0] + self.size[0] / 2) / self.CELL)
        row = int((point[1] + self.size[1] / 2) / self.CELL)
        return min(max(row, 0), self.evidence.shape[0] - 1), min(max(col, 0), self.evidence.shape[1] - 1)

    def point(self, cell):
        row, col = cell
        return [float((col + 0.5) * self.CELL - self.size[0] / 2),
                float((row + 0.5) * self.CELL - self.size[1] / 2)]

    def observe(self, position, heading, ranges, angles, movable):
        free, walls = set(), set()
        for radius, angle in zip(ranges[::6], angles[::6]):
            if not math.isfinite(radius) or radius < 5:
                continue
            radius = min(float(radius), MAX_RANGE_LIDAR_SENSOR - 5)
            direction = np.array([math.cos(heading + angle), math.sin(heading + angle)])
            for length in np.arange(0, max(0, radius - 15), self.CELL):
                free.add(self.cell(position + length * direction))
            end = position + radius * direction
            if radius < MAX_RANGE_LIDAR_SENSOR - 10 and all(distance(end, p) > 22 for p in movable):
                walls.add(self.cell(end))
        for cell in free - walls:
            self.evidence[cell] = max(-8, int(self.evidence[cell]) - 2)
        for cell in walls:
            self.evidence[cell] = min(8, int(self.evidence[cell]) + 3)
        self.evidence[self.cell(position)] = -8
        self.visits[self.cell(position)] += 1
        self.blocked = binary_dilation(self.evidence >= 3)
        return tuple(walls)

    def path(self, start, goal):
        start, goal = self.cell(start), self.cell(goal)
        blocked = self.blocked.copy()
        blocked[start] = blocked[goal] = False
        queue, costs, parent = [(0.0, start)], {start: 0.0}, {}
        # bounded A* on the coarse grid; finer maps if narrow passages require it.
        for _ in range(3000):
            if not queue:
                break
            _, cell = heapq.heappop(queue)
            if cell == goal:
                route = [cell]
                while cell in parent:
                    cell = parent[cell]
                    route.append(cell)
                return [self.point(c) for c in route[::-1][1:]]
            row, col = cell
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                other = row + dr, col + dc
                if not (0 <= other[0] < blocked.shape[0] and 0 <= other[1] < blocked.shape[1]):
                    continue
                if blocked[other] or (dr and dc and (blocked[row + dr, col] or blocked[row, col + dc])):
                    continue
                cost = costs[cell] + math.hypot(dr, dc) * (1.18 if self.evidence[other] == 0 else 1.0)
                if cost < costs.get(other, float('inf')):
                    costs[other], parent[other] = cost, cell
                    heapq.heappush(queue, (cost + math.hypot(goal[0] - other[0], goal[1] - other[1]), other))
        return []


class RollingRescue(DroneAbstract):
    """Each drone solves a local assignment using observations shared within radio range."""

    RECHECK_STEPS = 30

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grid = SensorGrid(self.size_area)
        self.pose = None
        self.heading = 0.0
        self.home = None
        # Record states: 0 observed free, 1 held, 2 confirmed disposed, 3 unresolved loss.
        self.bombs = {}
        self.serial = 0
        self.peers = {}
        self.task = None
        self.carrying = False
        self._last_grasper = 0
        self.route = []
        self.goal = None
        self.frontier = None
        self.wall_message = ()
        self.docking = 0

    def define_message_for_all(self):
        if self.pose is None:
            return None
        target = self.bombs.get(self.task)
        return {'kind': 'rolling-rescue', 'id': self.identifier, 'position': tuple(self.pose),
                'step': self.elapsed_timestep, 'carry': self.carrying,
                'target': tuple(target[:2]) if target else self.frontier,
                'home': self.home, 'bombs': tuple((key, tuple(value)) for key, value in self.bombs.items()),
                'walls': self.wall_message}

    def _remember(self, point, stamp, state=0, key=None):
        near = min(self.bombs, key=lambda k: distance(point, self.bombs[k]), default=None)
        if near is not None and distance(point, self.bombs[near]) < 22:
            if stamp >= self.bombs[near][2]:
                old = self.bombs[near]
                weight = 0.35 if state == old[3] == 0 else 1.0
                self.bombs[near] = [(1 - weight) * old[i] + weight * point[i] for i in [0, 1]] + [stamp, state]
            return near
        if key is None:
            self.serial += 1
            key = (self.identifier, self.serial)
        self.bombs[key] = [float(point[0]), float(point[1]), stamp, state]
        return key

    def _receive(self):
        for _, msg in self.communicator.received_messages:
            if not isinstance(msg, dict) or msg.get('kind') != 'rolling-rescue':
                continue
            self.peers[msg['id']] = msg
            if self.home is None and msg['home'] is not None:
                self.home = msg['home']
            for key, value in msg['bombs']:
                self._remember(value[:2], value[2], value[3], key)
            for cell in msg['walls']:
                self.grid.evidence[cell] = max(int(self.grid.evidence[cell]), 3)
        self.peers = {key: value for key, value in self.peers.items() if self.elapsed_timestep - value['step'] < 20}

    def _align_pose(self, velocity):
        return velocity

    def _sense(self):
        gps, compass = self.measured_gps_position(), self.measured_compass_angle()
        odom = self.odometer_values()
        velocity = None
        if compass is not None and math.isfinite(compass):
            self.heading = float(compass)
            if odom is not None and np.all(np.isfinite(odom)):
                # alpha uses the previous heading; odom[2] is this step's turn.
                angle = self.heading - float(odom[2]) + float(odom[1])
                # One-step displacement, used as mean velocity in engine step units.
                velocity = float(odom[0]) * np.array([math.cos(angle), math.sin(angle)])
        if gps is not None and np.all(np.isfinite(gps)):
            gps = np.asarray(gps, dtype=float)
            if self.pose is None:
                self.pose = gps.copy()
            else:
                drift = velocity if velocity is not None and np.all(np.isfinite(velocity)) else np.zeros(2)
                self.pose = 0.82 * (self.pose + drift) + 0.18 * gps
        if self.pose is None:
            return None, [], []
        velocity = self._align_pose(velocity)
        hits, objects, depot_hits = [], [], []
        for hit in self.semantic_values() or []:
            if not math.isfinite(hit.distance) or not math.isfinite(hit.angle):
                continue
            angle = self.heading + hit.angle
            point = self.pose + hit.distance * np.array([math.cos(angle), math.sin(angle)])
            if hit.entity_type in (DroneSemanticSensor.TypeEntity.BOMB, DroneSemanticSensor.TypeEntity.DRONE):
                objects.append(point)
            if hit.entity_type == DroneSemanticSensor.TypeEntity.BOMB:
                if not hit.grasped:
                    key = self._remember(point, self.elapsed_timestep)
                    hits.append((key, hit))
            elif hit.entity_type == DroneSemanticSensor.TypeEntity.DISPOSAL_CENTER:
                depot_hits.append((float(hit.distance), point, hit))
        if depot_hits:
            nearest = min(depot_hits, key=lambda value: value[0])
            if self.home is None:
                self.home = tuple(nearest[1])
        ranges = self.lidar_values()
        if ranges is not None and self.elapsed_timestep % 5 == self.identifier % 5:
            self.wall_message = self.grid.observe(self.pose, self.heading, np.asarray(ranges), self.lidar_rays_angles(), objects)
        return velocity, hits, depot_hits

    def _assign(self):
        available = [key for key, value in self.bombs.items()
                     if value[3] in (0, 3) and self.elapsed_timestep - value[2]
                     < (self.RECHECK_STEPS if value[3] == 3 else 700)]
        if not available:
            self.task = None
            return
        agents = [(self.identifier, self.pose, self.bombs.get(self.task, [])[:2])]
        agents += [(i, p['position'], p['target']) for i, p in self.peers.items() if not p['carry']]
        agents.sort(key=lambda item: item[0])
        available.sort(key=lambda key: (round(self.bombs[key][0] / 20), round(self.bombs[key][1] / 20)))
        costs = np.empty((len(agents), len(available)))
        for row, (identifier, position, current) in enumerate(agents):
            for col, key in enumerate(available):
                point = self.bombs[key]
                cost = distance(position, point) + (distance(point, self.home) if self.home else 0)
                if current is not None and len(current) == 2 and distance(current, point) < 25:
                    cost -= 35  # Switching cost stabilizes assignments under sensor noise.
                costs[row, col] = cost + 0.001 * identifier * col
        rows, cols = linear_sum_assignment(costs)
        self.task = None
        for row, col in zip(rows, cols):
            if agents[row][0] == self.identifier:
                self.task = available[col]

    def _explore(self):
        if self.frontier is not None and distance(self.pose, self.frontier) > 35 and self.elapsed_timestep % 80:
            return self.frontier
        unknown = self.grid.evidence == 0
        frontier = (self.grid.evidence < 0) & binary_dilation(unknown) & ~self.grid.blocked
        cells = np.argwhere(frontier)
        best, best_cost = None, float('inf')
        for cell in cells[::max(1, len(cells) // 100)]:
            point = self.grid.point(cell)
            length = distance(self.pose, point)
            if length < 55:
                continue
            crowding = sum(max(0, 150 - distance(point, p['target'])) for p in self.peers.values() if p['target'] is not None)
            row, col = cell
            gain = int(unknown[max(0, row - 2):row + 3, max(0, col - 2):col + 3].sum())
            cost = length - 12 * gain + 0.7 * crowding + 15 * self.grid.visits[row, col]
            if cost < best_cost:
                best, best_cost = point, cost
        if best is None:
            angle = self.identifier * 2.399 + self.elapsed_timestep / 140
            best = (self.pose + 140 * np.array([math.cos(angle), math.sin(angle)])).tolist()
            best = np.clip(best, -self.grid.size / 2 + 35, self.grid.size / 2 - 35).tolist()
        self.frontier = tuple(best)
        return self.frontier

    def _navigate(self, target, velocity, contact=False):
        delta = np.asarray(target) - self.pose
        length = float(np.linalg.norm(delta))
        ranges = self.lidar_values()
        angles = self.lidar_rays_angles()
        if not contact and length > 65:
            if self.goal is None or distance(target, self.goal) > 30 or self.elapsed_timestep % 30 == self.identifier % 30:
                self.grid.blocked = binary_dilation(self.grid.evidence >= 3)
                self.route = self.grid.path(self.pose, target)
                self.goal = tuple(target)
            while self.route and distance(self.pose, self.route[0]) < 28:
                self.route.pop(0)
            if self.route:
                delta = np.asarray(self.route[0]) - self.pose
        desired_angle = math.atan2(delta[1], delta[0])
        relative = (desired_angle - self.heading + math.pi) % (2 * math.pi) - math.pi
        best_cost, desired_velocity = float('inf'), np.zeros(2)
        if ranges is not None:
            ranges = np.asarray(ranges, dtype=float).copy()
            if contact:
                mask = (np.abs((angles - relative + math.pi) % (2 * math.pi) - math.pi) < 0.35) & (ranges > length - 22)
                ranges[mask] = MAX_RANGE_LIDAR_SENSOR
            for offset in np.linspace(-math.pi, math.pi, 37):
                direction = relative + offset
                cone = np.abs((angles - direction + math.pi) % (2 * math.pi) - math.pi) < 0.27
                clearance = float(np.nanmin(ranges[cone])) if cone.any() else MAX_RANGE_LIDAR_SENSOR
                speed = min(6.0, max(0.0, (clearance - 24) / 5), max(0.5, length * 0.22))
                world_angle = self.heading + direction
                v = speed * np.array([math.cos(world_angle), math.sin(world_angle)])
                cost = -float(np.dot(v, delta / max(1, np.linalg.norm(delta)))) + 0.003 * abs(offset)
                if cost < best_cost:
                    best_cost, desired_velocity = cost, v
        else:
            desired_velocity = 2 * delta / max(1, np.linalg.norm(delta))
        for peer in self.peers.values():
            away = self.pose - np.asarray(peer['position'])
            gap = float(np.linalg.norm(away))
            if 1 < gap < 38:
                desired_velocity += away / gap * (38 - gap) * 0.15
        velocity = velocity if velocity is not None and np.all(np.isfinite(velocity)) else np.zeros(2)
        force = (desired_velocity - velocity) / 5.5
        forward = force[0] * math.cos(self.heading) + force[1] * math.sin(self.heading)
        lateral = -force[0] * math.sin(self.heading) + force[1] * math.cos(self.heading)
        return {'forward': float(np.clip(forward, -1, 1)), 'lateral': float(np.clip(lateral, -1, 1)),
                'rotation': float(np.clip(relative * 1.8, -1, 1)), 'grasper': 1}

    def control(self):
        command = self._control()
        self._last_grasper = command['grasper']
        return command

    def _control(self):
        self._receive()
        velocity, hits, depot_hits = self._sense()
        carrying = bool(self.grasped_bombs())
        if carrying and not self.carrying and self.task in self.bombs:
            self.bombs[self.task][2:] = [self.elapsed_timestep, 1]
        if self.carrying and not carrying:
            if self.task in self.bombs:
                visible = any(key == self.task for key, _ in hits)
                if visible:
                    # The current free-target observation already updated its record.
                    pass
                elif self._last_grasper == 1 and self.drone_health > 0 and self.reward > 0:
                    # Holding was maintained: loss plus own reward supports disposal.
                    self.bombs[self.task][2:] = [self.elapsed_timestep, 2]
                else:
                    # Reward alone cannot identify a released bomb. Reobserve near
                    # the carrier; this is a search anchor, not a measured bomb center.
                    anchor = self.pose if self.pose is not None else self.bombs[self.task][:2]
                    self.bombs[self.task] = [float(anchor[0]), float(anchor[1]), self.elapsed_timestep, 3]
            self.task, self.route, self.docking = None, [], 0
        self.carrying = carrying
        if self.pose is None:
            return {'forward': 0.0, 'lateral': 0.0, 'rotation': 0.2, 'grasper': int(carrying)}
        if not carrying and (self.task not in self.bombs or self.bombs[self.task][3] != 0 or self.elapsed_timestep % 24 == self.identifier % 24):
            self._assign()
        if carrying and self.home is not None:
            target = self.home
            if depot_hits:
                nearest = min(depot_hits, key=lambda item: item[0])
                target = nearest[1]
                if nearest[0] < 38:
                    self.docking += 1
                    command = self._navigate(target, velocity, contact=True)
                    if self.docking > 16:
                        command['rotation'] = 0.8 if self.identifier % 2 else -0.8
                    if self.docking % 55 >= 48:
                        command['grasper'] = 0
                    return command
            return self._navigate(target, velocity)
        if carrying:
            return self._navigate(self._explore(), velocity)
        visible = [(key, hit) for key, hit in hits if key == self.task]
        if visible:
            hit = min(visible, key=lambda item: item[1].distance)[1]
            angle = self.heading + hit.angle
            target = self.pose + (hit.distance + 5) * np.array([math.cos(angle), math.sin(angle)])
            return self._navigate(target, velocity, contact=True)
        if self.task in self.bombs:
            target = self.bombs[self.task][:2]
        else:
            target = self._explore()
        remaining = self._misc_data.max_timestep_limit - self.elapsed_timestep
        if self.drone_health < 15 or remaining < 50:
            target = self.pose if self.home is None else self.home
        command = self._navigate(target, velocity)
        command['grasper'] = 1 if self.task is not None else 0
        return command


if __name__ == '__main__':
    grid = SensorGrid((200, 160))
    grid.blocked[:, 5] = True
    grid.blocked[5, 5] = False
    route = grid.path((-70, -50), (70, 50))
    assert route and any(grid.cell(point) == (5, 5) for point in route)
    assert all(not grid.blocked[grid.cell(point)] for point in route)
    rows, cols = linear_sum_assignment([[2, 9], [9, 2], [8, 8]])
    assert list(zip(rows, cols)) == [(0, 0), (1, 1)]
    print('Shortest-path passage and rectangular assignment checks passed.')

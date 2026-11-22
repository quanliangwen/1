"""两个控制器共用的传感器定位、已观测栅格和速度反馈控制。"""

import math
from collections import Counter

import numpy as np
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt, map_coordinates
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from swarm_rescue.simulation.utils.constants import MAX_RANGE_LIDAR_SENSOR
from swarm_rescue.solutions.boundary_anchor import BoundaryAnchor
from swarm_rescue.solutions.rolling_rescue import RollingRescue, SensorGrid, distance
from swarm_rescue.solutions.scan_geometry import scan_lines


class ObservedGrid(SensorGrid):
    """只在已观测自由格上生成执行路径；未知区域只进入预测情景。"""

    HULL_CLEARANCE = 18
    FOOTPRINT = HULL_CLEARANCE + 6
    WALL_LINE = np.array([[0, 0, 0], [1, 1, 1], [0, 0, 0]], dtype=bool)
    WALL_DIAGONAL = np.eye(3, dtype=bool)

    def __init__(self, size):
        super().__init__(size)
        self.stamps = np.zeros(self.evidence.shape, dtype=np.int32)
        self.tick = 0
        self.trees = {}
        self.clearance = np.zeros(self.evidence.shape)
        self.tight = np.zeros(self.evidence.shape, dtype=bool)
        self._topology = None
        self._walkable = None
        self._graphs = {}
        self._cell_keys = list(np.ndindex(self.evidence.shape))
        self.compute_stats = Counter()
        self.speed_scale = 1.0
        self._contacts = {}
        self._alignment_walls = None
        self._alignment_field = None
        self._supported_walls = np.zeros_like(self.evidence, dtype=bool)
        # Positive: locally seen hull clearance near a flight track. Negative:
        # a later close wall return with positioning available revoked it.
        self.passage_stamps = np.zeros_like(self.stamps)
        self.last_pose_fix = -1000
        self.pose_fixed = False
        self.return_guard = False
        self.carried_wall_guard = False

    def align(self, position, heading, endpoints, walls):
        """Bound the outage pose correction to surfaces already observed."""
        correction = np.zeros(3)
        if len(endpoints) < 12 or np.count_nonzero(walls) < 6:
            return correction
        if not np.array_equal(walls, self._alignment_walls):
            self._alignment_walls = walls
            self._alignment_field = distance_transform_edt(~walls) * self.CELL

        def residual(candidates, points):
            angles = heading + candidates[:, 2, None]
            cosine, sine = np.cos(angles), np.sin(angles)
            x = position[0] + candidates[:, 0, None] + cosine * points[:, 0] - sine * points[:, 1]
            y = position[1] + candidates[:, 1, None] + sine * points[:, 0] + cosine * points[:, 1]
            indices = np.array([(y + self.size[1] / 2) / self.CELL - .5,
                                (x + self.size[0] / 2) / self.CELL - .5])
            distance_field = map_coordinates(self._alignment_field, indices, order=1, cval=60.)
            return np.maximum(distance_field - self.CELL / 2, 0.)

        initial = residual(correction[None, :], endpoints)[0]
        overlap = initial < 35
        if np.count_nonzero(overlap) < max(12, .35 * len(endpoints)):
            return correction
        endpoints = endpoints[overlap]
        scale = np.array([12., 12., math.radians(8)])
        for shift, turn, offsets in ((12, 4, range(-2, 3)), (4, 2, range(-1, 2)), (2, .5, range(-1, 2))):
            yaw = np.radians([turn * i for i in offsets])
            choices = np.stack(np.meshgrid([-shift, 0, shift], [-shift, 0, shift], yaw), axis=-1).reshape(-1, 3)
            candidates = correction + choices
            candidates = candidates[(np.abs(candidates[:, :2]) <= 18).all(axis=1)
                                    & (np.abs(candidates[:, 2]) <= math.radians(10))]
            distances = residual(candidates, endpoints)
            costs = np.mean(np.minimum(distances, 30) ** 2, axis=1) + 4 * np.sum((candidates / scale) ** 2, axis=1)
            correction = candidates[int(np.argmin(costs))]
        fitted = residual(correction[None, :], endpoints)[0]
        if np.mean(fitted) >= 12 or np.mean(fitted < 20) < .7:
            correction[:] = 0
        return correction

    def observe(self, position, heading, ranges, angles, movable):
        valid = np.isfinite(ranges) & (ranges > 5)
        range_cap = MAX_RANGE_LIDAR_SENSOR - 5
        radii, bearings = np.minimum(ranges[valid][::2], range_cap), angles[valid][::2] + heading
        unit = np.column_stack((np.cos(bearings), np.sin(bearings)))
        lengths = np.arange(0, range_cap, 10)
        ray_points = position + lengths[None, :, None] * unit[:, None, :]
        free_points = ray_points[lengths[None, :] < radii[:, None] - 12]
        ends = position + radii[:, None] * unit
        wall_mask = radii < MAX_RANGE_LIDAR_SENSOR - 10
        if movable:
            objects = np.asarray(movable)
            gaps = np.linalg.norm(ends[:, None, :] - objects[None, :, :], axis=2)
            if self.speed_scale == 1:
                radial = np.abs(radii[:, None] - np.linalg.norm(objects - position, axis=1))
                wall_mask &= ~np.any((gaps < 25) & (radial < 12), axis=1)
            else:
                wall_mask &= gaps.min(axis=1) > 25

        def cells(points):
            coordinates = ((points + self.size / 2) / self.CELL).astype(int)
            inside = ((coordinates >= 0) & (coordinates < self.evidence.shape[::-1])).all(axis=1)
            coordinates = coordinates[inside]
            width = self.evidence.shape[1]
            indices = np.unique(coordinates[:, 1] * width + coordinates[:, 0])
            return {(int(index // width), int(index % width)) for index in indices}

        points = ends[wall_mask]
        if self.speed_scale == 1:
            steps = np.diff(ends, axis=0)
            linked = wall_mask[:-1] & wall_mask[1:] & (np.linalg.norm(steps, axis=1) < 32)
            # Join adjacent returns on the same surface before rasterization.
            between = ends[:-1][linked, None, :] + np.array([.25, .5, .75])[None, :, None] * steps[linked, None, :]
            points = np.concatenate((points, between.reshape(-1, 2)))
        walls = cells(points)
        free = cells(free_points) - walls
        wall_guard = self.return_guard or self.carried_wall_guard
        protected = [cell for cell in free if self._supported_walls[cell]] if wall_guard else ()
        if protected:
            # A long wall can only lose evidence to a close observation of
            # the whole cell. Grazing rays and peer free votes cannot open it.
            corners = np.array(((0, 0), (-.5, -.5), (-.5, .5), (.5, -.5), (.5, .5))) * self.CELL
            confirmed = self.clear_view(np.asarray([self.point(c) for c in protected])[:, None, :] + corners,
                                        position, heading, ranges, angles, 105).all(axis=1) if self.pose_fixed else ()
            free.difference_update(protected)
            free.update(cell for cell, clear in zip(protected, confirmed) if clear)
            self.compute_stats['wall_clear_rejected'] += len(protected) - np.count_nonzero(confirmed)
        if self.return_guard and self.pose_fixed and walls:
            # A direct, close return can retract a prior passage certificate.
            for cell in cells(ends[wall_mask & (radii <= 60)]):
                if self.passage_stamps[cell] > 0:
                    self.passage_stamps[cell] = -(self.tick + 1)
        if self.return_guard and self.tick - self.last_pose_fix <= 100:
            self.remember_passage(position, heading, ranges, angles, free, walls)
        for cell in free:
            self.evidence[cell] = max(-8, int(self.evidence[cell]) - 2)
            self.stamps[cell] = self.tick + 1
        for cell in walls:
            if self.passage_stamps[cell] > 0:
                self.compute_stats['passage_wall_rejected'] += 1
                continue
            self.evidence[cell] = min(8, int(self.evidence[cell]) + 3)
            self.stamps[cell] = self.tick + 1
        here = self.cell(position)
        if not wall_guard or not self._supported_walls[here]:
            self.evidence[here], self.stamps[here] = -8, self.tick + 1
        self.visits[here] += 1
        self.refresh()
        return tuple(walls)

    @staticmethod
    def clear_view(points, position, heading, ranges, angles, limit):
        delta = points - position
        depth = np.linalg.norm(delta, axis=-1)
        bearing = (np.arctan2(delta[..., 1], delta[..., 0]) - heading + math.pi) % (2 * math.pi) - math.pi
        ray = np.clip(np.searchsorted(angles, bearing), 1, len(angles) - 1)
        return (depth <= limit) & (np.minimum(ranges[ray - 1], ranges[ray]) > depth + 12)

    def remember_passage(self, position, heading, ranges, angles, free, walls):
        """Retain locally verified free hull footprints near the flown route."""
        if np.count_nonzero(np.isfinite(ranges) & (ranges > 5)) < .9 * len(ranges):
            return
        row, col = self.cell(position)
        height, width = self.evidence.shape
        cells = [(r, c) for r in range(max(1, row-2), min(height-1, row+3))
                 for c in range(max(1, col-2), min(width-1, col+3))
                 if (r, c) in free and (r, c) not in walls and not self._supported_walls[r, c]
                 and self.passage_stamps[r, c] <= 0]
        if not cells:
            return
        centres = np.asarray([self.point(c) for c in cells])
        clear = self.clear_view(centres, position, heading, ranges, angles, 38)
        near = (ranges > 5) & (ranges < 65)
        if near.any():
            yaw = angles[near] + heading
            returns = position + ranges[near, None] * np.column_stack((np.cos(yaw), np.sin(yaw)))
            clear &= (np.linalg.norm(centres[:, None] - returns, axis=-1) >= self.FOOTPRINT).all(axis=1)
        for cell, passed in zip(cells, clear):
            if passed:
                self.passage_stamps[cell] = self.tick + 1
                self.evidence[cell] = -8
                self.compute_stats['passage_cells_certified'] += 1

    def refresh(self):
        obstacles = self.evidence >= 3
        obstacles[[0, -1], :] = True
        obstacles[:, [0, -1]] = True
        free = self.evidence < 0
        previous = self._topology
        walls_changed = previous is None or not np.array_equal(obstacles, previous[0])
        if not walls_changed and np.array_equal(free, previous[1]):
            return
        if walls_changed:
            self.clearance = distance_transform_edt(~obstacles) * self.CELL
        if walls_changed and (self.return_guard or self.carried_wall_guard):
            support = np.zeros_like(obstacles)
            for along, across in ((self.WALL_LINE, self.WALL_LINE.T), (self.WALL_LINE.T, self.WALL_LINE),
                                  (self.WALL_DIAGONAL, self.WALL_DIAGONAL[:, ::-1]),
                                  (self.WALL_DIAGONAL[:, ::-1], self.WALL_DIAGONAL)):
                band = binary_dilation(obstacles, structure=across)
                support |= binary_erosion(band, structure=along, iterations=2)
            self._supported_walls = (self._supported_walls | (support & (self.evidence >= 6))) & obstacles
        if walls_changed and self.speed_scale == 1:
            # A known-free centre line can be one coarse cell wide. Keep the
            # exception local to opposed walls and their immediate approaches.
            opposed = np.zeros_like(obstacles)
            for walls, corridor in ((obstacles, opposed), (obstacles.T, opposed.T)):
                corridor[1:-1] |= walls[:-2] & walls[2:]
                between = walls[:-3] & walls[3:]
                corridor[1:-2] |= between
                corridor[2:-1] |= between
            opposed[1:-1, 1:-1] |= ((obstacles[:-2, :-2] & obstacles[2:, 2:])
                                    | (obstacles[:-2, 2:] & obstacles[2:, :-2]))
            self.tight = (binary_dilation(opposed & ~obstacles)
                          & (self.clearance >= self.HULL_CLEARANCE) & (self.clearance < 32))
        self.blocked = (self.clearance < 23) & ~self.tight
        self._topology = obstacles, free
        self._contacts.clear()
        empty = free & ((self.clearance >= 23) | self.tight)
        # In a mapped passage, plan the centre line for the hull. The live
        # controller still uses loaded braking distance and limits rotation.
        walkable = (empty, empty if self.speed_scale == 1 else free & ((self.clearance >= 32) | self.tight))
        changed = {loaded for loaded in (False, True)
                   if self._walkable is None or not np.array_equal(walkable[loaded], self._walkable[loaded])}
        self._walkable = walkable
        self.compute_stats['retained_trees'] += sum(key[1] not in changed for key in self.trees)
        self.trees = {key: value for key, value in self.trees.items()
                      if not (key[4] or (walls_changed if key[3] else key[1] in changed))}
        self._graphs = {key: value for key, value in self._graphs.items()
                        if not (key[4] or (walls_changed if key[3] else key[0] in changed))}

    def enable_return_guard(self):
        if not self.return_guard:
            self.return_guard = True
            self._topology = None
            self.refresh()

    def set_carried_wall_guard(self, carrying):
        """Retain continuous wall evidence locally for the current return."""
        refresh = carrying and not (self.carried_wall_guard or self.return_guard)
        self.carried_wall_guard = carrying
        if refresh:
            self._topology = None
            self.refresh()

    def merge(self, evidence, stamps, passages):
        other = np.frombuffer(evidence, dtype=np.int8).reshape(self.evidence.shape)
        age = np.frombuffer(stamps, dtype=np.int32).reshape(self.evidence.shape)
        reopened = False
        if passages:
            self.enable_return_guard()
            proof = np.frombuffer(passages, dtype=np.int32).reshape(self.evidence.shape)
            adopt = (np.abs(proof) > np.abs(self.passage_stamps)) & ((proof < 0) | ~self._supported_walls)
            self.passage_stamps[adopt] = proof[adopt]
            opened = adopt & (proof > 0) & (self.evidence >= 0)
            reopened = opened.any()
            self.evidence[opened] = -8
            self.stamps[opened] = np.maximum(self.stamps[opened], proof[opened])
        newer = age > self.stamps
        protected = self.evidence >= 6
        if self.return_guard or self.carried_wall_guard:
            protected |= self._supported_walls
        newer &= ~(protected & (other < 3))
        if self.return_guard:
            newer &= ~((self.passage_stamps > 0) & (other >= 0))
        self.evidence[newer], self.stamps[newer] = other[newer], age[newer]
        if reopened or newer.any():
            self.refresh()

    def tree(self, start, loaded=False, avoid=(), *, narrow=False):
        return self.tree_cells((self.cell(start),), loaded, avoid, narrow=narrow)

    def tree_cells(self, starts, loaded=False, avoid=(), *, optimistic=False, narrow=False):
        starts = tuple(sorted(starts))
        loaded = self.graph_load(loaded)
        key = starts, loaded, avoid, optimistic, narrow
        if key in self.trees:
            return self.trees[key]
        if not starts:
            self.trees[key] = {}, {}
            return self.trees[key]
        graph = self.graph(starts, loaded, avoid, optimistic, narrow)
        width = self.evidence.shape[1]
        indices = [row * width + col for row, col in starts]
        distances, predecessors, _ = dijkstra(graph, directed=True, indices=indices,
                                              min_only=True, return_predecessors=True)
        reachable = np.flatnonzero(np.isfinite(distances))
        cells = self._cell_keys
        costs = dict(zip((cells[i] for i in reachable.tolist()), distances[reachable].tolist()))
        linked = reachable[predecessors[reachable] >= 0]
        parents = dict(zip((cells[i] for i in linked.tolist()),
                           (cells[i] for i in predecessors[linked].tolist())))
        self.trees[key] = costs, parents
        return costs, parents

    def route(self, start, goal, loaded=False, contact=False, avoid=(), *, narrow=False):
        costs, parents = self.tree(start, loaded, avoid, narrow=narrow)
        target = self.cell(goal)
        if target not in costs:
            if not contact:
                return ()
            row, col = self.cell(goal)
            reach = math.ceil(75 / self.CELL)
            candidates = ((r, c)
                          for r in range(max(0, row - reach), min(self.evidence.shape[0], row + reach + 1))
                          for c in range(max(0, col - reach), min(self.evidence.shape[1], col + reach + 1))
                          if (r, c) in costs)
            nearby = [c for c in candidates if distance(self.point(c), goal) < 75
                      and self.visible(self.point(c), goal)]
            if not nearby:
                return ()
            target = min(nearby, key=lambda c: distance(self.point(c), goal) + 0.05 * costs[c])
        cells = [target]
        while cells[-1] in parents:
            cells.append(parents[cells[-1]])
        return tuple(tuple(self.point(c)) for c in reversed(cells))

    def contact_cells(self, point, radius=35, loaded=True):
        """可接触目标、视线通畅且有足够机身净空的格子。"""
        key = tuple(point), radius, loaded
        if key in self._contacts:
            return self._contacts[key]
        walkable = self.walkable(loaded)
        row, col = self.cell(point)
        reach = math.ceil(radius / self.CELL)
        result = tuple((r, c) for r in range(max(0, row - reach), min(self.evidence.shape[0], row + reach + 1))
                     for c in range(max(0, col - reach), min(self.evidence.shape[1], col + reach + 1))
                     if walkable[r, c]
                     and distance(self.point((r, c)), point) < radius and self.visible(self.point((r, c)), point))
        if len(self._contacts) >= 512:
            self._contacts.clear()
        self._contacts[key] = result
        return result

    def return_frontier(self, start, home, ends, checked, corridor=()):
        costs = self.tree(start, loaded=True)[0]
        unknown = (self.evidence >= 0) & (self.evidence < 3)
        frontier = self.walkable(loaded=True) & binary_dilation(unknown)
        cells = [c for c in costs if frontier[c] and costs[c] > 30 and c not in checked]
        if not cells:
            return None
        # Unknown cells can guide the choice of observation point. The actual
        # route to that point still uses only observed free space.
        toward = self.tree_cells(ends or (self.cell(home),), loaded=True, optimistic=True)[0]
        cells = [c for c in cells if c in corridor and c in toward] or cells
        cell = min(cells, key=lambda c: (c not in toward,
            toward.get(c, 2 * distance(self.point(c), home)) + .35 * costs[c] + 10 * self.visits[c], c))
        return tuple(self.point(cell)), costs[cell]

    def coverage(self, point):
        row, col = self.cell(point)
        return frozenset((r, c) for r in range(max(0, row - 5), min(self.evidence.shape[0], row + 6))
                         for c in range(max(0, col - 5), min(self.evidence.shape[1], col + 6))
                         if self.evidence[r, c] == 0)

    def geodesic(self, a, b):
        return self.tree(a)[0].get(self.cell(b), distance(a, b) * 2)

    def visible(self, a, b):
        """预测传感器的已知墙遮挡；未知区域的墙仍属于模型误差。"""
        count = max(2, math.ceil(distance(a, b) / 10))
        cells = ((np.linspace(a, b, count)[1:-1] + self.size / 2) / self.CELL).astype(int)
        cells = np.clip(cells, 0, np.array(self.evidence.shape[::-1]) - 1)
        return bool(np.all(self.evidence[cells[:, 1], cells[:, 0]] < 3))

    def walkable(self, loaded=False):
        if self._walkable is None:
            self.refresh()
        return self._walkable[loaded]

    def graph_load(self, loaded):
        return bool(loaded and self.speed_scale > 1)

    def needs_alignment(self, start, goal, loaded):
        return any(self.tight[c] or (loaded and 0 < self.clearance[c] < 32)
                   for c in (self.cell(start), self.cell(goal)))

    def graph(self, starts, loaded, avoid, optimistic=False, narrow=False):
        loaded = self.graph_load(loaded)
        if optimistic:
            walkable = (self.clearance >= (32 if loaded else 23)) | self.tight
        else:
            walkable = self.walkable(loaded).copy()
        if narrow:
            # Recovery may use sensed free hull-width cells; walls and unknown cells stay excluded.
            walkable |= (self.evidence < 0) & (self.clearance >= self.HULL_CLEARANCE)
        if avoid:
            rows, cols = np.indices(walkable.shape)
            x = (cols + .5) * self.CELL - self.size[0] / 2
            y = (rows + .5) * self.CELL - self.size[1] / 2
            for point, radius in avoid:
                walkable &= (x - point[0]) ** 2 + (y - point[1]) ** 2 >= radius ** 2
        forced = tuple(start for start in starts if not walkable[start])
        key = loaded, avoid, forced, optimistic, narrow
        if key in self._graphs:
            self.compute_stats['graph_cache_hits'] += 1
            return self._graphs[key]
        for start in forced:
            walkable[start] = True
        height, width = walkable.shape
        nodes = np.arange(walkable.size).reshape(walkable.shape)
        sources, targets, weights = [], [], []
        for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
            rows, cols = slice(0, height - dr), slice(max(0, -dc), min(width, width - dc))
            next_rows, next_cols = slice(dr, height), slice(max(0, dc), min(width, width + dc))
            valid = walkable[rows, cols] & walkable[next_rows, next_cols]
            if dr and dc:
                valid &= walkable[next_rows, cols] & walkable[rows, next_cols]
            source, target = nodes[rows, cols][valid], nodes[next_rows, next_cols][valid]
            sources.extend((source, target))
            targets.extend((target, source))
            weight = np.full(source.size, math.hypot(dr, dc) * self.CELL)
            if narrow:
                safe = self.walkable(loaded).ravel()
                weight += self.CELL * ~(safe[source] & safe[target])
            weights.append(np.tile(weight, 2))
        graph = csr_matrix((np.concatenate(weights), (np.concatenate(sources), np.concatenate(targets))),
                           shape=(walkable.size, walkable.size))
        # Transient avoidance zones can create many graph keys; keep this cache bounded.
        if len(self._graphs) >= 16:
            self._graphs.clear()
        self._graphs[key] = graph
        self.compute_stats['graph_builds'] += 1
        return graph


class SensorRescue(RollingRescue):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grid = ObservedGrid(self.size_area)
        self.velocity_trim = np.zeros(2)
        self._odometry_only = False
        self.corridor_axis = None
        self._outage_walls = None
        self.boundary_anchor = BoundaryAnchor(self.size_area)

    def _align_pose(self, velocity):
        if not self._odometry_only or self.elapsed_timestep % 5 != self.identifier % 5:
            return velocity
        ranges = self.lidar_values()
        if ranges is None:
            return velocity
        ranges = np.asarray(ranges)
        angles = np.asarray(self.lidar_rays_angles())
        static = np.isfinite(ranges) & (ranges > 5) & (ranges < MAX_RANGE_LIDAR_SENSOR - 10)
        endpoints = ranges[:, None] * np.column_stack((np.cos(angles), np.sin(angles)))
        objects = []
        for hit in self.semantic_values() or []:
            if hit.entity_type.name in ("DRONE", "BOMB") and math.isfinite(hit.distance) and math.isfinite(hit.angle):
                point = hit.distance * np.array([math.cos(hit.angle), math.sin(hit.angle)])
                objects.append(point)
                static &= np.linalg.norm(endpoints - point, axis=1) > 25
        if np.any(self.grid.size / 2 - np.abs(self.pose) <= MAX_RANGE_LIDAR_SENSOR - 10):
            lines = scan_lines(ranges, angles, objects, MAX_RANGE_LIDAR_SENSOR - 10)
            shift, yaw, axes = self.boundary_anchor.correct(lines, self.pose, self.heading, self.elapsed_timestep)
            if axes:
                self.pose += shift
                self.heading += yaw
                self.grid.compute_stats["boundary_alignments"] += 1
                self.grid.compute_stats["boundary_two_axes"] += axes == 2
                return velocity
        if self._outage_walls is None:
            return velocity
        reference = self._outage_walls if self.carrying else self.grid.evidence >= 6
        dx, dy, yaw = self.grid.align(self.pose, self.heading, endpoints[static][::2], reference)
        if not self.carrying:
            self.pose += (dx, dy)
            self.heading += yaw
            return velocity
        # A scan from the current outage cannot become its own pose reference.
        # Dampen small fits so a symmetric corridor does not ratchet the pose.
        self.pose += np.clip(.35 * np.array((dx, dy)), -3, 3)
        self.heading += float(np.clip(.35 * yaw, -math.radians(1), math.radians(1)))
        return velocity

    def _sense(self):
        # 无定位/罗盘区依靠里程计续推；有 GPS 时继续复用原来的融合与语义处理。
        gps, compass, odom = self.measured_gps_position(), self.measured_compass_angle(), self.odometer_values()
        self.grid.pose_fixed = gps is not None and compass is not None and np.all(np.isfinite(gps)) and math.isfinite(compass)
        if self.grid.pose_fixed:
            self.grid.last_pose_fix = self.elapsed_timestep
        outage = gps is None and compass is None
        if outage and not self._odometry_only and self.pose is not None:
            self.grid.enable_return_guard()
            self._outage_walls = self.grid.evidence >= 6
        if self._odometry_only and gps is not None and np.all(np.isfinite(gps)):
            self.pose = np.asarray(gps, dtype=float).copy()
            self._outage_walls = None
        self._odometry_only = outage
        velocity = None
        if odom is not None and np.all(np.isfinite(odom)):
            heading = float(compass) if compass is not None else self.heading + float(odom[2])
            angle = heading - float(odom[2]) + float(odom[1])
            velocity = float(odom[0]) * np.array([math.cos(angle), math.sin(angle)])
            if compass is None:
                self.heading = heading
            if gps is None and self.pose is not None:
                self.pose += velocity
        predicted_heading = self.heading
        measured_velocity, hits, depot_hits = super()._sense()
        if measured_velocity is None and velocity is not None:
            yaw = self.heading - predicted_heading
            cosine, sine = math.cos(yaw), math.sin(yaw)
            measured_velocity = np.array([cosine * velocity[0] - sine * velocity[1],
                                          sine * velocity[0] + cosine * velocity[1]])
        return measured_velocity, hits, depot_hits

    def update_cargo(self):
        """统一处理抓取、确认处置和意外脱落，返回载荷是否改变。"""
        carrying = bool(self.grasped_bombs())
        changed = carrying != self.carrying
        if carrying and not self.carrying:
            if self.task not in self.bombs:
                self.task = self._remember(self.pose, self.elapsed_timestep)
            self.bombs[self.task][2:] = [self.elapsed_timestep, 1]
        elif self.carrying and not carrying:
            # A nearby track can still be visible after the held bomb is disposed.
            disposed = self._last_grasper and self.reward > 0
            self.bombs[self.task] = [*self.pose, self.elapsed_timestep, 2 if disposed else 3]
            self.task = None
        self.carrying = carrying
        if carrying:
            self.bombs[self.task] = [*self.pose, self.elapsed_timestep, 1]
        if changed:
            self.velocity_trim[:] = 0
        return changed

    @staticmethod
    def corridor_walls(direction, points):
        """Fit two parallel side walls in the direction of travel."""
        across = np.array([-direction[1], direction[0]])
        along, lateral = points @ direction, points @ across
        flank = (np.abs(along) < 1.65 * np.abs(lateral)) & (np.abs(lateral) > 7) & (np.abs(lateral) < 55)
        walls = []
        slopes = []
        for side in (-1, 1):
            indices = flank & (side * lateral > 0)
            x, y = along[indices], lateral[indices]
            if len(x) < 5 or np.ptp(x) < 17:
                return None
            x0, y0 = x - x.mean(), y - y.mean()
            slope = np.dot(x0, y0) / np.dot(x0, x0)
            if np.sqrt(np.mean((y0 - slope * x0) ** 2)) > 3.15:
                return None
            slopes.append(slope)
            walls.append(points[indices])
        if abs(slopes[0] - slopes[1]) > .18 or abs(sum(slopes)) > 1.5:
            return None
        axis = direction + .5 * sum(slopes) * across
        axis /= np.linalg.norm(axis)
        normal = np.array([-axis[1], axis[0]])
        left, right = (float(np.median(p @ normal)) for p in walls)
        width, offset = right - left, .5 * (left + right)
        if not (34 <= width <= 50 and left < -10 and right > 10):
            return None
        return axis, width, offset

    def corridor_motion(self, delta, ranges, bearings, finite, contact_hits=(), *, backout=False, probe_fit=None):
        direction = delta / np.linalg.norm(delta)
        angles = self.heading + bearings
        rays = np.column_stack((np.cos(angles), np.sin(angles)))
        points = rays[finite] * ranges[finite, None]
        walls = probe_fit if probe_fit is not None else self.corridor_walls(direction, points)
        if walls is None and not backout:
            return None
        axis, width, offset = walls if walls is not None else (direction, 0., 0.)
        normal = np.array([-axis[1], axis[0]])
        depth, side = points @ axis, points @ normal
        # A grazing return near a fitted side wall is not a blockage in the lane.
        half_lane = min(16., width / 2 - 3.5) if backout and walls is not None else 16.
        if probe_fit is not None:
            half_lane = self.grid.HULL_CLEARANCE
        ahead = (depth > 0) & (np.abs(side - offset) < half_lane)
        if probe_fit is not None:
            # Range noise on lateral beams moves returns into the lane.
            # Use the measured side planes to classify those returns.
            wall_error = np.abs(np.abs(side - offset) - width / 2)
            radial_error = 2 + 6 * np.abs(rays[finite] @ normal)
            ahead &= wall_error > radial_error
        for hit in contact_hits:
            if hit.entity_type.name == "BOMB" and not hit.grasped:
                angle = self.heading + hit.angle
                aim = hit.distance * np.array((math.cos(angle), math.sin(angle)))
                same_bomb = ((np.abs(side - aim @ normal) < 15)
                             & (np.abs(depth - aim @ axis) < 17)
                             & (np.abs(side - offset) < width / 2 - 5))
                ahead &= ~same_bomb
        stop = float(depth[ahead].min()) if np.any(ahead) else MAX_RANGE_LIDAR_SENSOR
        margin = 34 if self.carrying else 22
        speed = min(1.65 if backout else 1.35, float(delta @ axis) / 6, max(0., stop - margin) / 7)
        if backout or probe_fit is not None:
            # When the sides open up, continue on the stored axis only with live laser coverage.
            sector = rays @ axis > .87
            if not sector.any() or np.count_nonzero(finite & sector) < .75 * np.count_nonzero(sector):
                speed = 0.
        if probe_fit is not None and width / 2 - abs(offset) < self.grid.HULL_CLEARANCE:
            speed = 0.
        if contact_hits:
            speed = min(speed, .60)
        shift = float(np.clip(.22 * offset, -.50, .50))
        course = math.atan2(axis[1], axis[0])
        turn = (course - self.heading + math.pi / 2) % math.pi - math.pi / 2
        if abs(turn) > .32:
            speed = min(speed, .30)
        return speed * axis + shift * normal, turn, axis if walls is not None else None

    # Own dropped bombs have no drone collision (Bomb.ignore_drone_collisions),
    # but they still intersect the lidar. A drone that is only relaying (no bombs
    # left) must not be braked by the bombs it left behind.
    OWN_BOMB_RADIUS = 12.0
    OWN_BOMB_FILTER_MARGIN = 3.0

    def _own_bomb_returns(self, bearings, ranges):
        """Mask of lidar rays whose world hit lands on this drone's own bombs."""
        own = [np.asarray(p, dtype=float)
               for key, p in self.drop_records.items()
               if int(key[0]) == int(self.identifier)]
        mask = np.zeros(len(ranges), dtype=bool)
        if not own:
            return mask
        finite = np.isfinite(ranges) & (ranges > 0)
        idx = np.where(finite)[0]
        if idx.size == 0:
            return mask
        px, py = self.pose
        world_ang = float(self.heading) + np.asarray(bearings)[idx]
        hits = np.column_stack((px + ranges[idx] * np.cos(world_ang),
                                py + ranges[idx] * np.sin(world_ang)))
        limit = self.OWN_BOMB_RADIUS + self.OWN_BOMB_FILTER_MARGIN
        for bp in own:
            inside = np.linalg.norm(hits - bp, axis=1) <= limit
            mask[idx[inside]] = True
        return mask

    def drive(self, goal, velocity, contact_hits=(), grasp=False, *, backout=False,
              ignore_own_bombs=False):
        """目标速度 + 制动反馈；同一函数用于探索、取送和等待制动。"""
        delta = np.asarray(goal) - self.pose
        length = float(np.linalg.norm(delta))
        ranges = self.lidar_values()
        desired = np.zeros(2)
        self.corridor_axis = None
        tight = self.grid.needs_alignment(self.pose, goal, self.carrying)
        if ranges is not None and length > 5:
            bearings = np.asarray(self.lidar_rays_angles())
            ranges = np.asarray(ranges, dtype=float).copy()
            finite = np.isfinite(ranges)
            for contact_hit in contact_hits:
                angular_gap = np.abs((bearings - contact_hit.angle + math.pi) % (2 * math.pi) - math.pi)
                finite &= ~((angular_gap < 0.13) & (np.abs(ranges - contact_hit.distance) < 18))
            if ignore_own_bombs:
                own_hits = self._own_bomb_returns(bearings, ranges)
                ranges[own_hits] = np.nan
                finite &= ~own_hits
            if tight or contact_hits or backout:
                corridor = self.corridor_motion(delta, ranges, bearings, finite, contact_hits if grasp else (),
                                                backout=backout)
                if corridor is not None:
                    desired, turn, self.corridor_axis = corridor
                    return self.motion_command(desired, velocity, turn, .18, grasp, 3.7)
            angles = self.heading + np.linspace(-math.pi, math.pi, 49)
            differences = angles[:, None] - self.heading - bearings[None, :]
            projection = ranges[None, :] * np.cos(differences)
            lateral = ranges[None, :] * np.sin(differences)
            braking = 34 if self.carrying else 22
            radius = self.grid.HULL_CLEARANCE if tight else braking
            obstacles = finite[None, :] & (projection > 0) & (np.abs(lateral) < radius)
            clearance = np.min(np.where(obstacles, projection, MAX_RANGE_LIDAR_SENSOR), axis=1)
            cruise = ((2.2 if self.carrying else 2.8) if tight
                      else (2.5 if self.carrying else 4.0) * self.grid.speed_scale)
            speeds = np.minimum(cruise, np.maximum(0, (clearance - braking) / 6))
            speeds = np.minimum(speeds, length / 6)
            vectors = speeds[:, None] * np.column_stack((np.cos(angles), np.sin(angles)))
            values = vectors @ (delta / length)
            desired = vectors[int(np.argmax(values))]
            if tight and float(np.max(values)) < .1:
                # A wall alongside the hull must not prohibit tangential motion.
                # Permit a short sweep only if it preserves every observed clearance.
                offsets = np.clip(projection, 0, 3.6)
                gaps = np.hypot(lateral, projection - offsets)
                floor = np.minimum(ranges, radius) - .15
                safe = np.all(~finite[None, :] | (gaps >= floor), axis=1)
                scores = np.where(safe, np.cos(angles - math.atan2(delta[1], delta[0])), 0.)
                k = int(np.argmax(scores))
                if scores[k] > .2:
                    desired = min(.6, length / 6) * np.array((math.cos(angles[k]), math.sin(angles[k])))
            elif (contact_hits or self.carrying) and self.grid.speed_scale > 1 and float(np.max(values)) < .1:
                # Movable free bombs need the drone body, not the full rotating
                # cargo safety disk, during a slow final contact approach.
                movable = np.zeros(len(ranges), dtype=bool)
                for hit in self.semantic_values() or []:
                    if (getattr(hit.entity_type, "name", None) != "BOMB" or hit.grasped
                            or not 0 < hit.distance < 80):
                        continue
                    gap = np.abs((bearings - hit.angle + math.pi) % (2 * math.pi) - math.pi)
                    movable |= (gap < .13) & (np.abs(ranges - hit.distance) < 18)
                radii = np.where(movable, 14., radius)
                close = finite[None, :] & (projection > 0) & (np.abs(lateral) < radii)
                margin = np.min(np.where(close, projection - radii, MAX_RANGE_LIDAR_SENSOR), axis=1)
                slow = np.minimum(.5, np.maximum(0, margin / 6))
                slow = np.minimum(slow, length / 6)
                creep = slow[:, None] * np.column_stack((np.cos(angles), np.sin(angles)))
                progress = creep @ (delta / length)
                if float(np.max(progress)) > float(np.max(values)):
                    desired = creep[int(np.argmax(progress))]
        turn = (math.atan2(delta[1], delta[0]) - self.heading + math.pi) % (2 * math.pi) - math.pi
        turn_limit = .2 if tight and self.carrying else .6
        return self.motion_command(desired, velocity, turn if length > 5 and not backout else 0., turn_limit, grasp)

    def motion_command(self, desired, velocity, turn, turn_limit, grasp, empty_damping=5.5):
        velocity = np.zeros(2) if velocity is None else velocity
        error = desired - velocity
        if self.carrying:
            # 炸弹抓持后仍有驱动力；积分项补偿持续扰动，避免带载速度长期偏低。
            self.velocity_trim = np.clip(self.velocity_trim + .02 * error, -.45, .45)
            force = error / 2.5 + self.velocity_trim
        else:
            self.velocity_trim[:] = 0
            force = error / empty_damping
        cosine, sine = math.cos(self.heading), math.sin(self.heading)
        return {"forward": float(np.clip(force[0] * cosine + force[1] * sine, -1, 1)),
                "lateral": float(np.clip(-force[0] * sine + force[1] * cosine, -1, 1)),
                "rotation": float(np.clip(turn, -turn_limit, turn_limit)),
                "grasper": int(self.carrying or grasp)}


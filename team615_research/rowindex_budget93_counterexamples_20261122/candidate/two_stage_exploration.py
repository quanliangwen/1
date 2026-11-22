"""二维 RACER/FUEL 式探索：观测覆盖、工作量分区和开放式 LKH 排序。"""

import math
from dataclasses import dataclass, field

import elkai
import numpy as np
from scipy.ndimage import binary_dilation, label, uniform_filter

from swarm_rescue.simulation.utils.constants import MAX_RANGE_SEMANTIC_SENSOR
from swarm_rescue.solutions.rescue_shared import ObservedGrid, distance


@dataclass(frozen=True)
class SearchHandoff:
    version: tuple[int, int]  # Original owner and step of its map snapshot.
    recipient: int
    cells: frozenset
    entrance: tuple[int, int]
    expires: int
    resume_at: int


@dataclass
class SearchTask:
    cells: frozenset
    point: tuple
    started: int
    progress: int
    covered: int = 0
    remaining: float = math.inf
    motion: tuple | None = None
    misses: int = 0
    checked: set = field(default_factory=set)
    handoff: tuple[int, int] | None = None
    handoff_scanned: bool = False
    return_check_until: int = 0


class ExplorationGrid(ObservedGrid):
    SEMANTIC_RAYS = np.linspace(-math.pi, math.pi, 35)
    CLOSE_SCAN = 95
    OPENING_TILE = 6

    def __init__(self, size):
        super().__init__(size)
        # 0 unseen, 1 distant beam, 2 near beam. Same byte per cell on the radio.
        self.searched = np.zeros(self.evidence.shape, dtype=np.uint8)
        self.searched_here = np.zeros_like(self.searched)
        self.last_scan_cells = ()
        self.capture_scan_cells = False
        self._search_clearance = None
        self._close_scan = np.zeros(self.evidence.shape, dtype=bool)
        rows, cols = np.indices(self.evidence.shape)
        self.centres = np.stack((cols + .5, rows + .5), axis=-1) * self.CELL - self.size / 2

    def responsibility_regions(self, count):
        """Tile the task boundary into near-equal areas labeled by drone ID."""
        rows, cols = self.evidence.shape
        bands = min(count, max(1, round(math.sqrt(count * rows / cols))))
        per_band, extra = divmod(count, bands)
        regions = np.empty((rows, cols), dtype=int)
        columns = np.arange(cols)
        first = 0
        for band in range(bands):
            regions_in_band = per_band + (band < extra)
            end = first + regions_in_band
            low, high = round(rows * first / count), round(rows * end / count)
            regions[low:high] = first + columns * regions_in_band // cols
            first = end
        return regions

    def configure_opening(self, count):
        owners = self.responsibility_regions(count)
        rows, cols = np.indices(owners.shape)
        width = self.OPENING_TILE
        coarse = (rows // width) * math.ceil(owners.shape[1] / width) + cols // width
        self._opening_coarse = coarse * count + owners
        self._opening_child = 1 + 2 * (rows % width >= width // 2) + (cols % width >= width // 2)
        self._opening_size = np.bincount(self._opening_coarse.ravel())
        self._opening_split = np.zeros(len(self._opening_size), dtype=bool)
        return owners

    def opening_tiles(self):
        """Refine each tile once its own settled area reaches half the tile."""
        settled = (self.evidence >= 3) | ((self.evidence < 0) & (self.searched > self.close_scan_cells()))
        count = np.bincount(self._opening_coarse[settled], minlength=len(self._opening_size))
        new = (~self._opening_split) & (self._opening_size > 0) & (2 * count >= self._opening_size)
        self._opening_split |= new
        self.compute_stats["opening_tiles_refined"] += int(np.count_nonzero(new))
        return 5 * self._opening_coarse + self._opening_child * self._opening_split[self._opening_coarse]

    def close_scan_cells(self):
        """A far beam at a grid centre does not finish a blind recess."""
        if self.speed_scale == 1 and self._search_clearance is not self.clearance and self._topology is not None:
            walls = self._topology[0]
            between = np.zeros_like(walls)
            for axis in (0, 1):
                side = walls.swapaxes(0, axis)
                before, after = np.zeros_like(side), np.zeros_like(side)
                for offset in (1, 2, 3):
                    before[offset:] |= side[:-offset]
                    after[:-offset] |= side[offset:]
                between.swapaxes(0, axis)[:] |= before & after
            self._close_scan = (binary_dilation(between & ~walls)
                                & (self.clearance <= 45) & ~walls)
            self._search_clearance = self.clearance
        return self._close_scan

    def local_coverage(self, cells):
        close = self.close_scan_cells()
        return sum(self.searched_here[c] > int(close[c]) for c in cells)

    @staticmethod
    def sweep_target(block, options):
        """Visit reachable cells in alternating directions across the search block."""
        rows, columns = zip(*block)
        along = 0 if max(rows) - min(rows) > max(columns) - min(columns) else 1
        across = 1 - along
        strips = sorted({cell[across] for cell in block})
        strip_index = {strip: i for i, strip in enumerate(strips)}

        def sweep_order(cell):
            index = strip_index[cell[across]]
            direction = 1 if index % 2 == 0 else -1
            return index, direction * cell[along]

        return min(options, key=sweep_order)

    def observe_semantics(self, position, heading, ranges, bearings):
        """按语义射线的实际方向记录搜索覆盖，并用激光距离处理墙遮挡。"""
        delta = self.centres - position
        radius = np.linalg.norm(delta, axis=-1)
        near = (self.speed_scale == 1) & (radius < self.CLOSE_SCAN)
        scan_radius = MAX_RANGE_SEMANTIC_SENSOR - 10
        update = (self.searched == 0) | (near & (self.searched < 2))
        selected = (radius < scan_radius) & (True if self.capture_scan_cells else update)
        if not selected.any():
            self.last_scan_cells = ()
            return
        delta = delta[selected]
        radius = radius[selected]
        angle = (np.arctan2(delta[..., 1], delta[..., 0]) - heading + math.pi) % (2 * math.pi) - math.pi
        rays = self.SEMANTIC_RAYS
        if self.speed_scale == 1:
            nearest = np.rint((angle + math.pi) / (rays[1] - rays[0])).astype(int)
        else:
            nearest = np.abs((angle[..., None] - rays + math.pi) % (2 * math.pi) - math.pi).argmin(axis=-1)
        gap = (angle - rays[nearest] + math.pi) % (2 * math.pi) - math.pi
        limits = np.interp(rays, bearings, np.nan_to_num(ranges, nan=0))
        covered = ((radius < np.minimum(scan_radius, limits[nearest] - 12))
                   & (radius * np.abs(np.sin(gap)) < 12))
        level = covered * (1 + near[selected])
        if self.capture_scan_cells:
            self.last_scan_cells = tuple(map(tuple, np.argwhere(selected)[covered].tolist()))
        old_update = update[selected]
        self.searched[selected] = np.maximum(self.searched[selected], level * old_update)
        self.searched_here[selected] = np.maximum(self.searched_here[selected], level * old_update)

    def search_work(self, start):
        costs, _ = self.tree(start)
        reachable = np.zeros(self.evidence.shape, dtype=bool)
        for cell in costs:
            reachable[cell] = True
        # 看过但证据仍不确定的格子也需要复查，否则会形成没有前沿的断路。
        unknown = (self.evidence >= 0) & (self.evidence < 3) & ~self.blocked
        work = binary_dilation(unknown) | (self.searched <= self.close_scan_cells())
        # 已领取区域不再可达时，尚未搜索的部分仍然待处理。
        pending = (self.evidence < 3) & (work | (self.evidence >= 0))
        return costs, work & reachable, pending

    def target_blocks(self, work, partitions=None):
        regions, count = label(work, np.ones((3, 3)))
        points = []
        # 大前沿分成 120 px 区域，收尾时细分为 60 px。
        width = 6 if np.count_nonzero(work) > 80 else 3
        for region in range(1, count + 1):
            cells = np.argwhere(regions == region)
            blocks = cells // width if partitions is None else partitions[tuple(cells.T)][:, None]
            for block in np.unique(blocks, axis=0):
                members = cells[np.all(blocks == block, axis=1)]
                centre = members.mean(axis=0)
                cell = min(map(tuple, members), key=lambda c: np.linalg.norm(np.array(c) - centre))
                point = tuple(self.point(cell))
                if any(distance(point, p) < 40 and (self.speed_scale > 1 or self.visible(point, p)) for p in points):
                    continue
                points.append(point)
                yield point, members

    def targets(self, start):
        blocks = list(self.target_blocks(self.search_work(start)[1]))
        return [point for point, _ in blocks], [float(len(cells)) for _, cells in blocks]

    def frontier_gain(self):
        unknown = (self.evidence == 0) & ~self.blocked
        return uniform_filter(unknown.astype(np.float32), size=7) * binary_dilation(unknown)


def open_tour(grid, start, points):
    """虚拟回程代价为零，将开放访问序列交给 LKH 的 ATSP 接口。"""
    if len(points) < 2:
        return list(points)
    nodes = [tuple(start), *points]
    matrix = np.zeros((len(nodes), len(nodes)), dtype=int)
    for i, point in enumerate(nodes):
        costs, _ = grid.tree(point)
        for j in range(1, len(nodes)):
            if i != j:
                matrix[i, j] = max(1, math.ceil(costs.get(grid.cell(nodes[j]), 1_000_000)))
    order = elkai.DistanceMatrix(matrix.tolist()).solve_tsp(runs=1)
    return [nodes[i] for i in order if i != 0]


def allocate_regions(grid, agents, points, weights, preferred_owners=None):
    """容量表示搜索工作量；先插入，再在无人机对之间迁移区域。"""
    ids = sorted(agents)
    routes = {i: [] for i in ids}
    loads = {i: 0.0 for i in ids}
    if not points:
        return routes
    capacity = max(max(weights), 1.35 * sum(weights) / len(ids))
    travel = {i: grid.tree(agents[i])[0] for i in ids}
    point_cells = [grid.cell(p) for p in points]

    def cost(i, k):
        if preferred_owners is None:
            return travel[i].get(point_cells[k], 1_000_000)
        # Credit the initial owner by one 120 px search-block width.
        return travel[i].get(point_cells[k], math.inf) + grid.OPENING_TILE * grid.CELL * (i != preferred_owners[k])

    for k in sorted(range(len(points)), key=lambda k: -weights[k]):
        reachable = ids if preferred_owners is None else [i for i in ids if point_cells[k] in travel[i]]
        if not reachable:
            continue
        available = [i for i in reachable if loads[i] + weights[k] <= capacity] or reachable
        owner = min(available, key=lambda i: cost(i, k) + 15 * loads[i])
        routes[owner].append(k)
        loads[owner] += weights[k]
    # 两机交换共享同一代价函数，不另写一套分配逻辑。
    for i in ids:
        for j in ids:
            if i == j:
                continue
            for k in routes[i][:]:
                if loads[j] + weights[k] <= capacity and cost(j, k) + 15 * loads[j] < cost(i, k) + 15 * (loads[i] - weights[k]):
                    routes[i].remove(k)
                    routes[j].append(k)
                    loads[i] -= weights[k]
                    loads[j] += weights[k]
    return {i: [points[k] for k in routes[i]] for i in ids}

"""带加减速原语的安全区间搜索；所有时间均为仿真步。

原语从静止出发并在终点制动，等待只发生在静止状态。这是 SIPP-IP 思路的
保守实现，没有复现论文中完整的速度区间投影。预约覆盖整段扫掠区域。
"""

import heapq
import math
import time
from collections import defaultdict

import numpy as np

from swarm_rescue.simulation.reporting.score_manager import ScoreManager
from swarm_rescue.simulation.utils.constants import DRONE_INITIAL_HEALTH
from swarm_rescue.solutions.rescue_shared import distance


def move_time(length, loaded=False, scale=1.0):
    speed, acceleration = (2.5, .35) if loaded else (4.0, .5)
    speed *= scale
    ramp = speed * speed / acceleration
    return math.ceil(2 * math.sqrt(length / acceleration) if length < ramp else length / speed + speed / acceleration)


def merge_intervals(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


class Reservations:
    def __init__(self, grid, horizon):
        self.grid, self.horizon = grid, horizon
        self.cells = defaultdict(list)
        self._safe = {}
        self._sweeps = {}
        self._occupied = {}
        self._prefixes = {}

    def sweep(self, a, b, radius=0):
        key = tuple(a), tuple(b), radius
        if key in self._sweeps:
            return self._sweeps[key]
        count = max(1, math.ceil(distance(a, b) / 10))
        cells = {self.grid.cell((a[0] + (b[0] - a[0]) * k / count, a[1] + (b[1] - a[1]) * k / count))
                 for k in range(count + 1)}
        if not radius:
            self._sweeps[key] = cells
            return cells
        size = math.ceil(radius / self.grid.CELL)
        return {(r + dr, c + dc) for r, c in cells
                for dr in range(-size, size + 1) for dc in range(-size, size + 1)
                if math.hypot(dr, dc) * self.grid.CELL <= radius + 10}

    def add(self, path, park_until=None, separation=58):
        if not path:
            return
        path = list(path)
        if park_until is not None and park_until > path[-1][0]:
            path.append((park_until, *path[-1][1:]))
        for a, b in zip(path, path[1:]):
            for cell in self.sweep(a[1:], b[1:], separation):
                self.cells[cell].append((a[0] - 2, b[0] + 2))
        self._safe.clear()
        self._occupied.clear()
        self._prefixes.clear()

    def safe(self, cell):
        if cell not in self._safe:
            result, now = [], 0
            for start, end in merge_intervals(self.cells[cell]):
                if start > now:
                    result.append((now, min(start, self.horizon)))
                now = max(now, end)
            if now < self.horizon:
                result.append((now, self.horizon))
            self._safe[cell] = result
        return self._safe[cell]

    def departure(self, a, b, earliest, latest, duration):
        key = tuple(a), tuple(b)
        if key not in self._occupied:
            self._occupied[key] = merge_intervals([period for c in self.sweep(a, b) for period in self.cells[c]])
        occupied = self._occupied[key]
        departure = earliest
        for start, end in occupied:
            if departure + duration <= start:
                break
            if departure < end and departure + duration > start:
                departure = end
        return departure if departure <= latest else None


def route_waypoints(start, route, limit=60):
    """沿空间路径合并同向栅格，保留转角并限制运动段长度。"""
    result = [tuple(start)]
    previous = None
    for a, b in zip(route, route[1:]):
        direction = (round(b[0] - a[0]), round(b[1] - a[1]))
        if previous is not None and direction != previous and distance(result[-1], a) > 1:
            result.append(tuple(a))
        if distance(result[-1], b) >= limit:
            result.append(tuple(b))
        previous = direction
    if route and distance(result[-1], route[-1]) > 1:
        result.append(tuple(route[-1]))
    return result


def time_route(grid, start, spatial, now, reservations, loaded=False, hold=12, *, narrow=False):
    """先给已有空间路径安排安全的出发时刻，提供不依赖二维搜索的可行解。"""
    result, at = [(now, *start)], now
    stride = grid.CELL if narrow else (120 if loaded and grid.speed_scale > 1 else 60)
    for end in route_waypoints(start, spatial, stride)[1:]:
        point = result[-1][1:]
        source = next((b for a, b in reservations.safe(grid.cell(point)) if a <= at < b), None)
        if source is None:
            return ()
        duration = move_time(distance(point, end), loaded, grid.speed_scale)
        departure = None
        for lo, hi in reservations.safe(grid.cell(end)):
            departure = reservations.departure(point, end, max(at, lo), min(source, hi) - duration, duration)
            if departure is not None:
                break
        if departure is None:
            return ()
        if departure > at:
            result.append((departure, *point))
        at = departure + duration
        result.append((at, *end))
    if not any(a <= at and at + hold <= b for a, b in reservations.safe(grid.cell(result[-1][1:]))):
        return ()
    result.append((at + hold, *result[-1][1:]))
    return tuple(result)


def safe_path(grid, start, goal, now, reservations, loaded=False, hold=12, seconds=.04, compare=False):
    """在 (栅格, 安全区间) 上搜索；长直线原语减少逐格停车。"""
    # 每个原语终点停车；需要更快的连续通行时再实现完整速度区间投影。
    begun = time.perf_counter() if compare else None
    spatial = grid.route(start, goal, loaded=loaded, contact=True)
    if not spatial:
        return ()
    incumbent = time_route(grid, start, spatial, now, reservations, loaded, hold)
    waiting = (sum(b[0] - a[0] for a, b in zip(incumbent, incumbent[1:])
                   if distance(a[1:], b[1:]) < 1) - hold) if incumbent and compare else 0
    refine = bool(incumbent and compare and waiting > 60)
    if incumbent and not refine:
        return incumbent
    expanded = 0
    if refine:
        stats = grid.compute_stats
        stats["bypass_checks"] += 1
        unit = move_time(grid.CELL, loaded, grid.speed_scale)
        triple = move_time(3 * grid.CELL, loaded, grid.speed_scale)

        def finish(path):
            gain = incumbent[-1][0] - path[-1][0]
            stats["bypass_nodes"] += expanded
            stats["bypass_wins"] += gain > 0
            stats["bypass_kept"] += gain == 0
            stats["bypass_step_gain"] += gain
            elapsed = time.perf_counter() - begun
            stats["bypass_seconds"] += elapsed
            stats["bypass_max_seconds"] = max(stats["bypass_max_seconds"], elapsed)
            return path

        if time.perf_counter() >= begun + seconds:
            stats["bypass_budget_exhausted"] += 1
            return finish(incumbent)
    target = grid.cell(spatial[-1])
    source = grid.cell(start)
    intervals = reservations.safe(source)
    interval = next((i for i, (a, b) in enumerate(intervals) if a <= now < b), None)
    if interval is None:
        return finish(incumbent) if refine else ()
    walkable = grid.walkable(loaded).copy()
    walkable[source] = True
    root = (source, interval)
    queue, arrival, parent = [(now, now, root)], {root: now}, {}
    deadline = begun + seconds if refine else time.perf_counter() + seconds
    while queue and time.perf_counter() < deadline:
        bound, at, state = heapq.heappop(queue)
        if at != arrival[state]:
            continue
        if refine:
            if bound + hold >= incumbent[-1][0]:
                break
            expanded += 1
        cell, index = state
        point = tuple(start) if state == root else tuple(grid.point(cell))
        if cell == target and at + hold <= reservations.safe(cell)[index][1]:
            chain, current = [], state
            while current != root:
                previous, departure = parent[current]
                chain.append((current, previous, departure))
                current = previous
            result = [(now, *start)]
            for current, previous, departure in reversed(chain):
                if departure > result[-1][0]:
                    result.append((departure, *result[-1][1:]))
                result.append((arrival[current], *grid.point(current[0])))
            result.append((at + hold, *result[-1][1:]))
            candidate = tuple(result)
            return finish(candidate if candidate[-1][0] < incumbent[-1][0] else incumbent) if refine else candidate
        upper = reservations.safe(cell)[index][1]
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            for length in (1, 3):
                other = cell[0] + length * dr, cell[1] + length * dc
                if not (0 <= other[0] < walkable.shape[0] and 0 <= other[1] < walkable.shape[1]):
                    continue
                valid = all(walkable[cell[0] + step * dr, cell[1] + step * dc]
                            and (not dr or not dc or (walkable[cell[0] + (step - 1) * dr, cell[1] + step * dc]
                                                     and walkable[cell[0] + step * dr, cell[1] + (step - 1) * dc]))
                            for step in range(1, length + 1))
                if not valid:
                    continue
                end = tuple(grid.point(other))
                duration = move_time(distance(point, end), loaded, grid.speed_scale)
                for j, (lo, hi) in enumerate(reservations.safe(other)):
                    earliest = max(at, lo)
                    latest = min(upper, hi) - duration
                    if earliest > latest:
                        continue
                    departure = reservations.departure(point, end, earliest, latest, duration)
                    if departure is None:
                        continue
                    reached, next_state = departure + duration, (other, j)
                    if reached < arrival.get(next_state, math.inf):
                        estimate = move_time(distance(end, grid.point(target)), loaded, grid.speed_scale)
                        if refine:
                            axes = (abs(other[0] - target[0]), abs(other[1] - target[1]))
                            estimate = max(estimate, *(n // 3 * triple + n % 3 * unit for n in axes))
                            if reached + estimate + hold >= incumbent[-1][0]:
                                continue
                        arrival[next_state], parent[next_state] = reached, (state, departure)
                        heapq.heappush(queue, (reached + estimate, reached, next_state))
    if refine:
        if queue and time.perf_counter() >= deadline:
            stats["bypass_budget_exhausted"] += 1
        return finish(incumbent)
    return ()


def progress_path(state, now, scale=1.0):
    """从最近报告的实际机位重建未执行预约，并传播迟到量。"""
    point = tuple(state["point"])
    path = state.get("path", ())
    index = min(max(1, state.get("path_index", 1)), len(path))
    stamp = state["step"]
    if not path or index >= len(path) or now - stamp > 30:
        return ((now, *point), (now + 20, *point))
    target = path[index]
    remaining = move_time(distance(point, target[1:]), state["held"] is not None, scale)
    # A reported wait retains its release time. Lateness propagates to every successor.
    reach = max(target[0], now + remaining)
    shift = reach - target[0]
    result = [(now, *point), (reach, *target[1:])]
    result.extend((p[0] + shift, *p[1:]) for p in path[index + 1:])
    return tuple(result)


def predicted_score(done, total, health, drones, finish, limit):
    scorer = ScoreManager(drones, limit, None, max(1, total))
    return scorer.compute_score(done, 0, 100 * health / (DRONE_INITIAL_HEALTH * drones), finish)[0]

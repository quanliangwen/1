"""容量为 1 的取送调度：后悔值插入、LNS 和统一的预约路径评价。"""

import math
from collections import Counter
import random
import time
from dataclasses import dataclass

import numpy as np

from swarm_rescue.solutions.rescue_shared import distance
from swarm_rescue.solutions.two_stage_paths import Reservations, move_time, safe_path, time_route, predicted_score


@dataclass(frozen=True)
class Agent:
    identifier: int
    point: tuple
    health: float
    held: tuple | None = None
    blocked: tuple = ()
    committed: bool = False


@dataclass
class DispatchPlan:
    sequences: dict
    legs: dict
    finishes: dict
    score: float

    def paths(self):
        return {i: tuple(p for _, _, path in legs for p in path) for i, legs in self.legs.items()}

    def quality(self):
        return self.score, len(self.finishes), -max(self.finishes.values(), default=0), -sum(self.finishes.values())


def traffic_priority(identifier, point, loaded, home):
    """携雷优先；距中心更近的返程机先走，避免前车给后车让路。"""
    return not loaded, distance(point, home) if loaded else 0, identifier


def parking_point(grid, anchor, identifier, count, radius=100, start=None):
    angle = 2 * math.pi * identifier / count
    wanted = (anchor[0] + radius * math.cos(angle), anchor[1] + radius * math.sin(angle))
    reachable = grid.tree(start)[0] if start is not None else None
    candidates = [tuple(c) for c in np.argwhere((grid.evidence < 0) & (grid.clearance >= 40))
                  if max(60, radius - 40) <= distance(grid.point(c), anchor) <= max(220, radius + 80)
                  and (reachable is None or tuple(c) in reachable)]
    return tuple(grid.point(min(candidates, key=lambda c: distance(grid.point(c), wanted)))) if candidates else tuple(start if start is not None else anchor)


class Dispatcher:
    def __init__(self, grid, home, limit, drones, seed=17):
        self.grid, self.home, self.limit, self.drones = grid, home, limit, drones
        self.rng = random.Random(seed)
        self.routes = {}
        self._segments = {}
        self.statistics = {}
        if not hasattr(grid, "compute_stats"):
            grid.compute_stats = Counter()

    def route(self, a, b, loaded):
        key = self.grid.cell(a), self.grid.cell(b), loaded
        if key not in self.routes:
            raw = self.grid.route(a, b, loaded=loaded, contact=True)
            points = list(raw[:1])
            previous = None
            for first, second in zip(raw, raw[1:]):
                direction = (round(second[0] - first[0]), round(second[1] - first[1]))
                if previous is not None and direction != previous:
                    points.append(first)
                previous = direction
            if raw:
                points.append(raw[-1])
            self.routes[key] = tuple(points)
        return self.routes[key]

    def stops(self, agent, key, tasks):
        delivery = ("deliver", self.home, True)
        if key == agent.held:
            return [delivery]
        if key in agent.blocked:
            return None
        approach = self.grid.tree(agent.point)[0]
        transport = self.grid.tree_cells(self.grid.contact_cells(self.home, 75), loaded=True)[0]
        cells = [c for c in self.grid.contact_cells(tasks[key][:2]) if c in approach and c in transport]
        if not cells:
            return None
        cell = min(cells, key=lambda c: approach[c] / 4 + transport[c] / 2.5)
        return [("pickup", tuple(self.grid.point(cell)), False), delivery]

    def estimate(self, agent, sequence, tasks, now, reservations):
        # Each reservation table owns its prefix cache; add() invalidates it.
        context = (agent, now, id(self.grid._topology), tuple(self.home), self.limit)
        cache = reservations._prefixes.setdefault(context, {})
        keys, prefix = [()], ()
        for k in sequence:
            prefix += ((k, tuple(tasks[k][:2])),)
            keys.append(prefix)
        begin = len(sequence)
        while begin and keys[begin] not in cache:
            begin -= 1
        if begin:
            point, finish, saved = cache[keys[begin]]
            if not math.isfinite(finish):
                return math.inf, ()
            trajectory = list(saved)
            self.grid.compute_stats['prefix_hits'] += 1
            self.grid.compute_stats['prefix_tasks_skipped'] += begin
        else:
            point, finish = agent.point, now
            trajectory = [(now, *point)]
        for index in range(begin, len(sequence)):
            k = sequence[index]
            stops = self.stops(agent, k, tasks)
            if stops is None:
                cache[keys[index + 1]] = point, math.inf, ()
                return math.inf, ()
            for _, goal, loaded in stops:
                route = self.route(point, goal, loaded)
                if not route:
                    cache[keys[index + 1]] = point, math.inf, ()
                    return math.inf, ()
                segment_key = route, loaded
                if segment_key not in self._segments:
                    self._segments[segment_key] = tuple((a, b, move_time(distance(a, b), loaded, self.grid.speed_scale))
                                                        for a, b in zip(route, route[1:]))
                    self.grid.compute_stats['segment_builds'] += 1
                else:
                    self.grid.compute_stats['segment_hits'] += 1
                for a, b, duration in self._segments[segment_key]:
                    departure = reservations.departure(a, b, finish, self.limit - duration, duration)
                    if departure is None:
                        cache[keys[index + 1]] = point, math.inf, ()
                        return math.inf, ()
                    if departure > finish:
                        trajectory.append((departure, *a))
                    finish = departure + duration
                    trajectory.append((finish, *b))
                finish += 12
                point = route[-1]
                trajectory.append((finish, *point))
            cache[keys[index + 1]] = point, finish, tuple(trajectory)
        return finish, tuple(trajectory)

    def trip(self, agent, key, tasks, now, reservations, deadline=math.inf):
        """完整取送计划；None 表示通路尚未建立，空元组表示当前时限不满足。"""
        stops = self.stops(agent, key, tasks)
        if stops is None:
            return None
        point, at, legs = agent.point, now, []
        traffic = any(reservations.cells.values())
        for mode, goal, loaded in stops:
            if time.perf_counter() >= deadline:
                return ()
            if traffic:
                path = safe_path(self.grid, point, goal, at, reservations, loaded,
                                 seconds=min(.035, max(.001, deadline - time.perf_counter())))
            else:
                spatial = self.grid.route(point, goal, loaded=loaded, contact=True)
                if not spatial:
                    return None
                path = time_route(self.grid, point, spatial, at, reservations, loaded)
            if not path or path[-1][0] > self.limit:
                return ()
            legs.append((mode, key, path))
            at, point = path[-1][0], path[-1][1:]
        return tuple(legs)

    def insert(self, agents, tasks, sequences, pending, now, reservations, deadline=math.inf):
        """同一插入函数同时用于初始构造和 LNS 修复。"""
        sequences = {i: list(route) for i, route in sequences.items()}
        pending = set(pending)
        predicted = {i: self.estimate(a, sequences[i], tasks, now, reservations) for i, a in agents.items()}
        while pending and time.perf_counter() < deadline:
            traffic, estimates = {}, {}
            for i, agent in agents.items():
                table = Reservations(self.grid, self.limit)
                table.cells.update({c: list(periods) for c, periods in reservations.cells.items()})
                for j, (_, path) in predicted.items():
                    if j != i:
                        table.add(path)
                traffic[i] = table
                estimates[i] = self.estimate(agent, sequences[i], tasks, now, table)[0]
            choices = []
            for k in sorted(pending):
                if time.perf_counter() >= deadline:
                    break
                options = []
                for i, agent in agents.items():
                    first = int(agent.held is not None)
                    for index in range(first, len(sequences[i]) + 1):
                        trial = sequences[i][:index] + [k] + sequences[i][index:]
                        finish = self.estimate(agent, trial, tasks, now, traffic[i])[0]
                        cost = finish - estimates[i] + .3 * max(0, finish - max(estimates.values()))
                        if math.isfinite(cost):
                            options.append((cost, i, index, finish))
                if options:
                    options.sort()
                    regret = options[1][0] - options[0][0] if len(options) > 1 else 1_000_000
                    choices.append((regret, -options[0][0], k, options[0]))
            if not choices:
                break
            _, _, k, (_, owner, index, finish) = max(choices)
            sequences[owner].insert(index, k)
            predicted[owner] = self.estimate(agents[owner], sequences[owner], tasks, now, reservations)
            pending.remove(k)
        return sequences

    def schedule(self, agents, tasks, sequences, now, done, total, fixed=(), order=None, deadline=math.inf, reuse=None, affected=()):
        order = order or sorted(agents, key=lambda i: traffic_priority(i, agents[i].point, agents[i].held is not None, self.home))
        legs, finishes = {i: [] for i in agents}, {}
        committed = {}
        frozen = set()
        if reuse is not None:
            for i in agents:
                if (i not in affected and tuple(sequences[i]) == reuse.sequences[i]
                        and reuse.legs[i] and all(k in reuse.finishes for k in sequences[i])):
                    legs[i] = list(reuse.legs[i])
                    committed[i] = tuple(p for _, _, path in legs[i] for p in path)
                    finishes.update({k: reuse.finishes[k] for k in sequences[i]})
                    frozen.add(i)
        self.grid.compute_stats['schedule_calls'] += 1
        self.grid.compute_stats['schedule_agents'] += len(agents) - len(frozen)
        self.grid.compute_stats['schedule_frozen_agents'] += len(frozen)
        for i in order:
            if i in frozen:
                continue
            reservations = Reservations(self.grid, self.limit)
            for path in (*fixed, *committed.values()):
                reservations.add(path, park_until=self.limit)
            # 尚未获得路径的无人机按停放处理；规划失败也不会使它从场景中消失。
            for j, other in agents.items():
                if j != i and j not in committed:
                    end = now + 20 if sequences[j] else self.limit
                    reservations.add(((now, *other.point), (end, *other.point)))
            agent, point, at = agents[i], agents[i].point, now
            for k in sequences[i]:
                task_legs = self.stops(agent, k, tasks)
                if task_legs is None:
                    break
                planned = []
                for mode, goal, loaded in task_legs:
                    if time.perf_counter() >= deadline:
                        break
                    path = safe_path(self.grid, point, goal, at, reservations, loaded,
                                     seconds=min(.035, max(.001, deadline - time.perf_counter())))
                    if not path:
                        break
                    planned.append((mode, k, path))
                    at, point = path[-1][0], path[-1][1:]
                if len(planned) != len(task_legs):
                    break
                legs[i].extend(planned)
                finishes[k] = at
            path = tuple(p for _, _, segment in legs[i] for p in segment)
            if path:
                park = parking_point(self.grid, self.home, i, self.drones, radius=220, start=point)
                departure = safe_path(self.grid, point, park, at, reservations, seconds=.015)
                if departure:
                    legs[i].append(("park", None, departure))
                    path += departure
                committed[i] = path
        if frozen:
            stationary = Reservations(self.grid, self.limit)
            for i, agent in agents.items():
                if not legs[i]:
                    stationary.add(((now, *agent.point), (self.limit, *agent.point)))
            for i in frozen:
                for a, b in zip(committed[i], committed[i][1:]):
                    if stationary.departure(a[1:], b[1:], a[0], a[0], b[0] - a[0]) is None:
                        self.grid.compute_stats['local_stationary_rejections'] += 1
                        return reuse
        score = predicted_score(done + len(finishes), total, sum(a.health for a in agents.values()),
                                self.drones, max(finishes.values(), default=now), self.limit)
        return DispatchPlan({i: tuple(route) for i, route in sequences.items()}, legs, finishes, score)

    def solve(self, agents, tasks, now, done=0, total=None, current=None, fixed=(), seconds=.18, iterations=8):
        started = time.perf_counter()
        deadline = started + seconds
        total = total if total is not None else done + len(tasks)
        held = {a.held for a in agents.values() if a.held is not None}
        sequences = {i: [a.held] if a.held is not None else [] for i, a in agents.items()}
        if now >= self.limit:
            self.statistics = {"seconds": 0., "iterations": 0, "scheduled": 0}
            return DispatchPlan({i: tuple(q) for i, q in sequences.items()}, {i: [] for i in agents}, {}, 0.)
        if current:
            used = set(held)
            for i in agents:
                for k in current.get(i, ()):
                    eligible = [j for j, a in agents.items() if a.held is None and k not in a.blocked]
                    close = (k in tasks and eligible and distance(agents[i].point, tasks[k])
                             <= min(distance(agents[j].point, tasks[k]) for j in eligible) + 100)
                    if k in tasks and k not in used and k not in agents[i].blocked and (agents[i].committed or close):
                        sequences[i].append(k)
                        used.add(k)
        assigned = {k for route in sequences.values() for k in route}
        # 先给所有任务一个完整的空间分配；优化超时也保留这份初始解。
        loads = {i: float(now) for i in agents}
        points = {i: a.point for i, a in agents.items()}
        for i, route in sequences.items():
            for k in route:
                loads[i] += distance(points[i], tasks[k]) / 4 + distance(tasks[k], self.home) / 2.5 + 24
                points[i] = self.home
        for k in sorted(set(tasks) - assigned, key=lambda k: min(distance(a.point, tasks[k]) for a in agents.values())):
            eligible = [i for i, a in agents.items() if k not in a.blocked]
            if not eligible:
                continue
            owner = min(eligible, key=lambda i: loads[i] + distance(points[i], tasks[k]) / 4)
            loads[owner] += distance(points[owner], tasks[k]) / 4 + distance(tasks[k], self.home) / 2.5 + 24
            sequences[owner].append(k)
            points[owner] = self.home
        reservations = Reservations(self.grid, self.limit)
        for path in fixed:
            reservations.add(path, park_until=self.limit)
        best = self.schedule(agents, tasks, sequences, now, done, total, fixed, deadline=deadline)
        completed = 0
        for iteration in range(iterations):
            if time.perf_counter() >= deadline:
                break
            movable = [k for k in tasks if k not in held]
            if not movable:
                break
            amount = min(len(movable), max(2, math.ceil(len(movable) * .3)))
            if iteration % 3 == 0:
                removed = sorted(movable, key=lambda k: best.finishes.get(k, self.limit), reverse=True)[:amount]
            elif iteration % 3 == 1:
                # 同一通道附近的任务一起移出；用已观测净空识别狭窄位置。
                removed = sorted(movable, key=lambda k: self.grid.clearance[self.grid.cell(tasks[k][:2])])[:amount]
            else:
                removed = self.rng.sample(movable, amount)
            partial = {i: [k for k in route if k not in removed] for i, route in best.sequences.items()}
            repair = self.insert(agents, tasks, partial, removed, now, reservations, deadline)
            affected = {i for i, route in best.sequences.items() if any(k in removed for k in route)}
            trial = self.schedule(agents, tasks, repair, now, done, total, fixed, deadline=deadline,
                                  reuse=best, affected=affected)
            if trial.quality() > best.quality():
                best = trial
            completed += 1
        self.statistics = {"seconds": round(time.perf_counter() - started, 4), "iterations": completed,
                           "scheduled": len(best.finishes), "predicted_score": round(best.score, 3)}
        return best

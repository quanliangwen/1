"""单中心、单载荷的限时 LBBD：分配主问题 + 联合时序子问题。

每次 solve 都冻结一份传感器地图、目标和队友状态。割只在这份快照内有效。
工作量割与共享区域容量割有解析证明；预约寻路只提供可行计划，不提供不可行性证明。
"""

import math
import time
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix
from scipy.ndimage import label

from swarm_rescue.solutions.rescue_shared import distance
from swarm_rescue.solutions.two_stage_dispatch import Dispatcher


class TaskGraph:
    """把观测栅格压缩成接近、运送、中心出发的取送三类路径模板。"""

    def __init__(self, grid, home, agents, tasks):
        self.grid, self.home = grid, home
        self.ids = tuple(sorted(agents))
        held = {a.held for a in agents.values() if a.held is not None}
        self.keys = tuple(k for k in sorted(tasks) if k not in held)
        self.agents, self.tasks = agents, tasks
        self.legs = {}
        self.endpoints = {}
        if not hasattr(grid, 'compute_stats'):
            grid.compute_stats = Counter()
        cached = getattr(grid, '_lbbd_geometry', None)
        if cached is None or cached['topology'] is not grid._topology:
            cached = dict(topology=grid._topology, contacts={}, legs={}, components={})
            grid._lbbd_geometry = cached
        self.geometry = cached
        self.contact_cache = cached['contacts']
        m, n = len(self.ids), len(self.keys)
        self.loop = np.zeros(n)
        self.first = np.zeros((m, n))
        self.release = np.zeros(m)
        self.loaded = np.array([agents[i].held is not None for i in self.ids])
        # 接触允许终点停在目标周围；扣除两端余量后才用欧氏距离作下界。
        for k, key in enumerate(self.keys):
            p = tasks[key][:2]
            out = max(0, distance(home, p) - 150) / (4 * grid.speed_scale) + 12
            back = max(0, distance(p, home) - 150) / (2.5 * grid.speed_scale) + 12
            self.loop[k] = out + back
            for i, identifier in enumerate(self.ids):
                self.first[i, k] = max(0, distance(agents[identifier].point, p) - 150) / (4 * grid.speed_scale) + 12 + back
        for i, identifier in enumerate(self.ids):
            if self.loaded[i]:
                self.release[i] = max(0, distance(agents[identifier].point, home) - 150) / (2.5 * grid.speed_scale) + 12
        self.nominal = self.loop.copy(), self.first.copy(), self.release.copy()

    def contacts(self, point):
        """节点是能携雷通行的无人机位置集合，不是炸弹的物体坐标。"""
        key = tuple(point)
        if key not in self.contact_cache:
            radius = 75 if key == tuple(self.home) else 35
            self.contact_cache[key] = self.grid.contact_cells(point, radius)
        return self.contact_cache[key]

    def leg(self, start, goal, loaded, from_agent=False):
        key = tuple(start), tuple(goal), loaded, from_agent
        if key in self.legs:
            return self.legs[key]
        if not from_agent and key in self.geometry['legs']:
            result, endpoints = self.geometry['legs'][key]
            self.legs[key] = result
            if endpoints is not None:
                self.endpoints[key] = endpoints
            self.grid.compute_stats['lbbd_leg_hits'] += 1
            return result
        sources = (self.grid.cell(start),) if from_agent else self.contacts(start)
        targets = self.contacts(goal)
        # 网格是无向图；运回中心的下界复用从中心出发的多源最短路。
        reverse = not from_agent and tuple(goal) == tuple(self.home)
        roots, ends = (targets, sources) if reverse else (sources, targets)
        costs, parents = self.grid.tree_cells(roots, loaded)
        endpoint = min((c for c in ends if c in costs), key=costs.get, default=None)
        if endpoint is None:
            result = math.inf, {}
        else:
            # 最短几何路程 / 速度上界 <= 任何含加减速、等待的可行行程。
            # 接近与运输分别在接触集合内取最短值，是联合取送的有效松弛。
            offset = distance(start, self.grid.point(sources[0])) if from_agent else 0
            length = max(0, costs[endpoint] - offset)
            duration = length / ((2.5 if loaded else 4.0) * self.grid.speed_scale) + 12
            tiles = {(r // 3, c // 3) for r, c in targets}
            usage = {next(iter(tiles)): 12.0} if len(tiles) == 1 else {}
            cell = endpoint
            while cell in parents:
                r, c = cell
                if self.grid.clearance[r, c] < 45:
                    usage.setdefault((r // 3, c // 3), 0.0)
                cell = parents[cell]
            result = float(duration), usage
            self.endpoints[key] = sources, targets
        self.legs[key] = result
        if not from_agent:
            self.geometry['legs'][key] = result, self.endpoints.get(key)
            self.grid.compute_stats['lbbd_leg_builds'] += 1
        return result

    def certify_resources(self):
        """只有删去区域后确实断开的两端，才计入必经通道占用。

        空载自由图比带载图宽松；在这个图上仍不可绕过的区域才是证书。
        3×3 格的中心最大间距为 56.6 px，小于预约表的 58 px 间隔。
        每次必经至少占一个离散时步，服务终点占用 12 步。
        """
        walkable = (self.grid.evidence < 0) & (self.grid.clearance >= 23)
        candidates = {resource for _, usage in self.legs.values() for resource in usage}
        for resource in candidates:
            row, col = resource
            if resource not in self.geometry['components']:
                reduced = walkable.copy()
                reduced[row * 3:(row + 1) * 3, col * 3:(col + 1) * 3] = False
                self.geometry['components'][resource] = label(reduced)[0]
                self.grid.compute_stats['lbbd_certificate_builds'] += 1
            else:
                self.grid.compute_stats['lbbd_certificate_hits'] += 1
            parts = self.geometry['components'][resource]
            for key, (sources, targets) in self.endpoints.items():
                a, b = {parts[c] for c in sources}, {parts[c] for c in targets}
                if 0 not in a and 0 not in b and not a.intersection(b):
                    self.legs[key][1][resource] = 1.0

    def refine(self):
        """执行完整的空间图搜索，不用有时间上限的寻路失败生成割。"""
        for k, key in enumerate(self.keys):
            p = self.tasks[key][:2]
            out = self.leg(self.home, p, False)[0]
            back = self.leg(p, self.home, True)[0]
            self.loop[k] = out + back
            for i, identifier in enumerate(self.ids):
                approach = self.leg(self.agents[identifier].point, p, False, from_agent=True)[0]
                self.first[i, k] = approach + back
        for i, identifier in enumerate(self.ids):
            if self.loaded[i]:
                self.release[i] = self.leg(self.agents[identifier].point, self.home, True, from_agent=True)[0]
        self.certify_resources()

        def combine(*legs):
            usage = defaultdict(float)
            for _, values in legs:
                for resource, amount in values.items():
                    usage[resource] += amount
            return dict(usage)

        self.loop_usage, self.first_usage = [], [[] for _ in self.ids]
        for key in self.keys:
            p = self.tasks[key][:2]
            back = self.leg(p, self.home, True)
            self.loop_usage.append(combine(self.leg(self.home, p, False), back))
            for i, identifier in enumerate(self.ids):
                self.first_usage[i].append(combine(self.leg(self.agents[identifier].point, p, False, from_agent=True), back))
        self.release_usage = [self.leg(self.agents[i].point, self.home, True, from_agent=True)[1] if self.loaded[j] else {}
                              for j, i in enumerate(self.ids)]

    def resource_arrays(self):
        resources = set().union(*(u.keys() for u in self.loop_usage),
                                *(u.keys() for row in self.first_usage for u in row),
                                *(u.keys() for u in self.release_usage))
        for resource in sorted(resources):
            loop = np.array([u.get(resource, 0) for u in self.loop_usage])
            first = np.array([[u.get(resource, 0) for u in row] for row in self.first_usage])
            release = np.array([u.get(resource, 0) for u in self.release_usage])
            yield resource, loop, first, release

    def sequences(self, x, y):
        result = {}
        for i, identifier in enumerate(self.ids):
            assigned = list(np.flatnonzero(x[i] > .5))
            first = next((k for k in assigned if y[i, k] > .5), None)
            # 单中心下余下任务的顺序不影响独立完工时长；先做短任务，
            # 可在通信中断或截止时间临近时更早获得实际处置收益。
            assigned.sort(key=lambda k: (k != first, self.loop[k], k))
            held = self.agents[identifier].held
            result[identifier] = ([held] if held is not None else []) + [self.keys[k] for k in assigned]
        return result


class AssignmentMaster:
    """x 表示归属，y 表示从当前机位直接执行的首任务，C 表示剩余完工时长。"""

    def __init__(self, graph, remaining, current):
        self.graph, self.remaining = graph, remaining
        self.current = current or {}
        self.work_cuts = set()
        self.resource_cuts = {}
        self.last_status = None

    def solve(self, seconds):
        g, horizon = self.graph, self.remaining
        m, n = g.first.shape
        count = m * n
        size = 2 * count + 1
        c_index = size - 1
        objective = np.zeros(size)
        objective[:count] = -10 * horizon
        objective[c_index] = 1
        lower, upper = np.zeros(size), np.ones(size)
        upper[c_index] = horizon
        rows, cols, values, rhs = [], [], [], []

        def add(coefficients, bound):
            row = len(rhs)
            for column, value in coefficients.items():
                if value:
                    rows.append(row); cols.append(column); values.append(value)
            rhs.append(bound)

        loop0, first0, release0 = g.nominal
        claims = defaultdict(list)
        for i, identifier in enumerate(g.ids):
            queue = self.current.get(identifier, ())
            if queue and queue[0] in g.keys and not g.loaded[i] and g.agents[identifier].committed:
                claims[g.keys.index(queue[0])].append(i)
        committed = {k: min(owners, key=lambda i: (g.first[i, k], i)) for k, owners in claims.items()}
        for k in range(n):
            add({i * n + k: 1 for i in range(m)}, 1)
        for i, identifier in enumerate(g.ids):
            xs = [i * n + k for k in range(n)]
            ys = [count + j for j in xs]
            for k, key in enumerate(g.keys):
                if key in g.agents[identifier].blocked:
                    upper[xs[k]] = upper[ys[k]] = 0
            if g.loaded[i]:
                upper[ys] = 0
            else:
                add(dict.fromkeys(ys, 1), 1)
                for x, y in zip(xs, ys):
                    add({y: 1, x: -1}, 0)
                    add({x: 1, **dict.fromkeys(ys, -1)}, 0)
            loop, first, release = (g.loop, g.first, g.release) if i in self.work_cuts else (loop0, first0, release0)
            # 不能在当前图上完成运输的任务暂不进入分配，下一快照重新检查。
            if i in self.work_cuts:
                for k in range(n):
                    if not math.isfinite(loop[k]):
                        upper[xs[k]] = upper[ys[k]] = 0
                    elif not math.isfinite(first[i, k]):
                        upper[ys[k]] = 0
                if not math.isfinite(release[i]) or release[i] > horizon:
                    upper[xs] = upper[ys] = 0
                    release = release.copy()
                    release[i] = 0
            coefficients = {c_index: -1}
            for k, (x, y) in enumerate(zip(xs, ys)):
                if math.isfinite(loop[k]):
                    coefficients[x] = loop[k]
                    if math.isfinite(first[i, k]):
                        coefficients[y] = first[i, k] - loop[k]
                # 初始主问题只用几何下界；少量首航代价用于打破等价分配。
                objective[y] = .06 * first0[i, k]
                if self.current.get(identifier, ()) and self.current[identifier][0] == g.keys[k]:
                    objective[y] -= 25
                if committed.get(k) == i and upper[y] and first[i, k] <= horizon:
                    lower[x] = lower[y] = 1
            add(coefficients, -release[i])
        for loop, first, release in self.resource_cuts.values():
            coefficients = {c_index: -1}
            for i in range(m):
                for k in range(n):
                    coefficients[i * n + k] = loop[k]
                    coefficients[count + i * n + k] = first[i, k] - loop[k]
            add(coefficients, -sum(release))
        matrix = coo_matrix((values, (rows, cols)), shape=(len(rhs), size)).tocsc()
        result = milp(objective, integrality=np.r_[np.ones(2 * count), 0],
                      bounds=Bounds(lower, upper), constraints=LinearConstraint(matrix, -np.inf, rhs),
                      options={"time_limit": max(.005, seconds), "mip_rel_gap": 1e-6})
        self.last_status = result.status
        if result.x is None:
            return None
        return result.x[:count].reshape(m, n), result.x[count:2 * count].reshape(m, n), result.x[-1]

    def feedback(self, solution):
        """解析推导的两类割；不接收 safe_path 的成功/失败信号。

        单机：C >= r_i + Σ b_k x_ik + Σ (f_ik-b_k)y_ik。
        资源：C >= Σ_i r_ir + Σ_ik b_kr x_ik + Σ_ik(f_ikr-b_kr)y_ik。
        前者是去掉交通冲突的松弛；后者是单容量资源的总占用下界。
        """
        x, y, estimate = solution
        g, added = self.graph, 0
        for i in range(len(g.ids)):
            if i not in self.work_cuts:
                self.work_cuts.add(i)
                added += 1
        violations = []
        for resource, loop, first, release in g.resource_arrays():
            amount = sum(release) + np.sum(x * loop) + np.sum(y * (first - loop))
            if resource not in self.resource_cuts and amount > estimate + .5:
                violations.append((amount, resource, loop, first, release))
        for _, resource, loop, first, release in sorted(violations, key=lambda v: -v[0])[:4]:
            self.resource_cuts[resource] = loop, first, release
            added += 1
        return added


class LBBDDispatcher(Dispatcher):
    USE_CUTS = True

    def solve(self, agents, tasks, now, done=0, total=None, current=None, fixed=(), seconds=.24, iterations=4):
        started = time.perf_counter()
        deadline = started + seconds
        # Build the fallback first, reserving time for the master, cuts and schedule.
        # Letting LNS consume the entire budget silently disables LBBD on hard maps.
        incumbent = super().solve(agents, tasks, now, done, total, current, fixed,
                                  seconds=.25 * seconds, iterations=0)
        heuristic_seconds = self.statistics["seconds"]
        repaired = self.statistics["iterations"]
        graph = TaskGraph(self.grid, self.home, agents, tasks)
        master = AssignmentMaster(graph, max(1, self.limit - now), current)
        # 仅凭有效下界删除已经来不及完成的新任务；实际载荷继续由原机送回。
        for i, identifier in enumerate(graph.ids):
            minimum = graph.release[i] + graph.loop if graph.loaded[i] else graph.first[i]
            incumbent.sequences[identifier] = tuple(k for k in incumbent.sequences[identifier]
                if k == agents[identifier].held or minimum[graph.keys.index(k)] <= self.limit - now)
        active = bool(graph.keys) and time.perf_counter() < deadline - .06
        solution = master.solve(min(.04, seconds / 5)) if active else None
        master_calls = int(active)
        initial_bound = solution[2] if solution is not None else None
        # 图搜索先于任何割。它是确定性的完整搜索，不使用调度器的超时结果。
        if active:
            graph.refine()
        if active and self.USE_CUTS and solution is None:
            master.work_cuts.update(range(len(graph.ids)))
            solution = master.solve(min(.04, max(.005, deadline - time.perf_counter() - .03)))
            master_calls += 1
        if self.USE_CUTS and solution is not None:
            for _ in range(iterations):
                added = master.feedback(solution)
                if not added or time.perf_counter() > deadline - .06:
                    break
                candidate = master.solve(min(.04, max(.005, deadline - time.perf_counter() - .06)))
                master_calls += 1
                if candidate is None:
                    break
                solution = candidate
        if solution is None:
            candidate = None
        else:
            sequences = graph.sequences(solution[0], solution[1])
            # 复用公共调度器的通行顺序，与 local_route 保持一致。
            candidate = self.schedule(agents, tasks, sequences, now, done,
                                      total if total is not None else done + len(tasks), fixed,
                                      deadline=max(deadline, time.perf_counter() + .025))
        if candidate is not None:
            candidate.sequences = {i: tuple(k for k in route if k in candidate.finishes or k == agents[i].held)
                                   for i, route in candidate.sequences.items()}
        # 保留原方案的完整承诺。动态目标和通信确认存在误差，小幅预测改善不触发换路。
        finish = max(incumbent.finishes.values(), default=now)
        improves = candidate is not None and candidate.quality() > incumbent.quality() and (
            len(candidate.finishes) > len(incumbent.finishes) or
            max(candidate.finishes.values(), default=now) < finish - max(30, .05 * (finish - now)))
        best = candidate if improves else incumbent
        self.statistics = {"seconds": round(time.perf_counter() - started, 4),
                           "master_calls": master_calls, "master_status": master.last_status,
                           "workload_cuts": len(master.work_cuts), "resource_cuts": len(master.resource_cuts),
                           "initial_bound": None if initial_bound is None else round(initial_bound, 2),
                           "final_bound": None if solution is None else round(solution[2], 2),
                           "scheduled": len(best.finishes), "assigned": sum(map(len, best.sequences.values())),
                           "incumbent_used": best is incumbent,
                           "heuristic_iterations": repaired,
                           "heuristic_seconds": heuristic_seconds,
                           "predicted_score": round(best.score, 3), "snapshot_step": now}
        return best


class NoCutsDispatcher(LBBDDispatcher):
    """消融对照：保留同一主问题与联合执行器，仅关闭反馈割。"""

    USE_CUTS = False

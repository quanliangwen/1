"""共享同一探索、通信和运动控制，用调度器选择完成 LBBD 消融。"""

from swarm_rescue.simulation.utils.constants import MAX_RANGE_SEMANTIC_SENSOR
from swarm_rescue.solutions.lbbd_dispatch import LBBDDispatcher, NoCutsDispatcher
from swarm_rescue.solutions.rescue_shared import distance
from swarm_rescue.solutions.two_stage_rescue import TwoStageRescue


class LBBDRescue(TwoStageRescue):
    EXPLORATION_FRACTION = .20
    MAX_EXPLORATION_STEPS = 800
    MIN_DISPOSAL_STEPS = 1800
    dispatcher_class = LBBDDispatcher

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.planning_totals = {"calls": 0, "seconds": 0.0, "master_calls": 0,
                                "workload_cuts": 0, "resource_cuts": 0,
                                "active_calls": 0, "accepted": 0}
        self.phase_report = None

    def publish(self):
        if self.phase == "dispose" and self.phase_report is None:
            self.phase_report = {"step": self.elapsed_timestep,
                                 "reason": ("budget" if self.elapsed_timestep >= self.exploration_deadline else
                                     "wall_budget" if self.limits.max_walltime_limit is not None and
                                     self.elapsed_walltime >= self.EXPLORATION_FRACTION * self.limits.max_walltime_limit else "coverage"),
                                 "unresolved_regions": len(self.grid.targets(self.pose)[0]),
                                 "known_tasks": len(self.bombs), "fresh_members": sorted(self.fresh_states()),
                                 "point": tuple(self.pose), "health": float(self.drone_health),
                                 "remaining_steps": self.limits.max_timestep_limit - self.elapsed_timestep}
        super().publish()

    def pickup_point(self, target, loaded=False):
        """接触点必须看得见目标；带载时先恢复到交付目标的连通路径。"""
        if loaded:
            return super().pickup_point(target, loaded=True)
        if self.grid.route(self.pose, target, contact=True):
            return tuple(target)
        costs, _ = self.grid.tree(self.pose)
        visible = [c for c in costs if distance(self.grid.point(c), target) < MAX_RANGE_SEMANTIC_SENSOR - 15
                   and self.grid.visible(self.grid.point(c), target)]
        if visible:
            cell = min(visible, key=lambda c: distance(self.grid.point(c), target) + .05 * costs[c])
            return tuple(self.grid.point(cell))
        points, _ = self.grid.targets(self.pose)
        if points and self.grid.speed_scale <= 1:
            return min(points, key=lambda p: distance(p, target) + .2 * costs.get(self.grid.cell(p), 1e6)
                       + 10 * self.grid.visits[self.grid.cell(p)])
        return super().pickup_point(target)

    def make_plan(self, first=False):
        previous = self.last_planning
        super().make_plan(first)
        if self.last_planning is previous:
            return
        self.planning_totals["calls"] += 1
        self.planning_totals["active_calls"] += self.last_planning.get("master_calls", 0) > 0
        self.planning_totals["accepted"] += self.last_planning.get("incumbent_used") is False
        for key in ("seconds", "master_calls", "workload_cuts", "resource_cuts"):
            self.planning_totals[key] += self.last_planning.get(key, 0)


class NoCutsRescue(LBBDRescue):
    dispatcher_class = NoCutsDispatcher


class HeuristicRescue(LBBDRescue):
    """原插入/LNS 调度器，探索预算与 LBBD 完全一致。"""

    dispatcher_class = TwoStageRescue.dispatcher_class

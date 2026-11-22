"""比赛入口：限时协同探索，然后以拆除为主、空闲补查。

控制器只读传感器和收到的消息。地图、队友状态与计划均广播值快照，
没有全局共享队伍对象。分配在当前通信组内确认，不等待失联队友。
"""

import math
from collections import deque
from dataclasses import dataclass, field, replace

import numpy as np
from scipy.optimize import linear_sum_assignment

from swarm_rescue.simulation.utils.constants import MAX_RANGE_SEMANTIC_SENSOR, RANGE_COMMUNICATION
from swarm_rescue.solutions.rescue_shared import SensorRescue, distance
from swarm_rescue.solutions.two_stage_exploration import (
    ExplorationGrid, SearchHandoff, SearchTask, allocate_regions, open_tour,
)
from swarm_rescue.solutions.two_stage_dispatch import Agent, Dispatcher, parking_point, traffic_priority
from swarm_rescue.solutions.two_stage_paths import Reservations, move_time, safe_path, progress_path, time_route
from swarm_rescue.solutions.loaded_progress import CarriedProgress
from swarm_rescue.solutions.in_block_frontier import observation_point
from swarm_rescue.solutions.frontier_audit import audit_frontier
from swarm_rescue.solutions.egress_gate import EgressGate
from swarm_rescue.solutions.search_roaming import SearchRoaming


@dataclass
class GapExit:
    axis: np.ndarray
    start: np.ndarray
    minimum: float
    began: int
    last_move: int
    best: float = 0.
    last_wall: float = 0.


@dataclass
class GapProbe:
    axis: np.ndarray
    start: np.ndarray
    last_move: int
    depth: float = 0.
    station: int = 1
    backing: bool = False
    entrance: tuple | None = None
    width: float = 0.
    last_fit: int = -1000
    passage: "GapPassage | None" = None
    limit: float = 0.
    published: bool = False
    pullout: tuple | None = None
    retreat: tuple | None = None


@dataclass(frozen=True)
class GapPassage:
    source: int
    step: int
    target: tuple
    entrance: tuple
    end: tuple
    axis: tuple
    width: float


@dataclass(frozen=True)
class GapSurvey:
    source: int
    step: int
    entrance: tuple
    end: tuple
    axis: tuple
    width: float
    cells: frozenset
    expires: int
    clear: int = 0
    recipient: int | None = None

    @property
    def version(self):
        return self.source, self.step


@dataclass
class SurveyRun:
    offer: GapSurvey
    stage: tuple
    route: deque
    last_move: int
    depth: float = -100.
    staged: bool = False
    inside: bool = False
    passed: bool = False
    retreat: bool = False
    scanned: int = 0
    coverage: dict = field(default_factory=dict)
    fit: deque = field(default_factory=lambda: deque(maxlen=5))
    backtrack: list = field(default_factory=list)
    viewpoints: set = field(default_factory=set)


class TwoStageRescue(SensorRescue):
    EXPLORATION_FRACTION = .25
    MAX_EXPLORATION_STEPS = 1000
    MIN_DISPOSAL_STEPS = 0
    PICKUP_LEASE = 240
    PICKUP_OBSERVATION_AGE = 2 * PICKUP_LEASE
    SEARCH_REVIEW = 40
    SEARCH_STALL = 240
    EARLY_TRIP_STEPS = 220
    EARLY_TRIP_BUFFER = 30
    EARLY_CONTACT_CLEARANCE = 64
    GAP_PASSAGE_AGE = 600
    dispatcher_class = Dispatcher

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grid = ExplorationGrid(self.size_area)
        self.limits = kwargs["misc_data"]
        self.responsibility = self.grid.configure_opening(self.limits.number_drones)
        self.frontier_egress = EgressGate()
        self.search_roaming = SearchRoaming()
        self.phase = "explore"
        self.anchor = None
        self.home_fix = None
        self.depot_stance = None
        self.ready = False
        self.states = {}
        self.aliases = {}
        self.pickup_origins = {}
        self.map_versions = {}
        self.proposal = None
        self.commit = None
        self.ack = None
        self.applied = None
        self.queue = []
        self.legs = []
        self.timed_path = ()
        self.path_index = 1
        # The simulator starts control at step 2. A new claim takes two
        # steps to reach a peer, so give each drone a separate review slot.
        self.next_explore = 2 + self.SEARCH_REVIEW * self.identifier // self.limits.number_drones
        self.search_task = None
        self.search_offer = None
        self.accepted_handoffs = set()
        self.search_steps = 0
        self.search_paused = False
        self.search_retry = None
        self.scout_until = 0
        self.next_dispatch = 0
        self.next_route = 0
        self._message = None
        self._map_message = None
        self.last_planning = {}
        self.phase_started = None
        self.exploration_deadline = self.exploration_budget(self.limits.max_timestep_limit)
        # Use faster cruise only when the exploration budget cannot span the known area at baseline speed.
        self.grid.speed_scale = 1.5 if self.exploration_deadline < max(self.grid.size) / 4 else 1.0
        self.mode = "explore"
        self.next_assign = 0
        self.next_contact_check = 0
        self.next_early_check = 0
        self.early_pickup_until = 0
        self.missing_since = None
        self.progress_pose = None
        self.progress_step = 0
        self.motion_goal = None
        self.recovery_until = 0
        self.recovery_point = None
        self.carrier_yield_until = 0
        self.pickup_contact_window = None
        self.next_pickup_contact_window = 0
        self.delivery_point = None
        self.return_probe = None
        self.checked_return_cells = set()
        self.return_corridor = frozenset()
        self.checked_pickup_returns = set()
        self.next_trip_check = 0
        self.pickup_forecast = None

        self.motion_pose = None
        self.progress_key = None
        self.task_progress_point = None
        self.task_progress_motion = None
        self.task_progress_step = 0
        self.next_progress_check = 0

        self.failed_pickups = {}
        self.pickup_since = None
        self.pickup_transfer = None
        self.local_pickup_hits = set()
        self.carried_progress = CarriedProgress()
        self.gap_entry = None
        self.gap_exit = None
        self.gap_probe = None
        self.gap_scans = deque(maxlen=5)
        self.recent_gap_entries = deque(maxlen=12)
        self.gap_passage = None
        self.gap_survey = None
        self.survey_run = None
        self.survey_used = set()
        self.survey_events = deque(maxlen=96)

    @classmethod
    def exploration_budget(cls, limit):
        """比例与绝对上限同时生效，并为短局保留取送时间。"""
        return min(cls.MAX_EXPLORATION_STEPS, int(cls.EXPLORATION_FRACTION * limit),
                   max(0, limit - cls.MIN_DISPOSAL_STEPS))

    def task_progress(self, target, loaded):
        """在同一张当前地图比较两次机位，不跨地图保留最短距离。"""
        t = self.elapsed_timestep
        key = self.task, loaded
        motion = self.motion_pose if self.motion_pose is not None else self.pose
        if key != self.progress_key:
            self.progress_key = key
            self.task_progress_point = tuple(self.pose)
            self.task_progress_motion = tuple(motion)
            self.task_progress_step = t
        if t < self.next_progress_check:
            return
        self.next_progress_check = t + 5
        cells = self.grid.contact_cells(target, 75 if loaded else 35, loaded=loaded)
        costs, _ = self.grid.tree_cells(cells, loaded=loaded)
        def remaining(point):
            row, col = self.grid.cell(point)
            return costs.get((row, col), min((costs.get((row + dr, col + dc), math.inf) + self.grid.CELL
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))), default=math.inf))
        before, current = remaining(self.task_progress_point), remaining(self.pose)
        if (math.isfinite(current) and before - current >= 20
                and distance(motion, self.task_progress_motion) > 12):
            self.task_progress_point = tuple(self.pose)
            self.task_progress_motion = tuple(motion)
            self.task_progress_step = t

    def claim_valid(self, state, key):
        progress = state.get("progress")
        return (state["health"] > 0 and state["held"] is None
                and self.elapsed_timestep - state["step"] < 240
                and progress is not None and self.resolve(progress[0]) == key
                and self.elapsed_timestep - progress[1] <= self.PICKUP_LEASE)

    def release_pickup(self, reason, key=None):
        key = self.task if key is None else key
        t = self.elapsed_timestep
        if key is not None:
            self.failed_pickups[key] = t + (30 if reason == "duplicate_claim" else self.PICKUP_LEASE)
        if self.early_pickup_until:
            self.grid.compute_stats["early_pickup_released"] += 1
            self.early_pickup_until = 0
        self.pickup_since = None
        self.pickup_transfer = None
        self.queue, self.legs, self.timed_path, self.task = [], [], (), None
        self.progress_key = None
        self.next_assign, self.next_dispatch = t + 30, t

    def reconcile_pickup(self):
        """Resolve simultaneous claims before following a pickup leg."""
        if self.carrying or not self.queue:
            return
        key = self.resolve(self.queue[0])
        t = self.elapsed_timestep
        since = self.pickup_since if self.resolve(self.task) == key else None
        rank = (t if since is None else since, self.identifier)
        transfer = self.pickup_transfer
        replaced = transfer[1] if transfer and self.resolve(transfer[0]) == key else ()
        for identifier, state in self.fresh_states().items():
            peer_since = state.get("pickup_since")
            if (identifier != self.identifier and peer_since is not None
                    and any(self.resolve(k) == key for k in state["queue"])
                    and self.claim_valid(state, key)):
                incoming = state.get("pickup_transfer")
                if incoming and self.resolve(incoming[0]) == key and (self.identifier, since) in incoming[1]:
                    self.release_pickup("transferred", key)
                    return
                if (peer_since, identifier) < rank and (identifier, peer_since) not in replaced:
                    self.release_pickup("duplicate_claim", key)
                    return

    def define_message_for_all(self):
        return self._message

    def resolve(self, key):
        while key in self.aliases and self.aliases[key] != key:
            key = self.aliases[key]
        return key

    def _remember(self, point, stamp, state=0, key=None, origin=None):
        """短距离时空关联；消息中的原始编号通过 aliases 统一到本地轨迹。"""
        original = key
        key = self.resolve(key)
        location = point if state == 0 else origin
        if key not in self.bombs and location is not None:
            candidates = [k for k, value in self.bombs.items() if value[3] in (0, 3)
                          and distance(location, value) < (40 if state != 0 else min(70, 40 + max(0, stamp - value[2])))]
            key = min(candidates, key=lambda k: distance(location, self.bombs[k]), default=key)
        if key is None:
            self.serial += 1
            key = (self.identifier, self.serial)
        if original is not None:
            self.aliases[original] = key
        if origin is not None:
            self.pickup_origins[key] = tuple(origin)
        old = self.bombs.get(key)
        if old is None or (stamp >= old[2] and old[3] != 2):
            self.bombs[key] = [float(point[0]), float(point[1]), stamp, state]
        return key

    def consolidate_tracks(self):
        """合并不同观察者对同一目标建立的近邻轨迹，保留最新观测。"""
        keys = sorted(self.bombs)
        for index, key in enumerate(keys):
            if key not in self.bombs or self.bombs[key][3] not in (0, 3):
                continue
            for other in keys[index + 1:]:
                if other in self.bombs and self.bombs[other][3] in (0, 3) and distance(self.bombs[key], self.bombs[other]) < 40:
                    if self.bombs[other][2] > self.bombs[key][2]:
                        self.bombs[key] = self.bombs[other]
                    self.aliases[other] = key
                    del self.bombs[other]
        self.queue = list(dict.fromkeys(self.resolve(k) for k in self.queue))
        self.task = self.resolve(self.task)

    def receive(self):
        for _, message in self.communicator.received_messages:
            if not isinstance(message, dict) or message.get("kind") != "two-stage":
                continue
            if self.anchor is None and message["anchor"] is not None:
                self.anchor = message["anchor"]
            if self.home is None and message["home"] is not None:
                self.home = message["home"]
            if message["home_fix"] is not None:
                self.remember_home(message["home_fix"])
            for key, value, origin in message["bombs"]:
                self._remember(value[:2], value[2], value[3], key, origin)
            for state in message["states"]:
                previous = self.states.get(state["id"])
                if state["id"] != self.identifier and (previous is None or state["step"] > previous["step"]):
                    self.states[state["id"]] = state
            version, evidence, stamps, searched, passages = message["grid"]
            if version > self.map_versions.get(message["id"], -1):
                self.grid.merge(evidence, stamps, passages)
                observed = np.frombuffer(searched, dtype=np.uint8).reshape(self.grid.evidence.shape)
                np.maximum(self.grid.searched, observed, out=self.grid.searched)
                self.map_versions[message["id"]] = version
            for name in ("proposal", "commit"):
                incoming, current = message[name], getattr(self, name)
                if incoming is not None and (self.identifier not in incoming["sequences"]
                        or (self.phase == "dispose" and incoming["first"]
                            and incoming["version"][0] < self.phase_started)):
                    continue
                if incoming is not None and (current is None or incoming["version"] > current["version"]):
                    setattr(self, name, incoming)

    def map_snapshot(self):
        return (self.elapsed_timestep, self.grid.evidence.tobytes(), self.grid.stamps.tobytes(),
                self.grid.searched.tobytes(), self.grid.passage_stamps.tobytes() if self.grid.return_guard else b"")

    def publish(self):
        t = self.elapsed_timestep
        if self._map_message is None or t % 15 == self.identifier % 15:
            self._map_message = self.map_snapshot()
        state = {"id": self.identifier, "step": t, "point": tuple(self.pose), "health": self.drone_health,
                 "phase": self.phase, "ready": self.ready, "held": self.task if self.carrying else None,
                 "goal": self.goal, "motion_goal": self.motion_goal, "queue": tuple(self.queue),
                 "path": self.timed_path, "ack": self.ack}
        state["path_index"] = self.path_index
        state["pickup_since"] = self.pickup_since
        if (self.pickup_transfer and not self.carrying and self.queue
                and self.resolve(self.pickup_transfer[0]) == self.resolve(self.queue[0])):
            state["pickup_transfer"] = self.pickup_transfer
        state["progress"] = (self.task, self.task_progress_step) if self.task is not None and not self.carrying else None
        state["blocked"] = tuple(k for k, until in self.failed_pickups.items() if until > t)
        state["scout_until"] = self.scout_until
        state["depot_stance"] = self.depot_stance
        state["gap_passage"] = self.gap_passage
        task = self.search_task
        state["search"] = ((task.started, task.point) if task and not self.search_paused
                           and not self.carrying and not self.queue and self.goal == task.point else None)
        # The original footprint field also covers search during disposal.
        if state["search"] is not None:
            state["opening_cells"] = task.cells
        offer = self.search_offer
        state["search_offer"] = (offer if offer and self.carrying and self.gap_exit is None
                                 and self.gap_survey is None and t < offer.expires else None)
        state["search_handoff"] = ((task.handoff, task.cells) if state["search"] is not None
                                   and task.handoff is not None else None)
        survey = self.gap_survey
        if survey and survey.cells and t < survey.expires:
            state["gap_survey"] = survey
        if self.survey_run is not None:
            offer = self.survey_run.offer
            state["survey_lane"] = offer
            if not self.survey_run.retreat:
                state["search_handoff"] = (offer.version, offer.cells)
        self.states[self.identifier] = state
        self._message = {"kind": "two-stage", "id": self.identifier, "anchor": self.anchor,
                         "home": self.home, "home_fix": self.home_fix,
                         "states": tuple(dict(v) for v in self.states.values()),
                         "bombs": tuple((k, tuple(v), self.pickup_origins.get(k)) for k, v in self.bombs.items()), "grid": self._map_message,
                         "proposal": self.proposal, "commit": self.commit}

    def fresh_states(self, age=30):
        return {i: s for i, s in self.states.items() if self.elapsed_timestep - s["step"] <= age and s["health"] > 0}

    def awaiting_commit(self):
        if self.early_pickup_until:
            return False
        if self.proposal is None or self.ack != self.proposal["version"] or self.elapsed_timestep >= self.proposal["activate"]:
            return False
        sequence = self.proposal["sequences"].get(self.identifier, ())
        first = self.resolve(sequence[0]) if sequence else None
        return not self.carrying and first != self.task

    def advance_phase(self):
        """统一的硬截止时间保证失联、残余前沿和无人机损失不会永久阻塞处置。"""
        wall_limit = self.limits.max_walltime_limit
        wall_due = wall_limit is not None and self.elapsed_walltime >= self.EXPLORATION_FRACTION * wall_limit
        if self.phase != "dispose" and (self.elapsed_timestep >= self.exploration_deadline or wall_due):
            self.phase, self.phase_started = "dispose", self.elapsed_timestep
            self.ready = True
            self.proposal = self.commit = self.ack = None
            self.next_dispatch = self.elapsed_timestep

    def search_distance(self, point):
        if not self.route:
            return distance(self.pose, point)
        return distance(self.pose, self.route[0]) + sum(map(distance, self.route, self.route[1:]))

    def set_search_point(self, task, point):
        task.point = self.goal = point
        self.route = list(self.search_route(point))
        task.remaining = self.search_distance(point)
        task.motion = tuple(self.motion_pose if self.motion_pose is not None else self.pose)

    def offer_search_handoff(self):
        """Offer the paused search footprint once the carrier starts its return."""
        task = self.search_task
        if task is None or self.home is None or self._odometry_only or self.communicator_is_disabled():
            return
        peers = [s for i, s in self.fresh_states().items()
                 if i != self.identifier and s["held"] is None and not s["queue"]
                 and distance(s["point"], self.pose) <= RANGE_COMMUNICATION]
        if not peers:
            return
        t, scale = self.elapsed_timestep, self.grid.speed_scale
        costs, work, pending = self.grid.search_work(self.pose)
        close = self.grid.close_scan_cells()
        cells = frozenset(c for c in task.cells if pending[c] and self.grid.searched[c] <= close[c])
        walkable = self.grid.walkable()
        entrance = min((c for c in cells if work[c] and walkable[c]),
                       key=lambda c: (costs[c], c), default=None)
        if entrance is None:
            return
        point = self.grid.point(entrance)
        depot = self.home
        delivered_at = t + move_time(distance(self.pose, depot), loaded=True, scale=scale)
        for mode, key, path in self.legs:
            if mode == "deliver" and self.resolve(key) == self.task and path and path[-1][0] > t:
                delivered_at, *depot = path[-1]
                break
        resume_at = min(self.limits.max_timestep_limit,
                        delivered_at + move_time(distance(depot, point), scale=scale))
        expires = min(t + self.SEARCH_STALL, resume_at - self.SEARCH_REVIEW)
        if expires <= t:
            return
        from_entrance = self.grid.tree(point)[0]
        candidates = []
        for state in peers:
            length = from_entrance.get(self.grid.cell(state["point"]))
            if length is None:
                continue
            eta = t + move_time(length, scale=scale)
            if state.get("search") is not None:
                eta += self.SEARCH_REVIEW
            if eta < expires:
                candidates.append((eta, state["id"]))
        if candidates:
            _, recipient = min(candidates)
            self.search_offer = SearchHandoff((self.identifier, t), recipient, cells, entrance, expires, resume_at)
            self._map_message = None  # Publish the exact coverage revision referenced by the offer.
            self.grid.compute_stats["search_handoff_offered"] += 1

    def search_route(self, point):
        route = self.grid.route(self.pose, point)
        roaming = self.search_roaming
        if roaming.allows(self.pose, point, route):
            return route
        if distance(roaming.origin, point) < roaming.radius:
            return ()
        route = self.grid.route(self.pose, point, avoid=((roaming.origin, roaming.radius),))
        return route if roaming.allows(self.pose, point, route) else ()

    def search_route_allowed(self, point):
        return not self.search_roaming.departed or bool(self.search_route(point))

    def roam_when_idle(self, costs, peers):
        if self.phase != "dispose":
            self.phase = "explore"
        previous = self.search_roaming.target
        self.goal, self.route = self.search_roaming.idle_waypoint(
            self.grid, self.pose, costs, [s["point"] for s in peers.values()], RANGE_COMMUNICATION,
            self.search_route)
        if self.search_roaming.target is not None and self.search_roaming.target != previous:
            self.search_roaming_event = self.elapsed_timestep, "roam", self.goal, None

    def accept_search_handoff(self, costs, work, pending, reserved, occupied):
        """Choose one reachable offer when the drone is free to start another search."""
        if self.carrying or self.queue or self.search_task is not None:
            return False
        t = self.elapsed_timestep
        offers = [s["search_offer"] for s in self.states.values() if s.get("search_offer") is not None]
        for offer in sorted(offers, key=lambda o: (o.version[1], o.version[0])):
            sender, issued = offer.version
            if (offer.recipient != self.identifier or t >= offer.expires or offer.version in self.accepted_handoffs
                    or self.map_versions.get(sender, -1) < issued or offer.entrance not in costs):
                continue
            walkable = self.grid.walkable()
            if not walkable[offer.entrance]:
                continue
            close = self.grid.close_scan_cells()
            cells = frozenset(c for c in offer.cells - reserved
                              if work[c] and pending[c] and walkable[c] and self.grid.searched[c] <= close[c])
            if not cells or not cells.isdisjoint(occupied):
                continue
            cell = min(cells, key=lambda c: (costs[c], c))
            arrival = t + move_time(costs[cell], scale=self.grid.speed_scale)
            if arrival + self.SEARCH_REVIEW >= offer.resume_at:
                continue
            point = tuple(self.grid.point(cell))
            if not self.search_route_allowed(point):
                continue
            self.search_task = SearchTask(cells, point, t, self.search_steps, self.grid.local_coverage(cells),
                                          handoff=offer.version)
            self.set_search_point(self.search_task, point)
            self.accepted_handoffs.add(offer.version)
            self.grid.compute_stats["search_handoff_accepted"] += 1
            self.grid.compute_stats["search_handoff_claim_steps"] += t - issued
            self.grid.compute_stats["search_started"] += 1
            return True
        return False

    def continue_search(self, task, costs, work, pending, resumed):
        """Keep the footprint across retile, pickup and temporary loss of a route."""
        if task.return_check_until and (self.elapsed_timestep >= task.return_check_until or
                                        (task.checked and self.reached_search_point(task.point))):
            return 'return_check_ended'
        remaining = [c for c in task.cells if pending[c]]
        if not remaining:
            return 'completed'
        if (self.search_roaming.departed and self.route
                and not self.search_roaming.allows(self.pose, task.point, self.route)):
            return 'birth_route'
        reachable = sorted(c for c in remaining if work[c])
        if not reachable:
            task.misses += 1
            if task.misses >= 2:
                return 'unavailable'
            self.goal, self.route = tuple(self.pose), []
            return None
        task.misses = 0
        motion = tuple(self.motion_pose if self.motion_pose is not None else self.pose)
        covered = self.grid.local_coverage(task.cells)
        length = self.search_distance(task.point)
        if covered > task.covered:
            task.covered = covered
            if not resumed:
                task.progress = self.search_steps
        if (not resumed and self.goal == task.point and task.motion is not None
                and length + self.grid.CELL <= task.remaining and distance(motion, task.motion) > 12):
            task.remaining, task.motion, task.progress = length, motion, self.search_steps
        if self.search_steps - task.progress >= self.SEARCH_STALL:
            return 'stalled'

        cell = self.grid.cell(task.point)
        arrived = self.reached_search_point(task.point)
        if arrived:
            task.checked.add(cell)
        options = [c for c in reachable if c not in task.checked]
        point = task.point
        if cell not in reachable or (arrived and options):
            if options and self.communicator_is_disabled():
                # PythonRobotics Grid-Based Sweep (ef64608): reverse on the next strip.
                next_cell = self.grid.sweep_target(task.cells, options)
                self.grid.compute_stats["isolated_sweep_choices"] += 1
            else:
                next_cell = min(options or reachable, key=costs.__getitem__)
            point = tuple(self.grid.point(next_cell))
        if not self.search_route_allowed(point):
            options = [c for c in reachable if self.search_route_allowed(self.grid.point(c))]
            if not options:
                return 'birth_route'
            point = tuple(self.grid.point(min(options, key=costs.__getitem__)))
        if point != task.point:
            self.grid.compute_stats['search_changed_point'] += 1
        # Reuse the route until it is interrupted or its next portion is invalid.
        here = self.grid.cell(self.pose)
        walkable = self.grid.walkable()
        invalid = any(c != here and not walkable[c]
                      for c in map(self.grid.cell, self.route[:3]))
        if resumed or point != task.point or self.goal != point or invalid or (not self.route and not arrived):
            self.set_search_point(task, point)
        return None

    def _empty_frontier_support(self, own, points, gain, costs):
        if not self.grid.pose_fixed or (not getattr(self, 'mapping_time_search', False) and self.carried_bombs_count()):
            return ()
        best_own = max((gain[self.grid.cell(point)] for point in own), default=0.)
        if best_own >= .2:
            return ()
        budget_steps = self.limits.max_timestep_limit - self.elapsed_timestep
        if budget_steps < 240 or self.elapsed_walltime >= .80 * self.limits.max_walltime_limit:
            return ()
        candidates = []
        for point in points:
            cell = self.grid.cell(point)
            cost = costs[cell]
            if self.responsibility[cell] != self.identifier and cost <= min(420, budget_steps-120) and gain[cell] >= .2:
                candidates.append(point)
        return candidates

    def _mapping_search_rank(self, cells, gain, cost, point):
        # Untouched and under-observed map cells per estimated travel effort.
        information = len(cells) + sum(float(gain[cell]) for cell in sorted(cells))
        return -information / (150. + cost), cost, point

    def explore(self):
        t = self.elapsed_timestep
        if self.gap_probe is not None:
            return
        if self.awaiting_commit() or t < self.recovery_until:
            self.search_paused = self.search_task is not None
            return
        resumed = self.search_paused
        if t < self.next_explore and not resumed:
            return
        self.next_explore = t + self.SEARCH_REVIEW
        self.search_paused = False
        costs, work, pending = self.grid.search_work(self.pose)
        self.ready = False
        has_work = work.any()
        opening = self.phase != "dispose"
        mapping_only = getattr(self, "mapping_time_search", False)
        if has_work and opening:
            self.phase = "explore"
        peers = {i: s for i, s in self.fresh_states().items() if i != self.identifier}
        handoffs = {i: s["search_handoff"] for i, s in peers.items() if s.get("search_handoff") is not None}
        reserved = frozenset().union(*(cells for _, cells in handoffs.values()))
        claims = {i: s['search'] for i, s in peers.items() if s.get('search') is not None
                  and s['held'] is None and not s['queue'] and i not in handoffs}
        cell_claims = {i: peers[i]["opening_cells"] for i in claims if peers[i].get("opening_cells")}
        task = self.search_task
        if task is not None:
            # Live handoffs reserve only their own cells, even if an older search resumes nearby.
            other_cells = reserved
            if task.handoff is not None:
                older = (cells for version, cells in handoffs.values()
                         if (version[1], version[0]) < (task.handoff[1], task.handoff[0]))
                other_cells = frozenset().union(*older)
            overlap = frozenset()
            if task.handoff is None and cell_claims:
                earlier = (cells for i, cells in cell_claims.items()
                           if (claims[i][0], i) < (task.started, self.identifier))
                overlap = task.cells.intersection(frozenset().union(*earlier)) - other_cells
                other_cells |= overlap
                counter = "opening_released_claim_cells" if opening else "search_released_claim_cells"
                self.grid.compute_stats[counter] += len(overlap)
            if not task.cells.isdisjoint(other_cells):
                task.cells -= other_cells
                task.checked.intersection_update(task.cells)
                task.covered = self.grid.local_coverage(task.cells)
            if not task.cells:
                ended = 'shared' if overlap else 'handed_off'
            elif task.handoff is None and any(
                    (start, i) < (task.started, self.identifier)
                    and ((i not in cell_claims and self.grid.cell(point) in task.cells) or
                         (self.grid.speed_scale == 1 and self.phase == 'dispose' and distance(point, task.point) < 50
                          and self.grid.visible(point, task.point)))
                    for i, (start, point) in claims.items()):
                ended = 'shared'
            else:
                ended = self.continue_search(task, costs, work, pending, resumed)
            if ended is None:
                if resumed:
                    self.grid.compute_stats['search_resumed'] += 1
                return
            self.grid.compute_stats['search_' + ended] += 1
            self.search_task = None
            self.scout_until = 0
            if ended in ('unavailable', 'stalled'):
                self.search_retry = (t + 3 * self.SEARCH_REVIEW, task.cells)
        if has_work:
            occupied = {self.grid.cell(point) for _, point in claims.values()}
            if self.accept_search_handoff(costs, work, pending, reserved, occupied):
                return
            coordinating = not opening and any(
                s["held"] is None and not s["queue"] and distance(s["point"], self.pose) <= RANGE_COMMUNICATION
                for s in peers.values())
            if coordinating:
                # Let a new footprint reach neighbours before their next choice.
                delay = (2 * self.identifier - t) % (2 * self.limits.number_drones)
                if delay:
                    self.next_explore = t + delay
                    self.goal, self.route = tuple(self.pose), []
                    self.grid.compute_stats["search_claim_slot_waits"] += 1
                    return
            selectable = work.copy()
            for cell in reserved.union(*cell_claims.values()):
                selectable[cell] = False
            if self.search_retry is not None and t < self.search_retry[0]:
                for cell in self.search_retry[1]:
                    selectable[cell] = False
            blocks = {}
            partitions = self.grid.opening_tiles() if opening or coordinating else None
            gain = self.grid.frontier_gain() if partitions is not None else None
            weights = []
            for point, members in self.grid.target_blocks(selectable, partitions):
                if not self.search_route_allowed(point):
                    self.grid.compute_stats["search_birth_route_rejected"] += 1
                    continue
                cells = frozenset(map(tuple, members.tolist()))
                if (cells.isdisjoint(occupied) and
                        not (self.grid.speed_scale == 1 and self.phase == 'dispose'
                             and any(distance(point, other) < 50 and self.grid.visible(point, other)
                                     for _, other in claims.values()))):
                    blocks[point] = cells
                    weights.append(float(len(cells)) + (gain[tuple(members.T)].sum().item() if gain is not None else 0.))
            points = list(blocks)
            agents = {i: s["point"] for i, s in peers.items()
                      if i not in claims and i not in handoffs
                      and s["held"] is None and not s["queue"]}
            agents[self.identifier] = tuple(self.pose)
            preferred = [self.responsibility[self.grid.cell(p)] for p in points] if partitions is not None else None
            regions = allocate_regions(self.grid, agents, points, weights, preferred)
            assigned = regions[self.identifier]
            outbound = opening and self.anchor is not None
            if self.frontier_egress.released is not None:
                own = [point for point in points
                       if self.responsibility[self.grid.cell(point)] == self.identifier]
                if mapping_only:
                    assigned = assigned or own or points
                else:
                    support = self._empty_frontier_support(
                        own, points, gain if gain is not None else self.grid.frontier_gain(),
                        costs) if not self.carried_bombs_count() else ()
                    if support:
                        self.empty_frontier_support_event = (t, tuple(support))
                    assigned = support or own or assigned or points
            elif outbound and not assigned and points:
                assigned = points
            if assigned:
                if outbound:
                    depth = self.grid.tree(self.anchor)[0]
                    if self.grid.cell(self.pose) not in depth:
                        approaches = self.grid.contact_cells(self.anchor, 45, loaded=False)
                        depth = self.grid.tree_cells(approaches)[0]
                    point = min(assigned, key=lambda p: (costs[self.grid.cell(p)] / 4
                                - depth.get(self.grid.cell(p), 0) / 2.5, p))
                elif mapping_only:
                    if gain is None:
                        gain = self.grid.frontier_gain()
                    select = getattr(self, "_rank_redundant_search", None)
                    if select is None or self.frontier_egress.released is None:
                        point = min(assigned, key=lambda p: self._mapping_search_rank(blocks[p], gain, costs[self.grid.cell(p)], p))
                    else:
                        point = select(assigned, blocks, gain, costs, claims)
                else:
                    frontier = {}
                    if self.grid.speed_scale == 1:
                        if gain is None:
                            gain = self.grid.frontier_gain()
                        returns = self.grid.tree(self.home, loaded=True)[0] if self.home is not None else {}
                        # When known pickups are concentrated near the depot, send spare
                        # scouts to long-return branches while other drones clear the cluster.
                        origins = (self.pickup_origins.get(k, v[:2] if v[3] == 0 else None)
                                   for k, v in self.bombs.items())
                        short_work = sum(origin is not None and distance(origin, self.home) <= 1.5 * MAX_RANGE_SEMANTIC_SENSOR
                                         for origin in origins) if self.home is not None else 0
                        for p in assigned:
                            if gain[self.grid.cell(p)] >= .2:
                                frontier[p] = p
                            elif self.phase == "dispose" and (short_work >= 2 or coordinating):
                                edge = min(blocks[p], key=lambda c: (-gain[c], costs[c], c))
                                if gain[edge] >= .2:
                                    q = tuple(self.grid.point(edge))
                                    # Rescue a hidden frontier in a branch with a substantial return detour.
                                    if (returns.get(edge, 0.) > 1.65 * distance(q, self.home) + 120
                                            and not any(distance(q, other) < 50 and self.grid.visible(q, other)
                                                        for _, other in claims.values())):
                                        frontier[p] = q
                    scout = (frontier and self.phase == 'dispose' and self.home is not None
                             and t < .65 * self.limits.max_timestep_limit
                             and not any(s.get('scout_until', 0) > t and distance(s['point'], self.pose) < 170
                                         for s in peers.values()))
                    if scout:
                        # Spend one bounded scouting leg on work with a long return.
                        def scout_cost(p):
                            c = self.grid.cell(frontier[p])
                            return costs[c] / 4 - returns.get(c, 0) / 2.5 - 120 * gain[c]
                        point = min(frontier, key=scout_cost)
                        self.scout_until = t + min(300, 90 + math.ceil(costs[self.grid.cell(frontier[point])] / 3))
                        self.grid.compute_stats['search_scout_legs'] += 1
                    elif frontier:
                        def frontier_value(p):
                            c = self.grid.cell(frontier[p])
                            return gain[c] / (150 + costs[c])
                        point = max(frontier, key=frontier_value)
                    else:
                        closest = sorted(assigned, key=lambda p: costs[self.grid.cell(p)])[:12]
                        point = open_tour(self.grid, self.pose, closest)[0]
                cells = blocks[point]
                if not outbound and not mapping_only:
                    refined = frontier.get(point, point)
                    if self.search_route_allowed(refined):
                        point = refined
                original_point = point
                details = None
                if self.frontier_egress.released is not None and (outbound or mapping_only or not scout):
                    self.frontier_gate_audit = (t, audit_frontier(
                        getattr(self, "red_shadow_map", None), self.grid, self.pose,
                        cells, costs, original_point))
                    point, details = observation_point(
                        getattr(self, "red_shadow_map", None), self.grid, self.pose,
                        cells, costs, original_point, depth if outbound else None)
                if details is not None and not self.search_route_allowed(point):
                    point, details = original_point, None
                self.red_frontier_decision = (t, point, original_point, details)
                self.search_roaming.target = None
                if self.search_roaming.departed:
                    region = int(self.responsibility[self.grid.cell(point)])
                    self.search_roaming_event = t, "own" if region == self.identifier else "support", point, region
                covered = self.grid.local_coverage(cells)
                self.search_task = SearchTask(cells, point, t, self.search_steps, covered)
                self.set_search_point(self.search_task, point)
                self.grid.compute_stats['search_started'] += 1
                if opening:
                    if self.responsibility[self.grid.cell(point)] == self.identifier:
                        self.grid.compute_stats["opening_own_region_tasks"] += 1
                    else:
                        self.grid.compute_stats["opening_support_tasks"] += 1
            else:
                self.roam_when_idle(costs, peers)
            return
        self.roam_when_idle(costs, peers)

    def available(self, key):
        value = self.bombs.get(key)
        return value is not None and (value[3] == 0 or
                                      (value[3] == 3 and self.elapsed_timestep - value[2] >= 300))

    def pickup_candidate(self, key):
        return self.available(key) and self.elapsed_timestep - self.bombs[key][2] <= self.PICKUP_OBSERVATION_AGE

    def make_plan(self, first=False):
        states = self.fresh_states()
        blocked = tuple(self.bombs)
        t = self.elapsed_timestep
        agents = {i: Agent(i, s["point"], s["health"], self.resolve(s["held"]),
                           blocked if s.get("scout_until", 0) > t else tuple(self.resolve(k) for k in s.get("blocked", ())),
                           bool(s["queue"]) and self.claim_valid(s, self.resolve(s["queue"][0]))) for i, s in states.items()}
        agents[self.identifier] = Agent(self.identifier, tuple(self.pose), self.drone_health,
                                        self.task if self.carrying else None,
                                        blocked if self.scout_until > t else tuple(k for k, end in self.failed_pickups.items() if end > t),
                                        bool(self.queue) and self.task == self.queue[0] and self.elapsed_timestep - self.task_progress_step <= self.PICKUP_LEASE)
        claimed = {self.resolve(k) for i, s in self.states.items() if i not in agents
                   for k in s["queue"] if self.claim_valid(s, self.resolve(k))}
        if self.grid.speed_scale > 1:
            # A stale claim outside this group must not cancel a member's current pickup.
            claimed -= {self.resolve(k) for state in states.values() for k in state["queue"]}
        held = {a.held for a in agents.values() if a.held is not None}
        active = {self.resolve(s["queue"][0]) for s in states.values()
                  if s["queue"] and self.claim_valid(s, self.resolve(s["queue"][0]))}
        tasks = {k: v for k, v in self.bombs.items()
                 if k in held or (k not in claimed and (self.pickup_candidate(k) or (k in active and self.available(k))))}
        current = {i: tuple(self.resolve(k) for k in s["queue"] if self.resolve(k) in tasks and self.claim_valid(s, self.resolve(k))) for i, s in states.items()}
        for agent in agents.values():
            if agent.held is not None and agent.held not in tasks:
                return
        activate = self.elapsed_timestep + 25
        planner = self.dispatcher_class(self.grid, self.home, self.limits.max_timestep_limit, self.limits.number_drones)
        result = planner.solve(agents, tasks, activate, done=sum(v[3] == 2 for v in self.bombs.values()),
                               total=len(self.bombs), current=current, seconds=.24)
        self.last_planning = planner.statistics
        self.proposal = {"version": (self.elapsed_timestep, self.identifier), "activate": activate,
                         "first": first, "sequences": result.sequences, "legs": result.legs}
        self._map_message = self.map_snapshot()
        self.next_dispatch = self.elapsed_timestep + 160

    def coordinate(self):
        t = self.elapsed_timestep
        states = self.fresh_states()
        complete = len(states) == self.limits.number_drones
        proposal = self.proposal
        if proposal is not None and proposal["activate"] > t and self.identifier in proposal["sequences"]:
            sequence = [self.resolve(k) for k in proposal["sequences"][self.identifier]]
            keeps_load = not self.carrying or (sequence and sequence[0] == self.task)
            if self.early_pickup_until and sequence[:1] != self.queue:
                keeps_load = False
            if proposal["first"] and self.ack != proposal["version"]:
                self.ready = self.home is not None and not self.grid.targets(self.pose)[0]
            if keeps_load and (not proposal["first"] or (self.phase == "join" and self.ready)):
                self.ack = proposal["version"]
            elif self.ack == proposal["version"]:
                self.ack = None
        leader = min(states, default=self.identifier) if self.phase == "dispose" else 0
        if self.identifier == leader:
            members = set(proposal["sequences"]) if proposal else set()
            confirmed = members <= states.keys() and (not proposal["first"] or complete) if proposal else False
            if proposal is not None and t < proposal["activate"] and confirmed:
                if self.ack == proposal["version"] and all(states[i]["ack"] == self.ack for i in members if i != self.identifier):
                    self.commit = proposal
            pending = proposal is not None and t < proposal["activate"]
            if self.home is not None and not pending and t >= self.next_dispatch:
                if complete and self.phase == "join" and self.ready and all(s["ready"] for s in states.values()):
                    self.make_plan(first=True)
                elif self.phase == "dispose":
                    self.make_plan()
        commit = self.commit
        if commit is not None and self.identifier in commit["sequences"] and commit["version"] != self.applied and t >= commit["activate"]:
            self.phase = "dispose"
            if self.phase_started is None:
                self.phase_started = t
            self.applied = commit["version"]
            if self.early_pickup_until:
                return
            if (self.pickup_transfer and self.queue and not self.carrying
                    and self.resolve(self.pickup_transfer[0]) == self.resolve(self.queue[0])
                    and commit["version"][0] < self.pickup_transfer[2]):
                return
            # 只承诺下一个完整取送任务，避免失联无人机长期占用整串未来任务。
            queue = [self.resolve(k) for k in commit["sequences"][self.identifier]
                     if self.failed_pickups.get(self.resolve(k), 0) <= t][:1]
            if self.carrying:
                queue = [self.task]
            changed = queue != self.queue
            self.queue = queue
            self.legs = [(mode, self.resolve(k), tuple(path)) for mode, k, path in commit["legs"][self.identifier]
                         if self.resolve(k) in queue]
            if changed:
                self.pickup_transfer = None
                self.timed_path, self.path_index = (), 1
                self.next_route = t

    def update_load(self):
        previous = self.task
        origin = tuple(self.bombs.get(previous, self.pose)[:2]) if not self.carrying else None
        if self.update_cargo():
            self.search_offer = None
            self.pickup_transfer = None
            self.grid.set_carried_wall_guard(self.carrying)
            if self.carrying:
                if self.early_pickup_until:
                    self.grid.compute_stats["early_pickup_grasped"] += 1
                    self.early_pickup_until = 0
                self.pickup_origins[self.task] = origin
                self.begin_gap_exit()
                self.offer_search_handoff()
            else:
                if self.gap_exit is not None:
                    self.finish_gap_survey(False)
                self.gap_exit = None
            self.gap_entry = None
            if previous is not None and self.bombs[previous][3] == 2:
                self.remember_home((self.elapsed_timestep, self.identifier, *self.pose))
            self.delivery_point = None
            self.return_probe = None
            self.checked_return_cells.clear()
            self.return_corridor = frozenset()
            self.queue = [k for k in self.queue if k in self.bombs and self.bombs[k][3] in (0, 1)]
            self.timed_path, self.path_index = (), 1
            self.next_route = self.elapsed_timestep
            self.next_dispatch = min(self.next_dispatch, self.elapsed_timestep + 25)
            self.carried_progress.sync(bool(self.carrying), self.elapsed_timestep, self.pose, self.motion_pose)

    def remember_gap_entry(self):
        if self.motion_pose is None:
            return
        t, axis = self.elapsed_timestep, self.corridor_axis
        entry = self.gap_entry
        if entry is not None:
            start, inward, seen = entry
            along = float((self.motion_pose - start) @ inward)
            across = (self.motion_pose - start) - along * inward
            if t - seen > 100 or along < -22 or np.linalg.norm(across) > 26:
                self.gap_entry = entry = None
        if axis is not None:
            if entry is None or abs(float(axis @ entry[1])) < .85:
                self.gap_entry = (self.motion_pose.copy(), axis, t)
            else:
                self.gap_entry = (entry[0], entry[1], t)

    def remember_gap_passage(self, hits):
        """Share only the section the scout has already flown with a wall fit."""
        probe, t = self.gap_probe, self.elapsed_timestep
        if (probe is None or probe.passage is not None or probe.backing or probe.entrance is None
                or not self.grid.pose_fixed or probe.depth < 20 or t - probe.last_fit > 4):
            return
        entrance = np.asarray(probe.entrance)
        for key, hit in hits:
            offset = np.asarray(self.bombs[key][:2]) - entrance
            ahead = float(offset @ probe.axis)
            if ahead < probe.depth or np.linalg.norm(offset - ahead * probe.axis) > probe.width / 2 + 8:
                continue
            end = tuple(entrance + probe.depth * probe.axis)
            previous = self.gap_passage
            if (previous is None or self.resolve(previous.target) != key
                    or distance(end, previous.end) >= 10 or t - previous.step >= 60):
                self.gap_passage = GapPassage(self.identifier, t, key, probe.entrance, end,
                                              tuple(probe.axis), probe.width)
                probe.published = True
                self.grid.compute_stats["gap_passage_shared"] += 1

    def pickup_passage(self, key):
        if key is None or key not in self.bombs:
            return None
        t = self.elapsed_timestep
        records = (state.get("gap_passage") for state in self.states.values())
        return max((p for p in records if p is not None and t - p.step < self.GAP_PASSAGE_AGE
                    and self.resolve(p.target) == key), key=lambda p: p.step, default=None)

    def passage_approach(self, passage, stand=17, *, start=None):
        """Find a reachable approach on the same side as the recorded entrance."""
        axis = np.asarray(passage.axis)
        entrance = np.asarray(passage.entrance)
        staging = entrance - stand * axis
        costs, _ = self.grid.tree(self.pose if start is None else start)
        row, col = self.grid.cell(staging)
        choices = []
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                cell = row + dr, col + dc
                if cell in costs:
                    point = np.asarray(self.grid.point(cell))
                    along = float((point - entrance) @ axis)
                    lateral = np.linalg.norm(point - entrance - along * axis)
                    if -70 <= along <= -4 and lateral <= 38:
                        choices.append((distance(point, staging) + .03 * costs[cell], tuple(point)))
        return min(choices)[1] if choices else None

    def passage_offset(self, passage):
        direction = np.asarray(passage.axis)
        relative = self.pose - np.asarray(passage.entrance)
        along = float(relative @ direction)
        return direction, along, np.linalg.norm(relative - along * direction)

    def near_passage(self, passage):
        if passage is None or not self.grid.pose_fixed:
            return False
        _, along, lateral = self.passage_offset(passage)
        return -96 <= along <= 12 and lateral <= 38

    def gap_lidar(self, direction, ranges, *, entrance=False, recenter=False):
        angles = np.asarray(self.lidar_rays_angles())
        ranges = np.asarray(ranges)
        finite = np.isfinite(ranges) & (ranges > 5)
        bearings = angles[finite] + self.heading
        points = ranges[finite, None] * np.column_stack((np.cos(bearings), np.sin(bearings)))
        fit = self.corridor_walls(direction, points)
        if fit is None and entrance:
            # At the mouth, both side walls can be visible ahead of the hull.
            # Fit the same measured points around a point on the recorded axis.
            depth = points @ direction
            flank = np.array((-direction[1], direction[0]))
            shifts = (0., -10., 10., -17., 17.) if recenter else (0.,)
            for look in ((12., 22., 32., 44.) if recenter else (12., 22., 32.)):
                forward = (depth > look - 5) & (depth < look + 42)
                for shift in shifts:
                    translation = look * direction + shift * flank
                    fit = self.corridor_walls(direction, points[forward] - translation)
                    if fit is not None:
                        axis, width, offset = fit
                        normal = np.array((-axis[1], axis[0]))
                        return angles, ranges, finite, (axis, width, offset + float(translation @ normal))
        return angles, ranges, finite, fit

    def retreat_shared_gap(self, probe, ranges, velocity):
        """Clear the mouth before another drone starts its measured approach."""
        travel = float((self.motion_pose - probe.start) @ probe.axis)
        t = self.elapsed_timestep
        entrance = probe.entrance if probe.passage is None else probe.passage.entrance
        mouth_depth = float((self.pose - np.asarray(entrance)) @ probe.axis)
        clear = travel <= -13 and (not self.grid.pose_fixed or mouth_depth <= -19)
        if clear and probe.published and probe.pullout is None:
            candidates = []
            for cell, cost in self.grid.tree(self.pose)[0].items():
                if not 35 <= cost <= 115:
                    continue
                point = self.grid.point(cell)
                delta = np.asarray(point) - np.asarray(entrance)
                along = float(delta @ probe.axis)
                side = np.linalg.norm(delta - along * probe.axis)
                if -80 <= along <= -20 and side >= 48 and self.grid.visible(self.pose, point):
                    goal_cost = .15 * distance(point, self.goal) if self.goal is not None else 0.
                    candidates.append((cost + goal_cost, tuple(point)))
            if candidates:
                probe.pullout = min(candidates)[1]
                probe.last_move = t
                self.grid.compute_stats["gap_sender_pullouts"] += 1
        if probe.pullout is not None:
            if distance(self.pose, probe.pullout) > 12 and t - probe.last_move < 80:
                self.progress_pose, self.progress_step = tuple(self.pose), t
                return self.drive(probe.pullout, velocity)
            clear = True
        if clear or t - probe.last_move >= 185:
            self.gap_probe = None
            self.gap_scans.clear()
            self.next_explore = t
            if probe.passage is not None and self.resolve(probe.passage.target) == self.task:
                self.release_pickup("gap_no_progress")
            return self.motion_command(np.zeros(2), velocity, 0., .18, False)
        self.progress_pose, self.progress_step = tuple(self.pose), t
        delta = -max(8., travel + 18, mouth_depth + 23) * probe.axis
        if ranges is not None:
            angles, ranges, finite, fit = self.gap_lidar(-probe.axis, ranges)
            if fit is not None:
                desired, turn, self.corridor_axis = self.corridor_motion(
                    delta, ranges, angles, finite, backout=True, probe_fit=fit)
                return self.motion_command(desired, velocity, turn, .18, False, 3.7)
        return self.drive(self.pose + delta, velocity, backout=True)

    def inspect_gap(self, goal, ranges, velocity, mode, hits=()):
        """Keep a short empty-drone scan along a locally measured centre line."""
        t, probe = self.elapsed_timestep, self.gap_probe
        pickup = mode == "pickup"
        if (probe is not None and (probe.published or probe.passage is not None)
                and not self.carrying and self.motion_pose is not None):
            matching = (pickup and probe.passage is not None
                        and self.resolve(probe.passage.target) == self.task and not self.awaiting_commit())
            leaving = mode not in ("search", "explore") if probe.published else not matching
            if leaving and not probe.backing:
                probe.backing, probe.last_move = True, t
            if probe.backing:
                return self.retreat_shared_gap(probe, ranges, velocity)
        active_passage = probe.passage if probe is not None else None
        if active_passage is not None and self.resolve(active_passage.target) == self.task:
            passage = active_passage
        else:
            passage = self.pickup_passage(self.task) if pickup else None
        if ((mode not in ('search', 'explore') and passage is None)
                or (not pickup and self.queue) or self.carrying or self.awaiting_commit()
                or self.motion_pose is None or t < self.recovery_until):
            self.gap_probe = None
            self.gap_scans.clear()
            return None
        if probe is not None and pickup != (probe.passage is not None):
            self.gap_probe = probe = None
            self.gap_scans.clear()
        hit = next((h for key, h in hits if key == self.task), None) if pickup else None
        if probe is not None:
            travel = float((self.motion_pose - probe.start) @ probe.axis)
            if not probe.backing:
                if travel >= probe.depth + 3:
                    probe.last_move, probe.depth = t, travel
                    if pickup:
                        self.task_progress_step = t
                if not pickup and travel >= 25 * probe.station - 3:
                    probe.station += 1
                    self.grid.compute_stats['gap_probe_viewpoints'] += 1
                if pickup and hit is not None:
                    ray = np.array((math.cos(self.heading + hit.angle), math.sin(self.heading + hit.angle)))
                    if ray @ probe.axis > .9 and hit.distance <= MAX_RANGE_SEMANTIC_SENSOR:
                        probe.limit = max(probe.limit, travel + hit.distance)
                at_limit = travel >= probe.limit - 3 if pickup else probe.station > 3
                if at_limit or t - probe.last_move >= 36:
                    probe.backing, probe.last_move = True, t
            if probe.backing:
                if probe.published or probe.passage is not None:
                    return self.retreat_shared_gap(probe, ranges, velocity)
                if probe.retreat is None:
                    probe.retreat = (t, travel)
                began, last_depth = probe.retreat
                if travel < last_depth - 4:
                    probe.retreat = (began, travel)
                    probe.last_move = t
                clear = travel < 4
                if clear or t - probe.last_move >= 115 or t - began >= 320:
                    counter = "gap_empty_retreat_cleared" if clear else "gap_empty_retreat_expired"
                    self.grid.compute_stats[counter] += 1
                    self.gap_probe = None
                    self.gap_scans.clear()
                    self.next_explore = t
                    if pickup:
                        self.release_pickup("gap_no_progress")
                        return self.motion_command(np.zeros(2), velocity, 0., .18, False)
                    return None
                self.progress_pose, self.progress_step = tuple(self.pose), t
                return self.drive(self.pose - max(9., travel) * probe.axis, velocity, backout=True)
        elif pickup:
            if ranges is None or not self.near_passage(passage):
                return None
            direction, along, lateral = self.passage_offset(passage)
            source = self.fresh_states(20).get(passage.source)
            if source is not None and passage.source != self.identifier:
                delta = np.asarray(source["point"]) - np.asarray(passage.entrance)
                ahead = float(delta @ direction)
                if -19 < ahead < distance(passage.entrance, passage.end) + 35 and np.linalg.norm(delta - ahead * direction) < 25:
                    self.gap_scans.clear()
                    self.progress_pose, self.progress_step = tuple(self.pose), t
                    return self.drive(np.asarray(passage.entrance) - 72 * direction, velocity)
            if lateral > 22 or along < -38:
                self.progress_pose, self.progress_step = tuple(self.pose), t
                return self.drive(np.asarray(passage.entrance) - 18 * direction, velocity)
        else:
            if ranges is None or self.search_task is None or not self.grid.needs_alignment(self.pose, goal, False):
                return None
            delta = np.asarray(goal) - self.pose
            length = float(np.linalg.norm(delta))
            if length <= 5:
                return None
            direction = delta / length
            if velocity is not None and velocity @ direction > .65:
                return None
            if any(t - began < 360 and distance(self.pose, entry) < 40 and direction @ axis > .9
                   for began, entry, axis in self.recent_gap_entries):
                return None

        fit = None
        if ranges is not None:
            angles, ranges, finite, fit = self.gap_lidar(
                direction if probe is None else probe.axis, ranges, entrance=pickup)
        consistent = False
        if fit is not None and fit[1] >= 2 * self.grid.HULL_CLEARANCE:
            axis, width, offset = fit
            normal = np.array((-axis[1], axis[0]))
            centre = self.motion_pose + offset * normal
            self.gap_scans.append((t, axis, width, centre))
            consistent = sum(step >= t - 4 and axis @ old_axis > .978
                             and abs(width - old_width) <= 5 and abs((centre - old_centre) @ normal) <= 6
                             for step, old_axis, old_width, old_centre in self.gap_scans) >= 3
        if probe is None:
            if not consistent:
                if pickup and along < 5:
                    # Reach the recorded mouth at local-avoidance speed.
                    self.progress_pose, self.progress_step = tuple(self.pose), t
                    return self.drive(np.asarray(passage.entrance) + 8 * direction, velocity)
                if pickup:
                    return self.motion_command(np.zeros(2), velocity, 0., .18, False)
                return None
            if pickup:
                if abs(width - passage.width) > 5 or axis @ direction < .94:
                    return None
            else:
                # Only spend a separate inspection on coverage the current
                # viewpoint cannot already record as a near scan.
                look = self.pose + np.arange(100, 171, 20)[:, None] * axis
                cells = [self.grid.cell(p) for p in look]
                if all(self.grid.searched[c] == 2 or self.grid.evidence[c] >= 3 for c in cells):
                    return None
            self.gap_probe = probe = GapProbe(axis, self.motion_pose.copy(), t)
            if pickup:
                probe.passage = passage
                recorded_depth = float((np.asarray(passage.end) - self.pose) @ axis)
                # At the end of the record, one cell of live-checked motion
                # can bring the target into this receiver's own sensor range.
                probe.limit = max(15., recorded_depth + self.grid.CELL)
                self.grid.compute_stats['gap_pickup_started'] += 1
                if passage.source != self.identifier:
                    self.grid.compute_stats['gap_passage_received'] += 1
            else:
                if self.grid.pose_fixed:
                    probe.entrance = tuple(self.pose + offset * normal)
                    probe.width = width
                self.recent_gap_entries.append((t, tuple(self.pose), axis))
                self.grid.compute_stats['gap_probe_started'] += 1
            travel = 0.
        self.progress_pose, self.progress_step = tuple(self.pose), t
        if not consistent:
            course = math.atan2(probe.axis[1], probe.axis[0])
            turn = (course - self.heading + math.pi / 2) % math.pi - math.pi / 2
            self.corridor_axis = None
            return self.motion_command(np.zeros(2), velocity, turn, .18, False)
        probe.last_fit = t
        grasp = False
        if (pickup and hit is not None and hit.distance < 35
                and width / 2 - abs(offset) >= self.grid.HULL_CLEARANCE and self.pickup_blocker() is None):
            grasp = self.pickup_finish(tuple(self.pose), self.task, confirm=True) <= self.limits.max_timestep_limit
        remaining = max(6., (probe.limit if pickup else 25 * probe.station) - travel)
        desired, turn, self.corridor_axis = self.corridor_motion(
            remaining * probe.axis, ranges, angles, finite, (hit,) if grasp else (), probe_fit=fit)
        return self.motion_command(desired, velocity, turn, .18, grasp, 3.7)

    def begin_gap_exit(self):
        if self.gap_entry is None or self.corridor_axis is None or self.motion_pose is None:
            return
        start, inward, seen = self.gap_entry
        t = self.elapsed_timestep
        if t - seen > 8:
            return
        axis = self.corridor_axis
        if float(axis @ inward) < 0:
            axis = -axis
        depth = float((self.motion_pose - start) @ axis)
        if depth >= 10:
            self.gap_exit = GapExit(-axis, self.motion_pose.copy(), depth + 44, t, t)
            self.prepare_gap_survey(axis, depth)

    def survey_event(self, event, offer, count=None, **details):
        self.grid.compute_stats["survey_" + event] += 1
        self.survey_events.append(dict(step=self.elapsed_timestep, event=event, drone=self.identifier,
                                       source=offer.source, issued=offer.step, recipient=offer.recipient,
                                       entrance=offer.entrance, end=offer.end,
                                       cells=len(offer.cells) if count is None else int(count), **details))

    def survey_remaining(self, cells):
        close = self.grid.close_scan_cells()
        return frozenset(c for c in cells if self.grid.searched[c] <= int(close[c])
                         and self.grid.evidence[c] < 3)

    def survey_footprint(self, offer):
        # Only inherit connected, observed free space near the last verified point.
        # A rasterised narrow lane can be absent from the graph; its live-checked
        # centre line can still lead to the next observation point.
        end, axis = np.asarray(offer.end), np.asarray(offer.axis)
        row, col = self.grid.cell(end)
        shape = self.grid.evidence.shape
        costs, _ = self.grid.tree(end, narrow=True)
        free = set()
        for r in range(max(0, row - 5), min(shape[0], row + 6)):
            for c in range(max(0, col - 5), min(shape[1], col + 6)):
                cell = r, c
                if self.grid.evidence[cell] >= 0:
                    continue
                point = self.grid.centres[cell]
                offset = point - end
                along = float(offset @ axis)
                if np.linalg.norm(offset) > 100 or along < -45 or (point - offer.entrance) @ axis < 20:
                    continue
                lane = (abs(along) <= 45 and np.linalg.norm(offset - along * axis) <= offer.width / 2
                        and self.grid.visible(end, point))
                if costs.get(cell, math.inf) <= 120 or lane:
                    free.add(cell)
        # A blind pocket can start just beyond two connected free cells. Only
        # offer its first unknown cell, never a rectangle behind an unseen wall.
        fringe = set()
        for r, c in free:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if (r - dr, c - dc) not in free:
                    continue
                a, b = r + dr, c + dc
                cell = a, b
                if not (0 <= a < shape[0] and 0 <= b < shape[1]
                        and self.grid.evidence[cell] == 0
                        and self.grid.clearance[cell] >= self.grid.HULL_CLEARANCE):
                    continue
                point = self.grid.centres[cell]
                if np.linalg.norm(point - end) <= 100 and (point - offer.entrance) @ axis > 30:
                    fringe.add(cell)
        return self.survey_remaining(free | fringe)

    def prepare_gap_survey(self, axis, depth):
        if not self.grid.pose_fixed:
            return
        t = self.elapsed_timestep
        ranges = self.lidar_values()
        fit = self.gap_lidar(axis, ranges)[-1] if ranges is not None else None
        probe = self.gap_probe
        if fit is None and (probe is None or probe.passage is None or t - probe.last_fit > 4):
            return
        width = fit[1] if fit is not None else probe.passage.width
        end = self.pose.copy()
        if fit is not None:
            direction, _, offset = fit
            if direction @ axis >= .95:
                axis = direction
                end += offset * np.array((-axis[1], axis[0]))
        entrance = end - depth * axis
        if probe is not None and probe.passage is not None:
            # Prefer the previously measured mouth if our actual ingress agrees.
            earlier = np.asarray(probe.passage.entrance)
            offset = end - earlier
            along = float(offset @ axis)
            if abs(along - depth) <= 65 and np.linalg.norm(offset - along * axis) <= 12:
                entrance = earlier
        if distance(entrance, end) < 20 or width < 2 * self.grid.HULL_CLEARANCE:
            return
        draft = GapSurvey(self.identifier, t, tuple(entrance), tuple(end), tuple(axis), width,
                          frozenset(), t + 640)
        self.gap_survey = replace(draft, cells=self.survey_footprint(draft))
        if self.gap_survey.cells:
            self.survey_event("waiting", self.gap_survey)

    def finish_gap_survey(self, clear):
        offer = self.gap_survey
        if offer is None or offer.clear:
            return
        t = self.elapsed_timestep
        _, along, _ = self.passage_offset(offer)
        if not clear or not self.grid.pose_fixed or along > -22:
            self.survey_event("exit_unconfirmed", offer, exit_check=bool(clear),
                              pose_fixed=bool(self.grid.pose_fixed), along=round(along, 1))
            self.gap_survey = None
            return
        cells = self.survey_footprint(offer)
        if not cells:
            self.survey_event("no_remaining", offer, 0)
            self.gap_survey = None
            return
        traverse = math.ceil(1.7 * distance(offer.entrance, offer.end))
        self.gap_survey = replace(offer, cells=cells, clear=t, expires=t + min(700, 280 + traverse))
        self.survey_event("clear", self.gap_survey)

    def nominate_survey_receiver(self):
        offer, t = self.gap_survey, self.elapsed_timestep
        if offer is not None and t >= offer.expires:
            self.gap_survey = None
            return
        if (offer is None or not offer.clear or offer.recipient is not None
                or t % 15 != self.identifier % 15 or self.communicator_is_disabled()):
            return
        cells = self.survey_remaining(offer.cells)
        if not cells:
            self.survey_event("covered_by_team", offer, 0)
            self.gap_survey = None
            return
        outer = np.asarray(offer.entrance) - 40 * np.asarray(offer.axis)
        costs, _ = self.grid.tree(outer)
        peers = []
        axis = np.asarray(offer.axis)
        for i, s in self.fresh_states().items():
            if (i == self.identifier or s["held"] is not None or s["queue"]
                    or s.get("scout_until", 0) > t or s.get("search_handoff") is not None
                    or distance(s["point"], self.pose) > RANGE_COMMUNICATION):
                continue
            delta = np.asarray(s["point"]) - offer.entrance
            depth = float(delta @ axis)
            lateral = np.linalg.norm(delta - depth * axis)
            approach = costs.get(self.grid.cell(s["point"]), math.inf)
            in_mouth = -45 <= depth < distance(offer.entrance, offer.end) and lateral < 25
            if not in_mouth and (approach > 180 and
                    (distance(s["point"], outer) > 90 or not self.grid.visible(s["point"], outer))):
                continue
            peers.append((not in_mouth, distance(s["point"], offer.entrance) +
                          .15 * min(approach, 180) + 18 * (s["search"] is not None), i))
        if peers:
            self.gap_survey = replace(offer, recipient=min(peers)[2], cells=cells)
            self.survey_event("assigned", self.gap_survey)

    def claim_gap_survey(self):
        t = self.elapsed_timestep
        if (self.carrying or self.queue or self.motion_pose is None or self.awaiting_commit()
                or t < self.recovery_until or t < self.scout_until or not self.grid.pose_fixed
                or t % 15 != self.identifier % 15 or self.communicator_is_disabled()):
            return
        for state in self.states.values():
            offer = state.get("gap_survey")
            if (offer is None or not offer.clear or offer.recipient != self.identifier or t >= offer.expires
                    or offer.version in self.survey_used):
                continue
            if any(lane is not None and (t < lane.expires + 450 or t - peer["step"] <= 20)
                   and distance(lane.entrance, offer.entrance) < 40
                   and abs(np.dot(lane.axis, offer.axis)) > .85
                   for peer in self.states.values() for lane in (peer.get("survey_lane"),)):
                continue
            cells = self.survey_remaining(offer.cells)
            if not cells:
                self.survey_used.add(offer.version)
                self.survey_event("covered_by_team", offer, 0)
                continue
            entrance, axis = np.asarray(offer.entrance), np.asarray(offer.axis)
            _, along, lateral = self.passage_offset(offer)
            staged = -38 <= along < distance(offer.entrance, offer.end) and lateral < 23
            if self.gap_probe is not None and (not staged or self.gap_probe.passage is not None
                    or self.gap_probe.backing or self.gap_probe.axis @ axis < .9):
                continue
            if staged:
                stage, route = tuple(self.pose), ()
            else:
                stage = self.passage_approach(offer, stand=42)
                route = self.grid.route(self.pose, stage) if stage is not None else ()
                if not route:
                    continue
                offsets = np.asarray(route) - entrance
                depth = offsets @ axis
                if np.any((depth > 0) & (depth < distance(offer.entrance, offer.end))
                          & (np.linalg.norm(offsets - depth[:, None] * axis, axis=1) < 30)):
                    continue
            offer = replace(offer, cells=cells)
            self.survey_run = SurveyRun(offer, stage, deque(route), t,
                                        staged=staged,
                                        coverage={c: int(self.grid.searched_here[c]) for c in cells})
            self.gap_probe = None
            self.gap_scans.clear()
            self.timed_path, self.path_index = (), 1
            self.survey_used.add(offer.version)
            self.survey_event("claimed", offer)
            return

    def yield_survey_mouth(self, goal, velocity):
        t = self.elapsed_timestep
        for state in self.states.values():
            offer = state.get("survey_lane")
            # The receiver can pass out of radio range while inside. Hold its
            # approach until it reports leaving or the bounded retreat window ends.
            if (offer is None or offer.recipient == self.identifier
                    or (t >= offer.expires + 450 and t - state["step"] > 20)):
                continue
            axis, along, lateral = self.passage_offset(offer)
            if not (-65 <= along < 40 and lateral < 36):
                continue
            if along >= -18 and lateral < 25:
                return self.drive(np.asarray(offer.entrance) - 60 * axis, velocity, backout=True)
            direction = np.asarray(goal) - self.pose
            depth = float(direction @ axis)
            if depth < 6 or along + depth < -12:
                continue
            cross = self.pose + (-along / depth) * direction - offer.entrance
            if np.linalg.norm(cross) < 30:
                normal = np.array((-axis[1], axis[0]))
                side = 1 if (self.pose - offer.entrance) @ normal >= 0 else -1
                return self.drive(np.asarray(offer.entrance) - 78 * axis + side * 50 * normal, velocity)
        return None

    def survey_mouth_offset(self, offer, axis, along, angles, ranges, finite):
        """Measure the open interval between the two sides of the mouth."""
        normal = np.array((-axis[1], axis[0]))
        expected = float((np.asarray(offer.entrance) - self.pose) @ normal)
        direction = math.atan2(axis[1], axis[0]) - self.heading
        scan = np.where(finite, ranges, 0.)
        lateral = expected + np.arange(-48., 49., 2.)
        candidates = []
        for shift in (0., 8., 16., -8.):
            depth = shift - along
            if not 12 <= depth <= 75:
                continue
            angle = np.arctan2(lateral, depth)
            rays = (direction + angle + math.pi) % (2 * math.pi) - math.pi
            through = np.interp(rays, angles, scan) * np.cos(angle) > depth + 7
            for first, last in np.flatnonzero(np.diff(np.r_[False, through, False])).reshape(-1, 2):
                if first == 0 or last == len(through):
                    continue
                width = 2 * (last - first)
                centre = (lateral[first] + lateral[last - 1]) / 2
                if max(22, offer.width - 18) <= width <= offer.width + 10:
                    candidates.append((abs(width - offer.width) + .3 * abs(centre - expected)
                                       + abs(shift) / 8, float(centre)))
        return min(candidates)[1] if candidates else None

    def run_gap_survey(self, ranges, velocity):
        if self.survey_run is None:
            self.claim_gap_survey()
        run, t = self.survey_run, self.elapsed_timestep
        if run is None:
            return None
        offer = run.offer
        axis, along, lateral = self.passage_offset(offer)
        entrance, end = np.asarray(offer.entrance), np.asarray(offer.end)
        pending = self.survey_remaining(offer.cells)
        if not run.retreat:
            close = self.grid.close_scan_cells()
            count = sum(bool(self.grid.searched_here[c] > max(int(close[c]), run.coverage[c]))
                        for c in offer.cells)
            if count > run.scanned:
                self.survey_event("scan", offer, count)
                run.scanned, run.last_move = count, t
            if (not pending or self.queue or self.carrying or self.awaiting_commit()
                    or t >= offer.expires or t - run.last_move >= 105):
                self.survey_event("finished" if not pending and run.scanned else
                                  "covered_by_team" if not pending else "interrupted", offer, run.scanned,
                                  along=round(along, 1), lateral=round(lateral, 1))
                if not run.inside and along <= 0:
                    self.survey_run = None
                    return None
                run.retreat, run.last_move = True, t
                run.depth = along
        if run.retreat:
            if along < run.depth - 5:
                run.depth, run.last_move = along, t
            while run.backtrack and distance(self.pose, run.backtrack[-1]) < 12:
                run.backtrack.pop()
                run.last_move = t
            if run.backtrack and t - run.last_move < 135:
                return self.drive(run.backtrack[-1], velocity)
            if (along < -34 and lateral < 45) or t - run.last_move >= 135:
                self.survey_event("receiver_left" if along < -34 and lateral < 45
                                  else "receiver_exit_unconfirmed", offer, run.scanned)
                self.survey_run = None
                return None
            return self.drive(entrance - 56 * axis, velocity, backout=True)
        if ranges is None or not self.grid.pose_fixed:
            return self.motion_command(np.zeros(2), velocity, 0., .18, False)
        if not run.staged:
            while len(run.route) > 1 and distance(self.pose, run.route[0]) < 13:
                run.route.popleft()
                run.last_move = t
            if distance(self.pose, run.stage) >= 14:
                return self.drive(run.route[0], velocity)
            run.staged, run.last_move = True, t
            run.route.clear()
        if along > run.depth + 4:
            run.depth, run.last_move = along, t
        if not run.inside and along >= 12 and lateral <= offer.width / 2:
            run.inside = True
            self.survey_event("entered", offer)
        if not run.passed and run.inside and lateral <= offer.width / 2 and along >= distance(entrance, end) - 7:
            run.passed, run.last_move = True, t
            run.backtrack.append(tuple(self.pose))
        if run.passed:
            # The inherited prefix ends here. Any turn uses our own free-space graph.
            if distance(self.pose, run.backtrack[-1]) >= 18:
                run.backtrack.append(tuple(self.pose))
            while run.route and distance(self.pose, run.route[0]) < 12:
                run.route.popleft()
                run.last_move = t
            if run.route and t - run.last_move >= 55:
                run.route.clear()
            if not run.route and t % 15 == self.identifier % 15:
                costs, _ = self.grid.tree(self.pose, narrow=True)
                targets = [self.grid.point(c) for c in pending]
                points = []
                for c, cost in costs.items():
                    if not 20 <= cost <= 150 or c in run.viewpoints or self.grid.clearance[c] < 23:
                        continue
                    p = self.grid.point(c)
                    if (p - entrance) @ axis < distance(entrance, end) - 10:
                        continue
                    gain = sum(distance(p, q) <= 72 and self.grid.visible(p, q) for q in targets)
                    if gain:
                        points.append((cost + 55 / gain, c))
                if points:
                    cell = min(points)[1]
                    run.viewpoints.add(cell)
                    point = self.grid.point(cell)
                    run.route.extend(self.grid.route(self.pose, point, narrow=True)[1:])
                    run.last_move = t
            if run.route:
                return self.drive(run.route[0], velocity)
            return self.motion_command(np.zeros(2), velocity, .28, .18, False)
        angles, ranges, finite, fit = self.gap_lidar(axis, ranges, entrance=True, recenter=along < 24)
        if fit is not None:
            direction, width, offset = fit
            normal = np.array((-direction[1], direction[0]))
            if (abs(width - offer.width) <= 5 and direction @ axis >= .94
                    and width >= 2 * self.grid.HULL_CLEARANCE):
                centre = self.motion_pose + offset * normal
                run.fit.append((t, direction, width, centre))
                if sum(step >= t - 4 and direction @ other >= .978 and abs(width - w) <= 5
                       and abs((centre - point) @ normal) <= 6 for step, other, w, point in run.fit) >= 3:
                    delta = max(6., distance(entrance, end) - along) * axis
                    desired, turn, self.corridor_axis = self.corridor_motion(
                        delta, ranges, angles, finite, probe_fit=fit)
                    return self.motion_command(desired, velocity, turn, .18, False, 3.7)
        if along < 4:
            offset = self.survey_mouth_offset(offer, axis, along, angles, ranges, finite)
            if offset is not None:
                normal = np.array((-axis[1], axis[0]))
                if abs(offset) > 3:
                    return self.drive(self.pose + min(0., -14 - along) * axis
                                      + np.clip(1.8 * offset, -32, 32) * normal, velocity)
                return self.drive(self.pose + (8 - along) * axis + offset * normal, velocity)
            return self.drive(entrance + 8 * axis, velocity)
        course = math.atan2(axis[1], axis[0])
        turn = (course - self.heading + math.pi / 2) % math.pi - math.pi / 2
        return self.motion_command(np.zeros(2), velocity, turn, .18, False)

    def back_out_of_gap(self, velocity):
        gap = self.gap_exit
        if gap is None:
            return None
        t = self.elapsed_timestep
        travel = float((self.motion_pose - gap.start) @ gap.axis)
        if travel >= gap.best + 5:
            gap.best, gap.last_move = travel, t
        clear = travel >= max(gap.minimum, gap.last_wall + 36)
        if clear or t - gap.last_move >= 135 or t - gap.began >= 640:
            self.finish_gap_survey(clear)
            if not clear:
                self.search_offer = None
            self.gap_exit = None
            self.timed_path, self.legs, self.path_index, self.next_route = (), [], 1, t
            self.recovery_until, self.progress_pose, self.progress_step = 0, tuple(self.pose), t
            return None
        goal = tuple(self.pose + 60 * gap.axis)
        command = self.drive(goal, velocity, backout=True)
        if self.corridor_axis is not None:
            gap.last_wall = travel
        self.mode, self.goal, self.motion_goal = "deliver", goal, goal
        self.timed_path, self.path_index = (), 1
        self.search_paused, self.scout_until = self.search_task is not None, 0
        self._last_grasper = command["grasper"]
        self.publish()
        return command

    def remember_home(self, record):
        """保留共同的处置区参考点，实际返程站位另选。"""
        if self.home_fix is None or record[:2] < self.home_fix[:2]:
            self.home_fix = tuple(record)
            self.home = tuple(record[2:])

    def depot_cells(self):
        """复用通信中已观察到的站位和实际处置回执。"""
        confirmed = {tuple(v[:2]) for v in self.bombs.values() if v[3] == 2}
        if self.home_fix is not None:
            confirmed.add(self.home)
        observed = {s.get("depot_stance") for s in self.states.values()}
        observed.add(self.depot_stance)

        def cells(points):
            return tuple(sorted({cell for p in points if p is not None and self.grid.evidence[self.grid.cell(p)] < 3
                                 for cell in self.grid.contact_cells(p, 25, loaded=True)}))

        return cells(confirmed), cells(observed)

    def delivery_target(self):
        """当共同参考点没有通路时，转到本机可达的实际交付站位。"""
        t = self.elapsed_timestep
        if self.home is None or t < self.carried_progress.next_check:
            return self.delivery_point or self.home
        reachable = self.grid.tree(self.pose, loaded=True)[0]
        confirmed, observed = self.depot_cells()
        current = self.grid.cell(self.delivery_point) if self.delivery_point is not None else None
        home_connected = any(c in reachable for c in self.grid.contact_cells(self.home, 75))
        chosen = self.delivery_point if current in reachable and current in confirmed else None
        if chosen is None and not home_connected:
            for group in (confirmed, observed):
                cell = min((c for c in group if c in reachable),
                           key=lambda c: (c != current, reachable[c], c), default=None)
                if cell is not None:
                    chosen = tuple(self.grid.point(cell))
                    break
        if chosen != self.delivery_point:
            self.delivery_point = chosen
            self.timed_path, self.legs = (), []
            self.next_route = t
        return self.delivery_point or self.home

    def local_route(self, goal):
        """只修改自己的已分配任务路径；失联时不抢占其他无人机的任务。"""
        t = self.elapsed_timestep
        limit = self.limits.max_timestep_limit
        horizon = t + limit if self.carrying else limit
        reservations = Reservations(self.grid, horizon)
        nearby = []
        priority = traffic_priority(self.identifier, self.pose, self.carrying, self.home)
        for i, state in self.fresh_states(60).items():
            if i == self.identifier or traffic_priority(i, state["point"], state["held"] is not None, self.home) > priority:
                continue
            if distance(self.pose, state["point"]) < 100:
                nearby.append(state["point"])
            path = progress_path(state, t, self.grid.speed_scale)
            if path and path[-1][0] > t:
                reservations.add(path, park_until=min(self.limits.max_timestep_limit, path[-1][0] + 20))
            else:
                reservations.add(((t, *state["point"]), (t + 15, *state["point"])))
        narrow = ()
        passage = None
        connected_return = False
        if not self.carrying:
            passage = self.pickup_passage(self.task)
            approach = self.passage_approach(passage) if passage is not None else None
            if approach is not None:
                goal = approach
            elif not self.grid.route(self.pose, goal, contact=True):
                self.release_pickup("approach_unavailable")
                return
        elif (self.grid.route(self.pose, goal, loaded=True, contact=True)
              or (narrow := self.grid.route(self.pose, goal, loaded=True, contact=True, narrow=True))):
            connected_return = True
            if self.return_probe is not None:
                self.timed_path, self.legs = (), []
            self.return_probe = None
        elif self.grid.speed_scale > 1:
            goal = self.pickup_point(goal, loaded=True)
        else:
            if self.return_probe is not None:
                point, until = self.return_probe
                if (t >= until or distance(self.pose, point) < 20
                        or self.grid.cell(point) not in self.grid.tree(self.pose, loaded=True)[0]):
                    self.checked_return_cells.add(self.grid.cell(point))
                    self.return_probe = None
            if self.return_probe is None:
                confirmed, observed = self.depot_cells()
                ends = confirmed or observed or self.grid.contact_cells(goal, 75)
                frontier = self.grid.return_frontier(self.pose, goal, ends, self.checked_return_cells,
                                                     self.return_corridor)
                if frontier is not None:
                    point, length = frontier
                    self.return_probe = point, t + math.ceil(length / 2) + 120
                    if self.grid.cell(point) in self.return_corridor:
                        self.carried_progress.stats["return_route_probes"] += 1
            if self.return_probe is not None:
                goal = self.return_probe[0]
        if narrow:
            path = time_route(self.grid, self.pose, narrow, t + 2, reservations, loaded=True, narrow=True)
            if path:
                self.carried_progress.stats["narrow_return_plans"] += 1
        else:
            path = safe_path(self.grid, tuple(self.pose), goal, t + 2, reservations, self.carrying, compare=True)
        if connected_return and path:
            self.return_corridor = frozenset(c for a, b in zip(path, path[1:])
                for c in reservations.sweep(a[1:], b[1:], self.grid.CELL))
        if path or not self.timed_path or self.timed_path[-1][0] < t:
            self.timed_path, self.path_index = path, 1
        self.next_route = t + 45
        if nearby and not path and not any(a <= t + 2 < b for a, b in reservations.safe(self.grid.cell(self.pose))):
            # 起点已处在优先路径的缓冲区内，继续原地等会堵住对方；先按激光净空退让。
            if self.grid.speed_scale > 1 or passage is not None:
                costs, _ = self.grid.tree(self.pose, loaded=self.carrying)
                safe_points = []
                for cell in costs:
                    point = tuple(self.grid.point(cell))
                    if (25 < distance(self.pose, point) <= 85 and self.grid.visible(self.pose, point)
                            and any(a <= t + 2 and t + 60 <= b for a, b in reservations.safe(cell))):
                        safe_points.append(point)
                if safe_points:
                    goal_weight = .8 if passage is not None else .1
                    self.recovery_point = min(safe_points,
                        key=lambda p: distance(self.pose, p) + goal_weight * distance(p, goal))
                    if passage is not None:
                        self.grid.compute_stats["gap_reservation_pullouts"] += 1
                    self.recovery_until, self.progress_step = t + 30, t
                    self.next_route = self.next_explore = t + 30
                    self.timed_path, self.legs, self.path_index = (), [], 1
                    return
            peer = min(nearby, key=lambda p: distance(self.pose, p))
            self.recover(2 * self.pose - np.asarray(peer), self.lidar_values(), force=True)

    def early_trip(self, point, key, finish_by, *, returning=False):
        """Plan on the observed grid and verify loaded clearance along the return."""
        t = self.elapsed_timestep
        limit = finish_by - self.EARLY_TRIP_BUFFER
        if limit <= t + 2:
            return ()
        # Contact tracking can move the gripper away from the planned pickup stance.
        # Start early trips only where that motion has room on the observed map.
        target = self.bombs[key][:2]
        if any(self.grid.clearance[self.grid.cell(p)] < self.EARLY_CONTACT_CLEARANCE
               for p in (point, target)):
            return ()
        reservations = Reservations(self.grid, limit)
        for identifier, state in self.fresh_states().items():
            if identifier == self.identifier or not (state["held"] is not None or state["queue"]):
                continue
            path = progress_path(state, t, self.grid.speed_scale)
            if path:
                reservations.add(path)
        planner = Dispatcher(self.grid, self.home, limit, self.limits.number_drones)
        agent = Agent(self.identifier, point, self.drone_health, key if returning else None)
        trip = planner.trip(agent, key, self.bombs, t + 2, reservations)
        if not trip:
            return ()
        path = trip[-1][2]
        loaded = self.grid.walkable(loaded=True) & (self.grid.clearance >= 32)
        if any(not loaded[cell] for a, b in zip(path, path[1:])
               for cell in reservations.sweep(a[1:], b[1:])):
            return ()
        return trip

    def assign_early(self, hits):
        t = self.elapsed_timestep
        if (not hits or self.phase != "explore" or self.home is None or self._odometry_only
                or t < self.next_early_check or t < self.recovery_until or self.search_paused
                or t % self.limits.number_drones != self.identifier):
            return
        peers = [s for i, s in self.fresh_states().items()
                 if i != self.identifier and distance(s["point"], self.pose) <= RANGE_COMMUNICATION]
        if any(s["phase"] != "dispose" and (s["held"] is not None or s["queue"]) for s in peers):
            return
        task = self.search_task
        if task is not None and not self.reached_search_point(task.point):
            if not (self.route and self.reached_search_point(self.route[0])
                    and any(s.get("search") is not None for s in peers)):
                return
        claimed = {self.resolve(k) for i, s in self.states.items() if i != self.identifier
                   for k in s["queue"] if self.claim_valid(s, self.resolve(k))}
        nearest = min(((hit.distance, key) for key, hit in hits
                       if hit.distance < 65 and key not in claimed and self.available(key)
                       and self.failed_pickups.get(key, 0) <= t), default=None)
        if nearest is None:
            return
        self.next_early_check = t + 15
        key = nearest[1]
        finish_by = min(self.exploration_deadline, t + self.EARLY_TRIP_STEPS)
        trip = self.early_trip(tuple(self.pose), key, finish_by)
        if trip:
            self.queue, self.legs = [key], list(trip)
            self.early_pickup_until = finish_by
            self.grid.compute_stats["early_pickup_started"] += 1

    def observed_depot_finish(self, point, key, reservations, *, confirm):
        """Time a return to a sensed depot stance, including the pickup leg when needed."""
        now = self.elapsed_timestep + 2
        costs = self.grid.tree(point, loaded=confirm)[0]
        contacts = () if confirm else self.grid.contact_cells(self.bombs[key][:2])
        for group in self.depot_cells():
            if not group:
                continue
            if confirm:
                cell = min((c for c in group if c in costs), key=costs.__getitem__, default=None)
                if cell is None:
                    continue
                route = self.grid.route(point, self.grid.point(cell), loaded=True)
                depart, at = point, now
            else:
                returns, parents = self.grid.tree_cells(group, loaded=True)
                contact = min((c for c in contacts if c in costs and c in returns),
                              key=lambda c: costs[c] / 4 + returns[c] / 2.5, default=None)
                if contact is None:
                    continue
                approach = self.grid.route(point, self.grid.point(contact))
                pickup = time_route(self.grid, point, approach, now, reservations) if approach else ()
                if not pickup:
                    continue
                at, *depart = pickup[-1]
                cells = [contact]
                while cells[-1] in parents:
                    cells.append(parents[cells[-1]])
                route = tuple(self.grid.point(c) for c in cells)
            path = time_route(self.grid, depart, route, at, reservations, loaded=True) if route else ()
            if path:
                return path[-1][0]
        return math.inf

    def pickup_finish(self, point, key, *, confirm=False):
        """领取与抓取均检查从当前机位到实际交付的完整时间。"""
        t = self.elapsed_timestep
        limit = self.limits.max_timestep_limit - self.EARLY_TRIP_BUFFER
        if confirm and self.early_pickup_until:
            trip = self.early_trip(point, key, self.early_pickup_until, returning=True)
            if trip:
                self.legs = [leg for leg in self.legs if leg[0] == "pickup"] + list(trip)
                return trip[-1][2][-1][0]
            return math.inf
        reservations = Reservations(self.grid, limit)
        for identifier, state in self.fresh_states().items():
            if identifier != self.identifier and state["held"] is not None:
                path = progress_path(state, t, self.grid.speed_scale)
                if path:
                    reservations.add(path)
        if confirm and self.grid.speed_scale == 1:
            finish = self.observed_depot_finish(point, key, reservations, confirm=True)
            if math.isfinite(finish):
                return finish
        if not confirm or self.grid.speed_scale > 1:
            planner = Dispatcher(self.grid, self.home, limit, self.limits.number_drones)
            trip = planner.trip(Agent(self.identifier, point, self.drone_health, key if confirm else None),
                                key, self.bombs, t + 2, reservations)
            if trip:
                return trip[-1][2][-1][0]
            # A backup stance is useful when this drone can verify the target
            # or is already following a pickup plan. It cannot open a new
            # pickup from a remote report alone.
            if confirm or key in self.local_pickup_hits or key in self.queue:
                finish = self.observed_depot_finish(point, key, reservations, confirm=confirm)
                if math.isfinite(finish):
                    self.grid.compute_stats["observed_depot_pickup_routes"] += 1
                    return finish

        # A measured passage permits a bounded inspection from its entrance.
        # An isolated target coordinate does not justify leaving a search route.
        passage = self.pickup_passage(key)
        if passage is None or not self.grid.pose_fixed:
            return math.inf
        staging = self.passage_approach(passage, start=self.home)
        if staging is None:
            return math.inf
        probe = self.gap_probe
        inside = (probe is not None and probe.passage is not None
                  and self.resolve(probe.passage.target) == key and distance(point, self.pose) < 1)
        if confirm and not inside:
            return math.inf
        scale = self.grid.speed_scale
        if inside:
            departure = t + move_time(distance(point, staging), loaded=True, scale=scale)
        else:
            approach = self.grid.route(point, staging)
            path = time_route(self.grid, point, approach, t + 2, reservations) if approach else ()
            if not path:
                return math.inf
            depth = distance(staging, self.bombs[key][:2])
            departure = path[-1][0] + move_time(depth, scale=scale) + move_time(depth, loaded=True, scale=scale)
        route = self.grid.route(staging, self.home, loaded=True, contact=True)
        path = time_route(self.grid, staging, route, departure, reservations, loaded=True) if route else ()
        return path[-1][0] if path else math.inf

    def check_pickup_return(self, key):
        """Inspect a reachable frontier when a nearby observed pickup lacks a return connection."""
        t = self.elapsed_timestep
        if (not self.grid.pose_fixed or self.grid.speed_scale != 1 or self.scout_until > t
                or t < self.recovery_until or self.gap_probe is not None or self.survey_run is not None):
            return False
        peers = [s for i, s in self.fresh_states().items() if i != self.identifier]
        if any(s.get("scout_until", 0) > t and distance(s["point"], self.pose) <= RANGE_COMMUNICATION
               for s in peers):
            return False
        nominal = self.grid.contact_cells(self.home, 75, loaded=True)
        confirmed, observed = self.depot_cells()
        ends = tuple(sorted(set(nominal + confirmed + observed)))
        if not ends:
            return False
        approach = self.grid.tree(self.pose)[0]
        contacts = [c for c in self.grid.contact_cells(self.bombs[key][:2]) if c in approach]
        returns = self.grid.tree_cells(ends, loaded=True)[0]
        if not contacts or any(c in returns for c in contacts):
            return False
        frontier = self.grid.return_frontier(self.pose, self.home, ends, self.checked_pickup_returns)
        if frontier is None:
            return False
        point, length = frontier
        window = 2 * self.SEARCH_REVIEW + math.ceil(length / 3)
        if window > self.SEARCH_STALL:
            return False
        possible = self.grid.tree_cells(ends, loaded=True, optimistic=True)[0]
        return_steps = min((possible.get(c, math.inf) for c in contacts)) / 2.5
        if t + window + return_steps + self.EARLY_TRIP_BUFFER > self.limits.max_timestep_limit:
            return False
        cell = self.grid.cell(point)
        self.checked_pickup_returns.add(cell)
        cells = frozenset({cell})
        self.scout_until = t + window
        self.search_task = SearchTask(cells, point, t, self.search_steps, self.grid.local_coverage(cells),
                                      return_check_until=self.scout_until)
        self.search_paused = False
        self.set_search_point(self.search_task, point)
        self.grid.compute_stats["pickup_return_checks"] += 1
        return True

    def assign_local(self, hits=()):
        """通信组暂时没有提交计划时，领取没有新鲜队友声明的已知任务。"""
        t = self.elapsed_timestep
        if self.queue or self.carrying or self.home is None:
            return
        limit = self.limits.max_timestep_limit
        if t >= limit:
            return
        self.pickup_transfer = None
        unchecked = None
        if t >= self.next_contact_check:
            self.next_contact_check = t + 10
            for _, key in sorted((h.distance, k) for k, h in hits if h.distance < 65 and self.available(k)
                                  and self.failed_pickups.get(k, 0) <= t):
                owners = [s for i, s in self.states.items() if i != self.identifier
                          and self.claim_valid(s, key) and any(self.resolve(k) == key for k in s["queue"])]
                if any(s.get("pickup_since") is None or t - s["progress"][1] < self.SEARCH_REVIEW
                       or distance(s["point"], self.bombs[key])
                       <= 150 + 4 * self.grid.speed_scale * max(0, t - s["step"]) for s in owners):
                    continue
                finish = self.pickup_finish(tuple(self.pose), key)
                if not math.isfinite(finish) and unchecked is None:
                    unchecked = key
                if finish <= limit and all(self.pickup_finish(s["point"], key) > finish + self.SEARCH_REVIEW
                                           for s in owners):
                    self.queue = [key]
                    if owners:
                        versions = tuple((s["id"], s["pickup_since"]) for s in owners)
                        self.pickup_transfer = (key, versions, t)
                        self.grid.compute_stats["pickup_transfers"] += 1
                    return
        if unchecked is not None and self.check_pickup_return(unchecked):
            return
        if t < self.next_assign:
            return
        claimed = {self.resolve(k) for i, s in self.states.items() if i != self.identifier
                   for k in s["queue"] if self.claim_valid(s, self.resolve(k))}
        candidates = [k for k in self.bombs if self.pickup_candidate(k) and k not in claimed
                      and self.failed_pickups.get(k, 0) <= t]
        if self.scout_until > t:
            nearby = {k for k, hit in hits if hit.distance < 65}
            candidates = [k for k in candidates if k in nearby]
        if candidates and any(i != self.identifier and s["held"] is None and not s["queue"]
                              and distance(s["point"], self.pose) <= RANGE_COMMUNICATION
                              for i, s in self.fresh_states().items()):
            delay = (2 * self.identifier - t) % (2 * self.limits.number_drones)
            if delay:
                self.next_assign = t + delay
                self.grid.compute_stats["pickup_claim_slot_waits"] += 1
                return
        self.next_assign = t + 50
        if candidates:
            # 探索预算不足以横跨地图时，空闲组统一领取；其余场景沿用邻近领取。
            if self.exploration_deadline >= max(self.grid.size) / 4:
                candidates.sort(key=lambda k: self.grid.geodesic(self.pose, self.bombs[k][:2]))
                self.queue = next(([k] for k in candidates if self.pickup_finish(tuple(self.pose), k) <= limit), [])
                return
            free = {i: s["point"] for i, s in self.fresh_states().items()
                    if s["held"] is None and not s["queue"]}
            free[self.identifier] = tuple(self.pose)
            ids, candidates = sorted(free), sorted(candidates)
            costs = np.array([[self.grid.geodesic(free[i], self.bombs[k][:2]) / 4
                               + self.grid.geodesic(self.bombs[k][:2], self.home) / 2.5
                               for k in candidates] for i in ids])
            penalty = (len(ids) + 1) * self.limits.max_timestep_limit
            for row, i in enumerate(ids):
                for col, key in enumerate(candidates):
                    if (self.pickup_finish(free[i], key) > limit or
                            key in self.states.get(i, {}).get("blocked", ())):
                        costs[row, col] = penalty
            costs = np.column_stack((costs, np.full((len(ids), len(ids)), penalty)))
            rows, cols = linear_sum_assignment(costs)
            self.queue = [candidates[k] for row, k in zip(rows, cols) if ids[row] == self.identifier
                          and k < len(candidates) and costs[row, k] < penalty]

    def pickup_point(self, target, loaded=False):
        """取送目标暂不可达时先到可达观测点，更新位置和局部地图。"""
        if self.grid.route(self.pose, target, loaded=loaded, contact=True):
            return tuple(target)
        costs, _ = self.grid.tree(self.pose, loaded=loaded)
        cell = min(costs, key=lambda c: distance(self.grid.point(c), target) + .02 * costs[c])
        return tuple(self.grid.point(cell))

    def disposal_goal(self, hits=()):
        # 已被抓取的任务只由实际载荷持有者继续，空载队友立即释放旧分配。
        self.task = self.resolve(self.task)
        self.queue = [k for k in map(self.resolve, self.queue)
                      if self.available(k) or (self.carrying and k == self.task)]
        if self.early_pickup_until and not self.queue:
            self.release_pickup("early_pickup_unavailable")
        if not self.carrying and self.task is not None and self.task in self.queue:
            self.task_progress(self.bombs[self.task][:2], False)
            if self.elapsed_timestep - self.task_progress_step > self.PICKUP_LEASE:
                self.release_pickup("no_progress")
        if self.phase == "dispose":
            self.assign_local(hits)
        self.reconcile_pickup()
        if (not self.carrying and self.queue and not self.early_pickup_until
                and (self.queue[0] != self.task or self.elapsed_timestep >= self.next_trip_check)):
            self.next_trip_check = self.elapsed_timestep + 45
            if self.pickup_finish(tuple(self.pose), self.queue[0]) > self.limits.max_timestep_limit:
                self.release_pickup("trip_unavailable", self.queue[0])
        if not self.carrying:
            task = self.queue[0] if self.queue else None
            if task != self.task:
                self.missing_since = None
                self.timed_path, self.path_index = (), 1
                self.next_route = self.elapsed_timestep
                self.pickup_since = self.elapsed_timestep if task is not None else None
            self.task = task
        if self.task is not None and not self.carrying:
            self.task_progress(self.bombs[self.task][:2], False)
        if self.carrying:
            mode, goal = "deliver", self.delivery_target()
            self.carried_progress.update(self, goal)
        elif self.task is not None:
            mode, goal = "pickup", tuple(self.bombs[self.task][:2])
        else:
            self.explore()
            return "search"
        if self.home is None:
            self.explore()
            return "search"
        moved = self.goal is None or distance(goal, self.goal) > 35
        self.goal = tuple(goal)
        if mode == "pickup":
            active = self.gap_probe.passage if self.gap_probe is not None else None
            if ((active is not None and self.resolve(active.target) == self.task)
                    or self.near_passage(self.pickup_passage(self.task))):
                # The current corridor maneuver verifies live clearance on each
                # step. A timed route to the staging cell is no longer active.
                self.timed_path, self.path_index = (), 1
                self.next_route = self.elapsed_timestep
                return mode
        if not self.timed_path and (mode != "pickup" or self.pickup_passage(self.task) is None):
            committed = next((path for m, k, path in self.legs if m == mode and k == self.task), ())
            if (committed and committed[-1][0] > self.elapsed_timestep
                    and distance(committed[0][1:], self.pose) < 45
                    and (mode != "deliver" or self.delivery_point is None
                         or self.grid.cell(committed[-1][1:]) == self.grid.cell(goal))):
                self.timed_path, self.path_index = committed, 1
                self.next_route = self.elapsed_timestep + 45
        if self.elapsed_timestep % 5 == self.identifier % 5 and self.path_obstructed():
            self.timed_path, self.legs = (), []
            self.next_route = self.elapsed_timestep
        late = bool(self.timed_path and self.path_index < len(self.timed_path)
                    and self.elapsed_timestep > self.timed_path[self.path_index][0] + 12
                    and distance(self.pose, self.timed_path[self.path_index][1:]) > 20)
        if (not self.timed_path or moved or late or self.elapsed_timestep > self.timed_path[-1][0] + 12) and self.elapsed_timestep >= self.next_route:
            self.local_route(goal)
            if mode == "pickup" and self.task is None:
                self.explore()
                return "search"
        return mode

    def path_obstructed(self):
        """Revalidate the current segment against obstacles observed after planning."""
        if not self.timed_path or self.path_index >= len(self.timed_path):
            return False
        end = self.timed_path[self.path_index][1:]
        points = np.linspace(self.pose, end, max(2, math.ceil(distance(self.pose, end) / 5)))
        here = self.grid.cell(self.pose)
        return any(self.grid.evidence[cell] >= 3 for cell in (self.grid.cell(p) for p in points)
                   if cell != here)

    def _progress_pose_changed(self, target, step):
        return self.progress_pose is None or distance(self.pose, self.progress_pose) > 12

    def recover(self, goal, ranges, force=False):
        """局部控制长时间没有位移时，向有净空的方向退出，再重算路径。"""
        t = self.elapsed_timestep
        target = self.goal if not force and self.phase == "dispose" and self.mode != "search" and not self.timed_path else goal
        if self._progress_pose_changed(target, t):
            self.progress_pose, self.progress_step = tuple(self.pose), t
        if self.awaiting_commit() or distance(target, self.pose) < 20:
            self.progress_step = t
        if t >= self.recovery_until and (force or t - self.progress_step > 90) and ranges is not None:
            ranges = np.asarray(ranges)
            angles = self.heading + np.asarray(self.lidar_rays_angles())
            desired = math.atan2(target[1] - self.pose[1], target[0] - self.pose[0])
            score = np.nan_to_num(ranges) + 35 * np.cos(angles - desired)
            index = int(np.argmax(score))
            self.recovery_point = tuple(self.pose + min(85, max(0, ranges[index] - 40))
                                        * np.array([math.cos(angles[index]), math.sin(angles[index])]))
            self.recovery_until, self.progress_step = t + 30, t
            self.next_route = self.next_explore = t + 30
            self.timed_path = ()
        return self.recovery_point if t < self.recovery_until else goal

    def reached_search_point(self, point):
        return distance(self.pose, point) < (9 if self.grid.tight[self.grid.cell(point)] else 22)

    def waypoint(self):
        if self.awaiting_commit():
            return tuple(self.pose)
        if self.mode in ("pickup", "deliver"):
            if not self.timed_path or self.elapsed_timestep < self.timed_path[0][0]:
                return tuple(self.pose)
            while self.path_index < len(self.timed_path):
                at, *point = self.timed_path[self.path_index]
                tolerance = 9 if self.grid.needs_alignment(self.pose, point, self.carrying) else 20
                if self.elapsed_timestep < at or distance(self.pose, point) > tolerance:
                    break
                self.path_index += 1
            return self.timed_path[min(self.path_index, len(self.timed_path) - 1)][1:]
        reached = getattr(self, '_search_waypoint_reached', self.reached_search_point)
        while self.route and reached(self.route[0]):
            self.route.pop(0)
        if not self.route:
            return tuple(self.pose)
        skip = 0
        shortcut_allowed = getattr(self, '_search_shortcut_allowed', None)
        for index, point in enumerate(self.route[1:6], start=1):
            cells = [self.grid.cell(p) for p in np.linspace(self.pose, point, max(2, math.ceil(distance(self.pose, point) / 10)))]
            if (all(self.grid.evidence[c] < 0 and self.grid.clearance[c] >= 23 for c in cells)
                    and self.search_roaming.allows(self.pose, self.goal, [point])
                    and (shortcut_allowed is None or shortcut_allowed(point))):
                skip = index
            else:
                break
        # The checked shortcut replaces its skipped prefix.
        del self.route[:skip]
        return self.route[0]

    def pickup_blocker(self):
        """A grasper can attach to a nearby carried bomb as well as the intended free one."""
        held = [h for h in (self.semantic_values() or []) if h.grasped and h.distance < 65]
        if held:
            hit = min(held, key=lambda h: h.distance)
            angle = self.heading + hit.angle
            return self.pose + hit.distance * np.array([math.cos(angle), math.sin(angle)])
        peers = [s for i, s in self.fresh_states(15).items() if i != self.identifier
                 and distance(self.pose, s["point"]) < 80
                 and self.grid.visible(self.pose, s["point"])
                 and (s["held"] is not None or (i < self.identifier and s["queue"]
                      and s["goal"] is not None and distance(s["point"], s["goal"]) < 60))]
        return min(peers, key=lambda s: distance(self.pose, s["point"]))["point"] if peers else None

    def allow_pickup_contact(self):
        """Allow a short live contact attempt during a generic recovery."""
        t = self.elapsed_timestep
        if t < self.carrier_yield_until:
            return False
        window = self.pickup_contact_window
        if window is not None and window[0] == self.task and t < window[1]:
            return True
        if t < self.next_pickup_contact_window:
            return False
        target = np.asarray(self.bombs[self.task][:2])
        # A teammate must be approaching search work on the far side of
        # the target. In an isolated pickup, the usual recovery still runs.
        for identifier, peer in self.fresh_states(15).items():
            search = peer["search"]
            if identifier == self.identifier or search is None or peer["held"] is not None or peer["queue"]:
                continue
            point = np.asarray(peer["point"])
            offset = target - point
            if not 12 < np.linalg.norm(offset) < 110:
                continue
            direction = np.asarray(search[1]) - point
            length = np.linalg.norm(direction)
            if length <= self.grid.CELL:
                continue
            direction /= length
            ahead = float(offset @ direction)
            if 10 < ahead < length - self.grid.CELL and np.linalg.norm(offset - ahead * direction) < 30:
                self.pickup_contact_window = (self.task, t + 24)
                self.next_pickup_contact_window = t + 90
                self.grid.compute_stats["pickup_contact_recovery_windows"] += 1
                return True
        return False

    def yield_to_carrier(self, goal, ranges):
        """Move out of the carrier's current approach and keep the pullout for the recovery interval."""
        t = self.elapsed_timestep
        if self.carrying or t < self.recovery_until or t % 5 != self.identifier % 5:
            return
        for peer in sorted(self.fresh_states(8).values(), key=lambda s: distance(self.pose, s["point"])):
            if peer["held"] is None or peer["motion_goal"] is None:
                continue
            start = np.asarray(peer["point"])
            offset = self.pose - start
            if np.linalg.norm(offset) > 110 or not self.grid.visible(self.pose, start):
                continue
            delta = np.asarray(peer["motion_goal"]) - start
            length = np.linalg.norm(delta)
            if length < 10:
                continue
            direction = delta / length
            ahead = float(offset @ direction)
            if (not 0 < ahead < length + 35 or np.linalg.norm(offset - ahead * direction) >= 44
                    or (np.asarray(goal) - self.pose) @ direction > 35):
                continue
            costs, _ = self.grid.tree(self.pose)
            pullouts = []
            for cell, length_to_cell in costs.items():
                if not 24 <= length_to_cell <= 85:
                    continue
                point = np.asarray(self.grid.point(cell))
                relative = point - start
                side = relative - (relative @ direction) * direction
                if np.linalg.norm(side) >= 55 and self.grid.visible(self.pose, point):
                    pullouts.append((length_to_cell, tuple(point)))
            if pullouts:
                self.recovery_point = min(pullouts)[1]
                self.recovery_until, self.progress_step = t + 30, t
                self.next_route = self.next_explore = self.recovery_until
                self.timed_path, self.legs = (), []
            else:
                self.recover(self.pose + 85 * direction, ranges, force=True)
            self.carrier_yield_until = self.recovery_until
            return

    def control(self):
        self.receive()
        self.grid.tick = self.elapsed_timestep
        velocity, hits, depot_hits = self._sense()
        egress = self.frontier_egress.update(self.elapsed_timestep, self.pose,
                                            self.grid.pose_fixed, self._odometry_only)
        if egress is not None:
            self.frontier_egress_event = (self.elapsed_timestep, *egress)
        if self.pose is None:
            return {"forward": 0., "lateral": 0., "rotation": .2, "grasper": int(bool(self.grasped_bombs()))}
        self.search_roaming.observe(self.frontier_egress.origin, self.pose)
        if velocity is not None and np.all(np.isfinite(velocity)):
            if self.motion_pose is None:
                self.motion_pose = np.zeros(2)
            self.motion_pose += velocity
        if self.anchor is None and self.identifier == 0:
            self.anchor = tuple(self.pose)
        if self.grid.speed_scale == 1 and self.depot_stance is None and depot_hits:
            if 65 <= min(hit[0] for hit in depot_hits) <= 95:
                self.depot_stance = tuple(self.pose)
        if self.carrying and depot_hits and self.home_fix is None:
            self.home = tuple(min(depot_hits, key=lambda item: item[0])[1])
        if self.elapsed_timestep % 20 == self.identifier % 20:
            self.consolidate_tracks()
        hits = [(self.resolve(key), hit) for key, hit in hits]
        self.local_pickup_hits = {key for key, _ in hits}
        self.remember_gap_passage(hits)
        ranges = self.lidar_values()
        if ranges is not None and self.semantic_values() is not None and self.elapsed_timestep % 5 == self.identifier % 5:
            task = self.search_task
            measuring_handoff = task and task.handoff and not task.handoff_scanned and not self.search_paused
            previous_coverage = self.grid.local_coverage(task.cells) if measuring_handoff else 0
            self.grid.observe_semantics(self.pose, self.heading, np.asarray(ranges), np.asarray(self.lidar_rays_angles()))
            if measuring_handoff and self.grid.local_coverage(task.cells) > previous_coverage:
                task.handoff_scanned = True
                self.grid.compute_stats["search_handoff_first_scan"] += 1
                self.grid.compute_stats["search_handoff_gap_steps"] += self.elapsed_timestep - task.handoff[1]
        self.update_load()
        if (self.carrying and self.search_task is not None and self.gap_exit is None and self.gap_survey is None
                and self.elapsed_timestep % self.SEARCH_REVIEW == self.identifier % self.SEARCH_REVIEW
                and (self.search_offer is None or self.elapsed_timestep >= self.search_offer.expires)):
            self.offer_search_handoff()
        if self.gap_survey is not None:
            self.nominate_survey_receiver()
        self.advance_phase()
        if self.early_pickup_until and self.elapsed_timestep >= self.early_pickup_until:
            self.release_pickup("early_pickup_expired", self.queue[0] if self.queue else self.task)
        review_transit = getattr(self, '_review_transit_frontier', None)
        if review_transit is not None:
            review_transit(self.elapsed_timestep)
        if self.phase != "dispose" and not (self.carrying or self.queue or self.survey_run):
            self.assign_early(hits)
            if not self.queue:
                self.explore()
        self.publish()
        self.coordinate()
        command = self.back_out_of_gap(velocity)
        if command is not None:
            return command
        if self.survey_run is not None or self.elapsed_timestep % 15 == self.identifier % 15:
            command = self.run_gap_survey(ranges, velocity)
        if command is not None:
            self.mode, self.motion_goal = "search", None
            self.search_paused = self.search_task is not None
            self._last_grasper = command["grasper"]
            self.publish()
            return command
        mode = self.disposal_goal(hits) if self.phase == "dispose" or self.carrying or self.queue else self.phase
        self.mode = mode
        if self.carrying or self.queue:
            self.scout_until = 0
        if (mode in ("explore", "search") and not self.carrying and not self.queue and self.route
                and not self.search_roaming.allows(self.pose, self.goal, self.route)):
            self.route = []
            self.search_task = None
            self.search_roaming.target = None
            self.next_explore = self.elapsed_timestep
        goal, contacts = self.waypoint(), []
        if mode == "pickup" and self.task is not None:
            visible = any(key == self.task for key, _ in hits)
            arrived = (self.pickup_passage(self.task) is None and self.timed_path
                       and distance(self.pose, self.timed_path[-1][1:]) < 25)
            if (not visible and (arrived or distance(self.pose, self.bombs[self.task]) < 45)
                    and (self.grid.speed_scale <= 1 or (distance(self.pose, self.bombs[self.task]) < 75
                         and self.grid.visible(self.pose, self.bombs[self.task][:2])))):
                if self.missing_since is None:
                    self.missing_since = self.elapsed_timestep
                elif self.elapsed_timestep - self.missing_since > 80:
                    self.bombs[self.task][2:] = [self.elapsed_timestep, 3]
                    self.queue = [k for k in self.queue if k != self.task]
                    self.task, self.timed_path = None, ()
            else:
                self.missing_since = None
        if mode == "pickup":
            contacts = [h for key, h in hits if key == self.task and h.distance < 65]
            if not contacts and ranges is not None and self.grid.tight[self.grid.cell(self.pose)]:
                seen = min((h for key, h in hits if key == self.task), key=lambda h: h.distance, default=None)
                if seen is not None:
                    angle = self.heading + seen.angle
                    sight = seen.distance * np.array([math.cos(angle), math.sin(angle)])
                    r = np.asarray(ranges)
                    if self.corridor_motion(sight, r, np.asarray(self.lidar_rays_angles()), np.isfinite(r)) is not None:
                        contacts = [seen]
        elif mode == "deliver":
            at_stance = self.delivery_point is not None and distance(self.pose, self.delivery_point) < 35
            contacts = [item[2] for item in depot_hits if item[0] < (105 if at_stance else 75)]
        awaiting = self.awaiting_commit()
        if contacts and not awaiting:
            hit = min(contacts, key=lambda h: h.distance)
            angle = self.heading + hit.angle
            goal = tuple(self.pose + (hit.distance + 8) * np.array([math.cos(angle), math.sin(angle)]))
        else:
            contacts = []
        self.yield_to_carrier(goal, ranges)
        if mode in ("search", "explore") and not self.carrying:
            command = self.yield_survey_mouth(goal, velocity)
            if command is not None:
                self.search_paused = self.search_task is not None
                self._last_grasper = command["grasper"]
                self.publish()
                return command
        command = self.inspect_gap(goal, ranges, velocity, mode, hits)
        if command is not None:
            self.remember_gap_entry()
            self.search_steps += 1
            self._last_grasper = command["grasper"]
            self.publish()
            return command
        contact_goal = goal
        goal = self.recover(goal, ranges)
        recovering = self.elapsed_timestep < self.recovery_until
        grasp = mode == "pickup" and not awaiting and any(h.distance < 35 for h in contacts)
        blocker = None
        if grasp and (not recovering or self.elapsed_timestep >= self.carrier_yield_until):
            blocker = self.pickup_blocker()
        if recovering:
            if grasp and blocker is None and self.allow_pickup_contact():
                goal = contact_goal
            else:
                grasp, contacts, blocker = False, [], None
        if blocker is not None:
            grasp, contacts = False, []
            goal = self.recover(2 * self.pose - np.asarray(blocker), ranges, force=True)
        if grasp:
            finish = self.pickup_finish(tuple(self.pose), self.task, confirm=True)
            self.pickup_forecast = {"step": self.elapsed_timestep, "task": self.task,
                                    "finish": finish if math.isfinite(finish) else None}
            grasp = finish <= self.limits.max_timestep_limit
            if not grasp:
                self.release_pickup("deadline")
                contacts = []
                goal = tuple(self.pose)
        self.motion_goal = tuple(goal) if self.carrying else None
        command = self.drive(goal, velocity, contacts,
                             grasp=grasp)
        if not self.carrying:
            self.remember_gap_entry()
        if mode == "deliver" and depot_hits and min(h[0] for h in depot_hits) < 55:
            self.docking += 1
            if self.docking > 20:
                command["rotation"] = .7 if self.identifier % 2 else -.7
        else:
            self.docking = 0
        tight = self.grid.tight[self.grid.cell(self.pose)] or self.grid.tight[self.grid.cell(goal)]
        if (mode != "deliver" and not contacts
                and distance(goal, self.pose) < (6 if tight else 20)):
            command["rotation"] = .4
        if self.search_task is not None:
            self.search_paused = (self.carrying or mode not in ('explore', 'search') or awaiting
                                  or self.elapsed_timestep < self.recovery_until)
            if not self.search_paused:
                self.search_steps += 1
        self._last_grasper = command["grasper"]
        self.publish()
        return command

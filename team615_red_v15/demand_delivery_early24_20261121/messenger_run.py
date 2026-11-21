"""Deliver confirmed empty-stock facts only while drone 0 still lacks them."""
import math
from collections import deque

import numpy as np

from swarm_rescue.solutions.deadline_submission import DeadlineSubmission

IDLE, ACTIVE, DONE = "IDLE", "ACTIVE", "DONE"
APPROACH, HOLD, EXIT_ZONE = "APPROACH", "HOLD", "EXIT_ZONE"


class MessengerRun:
    MESSENGER_ID = 4
    START_FRAC = 40                 # percent of step limit before activation
    COMM_RANGE = 180
    EXCHANGE_HOLD = 12              # frames held inside the contact circle
    WAIT_PEER_FRAMES = 120          # wait at a stale last-known position
    ARRIVE_TOL = 25.0               # considered arrived at last-known point
    SECOND_ROUND_MIN_STEPS = 1500   # need this much budget to run another tour
    STALE_STEPS = 60                # a peer state older than this may be in NoCom
    APPROACH_STALL_WINDOW = 120     # no-progress window before giving up a target
    APPROACH_STALL_MOVE = 15.0      # below this displacement it is a local minimum
    EXIT_LOOKAHEAD = 150.0          # rolling goal distance; direction is held
    EXIT_TURN_ANGLE = math.pi / 3   # sweep to the next heading only on a stall
    EXIT_MAX_ATTEMPTS = 6           # bounded sweeps cover the full circle
    RECEIVER = 0
    DIRECT_TTL = 3
    DELIVERY_STEPS = 200
    SEND_MARGIN = 12
    MIN_WALL_SECONDS = 8.

    def __init__(self):
        self.state = IDLE
        self.phase = APPROACH
        self.target = None
        self.visited = set()
        self.round = 0
        self.hold_left = 0
        self.wait_start = None
        self.audit = []
        self.contacts = 0
        self.approach_poses = deque(maxlen=self.APPROACH_STALL_WINDOW + 1)
        # NoCom departure sub-state
        self.exit_dir = None
        self.exit_goal = None
        self.exit_attempts = 0
        self.exit_poses = deque(maxlen=self.APPROACH_STALL_WINDOW + 1)
        self.receiver_seen = False
        self.receiver_empty = set()
        self.receiver_sent_step = -1
        self.receiver_received_step = -1
        self.attempted_empty = set()
        self.task_payload = set()
        self.delivery_until = None
        self.contact_step = None

    def receive(self, drone, message, step):
        if int(drone.identifier) != self.MESSENGER_ID or message.get("id") != self.RECEIVER:
            return
        own = next((s for s in message.get("states", ())
                    if isinstance(s, dict) and s.get("id") == self.RECEIVER), None)
        stamp = None if own is None else own.get("step")
        if type(stamp) is not int or not 0 <= stamp <= step:
            return
        records = message.get("red_inventory")
        if not isinstance(records, dict):
            return
        for owner, record in records.items():
            if (type(owner) is int and 0 <= owner < drone.team_size
                    and isinstance(record, (tuple, list)) and len(record) == 2
                    and type(record[0]) is int and 0 <= record[0] <= stamp
                    and record[1] == 0):
                self.receiver_empty.add(owner)
        self.receiver_seen = True
        if stamp > self.receiver_sent_step:
            self.receiver_sent_step = stamp
            if step-stamp <= self.DIRECT_TTL:
                self.receiver_received_step = step

    def _needed(self, drone, step):
        if not self.receiver_seen:
            return set()
        confirmed = {owner for owner, (stamp, count) in drone.inventory_records.items()
                     if type(owner) is int and 0 <= owner < drone.team_size
                     and 0 <= stamp <= step and count == 0}
        # Drone 0 always knows its own local inventory. Zero-stock facts do not expire.
        return confirmed - self.receiver_empty - {self.RECEIVER}

    def _budget(self, drone, step):
        return min(self.DELIVERY_STEPS,
                   DeadlineSubmission.window_start(drone.limit)-self.SEND_MARGIN-step)

    def _finish(self, step, reason):
        self.audit.append((step, reason, self.RECEIVER, tuple(sorted(self.task_payload))))
        self.state = DONE
        self.target = None
        self.delivery_until = None
        self.contact_step = None
        self._clear_exit()

    # -- activation ----------------------------------------------------------
    def _can_activate(self, drone, step):
        if int(drone.identifier) != self.MESSENGER_ID:
            return False
        inv = drone.previous_inventory
        if inv is None or int(inv) != 0 or drone.pending_drop is not None:
            return False
        return step >= drone.limit * self.START_FRAC // 100

    def _alive_peers(self, drone):
        out = []
        for peer, st in drone.states.items():
            if (isinstance(peer, int) and peer != int(drone.identifier)
                    and isinstance(st, dict) and st.get("health", 0) > 0):
                out.append(peer)
        return out

    def _peer_point(self, drone, peer):
        st = drone.states.get(peer)
        if not st or "point" not in st:
            return None
        return np.asarray(st["point"], dtype=float)

    def _pick_target(self, drone, step):
        if (not self._needed(drone, step) - self.attempted_empty or self._budget(drone, step) <= 0
                or drone.walltime_limit-drone.elapsed_walltime <= self.MIN_WALL_SECONDS):
            return None
        state = drone.states.get(self.RECEIVER, {})
        point = self._peer_point(drone, self.RECEIVER)
        if (state.get("health", 0) <= 0 or type(state.get("step")) is not int
                or not 0 <= step-state["step"] <= self.STALE_STEPS
                or point is None or point.shape != (2,) or not np.isfinite(point).all()):
            return None
        return self.RECEIVER

    # -- NoCom departure ------------------------------------------------------
    def _roll_exit_goal(self, drone):
        # The goal always sits ahead of the current pose, so the chosen
        # direction is held continuously instead of being reset at a waypoint.
        p = np.asarray(drone.pose, dtype=float)
        self.exit_goal = p + self.EXIT_LOOKAHEAD * np.array(
            (math.cos(self.exit_dir), math.sin(self.exit_dir)))

    def _clear_exit(self):
        self.phase = APPROACH
        self.exit_dir = None
        self.exit_goal = None
        self.exit_attempts = 0
        self.exit_poses.clear()

    def _tick_exit_zone(self, drone, step, command):
        if self.phase != EXIT_ZONE:
            self.phase = EXIT_ZONE
            self.exit_attempts = 0
            self.exit_dir = float(drone.heading)
            self.exit_poses.clear()
            self.audit.append((step, "zone_exit_start", round(self.exit_dir, 4)))
        pose = np.asarray(drone.pose, dtype=float)
        self.exit_poses.append((step, pose.copy()))
        # Hold the current direction with a rolling goal; the local planner
        # keeps pushing toward it until the communicator comes back.
        self._roll_exit_goal(drone)
        # Own bombs do not block the body; filter their returns like elsewhere.
        command.update(drone.drive(tuple(self.exit_goal), drone.measured_velocity(),
                                   ignore_own_bombs=True))
        stalled = False
        if len(self.exit_poses) >= 2:
            f_step, f_pose = self.exit_poses[0]
            l_step, l_pose = self.exit_poses[-1]
            stalled = (l_step - f_step >= self.APPROACH_STALL_WINDOW and
                       np.linalg.norm(l_pose - f_pose) < self.APPROACH_STALL_MOVE)
        # Only a genuine stall (a wall the local planner cannot round) changes
        # the heading; merely travelling a long distance never resets it.
        if stalled:
            self.exit_attempts += 1
            if self.exit_attempts > self.EXIT_MAX_ATTEMPTS:
                self.audit.append((step, "zone_exit_giveup"))
                self._clear_exit()
                return
            self.exit_dir += self.EXIT_TURN_ANGLE
            self.exit_poses.clear()
            self.audit.append((step, "zone_exit_turn", round(self.exit_dir, 4)))

    # -- per-frame tick ------------------------------------------------------
    def tick(self, drone, step, command, steps_left):
        if int(drone.identifier) != self.MESSENGER_ID:
            return False
        needed = self._needed(drone, step)
        if self.state == ACTIVE:
            if not needed:
                self._finish(step, "receiver_satisfied")
                return False
            if (step >= self.delivery_until or
                    drone.walltime_limit-drone.elapsed_walltime <= self.MIN_WALL_SECONDS):
                self._finish(step, "delivery_budget_exhausted")
                return False
            # Coalesce new facts onto this trip without restarting its budget.
            self.task_payload.update(needed)
        else:
            if not self._can_activate(drone, step) or self._pick_target(drone, step) is None:
                return False
            self.state, self.phase, self.target = ACTIVE, APPROACH, self.RECEIVER
            self.task_payload = needed.copy()
            self.attempted_empty.update(needed)
            self.delivery_until = step + self._budget(drone, step)
            self.contact_step = self.wait_start = None
            self.approach_poses.clear()
            self.audit.append((step, "delivery_start", self.RECEIVER,
                               tuple(sorted(needed)), self.delivery_until))

        # NoCom: no peer can be contacted until the drone leaves the zone.
        if drone.communicator_is_disabled():
            self.attempted_empty.update(needed)
            self._tick_exit_zone(drone, step, command)
            return True
        if self.phase == EXIT_ZONE:
            self._clear_exit()
            self.audit.append((step, "zone_exit", tuple(map(float, drone.pose))))

        point = self._peer_point(drone, self.target)
        state = drone.states.get(self.RECEIVER, {})
        if (point is None or point.shape != (2,) or not np.isfinite(point).all()
                or state.get("health", 0) <= 0 or type(state.get("step")) is not int
                or not 0 <= step-state["step"] <= self.STALE_STEPS):
            self._finish(step, "receiver_position_stale")
            return False
        self.attempted_empty.update(needed)
        pose = np.asarray(drone.pose, dtype=float)
        gap = float(np.linalg.norm(point - pose))

        if self.phase == APPROACH:
            if 0 <= step-self.receiver_received_step <= self.DIRECT_TTL:
                self.phase = HOLD
                self.hold_left = self.EXCHANGE_HOLD
                self.contact_step = step
                self.contacts += 1
                self.audit.append((step, "contact", self.target, round(gap, 1)))
            else:
                command.update(drone.drive(tuple(point), drone.measured_velocity(),
                           ignore_own_bombs=True))
                # At a stale last-known point without contact: wait, then skip.
                if gap < self.ARRIVE_TOL:
                    if self.wait_start is None:
                        self.wait_start = step
                    elif step - self.wait_start >= self.WAIT_PEER_FRAMES:
                        self._finish(step, "peer_skipped")
                # Local minimum: still far from the goal but barely moving over
                # a sliding window. Give up this target instead of idling.
                if self.target is not None:
                    self.approach_poses.append((step, pose.copy()))
                    if len(self.approach_poses) >= 2:
                        f_step, f_pose = self.approach_poses[0]
                        l_step, l_pose = self.approach_poses[-1]
                        if (l_step - f_step >= self.APPROACH_STALL_WINDOW and
                                np.linalg.norm(l_pose - f_pose) < self.APPROACH_STALL_MOVE):
                            self._finish(step, "target_unreachable")
        else:  # HOLD
            self.hold_left = max(0, self.EXCHANGE_HOLD-(step-self.contact_step))
            # Stay close while the message channel exchanges evidence.
            command.update(drone.drive(tuple(point), drone.measured_velocity(),
                           ignore_own_bombs=True))
            if self.hold_left <= 0:
                self._finish(step, "delivery_unconfirmed")
        return True

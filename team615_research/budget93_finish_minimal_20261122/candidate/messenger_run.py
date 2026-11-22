"""Dedicated single-hop messenger.

One drone (the lowest-cost, earliest-empty aircraft) stops primary exploration
after it has dropped its own bombs and actively flies to each teammate in turn.
Closing to within the communication range lets the ordinary message channel
exchange live map/final-map evidence; the drone then relays what it has already
collected to the next peer. No ground-truth map, fixed coordinates, or private
peer state are read: targets come solely from teammates' broadcast states, and
the standard drive() lidar brake is used for navigation.
"""
import math
from collections import deque

import numpy as np

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
        pose = np.asarray(drone.pose, dtype=float)
        candidates = [p for p in self._alive_peers(drone) if p not in self.visited]
        if not candidates:
            return None
        def dist(p):
            pt = self._peer_point(drone, p)
            return float("inf") if pt is None else float(np.linalg.norm(pt - pose))
        return min(candidates, key=dist)

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
        if self.state == DONE:
            return False
        if self.state == IDLE:
            if self._can_activate(drone, step):
                self.state = ACTIVE
                self.audit.append((step, "messenger_enter",
                                   tuple(map(float, drone.pose))))
            return False

        # NoCom: no peer can be contacted until the drone leaves the zone.
        if drone.communicator_is_disabled():
            self._tick_exit_zone(drone, step, command)
            return True
        if self.phase == EXIT_ZONE:
            self._clear_exit()
            self.audit.append((step, "zone_exit", tuple(map(float, drone.pose))))

        if self.target is None:
            target = self._pick_target(drone, step)
            if target is None:
                # A full tour is complete. Run another round if budget allows.
                if (self.round == 0 and steps_left >= self.SECOND_ROUND_MIN_STEPS):
                    self.round += 1
                    self.visited.clear()
                    self.audit.append((step, "second_round"))
                    target = self._pick_target(drone, step)
                if target is None:
                    self.state = DONE
                    self.audit.append((step, "messenger_done", self.contacts))
                    return False
            self.target = target
            self.phase = APPROACH
            self.wait_start = None
            self.approach_poses.clear()
            self.audit.append((step, "target_picked", target))

        point = self._peer_point(drone, self.target)
        if point is None:
            self.visited.add(self.target)
            self.target = None
            return True
        pose = np.asarray(drone.pose, dtype=float)
        gap = float(np.linalg.norm(point - pose))

        if self.phase == APPROACH:
            if gap < self.COMM_RANGE:
                self.phase = HOLD
                self.hold_left = self.EXCHANGE_HOLD
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
                        self.audit.append((step, "peer_skipped", self.target))
                        self.visited.add(self.target)
                        self.target = None
                # Local minimum: still far from the goal but barely moving over
                # a sliding window. Give up this target instead of idling.
                if self.target is not None:
                    self.approach_poses.append((step, pose.copy()))
                    if len(self.approach_poses) >= 2:
                        f_step, f_pose = self.approach_poses[0]
                        l_step, l_pose = self.approach_poses[-1]
                        if (l_step - f_step >= self.APPROACH_STALL_WINDOW and
                                np.linalg.norm(l_pose - f_pose) < self.APPROACH_STALL_MOVE):
                            self.audit.append((step, "target_unreachable", self.target))
                            self.visited.add(self.target)
                            self.target = None
        else:  # HOLD
            self.hold_left -= 1
            # Stay close while the message channel exchanges evidence.
            command.update(drone.drive(tuple(point), drone.measured_velocity(),
                           ignore_own_bombs=True))
            if self.hold_left <= 0:
                self.visited.add(self.target)
                self.audit.append((step, "exchange_complete", self.target))
                self.target = None
        return True

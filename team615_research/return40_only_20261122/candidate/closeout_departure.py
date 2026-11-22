"""Deterministic closeout departure before a forced second drop.

The ordinary DropDeparture only starts on the first-drop frame and gives up
after a short window. This module is a fallback for the final wall-clock
window: when a bomb-carrying drone is stalled beside its own first bomb, it
locks a departure goal, opens a narrow (onboard-lidar only) tube far enough to
satisfy the SDK's 24px bomb-separation hard rule, then pulses place_bomb.
Everything here uses onboard sensors and the locally estimated first-bomb
position; no ground-truth map or fixed coordinates are read.
"""
import math
from collections import deque

import numpy as np

IDLE, DEPARTING, FORCING, DONE = "IDLE", "DEPARTING", "FORCING", "DONE"


class CloseoutDeparture:
    DEPART_TARGET_SEP = 28.0      # > SDK MIN_BOMB_SEPARATION (24), with margin
    SAFE_SEP = 26.0               # minimum achieved separation accepted
    ENTER_WALL = 25.0
    STALL_WINDOW = 30
    STALL_MOVE = 8.0
    DIR_STEP = math.pi / 12       # 15 degrees
    DIR_SPREAD = math.pi / 2      # search +-90 degrees around the base direction
    TUBE_HALF = 12.0              # narrowed tube (vs 23 elsewhere)
    WATCHDOG_FRAMES = 40
    WATCHDOG_MOVE = 3.0
    MAX_REPICK = 3
    PULSE_GAP = 2
    NEED_CLEAR = 30.0
    MIN_CLEAR = 26.0
    BOMB_RADIUS = 12.0            # SDK Bomb radius
    BOMB_FILTER_MARGIN = 3.0      # lidar noise std 2.5
    DEPART_SPEED = 3.0            # desired world-frame departure speed
    ALIGN_TOLERANCE = 1.0         # start translating within this heading error

    def __init__(self):
        self.state = IDLE
        self.audit = []
        self.lidar_snapshot = None
        self.lidar_log = []
        self._poses = deque(maxlen=self.STALL_WINDOW)
        self._goal = None
        self._depart_dir = None
        self._bomb1 = None
        self._repick = 0
        self._watchdog_start = None
        self._watchdog_pose = None
        self._force_inv = None
        self._last_pulse = -100

    # -- pose history / stall ------------------------------------------------
    def _track_pose(self, drone, step):
        self._poses.append((step, np.asarray(drone.pose, dtype=float).copy()))

    def _stalled(self):
        if len(self._poses) < self.STALL_WINDOW:
            return False
        first_step, first_pose = self._poses[0]
        last_step, last_pose = self._poses[-1]
        if last_step - first_step < self.STALL_WINDOW - 1:
            return False
        return float(np.linalg.norm(last_pose - first_pose)) < self.STALL_MOVE

    def _first_bomb(self, drone):
        key = (int(drone.identifier), 1)
        point = drone.drop_records.get(key)
        if point is None:
            return None
        return np.asarray(point, dtype=float)

    # -- direction selection -------------------------------------------------
    def _lidar_points(self, drone):
        """World-coord lidar hit points, excluding the drone's own first bomb.

        When the drone overlaps the bomb, every ray hits the bomb hull and the
        raw lidar sees nothing beyond it. The bomb is a known object being left
        and has no drone collision, so its returns are dropped here to recover
        the real (open) surroundings.
        """
        angles = np.asarray(drone.lidar_rays_angles(), dtype=float)
        ranges = np.asarray(drone.lidar_values(), dtype=float)
        finite = np.isfinite(ranges) & (ranges > 0)
        if not np.any(finite):
            return np.empty((0, 2))
        px, py = np.asarray(drone.pose, dtype=float)
        head = float(drone.heading)
        idx = np.where(finite)[0]
        world_dir = head + angles[idx]
        pts = np.column_stack((px + ranges[idx] * np.cos(world_dir),
                               py + ranges[idx] * np.sin(world_dir)))
        if self._bomb1 is not None:
            dist_bomb = np.linalg.norm(pts - self._bomb1, axis=1)
            pts = pts[dist_bomb > self.BOMB_RADIUS + self.BOMB_FILTER_MARGIN]
        return pts

    def _clear_at(self, drone, world_dir):
        pts = self._lidar_points(drone)
        if len(pts) == 0:
            return float("inf")
        px, py = np.asarray(drone.pose, dtype=float)
        rel = world_dir - float(drone.heading)
        dvec = np.array((math.cos(rel), math.sin(rel)))
        svec = np.array((-math.sin(rel), math.cos(rel)))
        delta = pts - np.array((px, py))
        fore = delta @ dvec
        side = np.abs(delta @ svec)
        in_tube = (fore > 0) & (side < self.TUBE_HALF)
        if not np.any(in_tube):
            return float("inf")
        return float(np.min(fore[in_tube]))

    def _pick_direction(self, drone, bomb1):
        base = math.atan2(drone.pose[1] - bomb1[1], drone.pose[0] - bomb1[0])
        candidates = [base + k * self.DIR_STEP for k in range(-6, 7)]

        def angular_gap(d):
            return abs((d - base + math.pi) % (2 * math.pi) - math.pi)

        # Prefer a 30px-clear direction closest to the base heading.
        scored = [(self._clear_at(drone, d), d) for d in candidates]
        for clear, d in sorted(scored, key=lambda x: angular_gap(x[1])):
            if clear >= self.NEED_CLEAR:
                return d, clear
        relaxed = [x for x in scored if x[0] >= self.MIN_CLEAR]
        if relaxed:
            clear, d = min(relaxed, key=lambda x: angular_gap(x[1]))
            return d, clear
        # Last resort: direction with the largest clearance.
        clear, d = max(scored, key=lambda x: x[0])
        return d, clear

    def _lock_goal(self, drone, step):
        direction, clear = self._pick_direction(drone, self._bomb1)
        self._depart_dir = direction
        self._goal = (self._bomb1
                      + np.array((math.cos(direction), math.sin(direction)))
                      * self.DEPART_TARGET_SEP)
        self._watchdog_start = step
        self._watchdog_pose = np.asarray(drone.pose, dtype=float).copy()
        self.audit.append((step, "direction_picked", round(direction, 4),
                           round(clear, 2), self._repick))
        return direction

    # -- entry ---------------------------------------------------------------
    def _should_enter(self, drone, wall_left):
        if wall_left > self.ENTER_WALL:
            return False
        if int(drone.previous_inventory or 0) <= 0:
            return False
        self._bomb1 = self._first_bomb(drone)
        if self._bomb1 is None:
            return False
        return self._stalled()

    def _enter_departing(self, drone, step):
        self.audit.append((step, "stall_enter", tuple(map(float, drone.pose))))
        if self.lidar_snapshot is None:
            rng = np.asarray(drone.lidar_values(), dtype=float)
            ang = np.asarray(drone.lidar_rays_angles(), dtype=float)
            self.lidar_snapshot = dict(
                step=step,
                pose=tuple(map(float, drone.pose)),
                heading=float(drone.heading),
                ranges=[None if not np.isfinite(v) else float(v) for v in rng],
                angles=[float(v) for v in ang])
        self._lock_goal(drone, step)
        self.state = DEPARTING

    # -- per-state ticks -----------------------------------------------------
    def _current_sep(self, drone):
        return float(np.linalg.norm(np.asarray(drone.pose, dtype=float) - self._bomb1))

    def _departure_command(self, drone):
        """Deterministic translation that bypasses the lidar obstacle brake.

        The ordinary drive() returns zero speed because every ray is blocked by
        the overlapping own bomb. Here the drone aligns to the locked departure
        direction and pushes forward at a fixed speed regardless of those
        (filtered) near-field returns.
        """
        turn = (self._depart_dir - float(drone.heading) + math.pi) % (2 * math.pi) - math.pi
        cmd = {"rotation": float(np.clip(turn, -0.6, 0.6)), "grasper": 0,
               "forward": 0.0, "lateral": 0.0}
        if abs(turn) <= self.ALIGN_TOLERANCE:
            vel = drone.measured_velocity()
            v_world = np.zeros(2) if vel is None else np.asarray(vel, dtype=float)
            desired = self.DEPART_SPEED * np.array(
                (math.cos(self._depart_dir), math.sin(self._depart_dir)))
            force = (desired - v_world) / 5.5
            c, s = math.cos(drone.heading), math.sin(drone.heading)
            cmd["forward"] = float(np.clip(force[0] * c + force[1] * s, -1, 1))
            cmd["lateral"] = float(np.clip(-force[0] * s + force[1] * c, -1, 1))
        return cmd

    def _tick_departing(self, drone, step, command):
        if self._current_sep(drone) >= self.SAFE_SEP:
            self.audit.append((step, "separation_open", round(self._current_sep(drone), 2)))
            self.state = FORCING
            self._force_inv = int(drone.previous_inventory)
            self._last_pulse = -100
            return
        # Watchdog: repick when no progress is made.
        if (step - self._watchdog_start >= self.WATCHDOG_FRAMES
                and np.linalg.norm(np.asarray(drone.pose) - self._watchdog_pose) < self.WATCHDOG_MOVE):
            if self._repick >= self.MAX_REPICK:
                self.audit.append((step, "give_up", self._repick))
                self.state = IDLE
                return
            self._repick += 1
            self._lock_goal(drone, step)
        command.update(self._departure_command(drone))

    def _tick_forcing(self, drone, step, command):
        inv = int(drone.previous_inventory)
        if inv < self._force_inv:
            self.audit.append((step, "drop_confirmed", inv))
            self.state = DONE
            return
        if drone.pending_drop is not None:
            # Pulse awaiting SDK confirmation; do not resend.
            return
        # Previous pulse was cleared as a silent rejection.
        if self._current_sep(drone) < self.SAFE_SEP:
            self.audit.append((step, "pulse_rejected_redepart", round(self._current_sep(drone), 2)))
            if self._repick >= self.MAX_REPICK:
                self.audit.append((step, "give_up", self._repick))
                self.state = IDLE
                return
            self._repick += 1
            self._watchdog_start = step
            self._watchdog_pose = np.asarray(drone.pose, dtype=float).copy()
            self.state = DEPARTING
            return
        if step - self._last_pulse >= self.PULSE_GAP:
            command.update(grasper=0, place_bomb=1)
            drone.pending_drop = (inv, np.asarray(drone.pose, dtype=float).copy(), step)
            self._last_pulse = step
            self.audit.append((step, "pulse_sent", tuple(map(float, drone.pose))))

    # -- public entry --------------------------------------------------------
    def tick(self, drone, step, command, wall_left, steps_left):
        self._track_pose(drone, step)
        self._log_lidar(drone, step)
        if self.state == DONE:
            return
        if self.state == IDLE:
            if self._should_enter(drone, wall_left):
                self._enter_departing(drone, step)
            return
        if self.state == DEPARTING:
            self._tick_departing(drone, step, command)
        elif self.state == FORCING:
            self._tick_forcing(drone, step, command)

    def _log_lidar(self, drone, step):
        # Whole-run lightweight log once the first bomb exists, to see when the
        # lidar is blinded by overlap with the drone's own bomb.
        if self._bomb1 is None:
            self._bomb1 = self._first_bomb(drone)
        if self._bomb1 is None:
            return
        rng = np.asarray(drone.lidar_values(), dtype=float)
        finite = np.isfinite(rng)
        n_pos = int(np.count_nonzero(finite & (rng > 0)))
        n_neg = int(np.count_nonzero(finite & (rng < 0)))
        dist = float(np.linalg.norm(np.asarray(drone.pose) - self._bomb1))
        self.lidar_log.append((step, round(dist, 2), n_pos, n_neg,
                               int(len(rng) - n_pos - n_neg)))

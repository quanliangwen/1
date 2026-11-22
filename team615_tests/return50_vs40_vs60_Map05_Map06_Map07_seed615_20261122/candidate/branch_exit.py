"""One guarded deployment after an aircraft leaves its own terminal search branch."""
import math
from collections import Counter

import numpy as np
from scipy.ndimage import label

from swarm_rescue.solutions.passage_ledger import PassageLedger


def in_pocket(grid, point, cells):
    return point is not None and grid.cell(point) in cells


class BranchExit:
    CLEARANCE = 23.
    EXPIRY = 400
    ACK_AGE = 100
    MAX_CELLS = 120

    def __init__(self):
        self.claim = None
        self.review = Counter()
        self.ack = {}
        self.incoming = {}
        self.finished = False
        self.last_position = None
        self.outbound = False
        self.exit_crossed = False
        self.exits = 0

    @classmethod
    def pocket(cls, grid, anchor, axis, witness):
        """Open a virtual cut between observed banks. Treat unknown as traversable."""
        rr, cc = grid.cell(anchor)
        h, w = grid.evidence.shape
        lo, left = max(0, rr - 14), max(0, cc - 14)
        hi, right = min(h, rr + 15), min(w, cc + 15)
        view = np.s_[lo:hi, left:right]
        delta = grid.centres[view] - anchor
        depth = delta @ axis
        across = delta[..., 0] * axis[1] - delta[..., 1] * axis[0]
        evidence = grid.evidence[view]
        bank = (np.abs(depth) <= grid.CELL) & (evidence >= 6)
        banks = [np.abs(across[bank & ((across * sign) >= 23.)
                                    & ((across * sign) <= 90.)]) for sign in (-1, 1)]
        if not all(side.size for side in banks):
            return frozenset()
        navigable = (evidence < 3) & (grid.clearance[view] >= cls.CLEARANCE)
        cut = ((np.abs(depth) <= grid.CELL) & (across >= -min(banks[0]))
               & (across <= min(banks[1])) & navigable)
        if not cut.any():
            return frozenset()
        r, c = grid.cell(witness)
        if not (lo <= r < hi and left <= c < right):
            return frozenset()
        zones, _ = label(navigable & ~cut, structure=np.ones((3, 3), dtype=bool))
        inner = zones[r-lo, c-left]
        if not inner:
            return frozenset()
        inside = zones == inner
        if (inside[0].any() or inside[-1].any() or inside[:, 0].any() or inside[:, -1].any()
                or np.any(inside & ((depth <= 0.) | (evidence >= 0)))):
            return frozenset()
        count = np.count_nonzero(inside)
        if not 8 <= count <= cls.MAX_CELLS or np.max(depth[inside]) < 65.:
            return frozenset()
        # The pocket must reconnect through this cut in the unmodified grid.
        restored, _ = label(navigable, structure=np.ones((3, 3), dtype=bool))
        if not np.any((restored == restored[r-lo, c-left]) & (depth <= -45.)):
            return frozenset()
        return frozenset((int(r)+lo, int(c)+left) for r, c in np.argwhere(inside))

    @staticmethod
    def crosses(grid, cells, anchor, points):
        if any(grid.cell(point) in cells for point in points):
            return True
        for start, end in zip(points, points[1:]):
            a, b = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
            if PassageLedger._segment_distance(anchor, a, b) > 300.:
                continue
            pieces = max(1, math.ceil(math.dist(a, b) / 10.))
            if any(grid.cell(a + (b-a)*k/pieces) in cells for k in range(1, pieces)):
                return True
        return False

    def conflicting_passage(self, drone, ledger, anchor, axis):
        return any(owner != drone.identifier and
                   any(math.dist(row[1:3], anchor) <= 72.
                       and abs(float(np.dot(row[3:5], axis))) >= .45
                       for row in entries)
                   for owner, entries in ledger.reports.items())

    def observe(self, drone, ledger, step, audit):
        if self.finished or step % 8 != int(drone.identifier) % 8:
            return
        pose = tuple(map(float, drone.pose))
        previous, self.last_position = self.last_position, pose
        if self.claim is not None:
            started, anchor, axis, _, _ = self.claim
            if (step - started > self.EXPIRY or math.dist(pose, anchor) > 290.
                    or self.conflicting_passage(drone, ledger, anchor, axis)):
                audit.append((step, "branch_expired", started, len(self.ack)))
                self.claim, self.outbound = None, False
                self.ack.clear()
                return
            if previous is None or not drone.grid.pose_fixed or drone._odometry_only:
                self.exit_crossed, self.outbound, self.exits = False, False, 0
                return
            relative = np.subtract(pose, anchor)
            before = np.subtract(previous, anchor)
            motion = relative - before
            along = float(np.dot(relative, axis))
            lateral = abs(relative[0]*axis[1] - relative[1]*axis[0])
            displacement = float(np.linalg.norm(motion))
            if displacement > 40. or lateral > 66. or np.dot(motion, axis) > 2.:
                self.exit_crossed, self.outbound, self.exits = False, False, 0
            elif 3. <= displacement and np.dot(motion, axis) < -2.:
                if along <= 0. < np.dot(before, axis):
                    self.exit_crossed = True
                if self.exit_crossed:
                    self.exits = min(2, self.exits+1)
                    self.outbound = self.exits >= 2
            return
        if (step % 24 != int(drone.identifier) % 8 or not drone.grid.pose_fixed
                or drone._odometry_only or drone.search_task is None):
            return
        self.review['observation_ticks'] += 1
        for record in reversed(ledger.local):
            tick, *geometry = record
            if not 0 <= step - tick <= 320:
                continue
            anchor, axis = tuple(geometry[:2]), tuple(geometry[2:4])
            if (math.dist(pose, anchor) > 200. or np.dot(np.subtract(pose, anchor), axis) < 50.
                    or self.conflicting_passage(drone, ledger, anchor, axis)):
                continue
            self.review['passages_examined'] += 1
            cells = self.pocket(drone.grid, anchor, axis, pose)
            if not cells:
                self.review['no_observed_terminal_pocket'] += 1
                continue
            if drone.grid.cell(drone.search_task.point) not in cells:
                self.review['no_own_search_task_in_pocket'] += 1
                continue
            grid = drone.grid
            swept = grid.close_scan_cells()
            if any(grid.searched_here[cell] <= swept[cell] for cell in cells):
                self.review['own_scan_incomplete'] += 1
                continue
            self.claim = step, anchor, axis, pose, tuple(sorted(cells))
            self.exit_crossed, self.outbound, self.exits = False, False, 0
            self.ack.clear()
            audit.append((step, "branch_claim", anchor, axis, pose, len(cells)))
            return

    def receive(self, drone, message):
        owner = message["id"]
        if type(owner) is not int or owner == drone.identifier or not 0 <= owner < drone.team_size:
            return
        now = int(drone.elapsed_timestep)
        claim = message.get("red_branch_claim")
        if isinstance(claim, tuple) and len(claim) == 5:
            stamp, anchor, axis, witness, cells = claim
            h, w = drone.grid.evidence.shape
            if (type(stamp) is int and 0 <= now-stamp <= self.EXPIRY
                    and drone._inside_team_point(anchor) and drone._inside_team_point(witness)
                    and len(axis) == 2 and .95 <= math.hypot(*axis) <= 1.05
                    and isinstance(cells, tuple) and 8 <= len(cells) <= self.MAX_CELLS
                    and all(isinstance(c, tuple) and len(c) == 2 and type(c[0]) is int
                            and type(c[1]) is int and 0 <= c[0] < h and 0 <= c[1] < w for c in cells)):
                self.incoming[owner] = stamp, anchor, frozenset(cells)
        own = self.claim
        acks = message.get("red_branch_acks", ())
        if own is not None and (int(drone.identifier), own[0]) in acks:
            if owner not in self.ack:
                self.review['ack_receipts'] += 1
            self.ack[owner] = now
        else:
            self.ack.pop(owner, None)

    def acknowledgments(self, drone, step):
        self.incoming = {owner: item for owner, item in self.incoming.items()
                         if step - item[0] <= self.EXPIRY}
        if not self.incoming or drone.pose is None or not drone.grid.pose_fixed or drone._odometry_only:
            return ()
        points = [drone.pose, *drone.route]
        if drone.goal is not None:
            points.append(drone.goal)
        task = drone.search_task
        return tuple((owner, started) for owner, (started, anchor, cells) in self.incoming.items()
                     if (self.claim is None or math.dist(anchor, self.claim[1]) > 90.)
                     and (task is None or cells.isdisjoint(task.cells))
                     and not self.crosses(drone.grid, cells, anchor, points))

    def allows(self, drone, ledger, step, protected, references, opening_limit, semantic):
        if (self.finished or self.claim is None or not self.outbound or not drone.route
                or protected in ("neck", "live_neck") or not drone.grid.pose_fixed
                or drone._odometry_only or step-drone.grid.last_pose_fix > 45
                or step >= drone.limit-20 or drone.walltime_limit-drone.elapsed_walltime < 3.):
            return False
        started, anchor, axis, witness, raw_cells = self.claim
        if (step-started > self.EXPIRY or any(row[0] <= opening_limit for row in references)
                or (protected == "passage" and not references)
                or any(math.dist(row[1:3], anchor) > 72. for row in references)
                or self.conflicting_passage(drone, ledger, anchor, axis)):
            return False
        cells = frozenset(raw_cells)
        # Also exclude a newly received overlapping branch claim or assignment.
        if any(not cells.isdisjoint(other[2]) for other in self.incoming.values()):
            return False
        if any(owner != drone.identifier and step-state["step"] <= self.ACK_AGE
               and (in_pocket(drone.grid, state.get("point"), cells)
                    or in_pocket(drone.grid, state.get("goal"), cells)
                    or not cells.isdisjoint(state.get("opening_cells", ())))
               for owner, state in drone.states.items()):
            return False
        if any(owner != drone.identifier and step - self.ack.get(owner, -1000) > self.ACK_AGE
               for owner in range(drone.team_size)):
            self.review['acks_missing_at_exit'] += 1
            return False
        depth = float(np.dot(np.subtract(drone.pose, anchor), axis))
        if not -105. <= depth <= -56. or not math.dist(drone.pose, anchor) <= 112.:
            return False
        if any(getattr(hit.entity_type, "name", "") == "DRONE" and hit.distance < 90.
               for hit in semantic):
            return False
        grid = drone.grid
        here = grid.cell(drone.pose)
        if grid.evidence[here] >= 0 or grid.clearance[here] < self.CLEARANCE:
            return False
        if self.pocket(grid, anchor, axis, witness) != cells:
            return False
        # Check a short prefix of the current route and leave the original route intact.
        # Every sample must be seen free and outside the pocket and narrow mouth.
        start, travelled = np.asarray(drone.pose), 0.
        for end in drone.route:
            end = np.asarray(end)
            leg = float(np.linalg.norm(end-start))
            if leg > 0.:
                length = min(leg, 64.-travelled)
                pieces = max(1, math.ceil(length / 8.))
                for k in range(1, pieces+1):
                    point = start + (end-start) * (length*k/(leg*pieces))
                    cell = grid.cell(point)
                    if (cell in cells or grid.evidence[cell] >= 0 or grid.clearance[cell] < self.CLEARANCE
                            or np.dot(np.subtract(point, anchor), axis) > -48.):
                        return False
                travelled += length
                if travelled >= 64.:
                    return True
            start = end
        return False

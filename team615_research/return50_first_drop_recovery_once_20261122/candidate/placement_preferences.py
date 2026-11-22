"""Placement preferences based on own public sensors and received bend reports."""
import math
from collections import deque

import numpy as np

from swarm_rescue.solutions.branch_exit import BranchExit
from swarm_rescue.solutions.local_exit_amnesty import LocalExit
from swarm_rescue.solutions.deep_placement import DeepPlacement, RejectedPatch
from swarm_rescue.solutions.opening_pair import OpeningPair
from swarm_rescue.solutions.placement_maneuvers import PlacementManeuvers
from swarm_rescue.solutions.scan_geometry import scan_lines
from swarm_rescue.solutions.placement_density import observed_bombs, violates_patch

from swarm_rescue.simulation.drone.bomb_deployer import MIN_BOMB_SEPARATION as SDK_SPACING

BOMB_SURFACE_RADIUS = 12.


def same_bend(a, b):
    return (math.dist(a[1:3], b[1:3]) <= 85.
            and sum(x*y for x,y in zip(a[3:5], b[3:5])) > .60
            and sum(x*y for x,y in zip(a[5:7], b[5:7])) > .60)


def first_shared_bend(reports, team_size):
    if len(reports) != team_size:
        return None
    for reference in sorted((bend for records in reports.values() for bend in records)):
        members = {}
        for owner, records in reports.items():
            match = next((bend for bend in records if same_bend(reference, bend)), None)
            if match is not None:
                members[owner] = match
        if len(members) == team_size:
            return max((bend[0], owner) for owner, bend in members.items()), reference
    return None


class PlacementPreferences:
    def __init__(self):
        self.turn_trace = deque(maxlen=73)
        self.corner = None
        self.corner_first_confirmed = False
        self.opening_position = None
        self.local_turns = []
        self.turn_reports = {}
        self.last_turn_step = -100
        self.request = None
        self.last_drop_point = None
        self.next_request = 0
        self.unlocalized_drops = set()
        self.audit = []
        self.blocks = {}
        self.deep = DeepPlacement()
        self.branch_exit = BranchExit()
        self.local_exit = LocalExit()
        self.opening_pair = OpeningPair()
        self.maneuvers = PlacementManeuvers()
        self.last_visible_turn = None
        self.rejected_patch = RejectedPatch()
        # LocalEscape reads this field before deciding whether to take control.
        self.wall_approach = None

    def receive(self, drone, message):
        owner = message["id"]
        if type(owner) is not int or owner == drone.identifier or not 0 <= owner < drone.team_size:
            return
        turns = message.get("red_turns")
        if not isinstance(turns, tuple) or not 0 < len(turns) <= 8:
            return
        previous = self.turn_reports.get(owner, ())
        if len(turns) <= len(previous) or turns[:len(previous)] != previous:
            return
        if all(isinstance(bend,tuple) and len(bend)==7 and type(bend[0]) is int
               and 0 < bend[0] < drone.elapsed_timestep and drone._inside_team_point(bend[1:3])
               and all(type(x) in (int,float) and math.isfinite(x) and abs(x)<=1 for x in bend[3:])
               for bend in turns):
            self.turn_reports[owner] = turns

    def lidar_lines(self, drone, ranges, angles, semantic):
        movable = [hit.distance*np.array((math.cos(hit.angle),math.sin(hit.angle)))
                   for hit in semantic if getattr(hit.entity_type,"name","") in
                   ("BOMB","DRONE","DISPOSAL_CENTER")]
        return scan_lines(ranges, angles, movable, 115.)

    def watch_bend(self, drone, step, ranges, angles, semantic):
        if (step - drone.grid.last_pose_fix > 180
                or self.turn_trace and math.dist(self.turn_trace[-1], drone.pose)>14.):
            self.turn_trace.clear()
            return
        self.turn_trace.append(tuple(drone.pose))
        if (len(self.turn_trace)<31 or len(self.local_turns)>=8 or step-self.last_turn_step<35
                or not drone.search_roaming.departed or step % 4 != drone.identifier % 4):
            return
        trace = np.asarray(self.turn_trace)
        end = trace[-1]
        turn = None
        for half in (15, 24, 36):
            if len(trace) <= 2 * half:
                break
            entry, middle = trace[-1-2*half], trace[-1-half]
            incoming, outgoing = middle - entry, end - middle
            before, after = np.linalg.norm(incoming), np.linalg.norm(outgoing)
            if min(before, after) < 20.:
                continue
            incoming, outgoing = incoming / before, outgoing / after
            if abs(float(incoming @ outgoing)) <= .42:
                mid_entry = trace[-1-2*half+half//2]
                mid_exit = trace[-1-half+half//2]
                if min(np.linalg.norm(mid_entry-entry), np.linalg.norm(mid_exit-middle)) >= 7.:
                    turn = middle, incoming, outgoing
                    break
        if turn is None:
            return
        middle, incoming, outgoing = turn
        lines = self.lidar_lines(drone,ranges,angles,semantic)
        corner_points = []
        for j,line in enumerate(lines):
            u=line[1]-line[0]
            u/=np.linalg.norm(u)
            for other in lines[j+1:]:
                v=other[1]-other[0]
                v/=np.linalg.norm(v)
                if abs(float(u @ v))>.30:
                    continue
                endpoints=[(a,b) for a in line for b in other if np.linalg.norm(a-b)<=28]
                corner_points.extend((a+b)/2 for a,b in endpoints)
        if not corner_points:
            return
        c,s=math.cos(drone.heading),math.sin(drone.heading)
        rotations=np.array(((c,s),(-s,c)))
        positions=[p @ rotations+end for p in corner_points if np.linalg.norm(p)<=100]
        if not positions:
            return
        point=min(positions,key=lambda q:np.linalg.norm(q-middle))
        if not drone._inside_team_point(point) or np.linalg.norm(point-middle)>85:
            return
        bend=(step, *map(float,point), *map(float,incoming), *map(float,outgoing))
        if not any(same_bend(bend,old) for old in self.local_turns):
            self.local_turns.append(bend)
            self.turn_reports[drone.identifier]=tuple(self.local_turns)
            self.last_turn_step=step
            self.audit.append((step,"bend_observed",bend))

    def finish_request(self, drone, step):
        if self.request is None:
            return
        request_step, reason, fixed, count = self.request
        if step<=request_step:
            return
        left=drone.carried_bombs_count()
        accepted=left<count
        if reason == 'narrow_short_drop':
            self.maneuvers.confirmed(step, accepted)
        if reason in ('local_slot_exit','side_alcove'):
            self.local_exit.finish(drone,accepted,left)
        self.audit.append((step,"confirmed" if accepted else "rejected",reason,fixed,request_step,left))
        if accepted:
            ordinal=drone.initial_inventory-left
            self.last_drop_point=drone.drop_records[(drone.identifier,ordinal)].copy()
            if not fixed:
                self.unlocalized_drops.add((drone.identifier,ordinal))
            if reason == "branch_exit":
                self.branch_exit.finished = True
                self.branch_exit.claim = None
            if reason == "corner_first":
                self.corner_first_confirmed = True
        else:
            self.next_request=step+6
        self.request=None

    def place(self, drone, command, step, reason, count):
        command.update(forward=0.,lateral=0.,rotation=0.,grasper=0,place_bomb=1)
        self.request=(step,reason,bool(drone.grid.pose_fixed),count)
        drone.pending_drop=(count,drone.pose.copy(),step)
        drone.last_attempt_step=step
        self.audit.append((step,"request",reason,bool(drone.grid.pose_fixed),count))

    def complete_last(self, drone, command, step, ranges, semantic):
        self.finish_request(drone, step)
        return drone.second_drop.complete_last(drone, step, command, ranges, semantic)

    @staticmethod
    def _first_drop_exit_clear(drone, ranges, semantic):
        # Verify the first short section of the existing route using the
        # current public scan. Do not steer, filter an obstacle, or relax the
        # safety rule to make an uncertain start look clear.
        if ranges is None or not drone.route:
            return False
        delta = np.asarray(drone.route[0], dtype=float) - drone.pose
        length = float(np.linalg.norm(delta))
        if not np.isfinite(length) or length < 12.:
            return False
        direction = math.atan2(delta[1], delta[0]) - drone.heading
        obstacles = [(hit.distance * math.cos(hit.angle), hit.distance * math.sin(hit.angle))
                     for hit in semantic if getattr(hit.entity_type, "name", "") in
                     ("DRONE", "BOMB", "DISPOSAL_CENTER")]
        return drone.local_escape.clearance(direction, np.asarray(drone.lidar_rays_angles()),
                                            np.asarray(ranges), min(36., length), obstacles)

    @staticmethod
    def _ordinary_start_step(limit):
        # Round up to 75% of the pinned SDK's 30% full-score time line.
        return (9 * limit + 39) // 40

    COVERAGE_MIN = 1.00
    COVERAGE_FLOOR = .80

    @classmethod
    def _coverage_minimum(cls, step, limit):
        # Map scoring reaches the full-time line at 30% of the step cap.
        full_score_step = .30 * limit
        ramp_start = .95 * full_score_step
        if step <= ramp_start:
            return cls.COVERAGE_MIN
        if step >= full_score_step:
            return cls.COVERAGE_FLOOR
        fraction = (step - ramp_start) / (full_score_step - ramp_start)
        return cls.COVERAGE_MIN - (cls.COVERAGE_MIN - cls.COVERAGE_FLOOR) * fraction
    LOOKAHEAD_DISTANCE = (32., 64.)

    def _visible_corner(self, drone, ranges, angles, semantic):
        if ranges is None:
            return None
        lines = self.lidar_lines(drone, ranges, angles, semantic)
        best = None
        for i, pair in enumerate(lines):
            axis = pair[1] - pair[0]
            axis /= np.linalg.norm(axis)
            for other in lines[i+1:]:
                direction = other[1] - other[0]
                direction /= np.linalg.norm(direction)
                if abs(float(axis @ direction)) > .30:
                    continue
                for a in pair:
                    for b in other:
                        if np.linalg.norm(a-b) <= 30.:
                            point = (a+b)/2
                            distance = float(np.linalg.norm(point))
                            if best is None or distance < best[0]:
                                best = distance, point
        if best is None:
            return None
        c, s = math.cos(drone.heading), math.sin(drone.heading)
        return best[1] @ np.array(((c, s), (-s, c))) + drone.pose

    @staticmethod
    def _corner_weight(point, corner):
        return 1.20 if corner is not None and math.dist(point, corner) <= 80. else 1.

    def _forward_gain(self, drone, estimate, corner=None):
        """Sample only the route that the search controller has already chosen."""
        previous = np.asarray(drone.pose, dtype=float)
        travelled = 0.
        best = 0.
        index = 0
        for waypoint in drone.route[:4]:
            end = np.asarray(waypoint, dtype=float)
            length = float(np.linalg.norm(end - previous))
            if length > 1e-6:
                while (index < len(self.LOOKAHEAD_DISTANCE)
                       and self.LOOKAHEAD_DISTANCE[index] <= travelled + length):
                    fraction = (self.LOOKAHEAD_DISTANCE[index] - travelled) / length
                    point = previous + fraction * (end - previous)
                    gain, _, _ = estimate(point)
                    best = max(best, gain * self._corner_weight(point, corner))
                    index += 1
            if index == len(self.LOOKAHEAD_DISTANCE):
                break
            travelled += length
            previous = end
        return best

    def _patch_open(self, drone, semantic, step):
        margin = 45. if drone.grid.pose_fixed else 55.
        if violates_patch(drone.pose, observed_bombs(drone, semantic), margin):
            self.reject("patch_full")
            if self.blocks["patch_full"] <= 24:
                self.audit.append((step, "patch_full", tuple(map(float, drone.pose))))
            return False
        return True

    def _note_local_rejection(self, point, step):
        if self.rejected_patch.reject(point, step):
            self.reject("skip_patch_started")
            if self.blocks["skip_patch_started"] <= 24:
                self.audit.append((step, "skip_patch", tuple(map(float, point))))

    def reject(self, reason):
        self.blocks[reason] = self.blocks.get(reason, 0) + 1

    def _corner_request(self, drone, count, step):
        if self.corner is None:
            return None
        (passed, owner), bend = self.corner
        if owner != drone.identifier or step - passed > 110 or math.dist(drone.pose, bend[1:3]) > 115.:
            return None
        if count == drone.initial_inventory:
            return "corner_first"
        if count == drone.initial_inventory - 1 and self.corner_first_confirmed:
            return "corner_second"
        return None

    def _spaced_from_bombs(self, drone, semantic, corner_second):
        if self.last_drop_point is not None and math.dist(drone.pose, self.last_drop_point) < SDK_SPACING:
            return False
        for hit in semantic:
            if getattr(hit.entity_type, "name", "") != "BOMB" or not 0. <= hit.distance < SDK_SPACING:
                continue
            if corner_second and self.last_drop_point is not None:
                yaw = drone.heading + hit.angle
                distance = hit.distance + BOMB_SURFACE_RADIUS
                centre = drone.pose + distance * np.array((math.cos(yaw), math.sin(yaw)))
                # Only exempt the surface echo of the very bomb this aircraft put down.
                # The SDK independently checks the exact centre-to-centre spacing.
                if distance >= SDK_SPACING and math.dist(centre, self.last_drop_point) <= BOMB_SURFACE_RADIUS:
                    continue
            return False
        return True

    def _protected_turn(self, drone, step, ranges, angles, semantic):
        if self.deep.near_neck(drone.pose, step):
            return "neck"
        if self.deep.here(drone.pose, 68.):
            return "neck_exit"
        if any(math.dist(drone.pose, bend[1:3]) <= 80.
               for reports in self.turn_reports.values() for bend in reports):
            return "shared_bend"
        if ranges is None:
            return None
        wall_corner = self._visible_corner(drone, ranges, angles, semantic)
        if wall_corner is not None and math.dist(drone.pose, wall_corner) <= 72.:
            self.last_visible_turn = step, tuple(map(float, wall_corner))
            return "wall_corner"
        remembered = self.last_visible_turn
        if remembered is not None and step - remembered[0] <= 140 and math.dist(drone.pose, remembered[1]) <= 72.:
            return "recent_bend"
        direction = 0.
        if drone.route:
            dx, dy = np.asarray(drone.route[0], dtype=float) - drone.pose
            direction = math.atan2(dy, dx) - drone.heading
        movable = drone.memory.semantic_mask(ranges, angles, semantic)
        if self.deep.narrow(ranges, angles, direction, movable):
            return "live_neck"
        return None

    def _last_at_turn(self, drone, ranges, semantic):
        local = {
            owner: tuple(bend for bend in reports if math.dist(drone.pose, bend[1:3]) <= 85.)
            for owner, reports in self.turn_reports.items()
        }
        vote = first_shared_bend(local, drone.team_size)
        return (vote is not None and vote[0][1] == drone.identifier
                and self._first_drop_exit_clear(drone, ranges, semantic))

    def update(self, drone, command, step, ranges, semantic):
        self.finish_request(drone, step)
        count = drone.carried_bombs_count()
        final = step * 10 >= 9 * drone.limit or drone.elapsed_walltime >= .9 * drone.walltime_limit
        late = step * 10 >= 7 * drone.limit
        angles = np.asarray(drone.lidar_rays_angles()) if ranges is not None else None
        ranges = np.asarray(ranges) if ranges is not None else None
        self.deep.observe(drone, step, ranges, angles, semantic, self.audit)
        if self.opening_position is None and not late:
            self.opening_position = tuple(drone.pose)
        if self.corner is None and not late and ranges is not None:
            self.watch_bend(drone, step, ranges, angles, semantic)
            if step % 4 == drone.identifier % 4:
                self.corner = first_shared_bend(self.turn_reports, drone.team_size)
                if self.corner is not None:
                    self.audit.append((step, "bend_elected", self.corner))
        cutoff = self._ordinary_start_step(drone.limit)
        if step < cutoff:
            pair = self.opening_pair
            if count and ranges is not None and self.deep.near_neck(drone.pose,step) and step % 4 == drone.identifier % 4:
                pair.record(drone,step,self.lidar_lines(drone,ranges,angles,semantic),self.audit)
            if count == drone.initial_inventory and not pair.tried and pair.samples:
                refs = [ref for ref in self.deep.passages.nearby(drone.pose,cutoff) if ref[0] < cutoff]
                if self.deep.passages.last_for(refs,drone.team_size) == drone.identifier:
                    pair.choose(drone,step,cutoff,self.audit)
            if pair.targets and count:
                pair.move(drone,command,step,ranges,semantic,self)
            self.wall_approach = True if pair.targets and count else None
            return
        self.wall_approach = None
        if self.opening_pair.targets:
            self.audit.append((step,"gap_pair_aborted","phase_end"))
            self.opening_pair.targets = ()
        if not count or step < self.next_request or step - drone.last_attempt_step < 2:
            return
        if step % (2 * drone.team_size) != 2 * drone.identifier:
            return
        passages = self.deep.passages
        opening_limit = int(.15 * drone.limit)
        references = passages.nearby(drone.pose, opening_limit)
        is_passage = bool(references) or passages.near_recent_narrow(drone.pose, opening_limit)
        second = getattr(drone,"second_drop",None)
        halo_checked = (is_passage and not final and count == drone.initial_inventory-1
                        and second is not None and second.recent_at(drone.pose,step))
        if halo_checked:
            on_outer_halo = passages.opening_halo_only(
                drone.pose,references,opening_limit,passages.LOCAL_RADIUS+23.+SDK_SPACING)
            live = None
            if on_outer_halo:
                # A prior transit may reserve a wider area on the map. Keep
                # the actual passage and live turns protected.
                remembered = self.last_visible_turn
                try:
                    live = self._protected_turn(drone,step,ranges,angles,semantic)
                finally:
                    self.last_visible_turn = remembered
            if on_outer_halo and live is None and second.on_route_opportunity(drone,step,ranges,semantic):
                is_passage = False
                second.audit.append((step,"halo_review","outer_clear",len(references)))
            else:
                reason = "transit" if not on_outer_halo else live or "not_opportunity"
                second.audit.append((step,"halo_review",reason,len(references)))
        protected = "passage" if is_passage else self._protected_turn(drone, step, ranges, angles, semantic)
        if is_passage:
            winner = passages.last_for(references, drone.team_size)
            eligible = winner == drone.identifier and self._first_drop_exit_clear(drone, ranges, semantic)
        else:
            eligible = protected is not None and self._last_at_turn(drone, ranges, semantic)
        branch = (protected is not None and not eligible
                  and self.branch_exit.allows(drone, passages, step, protected, references, opening_limit, semantic)
                  and self._first_drop_exit_clear(drone, ranges, semantic))
        local = None
        if (protected is not None and not (eligible or branch)
                and not any(row[0] <= opening_limit for row in references)
                and not passages.near_recent_narrow(drone.pose,opening_limit)
                and self._first_drop_exit_clear(drone,ranges,semantic)):
            local = self.local_exit.candidate(drone,step,ranges,angles,semantic)
            if local is not None:
                self.local_exit.review['local_eligible'] += 1
        if protected is not None and not (eligible or branch or local is not None):
            if is_passage and not final and self.maneuvers.drop_in_lane(
                    self, drone, command, step, ranges, angles, semantic, count):
                return
            self.reject("turn_hold")
            key = "turn_hold_" + protected
            self.reject(key)
            if self.blocks[key] <= 12:
                self.audit.append((step, "turn_hold", protected, tuple(map(float, drone.pose))))
            return
        if self.rejected_patch.blocked(drone.pose, step):
            self.reject("skip_patch_active")
            return
        if not self._spaced_from_bombs(drone, semantic, False):
            self.reject("spacing")
            self._note_local_rejection(drone.pose, step)
            return
        if not self._patch_open(drone, semantic, step):
            self._note_local_rejection(drone.pose, step)
            return
        reserved = count < drone.initial_inventory
        opportunistic = (reserved and not final and protected is None and second is not None
                         and second.on_route_opportunity(drone,step,ranges,semantic))
        if not final:
            if not drone.search_roaming.departed:
                return
            if not drone.route:
                self.reject("no_route")
                return
            if reserved and ((not opportunistic and local is None and not self.deep.here(drone.pose, drone.blast_radius))
                             or self.last_drop_point is None
                             or math.dist(drone.pose, self.last_drop_point) < drone.blast_radius):
                self.reject("reserve")
                return
        team = getattr(drone,"team_wall",None)
        estimate = (team.query(drone,semantic,step) if team is not None and not final
                    else drone.placement_gain_query(semantic))
        gain, unweighted, support = estimate(drone.pose)
        minimum = self._coverage_minimum(step, drone.limit)
        if gain < minimum:
            if (step >= .30*drone.limit and team is not None and not reserved and not final
                    and protected is None and not is_passage
                    and team.propose_greedy_first(drone,command,step,ranges,angles,semantic,
                                                  minimum,estimate,count)):
                return
            self.reject("deadline_low_gain" if final else "low_gain")
            return
        if final:
            self.audit.append((step, "coverage_floor_pass", gain, minimum))
            self.audit.append((step, "coverage_evidence", unweighted, support))
            if branch:
                self.audit.append((step, "branch_authorized", self.branch_exit.claim[1], tuple(drone.pose)))
            self._place_selected(drone,command,step,count,local,"branch_exit" if branch else "deadline")
            return
        best_forward = self._forward_gain(drone, estimate)
        if gain < .70 * max(gain,best_forward):
            self.reject("forward_gain")
            return
        if not drone.grid.pose_fixed and not self._first_drop_exit_clear(drone, ranges, semantic):
            self.reject("exit_clearance")
            return
        self.audit.append((step, "coverage_floor_pass", gain, minimum))
        self.audit.append((step, "coverage_evidence", unweighted, support))
        self.audit.append((step, "route_gain", gain, best_forward))
        if opportunistic:
            second.audit.append((step,"on_route_request",tuple(map(float,drone.pose)),gain,best_forward))
            self._place_selected(drone,command,step,count,None,"on_route_second")
            return
        if (second is not None and reserved and not branch and local is None
                and protected is None and second.reserve(drone,step,ranges,semantic)):
            if second.control(drone,step,command,ranges,semantic) == "approach":
                team.reservation = None
                return
        if (team is not None and not protected and (second is None or second.plan is None)
                and self.maneuvers.start_approach(self, drone, step, ranges, angles, semantic, gain, estimate, count)):
            command.update(forward=0., lateral=0., rotation=0.)
            return
        if (team is not None and (second is None or second.plan is None)
                and not branch and local is None and not is_passage
                and protected is None and team.propose(drone,command,step,ranges,angles,semantic,
                                                          gain,estimate,count)):
            return
        reason = "deep_coverage" if reserved else ("late_coverage" if late else "coverage")
        if branch:
            self.audit.append((step, "branch_authorized", self.branch_exit.claim[1], tuple(drone.pose)))
        self._place_selected(drone,command,step,count,local,"branch_exit" if branch else reason)

    def _place_selected(self, drone, command, step, count, certified, reason):
        if certified is not None:
            reason, site = certified
            self.local_exit.pending = site
            self.audit.append((step,"local_amnesty_authorized",reason,site,tuple(drone.pose)))
        self.place(drone,command,step,reason,count)

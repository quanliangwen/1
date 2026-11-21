"""Attach the red inventory and scoring APIs to R295's search controller."""
import hashlib
import math
from collections import deque

import cv2
import numpy as np

from swarm_rescue.solutions.coverage_placement import CoveragePlacementDrone, marginal_coverage
from swarm_rescue.solutions.deadline_submission import DeadlineSubmission
from swarm_rescue.solutions.pre_submit_scan import PreSubmitScan
from swarm_rescue.solutions.partial_map_submit import provisional_map
from swarm_rescue.solutions.greedy_mapping import MapMemory
from swarm_rescue.solutions.final_map_relay import FinalMaps
from swarm_rescue.solutions.fast_closeout import FastCloseout
from swarm_rescue.solutions.drop_departure import DropDeparture
from swarm_rescue.solutions.closeout_departure import CloseoutDeparture, DEPARTING, FORCING
from swarm_rescue.solutions.messenger_run import MessengerRun
from swarm_rescue.solutions.second_drop_site import SecondDropSite
from swarm_rescue.solutions.team_wall import TeamWall
from swarm_rescue.solutions.submission_renderer import SubmissionBearings
from swarm_rescue.solutions.final_map_reconnect import FinalMapReconnect
from swarm_rescue.solutions.fine_wall_coverage import FineWallCoverage
from swarm_rescue.solutions.lbbd_rescue import LBBDRescue
from swarm_rescue.solutions.placement_preferences import PlacementPreferences
from swarm_rescue.solutions.local_escape import LocalEscape
from swarm_rescue.solutions.blocked_prefix import BlockedPrefix
from swarm_rescue.solutions.search_reconnect import SearchReconnect
from swarm_rescue.solutions.escape_exit_route import active_shortcut_guard, choose_exit, shortcut_allowed
from swarm_rescue.solutions.two_stage_exploration import SearchTask


def _map_cache_digest(owner, version, estimate, packed):
    header = f"{owner}:{version}:{estimate}:".encode("ascii")
    return hashlib.sha256(header + packed).hexdigest()


def cached_eligible(step, sent, received):
    return 0 <= received-sent <= 480 and 0 <= step-received <= 240

def local_score(bitmap, hits):
    # Assess predicted walls only against stable lidar evidence in the same frame.
    # A one-cell (two-pixel) tolerance allows raster quantization.
    k=np.ones((3,3), np.uint8)
    hit_band=cv2.dilate(hits.astype(np.uint8),k)>0
    map_band=cv2.dilate(bitmap.astype(np.uint8),k)>0
    precision=np.count_nonzero(bitmap & hit_band)/max(1,np.count_nonzero(bitmap))
    recall=np.count_nonzero(hits & map_band)/max(1,np.count_nonzero(hits))
    dice=2*precision*recall/max(1e-12,precision+recall)
    return dict(precision=precision,recall=recall,score=dice)


def _live_prefix_open(pose, point, hits):
    delta = np.asarray(point, dtype=float) - pose
    length = np.linalg.norm(delta)
    if length <= 1e-6:
        return True
    axis = delta / length
    along = hits @ axis
    side = np.abs(hits[:, 0] * axis[1] - hits[:, 1] * axis[0])
    return not np.any((along > 0.) & (along < 26.) & (side < 23.))


class RedHooks(LBBDRescue):
    mapping_time_search = True
    EARLY_SUBMISSION_STEPS = 24
    _sync_placement = CoveragePlacementDrone._sync_placement
    _all_inventory_empty = CoveragePlacementDrone._all_inventory_empty
    _known_bomb_positions = CoveragePlacementDrone._known_bomb_positions
    _placement_spacing = CoveragePlacementDrone._placement_spacing

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.team_size = self.limits.number_drones
        self.limit = self.limits.max_timestep_limit
        self.walltime_limit = self.limits.max_walltime_limit
        self.memory = MapMemory(*map(int, self.size_area))
        self.red_shadow_map = self.memory
        self.submission_bearings = SubmissionBearings(self.memory.width,self.memory.height)
        self.fine_wall_coverage = FineWallCoverage(self.memory, int(self.identifier), self.team_size)
        self.wall_source_packet = None
        self.blast_radius = round(.12 * min(self.size_area))
        self.initial_inventory = self.previous_inventory = self.pending_drop = None
        self.placement_goal = self.coverage = None
        self.last_coverage_step = self.last_attempt_step = -100
        self.drop_records = {}
        self.drop_hints = ()
        self.drop_hint_revision = -1
        self.team_exchange_audit = []
        self.grid.capture_scan_cells = True
        self.peer_scan_progress = {}
        self.own_scan_progress = deque(maxlen=8)
        self.own_scan_step = -1
        self.overlap_audit = []
        self.midflight_last_task = None
        self.midflight_review_audit = []
        self.midflight_peer_sweep = {}
        self.inventory_records = {}
        self.submitted = False
        self.red_packet = None
        self.final_maps = FinalMaps(int(self.identifier), self.team_size)
        self.fast_closeout = FastCloseout(self.identifier,self.team_size)
        self.drop_departure = DropDeparture()
        self.closeout = CloseoutDeparture()
        self.messenger = MessengerRun()
        self.second_drop = SecondDropSite()
        self.team_wall = TeamWall()
        self.final_reconnect = FinalMapReconnect()
        self.final_submission_versions = {}
        self.deadline_versions = {}
        self.prepared_map = None
        self.received_maps = {}
        self.cache_received_steps = {}
        self.map_cache_acks = {}
        self.last_map_offer = -45
        self.map_cache_audit = []
        self.submitted_cache = None
        self.relay_cache = None
        self.relay_attempts = 0
        self.last_relay_attempt = -45
        self.relay_audit = []
        self.map_bids = {}
        self.own_sent_bids = deque(maxlen=16)
        self.last_eligible_bid_comparison = {}
        self.submission_priority_audit = None
        self.deadline_submission = DeadlineSubmission()
        self.pre_submit_scan = PreSubmitScan()
        self.deadline_submission_event = None
        self.map_quality = None
        self.submission_elected_rank = None
        self.submission_wait_started = None
        self.submission_wait_for = None
        self.map_revision = {}
        self.last_confirmed_drop_step = None
        self.red_submission_step = None
        self.local_check_task = None
        self.local_check_until = 0
        self.local_check_audit = []
        self.recovery_audit = []
        self.sector_recovery_audit = []
        self.empty_recovery_audit = []
        self.progress_odometry = deque(maxlen=15)
        self.progress_odometry_step = None
        self.progress_veto_audit = []
        self.first_ready_to_submit_step = None
        self.early_submission = None
        self.early_submission_event = None
        self.placement = PlacementPreferences()
        self.local_escape = LocalEscape()
        self.blocked_prefix = BlockedPrefix()
        self.search_reconnect = SearchReconnect()

    # Red aircraft place bombs. The inherited rescue dispatcher would
    # treat those same bombs as pickup targets once they appear.
    def assign_early(self, hits):
        return

    def assign_local(self, hits=()):
        return

    def coordinate(self):
        return

    def receive(self):
        super().receive()
        for _, message in self.communicator.received_messages:
            if not isinstance(message, dict) or message.get("kind") != "two-stage":
                continue
            self.search_reconnect.record_contact(self)
            self.pre_submit_scan.on_message(int(self.elapsed_timestep))
            self._receive_team_coordination(message, int(self.elapsed_timestep))
            self.placement.receive(self, message)
            self.placement.branch_exit.receive(self, message)
            self.placement.local_exit.receive(self, message)
            self.placement.deep.passages.receive(self, message["id"], message)
            self._receive_scan_progress(message)
            self.fast_closeout.receive(self,message)
            self.team_wall.receive(self,message)
            self.submission_bearings.receive(message['id'],message.get('red_submission_bearings'))
            bid = message.get("red_map_bid")
            sender = message["id"]
            if (type(sender) is int and 0 <= sender < self.team_size
                    and isinstance(bid, tuple) and len(bid) == 3):
                stamp, score, ready = bid
                if (type(stamp) is int and 0 <= stamp <= int(self.elapsed_timestep)
                        and type(score) is int and 0 <= score <= 10000 and type(ready) is bool
                        and stamp > self.map_bids.get(sender, (-1, 0, False))[0]):
                    self.map_bids[sender] = bid
                    # Compare estimates from the same transmission step. Once
                    # separated, a new local score must not change that ordering.
                    if ready and stamp < DeadlineSubmission.window_start(self.limit):
                        own = next((sent for sent in reversed(self.own_sent_bids)
                                    if sent[0] == stamp and sent[2]), None)
                        if own is not None:
                            self.last_eligible_bid_comparison[sender] = stamp, score, own[1]
            self._receive_cached_map(sender, message, int(self.elapsed_timestep))
            self.final_maps.receive(sender, int(self.elapsed_timestep),
                                    message.get("red_final_have"), message.get("red_final_map"))
            self.final_reconnect.record(self, message, int(self.elapsed_timestep))
            packet = message.get("red_map")
            owner = message["id"]
            if packet is not None and packet[0] > self.map_revision.get(owner, -1):
                self.memory.merge(packet[1])
                self.fine_wall_coverage.merge_direct(owner, message.get("red_wall_sources"))
                self.map_revision[owner] = packet[0]
            self.messenger.receive(self, message, int(self.elapsed_timestep))

    def define_message_for_all(self):
        message = super().define_message_for_all()
        if message is None:
            return None
        step = int(self.elapsed_timestep)
        bid = self._own_map_bid(step)
        if bid is not None and bid[2] and step < DeadlineSubmission.window_start(self.limit):
            self.own_sent_bids.append(bid)
        offer = self._cached_map_offer(step)
        verified_drops = {k:p for k,p in self.drop_records.items()
                          if k not in self.placement.unlocalized_drops}
        return dict(message, red_map_offer=offer, red_map_relay=self._relay_map_offer(step),
                    red_turns=tuple(self.placement.local_turns),
                    red_branch_claim=self.placement.branch_exit.claim,
                    red_local_exit=self.placement.local_exit.packet(self, step),
                    red_fast_closeout=self.fast_closeout.packet(step),
                    red_wall_reservation=self.second_drop.packet(step) or self.team_wall.packet(step),
                    red_submission_bearings=self.submission_bearings.packet(step,self.red_packet[0] if self.red_packet is not None else None),
                    red_branch_acks=self.placement.branch_exit.acknowledgments(self, step),
                    red_passages=dict(self.placement.deep.passages.reports),
                    red_map_ack={owner: item[:3] for owner, item in self.received_maps.items()},
                    red_inventory=dict(self.inventory_records),
                    direct_scan_progress=self._advertise_scan_progress(step),
                    direct_latest_sweep=self.own_scan_progress[-1] if self.own_scan_progress else None,
                    red_drops=verified_drops, red_map=self.red_packet,
                    red_wall_sources=self.wall_source_packet,
                    drop_hints=(self.drop_hint_revision, self.drop_hints),
                     red_final_have=self.final_maps.mask,
                     red_final_map=self.final_maps.outgoing(step), red_map_bid=bid)

    def _receive_team_coordination(self, message, step):
        sender = message["id"]
        if type(sender) is not int or sender == self.identifier or not 0 <= sender < self.team_size:
            return
        for owner, record in message.get("red_inventory", {}).items():
            stamp, count = record
            previous = self.inventory_records.get(owner, (-1, None))
            if (0 <= owner < self.team_size and owner != self.identifier
                    and previous[0] < stamp <= step and 0 <= count <= self.initial_inventory
                    and (previous[1] is None or count <= previous[1])):
                self.inventory_records[owner] = record
                if count != previous[1]:
                    self.team_exchange_audit.append(("stock", step, sender, owner, count))
        for key, point in message.get("red_drops", {}).items():
            owner, ordinal = key
            if (key not in self.drop_records and owner != self.identifier
                    and 0 <= owner < self.team_size and 1 <= ordinal <= self.initial_inventory
                    and self._inside_team_point(point)):
                self.drop_records[key] = np.asarray(point, dtype=float)
                self.last_coverage_step = -100
                self.team_exchange_audit.append(("drop", step, sender, owner, ordinal))
        hints = message.get("drop_hints")
        if self.identifier != 0 and hints is not None:
            stamp, points = hints
            if self.drop_hint_revision < stamp <= step and len(points) <= 2:
                if all(self._inside_team_point(point) and math.isfinite(gain) and gain > 0
                       for point, gain in points):
                    self.drop_hint_revision, self.drop_hints = stamp, points
                    self.team_exchange_audit.append(("hints", step, sender, stamp, len(points)))

    def _inside_team_point(self, point):
        return (len(point) == 2 and all(math.isfinite(x) and abs(x) < limit / 2
                                       for x, limit in zip(point, self.size_area)))

    def placement_gain_query(self, semantic):
        bombs = self._known_bomb_positions(semantic)

        def query(point):
            return self.fine_wall_coverage.measure(self.memory, point, bombs, self.blast_radius,
                                                   step=self.elapsed_timestep)

        return query

    def _update_drop_hints(self, step, semantic):
        if (self.identifier != 0 or not self.grid.pose_fixed or self.frontier_egress.released is None
                or step % 60 or self.communicator_is_disabled()):
            return
        known_bombs = self._known_bomb_positions(semantic)
        coverage = marginal_coverage(self.memory, known_bombs, self.blast_radius)
        hints = []
        route_costs, _ = self.grid.tree(self.pose)
        walkable = self.grid.walkable()
        for cell, cost in sorted(route_costs.items(), key=lambda item: item[1]):
            if cost > 240:
                break
            point = tuple(self.grid.point(cell))
            if not (cost >= 20 and walkable[cell] and self._inside_team_point(point)):
                continue
            if self._placement_block(point, step, semantic, stationary=False) is not None:
                continue
            gain = float(coverage[self.memory.world_to_cell(point)])
            if gain >= .30:
                hints.append((gain, point))
        selected = []
        for gain, point in sorted(hints, reverse=True):
            if all(math.dist(point, old) >= 64 for old, _ in selected):
                selected.append((point, round(gain, 4)))
                if len(selected) == 2:
                    break
        self.drop_hints = tuple(selected)
        self.drop_hint_revision = step
        if selected:
            self.team_exchange_audit.append(("hint_offer", step, self.drop_hints))

    def _advertise_scan_progress(self, step):
        # The scan mask contains current local ray hits on both new and revisited cells.
        if (self.frontier_egress.released is None or not self.grid.pose_fixed or
                self.search_task is None or self.search_paused or self.carrying or self.queue or
                self.goal != self.search_task.point or step < self.recovery_until):
            self.own_scan_progress.clear()
            return None
        if (step != self.own_scan_step and step % 5 == self.identifier % 5
                and self.semantic_values() is not None and self.lidar_values() is not None
                and self.grid.last_scan_cells):
            self.own_scan_progress.append((step, self.grid.last_scan_cells))
            self.own_scan_step = step
        if not self.own_scan_progress or step - self.own_scan_progress[-1][0] > 12:
            return None
        cells = frozenset(cell for stamp, packet in self.own_scan_progress if step - stamp <= 40 for cell in packet)
        return self.own_scan_progress[-1][0], self.search_task.started, cells

    def _receive_scan_progress(self, message):
        sender = message["id"]
        if sender == self.identifier:
            return
        proof = message.get("direct_scan_progress")
        own_state = next((state for state in message["states"] if state["id"] == sender), None)
        if (proof is None or own_state is None or own_state["search"] is None or
                proof[1] != own_state["search"][0] or not 0 <= own_state["step"] - proof[0] <= 12):
            self.peer_scan_progress.pop(sender, None)
        else:
            self.peer_scan_progress[sender] = proof
        sweep = message.get('direct_latest_sweep')
        if (proof is not None and sender in self.peer_scan_progress and sweep is not None and
                sweep[0] == proof[0] and own_state['step'] >= sweep[0]):
            self.midflight_peer_sweep[sender] = (sweep[0], proof[1], frozenset(sweep[1]))
        else:
            self.midflight_peer_sweep.pop(sender, None)

    def _rank_redundant_search(self, assigned, blocks, gain, costs, claims):
        step = int(self.elapsed_timestep)
        sweeps = {peer: proof[2] for peer, proof in self.peer_scan_progress.items()
                  if peer in claims and claims[peer][0] == proof[1] and 0 <= step - proof[0] <= 12}
        ranks = {point: self._mapping_search_rank(blocks[point], gain, costs[self.grid.cell(point)], point)
                 for point in assigned}
        original = min(ranks, key=ranks.get)
        if not sweeps or len(ranks) < 2 or not self.grid.pose_fixed or self.communicator_is_disabled():
            return original
        footprint = blocks[original]
        close = self.grid.close_scan_cells()
        settled = {c for c in footprint if self.grid.evidence[c] < 0 and self.grid.searched[c] > int(close[c])}
        overlaps = [(peer, len(settled & sweep)) for peer, sweep in sweeps.items()]
        peer, duplicate = max(overlaps, key=lambda item: item[1])
        selected, tested = original, []
        original_new = None
        if duplicate >= 2 and 2 * duplicate >= len(footprint):
            original_new = self._frontier_novel_cells(original, close)
            hits = self._tail_live_hits()
            budget = costs[self.grid.cell(original)] + 40
            deadline_safe = step + self.SEARCH_REVIEW < self.limit and self.elapsed_walltime + 5 < self.walltime_limit
            if hits is not None and deadline_safe:
                for point in sorted(ranks, key=ranks.get):
                    if point == original or costs[self.grid.cell(point)] > budget:
                        continue
                    new = self._frontier_novel_cells(point, close)
                    if new < original_new + 2:
                        tested.append((point, new, 'novelty'))
                        continue
                    route = self.search_route(point)
                    if not self._local_check_route(point, route, hits):
                        tested.append((point, new, 'route'))
                        continue
                    tested.append((point, new, 'selected'))
                    selected = point
                    break
        self.overlap_audit.append((step, tuple(sorted(sweeps)), len(ranks), original, selected,
                                   (peer, duplicate, len(footprint), original_new, tested)))
        return selected

    def _frontier_novel_cells(self, point, close):
        # A cell counts only if the approach-side line stays inside known free space.
        grid = self.grid
        r, c = grid.cell(point)
        count = 0
        for row in range(max(0, r - 4), min(grid.evidence.shape[0], r + 5)):
            for col in range(max(0, c - 4), min(grid.evidence.shape[1], c + 5)):
                cell = row, col
                evidence = grid.evidence[cell]
                if evidence >= 3 or grid.blocked[cell] or (evidence < 0 and grid.searched[cell] > int(close[cell])):
                    continue
                end = grid.point(cell)
                distance = math.dist(point, end)
                if distance > 75:
                    continue
                line = np.linspace(point, end, max(2, math.ceil(distance / 10) + 1))
                if all(grid.evidence[inner] < 0 for sample in line[:-1]
                       if (inner := grid.cell(sample)) != cell):
                    count += 1
        return count

    def _review_transit_frontier(self, step):
        task = self.search_task
        if (task is None or task is self.midflight_last_task or step % 3 != self.identifier % 3
                or not 5 <= step - task.started <= 70 or not self.route or self.goal != task.point
                or self.search_paused or task.handoff is not None or task.return_check_until
                or self.local_check_task == task.started or self.carrying or self.queue
                or self.pending_drop is not None or self.gap_probe is not None or self.survey_run is not None
                or step < self.recovery_until or self.frontier_egress.released is None
                or not self.grid.pose_fixed or self.communicator_is_disabled()
                or step >= .72 * self.limit or self.elapsed_walltime >= .74 * self.walltime_limit
                or self.reached_search_point(task.point)):
            return
        # Proof must be from a fresh actual scan of the goal's immediate footprint,
        # while this very goal still has an active route. No intention is treated as observation.
        original = task.point
        centre = self.grid.cell(original)
        peers = self.fresh_states(age=12)
        evidence = []
        for peer, (stamp, started, cells) in self.midflight_peer_sweep.items():
            state = peers.get(peer)
            if (state is None or state['search'] is None or state['search'][0] != started
                    or not task.started < stamp <= step or step - stamp > 8):
                continue
            adjacent = {cell for cell in task.cells.intersection(cells)
                        if max(abs(cell[0]-centre[0]), abs(cell[1]-centre[1])) <= 1}
            if centre in adjacent or len(adjacent) >= 2:
                evidence.append((peer, stamp, len(adjacent)))
        if not evidence:
            return
        self.midflight_last_task = task
        review = dict(step=step, task=task.started, original=original, evidence=evidence,
                      selected=None, tested=[])
        self.midflight_review_audit.append(review)
        hits = self._tail_live_hits()
        if hits is None:
            return
        close = self.grid.close_scan_cells()
        original_new = self._frontier_novel_cells(original, close)
        review['original_new'] = original_new
        costs, work, _ = self.grid.search_work(self.pose)
        for state in peers.values():
            for cell in state.get('opening_cells', ()):
                work[cell] = False
        for cell in task.cells:
            work[cell] = False
        cap = min(140., self.search_distance(original) + 40.)
        walkable = self.grid.walkable()
        nearby = sorted((cost, cell) for cell, cost in costs.items()
                        if cost <= cap and work[cell] and walkable[cell]
                        and self.grid.clearance[cell] >= 23 and self.grid.evidence[cell] < 0)
        for cost, cell in nearby[:14]:
            point = tuple(self.grid.point(cell))
            if self.reached_search_point(point):
                continue
            new = self._frontier_novel_cells(point, close)
            if new < original_new + 2:
                review['tested'].append((point, new, 'novelty'))
                continue
            route = self.search_route(point)
            if not self._local_check_route(point, route, hits):
                review['tested'].append((point, new, 'route'))
                continue
            length = math.dist(self.pose, route[0]) + sum(math.dist(a, b) for a,b in zip(route,route[1:]))
            if length > cap:
                review['tested'].append((point, new, 'distance'))
                continue
            review['tested'].append((point, new, 'selected'))
            cells = frozenset(c for c in costs if work[c] and
                              max(abs(c[0]-cell[0]), abs(c[1]-cell[1])) <= 1)
            replacement = SearchTask(cells, point, step, self.search_steps, self.grid.local_coverage(cells))
            self.search_task = self.midflight_last_task = replacement
            self.goal, self.route = point, list(route)
            replacement.remaining = length
            replacement.motion = tuple(self.motion_pose if self.motion_pose is not None else self.pose)
            self.next_explore = step + self.SEARCH_REVIEW
            review.update(selected=point, new_cells=new, route_length=length)
            return

    def _render_submission(self, memory=None):
        if memory is None:
            memory = self.memory
        return self.submission_bearings.render(memory)

    def _submission_image(self, step):
        if self.final_maps.snapshots:
            memory, versions = self.final_maps.fuse(self.memory)
            image = self._render_submission(memory)
            if image.any():
                return image, None, versions
        image = self._render_submission()
        selected = self._select_submission_cache(step, image)
        if selected is None:
            return image, None, {}
        owner, (version, estimate, digest, packed) = selected
        shape = self.memory.height, self.memory.width
        image = np.unpackbits(np.frombuffer(packed, np.uint8), count=math.prod(shape)).reshape(shape)
        return image, (owner, version, estimate, digest), {}

    def _prepare_map_cache(self, step):
        if (self.previous_inventory != 0 or self.pending_drop is not None
                or self.map_quality is None or self.limit - step <= 48
                or self.walltime_limit - self.elapsed_walltime <= 3.
                or (self.prepared_map is not None and step - self.prepared_map[0] < 360)):
            return
        image = self._render_submission()
        if image.any():
            packed = np.packbits(image.reshape(-1) != 0).tobytes()
            digest = _map_cache_digest(int(self.identifier), step, self.map_quality, packed)
            self.prepared_map = (step, self.map_quality, digest, packed)
            return image
        return None

    def _cached_map_offer(self, step):
        prepared = self.prepared_map
        if (prepared is None or step - prepared[0] > 480
                or step - self.last_map_offer < 45 or self.communicator_is_disabled()):
            return None
        if not any(0 <= step - stamp <= 64 and self.map_cache_acks.get(peer) != prepared[:3]
                   for peer, (stamp, _, _) in self.map_bids.items()):
            # A receiving aircraft can still carry inventory. A recent actual
            # map message is enough as a contact witness.
            if not any(0 <= step - stamp <= 64 and self.map_cache_acks.get(peer) != prepared[:3]
                       for peer, stamp in self.map_revision.items()):
                return None
        self.last_map_offer = step
        return prepared

    def _relay_map_offer(self, step):
        if (self.identifier != 2 or self.limit - step > 720 or self.communicator_is_disabled()
                or self.relay_attempts >= 3 or step - self.last_relay_attempt < 45):
            return None
        # A recently received bid from the destination witnesses a contact.
        peer = self.map_bids.get(1)
        if peer is None or not 0 <= step - peer[0] <= 64:
            return None
        offer = self.received_maps.get(0)
        if offer is None or not 0 <= step - offer[0] <= 480:
            return None
        self.relay_cache = offer
        self.relay_attempts += 1
        self.last_relay_attempt = step
        self.relay_audit.append(("sent", step, 0, *offer[:3]))
        return 1, 0, offer

    def _receive_cached_map(self, sender, message, step):
        if type(sender) is not int or sender == self.identifier or not 0 <= sender < self.team_size:
            return
        ack = message.get("red_map_ack")
        if (self.prepared_map is not None and isinstance(ack, dict)
                and ack.get(int(self.identifier)) == self.prepared_map[:3]):
            self.map_cache_acks[sender] = self.prepared_map[:3]
        if (self.identifier == 2 and sender == 1 and self.relay_cache is not None
                and isinstance(ack, dict) and ack.get(0) == self.relay_cache[:3]
                and self.received_maps.get(0) == self.relay_cache):
            self.relay_attempts = 3
        offer = message.get("red_map_offer")
        self._store_cached_map(sender, offer, step)
        relay = message.get("red_map_relay")
        if (self.identifier == 1 and sender == 2 and isinstance(relay, tuple)
                and len(relay) == 3 and relay[:2] == (1, 0)
                and self._store_cached_map(0, relay[2], step)):
            self.relay_audit.append(("received", step, 0, *relay[2][:3]))

    def _store_cached_map(self, sender, offer, step):
        if not isinstance(offer, tuple) or len(offer) != 4:
            return
        version, estimate, digest, packed = offer
        size = self.memory.height * self.memory.width
        old = self.received_maps.get(sender)
        if (type(version) is not int or not 0 <= version <= step or step - version > 480
                or (old is not None and version <= old[0])
                or type(estimate) is not int or not 0 <= estimate <= 10000
                or type(digest) is not str or type(packed) is not bytes
                or len(packed) != (size + 7) // 8 or not any(packed)
                or _map_cache_digest(sender, version, estimate, packed) != digest):
            return
        self.received_maps[sender] = offer
        self.cache_received_steps[sender] = step
        self.map_cache_audit.append((step, sender, version, estimate, digest))
        return True

    def _select_submission_cache(self, step, own_image):
        hits = self.memory.hits >= 3
        if not hits.any():
            return None
        shape = (self.memory.height, self.memory.width)
        stride = self.memory.FINE
        own_score = local_score(own_image[::stride, ::stride] != 0, hits)["score"]
        best = None
        best_rank = (own_score, 0, 0)
        for sender, item in self.received_maps.items():
            if not cached_eligible(step, item[0], self.cache_received_steps[sender]):
                continue
            image = np.unpackbits(np.frombuffer(item[3],np.uint8),
                                  count=math.prod(shape)).reshape(shape)
            rank = (local_score(image[::stride, ::stride] != 0, hits)["score"], item[0], -sender)
            if rank[0] > own_score and rank > best_rank:
                best_rank = rank
                best = sender, item
        return best

    def _own_map_bid(self, step):
        if step >= DeadlineSubmission.window_start(self.limit):
            score = self.deadline_submission.score
            return (step, score, True) if score is not None and self.previous_inventory == 0 and self.pending_drop is None else None
        if self.map_quality is None or self.previous_inventory != 0 or self.pending_drop is not None:
            return None
        return step, self.final_maps.rank(self.map_quality), self.first_ready_to_submit_step is not None

    def _prefer_own_submission(self, step):
        owner = int(self.identifier)
        own_bid = self._own_map_bid(step)
        if own_bid is None:
            return False
        own = (own_bid[1], -owner)
        fresh = [(score, -peer, ready) for peer, (stamp, score, ready) in self.map_bids.items()
                 if 0 <= step - stamp <= 32]
        if any(ready and (score, peer) > own for score, peer, ready in fresh):
            return False
        best = max([(score, peer) for score, peer, _ in fresh] + [own])
        # When eligible peers separate, give a verified higher-ranked peer
        # one limited chance. The absolute window prevents repeated elections.
        if best == own:
            known_higher = [(other_score,-peer,stamp,own_score)
                            for peer,(stamp,other_score,own_score) in self.last_eligible_bid_comparison.items()
                            if step-stamp > 32 and self.map_bids[peer][0] == stamp
                            and (other_score,-peer) > (own_score,-owner)]
            if known_higher and step < self.pre_submit_scan.finish(self) + 48 and self.walltime_limit-self.elapsed_walltime > 1.5:
                if self.submission_priority_audit is None:
                    score, peer, stamp, own_score = max(known_higher)
                    self.submission_priority_audit = dict(step=step, preferred=-peer, agreed_step=stamp,
                                                          self_estimate=own_score, peer_estimate=score)
                return False
            return True
        # Keep broadcasting the verified inventory while the better aircraft
        # has a bounded opportunity to receive it and become eligible.
        if self.submission_wait_started is None:
            self.submission_wait_started = step
            self.submission_wait_for = -best[1]
        return (step - self.submission_wait_started >= 48 or self.limit - step <= 4
                or self.walltime_limit - self.elapsed_walltime <= 1.5)

    def _placement_block(self, point, step, semantic, *, stationary, minimum_clearance=23.):
        if not self.grid.pose_fixed or not self.search_roaming.departed:
            return "position"
        cell = self.grid.cell(point)
        if self.grid.evidence[cell] >= 0 or self.grid.clearance[cell] < minimum_clearance:
            return "clearance"
        if stationary:
            odom = self.odometer_values()
            if odom is None or not np.isfinite(odom[0]) or odom[0] > 2.5:
                return "speed"
        for hit in semantic:
            if getattr(hit.entity_type, "name", "") == "DISPOSAL_CENTER":
                angle = self.heading + hit.angle
                location = self.pose + hit.distance * np.array([math.cos(angle), math.sin(angle)])
                if math.dist(point, location) < 120:
                    return "disposal"
        if self.home is not None and math.dist(point, self.home) < 120:
            return "disposal"
        spacing = max(32., self._placement_spacing(step))
        if any(math.dist(point, bomb) < spacing for bomb in self._known_bomb_positions(semantic)):
            return "spacing"
        return None

    def _tail_live_hits(self):
        ranges = self.lidar_values()
        if ranges is None:
            return None
        ranges = np.asarray(ranges, dtype=float)
        valid = np.isfinite(ranges) & (ranges > 0.)
        if not valid.any():
            return None
        bearings = np.asarray(self.lidar_rays_angles())[valid] + self.heading
        return ranges[valid, None] * np.column_stack((np.cos(bearings), np.sin(bearings)))

    def waypoint(self):
        point = super().waypoint()
        point = choose_exit(self, self.local_escape, point)
        if active_shortcut_guard(self, self.local_escape) is not None:
            return point
        point = self.blocked_prefix.update(self, point)
        point = self.search_reconnect.waypoint(self,self.blocked_prefix,point)
        return self.final_reconnect.waypoint(self, point)

    def _search_waypoint_reached(self, point):
        view = self.blocked_prefix.view
        reconnect = self.search_reconnect.task
        if reconnect is not None and reconnect is self.search_task and tuple(point)==reconnect.point:
            return math.dist(self.pose,point) <= 10.
        if view.task is not None and view.active(self,self.search_task) and tuple(point) == view.task.point:
            return math.dist(self.pose,point) <= 10.
        if self.blocked_prefix.active(self) and tuple(point) == self.blocked_prefix.first:
            return False
        guard = active_shortcut_guard(self, self.local_escape)
        if guard is not None and tuple(point) == guard[1]:
            return False
        return self.reached_search_point(point)

    def _search_shortcut_allowed(self, point):
        view = self.blocked_prefix.view
        return (shortcut_allowed(self, self.local_escape, point)
                and self.blocked_prefix.allows_waypoint(self, point)
                and bool(view.guarded_route(self,[point],self.blocked_prefix.outside)))

    def _tail_prefix(self, route):
        return next((p for p in route if not self.reached_search_point(p)), None)

    def _progress_pose_changed(self, target, step):
        changed = super()._progress_pose_changed(target, step)
        if (not changed or self.progress_pose is None or len(self.progress_odometry) != 15
                or math.dist(self.pose, target) < 20):
            return changed
        dx = sum(v[0] for v in self.progress_odometry)
        dy = sum(v[1] for v in self.progress_odometry)
        if math.hypot(dx, dy) >= 2:
            return True
        self.progress_veto_audit.append((step, tuple(self.pose)))
        return False

    def _observe_progress_motion(self):
        step = int(self.elapsed_timestep)
        if self.progress_odometry_step == step:
            return
        if self.progress_odometry_step != step - 1:
            self.progress_odometry.clear()
        self.progress_odometry_step = step
        if (not self.grid.pose_fixed or self.frontier_egress.released is None or self.gap_probe is not None
                or self.mode not in ("explore", "search") or not self.carried_bombs_count()):
            self.progress_odometry.clear()
            return
        odom = self.odometer_values()
        if odom is None or not np.all(np.isfinite(odom)):
            self.progress_odometry.clear()
            return
        travel, relative, turn = map(float, odom)
        yaw = self.heading - turn + relative
        self.progress_odometry.append((travel * math.cos(yaw), travel * math.sin(yaw)))

    def recover(self, goal, ranges, force=False):
        self._observe_progress_motion()
        previous_until = self.recovery_until
        target = super().recover(goal, ranges, force=force)
        if (self.recovery_until == previous_until or self.frontier_egress.released is None
                or self.mode not in ("search", "explore") or self.gap_probe is not None
                or not self.carried_bombs_count()):
            return target
        hits = self._tail_live_hits()
        if hits is None:
            return target
        if math.dist(self.pose, target) >= 16 and _live_prefix_open(self.pose, target, hits):
            return target
        relative = np.asarray(ranges, dtype=float)
        bearings = np.asarray(self.lidar_rays_angles()) + self.heading
        finite = np.isfinite(relative) & (relative >= 62)
        desired = math.atan2(goal[1] - self.pose[1], goal[0] - self.pose[0])
        score = np.where(finite, relative + 35 * np.cos(bearings - desired), -np.inf)
        primary = [bearings[index] for index in np.argsort(-score)[:24] if finite[index]]
        candidates = [(angle, False) for angle in primary]
        if self.grid.pose_fixed:
            # Test a small fixed set only after every inherited ray choice
            # fails. The observed grid and full live tube still veto motion.
            sectors = desired + np.array([0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6,
                                           -6, 7, -7, 8, -8, 9, -9, 10, -10, 11, -11, 12]) * (math.pi / 12)
            candidates.extend((angle, True) for angle in sectors)
        for angle, sector in candidates:
            if sector:
                aligned = np.cos(bearings - angle) >= math.cos(math.pi / 24)
                if not np.any(finite & aligned):
                    continue
            point = tuple(self.pose + 30 * np.array([math.cos(angle), math.sin(angle)]))
            axis = (np.asarray(point) - self.pose) / 30
            along = hits @ axis
            side = np.abs(hits[:, 0] * axis[1] - hits[:, 1] * axis[0])
            if np.any((along > 0) & (along <= 56) & (side < 23)):
                continue
            cells = {self.grid.cell(q) for q in np.linspace(self.pose, point, 16)}
            cells.discard(self.grid.cell(self.pose))
            if (not cells or any(self.grid.evidence[c] >= 0 or self.grid.clearance[c] < 23 for c in cells)
                    or not _live_prefix_open(self.pose, point, hits)
                    or not self.search_roaming.allows(self.pose, point, [point])):
                continue
            if sector:
                self.sector_recovery_audit.append((int(self.elapsed_timestep), tuple(self.pose), point))
            self.recovery_point = point
            self.recovery_audit.append((int(self.elapsed_timestep), tuple(self.pose), tuple(target), point))
            return point
        if self.grid.pose_fixed and math.dist(self.pose, target) < 1e-6:
            step = int(self.elapsed_timestep)
            old_next = tuple(self.route[0]) if self.route else None
            self.empty_recovery_audit.append((step, tuple(self.pose), old_next))
            self.recovery_until = previous_until
            self.next_explore = min(self.next_explore, step + 1)
            # Let the normal search replan on its next tick. This tick still
            # emits the original hold command and passes the live guard.
        return target

    def _local_check_route(self, point, route, hits):
        if not route or not self.search_roaming.allows(self.pose, point, route):
            return False
        length = math.dist(self.pose, route[0]) + sum(math.dist(a, b) for a, b in zip(route, route[1:]))
        if length > 140:
            return False
        here = self.grid.cell(self.pose)
        if any(self.grid.evidence[c] >= 0 or self.grid.clearance[c] < 23
               for c in map(self.grid.cell, route) if c != here):
            return False
        prefix = self._tail_prefix(route)
        return prefix is not None and _live_prefix_open(self.pose, prefix, hits)

    def search_route(self, point):
        route = super().search_route(point)
        return self.blocked_prefix.view.guarded_route(self,route,self.blocked_prefix.outside)

    def continue_search(self, task, costs, work, pending, resumed):
        view = self.blocked_prefix.view
        if task is self.search_reconnect.task:
            return self.search_reconnect.continue_task(self,self.blocked_prefix,task)
        if task is view.task:
            point = task.point
            if not view.active(self,task) or math.dist(self.pose,point) <= 10.:
                reached = math.dist(self.pose,point) <= 10.
                if reached:
                    view.observed = view.center
                self.blocked_prefix.audit.append((int(self.elapsed_timestep),"view_reached" if reached else "view_expired",view.center,point))
                view.task = None
                return "completed"
            here = self.grid.cell(self.pose)
            if (not self.route or any(self.grid.evidence[c] >= 0 or self.grid.clearance[c] < 23.
                                      for p in self.route[:3] if (c := self.grid.cell(p)) != here)):
                view.task = None
                return "unavailable"
            return None
        if self.route and not view.guarded_route(self,self.route,self.blocked_prefix.outside):
            self.route = []
            return "unavailable"
        result = super().continue_search(task, costs, work, pending, resumed)
        step = int(self.elapsed_timestep)
        active = self.local_check_task == task.started
        if active and (self.reached_search_point(task.point) or step >= self.local_check_until):
            return "completed"
        if result != "completed":
            return result
        if (self.frontier_egress.released is None or not self.grid.pose_fixed
                or self.gap_probe is not None or step < self.recovery_until
                or step >= .72 * self.limit or self.elapsed_walltime >= .74 * self.walltime_limit):
            return result
        hits = self._tail_live_hits()
        if hits is None:
            return result
        if active:
            return None if self._local_check_route(task.point, self.route, hits) else result
        if self.reached_search_point(task.point) or self.grid.cell(task.point) in costs:
            return result
        close = self.grid.close_scan_cells()
        if not any(self.grid.searched[c] > close[c] and self.grid.searched_here[c] <= close[c] for c in task.cells):
            return result
        candidates = []
        for cell, cost in costs.items():
            if cost > 140 or self.grid.evidence[cell] >= 0 or self.grid.clearance[cell] < 23:
                continue
            point = tuple(self.grid.point(cell))
            offset = math.dist(point, task.point)
            if offset <= 80 and math.dist(point, self.pose) > 28:
                candidates.append((offset, cost, point))
        for _, _, point in sorted(candidates)[:8]:
            route = list(self.search_route(point))
            if not self._local_check_route(point, route, hits):
                continue
            task.point = self.goal = point
            self.route = route
            self.local_check_task = task.started
            self.local_check_until = step + 2 * self.SEARCH_REVIEW
            self.local_check_audit.append((step, task.started, point, self.search_distance(point)))
            return None
        return result

    def _force_deadline_submission(self, step):
        deadline = self.deadline_submission
        reason = deadline.fallback_reason(step, self.limit, self.elapsed_walltime, self.walltime_limit)
        if reason is None:
            return False

        if deadline.image is not None:
            image, cache, versions = deadline.image, deadline.cache, self.deadline_versions.copy()
        elif deadline.backup_image is not None:
            image, cache, versions = deadline.backup_image, None, {}
        else:
            image, cache, versions = self._submission_image(step)
            if not image.any():
                return False

        # Submission ends the SDK round before its next physics tick. Stock
        # has already been synchronized, so only completed drops count here.
        self.submit_exploration_map(image.astype(np.uint8, copy=False))
        self.submitted_cache = cache
        self.final_submission_versions = versions
        self.submission_elected_rank = deadline.score
        self.red_submission_step = step
        self.submitted = True
        self.deadline_submission_event = dict(
            step=step, fallback=reason, remaining_steps=self.limit-step,
            remaining_walltime=self.walltime_limit-self.elapsed_walltime,
            local_inventory=self.previous_inventory, team_confirmed=self._all_inventory_empty(),
            backup_step=deadline.backup_step if image is deadline.backup_image else None,
        )
        return True

    def _submit_at_deadline(self, step):
        deadline = self.deadline_submission
        clear = self.previous_inventory == 0 and self.pending_drop is None
        if not clear:
            return
        refresh = (len(self.final_maps.snapshots) > len(self.deadline_versions)
                   and self.walltime_limit - self.elapsed_walltime > 3
                   and step % 4 == int(self.identifier) % 4)
        if deadline.score is None or refresh:
            image, cache, versions = self._submission_image(step)
            if not image.any():
                return
            deadline.image = image.astype(np.uint8)
            deadline.cache = cache
            self.deadline_versions = versions
            deadline.score = self.final_maps.rank(self.map_quality or 0)
        own = deadline.score, -int(self.identifier)
        peers = DeadlineSubmission.peer_ranks(step,self.limit,self.map_bids)
        if not DeadlineSubmission.submit_due(step,self.limit,own,peers):
            return
        self.submit_exploration_map(deadline.image)
        self.submitted_cache = deadline.cache
        self.final_submission_versions = self.deadline_versions.copy()
        self.submission_elected_rank = deadline.score
        self.red_submission_step = step
        self.submitted = True
        self.deadline_submission_event = dict(step=step,local_estimate=deadline.score,
            in_window_peer_estimates={-peer: score for score,peer in peers},
            slot=DeadlineSubmission.slot(self.limit,deadline.score),
            team_confirmed=self._all_inventory_empty())

    def _submission_window_open(self, step):
        return step >= self.limit * 3 // 5 or self.elapsed_walltime >= .85 * self.walltime_limit

    def _try_early_submission(self, step):
        if (int(self.identifier) != 0 or self.previous_inventory != 0
                or self.pending_drop is not None or not self._all_inventory_empty()
                or any(not 0 <= self.inventory_records[peer][0] <= step
                       for peer in range(self.team_size))):
            return False
        if self.early_submission is None:
            if provisional_map(step, self.map_quality, self.map_revision,
                               self.walltime_limit-self.elapsed_walltime):
                return False
            image, cache, versions = self._submission_image(step)
            if not image.any():
                return False
            image = image.astype(np.uint8, copy=True)
            self.early_submission = step, image, cache, versions.copy()
            self.deadline_submission.remember(step, image)
            if self.first_ready_to_submit_step is None:
                self.first_ready_to_submit_step = step
        ready, saved_image, saved_cache, saved_versions = self.early_submission
        if step-ready < self.EARLY_SUBMISSION_STEPS:
            return False
        # One collection budget covers all old scan, snapshot and election waits.
        image, cache, versions = self._submission_image(step)
        if not image.any():
            image, cache, versions = saved_image, saved_cache, saved_versions
        self.submit_exploration_map(image.astype(np.uint8, copy=False))
        self.submitted_cache = cache
        self.final_submission_versions = versions.copy()
        self.submission_elected_rank = self.final_maps.rank(self.map_quality or 0)
        self.red_submission_step = step
        self.submitted = True
        self.early_submission_event = dict(ready_step=ready, step=step,
                                          collection_steps=self.EARLY_SUBMISSION_STEPS)
        return True

    def control(self):
        step = int(self.elapsed_timestep)
        before = self.previous_inventory
        self._sync_placement(step)
        if before is not None and self.previous_inventory < before:
            self.last_confirmed_drop_step = step
        if self.submitted or self._force_deadline_submission(step):
            return CoveragePlacementDrone._empty_command()
        command = super().control()
        command["place_bomb"] = 0
        if self.pose is None:
            return command

        if self._try_early_submission(step):
            return command

        # Final-window fallback: track every frame, and once the closeout state
        # machine takes over a stalled bomb-carrying drone, it owns the command
        # so the ordinary branches cannot override its deterministic departure.
        wall_left = self.walltime_limit - self.elapsed_walltime
        steps_left = self.limit - step
        self.closeout.tick(self, step, command, wall_left, steps_left)
        if self.closeout.state in (DEPARTING, FORCING):
            return command

        # Dedicated messenger: once active it owns navigation so the ordinary
        # exploration/placement branches cannot override its tour.
        if self.messenger.tick(self, step, command, steps_left):
            return command

        ranges = self.lidar_values()
        semantic = self.semantic_values() or ()
        if ranges is not None and step % 4 == 0:
            observations = self.memory.observe(self.pose, self.heading, ranges, self.lidar_rays_angles(), semantic)
            fixed = self.grid.pose_fixed and not self._odometry_only
            self.fine_wall_coverage.observe(observations, fixed)
            self.submission_bearings.observe(self.memory,self.pose,self.heading,np.asarray(ranges),
                                             np.asarray(self.lidar_rays_angles()),semantic)
        refresh = self.pre_submit_scan.refresh_due(self,step)
        if refresh or step % 45 == self.identifier:
            self.red_packet = step, self.memory.packet()
            self.wall_source_packet = self.fine_wall_coverage.packet()
            if refresh:
                self.pre_submit_scan.refreshed.append(step)
            _, wall_evidence, _, _ = self.red_packet[1]
            # Lightweight version of the existing observed-area and stable-wall
            # estimate. Ground-truth map and official score are unavailable in flight.
            known = self.memory.free.mean()
            stable = min(1., np.count_nonzero(wall_evidence >= 3) / (.018 * self.memory.hits.size))
            self.map_quality = round(10000 * (.90 * known + .10 * stable))
            prepared_image = self._prepare_map_cache(step)
            deadline = self.deadline_submission
            if prepared_image is not None:
                deadline.remember(step, prepared_image)
            elif (deadline.backup_due(step) and self.walltime_limit - self.elapsed_walltime > 3.
                  and np.any(wall_evidence >= 3)):
                image = self._render_submission()
                if image.any():
                    deadline.remember(step, image)
        self._update_drop_hints(step, semantic)
        maneuvers = self.placement.maneuvers
        if self.previous_inventory or maneuvers.exit is not None or maneuvers.waiting_exit is not None:
            maneuvers.remember(self, step)
        if step >= self.placement._ordinary_start_step(self.limit) and self.search_roaming.departed:
            self.placement.local_exit.observe(self,step,ranges,semantic,self.placement.audit)
            if self.previous_inventory:
                self.placement.branch_exit.observe(self, self.placement.deep.passages, step, self.placement.audit)

        first_drop = (before is not None and before==self.initial_inventory
                      and self.previous_inventory==before-1 and self.previous_inventory>0)
        self.drop_departure.update(self,step,first_drop)
        self.drop_departure.steer(self,command,step,ranges,semantic)
        self.second_drop.observe_route(self,step,ranges,semantic)
        if maneuvers.waiting_exit is not None or maneuvers.exit is not None:
            self.placement.finish_request(self, step)
            if maneuvers.advance(self.placement, self, command, step, ranges, semantic):
                return command
        if self.fast_closeout.act(self,step,command,ranges,semantic):
            self.team_wall.reservation=None
            return command
        if self.drop_departure.controls_step==step:
            self.team_wall.reservation=None
            self.placement.finish_request(self,step)
            return command
        if maneuvers.approach is not None:
            self.placement.finish_request(self, step)
            if maneuvers.advance(self.placement, self, command, step, ranges, semantic):
                return command
        state = self.second_drop.control(self,step,command,ranges,semantic)
        if state == "approach":
            self.team_wall.reservation = None
            self.placement.finish_request(self,step)
            return command
        if state != "ready" and self.team_wall.steer(self,command,step,ranges,semantic):
            self.local_escape.apply(self,command,step,ranges,semantic)
            return command

        # Freeze the closing submission snapshot after this aircraft is empty.
        # R483's ordinary live map packets continue feeding its existing rules.
        if (self.previous_inventory == 0 and self.pending_drop is None
                and (step >= self.limit * 9 // 10 or self._all_inventory_empty()
                     and step >= self.pre_submit_scan.finish(self))):
            self.final_maps.freeze(step, self.memory)
        if step >= DeadlineSubmission.window_start(self.limit):
            self._submit_at_deadline(step)
            if self.submitted:
                return command
            if not self._all_inventory_empty():
                self.placement.update(self,command,step,ranges,semantic)
            self.local_escape.apply(self,command,step,ranges,semantic)
            return command

        if self._all_inventory_empty():
            latest = max(stamp for stamp, _ in self.inventory_records.values() if stamp <= step)
            # Requests are processed on a physics tick. Empty inventory can
            # only be observed on a later tick, including the local last drop.
            if self.pending_drop is None and latest <= step:
                if self.first_ready_to_submit_step is None:
                    self.first_ready_to_submit_step = step
                if not self._submission_window_open(step):
                    return command
                if self.pre_submit_scan.waiting(self,step):
                    self.pre_submit_scan.record_wait(self,step)
                    return command
                self.pre_submit_scan.record_finish(self,step)
                if self.final_maps.waiting(step, DeadlineSubmission.window_start(self.limit),
                                           self.walltime_limit - self.elapsed_walltime):
                    return command
                if not self._prefer_own_submission(step):
                    return command
                if provisional_map(step, self.map_quality, self.map_revision,
                                   self.walltime_limit-self.elapsed_walltime):
                    return command
                image, cache, versions = self._submission_image(step)
                if image.any():
                    self.submit_exploration_map(image.astype(np.uint8))
                    self.submitted_cache = cache
                    self.final_submission_versions = versions
                    self.submission_elected_rank = self.final_maps.rank(self.map_quality or 0)
                    self.red_submission_step = step
                    self.submitted = True
        else:
            self.placement.update(self,command,step,ranges,semantic)
        self.local_escape.apply(self,command,step,ranges,semantic)
        return command


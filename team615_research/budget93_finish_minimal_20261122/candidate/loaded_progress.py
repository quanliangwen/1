"""Independent carried-episode progress and bounded scheduled-wait certificates."""
from collections import Counter
import math


def distance(a, b):
    return math.dist(a[:2], b[:2])


class CarriedProgress:
    CHECK_STEPS = 50
    STALL_STEPS = 300
    WAIT_STEPS = 480
    REVIEW_STEPS = 120

    def __init__(self):
        self.active = False
        self.stats = Counter()
        self.certificate = None
        self.next_review = 0

    def sync(self, carrying, now, pose, motion=None):
        if carrying == self.active:
            return
        self.active = carrying
        self.certificate = None
        if carrying:
            self.started = self.best_step = now
            self.next_check = now
            self.next_review = now
            self.history, self.pending = {}, {}
            self.accepted_point = tuple(pose)
            self.best_motion = tuple(motion) if motion is not None else tuple(pose)
            self.reviews = 0
            self.recovered = False
            self.remaining = None
            self.departure_grace = now
            self.stats['episodes'] += 1
        else:
            self.history, self.pending = {}, {}
            self.remaining = None
            self.stats['completed_or_lost_load'] += 1

    def _measure(self, drone, target):
        now, grid = drone.elapsed_timestep, drone.grid
        cell = grid.cell(drone.pose)
        motion = drone.motion_pose if drone.motion_pose is not None else drone.pose
        if cell not in self.history and cell not in self.pending:
            self.pending[cell] = now, tuple(drone.pose), tuple(motion)
        if now < self.next_check:
            return
        self.next_check = now + self.CHECK_STEPS
        self.stats['distance_checks'] += 1
        cells = ((grid.cell(target),) if drone.delivery_point is not None
                 else grid.contact_cells(target, 75, loaded=True))
        costs = grid.tree_cells(cells, loaded=True)[0] if cells else {}
        if cell not in costs and cells:
            costs = grid.tree_cells(cells, loaded=True, narrow=True)[0]
        current = costs.get(cell, math.inf)
        raw_best = min((costs.get(key, math.inf) for key in self.history), default=math.inf)
        accepted = costs.get(grid.cell(self.accepted_point), math.inf)
        if not math.isfinite(accepted) and math.isfinite(raw_best):
            key = min(self.history, key=lambda key: costs.get(key, math.inf))
            _, self.accepted_point, self.best_motion = self.history[key]
            accepted = raw_best
        # Pending first visits remain separate until this check. The current
        # cell may have been reached at step49; that does not erase its new
        # record when the step50 map is compared with older history.
        for key, (stamp, pose, measured_motion) in sorted(self.pending.items(), key=lambda item: item[1][0]):
            cost = costs.get(key, math.inf)
            novel = math.isfinite(cost) and cost < raw_best-1e-7
            raw_best = min(raw_best, cost)
            if novel and not math.isfinite(accepted):
                self.accepted_point, self.best_motion, accepted = pose, measured_motion, cost
            elif (novel and accepted-cost >= 20-1e-7
                    and distance(measured_motion, self.best_motion) > 12):
                self.best_step, self.best_motion, self.accepted_point = stamp, measured_motion, pose
                accepted = cost
                self.reviews, self.recovered = 0, False
                self.stats['new_historical_best'] += 1
        self.history.update(self.pending)
        self.pending.clear()
        self.remaining = current if math.isfinite(current) else None
        if self.remaining is None:
            self.stats['unknown_checks'] += 1

    def _dependencies(self, drone, path, index):
        states = drone.fresh_states(30)
        if not states:
            return {}
        from swarm_rescue.solutions.two_stage_paths import Reservations, progress_path
        from swarm_rescue.solutions.two_stage_dispatch import traffic_priority
        table = Reservations(drone.grid, drone.limits.max_timestep_limit)
        swept = table.sweep(path[index][1:], path[index+1][1:])
        priority = traffic_priority(drone.identifier, drone.pose, True, drone.home)
        result = {}
        for identifier, state in states.items():
            if (identifier == drone.identifier or
                    traffic_priority(identifier, state['point'], state['held'] is not None, drone.home) > priority):
                continue
            peer_path = progress_path(state, drone.elapsed_timestep, drone.grid.speed_scale)
            for action, (a, b) in enumerate(zip(peer_path, peer_path[1:]), max(1, state.get('path_index', 1))):
                if (abs(b[0]+2-path[index][0]) <= 3
                        and swept & table.sweep(a[1:], b[1:], 58)):
                    result[identifier] = dict(path=tuple(tuple(p) for p in state.get('path', ())),
                        action=action, point=tuple(state['point']), motion_step=state['step'])
                    break
        return result

    def _peer_valid(self, drone, certificate):
        for identifier, record in certificate['predecessors'].items():
            state = drone.states.get(identifier)
            if state is None or drone.elapsed_timestep-state['step'] > 60 or state['health'] <= 0:
                return False
            if tuple(tuple(p) for p in state.get('path', ())) != record['path']:
                return False
            if state.get('path_index', 1) > record['action']:
                self.stats['predecessor_action_completed'] += 1
                return False
            if distance(state['point'], record['point']) > 12:
                record['point'], record['motion_step'] = tuple(state['point']), state['step']
                self.stats['predecessor_motion_updates'] += 1
        return True

    def _waiting(self, drone):
        now, path, index = drone.elapsed_timestep, drone.timed_path, drone.path_index
        old = self.certificate
        same = old is not None and path is old['path'] and index == old['action'] and drone.task == old['task']
        if old is not None and not same:
            if now >= old['end']:
                self.departure_grace = max(self.departure_grace, min(old['until']+self.CHECK_STEPS,
                                             self.best_step+self.WAIT_STEPS+self.CHECK_STEPS))
            self.certificate = None
        is_wait = (bool(path) and 0 < index < len(path)-1
                   and distance(path[index-1][1:], path[index][1:]) < 1
                   and distance(path[index][1:], path[index+1][1:]) >= 1
                   and distance(drone.pose, path[index][1:]) <= 20)
        if not is_wait:
            return False, False
        if self.certificate is None:
            a, b = path[index-1], path[index]
            if b[0] <= now:
                return False, False
            # Fixed across path replacements unless a genuinely new historical
            # best was reached. Static safety windows need no named predecessor.
            cap = min(b[0], self.best_step+self.WAIT_STEPS)
            if self.remaining is not None:
                cruise = 2.5*drone.grid.speed_scale
                cap = min(cap, drone.limits.max_timestep_limit-math.ceil(self.remaining/cruise)-12)
            self.certificate = dict(path=path, task=drone.task, action=index, start=a[0], end=b[0],
                until=cap, predecessors=self._dependencies(drone, path, index), valid=True)
            self.stats['wait_certificates'] += 1
        certificate = self.certificate
        if self.remaining is not None:
            certificate['until'] = min(certificate['until'], drone.limits.max_timestep_limit
                - math.ceil(self.remaining/(2.5*drone.grid.speed_scale))-12)
        if certificate['valid'] and not self._peer_valid(drone, certificate):
            certificate['valid'] = False
            self.stats['wait_invalidations'] += 1
        # Motion evidence is recorded without ever pushing the fixed end later.
        if certificate['valid'] and certificate['until'] == certificate['end'] and now >= certificate['end']:
            self.departure_grace = max(self.departure_grace, certificate['end']+self.CHECK_STEPS)
        valid = certificate['valid'] and now < certificate['until']
        expired = (not certificate['valid'] or now >= certificate['until']
                   and (certificate['until'] < certificate['end'] or now > certificate['end']+12))
        return valid, expired

    def update(self, drone, target):
        now = drone.elapsed_timestep
        self.sync(bool(drone.carrying), now, drone.pose, drone.motion_pose)
        if not self.active or target is None:
            return
        self._measure(drone, target)
        waiting, expired = self._waiting(drone)
        if waiting or now < self.departure_grace or now < drone.recovery_until:
            return
        age = now-self.best_step
        stalled = age >= self.STALL_STEPS and (self.remaining is None or self.remaining > drone.grid.CELL)
        if not (stalled or expired) or now < self.next_review:
            return
        self.next_review = now+self.REVIEW_STEPS
        if self.reviews < 2:
            self.reviews += 1
            self.stats['bounded_replans'] += 1
            if self.remaining is None:
                self.stats['unreachable_reviews'] += 1
            # Existing local_route retains the old path if no replacement is
            # found while it is still live; reservation/parking rules stay intact.
            drone.local_route(target)
        elif (stalled and age >= 2*self.STALL_STEPS and not self.recovered
              and not (self.certificate is not None and self.certificate['valid']
                       and now < self.certificate['end'])):
            self.recovered = True
            self.stats['bounded_recoveries'] += 1
            if self.remaining is None and drone.return_probe is not None:
                drone.checked_return_cells.add(drone.grid.cell(drone.return_probe[0]))
                drone.return_probe = None
            drone.recover(target, drone.lidar_values(), force=True)
        if drone.recovery_until > now:
            # A recovery started by local_route or this ledger must not be
            # overwritten by disposal_goal restoring an old committed leg.
            drone.timed_path, drone.legs = (), []
            drone.next_route = max(drone.next_route, drone.recovery_until)

"""Return once to the first shared split area, using onboard trail and radio."""
import math

import numpy as np

from swarm_rescue.solutions.deadline_submission import DeadlineSubmission


class ReturnExchange:
    FRACTION_PERCENT = 60
    SPLIT_SPAN = 160.
    LAUNCH_CLEAR = 140.
    MARK_CONTACT = 150.
    CONTACT_AREA = 160.
    STATE_AGE = 12
    TRAIL_SPACING = 12.
    REACHED = 8.
    MIN_WALL_LEFT = 8.
    SEND_MARGIN = 12
    ACK_FLUSH = 2

    def __init__(self):
        self.anchor = None
        self.launch = None
        self.trail = []
        self.cells = {}
        self.gate = None
        self.phase = 'OBSERVE'
        self.route = []
        self.detour = []
        self.next_plan = 0
        self.floor = None
        self.receipts = {}
        self.complete_step = None
        self.hold = None
        self.started_step = None
        self.audit = []

    @classmethod
    def start(cls, drone):
        return drone.limit * cls.FRACTION_PERCENT // 100

    @classmethod
    def budget_open(cls, drone, step):
        return (step < DeadlineSubmission.window_start(drone.limit)-cls.SEND_MARGIN
                and drone.walltime_limit-drone.elapsed_walltime > cls.MIN_WALL_LEFT)

    def owns(self, drone, step):
        return (self.phase != 'RELEASED' and step >= self.start(drone)
                and drone.previous_inventory == 0 and drone.pending_drop is None
                and self.budget_open(drone, step))

    @staticmethod
    def inside(drone, point):
        try:
            return (isinstance(point, (tuple, list, np.ndarray)) and len(point) == 2
                    and all(math.isfinite(float(v)) and abs(float(v)) < size/2
                            for v, size in zip(point, drone.size_area)))
        except (TypeError, ValueError):
            return False

    @staticmethod
    def known_segment(drone, a, b):
        grid = drone.grid
        length = math.dist(a, b)
        for p in np.linspace(a, b, max(2, 1+math.ceil(length/4.))):
            cell = grid.cell(p)
            clearance = grid.clearance[cell]
            if grid.evidence[cell] >= 0 or (clearance < 23.
                    and not (grid.tight[cell] and clearance >= grid.HULL_CLEARANCE)):
                return False
        return True

    @staticmethod
    def key(point):
        return tuple(round(float(x)/8.) for x in point)

    def rebuild(self):
        self.cells = {self.key(p): i for i, p in enumerate(self.trail)}

    def remember(self, drone):
        point = tuple(map(float, drone.pose))
        if self.trail and math.dist(point, self.trail[-1]) < self.TRAIL_SPACING:
            return
        cell = self.key(point)
        close = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                i = self.cells.get((cell[0]+dx, cell[1]+dy))
                if (i is not None and math.dist(point, self.trail[i]) <= self.REACHED
                        and self.known_segment(drone, point, self.trail[i])):
                    close.append(i)
        if close:
            # Remove a completed loop only where a short known-free join exists.
            self.trail = self.trail[:min(close)+1]
            self.rebuild()
        self.trail.append(point)
        self.cells[cell] = len(self.trail)-1

    def set_gate(self, drone):
        if self.anchor is None or self.gate is not None:
            return
        point = self.anchor[1:]
        near = [i for i, p in enumerate(self.trail) if math.dist(p, point) <= self.CONTACT_AREA]
        if near:
            index = min(near, key=lambda i: math.dist(self.trail[i], point)) if int(drone.identifier) == 0 else near[-1]
            self.trail = self.trail[index:]
            self.gate = self.trail[0]
            self.rebuild()
            if self.phase == 'RETURN':
                self.route = list(reversed(self.trail))
                self.detour = []

    def observe(self, drone, step):
        if step >= self.start(drone) and not self.budget_open(drone, step):
            if self.phase != 'RELEASED':
                self.phase = 'RELEASED'
                self.audit.append((step, 'return_cutoff'))
            return
        if drone.pose is None or not self.inside(drone, drone.pose):
            return
        if self.launch is None:
            self.launch = tuple(map(float, drone.pose))
        if self.phase == 'OBSERVE':
            self.remember(drone)
        if (int(drone.identifier) == 0 and self.anchor is None and step < self.start(drone)
                and drone.grid.pose_fixed and not drone._odometry_only
                and not drone.communicator_is_disabled()
                and math.dist(self.launch, drone.pose) >= self.LAUNCH_CLEAR):
            points = [tuple(map(float, drone.pose))]
            for peer in range(1, drone.team_size):
                state = drone.states.get(peer)
                if (state is None or not 0 <= step-state['step'] <= self.STATE_AGE
                        or state['health'] <= 0 or not self.inside(drone, state.get('point'))):
                    break
                points.append(state['point'])
            if len(points) == drone.team_size:
                span = max(math.dist(a, b) for a in points for b in points)
                cell = drone.grid.cell(drone.pose)
                if (span >= self.SPLIT_SPAN and max(math.dist(points[0], p) for p in points) <= self.MARK_CONTACT
                        and drone.grid.evidence[cell] < 0 and drone.grid.clearance[cell] >= 23.):
                    self.anchor = (step, *map(float, drone.pose))
                    self.audit.append((step, 'mark_first_split', self.anchor, float(span)))
        self.set_gate(drone)

    def packet_due(self, drone, step):
        return self.owns(drone, step) and self.floor is None

    def packet_built(self, drone, step):
        if (self.floor is None and self.owns(drone, step) and drone.red_packet is not None
                and self.start(drone) <= drone.red_packet[0] <= step):
            self.floor = drone.red_packet[0]

    def at_hub(self, drone):
        return (int(drone.identifier) == 0 and self.phase == 'HOLD' and self.anchor is not None
                and drone.pose is not None and math.dist(drone.pose, self.anchor[1:]) <= self.REACHED)

    def message(self, drone, step):
        return dict(anchor=self.anchor, active=self.owns(drone, step), floor=self.floor,
                    hub_ready=self.at_hub(drone),
                    acks=dict(self.receipts) if int(drone.identifier) == 0 else {})

    @staticmethod
    def valid_map(drone, packet, step):
        if not isinstance(packet, tuple) or len(packet) != 2:
            return False
        version, evidence = packet
        if (type(version) is not int or not 0 <= version <= step
                or not isinstance(evidence, tuple) or len(evidence) != 4):
            return False
        ids, values, free, visits = evidence
        return (isinstance(ids, np.ndarray) and ids.ndim == 1 and ids.dtype.kind in 'iu'
                and np.asarray(values).shape == ids.shape
                and (not ids.size or (ids.min() >= 0 and ids.max() < drone.memory.hits.size))
                and np.asarray(free).size*8 >= drone.memory.free.size
                and np.asarray(visits).shape == drone.memory.shape)

    def receive(self, drone, message, step):
        sender = message.get('id')
        body = message.get('red_return_exchange')
        if (type(sender) is not int or not 0 <= sender < drone.team_size or sender == drone.identifier
                or not isinstance(body, dict)):
            return
        incoming = body.get('anchor')
        if (self.anchor is None and int(drone.identifier) != 0
                and isinstance(incoming, (tuple, list)) and len(incoming) == 3
                and type(incoming[0]) is int and 0 <= incoming[0] < self.start(drone)
                and incoming[0] <= step and self.inside(drone, incoming[1:])):
            self.anchor = tuple(incoming)
            self.audit.append((step, 'adopt_first_split', self.anchor, sender))
            self.set_gate(drone)
        if self.anchor is None or not isinstance(incoming, (tuple, list)) or tuple(incoming) != self.anchor:
            return
        if (sender == 0 and self.floor is not None and body.get('hub_ready') is True
                and self.owns(drone, step) and isinstance(body.get('acks'), dict)):
            ack = body['acks'].get(int(drone.identifier))
            if (type(ack) is int and self.floor <= ack <= step and self.phase != 'DELIVERED'):
                self.phase = 'DELIVERED'
                self.hold = tuple(map(float, drone.pose)) if drone.pose is not None else None
                self.audit.append((step, 'delivery_ack', ack))
        if (self.at_hub(drone) and self.owns(drone, step) and sender not in self.receipts
                and body.get('active') is True):
            floor = body.get('floor')
            packet = message.get('red_map')
            if (type(floor) is int and self.start(drone) <= floor <= step
                    and self.valid_map(drone, packet, step) and packet[0] >= floor
                    and drone.map_revision.get(sender, -1) >= packet[0]):
                self.receipts[sender] = packet[0]
                self.audit.append((step, 'map_received', sender, packet[0]))

    def brake(self, drone, command, point=None):
        point = tuple(drone.pose) if point is None else point
        command.update(drone.drive(point, drone.measured_velocity(), ignore_own_bombs=True))
        command['place_bomb'] = 0

    def tick(self, drone, step, command):
        if not self.owns(drone, step) or drone.pose is None:
            return False
        if self.phase == 'OBSERVE':
            self.set_gate(drone)
            self.phase = 'RETURN'
            self.started_step = step
            self.route = list(reversed(self.trail))
            drone.route = []
            drone.search_task = None
            if drone.messenger.state != 'DONE':
                drone.messenger.state = 'DONE'
                drone.messenger.audit.append((step, 'return_phase_handoff'))
            self.audit.append((step, 'return_started', self.anchor, len(self.route)))
        if self.phase == 'DELIVERED':
            self.brake(drone, command, self.hold)
            return True
        if self.anchor is None:
            if int(drone.identifier) == 0 or step-self.started_step >= self.STATE_AGE:
                self.phase = 'RELEASED'
                self.audit.append((step, 'no_shared_split_marker'))
                return False
            self.brake(drone, command)
            return True
        if self.gate is None:
            self.phase = 'RELEASED'
            self.audit.append((step, 'no_recorded_return_gate'))
            return False
        if int(drone.identifier) == 0 and (self.phase == 'HOLD'
                or math.dist(drone.pose, self.anchor[1:]) <= self.REACHED):
            if self.phase != 'HOLD':
                self.phase = 'HOLD'
                self.audit.append((step, 'hub_ready', self.anchor))
            if self.floor is not None:
                self.receipts[0] = max(self.receipts.get(0, -1), self.floor)
            if len(self.receipts) == drone.team_size and self.complete_step is None:
                self.complete_step = step
                self.audit.append((step, 'all_maps_received'))
            self.brake(drone, command, self.anchor[1:])
            return True
        while self.route and math.dist(drone.pose, self.route[0]) <= self.REACHED:
            self.route.pop(0)
        if not self.route:
            # The local branch gate is in the radio area. Do not crowd the hub.
            target = self.anchor[1:] if int(drone.identifier) == 0 else self.gate
        else:
            target = self.route[0]
        goal = target
        while self.detour and math.dist(drone.pose, self.detour[0]) <= self.REACHED:
            self.detour.pop(0)
        if self.detour:
            target = self.detour[0]
        if not self.known_segment(drone, drone.pose, target):
            if step >= self.next_plan:
                self.next_plan = step+20
                path = list(drone.grid.route(drone.pose, goal))
                self.detour = [p for p in path if math.dist(drone.pose, p) > self.REACHED]
            if not self.detour or not self.known_segment(drone, drone.pose, self.detour[0]):
                self.brake(drone, command)
                return True
            target = self.detour[0]
        self.brake(drone, command, target)
        return True

    def can_submit(self, drone, step):
        return (self.at_hub(drone) and self.owns(drone, step)
                and len(self.receipts) == drone.team_size and self.complete_step is not None
                and step-self.complete_step >= self.ACK_FLUSH)

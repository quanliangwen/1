"""One solo closeout when live radio has gone quiet and a loaded aircraft is stuck."""
from collections import deque
import math


class IsolatedCloseout:
    RADIO_QUIET_STEPS = 120
    STILL_STEPS = 96
    MAX_DISPLACEMENT = 12.

    def __init__(self):
        self.last_real_contact = 0
        self.positions = deque(maxlen=13)
        self.started = False

    def ready(self, drone, step, estimate):
        if (self.started or not drone.previous_inventory or not drone.search_roaming.departed
                or step < .30*drone.limit or step-self.last_real_contact < self.RADIO_QUIET_STEPS):
            return None
        point=tuple(map(float,drone.pose))
        samples=self.positions
        stalled=(len(samples)==samples.maxlen and samples[-1][0]-samples[0][0]>=self.STILL_STEPS
                 and drone.last_confirmed_drop_step is not None
                 and step-drone.last_confirmed_drop_step>=self.STILL_STEPS
                 and max(math.dist(p,point) for _,p in samples)<=self.MAX_DISPLACEMENT)
        if stalled:
            return "post_drop_stall"
        if estimate is not None and estimate[1] and 0<=step-estimate[0]<=100:
            return "local_low_gain"
        return None

    def track(self, drone, step):
        if not self.started and drone.previous_inventory and step%8==int(drone.identifier)%8:
            self.positions.append((step,tuple(map(float,drone.pose))))

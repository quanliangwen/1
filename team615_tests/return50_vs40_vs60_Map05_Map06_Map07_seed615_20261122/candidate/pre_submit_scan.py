"""Bounded continuation of existing searches and a refresh upon radio contact."""


class PreSubmitScan:
    STEPS = 180
    MIN_WALLTIME_LEFT = 12.

    def __init__(self):
        self.refresh_step = -1
        self.refreshed = []
        self.wait_started = None
        self.audit = []

    @staticmethod
    def start(drone):
        return drone.limit * 3 // 5

    def finish(self, drone):
        return min(self.start(drone) + self.STEPS, drone.limit-30)

    def waiting(self, drone, step):
        return (self.start(drone) <= step < self.finish(drone)
                and drone.walltime_limit-drone.elapsed_walltime >= self.MIN_WALLTIME_LEFT)

    def on_message(self, step):
        self.refresh_step = step

    def refresh_due(self, drone, step):
        if (not self.waiting(drone,step) or drone.previous_inventory != 0
                or drone.communicator_is_disabled() or step-self.refresh_step > 2
                or self.refresh_step < self.start(drone)):
            return False
        packet = drone.red_packet
        return packet is None or step-packet[0] >= 12

    def record_wait(self, drone, step):
        if self.wait_started is None:
            self.wait_started = step
            self.audit.append((step,"begin",int(drone.map_quality or 0)))

    def record_finish(self, drone, step):
        if self.wait_started is not None and len(self.audit)==1:
            self.audit.append((step,"submit_window",int(drone.map_quality or 0)))

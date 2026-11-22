"""Last-window election and emergency submission budget."""
from dataclasses import dataclass


@dataclass
class DeadlineSubmission:
    WINDOW = 30
    BID_STEPS = 3
    SCORE_SLOTS = 22
    SCORE_MAX = 10000
    FALLBACK_STEPS = 4
    MIN_WALL_MARGIN = 1.5
    WALL_OVERHEAD = 0.5
    BACKUP_INTERVAL = 360
    image: object = None
    score: int | None = None
    cache: tuple | None = None
    backup_image: object = None
    backup_step: int = -1
    observed_step: int | None = None
    observed_walltime: float | None = None
    recent_step_seconds: float = 0.0

    def fallback_reason(self, step, limit, elapsed_walltime, walltime_limit):
        if self.observed_step is not None and step > self.observed_step:
            seconds = (elapsed_walltime - self.observed_walltime) / (step - self.observed_step)
            self.recent_step_seconds = 0.8 * self.recent_step_seconds + 0.2 * max(0.0, seconds)
        self.observed_step = step
        self.observed_walltime = elapsed_walltime

        seconds_per_step = max(self.recent_step_seconds, elapsed_walltime / max(1, step))
        wall_margin = max(self.MIN_WALL_MARGIN, self.WALL_OVERHEAD + self.FALLBACK_STEPS * seconds_per_step)
        if walltime_limit - elapsed_walltime <= wall_margin:
            return "walltime"
        if limit - step <= self.FALLBACK_STEPS:
            return "timestep"
        return None

    def backup_due(self, step):
        return self.backup_image is None or step - self.backup_step >= self.BACKUP_INTERVAL

    def remember(self, step, image):
        self.backup_step = step
        self.backup_image = image

    @classmethod
    def window_start(cls, limit):
        return limit-cls.WINDOW+1

    @classmethod
    def slot(cls, limit, score):
        delay = ((cls.SCORE_MAX-score)*(cls.SCORE_SLOTS-1))//cls.SCORE_MAX
        return cls.window_start(limit)+cls.BID_STEPS+delay

    @classmethod
    def peer_ranks(cls, step, limit, bids):
        start = cls.window_start(limit)
        return [(score,-peer) for peer,(stamp,score,eligible) in bids.items()
                if eligible and start <= stamp <= step]

    @classmethod
    def submit_due(cls, step, limit, own, bids):
        if step < cls.slot(limit,own[0]):
            return False
        higher = [rank for rank in bids if rank > own]
        if not higher:
            return True
        # Give the elected candidate time to submit. If it never does, use
        # the final few frames instead of losing the whole team's map.
        return step >= limit-cls.FALLBACK_STEPS

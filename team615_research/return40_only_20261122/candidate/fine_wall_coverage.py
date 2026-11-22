"""Fine-cell wall gain under an exact candidate blast and known prior blasts."""
import math

import numpy as np

from swarm_rescue.solutions.local_wall_alignment import cell_weights


class FineWallCoverage:
    CACHE_STEPS = 16

    def __init__(self, memory, owner, team_size):
        self.owner = owner
        self.team_size = team_size
        self.local_hits = np.zeros(memory.hits.size, dtype=np.uint8)
        self.sources = np.zeros(memory.hit_shape, dtype=np.uint8)
        self._alignment_cache = {}
        self._alignment_epoch = None

    def observe(self, observation, fixed):
        if not fixed:
            return
        indices, counts = observation
        values = np.minimum(3, self.local_hits[indices].astype(np.int16) + counts)
        self.local_hits[indices] = values
        self.sources.ravel()[indices[values >= 3]] |= 1 << self.owner

    def packet(self):
        return np.flatnonzero(self.local_hits >= 3).astype(np.int32)

    def merge_direct(self, sender, ids):
        if (type(sender) is not int or sender == self.owner or not 0 <= sender < self.team_size
                or not isinstance(ids, np.ndarray) or ids.ndim != 1 or ids.dtype != np.int32):
            return
        if ids.size and (ids.min() < 0 or ids.max() >= self.sources.size):
            return
        self.sources.ravel()[ids] |= 1 << sender

    def measure(self, memory, point, bombs, radius, *, step=None):
        if step is None:
            cache = {}
        else:
            epoch = int(step) // self.CACHE_STEPS
            if epoch != self._alignment_epoch:
                self._alignment_cache.clear()
                self._alignment_epoch = epoch
            cache = self._alignment_cache
        x, y = point
        fine = memory.FINE
        half = fine / 2.
        # Include 2 cells of padding so support near the query edge is visible.
        c0 = max(0, math.floor((x + memory.width/2 - radius) / fine) - 2)
        r0 = max(0, math.floor((memory.height/2 - y - radius) / fine) - 2)
        c1 = min(memory.hit_shape[1], math.ceil((x + memory.width/2 + radius) / fine) + 2)
        r1 = min(memory.hit_shape[0], math.ceil((memory.height/2 - y + radius) / fine) + 2)
        rr, cc = np.nonzero(memory.hits[r0:r1, c0:c1] >= 3)
        xx = (cc + c0 + .5) * fine - memory.width/2
        yy = memory.height/2 - (rr + r0 + .5) * fine

        # The furthest corner must fit. A cell touching an already-covered
        # disk is conservatively removed using its nearest point to that bomb.
        supported = (np.abs(xx-x)+half)**2 + (np.abs(yy-y)+half)**2 <= radius**2
        for bx, by in bombs:
            near_sq = np.maximum(0., np.abs(xx-bx)-half)**2 + np.maximum(0., np.abs(yy-by)-half)**2
            supported &= near_sq > radius**2
        rr, cc = rr[supported], cc[supported]
        if not rr.size:
            return 0., 0., [0, 0, 0]

        weights = cell_weights(self.sources, self.team_size, rr+r0, cc+c0, cache)
        band = np.where(weights>=1.,2,np.where(weights>=.70,1,0))

        # Maintain score units and the existing per-16px-cell evidence cap,
        # after applying the fine-cell blast mask.
        cells_per_edge = memory.CELL // fine
        rc = (rr + r0) // cells_per_edge
        cc = (cc + c0) // cells_per_edge
        stride = int(cc.max())-int(cc.min())+1
        groups = (rc-rc.min()) * stride + cc-cc.min()
        rim = np.ones((int(rc.max()-rc.min())+1, stride))
        rim[np.unique(rc[(rc==0) | (rc==memory.shape[0]-1)])-rc.min(), :] = .5
        rim[:, np.unique(cc[(cc==0) | (cc==memory.shape[1]-1)])-cc.min()] = .5

        def total(histogram):
            scale = rim.ravel()[:len(histogram)]
            return float(np.dot(np.minimum(histogram / cells_per_edge**2, .20), scale))

        return total(np.bincount(groups, weights)), total(np.bincount(groups)), np.bincount(band, minlength=3).tolist()

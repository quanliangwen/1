"""V14 measured wall backbone and independent-incidence submission patches."""
import cv2
import numpy as np

from swarm_rescue.solutions.bearing_core import corroborated_map, independent_incidence, hit_direction_bits
from swarm_rescue.solutions.line_regularization import render_with_observed_boundary
from swarm_rescue.solutions.submission_wall_fill import add_wall_gaps


class SubmissionBearings:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.bits = np.zeros(((height + 3)//4, (width + 3)//4), np.uint8)
        self.revision = None
        self.wire = None
        self.received = {}

    def observe(self, memory, position, heading, ranges, angles, semantic):
        excluded = memory.semantic_mask(ranges, angles, semantic)
        ids, bits = hit_direction_bits(position, heading, ranges, angles, excluded, self.width, self.height)
        self.bits.ravel()[ids] |= bits

    def packet(self, step, map_revision):
        if map_revision is None:
            return None
        if self.revision != map_revision:
            ids = np.flatnonzero(self.bits.ravel()).astype(np.int32)
            self.wire = map_revision, ids, self.bits.ravel()[ids].copy()
            self.revision = map_revision
        return self.wire

    def receive(self, sender, packet):
        if not isinstance(packet, tuple) or len(packet) != 3:
            return
        step, ids, values = packet
        if (type(step) is not int or step <= self.received.get(sender, -1)
                or not isinstance(ids, np.ndarray) or not isinstance(values, np.ndarray)
                or ids.ndim != 1 or values.shape != ids.shape or ids.dtype.kind not in "iu"
                or values.dtype != np.uint8 or ids.size > self.bits.size
                or (ids.size and (int(ids.min()) < 0 or int(ids.max()) >= self.bits.size))):
            return
        np.bitwise_or.at(self.bits.ravel(),ids,values)
        self.received[sender] = step

    def render(self, memory):
        parent = render_with_observed_boundary(memory, line_width=8, keep_raw=False,
                     fit_band=10, duplicate_distance=8, covariance_limit=30,
                     boundary_bin_evidence=1, boundary_hit_threshold=1)
        additions, _ = corroborated_map(parent,memory.hits,self.bits,self.width,self.height)
        independent = np.repeat(np.repeat(independent_incidence(self.bits),2,axis=0),2,axis=1)
        stable = (memory.hits>=3) & independent[:memory.hits.shape[0],:memory.hits.shape[1]]
        mask = np.repeat(np.repeat(stable.astype(np.uint8),2,axis=0),2,axis=1)
        mask = cv2.dilate(mask[:self.height,:self.width], np.ones((3,3),np.uint8))
        original = np.maximum(parent, additions & mask)
        return add_wall_gaps(original, memory.hits, self.bits)

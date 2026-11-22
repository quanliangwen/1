"""Absolute normal corrections from measured outer walls of the closed arena."""

from collections import deque
import math

import numpy as np

from swarm_rescue.solutions.scan_geometry import project


class BoundaryAnchor:
    def __init__(self, size):
        self.size = np.asarray(size, dtype=float)
        # The closed arena has a 6 px border. Use the interior face.
        self.faces = self.size / 2 - 6
        self.history = {(axis, sign): deque(maxlen=24) for axis in (0, 1) for sign in (-1, 1)}

    def correct(self, lines, position, heading, step):
        shift = np.zeros(2)
        if not len(lines):
            return shift, 0., 0
        world = project(lines, position, heading)
        span = np.linalg.norm(world[:, 1] - world[:, 0], axis=1)
        centre = world.mean(axis=1)
        trusted = []
        for (axis, sign), records in self.history.items():
            along = 1 - axis
            face = sign * self.faces[axis]
            drift = centre[:, axis] - face
            skew = np.ptp(world[:, :, axis], axis=1)
            possible = (span >= 60) & (abs(drift) <= 12) & (skew <= .105 * span)
            possible &= (abs(world[:, :, along]) <= self.size[along] / 2 + 6).all(axis=1)
            if not possible.any():
                continue
            i = int(np.argmax(np.where(possible, span, 0)))
            first, last = sorted(world[i, :, along])
            records.append((step, first, last, float(drift[i])))
            while records and step - records[0][0] > 115:
                records.popleft()
            if len({t for t, *_ in records}) < 3:
                continue
            extent = 0.
            end = -math.inf
            for start, stop in sorted((a, b) for _, a, b, _ in records):
                extent += max(0., stop - max(start, end))
                end = max(end, stop)
            offsets = np.asarray([error for _, _, _, error in records])
            if extent < .28 * self.size[along] or np.std(offsets) > 5 or abs(np.median(offsets)) > 9:
                continue
            edge = world[i, 1] - world[i, 0]
            error = (math.atan2(edge[1], edge[0]) + math.pi / 4) % (math.pi / 2) - math.pi / 4
            trusted.append((axis, face, i, error))
        if not trusted:
            return shift, 0., 0
        weight = [span[i] for _, _, i, _ in trusted]
        error = float(np.average([yaw for _, _, _, yaw in trusted], weights=weight))
        yaw = float(np.clip(-.6 * error, -math.radians(2), math.radians(2)))
        corrected = project(lines.mean(axis=1), position, heading + yaw)
        axes = {axis for axis, *_ in trusted}
        for axis in axes:
            offsets = [face - corrected[i, axis] for a, face, i, _ in trusted if a == axis]
            shift[axis] = np.clip(.6 * np.median(offsets), -5, 5)
        return shift, yaw, len(axes)

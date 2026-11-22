"""Line segments supported by contiguous laser returns."""

import math

import numpy as np


def scan_lines(ranges, angles, movable, limit):
    finite = np.isfinite(ranges) & (ranges > 5) & (ranges < limit)
    points = np.where(finite, ranges, 0)[:, None] * np.column_stack((np.cos(angles), np.sin(angles)))
    for point in movable:
        finite &= np.sum((points - point) ** 2, axis=1) > 25 ** 2
    rays = np.flatnonzero(finite)
    if rays.size < 5:
        return np.empty((0, 2, 2))
    breaks = (np.diff(rays) != 1) | (np.linalg.norm(np.diff(points[rays], axis=0), axis=1) > 21)
    segments = []

    def fit(group):
        if len(group) < 5:
            return
        centre = group.mean(axis=0)
        x, y = (group - centre).T
        angle = .5 * math.atan2(2 * (x @ y), x @ x - y @ y)
        axis = np.array((math.cos(angle), math.sin(angle)))
        residual = abs(y * axis[0] - x * axis[1])
        split = int(np.argmax(residual))
        if residual[split] > 6:
            fit(group[:split])
            fit(group[split + 1:])
            return
        along = (group - centre) @ axis
        low, high = along.min(), along.max()
        if high - low >= 22 and np.mean(residual ** 2) <= 3.1 ** 2:
            segments.append(centre + np.array([[low], [high]]) * axis)

    for group in np.split(points[rays], np.flatnonzero(breaks) + 1):
        fit(group)
    return np.asarray(segments).reshape(-1, 2, 2)


def project(lines, position, heading):
    c, s = math.cos(heading), math.sin(heading)
    return lines @ np.array(((c, s), (-s, c))) + position

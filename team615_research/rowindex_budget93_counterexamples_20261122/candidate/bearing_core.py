"""Finite public lidar-incidence set and measured-only corroborated support."""
import math

import cv2
import numpy as np


def hit_direction_bits(position, heading, distances, angles, excluded, width, height):
    """Sparse OR updates for actual wall-hit endpoints in 4 px cells."""
    p = np.asarray(position, float)
    d = np.asarray(distances, float)
    a = np.asarray(angles, float)
    e = np.asarray(excluded, bool)
    if (p.shape != (2,) or not np.isfinite(p).all() or not np.isfinite(float(heading))
            or d.ndim != 1 or d.shape != a.shape or d.shape != e.shape
            or width <= 0 or height <= 0):
        return np.empty(0, np.int32), np.empty(0, np.uint8)
    keep = np.isfinite(d) & np.isfinite(a) & (d > 8) & (d < 220) & ~e
    if not keep.any():
        return np.empty(0, np.int32), np.empty(0, np.uint8)
    theta = float(heading) + a[keep]
    xx = p[0] + d[keep] * np.cos(theta)
    yy = p[1] + d[keep] * np.sin(theta)
    cols = np.floor((xx + width / 2) / 4).astype(np.int32)
    rows = np.floor((height / 2 - yy) / 4).astype(np.int32)
    h, w = (height + 3) // 4, (width + 3) // 4
    valid = (rows >= 0) & (rows < h) & (cols >= 0) & (cols < w)
    ids = rows[valid] * w + cols[valid]
    sectors = np.floor(np.mod(theta[valid], 2 * math.pi) * (4 / math.pi)).astype(np.int32)
    bits = np.left_shift(np.uint8(1), sectors.astype(np.uint8)).astype(np.uint8)
    result = np.zeros(h * w, np.uint8)
    np.bitwise_or.at(result, ids, bits)
    nonzero = np.flatnonzero(result)
    return nonzero.astype(np.int32), result[nonzero]


def independent_incidence(bits):
    """Two populated 45 degree bins separated by at least one empty bin."""
    b = np.asarray(bits, np.uint8)
    result = np.zeros(b.shape, bool)
    for first in range(8):
        for second in range(first + 1, 8):
            if min(second - first, 8 - (second - first)) >= 2:
                result |= ((b & (1 << first)) != 0) & ((b & (1 << second)) != 0)
    return result


def fine_any_to_four(mask, shape):
    fine = np.asarray(mask, bool)
    if fine.ndim != 2 or fine.shape[0] > 2 * shape[0] or fine.shape[1] > 2 * shape[1]:
        return np.zeros(shape, bool)
    padded = np.zeros((2 * shape[0], 2 * shape[1]), bool)
    padded[:fine.shape[0], :fine.shape[1]] = fine
    return padded.reshape(shape[0], 2, shape[1], 2).any(axis=(1, 3))


def corroborated_map(parent_image, hits, direction_bits, width, height, nonwall=None):
    """Union only short patches centered on measured, independent-angle hits."""
    parent = np.asarray(parent_image, np.uint8)
    hit = np.asarray(hits, np.uint8)
    bearing = np.asarray(direction_bits, np.uint8)
    shape = ((height + 3) // 4, (width + 3) // 4)
    if (parent.shape != (height, width) or hit.shape != ((height + 1) // 2, (width + 1) // 2)
            or bearing.shape != shape):
        return parent.copy(), {'qualified_cells': 0, 'added_pixels': 0, 'valid': False}
    measured = fine_any_to_four(hit > 0, shape)
    supported = independent_incidence(bearing) & measured
    if nonwall is not None:
        supported &= ~fine_any_to_four(nonwall, shape)
    patch = np.repeat(np.repeat(supported.astype(np.uint8), 4, axis=0), 4, axis=1)
    patch = patch[:height, :width]
    patch = cv2.dilate(patch, np.ones((3, 3), np.uint8))
    # The original public frame/opening prior remains authoritative.
    band = 32
    patch[:band, :] &= parent[:band, :]
    patch[-band:, :] &= parent[-band:, :]
    patch[:, :band] &= parent[:, :band]
    patch[:, -band:] &= parent[:, -band:]
    out = np.maximum(parent, patch)
    return out, {'qualified_cells': int(supported.sum()),
                 'added_pixels': int(np.count_nonzero((out > 0) & (parent == 0))), 'valid': True}


def add_corrobated_wall_value(values, image, parent, cell, width, height):
    """Same observed added surface enters the inherited coarse layout value."""
    result = np.asarray(values, np.float32).copy()
    shape = ((height + cell - 1) // cell, (width + cell - 1) // cell)
    if result.shape != shape or np.asarray(image).shape != (height, width) or np.asarray(parent).shape != (height, width):
        return result
    delta = cv2.resize(np.asarray(image, np.float32) - np.asarray(parent, np.float32),
                       (shape[1], shape[0]), interpolation=cv2.INTER_AREA)
    rr, cc = np.indices(shape)
    xx = (cc + .5) * cell - width / 2
    yy = height / 2 - (rr + .5) * cell
    frame = (np.abs(xx) > width / 2 - cell) | (np.abs(yy) > height / 2 - cell)
    delta[frame] *= .5
    return np.clip(result + delta, 0., 1.)

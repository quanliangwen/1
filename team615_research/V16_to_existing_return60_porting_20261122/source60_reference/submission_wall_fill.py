"""Add measured gaps to a frozen submission bitmap."""
import math

import cv2
import numpy as np

from swarm_rescue.solutions.line_regularization import PlanningWallFit, regularized_walls


_BIN_SIZE = 4  # 8 px at the submission evidence resolution
_MIN_BINS = 4
_INCIDENCE_DIRECTIONS = np.column_stack((
    np.cos((np.arange(8) + .5) * math.pi / 4),
    -np.sin((np.arange(8) + .5) * math.pi / 4),
))


def _distance_to(mask):
    return cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)


def _supported_spans(first, last, points, incidence, gap):
    """Project consecutive repeated hits with a common incidence sector."""
    start = np.asarray(first, dtype=float)
    vector = np.subtract(last, start)
    length = np.linalg.norm(vector)
    bin_count = int(length / _BIN_SIZE)
    if bin_count < _MIN_BINS:
        return
    tangent = vector / length
    normal = np.array((-tangent[1], tangent[0]))
    lower = np.minimum(first, last) - 2
    upper = np.maximum(first, last) + 2
    nearby = np.all((points >= lower) & (points <= upper), axis=1)
    offsets = points[nearby] - start
    distance = offsets @ tangent
    in_band = (distance >= 0) & (distance < bin_count * _BIN_SIZE) & (np.abs(offsets @ normal) <= 2)
    distance = distance[in_band]
    if not distance.size:
        return
    bearings = incidence[nearby][in_band]
    bins = (distance / _BIN_SIZE).astype(np.intp)
    centers = np.rint(start + (np.arange(bin_count)[:, None] + .5) * _BIN_SIZE * tangent).astype(np.intp)
    x, y = centers.T
    inside = (x >= 0) & (y >= 0) & (x < gap.shape[1]) & (y < gap.shape[0])
    missing = np.zeros(bin_count, dtype=bool)
    missing[inside] = gap[y[inside], x[inside]]
    # The same non-grazing incidence sector must support each bin of the span.
    # Its points must already be repeated hits in the 2 px evidence grid.
    for sector in np.flatnonzero(np.abs(_INCIDENCE_DIRECTIONS @ normal) >= .5):
        valid = (bearings & (1 << sector)) != 0
        votes = np.bincount(bins[valid], minlength=bin_count)
        continuous = (votes >= 2) & missing
        edges = np.flatnonzero(np.diff(np.r_[False, continuous, False]))
        for lo, hi in edges.reshape(-1, 2):
            if hi - lo < _MIN_BINS:
                continue
            measured = distance[valid & (bins >= lo) & (bins < hi)]
            yield (tuple(np.rint(start + measured.min() * tangent).astype(int)),
                   tuple(np.rint(start + measured.max() * tangent).astype(int)))


def add_wall_gaps(original, hits, direction_bits):
    """Return the original ink plus corroborated lines in observed empty spans."""
    height, width = original.shape
    occupied = np.pad(original != 0, ((0, height % 2), (0, width % 2)))
    occupied = occupied.reshape(hits.shape[0], 2, hits.shape[1], 2).any(axis=(1, 3))
    gap = _distance_to(occupied) > 3  # require a 6 px gap from the original ink
    repeated = hits >= 2
    seed = repeated & gap
    # Keep the existing public frame treatment authoritative.
    border = 16  # 32 px in the rendered image
    seed[:border, :] = seed[-border:, :] = False
    seed[:, :border] = seed[:, -border:] = False
    if not seed.any():
        return original
    # Keep adjoining local context for Hough and fit using the original hits.
    halo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    region = cv2.dilate(seed.astype(np.uint8), halo) != 0
    response = cv2.GaussianBlur(hits.astype(np.float32), (0, 0), 1.2)
    proposals = (region & (response >= .40)).astype(np.uint8)
    fit = PlanningWallFit()
    regularized_walls(hits, fine=2, line_width=8, keep_raw=False,
                      fit_band=10, duplicate_distance=8, covariance_limit=30,
                      proposal_mask=proposals, _planning_fit=fit)
    if not fit.segments:
        return original
    rows, cols = np.nonzero(repeated & region)
    points = np.column_stack((cols, rows))
    incidence = direction_bits[rows // 2, cols // 2]
    supplement = np.zeros_like(hits)
    for first, last in fit.segments:
        for start, end in _supported_spans(first, last, points, incidence, gap):
            cv2.line(supplement, start, end, 1, 4)
    if not supplement.any():
        return original
    supplement[~gap | (_distance_to(repeated) > 3)] = 0
    pixels = np.repeat(np.repeat(supplement, 2, axis=0), 2, axis=1)[:height, :width]
    frame_width = 2 * border
    pixels[:frame_width, :] = pixels[-frame_width:, :] = 0
    pixels[:, :frame_width] = pixels[:, -frame_width:] = 0
    return np.maximum(original, pixels)


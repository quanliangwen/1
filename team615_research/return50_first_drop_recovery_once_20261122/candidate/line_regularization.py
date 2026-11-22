"""Render long wall hypotheses using only accumulated measured lidar hits.

This independent postprocessor never reads arena/map files or wall truth. Hough
voting proposes lines, weighted TLS recenters their observed support, and
longitudinal occupancy forbids filling long unobserved gaps.
"""
import math
from dataclasses import dataclass
import numpy as np
import cv2


@dataclass
class PlanningWallFit:
    signature: tuple | None = None
    input_bytes: bytes | None = None
    segments: tuple = ()
    hits: int = 0
    misses: int = 0


def planning_wall_bitmap(memory, line_width):
    """Use exact sensor bytes to share a width-independent fit on this drone."""
    owner = getattr(memory, '_memory', memory)
    cache = getattr(owner, '_planning_wall_fit', None)
    if cache is None:
        cache = PlanningWallFit()
        owner._planning_wall_fit = cache
    return regularized_walls(memory.hits, fine=memory.FINE, line_width=line_width,
                             keep_raw=False, fit_band=10, duplicate_distance=8,
                             covariance_limit=30, _planning_fit=cache)


def regularized_walls(hits, fine=2, line_width=10, keep_raw=True,
                      fit_band=6, duplicate_distance=2, covariance_limit=12,
                      snap_boundary_lines=False, *, _planning_fit=None, proposal_mask=None):
    hits = np.asarray(hits)
    thickness = max(1, int(math.ceil(line_width/fine)))
    if _planning_fit is not None:
        assert not keep_raw
        signature = (hits.shape, hits.dtype.str, fine, fit_band,
                     duplicate_distance, covariance_limit, snap_boundary_lines,
                     None if proposal_mask is None else proposal_mask.tobytes())
        current_bytes = hits.tobytes()
        if signature == _planning_fit.signature and current_bytes == _planning_fit.input_bytes:
            _planning_fit.hits += 1
            output = np.zeros(hits.shape, np.uint8)
            for first, last in _planning_fit.segments:
                cv2.line(output, first, last, 1, thickness)
            return output
        _planning_fit.misses += 1
        segments = []
    if proposal_mask is None or keep_raw:
        support = cv2.GaussianBlur(hits.astype(np.float32), (0, 0), 1.2)
    if proposal_mask is None:
        proposal_mask = (support >= .55).astype(np.uint8)
    proposals = cv2.HoughLinesP(proposal_mask, 1, math.pi/720,
                               threshold=25, minLineLength=25, maxLineGap=12)
    if keep_raw:
        output = cv2.dilate((support >= .7).astype(np.uint8), np.ones((3, 3), np.uint8))
    else:
        output = np.zeros(hits.shape, np.uint8)
    if proposals is None:
        if _planning_fit is not None:
            _planning_fit.signature = signature
            _planning_fit.input_bytes = current_bytes
            _planning_fit.segments = ()
        return output
    rows, cols = np.nonzero(hits >= 2)
    points = np.column_stack((cols, rows)).astype(float)
    # nonzero() is row-major: each image row occupies a contiguous point range.
    row_offsets = np.empty(hits.shape[0] + 1, dtype=np.intp)
    row_offsets[0] = 0
    np.cumsum(np.bincount(rows, minlength=hits.shape[0]), out=row_offsets[1:])
    weights = np.sqrt(np.minimum(hits[rows, cols].astype(float), 12))
    accepted = []
    for x1, y1, x2, y2 in np.asarray(proposals).reshape(-1, 4):
        start, end = np.array([x1, y1], float), np.array([x2, y2], float)
        tangent = end-start
        length = np.linalg.norm(tangent)
        tangent /= length
        normal = np.array([-tangent[1], tangent[0]])
        # A superset of the oriented fitting rectangle. Preserve the original
        # point order and exact dot products for every possible support point.
        # The extra pixel absorbs floating arithmetic at the coarse bound.
        margin=float(fit_band)+9.
        lower_y, upper_y = min(y1,y2)-margin, max(y1,y2)+margin
        if math.isfinite(lower_y) and math.isfinite(upper_y):
            first_row = min(hits.shape[0], max(0, math.floor(lower_y)))
            last_row = min(hits.shape[0], max(0, math.ceil(upper_y) + 1))
            row_start, row_stop = row_offsets[first_row], row_offsets[last_row]
        else:
            # Preserve the original comparison semantics for nonfinite options.
            row_start, row_stop = 0, len(points)
        local_points = points[row_start:row_stop]
        subset=row_start+np.flatnonzero((local_points[:,0]>=min(x1,x2)-margin) &
            (local_points[:,0]<=max(x1,x2)+margin) &
            (local_points[:,1]>=min(y1,y2)-margin) &
            (local_points[:,1]<=max(y1,y2)+margin))
        delta = points[subset]-start
        along, across = delta @ tangent, delta @ normal
        ids = subset[np.flatnonzero((np.abs(across) < fit_band) & (along > -8) & (along < length+8))]
        if len(ids) < 25:
            continue
        p, w = points[ids], weights[ids]
        center = np.average(p, axis=0, weights=w)
        cov = ((p-center)*w[:, None]).T @ (p-center)/w.sum()
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        tangent = eigenvectors[:, 1]
        normal = eigenvectors[:, 0]
        if eigenvalues[0] > covariance_limit or eigenvalues[1] < 15*eigenvalues[0]:
            continue
        distance = (p-center) @ tangent
        low, high = np.percentile(distance, [1, 99])
        length = high-low
        if length < 25:
            continue
        first, last = center+tangent*low, center+tangent*high
        # A wall must have evidence in >= 70% of 8 px longitudinal bins.
        bins = np.clip(((distance-low)/4).astype(int), 0, max(1, int(length/4)))
        histogram = np.bincount(bins, minlength=max(2, int(length/4)+1))
        present = histogram > 0
        if present.mean() < .70:
            continue
        if any(abs(normal @ (center-oldcenter)) < duplicate_distance and
               abs(tangent @ oldtangent) > .999 and
               np.linalg.norm(center-oldcenter) < .4*(length+oldlength)
               for oldcenter, oldtangent, oldlength in accepted):
            continue
        accepted.append((center, tangent, length))
        if snap_boundary_lines:
            # A long fitted physical surface parallel and very close to a
            # public arena limit is a boundary hypothesis. Recentering only
            # that observed segment avoids retaining its noisy parallel cloud.
            # No extrapolation beyond first/last measured support is performed.
            margin = 16/fine
            near_horizontal = abs(tangent[1]) < math.sin(math.radians(2))
            near_vertical = abs(tangent[0]) < math.sin(math.radians(2))
            if near_horizontal and max(first[1],last[1]) < margin:
                first[1]=last[1]=3/fine
            elif near_horizontal and min(first[1],last[1]) > hits.shape[0]-margin:
                first[1]=last[1]=hits.shape[0]-3/fine
            elif near_vertical and max(first[0],last[0]) < margin:
                first[0]=last[0]=3/fine
            elif near_vertical and min(first[0],last[0]) > hits.shape[1]-margin:
                first[0]=last[0]=hits.shape[1]-3/fine
        # Bridge at most the Hough 24 px gap, never extrapolate beyond evidence.
        first_pixel = tuple(np.round(first).astype(int))
        last_pixel = tuple(np.round(last).astype(int))
        cv2.line(output, first_pixel, last_pixel, 1, thickness)
        if _planning_fit is not None:
            segments.append((first_pixel, last_pixel))
    if _planning_fit is not None:
        _planning_fit.signature = signature
        _planning_fit.input_bytes = current_bytes
        _planning_fit.segments = tuple(segments)
    return output


def render_regularized(memory, line_width=10, keep_raw=True, **fit_options):
    mask = regularized_walls(memory.hits, memory.FINE, line_width, keep_raw, **fit_options)
    grid = np.repeat(np.repeat(mask, memory.FINE, axis=0), memory.FINE, axis=1)
    return grid[:memory.height, :memory.width].copy()


def render_with_observed_boundary(memory, boundary_width=7, gap_limit=40,
                                  line_width=14, keep_raw=True,
                                  boundary_hit_threshold=2, boundary_bin_evidence=2,
                                  boundary_min_span=48, boundary_bandwidth=16,
                                  **fit_options):
    """Arena bounds constrain only boundary spans with measured nearby evidence.

    Range returns close to the public arena limits identify the physical frame;
    no side is drawn in its entirety without evidence. One-dimensional closing
    joins only short gaps, and uncovered edge spans stay unknown.
    """
    grid = render_regularized(memory, line_width=line_width, keep_raw=keep_raw, **fit_options)
    radius = max(2, int(math.ceil(boundary_bandwidth/memory.FINE)))
    measured = memory.hits >= boundary_hit_threshold
    sides = [measured[:radius, :].sum(axis=0), measured[-radius:, :].sum(axis=0),
             measured[:, :radius].sum(axis=1), measured[:, -radius:].sum(axis=1)]
    for side, evidence in enumerate(sides):
        flag = (evidence >= boundary_bin_evidence).astype(np.uint8)
        kernel = np.ones((1, max(1, int(gap_limit/memory.FINE))), np.uint8)
        flag = cv2.morphologyEx(flag[None, :], cv2.MORPH_CLOSE, kernel)[0]
        count, labels, stats, _ = cv2.connectedComponentsWithStats(flag[None, :])
        for component in range(1, count):
            lo, length = int(stats[component, cv2.CC_STAT_LEFT]), int(stats[component, cv2.CC_STAT_WIDTH])
            if length*memory.FINE < boundary_min_span:
                continue
            lo, hi = lo*memory.FINE, min(len(evidence)*memory.FINE, (lo+length)*memory.FINE)
            if side == 0:
                grid[:boundary_width, lo:hi] = 1
            elif side == 1:
                grid[-boundary_width:, lo:hi] = 1
            elif side == 2:
                grid[lo:hi, :boundary_width] = 1
            else:
                grid[lo:hi, -boundary_width:] = 1
    return grid

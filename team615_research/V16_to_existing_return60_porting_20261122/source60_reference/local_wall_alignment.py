"""Locally align independent wall traces for coverage, leaving the map intact."""
import math

import cv2
import numpy as np


TILE = 16  # 32 px at the current 2 px grid resolution.
PAD = 5
BAND = 1.5  # Three physical pixels either side of a fitted wall.
MAX_SHIFT = 4.
ANGLE_DOT = math.cos(math.radians(18.))
KERNEL = np.ones((5, 5), dtype=np.uint8)
BIT_COUNT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def fit_line(points):
    if len(points) < 5:
        return None
    delta = points - points.mean(axis=0)
    var_y, cov, var_x = (delta[:, 0] @ delta[:, 0],
                         delta[:, 0] @ delta[:, 1], delta[:, 1] @ delta[:, 1])
    angle = .5 * math.atan2(2 * cov, var_y - var_x)
    tangent = np.array((math.cos(angle), math.sin(angle)))
    normal = np.array((-tangent[1], tangent[0]))
    narrow, long = delta @ normal, delta @ tangent
    if long @ long < 3 * max(narrow @ narrow, 1.) or np.ptp(long) < 5:
        return None
    projection = points @ normal
    inliers = points[np.abs(projection - np.median(projection)) <= BAND]
    if len(inliers) < 5 or np.ptp(inliers @ tangent) < 5:
        return None
    return normal, tangent, inliers


def aligned_tile(sources, team_size, tile_row, tile_col):
    start_y, start_x = TILE * tile_row, TILE * tile_col
    end_y = min(sources.shape[0], start_y + TILE)
    end_x = min(sources.shape[1], start_x + TILE)
    y0, x0 = max(0, start_y-PAD), max(0, start_x-PAD)
    patch = sources[y0:end_y+PAD, x0:end_x+PAD]
    ys, xs = slice(start_y-y0,end_y-y0), slice(start_x-x0,end_x-x0)
    raw = BIT_COUNT[patch[ys, xs]]
    nearby = cv2.dilate((patch != 0).astype(np.uint8), KERNEL)[ys, xs]
    # Adjacent cells alone cannot earn the high-confidence rate.
    weights = np.where(raw >= 2, 1., np.where(raw == 1, .70, np.where(nearby, .18, .15)))
    fitted = {}
    for owner in range(team_size):
        line = fit_line(np.argwhere(patch & (1 << owner)))
        if line is not None:
            fitted[owner] = line

    band = np.zeros(weights.shape, dtype=bool)
    aligned = np.zeros(patch.shape, dtype=np.uint8)
    grid = np.moveaxis(np.indices(patch.shape), 0, -1)[ys, xs]
    used = set()
    for seed, (normal, tangent, points) in fitted.items():
        if seed in used:
            continue
        offset = float(np.median(points @ normal))
        axis = points @ tangent
        peers = []
        for owner, (other_normal, _, other_points) in fitted.items():
            if owner in used or abs(other_normal @ normal) < ANGLE_DOT:
                continue
            other_axis = other_points @ tangent
            if min(axis.max(),other_axis.max()) - max(axis.min(),other_axis.min()) < 3:
                continue
            other_offset = float(np.median(other_points @ normal))
            if abs(other_offset-offset) <= MAX_SHIFT:
                peers.append((owner, other_points, other_offset))
        if len(peers) < 2:
            continue
        common = float(np.median([value for _,_,value in peers]))
        low = min(float((p @ tangent).min()) for _,p,_ in peers)
        high = max(float((p @ tangent).max()) for _,p,_ in peers)
        grid_axis = grid @ tangent
        band |= ((np.abs(grid @ normal-common) <= BAND) &
                 (grid_axis >= low-1) & (grid_axis <= high+1))
        for owner, coords, old in peers:
            if abs(common-old) > MAX_SHIFT:
                continue
            shifted = np.rint(coords+(common-old)*normal).astype(np.int32)
            rr, cc = shifted.T
            ok = (rr>=0) & (cc>=0) & (rr<patch.shape[0]) & (cc<patch.shape[1])
            aligned[rr[ok],cc[ok]] |= 1 << owner
        used.update(owner for owner, _, _ in peers)

    if used:
        direct = BIT_COUNT[aligned[ys,xs]]
        local = cv2.dilate((aligned!=0).astype(np.uint8),KERNEL)[ys,xs]
        line_weights = np.where(direct>=2, 1., np.where(direct==1,.70,np.where(local,.20,.15)))
        # Direct evidence can still justify a small contribution at a corner
        # or a separate wall. Neighbor-only scatter outside the band is removed.
        off_line = np.where(raw>=2, .40, np.where(raw==1, .20, 0.))
        weights = np.where(band, line_weights, off_line)
    return weights


def cell_weights(sources, team_size, rows, cols, cache):
    pairs = np.column_stack((rows//TILE,cols//TILE))
    tiles, labels = np.unique(pairs, axis=0, return_inverse=True)
    weights = np.empty(len(rows))
    for label,(ty,tx) in enumerate(tiles):
        key = int(ty), int(tx)
        if key not in cache:
            cache[key] = aligned_tile(sources,team_size,*key)
        keep = labels==label
        weights[keep] = cache[key][rows[keep]%TILE,cols[keep]%TILE]
    return weights

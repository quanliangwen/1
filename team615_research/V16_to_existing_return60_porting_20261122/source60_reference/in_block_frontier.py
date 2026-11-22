"""Choose an observation point on the already selected blue route."""

import math

import cv2
import numpy as np


def safe_prefix_candidates(grid, pose, block, costs, baseline, parents):
    start, target = grid.cell(pose), grid.cell(baseline)
    route = []
    node = target
    while node != start:
        previous = parents.get(node)
        if previous is None:
            return
        route.append((previous, node))
        node = previous

    base_cost = costs[target]
    for previous, node in reversed(route):
        checked = (node, (node[0],previous[1]), (previous[0],node[1]))
        if any(cell != start and (grid.evidence[cell] >= 0 or grid.clearance[cell] < 23.)
               for cell in checked):
            break
        if node == target or node not in block:
            continue
        travel = costs[node]
        point = tuple(grid.point(node))
        if travel <= min(160., base_cost-20.) and 32. <= math.dist(pose,point) <= 160.:
            yield point, travel


def observation_point(memory, grid, pose, block, costs, baseline, depth):
    if memory is None or len(block) < 2 or grid.cell(baseline) not in costs:
        return baseline, None
    _, parents = grid.tree(pose)
    candidates = list(safe_prefix_candidates(grid,pose,block,costs,baseline,parents))
    if not candidates:
        return baseline, None

    unknown = ~memory.free & ~memory.blocked()
    info = cv2.boxFilter(unknown.astype(np.float32), -1, (13,13),
                         normalize=False, borderType=cv2.BORDER_CONSTANT)
    best = None
    for point,travel in candidates:
        index = memory.world_to_cell(point)
        gain = float(info[index]) - .25*float(memory.visits[index])
        score = gain/(1. + .04*travel/memory.CELL)
        if score > 0. and (best is None or (score,-travel,point) > best):
            best = score,-travel,point
    if best is None:
        return baseline, None
    score,negative_cost,point = best
    return point,dict(score=round(score,4),route_cost=round(-negative_cost,2),
                      baseline_cost=round(costs[grid.cell(baseline)],2),
                      block_cells=len(block),shift_px=round(math.dist(point,baseline),2),
                      prefix_candidates=len(candidates))

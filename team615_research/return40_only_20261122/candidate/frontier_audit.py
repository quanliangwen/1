"""Count every gate independently of the existing R288 target selection."""
import math

import cv2
import numpy as np


def audit_frontier(memory, grid, pose, block, costs, baseline):
    start, target = grid.cell(pose), grid.cell(baseline)
    audit = dict(block=len(block),route=0,intersection=0,distance=0,known=0,clearance=0,gain=0,
                 safe_intersection_costs=[], first_safe_in_block=None)
    if memory is None or len(block)<2 or target not in costs:
        return {**audit,"stop":"precondition"}
    _, parents = grid.tree(pose)
    edges = []
    node = target
    while node != start:
        previous = parents.get(node)
        if previous is None:
            return {**audit,"stop":"no_chain"}
        edges.append((previous,node))
        node = previous
    audit["route"] = len(edges)
    in_block = []
    known = clear = True
    for previous,node in reversed(edges):
        checked = {node,(node[0],previous[1]),(previous[0],node[1])} - {start}
        known &= all(grid.evidence[cell] < 0 for cell in checked)
        clear &= all(grid.clearance[cell] >= 23. for cell in checked)
        if node == target or node not in block:
            continue
        point, travel = tuple(grid.point(node)), float(costs[node])
        eligible = travel<=min(160.,costs[target]-20.) and 32.<=math.dist(pose,point)<=160.
        audit["intersection"] += 1
        audit["distance"] += int(eligible)
        audit["known"] += int(eligible and known)
        audit["clearance"] += int(eligible and known and clear)
        if known and clear:
            audit["safe_intersection_costs"].append(round(travel,2))
            if audit["first_safe_in_block"] is None:
                audit["first_safe_in_block"] = round(travel,2)
            if eligible:
                in_block.append(point)
    if in_block:
        unknown = ~memory.free & ~memory.blocked()
        info = cv2.boxFilter(unknown.astype(np.float32),-1,(13,13),normalize=False,borderType=cv2.BORDER_CONSTANT)
        for point in in_block:
            cell = memory.world_to_cell(point)
            audit["gain"] += int(float(info[cell]) - .25*float(memory.visits[cell]) > 0.)
    return audit

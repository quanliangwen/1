"""Choose a safe first leg after releasing a physically stalled aircraft."""
import math
import numpy as np


def approaches(point, start, route, radius=22., horizon=80.):
    """Check continuous segments, using only the first part of the route."""
    origin = np.asarray(point)
    a = np.asarray(start)
    for end in route:
        b = np.asarray(end)
        offset = b-a
        length = float(np.linalg.norm(offset))
        if length < 1e-6:
            continue
        u = offset/length
        limit = min(length,horizon)
        close = a+u*np.clip((origin-a) @ u,0.,limit)
        if math.dist(close,origin)<radius:
            return True
        horizon -= limit
        if horizon <= 0.:
            break
        a = b
    return False


def choose_exit(drone, escape, original):
    guard = escape.exit_guard
    if guard is None:
        return original
    step = int(drone.elapsed_timestep)
    point, until = guard
    if step>until or drone.mode not in ("explore","search"):
        escape.exit_guard = None
        return original
    if not drone.route:
        return original
    old = list(drone.route)
    if not approaches(point,drone.pose,[original,*old[1:]]):
        escape.exit_guard = None
        escape.exit_choices.append((step,"original_clear",point,tuple(original),old[:5]))
        return original

    # Bias only this replan. Standard walkability still applies and the
    # actual rejoin segment must also pass the live 23px corridor check.
    avoid = ((point,22.),)
    if drone.search_roaming.departed:
        avoid += ((drone.search_roaming.origin,drone.search_roaming.radius),)
    rays = drone.lidar_values()
    if rays is not None:
        ranges = np.asarray(rays,dtype=float)
        angles = np.asarray(drone.lidar_rays_angles())
        objects = [(h.distance*math.cos(h.angle),h.distance*math.sin(h.angle))
                   for h in (drone.semantic_values() or ()) if getattr(h.entity_type,"name","") in
                   ("DRONE","BOMB","DISPOSAL_CENTER")]
        rejoin = [(drone.goal, [])]
        rejoin.extend((old[index],old[index+1:]) for index in range(min(5,len(old))))
        for target, tail in rejoin:
            if target is None:
                continue
            alternative = list(drone.grid.route(drone.pose,target,avoid=avoid))
            if not alternative:
                continue
            while alternative and drone.reached_search_point(alternative[0]):
                alternative.pop(0)
            if not alternative:
                continue
            route = alternative+tail
            if approaches(point,drone.pose,route) or not drone.search_roaming.allows(drone.pose,route[-1],route):
                continue
            first = np.asarray(route[0])-drone.pose
            length = float(np.linalg.norm(first))
            if length<5.:
                continue
            cells = {drone.grid.cell(q) for a,b in zip([drone.pose,*alternative],alternative)
                     for q in np.linspace(a,b,math.ceil(math.dist(a,b)/5)+1)}
            cells.discard(drone.grid.cell(drone.pose))
            if not cells or any(drone.grid.evidence[c]>=0 or drone.grid.clearance[c]<23. for c in cells):
                continue
            direction = math.atan2(first[1],first[0])-drone.heading
            if not escape.clearance(direction,angles,ranges,length,objects):
                continue
            drone.route = route
            escape.shortcut_guard = point, tuple(route[0]), until
            escape.exit_guard = None
            escape.exit_choices.append((step,"alternate",point,tuple(original),old[:5],route[:5]))
            return route[0]
    escape.exit_guard = None
    escape.exit_choices.append((step,"fallback",point,tuple(original),old[:5]))
    return original



def active_shortcut_guard(drone, escape):
    guard = getattr(escape, "shortcut_guard", None)
    if guard is None:
        return None
    stall, first, until = guard
    step = int(drone.elapsed_timestep)
    if step > until:
        reason = "shortcut_expired"
    elif math.dist(drone.pose, first) <= 8.:
        reason = "first_leg_reached"
    else:
        return guard
    escape.shortcut_guard = None
    escape.exit_choices.append((step, reason, stall, first))
    return None


def shortcut_allowed(drone, escape, target):
    guard = active_shortcut_guard(drone, escape)
    if guard is None:
        return True
    stall, _, _ = guard
    length = math.dist(drone.pose, target)
    if not approaches(stall, drone.pose, [target], horizon=length):
        return True
    witness = (int(drone.elapsed_timestep), "shortcut_blocked", stall, tuple(target))
    if not escape.exit_choices or escape.exit_choices[-1] != witness:
        escape.exit_choices.append(witness)
    return False

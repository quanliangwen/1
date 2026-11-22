"""Local bomb density from confirmed placements and semantic returns."""

from itertools import combinations
import math

import numpy as np

# A circular patch 80 pixels across, with 5 pixels added for estimation error.
# This is independent of the official pairwise separation.
PATCH_RADIUS = 40.
OBSERVED_RADIUS = PATCH_RADIUS + 5.


def enclosing_radius(a,b,c):
    sides=sorted((math.dist(a,b),math.dist(a,c),math.dist(b,c)))
    x,y,z=sides
    if z*z >= x*x+y*y:
        return z/2.
    twice_area=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
    return x*y*z/(2.*twice_area)


def violates_patch(point, positions, radius=OBSERVED_RADIUS):
    nearby=[p for p in positions if math.dist(point,p)<=2.*radius]
    return any(enclosing_radius(point,a,b)<=radius for a,b in combinations(nearby,2))


def observed_bombs(drone, semantic):
    # Confirmed records use different keys for distinct physical bombs. Only
    # append a local surface estimate if it is not already represented.
    positions=[tuple(p) for key,p in drone.drop_records.items()
               if key not in drone.placement.unlocalized_drops or key[0]==drone.identifier]
    surfaces=[]
    for hit in semantic:
        if getattr(hit.entity_type,"name","")!="BOMB" or not 0. < hit.distance <= 130.:
            continue
        yaw=drone.heading+hit.angle
        center=tuple(drone.pose+(hit.distance+9.)*np.array((math.cos(yaw),math.sin(yaw))))
        surfaces.append((hit.distance,center))
    for _,point in sorted(surfaces):
        if not any(math.dist(point,old)<23. for old in positions):
            positions.append(point)
    return positions

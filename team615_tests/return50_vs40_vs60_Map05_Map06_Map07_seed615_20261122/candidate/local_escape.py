"""Bounded lidar-checked escape for a searcher with no physical progress."""
from collections import deque
import math

import numpy as np


class LocalEscape:
    WINDOW = 80
    LENGTH = 36.
    CLEARANCE = 23.

    def __init__(self):
        self.motion = deque(maxlen=self.WINDOW)
        self.position = np.zeros(2)
        self.heading = 0.
        self.tick = -1
        self.active = None
        self.next_attempt = 0
        self.failed = []
        self.stall_point = None
        self.exit_guard = None
        self.exit_choices = []
        self.audit = []

    def update_motion(self, step, odom):
        if self.tick != step-1:
            self.motion.clear()
            self.active = None
        self.tick = step
        if odom is None or not np.all(np.isfinite(odom)):
            self.motion.clear()
            self.active = None
            return False
        travel, relative, yaw = map(float,odom)
        angle = self.heading + relative
        self.position += max(0., travel)*np.array((math.cos(angle), math.sin(angle)))
        self.heading = (self.heading + yaw + math.pi) % (2*math.pi) - math.pi
        self.motion.append(self.position.copy())
        return True

    @classmethod
    def clearance(cls, direction, angles, ranges, length, moving):
        relative = angles-direction
        finite = np.isfinite(ranges) & (ranges>0.)
        cosine, sine = np.cos(relative), np.sin(relative)
        forecast = (cosine>0.) & (np.abs(relative % (2*math.pi) - math.pi)>math.pi-math.atan2(cls.CLEARANCE,length))
        if not forecast.any() or np.count_nonzero(finite & forecast) < .90*np.count_nonzero(forecast):
            return False
        forward = ranges[finite]*cosine[finite]
        side = np.abs(ranges[finite]*sine[finite])
        # Retain the live 23px tube. Returns initially within the hull
        # clearance may only stay beside or move away from the aircraft.
        if np.any((forward>0.) & (forward<length+cls.CLEARANCE) & (side<cls.CLEARANCE)):
            return False
        for obstacle in moving:
            x,y = obstacle
            fore=x*math.cos(direction)+y*math.sin(direction)
            across=abs(-x*math.sin(direction)+y*math.cos(direction))
            if 0.<fore<length+cls.CLEARANCE and across<cls.CLEARANCE:
                return False
        return True

    def finish(self, drone, step, reason):
        origin, angle, end = self.active
        distance = float(np.linalg.norm(self.position-origin))
        self.audit.append((step,reason,distance))
        self.active = None
        self.motion.clear()
        self.next_attempt = step+70
        if reason=="escape_reached":
            self.exit_guard = self.stall_point, step+80
            self.failed.clear()
            drone.route=[]
            drone.search_task=None
            drone.search_roaming.target=None
            drone.next_explore=step+1
            drone.recovery_until=step
            drone.progress_pose=tuple(drone.pose)
            drone.progress_step=step
        else:
            self.failed=(self.failed+[angle])[-3:]

    def apply(self, drone, command, step, ranges, semantic):
        if (drone.gap_probe is not None or drone.gap_exit is not None or drone.survey_run is not None
                or drone.carrying or drone.queue or drone.mode not in ("search","explore")
                or drone.placement.wall_approach is not None or drone.submitted
                or step>=drone.limit-20 or drone.walltime_limit-drone.elapsed_walltime<3.):
            self.motion.clear()
            self.active = None
            return
        if not command.get("place_bomb") and step-drone.last_attempt_step<3:
            self.motion.clear()
            self.active = None
            return
        if command.get("place_bomb"):
            self.motion.clear()
            self.active = None
            return
        odom=drone.odometer_values()
        if not self.update_motion(step,odom) or ranges is None or drone.pose is None:
            return
        if self.active is None:
            if step<self.next_attempt or len(self.motion)<self.WINDOW:
                return
            if max(np.linalg.norm(point-self.position) for point in self.motion)>8.:
                return
        ranges=np.asarray(ranges,dtype=float)
        angles=np.asarray(drone.lidar_rays_angles())
        objects=[(hit.distance*math.cos(hit.angle),hit.distance*math.sin(hit.angle))
                 for hit in semantic if getattr(hit.entity_type,"name","") in ("DRONE","BOMB","DISPOSAL_CENTER")]
        if self.active is None:
            self.next_attempt=step+24
            relative_heading=0.
            if drone.route:
                vector=np.asarray(drone.route[0])-drone.pose
                if np.linalg.norm(vector)>5.:
                    relative_heading=math.atan2(vector[1],vector[0])-drone.heading
            offsets=(0,1,-1,2,-2,3,-3,4,-4,5,-5,6,-6,7,-7,8)
            for offset in offsets:
                direction=relative_heading+offset*math.pi/8
                world=direction+drone.heading
                remembered=direction+self.heading
                end=tuple(drone.pose+self.LENGTH*np.array((math.cos(world),math.sin(world))))
                if any(math.cos(old-remembered)>.92 for old in self.failed):
                    continue
                if not drone.search_roaming.allows(drone.pose,end,[end]):
                    continue
                if not self.clearance(direction,angles,ranges,self.LENGTH,objects):
                    continue
                self.stall_point = tuple(map(float,drone.pose))
                self.active=(self.position.copy(),remembered,step+55)
                self.audit.append((step,"escape_start",bool(drone.grid.pose_fixed),float(direction)))
                break
            if self.active is None:
                self.failed.clear()
                return
        origin, angle, expiry=self.active
        direction=angle-self.heading
        progress=float((self.position-origin) @ np.array((math.cos(angle), math.sin(angle))))
        if progress>=self.LENGTH-5.:
            self.finish(drone,step,"escape_reached")
            return
        if step>=expiry or not self.clearance(direction,angles,ranges,max(8.,self.LENGTH-progress),objects):
            self.finish(drone,step,"escape_aborted")
            return
        travel, relative, yaw=map(float,odom)
        world=direction+drone.heading
        measured=drone.heading-yaw+relative
        desired=min(1.25,max(.65,(self.LENGTH-progress)/8.))
        command.update(drone.motion_command(
            desired*np.array((math.cos(world),math.sin(world))),
            travel*np.array((math.cos(measured),math.sin(measured))),0.,.2,False))


"""Leave a real first drop before asking for another at the same location."""
import math

import numpy as np


class DropDeparture:
    GOAL = 36.
    DURATION = 62

    def __init__(self):
        self.started = None
        self.last_tick = None
        self.origin = np.zeros(2)
        self.offset = np.zeros(2)
        self.yaw = 0.
        self.heading = None
        self.length = 0.
        self.planned_at = None
        self.controls_step = None
        self.audit = []

    @staticmethod
    def vector(angle):
        return np.array((math.cos(angle),math.sin(angle)))

    def update(self, drone, step, first_drop):
        self.controls_step=None
        if first_drop:
            self.started=self.last_tick=step
            self.origin=np.asarray(drone.pose).copy()
            self.offset[:]=0.
            self.yaw=0.
            self.heading=None
            self.planned_at=None
            self.audit.append((step,"departure_started",tuple(map(float,drone.pose))))
            return
        if self.started is None:
            return
        odom=drone.odometer_values()
        if (step!=self.last_tick+1 or odom is None or not np.all(np.isfinite(odom))
                or abs(float(odom[0]))>14.):
            self.audit.append((step,"departure_odom_lost"))
            self.started=None
            return
        travel,relative,yaw=map(float,odom)
        self.offset+=max(0.,travel)*self.vector(self.yaw+relative)
        self.yaw+=yaw
        self.last_tick=step
        dist=float(np.linalg.norm(self.offset))
        if dist>=self.GOAL or step-self.started>=self.DURATION or not drone.previous_inventory:
            reason="departure_clear" if dist>=self.GOAL else "departure_ended"
            self.audit.append((step,reason,dist))
            self.started=None

    def options(self, base, clear):
        radial=float(np.linalg.norm(self.offset))
        minimum=min(20.,max(10.,self.GOAL-radial))
        for length in (self.GOAL,27.,minimum):
            for turn in (0,1,-1,2,-2,3,-3,4,-4,5,-5,6,-6,7,-7,8):
                direction=base+turn*math.pi/8
                v=self.vector(direction+self.yaw)
                final=self.offset+length*v
                if np.linalg.norm(final)<max(radial+8.,minimum):
                    continue
                if radial>8. and (self.offset @ v)<-5.:
                    continue
                if clear(direction,length):
                    yield direction,length,final

    def choose(self, drone, step, base, clear):
        return next(self.options(base,clear),None)

    def steer(self, drone, command, step, ranges, semantic):
        if (self.started is None or ranges is None or not drone.previous_inventory
                or step>=drone.limit-20 or drone.walltime_limit-drone.elapsed_walltime<3.):
            return False
        odom=drone.odometer_values()
        if odom is None or not np.all(np.isfinite(odom)):
            return False
        angles=np.asarray(drone.lidar_rays_angles())
        ranges=np.asarray(ranges)
        objects=[(hit.distance*math.cos(hit.angle),hit.distance*math.sin(hit.angle))
                 for hit in semantic if hit.entity_type.name in ("DRONE","BOMB","DISPOSAL_CENTER")
                 and math.isfinite(hit.distance) and math.isfinite(hit.angle)]

        def clear(direction,length):
            return drone.local_escape.clearance(direction,angles,ranges,length,objects)

        radius=float(np.linalg.norm(self.offset))
        remaining=min(36.,max(8.,self.GOAL-radius))
        if (self.heading is None or step-self.planned_at>=18
                or not clear(self.heading-self.yaw,remaining)):
            base=0.
            if drone.route:
                dx,dy=np.subtract(drone.route[0],drone.pose)
                if math.hypot(dx,dy)>5.:
                    base=math.atan2(dy,dx)-drone.heading
            selected=self.choose(drone,step,base,clear)
            if selected is None:
                self.heading=None
                return False
            direction,length,_=selected
            self.heading=self.yaw+direction
            self.planned_at=step
            self.length=length
            self.audit.append((step,"departure_path",round(direction,4),length,radius))
        direction=self.heading-self.yaw
        length=min(remaining,self.length)
        if not clear(direction,length):
            self.heading=None
            return False
        travel,relative,change=map(float,odom)
        velocity=travel*self.vector(drone.heading-change+relative)
        world=drone.heading+direction
        desired=min(2.8,max(1.25,length/7.))*self.vector(world)
        turn=(direction+math.pi/2)%math.pi-math.pi/2
        command.update(drone.motion_command(desired,velocity,turn,.18,False,3.7))
        self.controls_step=step
        return True

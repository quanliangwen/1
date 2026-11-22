"""Leave a real first drop before asking for another at the same location."""
import math
from collections import deque

import numpy as np


class DropDeparture:
    GOAL = 36.
    DURATION = 62
    RECOVERY_SECONDS = 3.
    RECOVERY_STALL = 30
    RECOVERY_STALL_MOVE = 8.
    RECOVERY_WATCH = 20
    RECOVERY_MIN_PROGRESS = 3.
    OWN_RADIUS = 12.
    HIT_MARGIN = 6.

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
        self.recovery_failed = False
        self.recovery_used = False
        self.recovery_started = None
        self.recovery_wall_started = None
        self.recovery_goal = None
        self.recovery_trace = deque(maxlen=self.RECOVERY_STALL)
        self.recovery_watch = deque(maxlen=self.RECOVERY_WATCH)
        self.recovery_tick = None
        self.before_drop_scan = None
        self.first_point = None

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
            self.recovery_failed=True
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
            still_near=(self.first_point is not None and self._reliable(drone)
                        and np.linalg.norm(np.asarray(drone.pose)-self.first_point)<self.GOAL)
            self.recovery_failed=bool(drone.previous_inventory) and (dist<self.GOAL or still_near)

    @staticmethod
    def _reliable(drone):
        return (drone.pose is not None and np.shape(drone.pose)==(2,)
                and np.all(np.isfinite(drone.pose)) and math.isfinite(float(drone.heading))
                and drone.grid.pose_fixed and not drone._odometry_only)

    def observe_recovery(self, drone, step, ranges, semantic):
        """Retain one pre-drop scan and a continuous, reliably located stall trace."""
        if self.recovery_used:
            return
        if not self._reliable(drone):
            self.recovery_trace.clear()
            self.recovery_tick=None
            return
        key=(int(drone.identifier),1)
        point=drone.drop_records.get(key)
        if point is None:
            if (drone.initial_inventory==2 and drone.previous_inventory==2
                    and drone.pending_drop is None and ranges is not None):
                angles=np.asarray(drone.lidar_rays_angles(),dtype=float)
                values=np.asarray(ranges,dtype=float)
                if (angles.ndim==1 and values.shape==angles.shape and len(angles)>=16
                        and np.all(np.isfinite(angles))):
                    order=np.argsort((angles+drone.heading)%(2*math.pi))
                    self.before_drop_scan=(step,np.asarray(drone.pose).copy(),
                        ((angles+drone.heading)%(2*math.pi))[order],values[order].copy())
            return
        if self.first_point is None:
            request=drone.placement.request
            if (np.shape(point)!=(2,) or not np.all(np.isfinite(point))
                    or key in drone.placement.unlocalized_drops
                    or (request is not None and request[3]==2 and not request[2])):
                return
            self.first_point=np.asarray(point,dtype=float).copy()
            # A stale/displaced scan cannot certify the area around the release.
            scan=self.before_drop_scan
            if (scan is not None and (not 0<step-scan[0]<=2
                    or np.linalg.norm(scan[1]-self.first_point)>8.)):
                self.before_drop_scan=None
        if self.recovery_tick!=step-1:
            self.recovery_trace.clear()
        odom=drone.odometer_values()
        if odom is None or np.shape(odom)!=(3,) or not np.all(np.isfinite(odom)) or abs(float(odom[0]))>14.:
            self.recovery_trace.clear()
            self.recovery_tick=None
            return
        self.recovery_tick=step
        self.recovery_trace.append((step,np.asarray(drone.pose).copy()))

    def _own_surface(self, drone, angles):
        vector=self.first_point-np.asarray(drone.pose)
        along=vector @ np.array((np.cos(angles+drone.heading),np.sin(angles+drone.heading)))
        across2=float(vector @ vector)-along*along
        root=np.sqrt(np.maximum(0.,self.OWN_RADIUS**2-across2))
        near,far=along-root,along+root
        surface=np.where(near>1.e-6,near,far)
        return np.where((across2<=self.OWN_RADIUS**2)&(surface>1.e-6),surface,np.nan)

    def _own_hit(self, drone, angle, distance):
        if not math.isfinite(float(distance)) or distance<=0. or not math.isfinite(float(angle)):
            return False
        predicted=self._own_surface(drone,np.array([angle]))[0]
        if not math.isfinite(predicted) or abs(distance-predicted)>self.HIT_MARGIN:
            return False
        point=np.asarray(drone.pose)+distance*self.vector(angle+drone.heading)
        if abs(float(np.linalg.norm(point-self.first_point))-self.OWN_RADIUS)>3.:
            return False
        # Do not identify a return shared with another known bomb as our own.
        return not any(key!=(int(drone.identifier),1)
            and np.linalg.norm(point-np.asarray(other))<=self.OWN_RADIUS+self.HIT_MARGIN
            for key,other in drone.drop_records.items())

    def _recovery_obstacles(self, drone, angles, ranges, semantic):
        own_angles=[];objects=[]
        for hit in semantic:
            kind=getattr(hit.entity_type,'name','')
            if not math.isfinite(float(hit.distance)) or not math.isfinite(float(hit.angle)):
                continue
            if (kind=='BOMB' and not hit.grasped
                    and self._own_hit(drone,float(hit.angle),float(hit.distance))):
                own_angles.append(float(hit.angle))
            elif kind in ('BOMB','DRONE','DISPOSAL_CENTER'):
                objects.append(hit.distance*self.vector(hit.angle))
        own=np.zeros(len(ranges),dtype=bool)
        for angle in own_angles:
            gap=np.abs((angles-angle+math.pi)%(2*math.pi)-math.pi)
            own|=gap<=.10
        own&=np.isfinite(ranges)&(ranges>0.)
        predicted=self._own_surface(drone,angles)
        own&=np.isfinite(predicted)&(np.abs(ranges-predicted)<=self.HIT_MARGIN)
        for i in np.flatnonzero(own):
            own[i]=self._own_hit(drone,float(angles[i]),float(ranges[i]))
        return own,objects

    def _prior_free(self, drone, direction, length):
        scan=self.before_drop_scan
        if scan is None:
            return False
        _,origin,angles,ranges=scan
        # Sample a padded 23px tube, not just its centreline. Missing rays are
        # unknown; a removed bomb hit never becomes a maximum-range reading.
        along=np.linspace(1.,length+23.,int(math.ceil((length+22.)/2.))+1)
        side=np.linspace(-23.,23.,24)
        u=self.vector(direction+drone.heading);v=np.array((-u[1],u[0]))
        points=(np.asarray(drone.pose)+along[:,None,None]*u+side[None,:,None]*v).reshape(-1,2)
        delta=points-origin
        distance=np.linalg.norm(delta,axis=1)
        bearings=np.arctan2(delta[:,1],delta[:,0])%(2*math.pi)
        upper=np.searchsorted(angles,bearings)%len(angles);lower=(upper-1)%len(angles)
        gaps=(angles[upper]-angles[lower])%(2*math.pi)
        spacing=np.median(np.diff(np.r_[angles,angles[0]+2*math.pi]))
        visible=(np.isfinite(ranges[upper])&np.isfinite(ranges[lower])
                 &(ranges[upper]>0.)&(ranges[lower]>0.)&(gaps<=min(.12,1.5*spacing)))
        # Five pixels cover sampling/measurement margin without shrinking the tube.
        free=visible&(distance+5.<np.minimum(ranges[upper],ranges[lower]))
        return bool(np.all(free))

    def _recovery_clear(self, drone, direction, length, angles, ranges, own, objects):
        cosine=np.cos(angles-direction);sine=np.sin(angles-direction)
        finite=np.isfinite(ranges)&(ranges>0.)
        forecast=(cosine>0.)&(np.abs((angles-direction+math.pi)%(2*math.pi)-math.pi)
                             <math.atan2(23.,max(1.,length)))
        if (not forecast.any() or np.count_nonzero(finite&forecast)<.9*np.count_nonzero(forecast)):
            return False
        forward=ranges*cosine;side=np.abs(ranges*sine)
        if np.any(finite&~own&(forward>0.)&(forward<length+23.)&(side<23.)):
            return False
        for point in objects:
            fore=float(point @ self.vector(direction))
            across=abs(float(point @ self.vector(direction+math.pi/2)))
            if 0.<fore<length+23. and across<23.:
                return False
        return self._prior_free(drone,direction,length)

    def _finish_recovery(self, step, reason):
        self.audit.append((step,'recovery_'+reason))
        self.recovery_started=None
        self.recovery_goal=None

    def recover(self, drone, command, step, ranges, semantic):
        """One bounded recovery; never places a bomb or changes a route."""
        active=self.recovery_started is not None
        if self.recovery_used and not active:
            return False
        if not active and (not self.recovery_failed or self.started is not None
                or self.first_point is None or len(self.recovery_trace)<self.RECOVERY_STALL):
            return False
        odom=drone.odometer_values()
        safe=(self._reliable(drone) and drone.initial_inventory==2 and drone.previous_inventory==1
              and drone.carried_bombs_count()==1 and drone.pending_drop is None
              and odom is not None and np.shape(odom)==(3,) and np.all(np.isfinite(odom))
              and abs(float(odom[0]))<=14. and ranges is not None)
        if active and self.recovery_watch:
            safe=safe and np.linalg.norm(np.asarray(drone.pose)-self.recovery_watch[-1])<=14.
        if not safe:
            if active:self._finish_recovery(step,'sensor_or_stock_exit')
            return False
        wall_left=drone.walltime_limit-drone.elapsed_walltime
        angles=np.asarray(drone.lidar_rays_angles(),dtype=float);ranges=np.asarray(ranges,dtype=float)
        if (angles.ndim!=1 or ranges.shape!=angles.shape or len(angles)<16
                or not np.all(np.isfinite(angles)) or np.count_nonzero(np.isfinite(ranges)&(ranges>0.))<3):
            if active:self._finish_recovery(step,'sensor_or_stock_exit')
            return False
        if active:
            if (step-self.recovery_started>=self.DURATION
                    or drone.elapsed_walltime-self.recovery_wall_started>=self.RECOVERY_SECONDS
                    or wall_left<=3. or drone.limit-step<=20
                    or self.recovery_tick!=step-1):
                self._finish_recovery(step,'timeout_or_budget_exit')
                return False
            if np.linalg.norm(np.asarray(drone.pose)-self.first_point)>=self.GOAL:
                self._finish_recovery(step,'clear')
                return False
        else:
            trace=self.recovery_trace
            if (trace[-1][0]!=step or trace[-1][0]-trace[0][0]!=self.RECOVERY_STALL-1
                    or max(np.linalg.norm(p-trace[0][1]) for _,p in trace)>=self.RECOVERY_STALL_MOVE
                    or np.linalg.norm(np.asarray(drone.pose)-self.first_point)>=32.
                    or wall_left<6. or drone.limit-step<82
                    or step+self.DURATION>drone.limit*93//100 or self.before_drop_scan is None):
                return False
            self.recovery_used=True
            self.recovery_started=step;self.recovery_wall_started=drone.elapsed_walltime
            self.recovery_watch.clear()
            self.audit.append((step,'recovery_started'))
        self.recovery_tick=step
        self.recovery_watch.append(np.asarray(drone.pose).copy())
        if (len(self.recovery_watch)==self.RECOVERY_WATCH
                and np.linalg.norm(self.recovery_watch[-1]-self.recovery_watch[0])<self.RECOVERY_MIN_PROGRESS):
            self._finish_recovery(step,'no_progress')
            return False
        own,objects=self._recovery_obstacles(drone,angles,ranges,semantic)
        if self.recovery_goal is None:
            base=math.atan2(*(np.asarray(drone.pose)-self.first_point)[::-1])-drone.heading
            for turn in (0,1,-1,2,-2,3,-3,4,-4,5,-5,6,-6,7,-7,8):
                direction=base+turn*math.pi/8
                goal=np.asarray(drone.pose)+self.GOAL*self.vector(direction+drone.heading)
                if (drone._inside_team_point(goal) and np.linalg.norm(goal-self.first_point)>=self.GOAL
                        and self._recovery_clear(drone,direction,self.GOAL,angles,ranges,own,objects)):
                    self.recovery_goal=goal
                    self.audit.append((step,'recovery_path',float(direction),self.GOAL))
                    break
            if self.recovery_goal is None:
                self._finish_recovery(step,'no_safe_path')
                return False
        delta=self.recovery_goal-np.asarray(drone.pose);length=float(np.linalg.norm(delta))
        direction=math.atan2(delta[1],delta[0])-drone.heading
        if not self._recovery_clear(drone,direction,length,angles,ranges,own,objects):
            self._finish_recovery(step,'obstacle_exit')
            command.update(drone.motion_command(np.zeros(2),
                float(odom[0])*self.vector(drone.heading-float(odom[2])+float(odom[1])),0.,.18,False,3.7))
            command.update(grasper=0,place_bomb=0)
            return True
        velocity=float(odom[0])*self.vector(drone.heading-float(odom[2])+float(odom[1]))
        desired=min(2.8,max(1.25,length/7.))*self.vector(direction+drone.heading)
        turn=(direction+math.pi/2)%math.pi-math.pi/2
        command.update(drone.motion_command(desired,velocity,turn,.18,False,3.7))
        command.update(grasper=0,place_bomb=0)
        self.controls_step=step
        return True

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

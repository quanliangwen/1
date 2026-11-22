"""Score-aware search closeout, with a bounded SDK-authoritative drop window."""
from collections import deque
import math

import numpy as np
from scipy.ndimage import binary_dilation
from swarm_rescue.simulation.drone.bomb_deployer import MIN_BOMB_SEPARATION
from swarm_rescue.solutions.final_map_relay import FinalMaps
from swarm_rescue.solutions.isolated_closeout import IsolatedCloseout


class FastCloseout:
    OBSERVATION_STEPS = 100
    DROP_STEPS = 24
    HANDOFF_STEPS = 48
    ANNOUNCE_STEPS = 8

    def __init__(self, owner, team_size):
        self.owner = int(owner)
        self.team_size = team_size
        self.history = deque(maxlen=3)
        self.advice = {}
        self.plan = None
        self.done = False
        self.maps = FinalMaps(owner, team_size)
        self.bids = {}
        self.vote = None
        self.audit = []
        self.target = None
        self.last_drop_target_step = -100
        self.last_amnesty_attempt = -100
        self.isolated = IsolatedCloseout()

    @staticmethod
    def score_time(step, limit):
        return 100.*max(0.,min(1.,(limit-step)/(.70*limit)))

    @classmethod
    def worth_closing(cls, step, limit, windows, wall_tiles, fraction, frontier_gain, has_overview):
        if len(windows)!=2 or not has_overview:
            return None
        # The count is a score proxy with an upper estimate from the faster
        # of two windows. Prefer a nearby substantial reachable frontier.
        predicted_map = 200.*max(windows)/max(100,wall_tiles)
        speed_gain = .10*(cls.score_time(step+cls.HANDOFF_STEPS,limit)
                          -cls.score_time(step+cls.HANDOFF_STEPS+2*cls.OBSERVATION_STEPS,limit))
        low_progress = max(windows)<=max(2.,.003*wall_tiles)
        decision=(fraction>=.95 or low_progress) and .5*predicted_map<speed_gain and frontier_gain<.12
        return bool(decision),float(predicted_map),float(speed_gain)

    def sample(self, drone, step):
        if self.plan is not None or self.done or step<.30*drone.limit or step%100!=self.owner:
            return
        grid=drone.grid
        evidence=grid.evidence
        stable=evidence>=6
        covered=(evidence<0) & (grid.searched>0)
        if self.history:
            earlier_free,earlier_walls=self.history[-1][1:3]
            changed=(np.count_nonzero(stable & ~binary_dilation(earlier_walls))
                     + .25*np.count_nonzero(covered & ~binary_dilation(earlier_free)))
            covered = covered | earlier_free
            stable = stable | earlier_walls
        else:
            changed=0
        self.history.append((step,covered.copy(),stable.copy(),float(changed)))
        if len(self.history)<3 or self.history[-1][0]-self.history[0][0]!=200:
            return
        wall_tiles=int(np.count_nonzero(stable))
        costs,work,_=grid.search_work(drone.pose)
        frontier=grid.frontier_gain()
        gain=max((float(frontier[cell]) for cell,cost in costs.items() if cost<=145. and work[cell]),default=0.)
        reachable=sum(bool(covered[cell]) for cell in costs)
        candidates=np.count_nonzero(binary_dilation(covered)&(evidence==0)&~grid.blocked)
        fraction=reachable/max(1,len(costs)+candidates)
        overview=float(drone.memory.free.mean())>=.43 and wall_tiles>=42 and drone.search_roaming.departed
        decision=self.worth_closing(step,drone.limit,[row[3] for row in list(self.history)[1:]],
                                    wall_tiles,fraction,gain,overview)
        if decision is not None:
            ready,predicted_map,time_gain=decision
            self.advice[self.owner]=(step,ready)
            self.audit.append((step,"benefit_review",ready,predicted_map,time_gain,float(fraction),gain))

    def initiate(self, drone, step):
        if self.plan is not None or self.done or step+self.ANNOUNCE_STEPS+self.HANDOFF_STEPS>=drone.limit-30:
            return
        ready=self.fresh_ready(step)
        if self.owner not in ready or len(ready)<2:
            return
        if step - self.advice[self.owner][0] > 4:
            return
        # Restrict origination to positively observed shared progress. Other
        # aircraft can receive this proposal without losing track of stock.
        active_recent={i:(tick,ok) for i,(tick,ok) in self.advice.items() if 0<=step-tick<=100}
        if any(not ok for tick,ok in active_recent.values()):
            return
        self.plan=(step+self.ANNOUNCE_STEPS,self.owner)
        self.audit.append((step,"planned",self.plan,tuple(sorted(ready))))

    def fresh_ready(self, step):
        return {owner for owner,(tick,ready) in self.advice.items() if ready and 0<=step-tick<=100}

    def packet(self, step):
        own=self.advice.get(self.owner)
        if self.plan is None or self.isolated.started:
            return own,None,None,None,None
        p=self.plan
        return own,p,(self.maps.mask,self.maps.outgoing(step)),self.bids.get(self.owner),self.vote

    def receive(self, drone, msg):
        sender=msg["id"]
        report=msg.get("red_fast_closeout")
        if (report is None or type(sender) is not int or sender==self.owner or not 0<=sender<self.team_size):
            return
        result,plan,tiles,bid,vote=report
        step=int(drone.elapsed_timestep)
        self.isolated.last_real_contact=step
        if self.isolated.started:
            return
        if (isinstance(result,tuple) and len(result)==2 and type(result[0]) is int
                and type(result[1]) is bool and 0<=step-result[0]<=100
                and result[0]>self.advice.get(sender,(-1,False))[0]):
            self.advice[sender]=result
        if (self.done or not isinstance(plan,tuple) or len(plan)!=2
                or any(type(x) is not int for x in plan)):
            return
        start,owner=plan
        if not (0<=owner<self.team_size and .30*drone.limit<=start<drone.limit-30-self.HANDOFF_STEPS
                and step-self.DROP_STEPS<start<=step+self.ANNOUNCE_STEPS):
            # Within an existing plan keep exchanging final data after drop
            # closes. A late plan cannot open a second drop window.
            if plan!=self.plan:
                return
        if self.plan is None or step<self.plan[0] and plan<self.plan:
            self.plan=plan
            self.audit.append((step,"adopted",plan,sender))
        if plan!=self.plan:
            return
        if tiles is not None:
            mask, snapshot=tiles
            if snapshot is not None and snapshot[1]<start+self.DROP_STEPS:
                snapshot=None
            self.maps.receive(sender,step,mask,snapshot)
        if (isinstance(bid,tuple) and len(bid)==3 and all(type(x) is int for x in bid)
                and start+self.DROP_STEPS<=bid[0]<=step
                and 0<=bid[1]<=10000 and 0<=bid[2]<1<<self.team_size):
            self.bids[sender]=bid
        if owner==sender and type(vote) is int and 0<=vote<self.team_size:
            self.vote=vote

    def phase(self, step):
        if self.plan is None or self.done:
            return None
        start,_=self.plan
        if step<start:
            return "prepare"
        if step<start+self.DROP_STEPS:
            return "drop"
        return "relay" if step<=start+self.HANDOFF_STEPS else None

    def legal_drop_pulse(self, drone, command, step):
        count=drone.previous_inventory
        if (self.phase(step)!="drop" or not count or drone.pending_drop is not None
                or step%4!=self.owner%4 or step>=drone.limit
                or drone.elapsed_walltime>=drone.walltime_limit
                or step-self.last_amnesty_attempt<2):
            return
        # No placement-policy gate. The official SDK checks the actual
        # physical minimum spacing, disposal-center overlap and inventory.
        command.update(grasper=0,place_bomb=1)
        drone.pending_drop=(count,drone.pose.copy(),step)
        drone.last_attempt_step=step
        drone.placement.request=(step,"fast_closeout",bool(drone.grid.pose_fixed),count)
        drone.placement.audit.append((step,"request","fast_closeout",bool(drone.grid.pose_fixed),count))
        self.last_amnesty_attempt=step

    def _choose_departure(self, drone, ranges, semantic):
        angles=np.asarray(drone.lidar_rays_angles())
        moving=[]
        bombs=[np.asarray(point) for point in drone.drop_records.values()]
        for hit in semantic:
            kind=hit.entity_type.name
            if kind not in ("BOMB","DRONE","DISPOSAL_CENTER") or not math.isfinite(hit.distance):
                continue
            relative=hit.distance*np.array((math.cos(hit.angle),math.sin(hit.angle)))
            moving.append(relative)
            if kind=="BOMB":
                yaw=drone.heading+hit.angle
                bombs.append(drone.pose+(hit.distance+12.)*np.array((math.cos(yaw),math.sin(yaw))))
        fav=None
        estimate=drone.team_wall.query(drone,semantic,int(drone.elapsed_timestep))
        lengths=(44.,30.,18.) if self.isolated.started else (44.,)
        for length in lengths:
            for direction in np.linspace(-math.pi,math.pi,24,endpoint=False):
                if not drone.local_escape.clearance(direction,angles,ranges,length,moving):
                    continue
                yaw=direction+drone.heading
                target=drone.pose+length*np.array((math.cos(yaw),math.sin(yaw)))
                terminal=min((math.dist(target,b) for b in bombs),default=100.)
                if terminal<MIN_BOMB_SEPARATION:
                    continue
                rank=estimate(target)[0],terminal
                if fav is None or rank>fav:
                    best,fav=target,rank
            if fav is not None:
                return best
        return None

    def move_remaining(self, drone, command, step, ranges, semantic):
        if not drone.previous_inventory or ranges is None:
            return
        odom=drone.odometer_values()
        if odom is None or not np.all(np.isfinite(odom)):
            return
        ranges=np.asarray(ranges,dtype=float)
        # Keep the old guarded motion if no useful short departure is visible.
        if (self.target is None or math.dist(drone.pose,self.target)<8.
                or step-self.last_drop_target_step>=12):
            self.target=self._choose_departure(drone,ranges,semantic)
            self.last_drop_target_step=step
        if self.target is None:
            return
        aim=np.subtract(self.target,drone.pose)
        local=math.atan2(aim[1],aim[0])-drone.heading
        moving=[(h.distance*math.cos(h.angle),h.distance*math.sin(h.angle))
                for h in semantic if h.entity_type.name in ("BOMB","DRONE","DISPOSAL_CENTER")]
        if not drone.local_escape.clearance(local,np.asarray(drone.lidar_rays_angles()),
                                             ranges,min(32.,np.linalg.norm(aim)),moving):
            self.target=None
            return
        yaw=drone.heading-float(odom[2])+float(odom[1])
        velocity=float(odom[0])*np.array((math.cos(yaw),math.sin(yaw)))
        command.update(drone.drive(self.target,velocity))

    def submit(self, drone, step):
        group = getattr(drone, "group_exchange", None)
        if group is not None and not group.ordinary_submit_allowed(drone, step, "fast_closeout"):
            return False
        start,turn=self.plan
        if not drone._all_inventory_empty() or drone.pending_drop is not None:
            return False
        self.maps.freeze(step,drone.memory)
        self.bids[self.owner]=(step,self.maps.rank(drone.map_quality or 0),self.maps.mask)
        if turn==self.owner and self.vote is None and step>=start+self.DROP_STEPS+12:
            fresh={owner:bid for owner,bid in self.bids.items() if step-bid[0]<=12}
            # A complete fusion may proceed as soon as bids arrive. Otherwise
            # give missing real snapshots and confirmations a bounded chance.
            best=max(fresh,key=lambda i:(fresh[i][1],-i))
            if fresh[best][2].bit_count()==self.team_size or step>=start+self.HANDOFF_STEPS-6:
                self.vote=best
                self.audit.append((step,"elected",best,fresh[best]))
        if self.vote!=self.owner:
            return False
        # Use the submissions renderer and its verified live memory, adding
        # the fast-final advice through the existing FinalMaps implementation.
        original=drone.final_maps
        drone.final_maps=self.maps
        try:
            image,cache,versions=drone._submission_image(step)
        finally:
            drone.final_maps=original
        if not image.any():
            return False
        drone.submit_exploration_map(image.astype(np.uint8))
        drone.submitted_cache=cache
        drone.final_submission_versions=versions
        drone.submission_elected_rank=self.bids[self.owner][1]
        drone.submitted=True
        drone.red_submission_step=step
        self.audit.append((step,"submitted",len(versions)))
        return True

    def act(self, drone, step, command, ranges, semantic):
        self.sample(drone,step)
        self.initiate(drone,step)
        self.isolated.track(drone,step)
        if (self.plan is None and not self.done and
                step+self.ANNOUNCE_STEPS+self.DROP_STEPS<drone.limit-30
                and drone.walltime_limit-drone.elapsed_walltime>3.):
            reason=self.isolated.ready(drone,step,self.advice.get(self.owner))
            if reason is not None:
                self.plan=(step+self.ANNOUNCE_STEPS,self.owner)
                self.isolated.started=True
                self.audit.append((step,"isolated_closeout",self.plan,reason,self.isolated.last_real_contact))
        phase=self.phase(step)
        if phase is None:
            if self.plan is not None and not self.done:
                self.audit.append((step,"expired",drone.previous_inventory,drone._all_inventory_empty()))
                self.done=True
            return False
        if self.isolated.started and phase=="relay":
            drone.placement.finish_request(drone,step)
            self.audit.append((step,"isolated_window_complete",drone.previous_inventory))
            self.done=True
            return False
        departure=getattr(drone,"drop_departure",None)
        relocating=departure is not None and departure.controls_step==step
        second=getattr(drone,"second_drop",None)
        site_state=None
        if second is not None and not relocating and phase in ("prepare","drop"):
            if phase=="prepare":
                second.reserve(drone,step,ranges,semantic)
            site_state=second.control(drone,step,command,ranges,semantic)
        if phase=="prepare":
            if site_state is not None:
                return True
            if self.isolated.started:
                if not relocating:
                    self.move_remaining(drone,command,step,ranges,semantic)
                    drone.local_escape.apply(drone,command,step,ranges,semantic)
                return True
            return False
        drone.placement.finish_request(drone,step)
        if phase=="drop":
            elapsed=step-self.plan[0]
            if second is not None and second.wait_for_site(site_state,elapsed):
                return True
            if not relocating and site_state!="ready":
                if second is not None:
                    second.clear(step,"sdk_fallback")
                self.move_remaining(drone,command,step,ranges,semantic)
                drone.local_escape.apply(drone,command,step,ranges,semantic)
            self.legal_drop_pulse(drone,command,step)
            return True
        # End repeat exploration during the short transaction. Recover normal
        # flight and the unchanged last-30 fallback if the group could not close.
        if not relocating:
            command.update(forward=0.,lateral=0.,rotation=0.,grasper=0,place_bomb=0)
        if drone.previous_inventory==0 and drone.pending_drop is None:
            self.maps.freeze(step,drone.memory)
        self.submit(drone,step)
        return True

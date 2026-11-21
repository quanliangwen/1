"""One return mission: local branch exchange, shared parent exchange, submit."""
from dataclasses import dataclass
import math
import numpy as np
from swarm_rescue.solutions.deadline_submission import DeadlineSubmission
from swarm_rescue.solutions.partial_map_submit import provisional_map
from swarm_rescue.solutions.exchange_plan import ExchangePlan, inside, known_segment
from swarm_rescue.solutions.map_candidates import MapCandidates


@dataclass(frozen=True)
class ReturnIntent:
    target: tuple
    route: tuple
    group: tuple
    eta: int


class GroupExchange:
    ACTIVE = {'RETURN_LOCAL','LOCAL_EXCHANGE','COURIER_TO_C','INTERGROUP_EXCHANGE','DELIVERED_HOLD'}

    def __init__(self, owner, team_size, limit, size):
        self.owner,self.team_size,self.limit=int(owner),team_size,limit
        self.plan=ExchangePlan(owner,team_size,limit)
        self.candidates=MapCandidates(owner,self.plan.epoch,*map(int,size))
        self.phase='OBSERVE'
        self.started_step=None
        self.complete_step=None
        self.route=[]
        self.detour=[]
        self.target=None
        self.group=(self.owner,)
        self.peer_status={}
        self.audit=[]
        self.choice=None
        self.choice_step=None
        self.choice_acks=set()
        self.next_plan=0
        self.blocked_since=None
        self.last_gate=None
        self.hold=None
        self.role=None
        self.releases=0
        self.best_installed=None
        self.selection_attempted=False
        self.original_messenger_state=None

    @property
    def owns_navigation(self):
        return self.phase in self.ACTIVE

    def start(self):return self.limit*3//5

    def cutoff(self):
        return min(self.limit*85//100,DeadlineSubmission.window_start(self.limit)-12)

    def expired(self, drone, step):
        return step>=self.cutoff() or drone.walltime_limit-drone.elapsed_walltime<=8

    def gate(self, step, reason):
        if reason != self.last_gate:
            self.last_gate=reason;self.audit.append((step,'return_preflight',reason))

    def observe(self, drone, step):
        self.plan.observe(drone,step,record_trail=self.phase=='OBSERVE')
        # A late finisher may hand over at an actual contact even when a full
        # return detour cannot fit. This never acquires/cancels navigation.
        if (self.plan.committed() and self.start()<=step and not self.expired(drone,step)
                and drone.previous_inventory==0 and drone.pending_drop is None
                and drone.placement.maneuvers.exit is None
                and drone.placement.maneuvers.waiting_exit is None):
            self.candidates.freeze_local(drone,step)
            self.candidates.build_local_image(drone,step)
        if self.owns_navigation and self.expired(drone,step):
            self.release(drone,'EXPIRED')
            self.audit.append((step,'coord_cutoff','released_navigation_and_submit_gate'))

    def release(self, drone, phase):
        self.phase=phase;self.releases+=1;self.role=None
        if self.original_messenger_state is not None and drone.messenger.state=='DONE':
            drone.messenger.state=self.original_messenger_state

    def prepare_return(self, drone, step):
        # Read-only with respect to all original controller/mission state.
        if self.phase!='OBSERVE' or step<self.start():return None
        if self.expired(drone,step):self.gate(step,'budget');return None
        if drone.previous_inventory!=0 or drone.pending_drop is not None:
            self.gate(step,'stock_or_pending');return None
        maneuvers=drone.placement.maneuvers
        if (maneuvers.exit is not None or maneuvers.waiting_exit is not None
                or drone.drop_departure.controls_step==step):
            self.gate(step,'placement_escape');return None
        if not self.plan.committed():self.gate(step,'no_shared_root');return None
        if not self.plan.reachable_root():self.gate(step,'no_root_trail_gate');return None
        group=self.plan.branch_group
        target=self.plan.local_region if len(group)>1 else self.plan.root[1:]
        index=self.plan.gate_index(target) if target is not None else None
        if index is None:
            target=self.plan.root[1:];index=self.plan.gate_index(target);group=(self.owner,)
        route=list(reversed(self.plan.trail[index:]))
        while route and math.dist(drone.pose,route[0])<=8:route.pop(0)
        # A radio area may be reached without crowding the marker itself.
        point=tuple(self.plan.trail[index])
        if route and not known_segment(drone,drone.pose,route[0]):
            connection=list(drone.grid.route(drone.pose,route[0]))
            if not connection:self.gate(step,'no_safe_join');return None
            route=connection+route
            while route and math.dist(drone.pose,route[0])<=8:route.pop(0)
            if route and not known_segment(drone,drone.pose,route[0]):
                self.gate(step,'unsafe_join');return None
        length=sum(math.dist(a,b) for a,b in zip([tuple(drone.pose)]+route,route))
        eta=math.ceil(length/2)+40
        if step+eta>=self.cutoff():self.gate(step,'insufficient_route_budget');return None
        self.gate(step,'ready')
        return ReturnIntent(point,tuple(map(tuple,route)),tuple(group),eta)

    def commit_return(self, drone, intent, step):
        assert self.phase=='OBSERVE' and self.plan.committed()
        self.phase='RETURN_LOCAL';self.started_step=step
        self.target,self.route,self.group=intent.target,list(intent.route),intent.group
        drone.route=[];drone.search_task=None
        self.original_messenger_state=drone.messenger.state
        if drone.messenger.state!='DONE':
            drone.messenger.state='DONE';drone.messenger.audit.append((step,'group_return_handoff'))
        self.candidates.freeze_local(drone,step)
        self.audit.append((step,'return_owned',self.group,self.target,intent.eta,self.plan.root))

    def receive(self, drone, message, step):
        body=message.get('red_group_exchange')
        if not isinstance(body,dict):return
        self.plan.receive(drone,message,body,step)
        peer=message.get('id')
        if (type(peer) is not int or peer==self.owner or not 0<=peer<self.team_size
                or tuple(body.get('epoch',()))!=self.plan.epoch):return
        ts=body.get('step')
        if type(ts) is not int or not 0<=step-ts<=12:return
        have=set()
        for row in body.get('receipts',()):
            if isinstance(row,tuple) and len(row)==4 and row[0] in ('snapshot','image'):
                have.add(row)
                kind,owner,version,checksum=row
                store=self.candidates.snapshots if kind=='snapshot' else self.candidates.images
                item=store.get(owner)
                if item is not None and (item['version'],item['digest'])==(version,checksum):
                    key=(peer,*row)
                    if key not in self.candidates.receipts:
                        self.candidates.receipts[key]=step
                        self.audit.append((step,'payload_acked',peer,*row))
        self.peer_status[peer]=dict(step=step,have=have,phase=body.get('phase'),
                                    eta=body.get('eta',100000),role=body.get('role'),
                                    group=tuple(body.get('group',())),point=body.get('point'))
        self.candidates.receive(drone,peer,body.get('payload'),step)
        choice=body.get('choice')
        if isinstance(choice,dict) and self.valid_choice(choice,step):
            proposer=choice['proposer']
            if self.choice is None or proposer < self.choice['proposer']:
                self.choice=dict(choice);self.choice_step=step;self.choice_acks=set()
                self.audit.append((step,'choice_received',peer,choice))
        if self.choice is not None:
            key=self.choice['key']
            if body.get('choice_ack')==key and body.get('choice')==self.choice:
                self.choice_acks.add(peer)
            owner=self.choice['image_owner']
            data=self.candidates.images.get(owner)
            if data is not None and data['digest']==self.choice['image_digest']:
                self.choice_acks.add(self.owner)

    def fresh(self, step):
        return {i:p for i,p in self.peer_status.items() if 0<=step-p['step']<=12}

    def eta_root(self, drone):
        if not self.plan.reachable_root() or drone.pose is None:return 100000
        i=self.plan.gate_index(self.plan.root[1:])
        near=min(range(len(self.plan.trail)),key=lambda j:math.dist(drone.pose,self.plan.trail[j]))
        lo,hi=sorted((i,near))
        length=math.dist(drone.pose,self.plan.trail[near])+sum(math.dist(a,b) for a,b in
                   zip(self.plan.trail[lo:hi],self.plan.trail[lo+1:hi+1]))
        length+=max(0.,math.dist(self.plan.trail[i],self.plan.root[1:])-80.)
        return int(math.ceil(length/2))+40

    def message(self, drone, step):
        body=self.plan.message(drone)
        body.update(phase=self.phase,group=self.group,role=self.role,
                    eta=self.eta_root(drone) if self.owns_navigation else 100000,
                    manifest=self.candidates.manifest(),receipts=self.candidates.manifest(),
                    choice=self.choice,score_table=self.candidates.score_table,
                    choice_ack=(self.choice['key'] if self.choice is not None
                        and self.owner in self.choice_acks else None),payload=None)
        if self.owner in self.candidates.snapshots and not self.expired(drone,step):
            body['payload']=self.candidates.payload(step,[p['have'] for p in self.fresh(step).values()])
        return body

    def ordinary_submit_allowed(self, drone, step, path='ordinary'):
        return not (self.plan.committed() and self.start()<=step<self.cutoff()
                    and not self.expired(drone,step) and self.phase not in ('ABORT','EXPIRED','SUBMITTED'))

    def complete(self, group=None):
        owners=set(range(self.team_size)) if group is None else set(group)
        return owners.issubset(self.candidates.snapshots) and owners.issubset(self.candidates.images)

    def go_root(self, drone, step):
        i=self.plan.gate_index(self.plan.root[1:])
        near=min(range(len(self.plan.trail)),key=lambda j:math.dist(drone.pose,self.plan.trail[j]))
        if near>=i:route=list(reversed(self.plan.trail[i:near+1]))
        else:route=list(self.plan.trail[near:i+1])
        root=self.plan.root[1:]
        if math.dist(route[-1],root)>80:
            if known_segment(drone,route[-1],root):route.append(tuple(root))
            else:
                tail=list(drone.grid.route(route[-1],root))
                if not tail or math.dist(tail[-1],root)>80:
                    self.release(drone,'ABORT');self.audit.append((step,'route_abort','no_C_radio_area_join'));return
                route.extend(map(tuple,tail))
        self.route=route;self.detour=[];self.target=tuple(route[-1])
        self.phase='COURIER_TO_C';self.role='courier'
        self.audit.append((step,'courier_to_C',self.target,self.eta_root(drone),self.candidates.manifest()))

    def tick_navigation(self, drone, step, command, ranges, semantic):
        if not self.owns_navigation:return False
        self.candidates.build_local_image(drone,step)
        if self.phase=='LOCAL_EXCHANGE':
            local_done=self.complete(self.group)
            leave_at=self.cutoff()-self.eta_root(drone)-40
            if local_done or step>=leave_at:
                fresh=self.fresh(step)
                wanted=set(self.group)
                eligible=[(self.eta_root(drone),self.owner)]
                for i,p in fresh.items():
                    have_snap={r[1] for r in p['have'] if r[0]=='snapshot'}
                    have_image={r[1] for r in p['have'] if r[0]=='image'}
                    if i in wanted and wanted.issubset(have_snap&have_image):
                        eligible.append((p['eta'],i))
                # A courier already announced in actual contact owns the lease.
                announced=[i for i,p in fresh.items() if i in wanted and p['role']=='courier']
                courier=min(announced) if announced else min(eligible)[1]
                if courier==self.owner:self.go_root(drone,step)
                else:
                    self.phase='DELIVERED_HOLD';self.role='delivered';self.hold=tuple(drone.pose)
                    self.audit.append((step,'delivered_hold',courier))
        while self.route and math.dist(drone.pose,self.route[0])<=8:self.route.pop(0)
        while self.detour and math.dist(drone.pose,self.detour[0])<=8:self.detour.pop(0)
        if self.phase in ('RETURN_LOCAL','COURIER_TO_C') and not self.route:
            self.phase='LOCAL_EXCHANGE' if self.phase=='RETURN_LOCAL' else 'INTERGROUP_EXCHANGE'
            self.hold=tuple(drone.pose)
            self.audit.append((step,'region_arrival',self.phase,self.target))
        target=self.detour[0] if self.detour else self.route[0] if self.route else self.hold or tuple(drone.pose)
        if not known_segment(drone,drone.pose,target):
            if self.blocked_since is None:self.blocked_since=step
            if step>=self.next_plan:
                self.next_plan=step+20
                self.detour=[tuple(p) for p in drone.grid.route(drone.pose,target) if math.dist(drone.pose,p)>8]
            if not self.detour or not known_segment(drone,drone.pose,self.detour[0]):
                if step-self.blocked_since>=40:
                    self.release(drone,'ABORT')
                    self.audit.append((step,'route_abort','no_safe_join'));return False
                target=tuple(drone.pose)
            else:target=self.detour[0]
        else:self.blocked_since=None
        command.update(drone.drive(target,drone.measured_velocity(),ignore_own_bombs=True))
        command['place_bomb']=0
        drone.local_escape.apply(drone,command,step,ranges,semantic)
        return True

    def valid_choice(self, choice, step):
        fields=('proposer','executor','backup','image_owner','image_digest','reference_digest','key','lease_end','created')
        if not all(k in choice for k in fields):return False
        from swarm_rescue.solutions.map_candidates import digest
        return (choice['key']==digest({k:v for k,v in choice.items() if k!='key'})
                and all(type(choice[k]) is int and 0<=choice[k]<self.team_size for k in ('proposer','executor','backup'))
                and type(choice['image_owner']) is int and 0<=choice['image_owner']<=self.team_size
                and type(choice['created']) is int and self.start()<=choice['created']<=step
                and choice['lease_end']==self.cutoff()
                and all(isinstance(choice[k],str) and len(choice[k])==64 for k in ('image_digest','reference_digest','key')))

    def try_submit(self, drone, step, score_fn):
        if self.owner not in self.candidates.snapshots or drone.previous_inventory!=0 or drone.pending_drop is not None:
            return False
        if not drone._all_inventory_empty():return False
        if provisional_map(step,drone.map_quality,drone.map_revision,drone.walltime_limit-drone.elapsed_walltime):
            return False
        if self.expired(drone,step) and self.choice is None and self.candidates.images:
            # Bounded coordination: compare only actually held images, no new fit.
            holders=[i for i,p in self.fresh(step).items() if any(r[0]=='image' for r in p['have'])]
            if min([self.owner]+holders)!=self.owner:return False
            selected=self.candidates.choose(drone,step,score_fn,fusion=False)
            self.candidates.install(drone,selected['owner'],step)
            image,cache,versions=drone.group_best_image
            if not image.any():return False
            drone.submit_exploration_map(image.astype(np.uint8,copy=False))
            drone.submitted_cache=cache;drone.final_submission_versions=versions
            drone.red_submission_step=step;drone.submitted=True;self.phase='SUBMITTED'
            self.audit.append((step,'soft_cutoff_submit',selected,sorted(self.candidates.snapshots)))
            return True
        if self.choice is None and self.complete() and not self.selection_attempted:
            # One scorer in the current actually connected set of full holders.
            full=set(range(self.team_size))
            peers=[]
            for i,p in self.fresh(step).items():
                snap={r[1] for r in p['have'] if r[0]=='snapshot'}
                imgs={r[1] for r in p['have'] if r[0]=='image'}
                if full.issubset(snap&imgs):peers.append(i)
            if min([self.owner]+peers)!=self.owner:return False
            self.selection_attempted=True
            selected=self.candidates.choose(drone,step,score_fn)
            if selected is None:return False
            owner=selected['owner']
            holders=[self.owner]+[i for i,p in self.fresh(step).items() if
                      ('image',owner,selected['version'],selected['digest']) in p['have']]
            executor=owner if owner in holders else min(holders)
            from swarm_rescue.solutions.map_candidates import digest
            backup=min((i for i in holders if i!=executor),default=executor)
            choice=dict(proposer=self.owner,executor=executor,backup=backup,image_owner=owner,
                        image_digest=selected['digest'],reference_digest=self.candidates.reference_digest,
                        lease_end=self.cutoff(),created=step)
            choice['key']=digest(choice)
            self.choice=choice;self.choice_step=step;self.choice_acks={self.owner}
            self.complete_step=step
            self.audit.append((step,'choice_proposed',choice))
        if self.choice is None:return False
        owner=self.choice['image_owner'];data=self.candidates.images.get(owner)
        if data is None or data['digest']!=self.choice['image_digest']:return False
        if self.best_installed!=data['digest']:
            self.candidates.install(drone,owner,step);self.best_installed=data['digest']
        self.choice_acks.add(self.owner)
        executor=self.choice['executor']
        if self.expired(drone,step) and self.owner==self.choice['backup']:
            executor=self.owner
        if self.owner!=executor or self.owner not in self.choice_acks:return False
        if step-self.choice['created']<2:return False
        image,cache,versions=drone.group_best_image
        if not image.any():return False
        drone.submit_exploration_map(image.astype(np.uint8,copy=False))
        drone.submitted_cache=cache;drone.final_submission_versions=versions
        drone.red_submission_step=step;drone.submitted=True
        self.phase='SUBMITTED'
        self.audit.append((step,'submitted',self.choice))
        return True

"""Empty drones only: optional jointly certified nonblocking waiting goals."""
import math
import time
import numpy as np
from swarm_rescue.solutions.waiting_core import states_valid,validate_plan,propose_waiting_plan,waiting_leader

class JointWaitingMixin:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._waiting_plan=None
        self._waiting_target=None
        self._waiting_build_step=-1000
        self._waiting_drive=None
        self.waiting_events=[]
        self._waiting_exchange_ready=False
        self._waiting_ready_reports={}

    def _waiting_emit(self,kind,step,**data):
        event=dict(kind=kind,owner=int(self.identifier or 0),step=int(step),**data)
        if len(self.waiting_events)<64:self.waiting_events.append(event)

    def _waiting_states(self,step):
        states={}
        for k,rec in self.fleet_states.items():
            if type(k)is not int or not isinstance(rec,(tuple,list))or len(rec)!=3:continue
            stamp,p,q=rec
            if type(stamp)is int and p is not None and 0<=step-stamp<=120:
                states[k]=(stamp,np.asarray(p,float).copy(),int(q))
        if self.pose is not None:states[int(self.identifier or 0)]=(int(step),np.asarray(self.pose).copy(),int(self.carried_bombs_count()))
        return states

    def _waiting_can_wait(self,step):
        if int(self.carried_bombs_count())!=0:
            self._waiting_exchange_ready=False
            return False
        if self._sortie_state=='SORTIE':return False
        survey=getattr(self,'survey_plan',None)
        if isinstance(survey,(tuple,list))and len(survey)==5:
            epoch,leader,owner,p,until=survey[0],survey[1],survey[2],survey[3],survey[4]
            if owner==int(self.identifier or 0)and p is not None and 0<=step-epoch<120 and step<until:return False
        docked=getattr(self,'_sortie_docked_step',None)
        if not self._waiting_exchange_ready and docked is not None and step-docked>=24:
            received=getattr(self,'last_peer_step',{})
            if any(peer!=int(self.identifier or 0)and docked<stamp<=step and step-stamp<100 for peer,stamp in received.items()):
                self._waiting_exchange_ready=True
                self._waiting_emit('MAP_EXCHANGE_COMPLETED',step,docked=int(docked))
        return self._waiting_exchange_ready

    def define_message_for_all(self):
        result=super().define_message_for_all()
        plan=self._waiting_plan
        result['waiting_plan_v1']=plan if plan is not None and plan['leader']==int(self.identifier or 0)and int(self.elapsed_timestep)<=plan['expires']else None
        step=int(self.elapsed_timestep)
        result['waiting_ready_v1']=(step,bool(self._waiting_can_wait(step)))
        return result

    def _messages(self):
        super()._messages()
        step=int(self.elapsed_timestep)
        if self.pose is None or self.rally is None:return
        states=self._waiting_states(step)
        for _,msg in self.communicator.received_messages:
            if not isinstance(msg,dict)or msg.get('kind')!='greedy-map-v1'or'map'not in msg:continue
            sender,sent=msg.get('id'),msg.get('step')
            if type(sender)is not int or self.last_peer_step.get(sender)!=sent:continue
            readiness=msg.get('waiting_ready_v1')
            if(isinstance(readiness,(tuple,list))and len(readiness)==2 and type(readiness[0])is int
                    and type(readiness[1])is bool and readiness[0]==sent and 0<=step-sent<=48):
                old_ready=self._waiting_ready_reports.get(sender,(-1,False))
                if sent>old_ready[0]:self._waiting_ready_reports[sender]=(sent,readiness[1])
            plan=msg.get('waiting_plan_v1')
            target=validate_plan(plan,step,int(self.identifier or 0),self.team_size,states,self.rally,sender,sent)
            if target is None:continue
            old=self._waiting_plan
            if old is None or(plan['epoch'], -plan['leader'])>(old['epoch'],-old['leader']):
                self._waiting_plan=plan
                self._waiting_emit('RECEIVED',step,leader=sender,epoch=plan['epoch'])

    def _plan_route(self,step,returning,peer_goals):
        original=super()._plan_route(step,returning,peer_goals)
        self._waiting_target=None
        if (self.submitted or self.pose is None or self.rally is None
                or int(self.carried_bombs_count())!=0 or self._sortie_state=='SORTIE'):
            return original
        if not self._waiting_can_wait(step):return original
        states=self._waiting_states(step)
        if not states_valid(states,step,self.team_size):return original
        own=int(self.identifier or 0)
        if own==waiting_leader(states)and np.linalg.norm(self.pose-self.rally)<=120. and step-self._waiting_build_step>=48:
            self._waiting_build_step=step
            protected=[]
            for peer,(stamp,pos,q)in states.items():
                if q<=0:continue
                report=self.assignment_reports.get(peer)
                if report is None:continue
                sent,inv,goal,since=report
                if goal is not None and inv==q and 0<=step-sent<=48 and 0<=step-since<self.GOAL_LEASE_STEPS:
                    protected.extend([pos,np.asarray(goal,float)])
            ready={peer for peer,(sent,flag)in self._waiting_ready_reports.items()if flag and 0<=step-sent<=48}
            ready.add(own)
            plan,audit=propose_waiting_plan(self.memory,step,own,self.team_size,states,self.rally,protected,time.perf_counter()+.05,eligible_idle=ready)
            self._waiting_emit('BUILD',step,audit=audit)
            if plan is not None:self._waiting_plan=plan
        target=validate_plan(self._waiting_plan,step,own,self.team_size,states,self.rally)
        if target is None:return original
        route,actual=self.memory.route(self.pose,destination=target)
        if actual is None or np.linalg.norm(np.asarray(actual)-target)>=1.:
            self._waiting_emit('ROUTE_REJECTED_KEEP_ORIGINAL',step,target=target.tolist())
            return original
        self._waiting_target=target.copy()
        self._waiting_emit('ROUTE_ACCEPTED',step,target=target.tolist(),epoch=self._waiting_plan['epoch'])
        return route or[target.copy()],target.copy()

    def _drive(self,*args,**kwargs):
        result=super()._drive(*args,**kwargs)
        self._waiting_drive=dict(result)
        return result

    def control(self):
        self._waiting_drive=None
        result=super().control()
        if(self.submitted or self.pose is None or self.rally is None
                or int(self.carried_bombs_count())!=0 or self._sortie_state=='SORTIE'
                or self._waiting_target is None):return result
        step=int(self.elapsed_timestep)
        if not self._waiting_can_wait(step):return result
        goal=validate_plan(self._waiting_plan,step,int(self.identifier or 0),self.team_size,self._waiting_states(step),self.rally)
        if goal is None:return result
        if np.linalg.norm(self.pose-goal)<=12.:
            velocity=self.measured_velocity()
            if velocity is None or not np.isfinite(velocity).all():velocity=np.zeros(2)
            c,s=math.cos(self.heading),math.sin(self.heading)
            result.update(forward=float(np.clip(-(velocity[0]*c+velocity[1]*s)/5.5,-1,1)),
                          lateral=float(np.clip(-(-velocity[0]*s+velocity[1]*c)/5.5,-1,1)),rotation=0.,grasper=0,place_bomb=0)
            if not any(e['kind']=='ARRIVED'and e.get('epoch')==self._waiting_plan['epoch']for e in self.waiting_events):
                self._waiting_emit('ARRIVED',step,target=goal.tolist(),epoch=self._waiting_plan['epoch'])
            return result
        # Recover the original motor command from this very control call if
        # the inherited completion layer tried to hold at the old rally point.
        return dict(self._waiting_drive)if self._waiting_drive is not None else result

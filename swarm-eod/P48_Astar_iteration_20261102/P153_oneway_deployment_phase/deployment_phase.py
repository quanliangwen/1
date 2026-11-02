"""One-way explore -> execute transition after an actual accepted fleet plan.

No new coordinator or synchronization promise. Original sensing, map rendering,
layout supplier, A-star, inventory confirmation and submission guard remain.
"""
import math
import numpy as np
from swarm_rescue.solutions.greedy_mapping import GreedyMappingDrone


class OneWayDeploymentMixin:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.deployment_started=None
        self.deployment_events=[]
        self.deployment_counts={}
        self._deployment_hold=False

    def _deployment_event(self,kind,step,**fields):
        self.deployment_counts[kind]=self.deployment_counts.get(kind,0)+1
        if len(self.deployment_events)<96:
            self.deployment_events.append(dict(kind=kind,owner=int(self.identifier or 0),step=int(step),**fields))

    def _latch_deployment(self,step):
        if self.deployment_started is not None:return True
        plan=getattr(self,'fleet_plan',None)
        if not isinstance(plan,(tuple,list))or len(plan)!=3:return False
        epoch,leader,plans=plan
        if type(epoch)is not int or type(leader)is not int or not 0<=step-epoch<self.PLAN_FRESH_STEPS:return False
        active=[k for k,(stamp,pos,_)in self.fleet_states.items()if pos is not None and 0<=step-stamp<self.STATE_FRESH_STEPS]
        if not active or leader!=min(active)or not isinstance(plans,dict):return False
        actual_task=False
        try:
            for owner,assignment in plans.items():
                if type(owner)is not int or owner not in active or not isinstance(assignment,(tuple,list))or len(assignment)!=2:continue
                original,goals=assignment
                if type(original)is not int or original<=0 or not isinstance(goals,(tuple,list)):continue
                if goals and any(np.asarray(p).shape!=(2,)or not np.isfinite(np.asarray(p,dtype=float)).all()for p in goals):return False
                if goals:actual_task=True
        except (TypeError,ValueError,OverflowError):return False
        if not actual_task:return False
        self.deployment_started=(int(step),epoch,leader)
        self._deployment_hold=True
        self.last_plan_step=-1000
        self.survey_plan=None
        if getattr(self,'_sortie_state',None)=='SORTIE':self._sortie_return(step)
        self._deployment_event('PHASE_BEGIN',step,plan_epoch=epoch,leader=leader,inventory=int(self.carried_bombs_count()))
        return True

    def _messages(self):
        result=super()._messages()
        self._latch_deployment(int(self.elapsed_timestep))
        return result

    def _should_defer_commitment(self,loss,remaining,execution,probe,completion_value,step):
        if self._latch_deployment(step):
            self._deployment_event('COMMIT_GATE_DISABLED',step)
            return False
        return super()._should_defer_commitment(loss,remaining,execution,probe,completion_value,step)

    def _build_survey_plan(self,step):
        if self._latch_deployment(step):
            self.survey_plan=None
            return
        return super()._build_survey_plan(step)

    def _sortie_admit(self,step,peer_goals):
        if self._latch_deployment(step):return None
        return super()._sortie_admit(step,peer_goals)

    def _plan_route(self,step,returning,peer_goals):
        self._latch_deployment(step)
        ordinary=super()._plan_route(step,returning,peer_goals)
        if not self._latch_deployment(step):return ordinary
        self._deployment_hold=False
        inventory=int(self.carried_bombs_count())
        if inventory==0:
            self._deployment_event('EMPTY_RETURN',step)
            return ordinary
        target=self.placement_goal
        if target is not None and ordinary[1]is not None and np.linalg.norm(np.asarray(ordinary[1])-target)<1.:
            self._deployment_event('DEPLOY_TARGET',step,target=np.asarray(target).tolist())
            return ordinary
        # A failed/rejected assignment is replanned by the original supplier.
        # The executed fallback is a relay return, never a new exploration bid.
        self.placement_goal=None
        route,goal=GreedyMappingDrone._plan_route(self,step,True,peer_goals)
        self._deployment_hold=goal is None
        self._deployment_event('RETURN_FOR_PLAN'if goal is not None else'HOLD_NO_KNOWN_RETURN',step,
                               target=None if goal is None else np.asarray(goal).tolist())
        return route,goal

    def _maybe_place(self,command,step,semantic):
        if not self._latch_deployment(step):return
        return super()._maybe_place(command,step,semantic)

    def control(self):
        command=super().control()
        if self.deployment_started is None or self.submitted or self.pose is None:return command
        step=int(self.elapsed_timestep)
        if step<self.escape_until or command.get('place_bomb',0):return command
        if not(self._deployment_hold or(not self.waypoints and self.placement_goal is None)):return command
        velocity=self.measured_velocity()
        if velocity is None or not np.isfinite(velocity).all():velocity=np.zeros(2)
        c,s=math.cos(self.heading),math.sin(self.heading)
        command.update(forward=float(np.clip(-(velocity[0]*c+velocity[1]*s)/5.5,-1,1)),
                       lateral=float(np.clip(-(-velocity[0]*s+velocity[1]*c)/5.5,-1,1)),
                       rotation=0.,grasper=0,place_bomb=0)
        return command

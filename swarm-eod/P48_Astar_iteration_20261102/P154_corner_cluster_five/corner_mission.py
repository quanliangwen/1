"""Carry a coverage-guarded cluster objective through actual fleet messages."""
import hashlib
import json
import numpy as np

def plan_signature(plan):
    try:
        epoch,leader,plans=plan
        data=[int(epoch),int(leader),[(int(k),int(n),[np.asarray(p,float).tolist()for p in goals])for k,(n,goals)in sorted(plans.items())]]
        return hashlib.sha256(json.dumps(data,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    except (TypeError,ValueError,KeyError,OverflowError):return None

class CornerMissionMixin:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.corner_context=None
        self.corner_commitments=0

    def _build_fleet_plan(self,step):
        result=super()._build_fleet_plan(step)
        plan=self.fleet_plan;audit=getattr(self.memory,'corner_cluster_diagnostics',{})
        if(plan is not None and plan[0]==step and plan[1]==int(self.identifier or 0)
                and audit.get('accepted')and audit.get('step')==step):
            self.corner_context=dict(epoch=plan[0],leader=plan[1],signature=plan_signature(plan),anchor=audit['anchor'],
                                     radius=audit['radius'],coverage_ratio=audit['coverage_ratio'])
        return result

    def define_message_for_all(self):
        result=super().define_message_for_all()
        result['corner_cluster_v1']=self.corner_context
        return result

    def _valid_corner_context(self,context,step):
        try:
            plan=self.fleet_plan
            if plan is None or not isinstance(context,dict):return False
            if not 0<=step-plan[0]<self.PLAN_FRESH_STEPS:return False
            if context['epoch']!=plan[0]or context['leader']!=plan[1]or context['signature']!=plan_signature(plan):return False
            anchor=np.asarray(context['anchor'],float);radius=float(context['radius']);ratio=float(context['coverage_ratio'])
            if anchor.shape!=(2,)or not np.isfinite(anchor).all()or not np.isfinite([radius,ratio]).all():return False
            return radius>0 and abs(radius-2.*self.blast_radius)<1e-8 and .9-1e-8<=ratio
        except (TypeError,ValueError,KeyError,OverflowError):return False

    def _messages(self):
        result=super()._messages();step=int(self.elapsed_timestep)
        if self._valid_corner_context(self.corner_context,step):return result
        self.corner_context=None
        for _,msg in self.communicator.received_messages:
            if not isinstance(msg,dict)or msg.get('kind')!='greedy-map-v1':continue
            sender,sent=msg.get('id'),msg.get('step')
            if sender not in self.last_peer_step or self.last_peer_step[sender]!=sent:continue
            context=msg.get('corner_cluster_v1')
            if self._valid_corner_context(context,step):self.corner_context=dict(context);break
        return result

    def _should_defer_commitment(self,loss,remaining,execution,probe,completion_value,step):
        # Original opportunity regret has no cluster objective. Only honour
        # the intentionally clustered point in this exact accepted joint plan.
        if self._valid_corner_context(self.corner_context,step)and self.placement_goal is not None:
            record=self.fleet_plan[2].get(int(self.identifier or 0))
            if record is not None:
                original,goals=record;index=max(0,int(original)-int(self.carried_bombs_count()))
                if index<len(goals):
                    target=np.asarray(goals[index],float)
                    if(np.linalg.norm(target-self.placement_goal)<1e-8 and
                            np.linalg.norm(target-np.asarray(self.corner_context['anchor']))<=self.corner_context['radius']+1e-8):
                        self.corner_commitments+=1
                        if self.corner_commitments<=12:
                            print('[CORNER_COMMIT] '+json.dumps(dict(owner=int(self.identifier or 0),step=int(step),target=target.tolist(),
                                  epoch=self.fleet_plan[0],anchor=self.corner_context['anchor'],radius=self.corner_context['radius'],
                                  coverage_ratio=self.corner_context['coverage_ratio']),separators=(',',':')),flush=True)
                        return False
        return super()._should_defer_commitment(loss,remaining,execution,probe,completion_value,step)

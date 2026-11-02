"""Fixed initial-stock quota and checked route suffix carry through messages."""
import hashlib,json
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
        self.corner_context=None;self.corner_commitments=0;self._corner_audit_count=0

    def _reserved_first_goals(self,step,active):
        reserved=super()._reserved_first_goals(step,active)
        state=getattr(self.memory,'corner_policy_state',None)
        if state is not None:
            state['reserved']={k:p.copy()for k,p in reserved.items()}
            previous={}
            if self.fleet_plan is not None and 0<=step-self.fleet_plan[0]<self.PLAN_FRESH_STEPS:
                for k,(_,inventory)in active.items():
                    record=self.fleet_plan[2].get(k)
                    if record is None:continue
                    initial,goals=record;index=max(0,int(initial)-inventory)
                    suffix=[np.asarray(p,float).copy()for p in goals[index:]]
                    if k in reserved:
                        if not suffix or np.linalg.norm(suffix[0]-reserved[k])>1e-8:continue
                        suffix=suffix[1:]
                    previous[k]=suffix
            state['previous_suffix']=previous
        return reserved

    def _build_fleet_plan(self,step):
        own_initial=int(self.initial_inventory or 0)
        # Official public team size and this drone's actual initial capacity;
        # never a sum of only currently fresh peer inventories.
        state=dict(initial_total=own_initial*int(self.team_size),confirmed=[p.copy()for p in self.drop_records.values()],reserved={},previous_suffix={})
        self.memory.corner_policy_state=state
        previous=self.fleet_plan
        result=super()._build_fleet_plan(step)
        plan=self.fleet_plan;audit=getattr(self.memory,'corner_cluster_diagnostics',{})
        issued=plan is not None and plan is not previous and plan[0]==step and plan[1]==int(self.identifier or 0)
        if issued:
            self.corner_context=None
            if audit.get('accepted')and audit.get('step')==step:
                self.corner_context=dict(epoch=plan[0],leader=plan[1],signature=plan_signature(plan),pivot=audit['corner'],anchor=audit['anchor'],radius=audit['radius'],coverage_ratio=audit['coverage_ratio'],initial_total=state['initial_total'],target_total=int(np.ceil(.6*state['initial_total'])))
            if self._corner_audit_count<40:
                self._corner_audit_count+=1
                print('[CORNER_PLAN_CHAIN] '+json.dumps(dict(owner=int(self.identifier or 0),step=step,signature=plan_signature(plan),accepted=bool(self.corner_context),state=dict(initial_total=state['initial_total'],reserved={k:np.asarray(p).tolist()for k,p in state['reserved'].items()},confirmed=[np.asarray(p).tolist()for p in state['confirmed']]),plans={k:[n,[np.asarray(p).tolist()for p in goals]]for k,(n,goals)in plan[2].items()}),separators=(',',':')),flush=True)
        return result

    def define_message_for_all(self):
        result=super().define_message_for_all();result['corner_cluster_v2']=self.corner_context;return result

    def _valid_corner_context(self,context,step):
        try:
            plan=self.fleet_plan
            if plan is None or not isinstance(context,dict):return False
            if not 0<=step-plan[0]<self.PLAN_FRESH_STEPS:return False
            if context['epoch']!=plan[0]or context['leader']!=plan[1]or context['signature']!=plan_signature(plan):return False
            anchor=np.asarray(context['anchor'],float);radius=float(context['radius']);ratio=float(context['coverage_ratio'])
            if anchor.shape!=(2,)or not np.isfinite(anchor).all()or not np.isfinite([radius,ratio]).all():return False
            pivot=np.asarray(context['pivot'],float)
            if pivot.shape!=(2,)or not np.isfinite(pivot).all():return False
            initial=int(self.initial_inventory or 0)*int(self.team_size)
            return initial>0 and context['initial_total']==initial and context['target_total']==int(np.ceil(.6*initial)) and abs(radius-2.*self.blast_radius)<1e-8 and .7-1e-8<=ratio
        except (TypeError,ValueError,KeyError,OverflowError):return False

    def _messages(self):
        result=super()._messages();step=int(self.elapsed_timestep)
        if self._valid_corner_context(self.corner_context,step):return result
        self.corner_context=None
        for _,msg in self.communicator.received_messages:
            if not isinstance(msg,dict)or msg.get('kind')!='greedy-map-v1':continue
            sender,sent=msg.get('id'),msg.get('step')
            if sender not in self.last_peer_step or self.last_peer_step[sender]!=sent:continue
            context=msg.get('corner_cluster_v2')
            if self._valid_corner_context(context,step):
                self.corner_context=dict(context)
                self.memory.corner_cluster_anchor=tuple(context['pivot'])+tuple(context['anchor'])
                break
        return result

    def _should_defer_commitment(self,loss,remaining,execution,probe,completion_value,step):
        if self._valid_corner_context(self.corner_context,step)and self.placement_goal is not None:
            record=self.fleet_plan[2].get(int(self.identifier or 0))
            if record is not None:
                original,goals=record;index=max(0,int(original)-int(self.carried_bombs_count()))
                if index<len(goals):
                    target=np.asarray(goals[index],float)
                    if np.linalg.norm(target-self.placement_goal)<1e-8 and np.linalg.norm(target-np.asarray(self.corner_context['anchor']))<=self.corner_context['radius']+1e-8:
                        self.corner_commitments+=1
                        return False
        return super()._should_defer_commitment(loss,remaining,execution,probe,completion_value,step)

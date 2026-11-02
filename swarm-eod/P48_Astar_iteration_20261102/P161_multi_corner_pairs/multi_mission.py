"""Carry 2--3-bomb corner bundles via actual signed fleet messages."""
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
        super().__init__(*args,**kwargs);self.corner_context=None;self.corner_commitments=0;self._corner_audit_count=0
    def _reserved_first_goals(self,step,active):
        reserved=super()._reserved_first_goals(step,active);state=getattr(self.memory,'corner_policy_state',None)
        if state is not None:
            state['reserved']={k:p.copy()for k,p in reserved.items()};previous={}
            if self.fleet_plan is not None and 0<=step-self.fleet_plan[0]<self.PLAN_FRESH_STEPS:
                for k,(_,inventory)in active.items():
                    record=self.fleet_plan[2].get(k)
                    if record is None:continue
                    initial,goals=record;index=max(0,int(initial)-inventory);suffix=[np.asarray(p,float).copy()for p in goals[index:]]
                    if k in reserved:
                        if not suffix or np.linalg.norm(suffix[0]-reserved[k])>1e-8:continue
                        suffix=suffix[1:]
                    previous[k]=suffix
            state['previous_suffix']=previous
        return reserved
    def _build_fleet_plan(self,step):
        state=dict(initial_total=int(self.initial_inventory or 0)*int(self.team_size),confirmed=[p.copy()for p in self.drop_records.values()],reserved={},previous_suffix={},regions=list(getattr(self.memory,'multi_corner_regions',[])))
        self.memory.corner_policy_state=state;previous=self.fleet_plan;result=super()._build_fleet_plan(step)
        plan=self.fleet_plan;audit=getattr(self.memory,'multi_corner_diagnostics',{})
        if plan is not None and plan is not previous and plan[0]==step and plan[1]==int(self.identifier or 0):
            self.corner_context=None
            if audit.get('accepted')and audit.get('step')==step:self.corner_context=dict(epoch=plan[0],leader=plan[1],signature=plan_signature(plan),regions=audit['regions'],coverage_ratio=audit['coverage_ratio'],initial_total=state['initial_total'])
            if self._corner_audit_count<40:
                self._corner_audit_count+=1
                data=dict(owner=int(self.identifier or 0),step=int(step),accepted=bool(self.corner_context),regions=[]if self.corner_context is None else self.corner_context['regions'],plans={k:[int(n),[np.asarray(p).tolist()for p in goals]]for k,(n,goals)in plan[2].items()},reserved={k:np.asarray(p).tolist()for k,p in state['reserved'].items()},rejections={k:[int(ts),int(q),np.asarray(p).tolist(),int(until)]for k,(ts,q,p,until)in self.assignment_rejections.items()})
                print('[MULTI_PLAN] '+json.dumps(data,separators=(',',':')),flush=True)
        return result
    def define_message_for_all(self):
        result=super().define_message_for_all();result['multi_corner_v1']=self.corner_context;return result
    def _valid_corner_context(self,context,step):
        try:
            plan=self.fleet_plan
            if plan is None or not isinstance(context,dict)or not 0<=step-plan[0]<self.PLAN_FRESH_STEPS:return False
            if context['epoch']!=plan[0]or context['leader']!=plan[1]or context['signature']!=plan_signature(plan):return False
            initial=int(self.initial_inventory or 0)*int(self.team_size)
            if context['initial_total']!=initial or initial<=0 or not np.isfinite(context['coverage_ratio'])or context['coverage_ratio']<.7-1e-8:return False
            regions=context['regions'];anchors=[]
            if not 2<=len(regions)<=min(5,initial//2):return False
            for r in regions:
                p=np.asarray(r['anchor'],float);pivot=np.asarray(r['pivot'],float)
                if p.shape!=(2,)or pivot.shape!=(2,)or not np.isfinite(p).all()or not np.isfinite(pivot).all():return False
                if abs(float(r['radius'])-self.blast_radius)>1e-8 or not 2<=int(r['planned_count'])<=3:return False
                if r['kind']not in ['inner','outer']:return False
                if any(np.linalg.norm(p-q)<2*self.blast_radius+40.+.71*self.memory.CELL-1e-8 for q in anchors):return False
                anchors.append(p)
            return True
        except (TypeError,ValueError,KeyError,OverflowError):return False
    def _messages(self):
        result=super()._messages();step=int(self.elapsed_timestep)
        if self._valid_corner_context(self.corner_context,step):return result
        self.corner_context=None
        for _,message in self.communicator.received_messages:
            if not isinstance(message,dict)or message.get('kind')!='greedy-map-v1':continue
            sender,sent=message.get('id'),message.get('step')
            if sender not in self.last_peer_step or self.last_peer_step[sender]!=sent:continue
            context=message.get('multi_corner_v1')
            if self._valid_corner_context(context,step):
                self.corner_context=dict(context);self.memory.multi_corner_regions=list(context['regions']);break
        return result
    def _should_defer_commitment(self,loss,remaining,execution,probe,completion_value,step):
        if self._valid_corner_context(self.corner_context,step)and self.placement_goal is not None:
            record=self.fleet_plan[2].get(int(self.identifier or 0))
            if record is not None:
                original,goals=record;index=max(0,int(original)-int(self.carried_bombs_count()))
                if index<len(goals):
                    target=np.asarray(goals[index],float)
                    if np.linalg.norm(target-self.placement_goal)<1e-8 and any(np.linalg.norm(target-np.asarray(r['anchor']))<=r['radius']+1e-8 for r in self.corner_context['regions']):self.corner_commitments+=1;return False
        return super()._should_defer_commitment(loss,remaining,execution,probe,completion_value,step)

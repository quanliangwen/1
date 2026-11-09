"""I001: fresh S10 plus CVaR/Gamma candidates; no extra final hard gate."""
import time
from s10_kernel import StrictSolver as S10Solver
from risk_models import RiskProposals

class StrictSolver(S10Solver):
    def __init__(self,*args,**kwargs):
        self.risk_method=kwargs.pop('risk_method','mix');self.phase_seconds=float(kwargs.pop('phase_seconds',180))
        self.extension_record=dict(method=self.risk_method,phase_budget=self.phase_seconds,phase_status='not_started');self._base_running=False
        super().__init__(*args,**kwargs)
    def shortlist(self):return sorted(self.pool.values(),key=lambda r:(r['cost'],r['selection']))
    def save(self,status):
        if self._base_running and status=='completed':status='running'
        return super().save(status)
    def run(self):
        self._base_running=True;super().run();self._base_running=False
        self.extension_record.update(base_seconds=time.monotonic()-self.start,base_pool=len(self.pool),phase_status='running');start=time.monotonic()
        if self.inst.m>5 and self.best is not None and self.risk_method!='none':
            if self.risk_method in ['cvar','gamma']:
                model=RiskProposals(self,self.phase_seconds);getattr(model,self.risk_method)();self.extension_record['risk']=model.summary()
            elif self.risk_method=='mix':
                g=RiskProposals(self,self.phase_seconds*.4);g.gamma();self.extension_record['gamma']=g.summary()
                c=RiskProposals(self,max(0.,self.phase_seconds-(time.monotonic()-start)));c.cvar();self.extension_record['cvar']=c.summary()
            else:raise ValueError('Unregistered robust method')
        self.extension_record.update(phase_status='completed',extension_seconds=time.monotonic()-start,final_pool=len(self.pool),all_certified_points_retained=True)
        if self.best is not None:self.final_check()
        self.save('completed')

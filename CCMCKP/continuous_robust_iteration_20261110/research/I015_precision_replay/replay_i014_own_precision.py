"""Post-search replay of actual closure on old own unresolved points, not cold search."""
from pathlib import Path
import sys,time,json,gzip,hashlib
H=Path(__file__).resolve().parent;I=H/'iterations/I015_precision_closure';D=H/'research/I015_precision_replay';D.mkdir(exist_ok=True);out=D/'RESULT.json';regfile=D/'REGISTRATION.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();sys.path[:0]=[str(I/'candidate'),str(I/'vendor313')]
from instance import load_instance
from exact_oracle import ExactOracle
from precision_closure import run_precision_closure
if out.exists() or regfile.exists():raise RuntimeError('Inspect registered replay instead of rerun')
file=H/'iterations/I014_hybrid_cdf_blocks/engineering39/result.json.gz';old=json.loads(gzip.decompress(file.read_bytes()));diag=json.load(open(H/'research/raw_precision/I014_UNRESOLVED_DIAGNOSTIC.json'));source={p.name:sha(p) for p in (I/'candidate').glob('*.py')};manifest=json.load(open(I/'SOURCE_MANIFEST.json'));meta=json.load(open(str(file)+'.run.json'));P=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/old['instance'];ref=json.load(open(H/'RAW_REFERENCE.json'))
if diag['result_sha256']!=sha(file) or source!=manifest['source_sha256']:raise RuntimeError('Replay source/own proposals changed')
for name,digest in meta['input_sha256'].items():
 if sha(P/name)!=digest or ref[str(P/name)]!=digest:raise RuntimeError('Original sample input changed')
seconds=max(0.,180.-old['extension']['extension_seconds']);reg=dict(time=time.time(),scope='post-search actual-module replay on four saved own I014 unresolved proposals with only original leftover180second phase; not new independent cold search or30-run Avg',old_result_sha256=sha(file),diagnostic_sha256=sha(H/'research/raw_precision/I014_UNRESOLVED_DIAGNOSTIC.json'),source_sha256=source,driver_sha256=sha(Path(__file__)),available_seconds=seconds,original_phase_seconds=180.,original_phase_used=old['extension']['extension_seconds'],queue_filter='all four own unresolved, no history/true-model or cost-scalar filter')
with regfile.open('x') as f:json.dump(reg,f,indent=2)
class Solver:
 def __init__(self):
  self.inst=load_instance(P);self.oracle=ExactOracle(self.inst,old['capacity'],'.99');self.pool={tuple(r['selection']):r for r in old['candidate_shortlist']};self.decisions={tuple(r['selection']):r['decision'] for r in diag['unresolved']};self.native_cache={};self.deadline=time.monotonic()+seconds
 def cost_of(self,q):return self.inst.selection_cost(q)
 def accept(self,q,source,c):
  if 100*int(c['lower_numerator'])<99*int(c['denominator']):raise ArithmeticError('Original raw99 required')
  self.pool[q]=dict(selection=list(q),cost=self.cost_of(q),certificate=c,source=source);self.decisions[q]=c;self.native_cache[q]=c['lower']
s=Solver();initial=set(s.pool);tick=time.monotonic();result=run_precision_closure(s,seconds,phase_started=tick);added=[s.pool[q] for q in sorted(set(s.pool)-initial)];r=dict(scope=reg['scope'],registration_sha256=sha(regfile),available_seconds=seconds,source_sha256=source,closure=result,added_records=added,new_MC_calls=0,uses_saved_vectors_for_external_replay_only=True,not_cold_solver_performance=True)
with out.open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(dict(scope=r['scope'],available_seconds=seconds,actual_seconds=result['closure_seconds'],accepted=result['accepted'],refuted=result['refuted'],unresolved=result['unresolved_remaining'],within_budget=result['phase_within_budget'],new_integer_calls=result['new_integer_calls'],admission_skips=result['admission_skips'],added_costs=[v['cost'] for v in added])),flush=True)

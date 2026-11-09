"""Posthoc finite-ambiguity guidance on saved controls, never an optimizer run."""
from pathlib import Path
import sys,hashlib,json,time
import numpy as np
H=Path(__file__).resolve().parent;I=H/'iterations/I015_precision_closure';D=H/'research/bootstrap_ambiguity';out=D/'CONTROL_DIAGNOSTIC.json';regfile=D/'CONTROL_REGISTRATION.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();sys.path[:0]=[str(I/'candidate'),str(I/'vendor313')]
from instance import load_instance
from bootstrap_cdf_models_v1 import bootstrap_models,robust_gradients
if out.exists() or regfile.exists():raise RuntimeError('Inspect registered control diagnosis instead of rerun')
math=json.load(open(D/'MATH_CHECK.json'))
if not math['passed'] or math['source_sha256']['bootstrap_cdf_models_v1.py']!=sha(H/'bootstrap_cdf_models_v1.py'):raise RuntimeError('Checked ambiguity model required')
old=json.load(open(H/'iterations/I002_cdf_neighborhood/pilot_validation/cdf_lns_39_seed970201.json.gz.post.json'))['selected'];prior=json.load(open(H/'research/D001_isolated_precision_LSS/REGISTRATION.json'));cases=[dict(label='I002_existing_qualified',selection=old['selection'],cost=old['cost'])]
for r in prior['tasks']:
 if r['index']==39:cases.append(dict(label='D001_posthoc_case39',selection=r['identity']['selection'],cost=r['cost']))
reg=dict(time=time.time(),scope='posthoc guidance diagnosis on saved known positive/negative controls; not independent cold search or predictive/performance evidence; probability labels joined only after sample-model scores',cases=cases,bins=2048,bootstrap_scenarios=4,seed=711016,source_sha256={n:sha(H/n) for n in ['bootstrap_cdf_models_v1.py','diagnose_bootstrap_guidance.py']})
with regfile.open('x') as f:json.dump(reg,f,indent=2)
P=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/APP_50_10_500_');meta=json.load(open(I/'engineering39/result.json.gz.run.json'));rawref=json.load(open(H/'RAW_REFERENCE.json'))
for n,digest in meta['input_sha256'].items():
 if sha(P/n)!=digest or rawref[str(P/n)]!=digest:raise RuntimeError('Original raw observations changed')
inst=load_instance(P);start=time.monotonic();models,overflow,construction=bootstrap_models(inst.samples,91.,reg['bins'],reg['bootstrap_scenarios'],reg['seed']);model_seconds=time.monotonic()-start;rows=[]
for r in cases:
 q=inst.validate_selection(r['selection']);tick=time.monotonic();worst,ps,w=robust_gradients([np.array(g) for g in inst.groups],models,q)
 rows.append(dict(r,nominal_grid_CDF=float(ps[0]),bootstrap_grid_CDFs=ps[1:].tolist(),worst_grid_CDF=worst,nominal_to_worst_drop=float(ps[0]-worst),gradient_seconds=time.monotonic()-tick))
# Join original external labels after all sample-only models/scores are built.
receipts={r['key']:H/'research/D001_isolated_precision_LSS/receipts'/(r['key']+'.json') for r in prior['tasks']}
for r in rows:
 identity=dict(instance=inst.name,capacity=91.,selection=r['selection'],seed=832273,draws=10000000,event='sum<=T');key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();file=receipts.get(key,H/'lss_cache'/(key+'.json'));v=json.load(open(file))
 if any(v[k]!=x for k,x in identity.items()) or v['passed']!=(v['real_probability']>=.985):raise RuntimeError('External control identity differs')
 r.update(external_original_LSS_point=v['real_probability'],external_qualified=v['passed'],external_receipt_sha256=sha(file))
result=dict(scope=reg['scope'],rows=rows,construction=construction,model_construction_seconds=model_seconds,total_seconds=time.monotonic()-start,model_array_bytes=models.nbytes,overflow_array_bytes=overflow.nbytes,all_rows_scored_before_label_join=True,no_new_MC=True,no_acceptance_gate=True,registration_sha256=sha(regfile))
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ['rows','construction']}));print(json.dumps([{k:v for k,v in r.items() if k!='selection'} for r in rows]))

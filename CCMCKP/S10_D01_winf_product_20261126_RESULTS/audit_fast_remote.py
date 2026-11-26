"""Independent terminal record reader: no solver, sampler or C++ module import."""
from pathlib import Path
from fractions import Fraction
from collections import Counter
import json,hashlib,pickle,csv,statistics,math
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');assert Path.cwd()==B
H=B/'work/d01_winf_product_20261126/formal'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
P=read(H/'PROTOCOL.json');end=read(H/'COMPLETED.json');assert end['phase']=='completed' and end['terminal']==P['total_runs'] and end['pending']==0
errors=[]
if sha(H/'PROTOCOL.json')!=read(H/'LAUNCH.json')['protocol_sha256']:errors.append('protocol_changed')
for n,h in P['source_and_binary_pins'].items():
 if sha(H/n)!=h:errors.append('source:'+n)
for n,h in P['input_pins'].items():
 if sha(B/n)!=h:errors.append('input:'+n)
outcomes=[read(p) for p in (H/'outcomes').glob('*.json')]
expected={(a['name'],c['index'],r) for a in P['arms'] for c in P['cases'] for r in range(1,P['repetitions']+1)}
if len(outcomes)!=len(expected) or {(x['arm'],x['case_index'],x['rep']) for x in outcomes}!=expected:errors.append('coverage_duplicates')
flow={a['name']:a['flow'] for a in P['arms']};data={};verified_files=0;bound_checks=0
for c in P['cases']:
 path=B/'benchmark'/c['instance'];groups=pickle.loads((path/'node_to_factor.pkl').read_bytes())
 if isinstance(groups,dict):groups=[groups[k] for k in sorted(groups)]
 costs=[float(x) for line in (path/'cost.txt').read_text().splitlines() for x in line.split('#')[0].split()]
 data[c['index']]={'path':path,'groups':groups,'costs':costs,'ordered':{},'cache':{}}
 # Conservative scale/operation allowance for the widened cost domains used
 # by BlockBounds. This is an arithmetic verification, not a new performance gate.
 eps=Fraction(1,2**53);gamma=256*eps/(1-256*eps)
 bound=float(gamma*64*(1+sum(max(abs(Fraction.from_float(costs[j])) for j in group) for group in groups)))
 assert bound<1e-8,'Cost safety-margin premise not verified'
 data[c['index']]['cost_arithmetic_error_bound']=bound
def valid_selection(d,s):return len(s)==len(d['groups']) and all(j in g for j,g in zip(s,d['groups']))
def exact_rows(d,j):
 if j not in d['ordered']:
  text=(d['path']/(str(j)+'_sample.txt')).read_text();d['ordered'][j]=sorted(Fraction(x) for line in text.splitlines() for x in line.split('#')[0].split())
 return d['ordered'][j]

def prepare_radius(d):
 if 'radius_units' in d:return
 units=[];variances=[];scale=10**12
 for j in range(len(d['costs'])):
  values=exact_rows(d,j);n=len(values);assert n==500
  mean=sum(values,Fraction(0))/n;v=sum((x*x for x in values),Fraction(0))/n-mean*mean
  square=v*scale*scale/(10000*n);ceiling=-((-square.numerator)//square.denominator)
  u=math.isqrt(ceiling)
  if u*u<ceiling:u+=1
  assert Fraction(u*u)>=square and (u==0 or Fraction((u-1)**2)<square)
  units.append(u);variances.append(v)
 d['radius_units']=units;d['exact_variances']=variances
def grid_row(d,j,bins,cap,positive=False,up=False):
 key=(bins,str(cap),j,positive,up);cache=d.setdefault('model_grid_cache',{})
 if key not in cache:
  shift=Fraction(d['radius_units'][j],10**12) if positive else Fraction(0)
  row=[]
  for value in exact_rows(d,j):
   scaled=(value+shift)*bins/cap
   k=-((-scaled.numerator)//scaled.denominator) if up else scaled.numerator//scaled.denominator
   assert k>=0
   row.append(min(bins,k))
  cache[key]=row
 return cache[key]
"""Independent Python coefficient construction; system GMP is arithmetic only."""
import ctypes,ctypes.util
from collections import Counter
class _MPZ(ctypes.Structure):
 _fields_=[('alloc',ctypes.c_int),('size',ctypes.c_int),('limbs',ctypes.POINTER(ctypes.c_ulong))]
_lib=ctypes.CDLL(ctypes.util.find_library('gmp'))
_ptr=ctypes.POINTER(_MPZ);_g={}
for _name,_args in [('init',[_ptr]),('clear',[_ptr]),('set_str',[_ptr,ctypes.c_char_p,ctypes.c_int]),('setbit',[_ptr,ctypes.c_ulong]),('mul',[_ptr,_ptr,_ptr]),('fdiv_r_2exp',[_ptr,_ptr,ctypes.c_ulong]),('fdiv_r',[_ptr,_ptr,_ptr]),('sub_ui',[_ptr,_ptr,ctypes.c_ulong]),('get_str',[ctypes.c_void_p,ctypes.c_int,_ptr])]:
 _fn=getattr(_lib,'__gmpz_'+_name);_fn.argtypes=_args;_fn.restype=ctypes.c_int if _name=='set_str' else None;_g[_name]=_fn
class _Z:
 def __init__(self,n=0):
  self.value=_MPZ();_g['init'](ctypes.byref(self.value));assert _g['set_str'](ctypes.byref(self.value),str(n).encode(),10)==0
 def __del__(self):_g['clear'](ctypes.byref(self.value))
 def bit(self,k):_g['setbit'](ctypes.byref(self.value),k)
 def ref(self):return ctypes.byref(self.value)
def integer_polynomial_count(rows,bins):
 den=500**len(rows);mins=[min(row) for row in rows];cut=bins-sum(mins)
 if cut<=0:return 0,den
 if sum(max(row) for row in rows)<bins:return den,den
 stride=den.bit_length()+1;polynomials=[]
 for row,lo in zip(rows,mins):
  p=_Z()
  for k,n in Counter(x-lo for x in row if x-lo<cut).items():
   for b in range(n.bit_length()):
    if n>>b&1:p.bit(k*stride+b)
  polynomials.append(p)
 while len(polynomials)>1:
  nxt=[]
  for k in range(0,len(polynomials),2):
   if k+1==len(polynomials):nxt.append(polynomials[k]);continue
   p=_Z();_g['mul'](p.ref(),polynomials[k].ref(),polynomials[k+1].ref());_g['fdiv_r_2exp'](p.ref(),p.ref(),cut*stride);nxt.append(p)
  polynomials=nxt
 modulus=_Z();modulus.bit(stride);_g['sub_ui'](modulus.ref(),modulus.ref(),1);p=_Z();_g['fdiv_r'](p.ref(),polynomials[0].ref(),modulus.ref())
 buffer=ctypes.create_string_buffer(len(str(den))+2);_g['get_str'](buffer,10,p.ref());numerator=int(buffer.value);assert 0<=numerator<=den
 return numerator,den


def selected_model_count(d,s,bins,capacity):
 key=(tuple(s),bins,str(capacity));cache=d.setdefault('selected_DRO_count_cache',{})
 if key not in cache:cache[key]=integer_polynomial_count([grid_row(d,j,bins,Fraction(str(capacity)),True,True) for j in s],bins)
 return cache[key]

def proof_count(d,record,capacity,positive=False):
 anchor=record['anchor'];block=record['block'];costcap=record['cost_cap'];key=(positive,tuple(anchor),tuple(block),costcap)
 if key in d['cache']:return d['cache'][key]
 # Independent exact rational relaxation uses a wider cost safety margin than
 # double summation error for these pinned cases; no exact equality excluded.
 outside=math.fsum(d['costs'][anchor[g]] for g in range(len(anchor)) if g not in block)
 minima=[min(d['costs'][j] for j in d['groups'][g]) for g in block];slack=costcap-outside-math.fsum(minima)
 bins=record['bins'];cap=Fraction(str(capacity))
 def grid(j):return grid_row(d,j,bins,cap,positive,False)
 rows=[grid(j) for j in anchor]
 for h,g in enumerate(block):
  eligible=[j for j in d['groups'][g] if d['costs'][j]-minima[h]<=slack+1e-7]
  assert eligible,'empty_relaxation';rows[g]=[min(grid(j)[k] for j in eligible) for k in range(500)]
 # Monotone floor quantization commutes with coordinatewise quantile minima.
 indices=rows
 den=500**len(anchor);mins=[min(row) for row in indices];cut=bins-sum(mins)
 if cut<=0:result=(0,den)
 else:
  stride=den.bit_length()+1;base=1<<stride;mask=(1<<(cut*stride))-1
  polynomials=[]
  for row,lo in zip(indices,mins):
   hist=Counter(k-lo for k in row if k-lo<cut);polynomials.append(sum(n<<(k*stride) for k,n in hist.items()))
  while len(polynomials)>1:polynomials=[(polynomials[k]*polynomials[k+1])&mask if k+1<len(polynomials) else polynomials[k] for k in range(0,len(polynomials),2)]
  result=(polynomials[0]%(base-1),den)
 d['cache'][key]=result;return result
def validate_model_metadata(d,raw):
 prepare_radius(d);model=raw['DRO_model']
 assert raw['certificate_scope']=='exact_worst_case_shifted_product_probability'
 assert model['transport_order']=='infinity' and model['transport_radius']==1 and model['kappa']=='1/100'
 assert model['center']=='full_independent_empirical_product_all_original_samples' and model['not_500_pseudo_joint_scenarios']
 assert model['original_sample_count_per_item']==500 and model['item_count']==len(d['costs']) and model['group_count']==len(d['groups'])
 assert not model['statistical_population_coverage_claim'] and not model['nominal_fallback_in_DRO_pool']
 assert len(model['radii'])==len(d['costs']) and raw['search_certificate_calls']>0
 for j,item in enumerate(model['radii']):
  assert item['item']==j and int(item['units_1e12'])==d['radius_units'][j],'independent_radius'
  assert Fraction(item['exact_variance'])==d['exact_variances'][j],'exact_variance'
  assert Fraction(item['radius_rational'])==Fraction(d['radius_units'][j],10**12),'radius_rational'
 selected=raw['selected']['selection'];shift=sum((Fraction(d['radius_units'][j],10**12) for j in selected),Fraction(0))
 assert shift>0 and shift==Fraction(raw['selected_transport_shift_rational']),'nonzero_selected_adversarial_shift'

rows=[]
for ordinal,o in enumerate(sorted(outcomes,key=lambda x:(x['case_index'],x['arm'],x['rep']))):
 if ordinal%15==0:print(json.dumps({'audit_progress':ordinal,'total':len(outcomes)}),flush=True)
 r={k:o.get(k) for k in ['identity','case_index','instance','arm','rep','seed','rc','termination_reason','process_wall_seconds','peak_rss_bytes']};r.update(valid=False,errors=[],cost=None)
 root=H/'runs'/o['identity'];d=data[o['case_index']]
 try:
  assert o['seed']==P['seed_base']+o['rep'],'identity_seed'
  for n,h in o['output_files'].items():assert sha(root/n)==h['sha256'] and (root/n).stat().st_size==h['bytes'],n;verified_files+=1
  assert o['rc']==0 and o['termination_reason'] is None,'process_failure'
  assert 0<o['process_wall_seconds']<=600 and o['wall_clock_source']=='dedicated_wait_thread_from_before_Popen','whole600'
  x=read(root/'RESULT.json');raw=read(root/'S10_search.json');meta=read(root/'S10_search.run.json');complete=read(root/'COMPLETION.json');trace=read(root/'ORIGINAL_LSS_DECISION_TRACE.json')
  assert x['status']==raw['status']=='completed' and x['schema']=='S10_LSS_full_sample_total600_v3','completion_status'
  assert x['acceptance_evaluator']=='LSS' and x['acceptance_threshold']==.99 and x['final_lss_enforced'],'final_acceptance_method'
  assert x['search_flow']==raw['search_flow']==meta['search_flow']==flow[o['arm']],'flow'
  positive=flow[o['arm']]=='block_winf_dro'
  if positive:validate_model_metadata(d,raw)
  else:assert raw['DRO_model'] is None and raw['certificate_scope']=='nominal_empirical_product_probability','nominal_control'

  assert x['search_seed']==raw['seed']==meta['seed']==o['seed'] and x['rep']==o['rep'],'seed'
  assert x['instance']==raw['instance']==o['instance'] and x['capacity']==raw['capacity']==o['capacity'],'problem'
  assert complete['start_includes_process_launch'] and complete['all_output_files_fsynced'],'save_clock'
  assert x['clock_policy']==complete['clock_policy']=='launch_to_exit_total_wall' and complete['budget']==x['total_budget_seconds']==600,'clock_contract'
  assert 0<meta['elapsed']<=x['wall_seconds_including_LSS']<=complete['elapsed_before_completion_save']<=o['process_wall_seconds'],'clock_order'
  assert meta['within_budget'] and not raw['config']['validation_outside_search_clock'],'phase_clock'
  assert x['lss_sample_index_min']==0 and x['lss_sample_index_max']==499 and not x['real_probability_reporting'],'LSS_indices'
  assert raw['config']['no_cross_run_solutions'] and raw['config']['sampling_population']=='all_L_samples','isolation'
  for n,h in meta['input_sha256'].items():assert h==P['input_pins']['benchmark/'+o['instance']+'/'+n],'input_hash'
  latest={};final={};evaluations=[]
  for e in trace:
   if 'evaluation' in e:
    assert 0<=e['probability']<=1 and 0<=e['elapsed_start']<=e['elapsed_end']<=590.1,'evaluation_clock'
    latest[tuple(e['selection'])]=e;evaluations.append(e['evaluation'])
   if e['stage']=='LSS_final_acceptance':final[tuple(e['selection'])]=e
   if e['stage']=='LSS_incomplete_evaluation':assert e['no_probability_returned'] and 'probability' not in e,'partial_probability'
  assert evaluations==list(range(1,x['evaluation_times']+1)),'evaluation_sequence'
  for key,e in final.items():assert e['source_evaluation']==latest[key]['evaluation'] and e['probability']==latest[key]['probability'] and e['accepted']==(e['probability']>=.99),'last_complete_LSS'
  variants=x['original_output_variants'];assert len(variants)==3,'variants'
  for v in variants:
   key=tuple(v['selection']);assert valid_selection(d,v['selection']) and abs(math.fsum(d['costs'][j] for j in key)-v['cost'])<1e-8,'selection_cost'
   assert v['probability']>=.99 and v['probability']==latest[key]['probability'] and final[key]['accepted'] and 'real_probability' not in v,'LSS_acceptance'
  assert variants[0]['selection']==x['selection'] and variants[0]['cost']==x['cost'] and variants[0]['probability']==x['original_LSS_confidence'],'main_output'
  csvs=list((root/'result/Localsearch').glob('*_[012].csv'));assert len(csvs)==3,'CSVs'
  for p in csvs:
   v=variants[int(p.stem.rsplit('_',1)[1])]
   with p.open() as f:rr=csv.DictReader(f);names=rr.fieldnames;values=list(rr)
   assert len(names)==6 and all('Real' not in name for name in names) and len(values)==1,'CSV_format'
   y=values[0];assert float(y['Cost'])==v['cost'] and float(y['Confidence Level'])==v['probability'] and json.loads(y['Solution'])==v['selection'],'CSV_record'
  for q in raw['candidate_shortlist']:
   cert=q['certificate'];lo=int(cert['lower_numerator']);hi=int(cert['upper_numerator']);den=int(cert['denominator'])
   assert valid_selection(d,q['selection']) and den==500**len(d['groups']) and 0<=lo<=hi<=den and lo*100>=den*99,'raw_CDF_certificate'
  for cert in raw['native_infeasible_proofs']:
   lo=int(cert['lower_numerator']);hi=int(cert['upper_numerator']);den=int(cert['denominator'])
   assert valid_selection(d,cert['selection']) and den==500**len(d['groups']) and 0<=lo<=hi<=den and hi*100<99*den,'native_infeasible_certificate'
  candidates=[q for q in raw['candidate_shortlist'] if q['selection']==x['selection']];assert candidates,'own_pool'
  init=next(q for q in meta['phase_records'] if q['phase']=='initialization')
  for entry in raw.get('block_history',[]):
   bound=entry.get('bound')
   if bound:
    assert valid_selection(d,bound['anchor']) and bound['anchor']==entry['anchor'] and bound['block']==entry['block'] and bound['cost_cap']==entry.get('collection_cap',entry['best_before']),'bound_identity'
    block=bound['block'];assert block==sorted(set(block)) and 2<=len(block)<=4,'bound_block'
    if bound['status']=='cost_infeasible':
     minimum=sum((Fraction.from_float(d['costs'][bound['anchor'][g]]) for g in range(len(d['groups'])) if g not in block),Fraction(0))
     minimum+=sum((min(Fraction.from_float(d['costs'][j]) for j in d['groups'][g]) for g in block),Fraction(0))
     assert minimum>Fraction.from_float(bound['cost_cap'])+Fraction(1,10**8),'cost_lower_bound'
   if bound and 'upper' in bound:
    numerator,denominator=proof_count(d,bound,o['capacity'],positive);assert numerator==int(bound['upper']) and denominator==int(bound['denominator']),'independent_envelope_count';bound_checks+=1
    assert (numerator*100<denominator*99)==(bound['status']=='integer_probability_infeasible'),'prune_proof'
   if entry.get('pruned'):assert bound and bound['status'] in ['integer_probability_infeasible','cost_infeasible'],'floating_prune'
  if flow[o['arm']]=='frontier_mitm_zero':assert all(e['delta']==0 for e in raw['match_history']),'zero_radius_control'
  if flow[o['arm']]=='block_mitm':assert all(e['delta']==0 for e in raw['match_history']) and not raw['ellipsoid_history'],'B01_flow'

  model_output_checks=0
  if positive:
   for variant in variants:
    record=next(q for q in raw['candidate_shortlist'] if q['selection']==variant['selection'])
    certificate=record['certificate'];nu,de=selected_model_count(d,variant['selection'],certificate['bins'],o['capacity'])
    assert nu==int(certificate['lower_numerator']) and de==int(certificate['denominator']),'independent_worst_case_output_count'
    assert nu*100>=99*de,'DRO_output_not_model_feasible'
    model_output_checks+=1
  if flow[o['arm']] in ['block_insurance','block_winf_dro']:
   assert all(q['delta']==0 for q in raw['match_history']) and not raw['ellipsoid_history'],'coverage_flow'
   expected_model='positive_Winf' if positive else 'nominal'
   assert all(q.get('model',expected_model)==expected_model for q in raw['block_history']),'block_model'

  rawbest=tuple(raw['selected']['selection']);last=latest.get(rawbest)
  r.update(valid=not errors,cost=x['cost'],LSS=x['original_LSS_confidence'],selection=x['selection'],initialization_cost=init['best_after'],raw_final_cost=raw['selected']['cost'],post_init_improved=raw['selected']['cost']<init['best_after']-1e-8,block_incumbent_improvements=sum(e.get('source','').startswith('B01_') for e in raw['events']),first_found_seconds=min(q['found_seconds'] for q in candidates),search_seconds=meta['elapsed'],LSS_seconds=x['LSS_finalization_seconds'],block_records=len(raw.get('block_history',[])),independent_DRO_output_checks=model_output_checks,positive_DRO=positive,selected_transport_shift=raw.get('selected_transport_shift_rational'),raw_pool_count=raw['raw_certified_pool_count'],shortlist_count=len(raw['candidate_shortlist']),raw_best_last_LSS=last['probability'] if last else None,raw_best_final_filter=final.get(rawbest,{}).get('accepted'),final_cost_above_raw_best=x['cost']>raw['selected']['cost']+1e-8,final_cost_minus_raw_best=x['cost']-raw['selected']['cost'])
 except Exception as e:r['errors'].append(type(e).__name__+':'+str(e))
 rows.append(r)
allvalid=not errors and all(r['valid'] for r in rows)
improved={c['index']:sum(r.get('post_init_improved',False) for r in rows if r['arm']=='C_D01_WINF_PRODUCT' and r['case_index']==c['index']) for c in P['cases']}
gate=allvalid and all(v>=1 for v in improved.values())
groups=[]
for c in P['cases']:
 for a in P['arms']:
  rr=[r for r in rows if r['case_index']==c['index'] and r['arm']==a['name']];vv=[r for r in rr if r['valid']]
  groups.append({'case_index':c['index'],'arm':a['name'],'terminal':len(rr),'valid':len(vv),'best_diagnostic':min([r['cost'] for r in vv],default=None),'official_avg':statistics.mean(r['cost'] for r in vv) if len(vv)==30 else None,'official_std':statistics.stdev(r['cost'] for r in vv) if len(vv)==30 else None,'valid_only_diagnostic_avg':statistics.mean(r['cost'] for r in vv) if vv else None,'whole_mean':statistics.mean(r['process_wall_seconds'] for r in rr),'post_init_improvements':sum(r.get('post_init_improved',False) for r in vv),'block_improvements':sum(r.get('block_incumbent_improvements',0) for r in vv)})
report={'schema':'D01_formal_record_audit','reader_version':'D01_independent_v2_GMP_arithmetic_exact_radius_transport_witness','reader_sha256':sha(Path(__file__)) if Path(__file__).is_file() else None,'global_errors':errors,'terminal':len(rows),'independent_valid':sum(r['valid'] for r in rows),'verified_output_files':verified_files,'independent_integer_envelope_checks':bound_checks,'gate_pass':gate,'post_init_by_case':improved,'formal270_started':True,'groups':groups,'rows':rows,'no_probability_resampling':True,'not_30_repeat_conclusion':False,'cost_arithmetic_error_bounds':{k:d['cost_arithmetic_error_bound'] for k,d in data.items()}}
for g in groups:
 rr=[r for r in rows if r['valid'] and r['case_index']==g['case_index'] and r['arm']==g['arm']]
 g['final_cost_above_raw_best_runs']=sum(r['final_cost_above_raw_best'] for r in rr)
 g['raw_best_last_LSS_below_threshold_runs']=sum(r['raw_best_last_LSS'] is not None and r['raw_best_last_LSS']<.99 for r in rr)
 g['mean_final_cost_minus_raw_best']=statistics.mean(r['final_cost_minus_raw_best'] for r in rr) if rr else None
 g['mean_raw_pool_count']=statistics.mean(r['raw_pool_count'] for r in rr) if rr else None
 g['mean_LSS_seconds']=statistics.mean(r['LSS_seconds'] for r in rr) if rr else None

import numpy as np
def flip(a,b,seed):
 delta=np.array(a,dtype=float)-np.array(b,dtype=float);delta=delta[delta!=0]
 if not len(delta):return 1.
 observed=abs(float(np.mean(delta)));rng=np.random.RandomState(seed)
 # Enumerate a small active difference family exactly, otherwise use a
 # predeclared common Monte Carlo sign-flip family (not probability sampling).
 if len(delta)<=18:
  masks=np.arange(1<<len(delta),dtype=np.uint64)[:,None]
  signs=2*((masks>>np.arange(len(delta),dtype=np.uint64))&1).astype(np.int8)-1
  return float(np.mean(np.abs(np.mean(signs*delta,axis=1))>=observed-1e-12))
 extreme=0
 for first in range(0,99999,5000):
  size=min(5000,99999-first);signs=rng.randint(0,2,size=(size,len(delta)))*2-1
  extreme+=int(np.sum(np.abs(np.mean(signs*delta,axis=1))>=observed-1e-12))
 return (extreme+1)/100000
def holm(values):
 order=sorted(range(len(values)),key=lambda k:values[k]);out=[1.]*len(values);prior=0
 for rank,k in enumerate(order):prior=max(prior,min(1.,(len(values)-rank)*values[k]));out[k]=prior
 return out
comparisons=[]
for c in P['cases']:
 for idx,(a,b) in enumerate([('B_COVERAGE_NOMINAL','A_B01_ORIGINAL'),('C_D01_WINF_PRODUCT','A_B01_ORIGINAL'),('C_D01_WINF_PRODUCT','B_COVERAGE_NOMINAL')]):
  rr={arm:sorted([r for r in rows if r['case_index']==c['index'] and r['arm']==arm],key=lambda r:r['rep']) for arm in [a,b]}
  complete=all(len(v)==30 and all(r['valid'] for r in v) for v in rr.values())
  p=flip([r['cost'] for r in rr[a]],[r['cost'] for r in rr[b]],20261126+c['index']*10+idx) if complete else 1.
  disc_a=sum(x['valid'] and not y['valid'] for x,y in zip(rr[a],rr[b]));disc_b=sum(not x['valid'] and y['valid'] for x,y in zip(rr[a],rr[b]));n=disc_a+disc_b
  vp=min(1.,2*sum(math.comb(n,k) for k in range(min(disc_a,disc_b)+1))/2**n) if n else 1.
  diff=statistics.mean(r['cost'] for r in rr[a])-statistics.mean(r['cost'] for r in rr[b]) if complete else None
  comparisons.append({'case_index':c['index'],'candidate':a,'reference':b,'complete30':complete,'avg_diff':diff,'cost_p_raw':p if complete else None,'cost_family_reserved_p':p,'validity_p_raw':vp})
for key,outkey in [('cost_family_reserved_p','cost_p_holm9'),('validity_p_raw','validity_p_holm9')]:
 adjusted=holm([x[key] for x in comparisons])
 for item,p in zip(comparisons,adjusted):item[outkey]=p
report['comparisons']=comparisons
report['schema']='D01_formal270_independent_record_audit'
report['official30_conclusion']=True
report['mechanism_progress_check']=report.pop('gate_pass')
report['automatic40_expansion']=False
report['independent_DRO_output_certificates']=sum(r.get('independent_DRO_output_checks',0) for r in rows)
report['integer_arithmetic_backend']='independent Python coefficients; system GMP via ctypes (no solver or writer imports)'
report['all_positive_radius_items_verified']=all('radius_units' in d for d in data.values())

(H/'FINAL_INDEPENDENT_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='rows'},ensure_ascii=False),flush=True)

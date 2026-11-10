from pathlib import Path
from fractions import Fraction as F
import argparse,json,gzip,hashlib,pickle,time
from independent_raw_recount import upward_grid_count
H=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def audit(study):
 D=H/'research'/study;out=D/'INDEPENDENT_REPLAY_AUDIT.json'
 if out.exists():raise RuntimeError('No independent replay audit overwrite')
 reg=json.load(open(D/'REGISTRATION.json'));file=D/'REPLAY_RESULT.json.gz';data=json.loads(gzip.decompress(file.read_bytes()));source=H/reg['saved_own_result'];prior=json.loads(gzip.decompress(source.read_bytes()));old={tuple(r['selection']) for r in prior['candidate_shortlist']};raw=json.load(open(H/'RAW_REFERENCE.json'));P=Path(reg['benchmark']);T=F(str(reg['capacity']));B=reg['bins'];started=time.monotonic()
 if data['registration_sha256']!=sha(D/'REGISTRATION.json') or data['source_saved_result_sha256']!=sha(source) or not data['no_cold_timing_or_Avg_claim'] or data['new_original_MC_calls']!=0 or not data['old_pool_never_removed'] or data['old_complete_pool_members']!=len(old):raise RuntimeError('Replay identity/scope differs')
 for n,d in reg['input_sha256'].items():
  if sha(H/n)!=d:raise RuntimeError('Registered replay source/input changed')
 for n,d in reg['benchmark_input_sha256'].items():
  if sha(P/n)!=d or raw[str(P/n)]!=d:raise RuntimeError('Original raw input differs')
 groups=pickle.load(open(P/'node_to_factor.pkl','rb'));groups=[groups[k] for k in sorted(groups,key=int)] if isinstance(groups,dict) else groups;prices=[F(x) for x in (P/'cost.txt').read_text().split()];arrays={int(n.split('_')[0]):[F(x) for x in (P/n).read_text().split()] for n in reg['benchmark_input_sha256'] if n.endswith('_sample.txt')}
 down={j:[F((x*B/T).numerator//(x*B/T).denominator)*T/B for x in a] for j,a in arrays.items()};checked=[];seen=set()
 for r in data['records']:
  q=tuple(r['selection']);center=r['center'];pair=r['pair'];c=r['certificate']
  if q in seen or q in old or len(q)!=len(groups) or len(set(q))!=len(q) or any(j not in groups[g] for g,j in enumerate(q)) or sum(a!=b for a,b in zip(center,pair))!=2 or sum(a!=b for a,b in zip(center,q))!=3 or sum(a!=b for a,b in zip(pair,q))!=1:raise RuntimeError('Replay fresh canonical three-group relation differs')
  seen.add(q);cost=float(sum((prices[j] for j in q),F(0)));cap=float(sum((prices[j] for j in center),F(0)))
  if abs(r['cost']-cost)>1e-9 or abs(r['center_cost_cap']-cap)>1e-9 or cost>=cap-1e-7 or c['selection']!=list(q) or c['bins']!=B or not c['all_original_samples'] or c['strict_event']!='sum<T':raise RuntimeError('Replay canonical original cost/certificate differs')
  n,d=upward_grid_count([arrays[j] for j in q],T,B);u,dd=upward_grid_count([down[j] for j in q],T,B)
  classification='raw_certified' if 100*n>=99*d else 'integer_raw_refuted' if 100*u<99*d else 'unresolved'
  if (str(n),str(u),str(d))!=(c['lower_numerator'],c['upper_numerator'],c['denominator']) or d!=dd or not 0<=n<=u<=d or classification!=r['classification'] or c['accepted']!=(100*n>=99*d) or c['infeasible']!=(100*u<99*d):raise RuntimeError('Independent ceil/floor original count/classification differs')
  checked.append(dict(selection=list(q),cost=cost,classification=classification,lower_numerator=str(n),upper_numerator=str(u),denominator=str(d),lower=float(F(n,d)),upper=float(F(u,d))))
 if len(seen)!=data['unique_fresh_checked'] or len(checked)!=len(data['records']) or sum(r['classification']=='raw_certified' for r in checked)!=data['accepted_new_raw']:raise RuntimeError('Complete replay accounting differs')
 v=dict(passed=True,scope='complete posthoc own-snapshot replay; direct canonical cost/groups/three-change relation and independent original all-sample ceil AND floor count; no cold/Avg/native qualification claim',registration_sha256=sha(D/'REGISTRATION.json'),result_sha256=sha(file),checked=len(checked),accepted_new_raw=sum(r['classification']=='raw_certified' for r in checked),integer_refuted=sum(r['classification']=='integer_raw_refuted' for r in checked),unresolved=sum(r['classification']=='unresolved' for r in checked),minimum_lower=min((r['lower'] for r in checked),default=None),maximum_upper=max((r['upper'] for r in checked),default=None),new_original_MC_calls=0,seconds=time.monotonic()-started,rows=checked)
 with out.open('x') as f:json.dump(v,f,indent=2)
 print(json.dumps({k:x for k,x in v.items() if k!='rows'}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--study',choices=['third_group_repair_replay','third_group_repair_balanced_replay'],required=True);audit(p.parse_args().study)

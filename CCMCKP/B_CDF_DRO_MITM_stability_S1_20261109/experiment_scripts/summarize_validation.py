import pathlib,json,gzip,hashlib,numpy as np
H=pathlib.Path(__file__).resolve().parent;D=H/'validation';reg=json.load(open(D/'REGISTRATION.json'));cases=reg['cases'];B=pathlib.Path('/home/junhao/quan/parallel_test_solver/CCMKCP/work/codex_v50_dro_ablation_20261016/results');rows=[];problems=[]
raw_registry=json.load(open(H/'frozen/original_experiment/source_inputs.json'))
for c in cases:
 i=c['index'];old=[json.load(gzip.open(p,'rt')) for p in B.glob(f'B_CDF_DRO_MITM_{i:02d}_r*.json.gz')];oldcost=[d['selected']['cost'] for d in old if d.get('selected')];records=[];failed=[]
 for rep in range(1,6):
  stem=f'S1_{i:02d}_r{rep:02d}';side=D/(stem+'.json.gz.run.json');terminal=D/(stem+'.terminal.json')
  if not terminal.exists():continue
  term=json.load(open(terminal))
  if term['exit']!=0 or not side.exists():failed.append(rep);continue
  run=json.load(open(side));d=json.load(gzip.open(D/(stem+'.json.gz'),'rt'));sel=run['selected'];good=sel is not None and run['within_budget'] and sel['probability']>=.99 and run['source_sha256']==reg['source_sha256'] and d['status']=='completed'
  if good:
   prefix='/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance']+'/'
   expected_inputs={pathlib.Path(k).name:v for k,v in raw_registry.items() if k.startswith(prefix)}
   good=run['input_sha256']==expected_inputs
  if good:
   import pickle
   raw=pathlib.Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark')/c['instance'];cost=np.loadtxt(raw/'cost.txt');groups=pickle.load(open(raw/'node_to_factor.pkl','rb'));groups=list(groups.values()) if isinstance(groups,dict) else groups;chosen=set(sel['selection'])
   good=len(sel['selection'])==len(groups) and len(chosen)==len(groups) and all(len(chosen.intersection(g))==1 for g in groups) and abs(cost[sel['selection']].sum()-sel['cost'])<1e-8
  if not good:failed.append(rep);continue
  records.append(dict(rep=rep,seed=run['seed'],cost=sel['cost'],elapsed=run['elapsed'],found_seconds=sel['found_seconds'],probability=sel['probability'],selection=sel['selection']))
 costs=[x['cost'] for x in records];complete=len(records)==5 and not failed
 row=dict(index=i,instance=c['instance'],capacity=c['tmax'],old_n=len(oldcost),old_best=min(oldcost),old_avg=float(np.mean(oldcost)),old_std=float(np.std(oldcost,ddof=1)),old_mean_found_seconds=float(np.mean([d['selected']['found_seconds'] for d in old if d.get('selected')])),old_mean_runtime=float(np.mean([d['runtime_before_save'] for d in old])),n=len(records),failed=failed,complete=complete,new_best=min(costs) if costs else None,new_avg=float(np.mean(costs)) if complete else None,new_std=float(np.std(costs,ddof=1)) if complete else None,mean_seconds=float(np.mean([r['elapsed'] for r in records])) if complete else None,new_mean_found_seconds=float(np.mean([r['found_seconds'] for r in records])) if complete else None,runs=records)
 if complete:
  row['avg_vs_old_best_pct']=(row['new_avg']/row['old_best']-1)*100;row['avg_vs_old_avg_pct']=(row['new_avg']/row['old_avg']-1)*100;row['target_met']=row['new_avg']<=row['old_best']+1e-8
 rows.append(row)
completed=sum(r['complete'] for r in rows);valid=sum(r['n'] for r in rows);failed=sum(len(r['failed']) for r in rows)
summary=dict(schema='S1_fixed_validation_summary',required_runs=200,valid=valid,failed=failed,complete_cases=completed,target_met_cases=sum(r.get('target_met',False) for r in rows),mean_improved_cases=sum(r['complete'] and r['new_avg']<r['old_avg']-1e-8 for r in rows),mean_regressed_cases=sum(r['complete'] and r['new_avg']>r['old_avg']+1e-8 for r in rows),rows=rows)
(D/'SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k!='rows'}))
for r in rows:
 if r['complete']:print(r['index'],r['instance'],r['capacity'],'oldavg',round(r['old_avg'],6),'newavg',round(r['new_avg'],6),'oldbest',round(r['old_best'],6),'gap%',round(r['avg_vs_old_best_pct'],4),'std',round(r['new_std'],6))

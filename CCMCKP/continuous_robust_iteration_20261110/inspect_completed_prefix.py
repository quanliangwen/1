from pathlib import Path
import argparse,json,time
H=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--cohort',choices=['P016','B016'],required=True);c=p.parse_args().cohort
D=H/('research/D005_I016_pair_prefix' if c=='P016' else 'research/D006_I016_breadth_prefix');result=dict(cohort=c,time=time.time())
for n in ['LAUNCH.json','POSTPROCESS_LAUNCH.json']:
 if (D/n).exists():
  v=json.load(open(D/n));pid=v['pid'];cmd=Path('/proc')/str(pid)/'cmdline';result[n]=dict(pid=pid,live=cmd.exists(),command=cmd.read_bytes().replace(b'\0',b' ').decode() if cmd.exists() else None)
for n in ['REGISTRATION.json','PROGRESS.json','RESULT.json','POSTPROCESS_TERMINAL.json','INDEPENDENT_FINAL_AUDIT.json','DEVELOPMENT_COMPARISON.json']:
 if not (D/n).exists():continue
 try:v=json.load(open(D/n))
 except Exception:result[n]='currently being written';continue
 if n=='REGISTRATION.json':result[n]=dict(pools=len(v['pools']),catalogue=v['catalogue_unique'],unknown={k:len(x['initial_prefix']['missing_keys']) for k,x in v['pools'].items()})
 elif n in ['PROGRESS.json','RESULT.json']:
  a=v['accounting'];result[n]=dict(batch=v.get('batch'),physical=a['physical_new_attempts'],complete=a['all_prefixes_complete'],errors=v.get('errors',v.get('controller_error')),pools={k:dict(complete=x['prefix_complete'],accepted=x['accepted'],missing=len(x['missing_keys']),failed=len(x['failed_keys']),cost=x['selected']['cost'] if x['selected'] else None) for k,x in a['pools'].items()})
 elif n=='DEVELOPMENT_COMPARISON.json':result[n]=dict(summaries={k:{n:x[n] for n in ['Best','Avg','Std_population','Avg_minus_own_Best']} for k,x in v['summaries'].items()},pairs=v['paired_rows'])
 else:result[n]={k:x for k,x in v.items() if k in ['passed','error','physical_new_MC_attempts','physical_new_original_MC_seconds','steps']}
print(json.dumps(result))

"""All1200-attempt final audit and Excel data; use Python3.13/flint runtime.

Missing qualification stays missing. Native simulation itself uses original
Python3.8/NumPy1.24.4; independent integer audits use the separate3.13 runtime.
"""
from pathlib import Path
import json,time,statistics
from f002_native_direct_audit import audit,sha
H=Path(__file__).resolve().parent;S=H/'formal/F002_I016_40x30';D=H/'research/F002_I016_formal_native'

def finish():
 required=[D/'FINISHED',D/'FORMAL_ISOLATION_AFTER.json',S/'INDEPENDENT_SEARCH_RAW_AUDIT.json']
 if not all(p.exists() for p in required):
  print(json.dumps(dict(ready=False,reason='actual full native stage/isolation/raw audit not yet terminal',final_statistics_written=False)));return
 out=S/'FINAL_AUDIT_STATS.json';auditfile=D/'INDEPENDENT_FINAL_AUDIT.json'
 if out.exists() or auditfile.exists():raise RuntimeError('No final formal audit/statistics overwrite')
 reg=json.load(open(S/'REGISTRATION.json'));nreg=json.load(open(D/'REGISTRATION.json'));attempts=json.load(open(D/'ALL1200_ATTEMPTS.json'));raw=json.load(open(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json'));cases={c['index']:c for c in json.load(open(H/'CASES.json'))};base={r['index']:r for r in json.load(open(H/'BASELINE_S10.json'))['rows']};prior=json.load(open(H/'formal/F001_I002_40x30/FINAL_AUDIT_STATS.json'));f001={r['index']:r for r in prior['summary']};expected={f'cdf_pair_cover_{i:02d}_seed{seed}':(i,seed) for i in reg['cases'] for seed in reg['seeds']}
 if len(expected)!=1200 or set(attempts)!=set(expected) or set(nreg['pools'])|set(nreg['excluded_attempts'])!=set(expected) or set(nreg['pools'])&set(nreg['excluded_attempts']) or nreg['formal_registration_sha256']!=sha(S/'REGISTRATION.json') or raw['registration_sha256']!=sha(S/'REGISTRATION.json') or not raw['integrity_passed'] or raw['registered_attempts']!=1200:raise RuntimeError('Actual ALL1200 original attempts/raw audit required')
 pre=json.load(open(H/'research/F002_native_audit_preflight/ACTUAL_COMPLETED_FIXTURE_CHECK.json'))
 if not pre['passed'] or pre['source_sha256']!=sha(H/'f002_native_direct_audit.py') or pre['new_MC_calls']!=0:raise RuntimeError('Matching real completed14-pool audit preflight required')
 a=audit(H,'research/F002_I016_formal_native');details=[];errors=[]
 for name,(i,seed) in sorted(expected.items(),key=lambda x:(x[1][0],x[1][1])):
  info=attempts[name];file=H/info['result_file'];term=json.load(open(str(file)+'.terminal.json'));state=a['pools'].get(name);choice=a['selected_by_pool'].get(name);recount=a['selected_raw_recounts'].get(name);elapsed=info.get('search_seconds',term['wall_seconds']);accepted=bool(state and state['accepted']);protocol_valid=accepted and info['protocol_valid']
  if info['index']!=i or info['seed']!=seed or term['index']!=i or term['seed']!=seed or bool(info['native_pool'])!=(name in nreg['pools']):raise RuntimeError('Formal attempt membership/identity differs')
  row=dict(index=i,instance=cases[i]['instance'],tmax=cases[i]['tmax'],seed=seed,method='cdf_pair_cover',search_exit=info['exit'],search_error=info['error'],search_protocol_valid=info['protocol_valid'],joint_accepted=accepted,protocol_valid=protocol_valid,search_seconds=elapsed,search_wall_seconds=term['wall_seconds'],within_budget=elapsed<=600 and info['exit']==0,raw_pool=info.get('raw_candidates',0),phase_seconds=info.get('phase_seconds'),native_pool=info['native_pool'],logical_MC_seconds=state['logical_original_MC_seconds'] if state else 0.,LSS_tested=state['prefix_calls'] if state else 0,LSS_rejected=state['cheaper_rejected'] if state else None,native_missing_keys=state['missing_keys'] if state else [],native_failed_keys=state['failed_keys'] if state else [],search_result_sha256=info.get('result_sha256'),post_error=info.get('native_exclusion'))
  row['within_budget']=term.get('within_budget')
  row['search_seconds_basis']='worker monotonic elapsed' if 'search_seconds' in info else 'observed terminal wall for unsuccessful attempt'
  if accepted:
   if not recount['passed'] or recount['lower']<.99 or choice['original_native_point']<.985:raise RuntimeError('Actual selected joint acceptance differs')
   row.update(cost=choice['cost'],selection=choice['selection'],real_probability=choice['original_native_point'],original_raw_lower=choice['certificate']['lower'],independent_raw_lower=recount['lower'],LSS_key=choice['native_key'],certificate=choice['certificate'])
  if not protocol_valid:errors.append(dict(index=i,seed=seed,search_protocol_valid=info['protocol_valid'],joint_accepted=accepted,search_error=info['error'],lineage_error=info.get('lineage_error'),native_missing_keys=row['native_missing_keys'],native_failed_keys=row['native_failed_keys'],native_exclusion=info.get('native_exclusion')))
  details.append(row)
 summary=[]
 for i in reg['cases']:
  rows=[r for r in details if r['index']==i];qualified=[r for r in rows if r['protocol_valid']];values=[r['cost'] for r in qualified];complete=len(values)==30
  if len(rows)!=30 or {r['seed'] for r in rows}!=set(reg['seeds']):raise RuntimeError('Never replace/drop registered trial')
  avg=statistics.mean(values) if complete else None;best=min(values) if values else None
  summary.append(dict(index=i,instance=cases[i]['instance'],tmax=cases[i]['tmax'],attempts=30,joint_accepted=sum(r['joint_accepted'] for r in rows),protocol_valid=len(values),best=best,avg=avg,std=statistics.pstdev(values) if complete else None,avg_minus_own_best=avg-best if complete else None,avg_minus_old_best=avg-base[i]['old_best'] if complete else None,old_best=base[i]['old_best'],S10_avg=base[i]['new_avg'],F001_avg=f001[i]['avg'],F001_std=f001[i]['std'],F001_avg_minus_F002_avg=f001[i]['avg']-avg if complete else None,mean_search_seconds=statistics.mean(r['search_seconds'] for r in rows),mean_search_wall_seconds=statistics.mean(r['search_wall_seconds'] for r in rows),mean_logical_MC_seconds=statistics.mean(r['logical_MC_seconds'] for r in rows),mean_standalone_logical_seconds=statistics.mean(r['search_seconds']+r['logical_MC_seconds'] for r in rows),minimum_real_probability=min((r['real_probability'] for r in qualified),default=None),minimum_independent_raw_lower=min((r['independent_raw_lower'] for r in qualified),default=None),old_best_known_joint_passed=base[i].get('old_Best_both_constraints_passed'),statistics_complete=complete))
 result=json.load(open(D/'RESULT.json'));launch=json.load(open(D/'LAUNCH.json'));nativefinish=(D/'FINISHED').stat().st_mtime
 final=dict(schema='F002_whole40x30_independent_audit_and_Excel_data',integrity_passed=a['integrity_passed'],all1200_qualified=all(r['protocol_valid'] for r in details),registered_attempts=1200,joint_accepted=sum(r['joint_accepted'] for r in details),protocol_valid=sum(r['protocol_valid'] for r in details),source_sha256=reg['source_sha256'],raw_recount_verifier_sha256=sha(H/'independent_raw_recount.py'),summary=summary,details=details,protocol_errors=errors,std_definition='population standard deviation over all30jointlyqualified protocolvalid trials; missing if any registered trial invalid',native_audit_sha256=None,native_controller_error=a['controller_error'],native_errors=a['native_errors'],native_stage_complete_without_errors=a['passed'],physical_new_invocation_attempts=a['physical_new_MC_attempts'],physical_new_successful_MC_calls=a['physical_successful_MC_receipts'],physical_new_native_call_wall_seconds=a['physical_new_original_MC_seconds'],physical_failed_attempt_wall_seconds=a['physical_failed_attempt_wall_seconds'],physical_speculative_MC_keys=a['speculative_extra_MC_keys'],physical_speculative_MC_seconds=a['speculative_extra_MC_seconds'],physical_attempt_wall_sum=result['private_attempt_wall_sum'],actual_native_stage_wall_seconds=nativefinish-launch['time'],unique_used_MC_keys=a['unique_required_identities'],total_logical_MC_calls=sum(r['LSS_tested'] for r in details),total_logical_MC_seconds=sum(r['logical_MC_seconds'] for r in details),MC_seed=832273,MC_draws_per_identity=10000000,MC_event='sum<=T',MC_is_not_1200independent_random_seed_estimates=True,raw_audit_sha256=sha(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json'),formal_registration_sha256=sha(S/'REGISTRATION.json'),native_registration_sha256=sha(D/'REGISTRATION.json'),native_finish_time=nativefinish)
 with auditfile.open('x') as f:json.dump(a,f,indent=2)
 final['native_audit_sha256']=sha(auditfile)
 with out.open('x') as f:json.dump(final,f,indent=2)
 print(json.dumps({k:v for k,v in final.items() if k not in ['source_sha256','summary','details','protocol_errors','native_errors','physical_speculative_MC_keys']}))
if __name__=='__main__':finish()

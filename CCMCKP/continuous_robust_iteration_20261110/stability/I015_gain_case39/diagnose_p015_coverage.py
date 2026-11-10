"""Post-search coverage attribution only; never imported by an optimizer."""
from pathlib import Path
import json,gzip,collections,itertools,time
from isolated_original_lss import sha
H=Path(__file__).resolve().parent;S=H/'stability/I015_gain_case39';out=S/'COVERAGE_DIAGNOSIS.json'
if out.exists():raise RuntimeError('No posthoc attribution overwrite')
reg=json.load(open(S/'REGISTRATION.json'));audit=json.load(open(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json'));d2=json.load(open(H/'research/D002_isolated_full_prefix/INDEPENDENT_FINAL_AUDIT.json'))
if not audit['passed'] or not d2['passed'] or not (S/'SEARCH_FINISHED').exists():raise RuntimeError('Both frozen search and earlier native audit required')
known={k:tuple(r['selection']) for k,r in d2['selected_by_pool'].items()};rows=[];sets={};sources={}
for seed in reg['seeds']:
 results={}
 for label in reg['sources']:
  file=S/'search'/(label+'_seed'+str(seed)+'.json.gz');info=next(r for r in audit['pools'] if r['seed']==seed and r['label']==label)
  if sha(file)!=info['result_sha256']:raise RuntimeError('Frozen audit result changed')
  results[label]=json.loads(gzip.decompress(file.read_bytes()));sources[file.relative_to(H).as_posix()]=sha(file)
 control=results['I002_control'];data=results['I015_hybrid'];h=data['extension']['hybrid'];pc=data['extension']['precision_closure'];c={tuple(r['selection']) for r in control['candidate_shortlist']};cdf={tuple(r['selection']) for r in h['cdf_pool_records']};final={tuple(r['selection']) for r in data['candidate_shortlist']};sets[seed]=final
 if not cdf<=final:raise RuntimeError('Own accepted CDF member removed')
 witnesses={}
 for label,q in known.items():
  hits=[r for r in data['candidate_shortlist'] if tuple(r['selection'])==q];witnesses[label]=dict(previous_D002_cost=d2['pools'][label]['cost'],in_this_CDF=q in cdf,in_this_final=q in final,source=hits[0]['source'] if hits else None,minimum_changed_groups_from_any_own_CDF_member=min(sum(a!=b for a,b in zip(q,c)) for c in cdf))
 rows.append(dict(seed=seed,I002_pool=len(c),I015_CDF_pool=len(cdf),paired_own_CDF_selection_sets_identical=c==cdf,I002_not_in_I015_CDF=len(c-cdf),CDF_added_vs_control=len(cdf-c),I015_final_pool=len(final),I015_new_vs_own_CDF=len(final-cdf),source_counts=dict(collections.Counter(r['source'] for r in data['candidate_shortlist'])),certificate_bins=dict(collections.Counter(str(r['certificate']['bins']) for r in data['candidate_shortlist'])),precision_new_accepted=pc['accepted'],cdf_seconds=h['cdf_seconds'],block_seconds=h['block_seconds'],precision_seconds=pc['closure_seconds'],previous_qualified_witness_coverage=witnesses))
overlaps=[]
for a,b in itertools.combinations(reg['seeds'],2):
 common=sets[a]&sets[b];union=sets[a]|sets[b];overlaps.append(dict(seed_a=a,seed_b=b,common=len(common),union=len(union),Jaccard=len(common)/len(union)))
result=dict(time=time.time(),scope='POSTHOC attribution on all6frozen searches after independent raw audit; earlier D002 vectors joined only here, not passed into any optimizer; no new MC, no native qualification of unseen vectors orAvg',all3_paired_CDF_sets_identical=all(r['paired_own_CDF_selection_sets_identical'] for r in rows),all_initial_control_members_retained=all(r['I002_not_in_I015_CDF']==0 for r in rows),rows=rows,final_pool_pairwise_overlap=overlaps,common_all3_final_members=len(set.intersection(*sets.values())),union_all3_final_members=len(set.union(*sets.values())),source_sha256=sources,search_raw_audit_sha256=sha(S/'INDEPENDENT_SEARCH_RAW_AUDIT.json'),prior_native_audit_sha256=sha(H/'research/D002_isolated_full_prefix/INDEPENDENT_FINAL_AUDIT.json'),new_original_MC_calls=0)
with out.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(all3_paired_CDF_sets_identical=result['all3_paired_CDF_sets_identical'],all_control_members_retained=result['all_initial_control_members_retained'],common_all3=result['common_all3_final_members'],union_all3=result['union_all3_final_members'],overlaps=overlaps,rows=[{k:v for k,v in r.items() if k not in ['source_counts','certificate_bins']} for r in rows])))

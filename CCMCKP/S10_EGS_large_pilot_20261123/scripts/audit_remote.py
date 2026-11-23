"""Independent record and integer-count audit; imports no search or evaluator writer."""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import hashlib,itertools,json,math,pickle,statistics,subprocess
import numpy as np
from concurrent.futures import ThreadPoolExecutor,as_completed

B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP')
H=B/'work/egs_large_pilot_20261123'
assert Path.cwd().resolve()==B.resolve()
P=json.loads((H/'PROTOCOL.json').read_text())
def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
if not (H/'COMPLETED.json').exists():
    print(json.dumps({'status':'NOT_TERMINAL','state':read(H/'STATE.json')}));raise SystemExit(0)
assert read(H/'COMPLETED.json')['phase']=='completed'
global_errors=[]
for name,digest in P['source_and_binary_pins'].items():
    if sha(H/name)!=digest:global_errors.append('source:'+name)
for name,digest in P['input_pins'].items():
    if sha(B/name)!=digest:global_errors.append('input:'+name)
if sha(H/'PROTOCOL.json')!=read(H/'LAUNCH.json')['protocol_sha256']:global_errors.append('protocol')
data={}
for case in P['cases']:
    folder=B/'benchmark'/case['instance']
    groups=pickle.loads((folder/'node_to_factor.pkl').read_bytes())
    if isinstance(groups,dict):groups=[groups[k] for k in sorted(groups)]
    costs=[float(x) for line in (folder/'cost.txt').read_text().splitlines() for x in line.split('#',1)[0].split()]
    atoms=[[Fraction(x) for line in (folder/(str(j)+'_sample.txt')).read_text().splitlines() for x in line.split('#',1)[0].split()] for j in range(len(costs))]
    means=[sum(map(float,a))/len(a) for a in atoms]
    variances=[sum((float(x)-mu)**2 for x in a)/len(a) for a,mu in zip(atoms,means)]
    data[case['index']]={'groups':groups,'costs':costs,'atoms':atoms,'means':means,'variances':variances,'capacity':Fraction(str(case['tmax']))}

count_cache={}
histogram_cache={}
def valid_selection(d,s):return len(s)==len(d['groups']) and all(j in g for j,g in zip(s,d['groups']))
def independent_count(index,selection,bins,up):
    key=(index,tuple(selection),bins,up)
    if key in count_cache:return count_cache[key]
    d=data[index];denominator=1;histograms=[];offset=0;maximum=0
    for j in selection:
        atoms=d['atoms'][j];denominator*=len(atoms)
        hkey=(index,j,bins,up)
        if hkey not in histogram_cache:
            counts=Counter()
            for value in atoms:
                assert value>=0
                ratio=value/d['capacity']*bins
                q=(-(-ratio.numerator//ratio.denominator)) if up else ratio.numerator//ratio.denominator
                counts[min(bins,q)]+=1
            histogram_cache[hkey]=counts
        counts=histogram_cache[hkey]
        low=min(counts);offset+=low;maximum+=max(counts)
        histograms.append({q-low:n for q,n in counts.items()})
    cut=bins-offset
    if cut<=0:result=(0,denominator)
    elif maximum<bins:result=(denominator,denominator)
    else:
        # Independent Python arbitrary integers, no calls/imports to the C++ writer.
        # Each slot is wider than the full Cartesian product count, so no carry.
        # Degree truncation preserves every coefficient contributing to sum<T.
        width=denominator.bit_length()+1
        helper=globals().get('H',Path('.'))/'audit_count_helper'
        if helper.is_file():
            payload=[str(width),str(cut),str(len(histograms))]
            for counts in histograms:
                entries=[(q,n) for q,n in counts.items() if q<cut]
                payload.append(str(len(entries)))
                for q,n in entries:payload.extend([str(q),str(n)])
            answer=subprocess.run([str(helper)],input=(' '.join(payload)+'\n').encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
            numerator=int(answer.stdout.strip())
        else:
            mask=(1<<(width*cut))-1
            factors=[sum(n<<(width*q) for q,n in counts.items() if q<cut) for counts in histograms]
            while len(factors)>1:
                factors=[((factors[k]*factors[k+1])&mask) if k+1<len(factors) else factors[k] for k in range(0,len(factors),2)]
            # Evaluation at base=1 sums coefficients. The sum is <= denominator,
            # strictly less than 2**width-1, so this residue is the exact count.
            numerator=factors[0]%((1<<width)-1)
        assert 0<=numerator<=denominator
        result=(numerator,denominator)
    count_cache[key]=result
    return result

def check_certificate(index,record):
    d=data[index];s=record['selection'];cert=record['certificate']
    assert valid_selection(d,s)
    assert abs(sum(d['costs'][j] for j in s)-record['cost'])<=1e-8
    assert cert['selection']==s and cert['all_original_samples'] and cert['strict_event']=='sum<T'
    lo,den=independent_count(index,s,cert['bins'],True)
    hi,den2=independent_count(index,s,cert['bins'],False)
    assert lo==int(cert['lower_numerator']) and hi==int(cert['upper_numerator'])
    assert den==den2==int(cert['denominator']) and lo*100>=den*99 and cert['accepted']
    return True

outcomes=[read(p) for p in (H/'outcomes').glob('*.json')]
expected={(arm['name'],case['index'],rep) for arm in P['arms'] for case in P['cases'] for rep in range(1,31)}
actual={(r['arm'],r['case_index'],r['rep']) for r in outcomes}
if actual!=expected or len(outcomes)!=270:global_errors.append('coverage_or_duplicates')
# Precompute only unique immutable certificate identities. Four independent
# read-only arithmetic workers run after the solver controller has terminated.
keys=set()
for outcome in outcomes:
    raw_path=H/'runs'/outcome['identity']/'S10_search.json'
    if outcome['rc']!=0 or not raw_path.exists():continue
    raw_record=read(raw_path)
    certificates=list(raw_record.get('candidate_shortlist',[]))
    if isinstance(raw_record.get('selected'),dict):certificates.append(raw_record['selected'])
    for candidate in certificates:
        if 'certificate' not in candidate:continue
        for up in [False,True]:keys.add((outcome['case_index'],tuple(candidate['selection']),candidate['certificate']['bins'],up))
if keys and (H/'audit_count_helper').exists():
    toolchain=read(H/'AUDIT_TOOLCHAIN.json')
    assert sha(H/'audit_count_helper.cpp')==toolchain['source_sha256']
    assert sha(H/'audit_count_helper')==toolchain['binary_sha256']
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures=[executor.submit(independent_count,*key) for key in keys]
        for number,future in enumerate(as_completed(futures),1):
            future.result()
            if number%100==0:
                (H/'AUDIT_PROGRESS.json').write_text(json.dumps({'done':number,'total_unique_counts':len(keys)}))
rows=[]
for outcome in sorted(outcomes,key=lambda r:(r['case_index'],r['arm'],r['rep'])):
    errors=[];index=outcome['case_index'];d=data[index]
    row={k:outcome.get(k) for k in ['identity','case_index','instance','capacity','arm','rep','seed','rc','termination_reason','process_wall_seconds','peak_rss_bytes']}
    row.update({'valid':False,'cost':None,'lss_probability':None,'reported_real_probability':None,
        'search_seconds':None,'final_selection_first_raw_accept_seconds':None,'selection':None,
        'egs_queries':0,'egs_new_acceptances':0,'egs_improvements':0,
        'initialization_best_cost':None,'raw_final_best_cost':None,'initialization_seconds':None})
    root=H/'runs'/outcome['identity']
    try:
        assert outcome['seed']==960000+outcome['rep']
        for name,item in outcome['output_files'].items():
            assert (root/name).stat().st_size==item['bytes'] and sha(root/name)==item['sha256']
        if outcome['rc']!=0:
            errors.append('process_exit:'+str(outcome['rc']))
            if (root/'FAILED.json').exists():row['failure_detail']=read(root/'FAILED.json')
        else:
            raw=read(root/'S10_search.json');meta=read(root/'S10_search.run.json');result=read(root/'RESULT.json')
            assert raw['status']==result['status']=='completed'
            assert raw['seed']==result['search_seed']==meta['seed']==outcome['seed']
            assert result['rep']==outcome['rep'] and raw['instance']==result['instance']==outcome['instance']
            assert raw['capacity']==result['capacity']==outcome['capacity']
            assert meta['within_budget'] and meta['elapsed']<=600 and meta['budget']==600
            assert meta['local_phases']=='none' and meta['backend']=='gurobi'
            assert raw['config']['nominal_CL']==.99 and raw['config']['all_original_samples']
            assert raw['config']['no_cross_run_solutions'] and raw['config']['no_dist_metadata_in_optimizer']
            for candidate in raw['candidate_shortlist']:check_certificate(index,candidate)
            assert raw['selected']['final_exact_recomputed'];check_certificate(index,raw['selected'])
            for name,digest in meta['input_sha256'].items():assert digest==P['input_pins']['benchmark/'+outcome['instance']+'/'+name]
            selected=result['selection']
            assert valid_selection(d,selected) and abs(sum(d['costs'][j] for j in selected)-result['cost'])<=1e-8
            assert result['original_LSS_confidence']>=.99
            assert result['original_output_variants'][0]['selection']==selected
            assert result['original_output_variants'][0]['cost']==result['cost']
            assert 0<=result['recorded_real_probability']<=1
            source=[x for x in raw['candidate_shortlist'] if x['selection']==selected]
            assert len(source)==1 and 0<=source[0]['found_seconds']<=meta['elapsed']
            if outcome['arm']=='S10_MITM':
                assert meta['search_flow']=='frontier_mitm' and result['arm']=='G_NONE'
            else:
                gamma=2.4 if outcome['arm']=='EGS_2p4' else 0
                assert meta['search_flow']=='ellipsoid_oa' and result['arm']=='EGS_OA_none'
                assert raw['config']['ellipsoid_gamma']==gamma and not raw['config']['ellipsoid_is_final_constraint']
                assert not raw['match_history']
                qs=[q for q in raw['ellipsoid_history'] if q.get('event')=='candidate_query']
                for q in qs:
                    if not q['has_candidate']:continue
                    s=q['selection'];assert valid_selection(d,s)
                    norm=math.sqrt(sum(d['variances'][j] for j in s))
                    risk=sum(d['means'][j] for j in s)+gamma*norm
                    assert abs(risk-q['risk'])<1e-7 and abs(norm-q['norm'])<1e-7
                    assert sum(d['costs'][j] for j in s)<=q['candidate_cost_bound']+1e-8
                    assert q['bound_scope']=='unvisited_ellipsoid_proxy_only_not_CCMCKP_cost'
                row.update({'egs_queries':len(qs),'egs_new_acceptances':sum(q.get('raw_certificate_accepted',False) for q in qs),
                    'egs_improvements':sum(q.get('incumbent_improved',False) for q in qs)})
            row.update({'valid':True,'cost':result['cost'],'lss_probability':result['original_LSS_confidence'],
                'reported_real_probability':result['recorded_real_probability'],'search_seconds':meta['elapsed'],
                'final_selection_first_raw_accept_seconds':source[0]['found_seconds'],'selection':selected})
            init=next(p for p in meta['phase_records'] if p['phase']=='initialization')
            row.update({'initialization_best_cost':init['best_after'],'initialization_seconds':init['elapsed'],
                'raw_final_best_cost':raw['selected']['cost']})
    except Exception as error:
        errors.append(type(error).__name__+':'+str(error));row['valid']=False
    row['errors']=errors
    rows.append(row)

summaries=[]
for case in P['cases']:
    for arm in P['arms']:
        subset=[r for r in rows if r['case_index']==case['index'] and r['arm']==arm['name']]
        valid=[r for r in subset if r['valid']];costs=[r['cost'] for r in valid]
        complete=len(valid)==30 and len(subset)==30 and not global_errors
        best=min(costs) if costs else None
        hits=[r for r in valid if abs(r['cost']-best)<=1e-8] if costs else []
        mean=statistics.mean(costs) if complete else None
        std=statistics.stdev(costs) if complete else None
        summaries.append({'case_index':case['index'],'instance':case['instance'],'capacity':case['tmax'],'arm':arm['name'],
            'registered':30,'terminal':len(subset),'valid':len(valid),'valid_rate':len(valid)/30,'best':best,
            'avg':mean,'sample_std':std,'cv':std/mean if mean else None,
            'valid_only_avg_diagnostic':statistics.mean(costs) if costs else None,
            'mean_final_selection_first_raw_accept_seconds':statistics.mean(r['final_selection_first_raw_accept_seconds'] for r in valid) if complete else None,
            'best_hits':len(hits),'mean_raw_accept_seconds_conditional_on_best':statistics.mean(r['final_selection_first_raw_accept_seconds'] for r in hits) if hits else None,
            'mean_search_seconds':statistics.mean(r['search_seconds'] for r in valid) if complete else None,
            'mean_process_wall_seconds':statistics.mean(r['process_wall_seconds'] for r in subset) if subset else None,
            'reported_realP_ge99_count':sum(r['reported_real_probability']>=.99 for r in valid),
            'mean_reported_realP':statistics.mean(r['reported_real_probability'] for r in valid) if complete else None,
            'mean_egs_queries':statistics.mean(r['egs_queries'] for r in subset) if subset else None,
            'total_egs_improvements':sum(r['egs_improvements'] for r in subset),
            'mean_initialization_best_cost':statistics.mean(r['initialization_best_cost'] for r in valid) if complete and all(r['initialization_best_cost'] is not None for r in valid) else None,
            'mean_raw_final_best_cost':statistics.mean(r['raw_final_best_cost'] for r in valid) if complete else None,
            'mean_initialization_seconds':statistics.mean(r['initialization_seconds'] for r in valid) if complete else None})

def mean_sign_flip(a,b,seed):
    diff=np.array(a,dtype=float)-np.array(b,dtype=float)
    diff=diff[diff!=0]
    if not len(diff):return 1.
    observed=abs(float(diff.sum()));tol=1e-12*max(1.,observed)
    if len(diff)<=20:
        sums=np.array([0.])
        for value in diff:sums=np.concatenate([sums+value,sums-value])
        return float(np.count_nonzero(np.abs(sums)>=observed-tol))/len(sums)
    rng=np.random.default_rng(seed);count=0;left=99999
    while left:
        n=min(5000,left);signs=2*rng.integers(0,2,size=(n,len(diff)))-1
        count+=np.count_nonzero(np.abs(signs@diff)>=observed-tol);left-=n
    return float(count+1)/100000
def paired_validity(a,b):
    d1=sum(x and not y for x,y in zip(a,b));d2=sum(y and not x for x,y in zip(a,b));n=d1+d2
    return min(1.,2*sum(math.comb(n,k) for k in range(min(d1,d2)+1))/2**n) if n else 1.
comparisons=[]
for c,case in enumerate(P['cases']):
    for k,(candidate,reference) in enumerate([('EGS_2p4','S10_MITM'),('EGS_0','S10_MITM'),('EGS_2p4','EGS_0')]):
        a=sorted([r for r in rows if r['case_index']==case['index'] and r['arm']==candidate],key=lambda r:r['rep'])
        b=sorted([r for r in rows if r['case_index']==case['index'] and r['arm']==reference],key=lambda r:r['rep'])
        ok=len(a)==len(b)==30 and all(r['valid'] for r in a+b) and not global_errors
        ma=statistics.mean(r['cost'] for r in a) if ok else None;mb=statistics.mean(r['cost'] for r in b) if ok else None
        comparisons.append({'case_index':case['index'],'candidate':candidate,'reference':reference,'complete_pairs':ok,
            'mean_difference':ma-mb if ok else None,'relative_mean_difference':ma/mb-1 if ok else None,
            'direction':('优' if ma<mb-1e-8 else '劣' if ma>mb+1e-8 else '平') if ok else '不可评',
            'p_mean_raw':mean_sign_flip([r['cost'] for r in a],[r['cost'] for r in b],20261123+10*c+k) if ok else None,
            'p_validity_raw':paired_validity([r['valid'] for r in a],[r['valid'] for r in b])})
for rawkey,outkey in [('p_mean_raw','p_mean_holm'),('p_validity_raw','p_validity_holm')]:
    order=sorted(range(len(comparisons)),key=lambda i:comparisons[i][rawkey] if comparisons[i][rawkey] is not None else 1.)
    previous=0
    for rank,i in enumerate(order):
        value=comparisons[i][rawkey]
        adjusted=min(1.,max(previous,(len(order)-rank)*(value if value is not None else 1.)))
        previous=adjusted;comparisons[i][outkey]=adjusted if value is not None else None

report={'schema':'EGS_real_large_pilot_independent_audit_v1','protocol_sha256':sha(H/'PROTOCOL.json'),
    'terminal':len(rows),'independent_valid':sum(r['valid'] for r in rows),'global_errors':global_errors,
    'certificate_count_cache_entries':len(count_cache),'case_summaries':summaries,'comparisons':comparisons,'runs':rows,
    'scope':'three real large cases only; no automatic full40 expansion',
    'realP_is_reporting_only':True,'official_avg_std_require_all30_valid':True,
    'timing_note':'first raw acceptance of final output selection is not first LSS admission time; search and entire process shown separately',
    'environment_note':'fresh matched Gurobi11.0.3 batch, not mixed with historical Gurobi13 runs'}
(H/'INDEPENDENT_AUDIT_STATISTICS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='runs'},ensure_ascii=False),flush=True)

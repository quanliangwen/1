"""Isolated real-source scoring tests. No SDK, simulator or wall fitting is loaded."""
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
from types import SimpleNamespace
import ast,collections,copy,gc,heapq,importlib.abc,json,math,os,platform,statistics,sys,time,typing

class BlockSDK(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='swarm_rescue' or fullname.startswith('swarm_rescue.'):
            raise RuntimeError('SDK import forbidden in offline scoring validation')
sys.meta_path.insert(0,BlockSDK())
import numpy as np
import cv2
ROOT=Path(__file__).resolve().parent
BUILD=json.loads((ROOT/'BUILD.json').read_text())
def save(name,data):(ROOT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def load(name,label):
    archive=ROOT/name
    assert sha256(archive.read_bytes()).hexdigest()==BUILD['baseline_zip_sha256' if label=='old' else 'candidate_zip_sha256']
    ns=dict(np=np,cv2=cv2,math=math,heapq=heapq,Optional=typing.Optional,__name__=label)
    with ZipFile(archive) as z:
        for filename,classes in [('greedy_mapping.py',{'MapMemory'}),('submission_renderer.py',{'SubmissionBearings'})]:
            tree=ast.parse(z.read(filename));nodes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name in classes]
            exec(compile(ast.Module(body=nodes,type_ignores=[]),str(archive)+'/'+filename,'exec'),ns)
        tree=ast.parse(z.read('map_candidates.py'))
        nodes=[n for n in tree.body if not isinstance(n,ast.ImportFrom)]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(archive)+'/map_candidates.py','exec'),ns)
        tree=ast.parse(z.read('red_hooks.py'));nodes=[]
        for n in tree.body:
            if isinstance(n,ast.FunctionDef) and n.name=='local_score':nodes.append(n)
            if isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and isinstance(t.value,ast.Name) and t.value.id=='local_score' for t in n.targets):nodes.append(n)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(archive)+'/red_hooks.py','exec'),ns)
    def no_render(*a,**k):raise RuntimeError('Fitting is forbidden in offline scoring validation')
    ns['SubmissionBearings'].render=no_render
    return SimpleNamespace(**ns)
old,new=load('baseline_snapshot.zip','old'),load('candidate_snapshot.zip','new')
def equal(a,b):
    assert type(a)==type(b),(type(a),type(b))
    if isinstance(a,np.ndarray):assert a.dtype==b.dtype and a.shape==b.shape and a.tobytes()==b.tobytes()
    elif isinstance(a,(tuple,list)):
        assert len(a)==len(b)
        for x,y in zip(a,b):equal(x,y)
    elif isinstance(a,dict):
        assert a.keys()==b.keys()
        for key in a:equal(a[key],b[key])
    else:assert a==b,(a,b)

EPOCH=('group-return-v1',5400,5)
def image_data(owner,version,bitmap,sources=None):
    data=dict(epoch=EPOCH,owner=int(owner),version=int(version),packed=old.frozen(np.packbits(np.asarray(bitmap,bool).ravel())),sources={} if sources is None else sources)
    data['digest']=old.digest(data);return data
def fixture(module,w,h,images,hits,snapshots=None):
    memory=module.MapMemory(w,h);memory.hits=np.asarray(hits,np.uint8)*3
    deadline=SimpleNamespace(remember=lambda step,image:None)
    drone=SimpleNamespace(memory=memory,submission_bearings=SimpleNamespace(bits=np.zeros(((h+3)//4,(w+3)//4),np.uint8)),
         team_size=5,walltime_limit=180,elapsed_walltime=100,deadline_submission=deadline)
    obj=module.MapCandidates(0,EPOCH,w,h);obj.images={k:module.frozen(v) for k,v in images.items()}
    obj.snapshots={} if snapshots is None else {k:module.frozen(v) for k,v in snapshots.items()}
    return obj,drone
def evaluate(module,pair,ordinary=False,step=4000,score=None):
    obj,drone=pair;winner=obj.choose(drone,step,score or module.local_score,fusion=False,ordinary=ordinary)
    output=None if winner is None else obj.install(drone,winner['owner'],step)
    return winner,obj.score_table,output
checks=[]
def check_case(name,w,h,images,hits,ordinary=False,snapshots=None):
    a,b=fixture(old,w,h,images,hits,snapshots),fixture(new,w,h,images,hits,snapshots)
    equal(evaluate(old,a,ordinary),evaluate(new,b,ordinary))
    equal(a[0].audit,b[0].audit)
    for owner in images:equal(a[0].images[owner]['packed'],b[0].images[owner]['packed'])
    if hasattr(b[0],'_scored_image'):assert b[0]._scored_image is None
    checks.append(name)

rng=np.random.default_rng(615)
for i in range(300):
    w,h=[(7,9),(64,63),(65,67),(1,1)][i%4]
    hits=rng.random(((h+1)//2,(w+1)//2))<.12
    images={owner:image_data(owner,3240+owner,(rng.random((h,w))<.15).astype(np.uint8)) for owner in range(1+i%7)}
    check_case(f'random_{i}',w,h,images,hits,ordinary=bool(i%2))
for name,bitmap,hits in [
    ('empty',np.zeros((7,9),np.uint8),np.zeros((4,5),bool)),
    ('odd_only',np.pad(np.ones((1,1),np.uint8),((1,5),(1,7))),np.zeros((4,5),bool)),
    ('all_walls',np.ones((7,9),np.uint8),np.ones((4,5),bool))]:
    check_case(name,9,7,{0:image_data(0,3240,bitmap),5:image_data(5,3300,bitmap)},hits,True)
pad=image_data(0,3240,np.zeros((7,9),np.uint8));pad['packed']=np.array(pad['packed'],copy=True);pad['packed'][-1]|=1
pad['digest']=old.digest({k:v for k,v in pad.items() if k!='digest'})
check_case('nonzero_padding_does_not_make_empty_map_nonempty',9,7,{0:pad},np.zeros((4,5),bool))
check_case('no_images',9,7,{},np.ones((4,5),bool))
for ordinary in [False,True]:
    data=[dict(owner=0,version=3240,digest='a',score=.9),dict(owner=1,version=3400,digest='b',score=.8971),dict(owner=2,version=3500,digest='c',score=.8969)]
    equal(old.MapCandidates.select_candidate(data,ordinary),new.MapCandidates.select_candidate(data,ordinary));checks.append('near_tie_'+str(ordinary))

# Handoff must be one-shot and reject any owner/version/digest/buffer mismatch.
for mode in ['valid','owner','version','digest','packed','twice','mutate_output']:
    images={owner:image_data(owner,3240+owner,np.ones((7,9),np.uint8)) for owner in [0,1]}
    pairs=[fixture(m,9,7,images,np.ones((4,5),bool)) for m in [old,new]]
    for module,(obj,drone) in zip([old,new],pairs):
        best=obj.choose(drone,4000,module.local_score,fusion=False);owner=best['owner']
        if mode=='owner':owner=1-owner
        if mode=='version':obj.images[owner]['version']+=1
        if mode=='digest':obj.images[owner]['digest']='replacement'
        if mode=='packed':obj.images[owner]['packed']=obj.images[owner]['packed'].copy()
        output=obj.install(drone,owner,4000)
        if module is old:expected=copy.deepcopy(output)
        else:equal(expected,output);assert obj._scored_image is None
        if mode=='twice':equal(output,obj.install(drone,owner,4001))
        if mode=='mutate_output':
            saved=obj.images[owner]['packed'].tobytes();output[0][:]=0
            assert obj.images[owner]['packed'].tobytes()==saved
            assert obj.install(drone,owner,4001)[0].any()
    checks.append('handoff_'+mode)

# The same mutable reference changes between rounds: no context may survive.
images={0:image_data(0,3240,np.ones((7,9),np.uint8))}
pairs=[fixture(m,9,7,images,np.zeros((4,5),bool)) for m in [old,new]]
for round_id in range(10):
    for module,(obj,drone) in zip([old,new],pairs):drone.memory.hits[round_id%4,:]=3
    equal(evaluate(old,pairs[0]),evaluate(new,pairs[1]));checks.append(f'changed_reference_round_{round_id}')
for module in [old,new]:
    pair=fixture(module,9,7,images,np.ones((4,5),bool))
    result=evaluate(module,pair,score=lambda bitmap,hits:old.local_score(bitmap,hits))
    if module is old:expected=result
    else:equal(expected,result)
checks.append('legacy_two_argument_callback')

cohorts={};coverage={};source_hashes={}
for cohort in ['Map06','Map08','Map09_historical','Map09_latest']:
    meta=json.loads((ROOT/'fixtures'/f'{cohort}_metadata.json').read_text())
    score=json.loads((ROOT/'fixtures'/f'{cohort}_score.json').read_text())
    source_hashes[cohort]={p.name:sha256(p.read_bytes()).hexdigest() for p in (ROOT/'fixtures').glob(cohort+'_*')}
    cases=[];cov=collections.Counter();cohort_counts=collections.Counter()
    with np.load(ROOT/'fixtures'/f'{cohort}_data.npz',allow_pickle=False) as arrays:
        for details in score['drone_details']:
            owner=details['drone'];md=meta[str(owner)];w,h=md['width'],md['height'];snapshots={};final_images={}
            def packet(prefix):return tuple(arrays[prefix+'_'+n].copy() for n in ['indices','values','free','visits'])
            for key,s in md['snapshots'].items():
                who=int(key);data=dict(epoch=EPOCH,owner=who,version=s['version'],memory=packet(f'd{owner}_snapshot{who}'),
                    bearings=arrays[f'd{owner}_snapshot{who}_bearings'].copy(),inventory={int(k):tuple(v) for k,v in s['inventory'].items()})
                data['digest']=old.digest(data);assert data['digest']==s['digest'];snapshots[who]=data
            for key,m in md['images'].items():
                who=int(key);data=dict(epoch=EPOCH,owner=who,version=m['version'],packed=arrays[f'd{owner}_image{who}'].copy(),sources={int(k):v for k,v in m['sources'].items()})
                data['digest']=old.digest(data);assert data['digest']==m['digest'];final_images[who]=data
            pixels=[d['packed'] for d in final_images.values()]
            if f'd{owner}_latest_live' in arrays.files:pixels.append(arrays[f'd{owner}_latest_live'].copy())
            active={};known_by_digest={d['digest']:d for d in final_images.values()}
            local_candidates=[packet(f'd{owner}_final')]+[d['memory'] for d in snapshots.values()]
            for event in details['group_candidate_audit']:
                kind=event[1]
                if kind=='snapshot_frozen':active[event[2]]=snapshots[event[2]]
                elif kind=='payload_stored' and event[3]=='snapshot':active[event[4]]=snapshots[event[4]]
                if kind!='map_selected':continue
                step,_,reference,table,_=event;pool={};exact_images=True
                source_options=[{k:v['digest'] for k,v in active.items()}]+[d['sources'] for d in final_images.values()]
                for row in table:
                    data=known_by_digest.get(row['digest'])
                    if data is None:
                        for packed in pixels:
                            for sources in source_options:
                                probe=dict(epoch=EPOCH,owner=row['owner'],version=row['version'],packed=packed,sources=sources)
                                probe['digest']=old.digest(probe)
                                if probe['digest']==row['digest']:data=probe;break
                            if data is not None:break
                    if data is not None:known_by_digest[data['digest']]=data;cov['recovered_image_occurrences']+=1
                    else:
                        exact_images=False;cov['proxy_image_occurrences']+=1
                        template=final_images.get(row['owner'],next(iter(final_images.values())))
                        data=dict(template,owner=row['owner']);data['digest']=old.digest({k:v for k,v in data.items() if k!='digest'})
                    pool[row['owner']]=data
                hits=None
                for local in local_candidates:
                    memory=old.MapMemory(w,h);memory.merge(local)
                    for snapshot in active.values():memory.merge(snapshot['memory'])
                    probe=memory.hits>=3
                    if old.digest(probe)==reference:hits=probe;break
                exact_reference=hits is not None
                if hits is None:
                    memory=old.MapMemory(w,h);memory.merge(local_candidates[0])
                    for snapshot in active.values():memory.merge(snapshot['memory'])
                    hits=memory.hits>=3;cov['proxy_reference_rounds']+=1
                else:cov['recovered_reference_rounds']+=1
                for ordinary in [False,True]:
                    pair_a=fixture(old,w,h,pool,hits,active);pair_b=fixture(new,w,h,pool,hits,active)
                    a=evaluate(old,pair_a,ordinary,step);b=evaluate(new,pair_b,ordinary,step);equal(a,b)
                    if exact_reference and exact_images:equal(a[1],table)
                    checks.append(f'{cohort}_d{owner}_step{step}_mode{ordinary}')
                if exact_reference and exact_images:cov['exact_historical_score_tables']+=1
                else:cov['snapshot_constructed_rounds']+=1
                cases.append((fixture(old,w,h,pool,hits,active),fixture(new,w,h,pool,hits,active),step))
                cohort_counts['rounds']+=1;cohort_counts['scores']+=len(table)
            cov['original_installs']+=sum(e[1]=='available_candidates_compared' for e in details['group_audit'])
    cohorts[cohort]=cases;coverage[cohort]=dict(cov,**cohort_counts)

# Instrument one batch only to prove the operation reductions, outside timings.
operation_counts={}
for label,module in [('old',old),('new',new)]:
    pair=copy.deepcopy(cohorts['Map09_latest'][0][0 if label=='old' else 1]);obj,drone=pair
    count=collections.Counter();original_image=obj.image;original_dilate=cv2.dilate
    def counted_image(owner):count['decode']+=1;return original_image(owner)
    def counted_dilate(*a,**k):count['dilate']+=1;return original_dilate(*a,**k)
    obj.image=counted_image;cv2.dilate=counted_dilate
    try:evaluate(module,pair)
    finally:cv2.dilate=original_dilate
    operation_counts[label]=dict(count)
assert operation_counts['old']==dict(decode=3,dilate=4)
assert operation_counts['new']==dict(decode=2,dilate=3)
save('EQUIVALENCE.json',dict(status='PASS',checks=len(checks),scenarios=checks,coverage=coverage,
    operation_example=operation_counts,baseline_zip_sha256=BUILD['baseline_zip_sha256'],candidate_zip_sha256=BUILD['candidate_zip_sha256'],
    fixture_file_hashes=source_hashes,full_matches=0,physics_steps=0,fitting_calls=0,sdk_import_blocked=True,
    historical_inputs_missing=True,notes='Only rounds with both matching reference digest and recovered image digests are exact historical scoring-table replays. Others are explicitly marked snapshot-constructed equivalence cases.'))
print('EQUIVALENCE PASS',len(checks),json.dumps(coverage),flush=True)

def cpu_counters():
    result={}
    for line in Path('/proc/stat').read_text().splitlines():
        f=line.split()
        if f[0]=='cpu' or f[0].startswith('cpu') and f[0][3:].isdigit():
            n=list(map(int,f[1:9]));result[f[0]]=(sum(n),n[3]+n[4])
    return result
available=sorted(os.sched_getaffinity(0));c0=cpu_counters();time.sleep(.5);c1=cpu_counters()
util={c:1-(c1['cpu'+str(c)][1]-c0['cpu'+str(c)][1])/max(1,c1['cpu'+str(c)][0]-c0['cpu'+str(c)][0]) for c in available}
selected=min(available,key=lambda c:(util[c],c));os.sched_setaffinity(0,{selected})
def timed(module,cases,index):
    wall=time.perf_counter_ns();cpu=time.process_time_ns()
    for case in cases:evaluate(module,case[index],False,case[2])
    return dict(wall_seconds=(time.perf_counter_ns()-wall)/1e9,cpu_seconds=(time.process_time_ns()-cpu)/1e9)
results={}
for name,cases in cohorts.items():
    for module,index in [(old,0),(new,1)]:timed(module,cases,index)
    samples=[];start=cpu_counters();load=os.getloadavg();gc.disable()
    try:
        for iteration in range(12):
            row={}
            for label in (['old','new'] if iteration%2==0 else ['new','old']):
                row[label]=timed(old if label=='old' else new,cases,0 if label=='old' else 1)
            samples.append(row)
    finally:gc.enable()
    end=cpu_counters();delta=end['cpu'][0]-start['cpu'][0];idle=end['cpu'][1]-start['cpu'][1]
    before=statistics.median(r['old']['wall_seconds'] for r in samples);after=statistics.median(r['new']['wall_seconds'] for r in samples)
    savings=[r['old']['wall_seconds']-r['new']['wall_seconds'] for r in samples]
    results[name]=dict(real_rounds=coverage[name]['rounds'],real_scores=coverage[name]['scores'],
         baseline_median_seconds=before,candidate_median_seconds=after,median_paired_saved_seconds=statistics.median(savings),
         paired_saved_min=min(savings),paired_saved_max=max(savings),
         baseline_cpu_median_seconds=statistics.median(r['old']['cpu_seconds'] for r in samples),
         candidate_cpu_median_seconds=statistics.median(r['new']['cpu_seconds'] for r in samples),
         estimated_decodes_before=coverage[name]['scores']+coverage[name]['original_installs'],
         estimated_decodes_after=coverage[name]['scores'],saved_reference_preprocesses=coverage[name]['scores']-coverage[name]['rounds'],
         system_cpu_busy_percent=100*(1-idle/delta),load_average=load,samples=samples)
    print(name,before,after,'saved',statistics.median(savings),flush=True)
stop=all(value['median_paired_saved_seconds']<1 for value in results.values())
save('BENCHMARK.json',dict(status='COMPLETE',method='Each batch contains exactly the historical comparison count and candidate count; fixed stored snapshots/images; fitting disabled; 12 alternating pairs; no multiplier across repetitions or maps.',
    historical_exact_rounds_and_proxy_coverage=coverage,results=results,python=sys.version,numpy=np.__version__,opencv=cv2.__version__,
    hostname=platform.node(),cpu_affinity=[selected],selected_cpu_initial_busy=util[selected],
    baseline_zip_sha256=BUILD['baseline_zip_sha256'],candidate_zip_sha256=BUILD['candidate_zip_sha256'],
    full_matches=0,physics_steps=0,fitting_calls=0,
    decision='STOP_ROUTE_KEEP_V16' if stop else 'OFFLINE_GATE_REACHED_REVIEW_REQUIRED',gate_seconds_per_game=1.,
    notes='Offline snapshot-based weighted comparison; missing historical live inputs prevent a precise original-game total saving claim.'))
assert not any(n=='swarm_rescue' or n.startswith('swarm_rescue.') for n in sys.modules)
print('DECISION','STOP_ROUTE_KEEP_V16' if stop else 'REVIEW',flush=True)

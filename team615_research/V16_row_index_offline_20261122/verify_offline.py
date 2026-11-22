"""Validate actual V16/candidate source with traced point IDs, draw calls and pixels."""
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
from types import ModuleType,SimpleNamespace
import ast,collections,gc,heapq,importlib.abc,json,math,os,statistics,sys,time,typing,warnings

ROOT=Path(__file__).resolve().parent
BUILD=json.loads((ROOT/'BUILD.json').read_text())
BENCHMARK_ONLY='--benchmark-only' in sys.argv
if BENCHMARK_ONLY:
    certified=json.loads((ROOT/'EQUIVALENCE.json').read_text())
    assert certified['status']=='PASS' and certified['candidate_zip_sha256']==BUILD['candidate_zip_sha256']
def save(name,value):(ROOT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')

# Set affinity before importing numeric libraries so their workers inherit it.
def counters():
    out={}
    for line in Path('/proc/stat').read_text().splitlines():
        f=line.split()
        if f[0]=='cpu' or f[0].startswith('cpu') and f[0][3:].isdigit():
            n=list(map(int,f[1:9]));out[f[0]]=(sum(n),n[3]+n[4])
    return out
allowed=sorted(os.sched_getaffinity(0));a=counters();time.sleep(.5);b=counters()
busy={c:1-(b['cpu'+str(c)][1]-a['cpu'+str(c)][1])/max(1,b['cpu'+str(c)][0]-a['cpu'+str(c)][0]) for c in allowed}
chosen=min(allowed,key=lambda c:(busy[c],c));os.sched_setaffinity(0,{chosen})
class BlockSimulation(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.startswith(('swarm_rescue.simulation','swarm_rescue.maps','swarm_rescue.launcher')):
            raise RuntimeError('Simulation imports forbidden in offline validation')
sys.meta_path.insert(0,BlockSimulation())
import numpy as np
import cv2
for name in ['swarm_rescue','swarm_rescue.solutions']:
    module=ModuleType(name);module.__path__=[];sys.modules[name]=module
def load(filename,label):
    archive=ROOT/filename
    assert sha256(archive.read_bytes()).hexdigest()==BUILD['baseline_zip_sha256' if label=='old' else 'candidate_zip_sha256']
    modules={}
    with ZipFile(archive) as z:
        for name in ['line_regularization','bearing_core','submission_wall_fill','submission_renderer']:
            full='swarm_rescue.solutions.'+name;module=ModuleType(full);module.__file__=str(archive)+'/'+name+'.py'
            sys.modules[full]=module;exec(compile(z.read(name+'.py'),module.__file__,'exec'),module.__dict__);modules[name]=module
        tree=ast.parse(z.read('greedy_mapping.py'));node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MapMemory')
        ns=dict(np=np,cv2=cv2,math=math,heapq=heapq,Optional=typing.Optional)
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(archive)+'/MapMemory','exec'),ns)
        tree=ast.parse(z.read('line_regularization.py'))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='regularized_walls')
        subset_line=next(n.lineno for n in fn.body if isinstance(n,ast.For))
        lines={}
        for n in ast.walk(fn):
            if isinstance(n,ast.Assign):
                names=[t.id for t in n.targets if isinstance(t,ast.Name)]
                if 'delta' in names:lines['subset']=n.lineno
            if isinstance(n,ast.If) and isinstance(n.test,ast.Compare):
                test=n.test.left
                if isinstance(test,ast.Call) and isinstance(test.func,ast.Name) and test.func.id=='len' and isinstance(test.args[0],ast.Name) and test.args[0].id=='ids':lines['ids']=n.lineno
    return SimpleNamespace(**modules,Memory=ns['MapMemory'],lines=lines,label=label)
old=load('baseline_snapshot.zip','old');new=load('candidate_snapshot.zip','new')

def arr(value):
    value=np.asarray(value)
    return value.dtype.str,value.shape,value.tobytes()
trace_counts=collections.Counter();checks=[];images_checked=[]
def capture(module,action,expected=None,forced=None):
    records=[] if expected is None else None;position=0;digest=sha256();local=collections.Counter()
    target=module.line_regularization.regularized_walls.__code__
    def emit(kind,value):
        nonlocal position
        item=(kind,value)
        if expected is None:records.append(item)
        else:
            assert position<len(expected),(module.label,'extra trace record',position,kind)
            assert expected[position]==item,(module.label,'trace mismatch',position,kind)
        position+=1;local[kind]+=1
        digest.update(kind.encode());digest.update(repr(value[:2] if isinstance(value,tuple) else value).encode())
        if isinstance(value,tuple) and len(value)==3 and isinstance(value[2],bytes):digest.update(value[2])
    def global_trace(frame,event,arg):
        if event=='call' and frame.f_code is target:
            emit('fit_call',(frame.f_locals['keep_raw'],frame.f_locals['snap_boundary_lines']))
            return trace
        return None
    def trace(frame,event,arg):
        if event=='line':
            for name,line in module.lines.items():
                if frame.f_lineno==line:emit(name,arr(frame.f_locals[name]))
        elif event=='return':emit('fit_mask',arr(arg))
        return trace
    original_hough=cv2.HoughLinesP;original_line=cv2.line
    def hough(mask,*args,**kwargs):
        emit('hough_input',arr(mask));emit('hough_parameters',(args,tuple(sorted(kwargs.items()))))
        result=(None if forced is None else forced.copy()) if forced is not False else original_hough(mask,*args,**kwargs)
        emit('proposals',None if result is None else arr(result));return result
    def line(image,p1,p2,color,thickness,*args,**kwargs):
        caller=sys._getframe(1)
        if caller.f_code is target and isinstance(caller.f_locals.get('first'),np.ndarray):
            emit('fit_float_endpoints',(arr(caller.f_locals['first']),arr(caller.f_locals['last'])))
        emit('line',(tuple(map(int,p1)),tuple(map(int,p2)),int(color),int(thickness)))
        return original_line(image,p1,p2,color,thickness,*args,**kwargs)
    cv2.HoughLinesP=hough;cv2.line=line;cv2.setRNGSeed(615)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore');sys.settrace(global_trace)
            try:output=action()
            finally:sys.settrace(None)
        probe=np.empty((4,7),np.float32);cv2.randu(probe,0,1);emit('following_rng_probe',arr(probe))
    finally:cv2.HoughLinesP=original_hough;cv2.line=original_line;sys.settrace(None)
    if expected is not None:assert position==len(expected),(position,len(expected))
    trace_counts.update(local)
    return output,records,dict(local),digest.hexdigest()
def compare(name,make_action,forced=False,expected_image=None):
    if BENCHMARK_ONLY:return None
    before,records,counts,_=capture(old,make_action(old),forced=forced)
    after,_,other,_=capture(new,make_action(new),expected=records,forced=forced)
    assert arr(before)==arr(after),(name,'output pixels')
    assert counts==other
    if expected_image is not None:
        assert np.packbits(before.astype(bool).ravel()).tobytes()==expected_image,(name,'stored V16 original image')
    checks.append(dict(name=name,**counts,pixel_sha256=sha256(np.asarray(before).tobytes()).hexdigest(),
                       matches_existing_V16_original=expected_image is not None))
    del records
    return before

rng=np.random.default_rng(615)
for i in range(60):
    h,w=[(64,96),(97,81),(48,65)][i%3]
    hits=rng.integers(0,5,(h,w),dtype=np.uint8)
    if i%2==0:hits[h//3:2*h//3,:]=0
    proposals=[]
    for _ in range(20):
        p=rng.integers(-25,max(w,h)+25,4,dtype=np.int32)
        if p[0]==p[2] and p[1]==p[3]:p[2]+=1
        proposals.append(p)
    proposals=np.asarray(proposals,np.int32).reshape(-1,1,4)
    options=dict(fit_band=[6,10,.25,-10][i%4],covariance_limit=30,duplicate_distance=8,
                 keep_raw=bool(i%2),snap_boundary_lines=bool(i%3==0))
    compare(f'forced_random_{i:02d}',lambda m,hits=hits,options=options:lambda:m.line_regularization.regularized_walls(hits,**options),forced=proposals)

# Horizontal/vertical/diagonal/reversed/edge/outside/zero-length proposals and row gaps.
hits=np.zeros((80,96),np.uint8)
hits[[0,1,20,39,40,59,78,79],:]=5;hits[:,[0,1,30,47,94,95]]=5
proposals=np.array([[0,0,95,0],[0,79,95,79],[0,0,0,79],[95,79,95,0],
 [0,0,79,79],[79,79,0,0],[0,40,95,40],[95,39,0,39],[-100,-100,-10,-10],
 [200,200,250,260],[20,20,20,20],[-10,79,110,79],[0,10,95,70]],np.int32).reshape(-1,1,4)
for band in [0,.5,6,10,float('nan'),float('inf'),-float('inf')]:
    compare('edges_band_'+str(band),lambda m,band=band:lambda:m.line_regularization.regularized_walls(hits,fit_band=band,keep_raw=False),forced=proposals)
compare('no_proposals',lambda m:lambda:m.line_regularization.regularized_walls(hits),forced=None)
compare('no_wall_points',lambda m:lambda:m.line_regularization.regularized_walls(np.zeros_like(hits),keep_raw=False),forced=proposals)
compare('single_row',lambda m:lambda:m.line_regularization.regularized_walls(np.full((1,96),4,np.uint8),keep_raw=False),forced=proposals)
compare('strided_fortran_input',lambda m:lambda:m.line_regularization.regularized_walls(np.asfortranarray(hits)[::2,::-1],keep_raw=False),forced=proposals)
for i in range(12):
    data=np.zeros((128,160),np.uint8)
    cv2.line(data,(0,i+8),(159,i+8),7,2);cv2.line(data,(30,0),(30,127),8,2)
    cv2.line(data,(4,120),(145,10),5,1)
    options=dict(keep_raw=bool(i%2),snap_boundary_lines=bool(i%3==0),line_width=3+i,fit_band=[6,10][i%2])
    compare(f'native_hough_lines_{i:02d}',lambda m,data=data,options=options:lambda:m.line_regularization.regularized_walls(data,**options))

for name,changes in [('cache_hit',{}),('width_only',{'line_width':13}),('different_hits',{'change_hits':True}),
                      ('different_mask',{'change_mask':True}),('different_fit_band',{'fit_band':6})]:
    def action(module,changes=changes):
        def run():
            cache=module.line_regularization.PlanningWallFit();data=hits.copy();mask=(data>0).astype(np.uint8)
            module.line_regularization.regularized_walls(data,keep_raw=False,line_width=8,fit_band=10,_planning_fit=cache,proposal_mask=mask)
            if changes.get('change_hits'):data[10:15,:]=4
            if changes.get('change_mask'):mask[10:15,:]=1
            result=module.line_regularization.regularized_walls(data,keep_raw=False,line_width=changes.get('line_width',8),
                  fit_band=changes.get('fit_band',10),_planning_fit=cache,proposal_mask=mask)
            return result
        return run
    compare(name,action)

fixtures={};fixture_receipts={}
for cohort in ['Map06','Map08','Map09']:
    meta=json.loads((ROOT/'fixtures'/f'{cohort}_metadata.json').read_text())
    fixture_receipts[cohort]={p.name:sha256(p.read_bytes()).hexdigest() for p in (ROOT/'fixtures').glob(cohort+'_*')}
    cases=[]
    with np.load(ROOT/'fixtures'/f'{cohort}_data.npz',allow_pickle=False) as data:
        for owner in range(5):
            md=meta[str(owner)];w,h=md['width'],md['height']
            packet=tuple(data[f'd{owner}_snapshot{owner}_{n}'].copy() for n in ['indices','values','free','visits'])
            bits=data[f'd{owner}_snapshot{owner}_bearings'].copy()
            expected=data[f'd{owner}_image{owner}'].tobytes()
            def prepare(module,packet=packet,bits=bits,w=w,h=h):
                memory=module.Memory(w,h);memory.merge(packet)
                bearing=module.submission_renderer.SubmissionBearings(w,h);bearing.bits=bits.copy()
                return lambda:bearing.render(memory)
            compare(f'{cohort}_frozen_drone{owner}',prepare,expected_image=expected)
            cases.append(dict(owner=owner,old=prepare(old),new=prepare(new)))
            print('SNAPSHOT_EQ_PASS',cohort,owner,flush=True)
        # Final received-packet reconstruction is a separate equivalence input, not a historical live replay.
        md=meta['0'];w,h=md['width'],md['height']
        packet=tuple(data[f'd0_final_{n}'].copy() for n in ['indices','values','free','visits'])
        bits=data['d0_final_bearings'].copy()
        compare(cohort+'_final_packet_reconstruction',lambda module,packet=packet,bits=bits,w=w,h=h:
                (lambda memory,bearing:(lambda:bearing.render(memory)))(
                    (lambda memory:(memory.merge(packet),memory)[1])(module.Memory(w,h)),
                    (lambda bearing:(setattr(bearing,'bits',bits.copy()),bearing)[1])(module.submission_renderer.SubmissionBearings(w,h))))
    fixtures[cohort]=cases
if not BENCHMARK_ONLY:
 save('EQUIVALENCE.json',dict(status='PASS',cases=len(checks),checks=checks,trace_counts_both_versions=dict(trace_counts),
    subset_and_ids_checked_for_every_proposal=True,drawn_line_sequence_and_pixels_checked=True,native_rng_probe_checked=True,
    existing_V16_frozen_originals_matched=15,final_packet_reconstruction_inputs=3,
    baseline_zip_sha256=BUILD['baseline_zip_sha256'],candidate_zip_sha256=BUILD['candidate_zip_sha256'],
    fixture_hashes=fixture_receipts,full_matches=0,physics_steps=0,
    note='Frozen originals are actual stored render inputs. Final-packet inputs omit unsaved count-one cells and are explicitly reconstructed, not historical live replays.'))
print('REUSED_BOUND_EQUIVALENCE' if BENCHMARK_ONLY else 'EQUIVALENCE PASS',
      certified['cases'] if BENCHMARK_ONLY else len(checks),json.dumps(dict(trace_counts)),flush=True)

def render_counts(cohort):
    details=json.loads((ROOT/'fixtures'/f'{cohort}_score.json').read_text())['drone_details']
    with ZipFile(ROOT/'fixtures'/f'{cohort}_recording.npz') as z:
        raw=z.read('timestamps.npy');width=2 if raw[6]==1 else 4;n=int.from_bytes(raw[8:8+width],'little')
        times=np.frombuffer(raw[8+width+n:],dtype='<f8')
    per={};frames=collections.Counter();parts=collections.Counter()
    for drone in details:
        live=-1;last=-1;count=0
        for e in drone['group_candidate_audit']:
            step,kind=e[:2]
            if kind=='snapshot_frozen' or kind=='payload_stored' and e[3]=='snapshot':last=step
            elif kind=='live_candidate_cached':live=step;count+=1;frames[step]+=1;parts['live_or_finish']+=1
            elif kind=='image_built':
                if e[2]==drone['drone']:count+=1;frames[step]+=1;parts['frozen_original']+=1
                elif e[2]==5:
                    wall=times[step-3] if step>=3 else 0
                    if step<4590 and 180-wall>8 and live<last:count+=1;frames[step]+=1;parts['new_fusion']+=1
        per[drone['drone']]=count
    heavy=int(sum(times[s-2]-times[s-3]>.5 for s in frames if s>=3))
    return dict(per_drone=per,total=sum(per.values()),parts=dict(parts),render_frames=len(frames),heavy_render_frames=heavy)

results={};all_samples={}
for cohort,cases in fixtures.items():
    counts=render_counts(cohort);samples=[]
    for case in cases:
        cv2.setRNGSeed(615);case['old']();cv2.setRNGSeed(615);case['new']()
        pairs=[];before=counters();load=os.getloadavg();gc.disable()
        try:
            for iteration in range(6):
                row={}
                for label in (['old','new'] if iteration%2==0 else ['new','old']):
                    wall=time.perf_counter_ns();cpu=time.process_time_ns();image=case[label]()
                    row[label]=dict(wall_seconds=(time.perf_counter_ns()-wall)/1e9,cpu_seconds=(time.process_time_ns()-cpu)/1e9)
                pairs.append(row)
        finally:gc.enable()
        after=counters();delta=after['cpu'][0]-before['cpu'][0];idle=after['cpu'][1]-before['cpu'][1]
        sample=dict(owner=case['owner'],original_median_seconds=statistics.median(p['old']['wall_seconds'] for p in pairs),
             candidate_median_seconds=statistics.median(p['new']['wall_seconds'] for p in pairs),
             median_paired_saved_seconds=statistics.median(p['old']['wall_seconds']-p['new']['wall_seconds'] for p in pairs),
             paired_saved_min_seconds=min(p['old']['wall_seconds']-p['new']['wall_seconds'] for p in pairs),
             paired_saved_max_seconds=max(p['old']['wall_seconds']-p['new']['wall_seconds'] for p in pairs),
             original_cpu_median_seconds=statistics.median(p['old']['cpu_seconds'] for p in pairs),
             candidate_cpu_median_seconds=statistics.median(p['new']['cpu_seconds'] for p in pairs),
             system_cpu_busy_percent=100*(1-idle/delta),load_average=load,samples=pairs)
        samples.append(sample)
        print('BENCH',cohort,case['owner'],sample['original_median_seconds'],sample['candidate_median_seconds'],
              'saved',sample['median_paired_saved_seconds'],flush=True)
    weighted=sum(s['median_paired_saved_seconds']*counts['per_drone'][s['owner']] for s in samples)
    heavy_proxy=counts['heavy_render_frames']*min(s['median_paired_saved_seconds'] for s in samples)
    results[cohort]=dict(log_counts=counts,per_snapshot=samples,call_count_weighted_saved_seconds=weighted,
        heavy_frames_one_call_minimum_snapshot_saving_scenario_seconds=heavy_proxy,
        offline_one_second_gate_passed=weighted>=1)
all_pass=all(r['offline_one_second_gate_passed'] for r in results.values())
save('BENCHMARK.json',dict(status='COMPLETE',results=results,python=sys.version,numpy=np.__version__,opencv=cv2.__version__,
    opencv_threads=cv2.getNumThreads(),fixed_logical_cpu=chosen,selected_cpu_initial_busy=busy[chosen],
    paired_batches_per_snapshot=6,baseline_zip_sha256=BUILD['baseline_zip_sha256'],candidate_zip_sha256=BUILD['candidate_zip_sha256'],
    gate_seconds_per_game=1,decision='OFFLINE_GATE_PASSED_NO_MATCH_AUTHORIZED' if all_pass else 'STOP_ROUTE_KEEP_V16',
    full_matches=0,physics_steps=0,
    method='Untraced complete V16/candidate renderer; alternating paired batches on the same inherited CPU affinity. Exact frozen snapshots; weighted with per-drone render-call counts from logs. Not an exact historical whole-game timing replay.',
    caveat='Historical live render inputs were not saved for every call. Weighted savings extrapolate frozen-snapshot timings. Heavy-frame scenario counts at most one call per >0.5s render frame and uses the smallest sampled saving; it is a scenario, not a formal lower bound.'))
assert not any(n.startswith(('swarm_rescue.simulation','swarm_rescue.maps','swarm_rescue.launcher')) for n in sys.modules)
print('DECISION','OFFLINE_GATE_PASSED_NO_MATCH_AUTHORIZED' if all_pass else 'STOP_ROUTE_KEEP_V16',flush=True)

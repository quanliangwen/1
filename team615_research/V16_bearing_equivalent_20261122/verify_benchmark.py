"""Exact pure-function comparisons and paired timings; no simulator imports."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
import argparse
import gc
import importlib.abc
import json
import os
import platform
import statistics
import sys
import time
import types
import warnings

class NoSimulation(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='swarm_rescue' or fullname.startswith('swarm_rescue.'):
            raise RuntimeError('Simulator import is forbidden in this pure-function test')
sys.meta_path.insert(0,NoSimulation())
import numpy as np
import cv2

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--verify-only',action='store_true');args=parser.parse_args()
build=json.loads((ROOT/'BUILD.json').read_text())
def save(name,obj):(ROOT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def load(archive,label):
    assert sha256(archive.read_bytes()).hexdigest()==build['baseline_zip_sha256' if label=='old' else 'candidate_zip_sha256']
    with ZipFile(archive) as z:code=z.read('bearing_core.py')
    module=types.ModuleType(label);module.__file__=str(archive)+'/bearing_core.py'
    exec(compile(code,module.__file__,'exec'),module.__dict__)
    return module
old=load(ROOT/'baseline_snapshot.zip','old');new=load(ROOT/'candidate_snapshot.zip','new')
checks=[]
def identical(a,b,path='result'):
    assert type(a)==type(b),(path,type(a),type(b))
    if isinstance(a,np.ndarray):
        assert a.dtype==b.dtype and a.shape==b.shape,(path,a.dtype,b.dtype,a.shape,b.shape)
        assert a.tobytes()==b.tobytes(),path
        assert a.flags.writeable==b.flags.writeable,path
    elif isinstance(a,(tuple,list)):
        assert len(a)==len(b),path
        for i,(x,y) in enumerate(zip(a,b)):identical(x,y,path+f'[{i}]')
    elif isinstance(a,dict):
        assert a.keys()==b.keys(),path
        for k in a:identical(a[k],b[k],path+f'[{k}]')
    else:assert a==b,path
def check(name,function,*values,**kwargs):
    inputs=[(v,v.tobytes()) for v in values if isinstance(v,np.ndarray)]
    def run(module):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                return ('value',getattr(module,function)(*values,**kwargs))
        except Exception as exc:return ('exception',type(exc).__name__,str(exc))
    a,b=run(old),run(new);identical(a,b,name)
    for value,data in inputs:assert value.tobytes()==data,(name,'input mutated')
    checks.append(name)

rng=np.random.default_rng(615)
combos=np.arange(256,dtype=np.uint8)
check('all_256_vector','independent_incidence',combos)
check('all_256_matrix','independent_incidence',combos.reshape(16,16))
for value in range(256):check(f'scalar_{value:03d}','independent_incidence',value)
for name,value in [('empty',(np.empty((0,9),np.uint8))),('empty_1d',np.empty(0,np.uint8)),
    ('strided',rng.integers(0,256,(43,29),dtype=np.uint8)[::2,::-3]),
    ('fortran',np.asfortranarray(rng.integers(0,256,(19,17),dtype=np.uint8))),
    ('list',[0,1,3,5,129,255]),('zero_dim',np.array(5,np.uint8)),
    ('wide_dtype',np.array([0,1,255,256,511],np.uint16)),('bool',np.array([False,True]))]:
    check(name,'independent_incidence',value)

def hit(name,p=(.25,.25),heading=0.,d=None,a=None,e=None,w=1700,h=1100):
    d=np.asarray([100.,100.,100.] if d is None else d)
    a=np.asarray(np.zeros(d.shape) if a is None else a)
    e=np.asarray(np.zeros(d.shape,bool) if e is None else e)
    check(name,'hit_direction_bits',p,heading,d,a,e,w,h)

hit('empty_rays',d=[])
hit('duplicate_cells',d=np.full(720,100.),a=np.zeros(720))
hit('same_cell_different_sectors',d=np.full(40,100.),a=np.tile([np.pi/4-1e-12,np.pi/4+1e-12],20))
hit('same_cell_wrap_sectors',d=np.full(40,100.),a=np.tile([-1e-12,1e-12],20))
hit('excluded_all',e=[1,1,1])
hit('all_outside',p=(1e6,1e6))
hit('distance_thresholds',d=[8,np.nextafter(8.,np.inf),219.999999999,220,np.nextafter(220.,0),0,-1,np.nan,np.inf,-np.inf])
hit('nonfinite_angles',a=[np.nan,np.inf,-np.inf])
hit('invalid_heading',heading=np.nan)
hit('invalid_pose',p=(np.nan,0))
hit('wrong_pose_shape',p=(0,))
hit('wrong_angle_shape',a=[0])
hit('wrong_excluded_shape',e=[0])
hit('two_dim_rays',d=np.zeros((2,2)))
hit('zero_width',w=0)
hit('negative_height',h=-1)
sectors=np.arange(-16,17,dtype=float)*np.pi/4
angle_edges=np.concatenate([sectors,np.nextafter(sectors,np.inf),np.nextafter(sectors,-np.inf)])
hit('sector_edges',d=np.full(angle_edges.size,60.),a=angle_edges)
for i,(w,h) in enumerate([(1,1),(3,5),(7,9),(1700,1100),(1660,1122)]):
    for j,p in enumerate([(-w/2,-h/2),(w/2,h/2),(0,0),(-w/2+.001,h/2-.001)]):
        hit(f'map_boundary_{i}_{j}',p=p,w=w,h=h,d=np.full(360,10.),a=np.linspace(-np.pi,np.pi,360,endpoint=False))
for i in range(2500):
    w,h=[(1700,1100),(1660,1122),(7,9),(64,63)][i%4]
    n=int(rng.integers(0,721));d=rng.uniform(-10,310,n);a=rng.uniform(-20*np.pi,20*np.pi,n)
    if n and i%3==0:
        d[:min(n,20)]=100.;a[:min(n,20)]=np.pi/4
    if n>5 and i%7==0:d[[0,1]]=np.nan,np.inf;a[[2,3]]=np.nan,np.inf
    hit(f'random_hit_{i:04d}',p=rng.uniform([-w*.65,-h*.65],[w*.65,h*.65]),heading=float(rng.uniform(-100,100)),
        d=d,a=a,e=rng.random(n)<.12,w=w,h=h)
for i in range(100):
    check(f'random_incidence_{i:03d}','independent_incidence',rng.integers(0,256,(71,79),dtype=np.uint8)[::2,::3])

fixtures=[]
for name in ('Map06','Map08','Map09'):
    meta=json.loads((ROOT/'fixtures'/f'{name}_metadata.json').read_text());w,h=meta['0']['width'],meta['0']['height']
    with np.load(ROOT/'fixtures'/f'{name}.npz',allow_pickle=False) as data:
        for owner in range(5):
            bits=data[f'd{owner}_final_bearings'].copy()
            check(f'{name}_drone{owner}_actual_direction_evidence','independent_incidence',bits)
            fixtures.append((name,owner,w,h,bits))
for i in range(40):
    w,h=65,67
    parent=(rng.random((h,w))>.90).astype(np.uint8)
    hits=rng.integers(0,6,((h+1)//2,(w+1)//2),dtype=np.uint8)
    bits=rng.integers(0,256,((h+3)//4,(w+3)//4),dtype=np.uint8)
    check(f'corroborated_map_output_{i:02d}','corroborated_map',parent,hits,bits,w,h)
save('EQUIVALENCE.json',dict(status='PASS',baseline_zip_sha256=build['baseline_zip_sha256'],candidate_zip_sha256=build['candidate_zip_sha256'],
     checks=len(checks),direction_combinations_exhausted=256,random_hit_cases=2500,actual_V16_direction_arrays=15,
     pixel_map_integration_cases=40,array_type_shape_dtype_bytes_and_input_immutability=True,scenarios=checks,
     simulator_import_blocked=True,full_matches=0,physics_steps=0))
print('EQUIVALENCE PASS',len(checks),'checks',flush=True)
if args.verify_only:raise SystemExit(0)

def cpu():
    nums=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));return sum(nums),nums[3]+nums[4]
def timed(fn,values,loops):
    wall=time.perf_counter_ns();process=time.process_time_ns()
    for _ in range(loops):fn(*values)
    return dict(wall_ns_per_call=(time.perf_counter_ns()-wall)/loops,
                cpu_ns_per_call=(time.process_time_ns()-process)/loops)
def bench(name,function,values,minimum_loops=30):
    for _ in range(6):getattr(old,function)(*values);getattr(new,function)(*values)
    probe=timed(getattr(old,function),values,10)['wall_ns_per_call']
    loops=max(minimum_loops,min(1000,int(40_000_000/max(probe,1))))
    samples=[];s0=cpu();start=time.time();load=os.getloadavg()
    enabled=gc.isenabled();gc.disable()
    try:
        for i in range(12):
            row={}
            for label in (('old','new') if i%2==0 else ('new','old')):
                row[label]=timed(getattr(old if label=='old' else new,function),values,loops)
            samples.append(row)
    finally:
        if enabled:gc.enable()
    s1=cpu();busy=100.*(1-(s1[1]-s0[1])/(s1[0]-s0[0]))
    old_us=statistics.median(r['old']['wall_ns_per_call']/1000 for r in samples)
    new_us=statistics.median(r['new']['wall_ns_per_call']/1000 for r in samples)
    old_cpu=statistics.median(r['old']['cpu_ns_per_call']/1000 for r in samples)
    new_cpu=statistics.median(r['new']['cpu_ns_per_call']/1000 for r in samples)
    return dict(name=name,function=function,loops_per_batch=loops,paired_batches=12,alternating_order=True,
                old_median_us=old_us,new_median_us=new_us,speedup=old_us/new_us,reduction_percent=100*(1-new_us/old_us),
                old_cpu_median_us=old_cpu,new_cpu_median_us=new_cpu,
                median_paired_speedup=statistics.median(r['old']['wall_ns_per_call']/r['new']['wall_ns_per_call'] for r in samples),
                system_cpu_busy_percent=busy,load_average_at_start=load,start_unix=start,end_unix=time.time(),samples=samples)

# Bind both implementations to the same otherwise idle logical CPU, selected before timing.
available=sorted(os.sched_getaffinity(0))
def core_times():
    out={}
    for line in Path('/proc/stat').read_text().splitlines():
        fields=line.split()
        if fields[0].startswith('cpu') and fields[0][3:].isdigit():
            vals=list(map(int,fields[1:9]));out[int(fields[0][3:])]=(sum(vals),vals[3]+vals[4])
    return out
t0=core_times();time.sleep(.5);t1=core_times()
util={c:1-(t1[c][1]-t0[c][1])/max(1,t1[c][0]-t0[c][0]) for c in available}
selected=min(available,key=lambda c:(util[c],c));os.sched_setaffinity(0,{selected})
benchmarks=[]
for name,w,h in [('Map06',1700,1100),('Map08',1660,1122),('Map09',1700,1100)]:
    for rays in (181,360):
        # 181 inclusive angles match SDK RESOLUTION_LIDAR_SENSOR/compute_ray_angles.
        angles=np.linspace(-np.pi,np.pi,rays)
        for mode in ('mixed','duplicate'):
            distances=(np.full(rays,100.) if mode=='duplicate' else rng.uniform(9.,219.,rays))
            aa=np.zeros(rays) if mode=='duplicate' else angles
            values=(np.array([.25,.25]),.37,distances,aa,np.zeros(rays,bool),w,h)
            identical(old.hit_direction_bits(*values),new.hit_direction_bits(*values))
            benchmarks.append(bench(name+f'_{rays}_'+mode,'hit_direction_bits',values))
for name,owner,w,h,bits in fixtures:
    if owner==0:benchmarks.append(bench(name+'_actual_drone0','independent_incidence',(bits,)))
benchmarks.append(bench('scalar','independent_incidence',(5,)))
codes={}
for label,archive in [('old','baseline_snapshot.zip'),('new','candidate_snapshot.zip')]:
    with ZipFile(ROOT/archive) as z:codes[label]=compile(z.read('bearing_core.py'),archive+'/bearing_core.py','exec')
imports={label:[] for label in codes}
for repeat in range(30):
    for label in (('old','new') if repeat%2==0 else ('new','old')):
        module=types.ModuleType(label);t=time.perf_counter_ns();exec(codes[label],module.__dict__)
        imports[label].append((time.perf_counter_ns()-t)/1000)
assert not any(name=='swarm_rescue' or name.startswith('swarm_rescue.') for name in sys.modules)
save('BENCHMARK.json',dict(status='COMPLETE',baseline_zip_sha256=build['baseline_zip_sha256'],candidate_zip_sha256=build['candidate_zip_sha256'],
     python=sys.version,executable=sys.executable,numpy=np.__version__,opencv=cv2.__version__,hostname=platform.node(),
     platform=platform.platform(),selected_cpu=selected,selected_cpu_initial_busy_fraction=util[selected],
     initial_affinity=available,thread_environment={k:os.environ.get(k) for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','LP_NUM_THREADS']},
     method='resident functions; identical inputs; 12 alternating old/new paired batches; median wall and CPU time; pre-generated fixtures',
     module_import_and_lookup_initialization_excluded=True,benchmarks=benchmarks,full_matches=0,physics_steps=0,simulator_import_blocked=True))
data=json.loads((ROOT/'BENCHMARK.json').read_text())
data['module_execution_after_dependencies_loaded_median_us']={label:statistics.median(values) for label,values in imports.items()}
data['sdk_ray_count']=181
save('BENCHMARK.json',data)
print(json.dumps([{k:r[k] for k in ['name','old_median_us','new_median_us','speedup','reduction_percent']} for r in benchmarks],indent=2),flush=True)

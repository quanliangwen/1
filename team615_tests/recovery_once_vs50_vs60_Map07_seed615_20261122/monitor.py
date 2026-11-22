"""User-authorized fixed idle physical-core comparison, exactly one match per arm."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import os
import platform
import subprocess
import time

ROOT=Path(__file__).resolve().parent
LOCK='/home/junhao/quan/parallel_test_solver/match/solver_study/serial_evaluation.lock'
CORE_COUNT=16
previous=None
def now():return datetime.now(timezone.utc).isoformat()
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def status(value):save(ROOT/'STATUS.json',dict(utc=now(),**value))
def counters():
    out={}
    for line in Path('/proc/stat').read_text().splitlines():
        fields=line.split()
        if fields[0]=='cpu' or fields[0].startswith('cpu') and fields[0][3:].isdigit():
            values=list(map(int,fields[1:9]));out[fields[0]]=(sum(values),values[3]+values[4])
    return out
def sample(cpus=()):
    global previous
    values=counters();busy=None;per_core={};stamp=time.monotonic()
    if previous is not None:
        for key in ['cpu']+['cpu'+str(c) for c in cpus]:
            total=values[key][0]-previous[key][0];idle=values[key][1]-previous[key][1]
            percent=100.*(total-idle)/total if total else 0.
            if key=='cpu':busy=percent
            else:per_core[key]=percent
    previous=values
    load=Path('/proc/loadavg').read_text().split()
    pressure={n:(Path('/proc/pressure')/n).read_text().strip() for n in ['cpu','memory','io']}
    return dict(utc=now(),monotonic=stamp,cpu_busy_percent=busy,load1=float(load[0]),load5=float(load[1]),
                load15=float(load[2]),runnable=load[3],pressure=pressure,selected_cpu_busy_percent=per_core)
def process_sample(pid,detailed):
    try:
        p=Path('/proc')/str(pid);raw=(p/'stat').read_text();f=raw[raw.rfind(')')+2:].split()
        result=dict(pid=pid,state=f[0],user_seconds=int(f[11])/os.sysconf('SC_CLK_TCK'),
                    system_seconds=int(f[12])/os.sysconf('SC_CLK_TCK'),threads=int(f[17]),cpu=int(f[36]),
                    rss_bytes=int(f[21])*os.sysconf('SC_PAGE_SIZE'))
        if detailed:
            total=[0,0,0];count=0
            for task in (p/'task').iterdir():
                try:
                    v=list(map(int,(task/'schedstat').read_text().split()));total=[x+y for x,y in zip(total,v)];count+=1
                except (FileNotFoundError,ProcessLookupError):pass
            result['thread_schedstat_sum']=dict(runtime_ns=total[0],runqueue_wait_ns=total[1],timeslices=total[2],read_threads=count)
            result['allowed_cpu_list']=[s for s in (p/'status').read_text().splitlines() if s.startswith('Cpus_allowed_list')]
        return result
    except (FileNotFoundError,ProcessLookupError):return None

maps=['Map07'];COUNT=8
with (ROOT/'DISPATCH_ONCE_CLAIM').open('x'):pass
for name in maps:assert not any((ROOT/name/n).exists() for n in ['START.json','RUN_ONCE_CLAIM','SDK_PID'])
save(ROOT/'HOST.json',dict(utc=now(),hostname=platform.node(),platform=platform.platform(),logical_cpus=os.cpu_count(),cpuinfo=Path('/proc/cpuinfo').read_text().split('\n\n')[0]))
queue=(ROOT/'queue_resources.jsonl').open('x',buffering=1);completed=[];lock=None
try:
    allowed=sorted(os.sched_getaffinity(0));groups={}
    for cpu in allowed:
        p=Path('/sys/devices/system/cpu')/f'cpu{cpu}'/'topology'
        key=int((p/'physical_package_id').read_text()),int((p/'core_id').read_text())
        groups.setdefault(key,[]).append(cpu)
    for name in maps:
        stage=ROOT/name
        status(dict(state='WAITING_SHARED_SLOT',map=name,completed_maps=completed))
        lock=open(LOCK,'r');fcntl.flock(lock,fcntl.LOCK_EX)
        while True:
            status(dict(state='SELECTING_8_IDLE_CPUS',map=name,completed_maps=completed))
            maximum={c:0. for c in allowed};sample(allowed)
            for _ in range(3):
                time.sleep(2);row=sample(allowed);queue.write(json.dumps(dict(map=name,**row))+'\n')
                for c in allowed:maximum[c]=max(maximum[c],row['selected_cpu_busy_percent']['cpu'+str(c)])
            by_socket={}
            for key,items in groups.items():
                if any(maximum[c]<=5 for c in items):by_socket.setdefault(key[0],[]).append((key,items))
            viable=[(s,sorted(v,key=lambda x:x[0],reverse=True)) for s,v in by_socket.items() if len(v)>=COUNT]
            if not viable:
                status(dict(state='WAITING_8_IDLE_CORES',map=name,completed_maps=completed,idle_physical_cores={s:len(v) for s,v in by_socket.items()}));continue
            socket,selected=min(viable,key=lambda x:(-len(x[1]),x[0]));selected=selected[:COUNT]
            cpus=sorted(min(v,key=lambda c:(maximum[c],c)) for _,v in selected);siblings=sorted(c for _,v in selected for c in v);break
        save(stage/'AFFINITY_SELECTION.json',dict(utc=now(),physical_cores=8,logical_cpus=cpus,sibling_cpus_monitored=siblings,socket=socket,core_topology=[dict(socket=k[0],core=k[1],siblings=v,assigned_cpu=min(v,key=lambda c:(maximum[c],c))) for k,v in selected],maximum_preselection_busy_percent={str(c):maximum[c] for c in siblings},note='Exactly 8 idle assigned logical CPUs from 8 distinct physical cores; SMT sibling threads may be busy. Affinity is not exclusive. Historical reference load differs.'))
        save(stage/'MONITOR_CONFIG.json',dict(mode='8_ASSIGNED_CPU_MAP_TEST',global_load_is_admission_gate=False,logical_cpus=cpus,physical_cores=8,selection_idle_cpu_max_percent=5,selection_samples=3,selection_interval_seconds=2,run_sample_seconds=1,sibling_cpu_idle_required=False,lock=LOCK,monitor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),retry=False))
        save(stage/'ADMISSION.json',dict(mode='8_ASSIGNED_CPU_MAP_TEST',admission=row,logical_cpus=cpus,sibling_cpus_monitored=siblings,global_load_is_admission_gate=False,lock_acquired=True))
        status(dict(state='RUNNING',map=name,seed=615,completed_maps=completed,logical_cpus=cpus))
        with (stage/'dispatch.log').open('x') as out,(stage/'resources.jsonl').open('x',buffering=1) as stream:
            proc=subprocess.Popen(['bash',str(stage/'run_monitored.sh'),str(stage)],cwd=stage,stdout=out,stderr=subprocess.STDOUT,preexec_fn=lambda:os.sched_setaffinity(0,set(cpus)))
            index=0;pid=None
            while proc.poll() is None:
                row=sample(siblings)
                if (stage/'SDK_PID').exists():pid=int((stage/'SDK_PID').read_text())
                row['test_process']=process_sample(pid,index%5==0) if pid else None
                stream.write(json.dumps(row)+'\n');index+=1;time.sleep(1)
            code=proc.wait()
        fcntl.flock(lock,fcntl.LOCK_UN);lock.close();lock=None
        save(stage/'MONITOR_FINISH.json',dict(utc=now(),returncode=code,pid=pid,samples=index,logical_cpus=cpus))
        if code or not (stage/'POST_RUN_SOURCE_CHECK.json').exists():raise RuntimeError(name+' failed; no automatic rerun')
        completed.append(name);save(stage/'STATUS.json',dict(state='COMPLETE',map=name,seed=615,new_red_rounds=1))
    status(dict(state='COMPLETE',maps=['Map07'],seed=615,completed_maps=completed,new_red_rounds=1))
except BaseException as exc:
    status(dict(state='FAILED',error=repr(exc),completed_maps=completed,no_automatic_rerun=True));raise
finally:
    if lock is not None:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
    queue.close()

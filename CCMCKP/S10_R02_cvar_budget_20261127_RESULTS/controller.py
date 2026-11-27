"""Frozen real large-case trial; no expansion, retries or algorithm changes."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import time
import threading

H=Path(__file__).resolve().parent
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP')
assert B.resolve() in H.resolve().parents
assert B==Path('/home/junhao/quan/parallel_test_solver/CCMKCP')
P=json.loads((H/'PROTOCOL.json').read_text())
PROTOCOL_BYTES=(H/'PROTOCOL.json').read_bytes()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):
    temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w') as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    temporary.replace(path)
def utc(): return datetime.now(timezone.utc).isoformat()
def memory():
    values={s.split(':',1)[0]:int(s.split()[1])*1024 for s in Path('/proc/meminfo').read_text().splitlines()}
    return values['MemAvailable']
def rss(pid):
    try:
        return int(next(s.split()[1] for s in Path('/proc/%s/status'%pid).read_text().splitlines() if s.startswith('VmRSS:')))*1024
    except (OSError,StopIteration): return 0
def command(pid):
    try:return Path('/proc/%s/cmdline'%pid).read_bytes().split(b'\0')
    except OSError:return []
def freeze():
    if (H/'PROTOCOL.json').read_bytes()!=PROTOCOL_BYTES: raise RuntimeError('Protocol changed during run')
    for name,expected in P['source_and_binary_pins'].items():
        if sha(H/name)!=expected: raise RuntimeError('Frozen source mismatch '+name)
    for name,expected in P['input_pins'].items():
        if sha(B/name)!=expected: raise RuntimeError('Frozen input mismatch '+name)

lock=(H/'CONTROLLER.lock').open('a+')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
if (H/'LAUNCH.json').exists():raise RuntimeError('Refuse duplicate controller or implicit restart')
freeze()
started=time.monotonic()
registration={'pid':os.getpid(),'utc':utc(),'protocol_sha256':sha(H/'PROTOCOL.json'),
    'max_workers':P['max_workers'],'tasks':P['total_runs'],'not_resuming_old_tasks':True}
write(H/'LAUNCH.json',registration)

tasks=[]
for rep in range(1,P['repetitions']+1):
    for case in P['cases']:
        arms=P['arms']
        shift=(rep+case['index'])%len(arms)
        for arm in arms[shift:]+arms[:shift]:
            tasks.append({'case':case,'rep':rep,'seed':P['seed_base']+rep,'arm':arm})
active={}
done=[]
pilot_verified=False
stop=False
resource_events=[]
def request_stop(signum,frame):
    global stop
    stop=True
signal.signal(signal.SIGTERM,request_stop)
signal.signal(signal.SIGINT,request_stop)
def terminate(item,reason):
    if item.get('termination_at'): return
    process=item['process']
    expected=str(item['binary']).encode()
    if process.poll() is None and expected in command(process.pid):
        os.killpg(process.pid,signal.SIGTERM)
        item['termination_reason']=reason
        item['termination_at']=time.monotonic()

last_state=0
max_active=0
try:
    while tasks or active:
        available=memory()
        total_rss=0
        reserve=0
        for identity,item in list(active.items()):
            process=item['process']
            resident=rss(process.pid)
            item['peak_rss_bytes']=max(item['peak_rss_bytes'],resident)
            total_rss+=resident
            reserve+=max(0,P['worker_reserve_bytes']-resident)
            elapsed=item.get('exited_monotonic',time.monotonic())-item['started']
            if item.get('termination_at') and process.poll() is None and time.monotonic()-item['termination_at']>8:
                if str(item['binary']).encode() in command(process.pid): os.killpg(process.pid,signal.SIGKILL)
            if resident>P['single_rss_limit_bytes']:
                terminate(item,'single_rss_limit')
            rc=process.poll()
            if rc is not None and 'exited_monotonic' in item:
                item['log'].close()
                record={k:item[k] for k in ['identity','case_index','instance','capacity','arm','rep','seed','pid','started_utc','peak_rss_bytes']}
                record.update({'rc':rc,'ended_utc':utc(),'process_wall_seconds':elapsed,
                    'termination_reason':item.get('termination_reason'),'wall_clock_source':'dedicated_wait_thread_from_before_Popen','output_files':{}})
                for file in item['out'].rglob('*'):
                    if file.is_file():record['output_files'][file.relative_to(item['out']).as_posix()]={'sha256':sha(file),'bytes':file.stat().st_size}
                if (item['out']/'RESULT.json').exists():
                    result=json.loads((item['out']/'RESULT.json').read_text())
                    record['reported_cost']=result.get('cost');record['reported_lss_probability']=result.get('original_LSS_confidence')
                write(H/'outcomes'/(identity+'.json'),record)
                done.append(record)
                del active[identity]
        if available<P['emergency_available_bytes'] or total_rss>P['total_own_rss_limit_bytes']:
            if active:
                event={'utc':utc(),'available_bytes':available,'own_rss_bytes':total_rss,'pids':[x['pid'] for x in active.values()]}
                resource_events.append(event);write(H/'RESOURCE_EVENTS.json',resource_events)
                for item in active.values():terminate(item,'system_memory_protection')
        if not pilot_verified and len(done)==P['first_wave_runs'] and not active:
            write(H/'STATE.json',{'utc':utc(),'controller_pid':os.getpid(),'phase':'pilot_independent_audit','completed':len(done),'pending':len(tasks),'active':0})
            freeze()
            with (H/'PILOT_AUDIT.log').open('xb') as auditlog:
                audit=subprocess.run([os.sys.executable,str(H/'audit_reader.py')],cwd=str(B),env=dict(os.environ,R02_AUDIT_REPS='5'),stdout=auditlog,stderr=subprocess.STDOUT)
            if audit.returncode:raise RuntimeError('Pilot audit reader failed; pending identities retained')
            report=json.loads((H/'PILOT_INDEPENDENT_AUDIT.json').read_text())
            technical=[r for r in report['rows'] if any(not e.startswith('AssertionError:process_failure:') for e in r['errors'])]
            passed=not report['global_errors'] and len(report['rows'])==45 and not technical
            write(H/'PILOT_CONTINUATION_DECISION.json',{'utc':utc(),'pass':passed,'terminal':45,'independent_valid':report['independent_valid'],'technical_error_identities':[r['identity'] for r in technical],'ordinary_failures_retained':True,'no_tuning':True})
            if not passed:raise RuntimeError('Pilot technical gate failed; no automatic continuation')
            pilot_verified=True;freeze()
        if stop:
            for item in active.values():terminate(item,'requested_stop')
            if not active:break
        elif tasks and (pilot_verified or tasks[0]['rep']<=P['first_wave_reps']) and len(active)<P['max_workers']:
            needed=P['available_headroom_bytes']+P['worker_reserve_bytes']+reserve
            disk=os.statvfs(H);free=disk.f_bavail*disk.f_frsize
            if available>=needed and total_rss+reserve+P['worker_reserve_bytes']<=P['total_own_rss_limit_bytes'] and free>P['minimum_free_disk_bytes']:
                task=tasks.pop(0)
                case=task['case'];arm=task['arm'];rep=task['rep']
                # Identity is reserved once. Existing outputs are never overwritten.
                identity='%s_i%02d_r%02d'%(arm['name'],case['index'],rep)
                out=H/'runs'/identity
                assert not out.exists() and not (H/'outcomes'/(identity+'.json')).exists()
                binary=H.parent/'bin/ccmckp_s10'
                cmd=[str(binary),'--instance',str(B/'benchmark'/case['instance']),'--capacity',str(case['tmax']),
                    '--seed',str(task['seed']),'--rep',str(rep),'--seconds','600','--out',str(out),
                    '--manifest',str(H.parent/'source/BENCHMARK_MANIFEST.json')]
                cmd+=['--search-flow',arm['flow']]
                if arm['gamma'] is not None:cmd+=['--ellipsoid-gamma',str(arm['gamma']),'--ellipsoid-slice','5']
                log=(H/'logs'/(identity+'.log')).open('wb')
                launch_time=time.monotonic()
                env=dict(os.environ,CCMCKP_LAUNCH_MONOTONIC=str(launch_time),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',BLIS_NUM_THREADS='1',GOTO_NUM_THREADS='1')
                process=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                    start_new_session=True,cwd=str(H),env=env)
                item={'identity':identity,'case_index':case['index'],'instance':case['instance'],'capacity':case['tmax'],
                    'arm':arm['name'],'rep':rep,'seed':task['seed'],'pid':process.pid,'started_utc':utc(),
                    'started':launch_time,'peak_rss_bytes':0,'process':process,'log':log,'out':out,'binary':binary}
                def watch_exit(task_item):
                    proc=task_item['process']
                    allowance=P['process_wall_watchdog_seconds']-(time.monotonic()-task_item['started'])
                    def kill_at_guard():
                        if proc.poll() is None:
                            task_item['termination_reason']='guarded_total_wall_timeout'
                            os.killpg(proc.pid,signal.SIGKILL)
                    guard=threading.Timer(max(.001,allowance),kill_at_guard)
                    guard.daemon=True;guard.start()
                    proc.wait()
                    task_item['exited_monotonic']=time.monotonic()
                    guard.cancel()
                threading.Thread(target=watch_exit,args=(item,),daemon=True).start()
                active[identity]=item
                max_active=max(max_active,len(active))
                with (H/'DISPATCH.jsonl').open('a') as f:
                    f.write(json.dumps({k:item[k] for k in ['identity','pid','started_utc','seed']})+'\n')
        if time.monotonic()-last_state>=10:
            state={'utc':utc(),'controller_pid':os.getpid(),'phase':'stopping' if stop else 'running',
                'completed':len(done),'total':P['total_runs'],'pending':len(tasks),'active':len(active),'available_bytes':available,
                'max_active_observed':max_active,'active_identities':list(active),'elapsed_seconds':time.monotonic()-started}
            write(H/'STATE.json',state);last_state=time.monotonic()
        time.sleep(.3)
    freeze()
    complete={'utc':utc(),'phase':'stopped' if stop else 'completed','terminal':len(done),'pending':len(tasks),
        'rc0':sum(r['rc']==0 for r in done),'resource_events':len(resource_events),
        'max_active_observed':max_active,'elapsed_seconds':time.monotonic()-started,'all_source_and_input_pins_unchanged':True,'automatic_full40_expansion':False}
    write(H/'COMPLETED.json',complete);write(H/'STATE.json',dict(complete,controller_pid=os.getpid(),active=0))
    if not stop:
        with (H/'FINAL_AUDIT.log').open('xb') as auditlog:
            audit=subprocess.run([os.sys.executable,str(H/'audit_reader.py')],cwd=str(B),stdout=auditlog,stderr=subprocess.STDOUT)
        write(H/'FINAL_AUDIT_PROCESS.json',{'utc':utc(),'rc':audit.returncode})
        if audit.returncode:raise RuntimeError('Final independent audit reader failed')
except BaseException as error:
    for item in active.values():terminate(item,'controller_error')
    end=time.monotonic()+8
    while active and time.monotonic()<end:
        if all(item['process'].poll() is not None for item in active.values()):break
        time.sleep(.2)
    for item in active.values():
        process=item['process']
        if process.poll() is None and str(item['binary']).encode() in command(process.pid):os.killpg(process.pid,signal.SIGKILL)
    write(H/'CONTROLLER_ERROR.json',{'utc':utc(),'error':repr(error)})
    raise

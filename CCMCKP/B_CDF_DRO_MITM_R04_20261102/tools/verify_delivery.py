"""Portable offline integrity/cost/group/time audit; never evaluates probability."""
import argparse,gzip,hashlib,io,json,math,pickle,zipfile
from pathlib import Path,PurePosixPath
import numpy as np
ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,default=Path(__file__).resolve().parents[1]);a=ap.parse_args();root=a.directory
h=lambda b:hashlib.sha256(b).hexdigest()
for line in (root/'SHA256SUMS.txt').read_text(encoding='utf8').splitlines():
    digest,name=line.split('  ',1);assert h((root/name).read_bytes())==digest,name
with zipfile.ZipFile(root/'inputs_frozen.zip') as data,zipfile.ZipFile(root/'source_complete.zip') as src,zipfile.ZipFile(root/'results_full_2400.zip') as z:
    assert data.testzip() is None and src.testzip() is None and z.testzip() is None
    em=json.loads(z.read('EXPORT_MANIFEST.json'))
    assert len(z.namelist())==len(set(z.namelist()))
    for name,m in em['files'].items():assert h(z.read(name))==m['sha256'],name
    source_manifest=json.loads(src.read('SOURCE_PACKAGE_MANIFEST.json'))
    for name,m in source_manifest['files'].items():assert h(src.read(name))==m['sha256'],name
    frozen=json.loads(src.read('R04_campaign/FREEZE.json'))
    for name,digest in frozen['files'].items():assert h(src.read('R04_campaign/'+name))==digest,name
    schedule='R04_campaign/scheduling_amendments/A02_20261101T1144Z/'
    assert h(src.read(schedule+'SCHEDULING_FREEZE.json'))=='96b28599b2facac514e30aac25382114b818e4a24810fb8e7428f3bde2b46a04'
    for name,digest in json.loads(src.read(schedule+'SCHEDULING_FREEZE.json'))['files'].items():assert h(src.read(schedule+name))==digest,name
    inputs=json.loads(z.read('control/INPUTS.json'))
    for name,digest in inputs.items():assert h(data.read('benchmark/'+name.split('/benchmark/',1)[1]))==digest,name
    protocol=json.loads(z.read('control/PROTOCOL.json'));cases={c['index']:c for c in protocol['cases']};seen=set();counts={'B':0,'R04':0};max_time=0.;minimum_probability=1.;starts={'B':[],'R04':[]};ends={'B':[],'R04':[]};initializations=0
    for name in z.namelist():
        if not(name.startswith('waves/') and name.endswith('/WAVE.json')):continue
        meta=json.loads(z.read(name));phase=meta['phase']
        if phase not in ('reference','R04_full') or meta['status']!='valid_complete':continue
        arm='B' if phase=='reference' else 'R04';idx=meta['index'];case=cases[idx];prefix=name[:-len('WAVE.json')];assert meta['valid']==meta['terminal']==meta['workers']==30
        c=np.loadtxt(io.BytesIO(data.read('benchmark/'+case['instance']+'/cost.txt'))).reshape(-1);groups=pickle.loads(data.read('benchmark/'+case['instance']+'/node_to_factor.pkl'))
        if isinstance(groups,dict):groups=[groups[k] for k in sorted(groups,key=lambda v:int(v))]
        journal=json.loads(z.read(prefix+'TIMING_JOURNAL.json'))
        for rep in range(1,31):
            key=(arm,idx,rep);assert key not in seen;seen.add(key);stem=prefix+'r%02d'%rep;raw=z.read(stem+'.json.gz');wb=z.read(stem+'.json.gz.worker.json');x=json.loads(gzip.decompress(raw));w=json.loads(wb);t=json.loads(z.read(stem+'.terminal.json'));s=x['selected'];cfg=x['config'];runtime=journal[str(rep)]
            assert h(raw)==t['record_sha'] and h(wb)==t['worker_sha'];assert x['seed']==w['seed']==832272+rep
            assert cfg['time_budget']==600 and cfg['work_reserve']==15 and cfg['native_draws']==1000000 and cfg['native_gate']==.99 and cfg['screen_gate']==.975 and cfg['screen_draws']==60000
            assert cfg['bins']==4096 and cfg['radii']==[.00025,0.,.0005] and x['capacity']==case['tmax']
            assert t['reason']=='returned' and t['returncode']==0 and runtime<=600
            assert runtime>=t['elapsed_before_terminal_save']>=w['elapsed_before_worker_sidecar']>=x['runtime_before_save']
            ids=s['selection'];assert len(ids)==len(set(ids))==len(groups) and all(len(set(g)&set(ids))==1 for g in groups)
            assert abs(math.fsum(float(c[j]) for j in ids)-s['cost'])<1e-8 and s['probability']>=.99
            assert w['independent_initialization'] and w['no_cross_seed_weights'] and x['external_solution_inputs'] is False and x['prior_count']==0
            assert any(v['source']=='current_run_V50_original_low_risk_initialization' for v in x['native_observations']);initializations+=1
            assert any(v['selection']==ids and v['probability']==s['probability'] for v in x['native_observations'])
            positive=[v['cost'] for v in x['native_observations'] if v['probability']>=.99];assert s['cost']==min(positive)
            starts[arm].append(t['started_monotonic']);ends[arm].append(t['started_monotonic']+runtime);counts[arm]+=1;max_time=max(max_time,runtime);minimum_probability=min(minimum_probability,s['probability'])
    assert counts=={'B':1200,'R04':1200} and initializations==2400 and min(starts['R04'])>=max(ends['B'])
print(json.dumps({'status':'passed','registered_and_valid':counts,'cases':40,'independent_initializations':initializations,'candidate_full_fresh_after_reference':True,'max_saved_runtime_seconds':max_time,'minimum_original_native_return':minimum_probability,'scope':'Archive hashes, frozen files, raw input bytes, recorded costs/groups/seeds/time/config/native-return provenance. No optimization or native resampling; not a population coverage/global-optimality certificate.'},indent=2))

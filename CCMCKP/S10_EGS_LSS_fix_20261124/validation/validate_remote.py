from pathlib import Path
import csv,hashlib,json,subprocess,time
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_lss_fix_20261124'
assert Path.cwd().resolve()==B.resolve()
F=H/'fixtures/LAB_3_2_500_';assert not list(F.glob('*_dist.txt'))
records=[]
def run(label,command):
    start=time.monotonic()
    p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (H/(label+'.log')).write_bytes(p.stdout)
    row={'label':label,'rc':p.returncode,'wall_seconds':time.monotonic()-start,'command':command}
    records.append(row)
    return p
try:
    p=run('lss_unit',[str(H/'build/lss_fix_test'),str(F),str(H/'unit_output')]);assert p.returncode==0,p.stdout.decode()
    unit=json.loads((H/'unit_output/UNIT_RECEIPT.json').read_text())
    for label,flow,gamma in [('S10','frontier_mitm',2.4),('EGS_2p4','ellipsoid_oa',2.4),('EGS_0','ellipsoid_oa',0.)]:
        output=H/'integration'/label
        p=run(label,[str(H/'build/ccmckp_s10'),'--instance',str(F),'--capacity','.5','--seed','960001','--seconds','30',
            '--rep','1','--out',str(output),'--search-flow',flow,'--ellipsoid-gamma',str(gamma)])
        assert p.returncode==0,p.stdout.decode()
        result=json.loads((output/'RESULT.json').read_text())
        assert result['status']=='completed' and result['acceptance_evaluator']=='LSS' and result['acceptance_threshold']==.99
        assert result['lss_sample_index_max']==499 and result['final_lss_enforced'] and not result['real_probability_reporting']
        assert 'recorded_real_probability' not in result and result['original_LSS_confidence']>=.99
        for v in result['original_output_variants']:assert v['probability']>=.99 and 'real_probability' not in v
        trace=json.loads((output/'ORIGINAL_LSS_DECISION_TRACE.json').read_text());last={}
        for event in trace:
            if 'evaluation' in event:last[tuple(event['selection'])]=event
        for v in result['original_output_variants']:assert last[tuple(v['selection'])]['probability']==v['probability']
        for name in (output/'result/Localsearch').glob('*_[012].csv'):
            with name.open() as f:rows=list(csv.reader(f))
            assert len(rows[0])==len(rows[1])==6 and all('Real' not in x for x in rows[0])
        records[-1].update({'cost':result['cost'],'LSS_probability':result['original_LSS_confidence'],
            'no_dist_files_required':True,'all_variants_last_LSS_verified':True,'CSV_realP_column_removed':True})
    p=run('reject_real_flag',[str(H/'build/ccmckp_s10'),'--real']);assert p.returncode!=0 and b'Unknown or incomplete option --real' in p.stdout
    data={'status':'PASS','scope':'targeted correctness regressions, not a benchmark performance claim','unit':unit,'checks':records,
        'extra_real_probability_MC':False,'binary_sha256':hashlib.sha256((H/'build/ccmckp_s10').read_bytes()).hexdigest(),
        'source_sha256':{p.relative_to(H/'source').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'source').rglob('*') if p.is_file()}}
except BaseException as e:
    (H/'VALIDATION_FAILURE.json').write_text(json.dumps({'error':repr(e),'checks':records},indent=2));raise
(H/'VALIDATION.json').write_text(json.dumps(data,indent=2));print(json.dumps({k:v for k,v in data.items() if k!='source_sha256'}),flush=True)

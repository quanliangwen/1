from pathlib import Path
import ast

F=Path(__file__).resolve().parent
text=(F.parent/'P142_profile_and_task_chain/run_diagnostic.py').read_text(encoding='utf-8-sig')
text=text.replace('P142_Astar_profile_and_task_chain_20261102','P143_Astar_drive_encounter_evidence_20261102')
text=text.replace('check_sdk_astar_profile.py','check_sdk_drive_evidence.py')
start=text.index('    arms=[]\n')
end=text.index("\nif __name__=='__main__':")
replacement='''    parent=F.parent/'P142_profile_and_task_chain/BASELINE_FIRST.json'
    assert hashlib.sha256(parent.read_bytes()).hexdigest()==pre['parent_failure_sha256']
    if(F/'STOP_REQUESTED').exists():raise RuntimeError('Human stop before evidence replay')
    label='DRIVE_EVIDENCE_FIRST'
    keep(label+'_SERIAL',remote(guard))
    write('STATUS.json',dict(utc=utc(),status='RUNNING_READ_ONLY_FAILED_ENCOUNTER_PROVENANCE',native_rounds=0),False)
    cmd=SSH+[R+'/.venv/bin/python',D+'/run_sdk_captured.py',D+'/check_sdk_drive_evidence.py',label,'P48_ASTAR','cross_sdk','800','.05','TRACE']
    keep(label,subprocess.run(cmd,capture_output=True,timeout=900))
    subprocess.run(['scp','-q','junhao@10.112.162.60:'+D+'/'+label+'.json',str(F/(label+'.json'))],check=True,timeout=45)
    a=load(parent);b=load(F/(label+'.json'))
    checks=dict(frame_rows_identical=a['rows']==b['rows'],
                original_checks_identical=a['checks']==b['checks'],
                maps_identical=a['map_results']==b['map_results'],
                submission_identity=[(e['owner'],e['step'],e['output_sha256'])for e in a['submission_records']]==[(e['owner'],e['step'],e['output_sha256'])for e in b['submission_records']],
                task_chain_identical=a['route_details']==b['route_details'],
                gate_chain_identical=a['gate_events']==b['gate_events'],
                actual_motor_returns=len(b['drive_evidence'])==30,
                intended_scope=all(e['owner']in[1,4]and 332<=e['step']<=346 for e in b['drive_evidence']))
    result=dict(status='PASS_FAILED_ENCOUNTER_PROVENANCE_IDENTITY'if all(checks.values())else'STOP_FIRST_PROVENANCE_MISMATCH',
                checks=checks,physics_steps=b['physics_steps'],original_health_failure_preserved=True,
                first_health_failure=next(r['step']for r in b['rows']if r['health']!=[50]*5),
                final_health=b['rows'][-1]['health'],drive_evidence=b['drive_evidence'],
                native_rounds=0,automatic_native=False,automatic_five=False,algorithm_changed=False,
                limitation='Not rescue of P142 failure, not a passing performance trial. Only own public motor inputs/locals; not actual substep contact identity.')
    write('RESULT_FIRST.json',result)
    write('STATUS.json',dict(utc=utc(),status=result['status'],native_rounds=0),False)
    print(json.dumps(dict(status=result['status'],checks=checks,events=len(b['drive_evidence']))),flush=True)
'''
text=text[:start]+replacement+text[end:]
ast.parse(text)
p=F/'run_diagnostic.py'
assert not p.exists()
p.write_bytes(text.encode())

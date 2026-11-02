"""Freeze the independent eligibility change, one authored SDK case, no native."""
from pathlib import Path
import ast,hashlib,json
F=Path(__file__).resolve().parent
P=F.parent/'P148_joint_waiting_rule'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
contract=json.loads((F/'CONTRACT_FIRST.json').read_text())
assert contract['status']=='PASS_READY_ELECTION_AND_ORIGINAL_WAITING_SCOPE'
assert all(sha(F/n)==h for n,h in contract['source_sha256'].items())
project=F/'candidate_project';assert not project.exists()
old=json.loads((P/'CANDIDATE_MANIFEST_V2_FIRST.json').read_text())
for n,h in old['candidate_files'].items():
    p=P/'candidate_project_v2'/n;assert sha(p)==h
    dest=project/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
sol=project/'src/swarm_rescue/solutions'
for n in['waiting_core.py','joint_waiting.py','wait_connectivity.py']:(sol/n).write_bytes((F/n).read_bytes())
files={p.relative_to(project).as_posix():sha(p)for p in project.rglob('*')if p.is_file()}
changes=[n for n,h in files.items()if old['candidate_files'][n]!=h]
assert set(changes)=={'src/swarm_rescue/solutions/waiting_core.py','src/swarm_rescue/solutions/joint_waiting.py'}
for p in sol.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
manifest=dict(old,candidate_files=files,changed_from_failed_P148=changes,
              rule='Same waiting rule, elect only among fresh actually-ready empty peers; no historical output filter.')
(F/'CANDIDATE_MANIFEST_FIRST.json').write_bytes((json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
(F/'BASE_WORKSPACE.json').write_bytes((P/'BASE_WORKSPACE.json').read_bytes())
code=(P/'check_sdk_joint_waiting_v2.py').read_bytes()
(F/'check_sdk_ready_waiting.py').write_bytes(code)
pre=json.loads((P/'PREDECLARATION_V2_FIRST.json').read_text())
pre.update(status='FROZEN_READY_ELIGIBILITY_CHANGE_BEFORE_FIRST_SDK_FRAME',
           code_sha256=sha(F/'check_sdk_ready_waiting.py'),manifest_sha256=sha(F/'CANDIDATE_MANIFEST_FIRST.json'),
           scope_revision='P148 actual no-op gate retained. Only readiness-domain leader logic changes; same physical arena/seed/thresholds to isolate it.',
           predecessor_failure=str(P/'RESULT_V2_FIRST.json'),predecessor_failure_sha256=sha(P/'RESULT_V2_FIRST.json'))
(F/'PREDECLARATION_FIRST.json').write_bytes((json.dumps(pre,ensure_ascii=False,indent=2)+'\n').encode())
(F/'SDK_GATE_ADDENDUM_FIRST.json').write_bytes((P/'SDK_GATE_ADDENDUM_FIRST.json').read_bytes())
workspace=(P/'prepare_workspace_v2.py').read_text().replace('CANDIDATE_MANIFEST_V2_FIRST','CANDIDATE_MANIFEST_FIRST').replace('candidate_project_v2','candidate_project').replace('P148V2','P149')
(F/'prepare_workspace.py').write_bytes(workspace.encode())
runner=(P/'run_diagnostic_v2.py').read_text()
for a,b in [('P148_Astar_joint_waiting_v2_20261102','P149_Astar_ready_waiting_20261102'),('check_sdk_joint_waiting_v2.py','check_sdk_ready_waiting.py'),('prepare_workspace_v2.py','prepare_workspace.py'),('candidate_project_v2','candidate_project'),('run_diagnostic_v2.py','run_diagnostic.py'),('P148V2','P149'),('V2_FIRST','FIRST'),('RESULT_V2_FIRST','RESULT_FIRST'),('JOINT_WAITING_V2_FIRST','READY_WAITING_FIRST')]:runner=runner.replace(a,b)
# FIRST suffix replacement above also yields JOINT_WAITING_FIRST; preserve readable unique stage-local label.
runner=runner.replace("label='JOINT_WAITING_FIRST'","label='READY_WAITING_FIRST'")
runner=runner.replace("    print(json.dumps(result,ensure_ascii=False),flush=True)","    print(json.dumps(dict(status=result['status'],checks=checks,physics_steps=b['physics_steps'],score=candidate,native_rounds=0),ensure_ascii=False),flush=True)")
ast.parse(runner);ast.parse(workspace)
(F/'run_diagnostic.py').write_bytes(runner.encode())
# Real exact-hash historical check, plus explicit conceptual review of failed rules.
historical=[]
for d in [F.parent,Path('E:/codex/PJ01_rule_refinement_20261101'),Path('E:/codex/UAV_rules_astar_restart_20261030')]:
    if not d.exists():continue
    for p in d.rglob('*waiting*.py'):
        if F in p.parents:continue
        historical.append(dict(path=str(p),sha256=sha(p)))
pair={sha(F/'waiting_core.py'),sha(F/'joint_waiting.py')}
matches=[p for p in historical if p['sha256']in pair]
assert not matches,matches
preflight=dict(status='PASS_NO_EXACT_HISTORICAL_SOURCE_MATCH',files_checked=len(historical),exact_matches=matches,
               conceptual_review=['P148 predecessor same parking concept, actual no-op retained. New eligible-domain election explicitly different.',
                                  'P18 exploration same-target yielding failed; not imported.',
                                  'P147 terminal joint graph principle retained, not a dynamic consensus guarantee.'],
               history=historical,sdk_frames=0,native_rounds=0)
(F/'MECHANISM_PREFLIGHT_FIRST.json').write_bytes((json.dumps(preflight,ensure_ascii=False,indent=2)+'\n').encode())
bound=['run_diagnostic.py','prepare_workspace.py','check_sdk_ready_waiting.py','PREDECLARATION_FIRST.json','CANDIDATE_MANIFEST_FIRST.json','MECHANISM_PREFLIGHT_FIRST.json','CONTRACT_FIRST.json','SDK_GATE_ADDENDUM_FIRST.json','DESIGN_FIRST.json']
(F/'LAUNCH_BINDING_FIRST.json').write_bytes((json.dumps(dict(script_sha256={n:sha(F/n)for n in bound}),indent=2)+'\n').encode())
print(json.dumps(dict(status=pre['status'],changes=changes,contract_checks=len(contract['checks']),source_files=len(files),historical_files=len(historical))))

"""Only relax P157's same-call coverage floor and matching message check."""
from pathlib import Path
import datetime,hashlib,json,shutil
F=Path(__file__).resolve().parent;F.mkdir(exist_ok=True);P=F.parent/'P157_inner_corner_free_quadrants'
D=F/'candidate_project';assert not D.exists();shutil.copytree(P/'candidate_project',D,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
S=D/'src/swarm_rescue/solutions'
p=S/'corner_cluster.py';text=p.read_text();assert text.count('COVERAGE_RATIO=.90')==1;p.write_text(text.replace('COVERAGE_RATIO=.90','COVERAGE_RATIO=.70'),encoding='utf-8')
p=S/'corner_mission.py';text=p.read_text();assert text.count('.9-1e-8<=ratio')==1;p.write_text(text.replace('.9-1e-8<=ratio','.7-1e-8<=ratio'),encoding='utf-8')
changed=[p.name for p in S.iterdir()if p.is_file()and p.read_bytes()!=(P/'candidate_project/src/swarm_rescue/solutions'/p.name).read_bytes()]
assert sorted(changed)==['corner_cluster.py','corner_mission.py']
manifest=dict(parent='P157',changed_from_parent=changed,change='coverage_floor .90 -> .70, including message validation; fixed6 unchanged',candidate_files={str(p.relative_to(D)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()for p in D.rglob('*')if p.is_file()})
(F/'CANDIDATE_MANIFEST_V2.json').write_text(json.dumps(manifest,indent=2)+'\n')
for name in ['BASE_WORKSPACE.json','check_sdk_inner.py']:shutil.copyfile(P/name,F/name)
prep=(P/'prepare_sdk_workspace.py').read_text().replace('workspace_P157','workspace_P159').replace("'P157':dict(","'P159':dict(")
(F/'prepare_sdk_workspace.py').write_text(prep,encoding='utf-8')
test=(P/'check_numeric.py').read_text().replace(">=.9",">=.7")
needle="d.corner_context['target_total']=2;"
assert test.count(needle)==1
test=test.replace(needle,"d.corner_context['coverage_ratio']=.75;check('new70_context_accepted',d._valid_corner_context(d.corner_context,100))\nd.corner_context['coverage_ratio']=.69;check('below70_context_rejected',not d._valid_corner_context(d.corner_context,100))\nd.corner_context['coverage_ratio']=.75\n"+needle)
(F/'check_numeric.py').write_text(test,encoding='utf-8')
runner=(P/'run_small.py').read_text().replace('P157_inner_corner_free_quadrants_20261102','P159_cluster_coverage70_20261102').replace("for arm in ['P157']:","for arm in ['P159']:").replace("F/'P157_SDK_FIRST.json'","F/'P159_SDK_FIRST.json'")
runner=runner.replace("wall_retained90=sb['wall_raw']>=.9*sa['wall_raw']", "wall_retained70=sb['wall_raw']>=.7*sa['wall_raw']")
runner=runner.replace("controllable_loss_at_most_half_point=sb['controllable_subtotal']is not None and sa['controllable_subtotal']is not None and sb['controllable_subtotal']>=sa['controllable_subtotal']-.5", "controllable_loss_within_new_wall_allowance=sb['controllable_subtotal']is not None and sa['controllable_subtotal']is not None and sb['controllable_subtotal']>=sa['controllable_subtotal']-(.2*.3*sa['wall_raw']+.25)")
# Bind the existing baseline before using it, not after seeing the new result.
runner=runner.replace("pre=read(F/'PREDECLARATION_FIRST.json')", "pre=read(F/'PREDECLARATION_FIRST.json')\n assert hashlib.sha256(Path(pre['baseline_path']).read_bytes()).hexdigest()==pre['baseline_sha256']\n assert hashlib.sha256((F/'CANDIDATE_MANIFEST_V2.json').read_bytes()).hexdigest()==pre['candidate_manifest_sha256']")
(F/'run_small.py').write_text(runner,encoding='utf-8')
baseline=F.parent/'P156_fixed_quota_inner_corner/P48_ASTAR_SDK_FIRST.json'
pre=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),human_request='fixed6 / retain70% predicted coverage',initial_total=10,cluster_quota=6,model_coverage_floor=.7,actual_wall_score_retained_gate=.7,map_loss_limit_pp=.5,time_nonregress=True,health_nonregress=True,all10=True,controllable_loss_allowance='.2*.3*baseline_wall_raw+.25',SDK_arms=['P159'],baseline_not_repeated=True,baseline_path=str(baseline),baseline_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),SDK_script_sha256=hashlib.sha256((F/'check_sdk_inner.py').read_bytes()).hexdigest(),candidate_manifest_sha256=hashlib.sha256((F/'CANDIDATE_MANIFEST_V2.json').read_bytes()).hexdigest(),SDK_horizon=1600,author_seed=615,author_wall_rate=.05,automatic_five=False,automatic_native=False,native_rounds=0,not_full_red_score_without_BLUE=True)
(F/'PREDECLARATION_FIRST.json').write_text(json.dumps(pre,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(changed=changed,fixed6=True,coverage_floor=.7,SDK_script_unchanged=(F/'check_sdk_inner.py').read_bytes()==(P/'check_sdk_inner.py').read_bytes())))

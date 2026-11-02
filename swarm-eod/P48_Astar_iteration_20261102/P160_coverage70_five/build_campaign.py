"""Freeze the explicitly requested five RED/BLUE maps using unchanged P159."""
from pathlib import Path
import ast,hashlib,json,shutil,zipfile
F=Path(__file__).resolve().parent;P=F.parent/'P159_cluster_coverage70';B=F.parent/'P154_corner_cluster_five'
V='P159_C70_ASTAR';stage='P160_coverage70_five_20261102';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
F.mkdir(exist_ok=True);assert not(F/'TEST_PROTOCOL.json').exists()
numeric=json.loads((P/'NUMERIC_FIRST.json').read_text());assert all(c['passed']for c in numeric['checks'])and len(numeric['checks'])==36
manifest=json.loads((P/'CANDIDATE_MANIFEST_V2.json').read_text());C=P/'candidate_project'
assert all(sha(C/n)==h for n,h in manifest['candidate_files'].items())
S=F/'versions'/V/'source';S.mkdir(parents=True)
for p in(C/'src/swarm_rescue/solutions').iterdir():
 if p.is_file():shutil.copyfile(p,S/p.name)
assert len(list(S.iterdir()))==44 and (S/'req.txt').read_bytes()==(C/'req.txt').read_bytes()
payload={p.name:sha(p)for p in S.iterdir()}
for p in S.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
archive=S.parent/'P159_coverage70_research.zip'
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED)as z:
 for p in sorted(S.iterdir()):z.writestr(p.name,p.read_bytes())
(F/'CANDIDATE_MANIFEST.json').write_text(json.dumps(dict(sha256=sha(archive),payload_files=payload,parent_manifest_sha256=sha(P/'CANDIDATE_MANIFEST_V2.json'),same_controller_as_P159=True,official_submission_ready=False),indent=2)+'\n')
contract=dict(status='PASS_COVERAGE70_FIXED_QUOTA_CHECKS',checks=numeric['checks'],parent_numeric_sha256=sha(P/'NUMERIC_FIRST.json'),source_sha256={n:payload[n]for n in ['corner_cluster.py','corner_mission.py']},SDK_small_actual_cluster=3,SDK_small_actual6_passed=False,human_direct_five_overrides_score_screen=True)
(F/'NUMERIC_CONTRACT_FIRST.json').write_text(json.dumps(contract,indent=2)+'\n')
for name in ['BASELINE_REFERENCE.json','BASELINE_BLUE_REFERENCE.json']:shutil.copyfile(B/name,F/name)
for name in ['start_local_collector.py','check_scoped_serial.py','watch_completion.py','launch_campaign.py','check_sdk_actual_zip_entry.py']:
 text=(B/name).read_text().replace('P154_CORNER_ASTAR',V).replace('P154_corner_cluster_five_20261102',stage)
 (F/name).write_text(text,encoding='utf-8')
for name in ['prepare_workspace.py','declare_native.py','run_offline.py','run_and_launch.py','collect_offline.py','draw_layouts.py','finalize_and_publish.py']:
 text=(B/name).read_text().replace('P154_CORNER_ASTAR',V).replace('P154_corner_cluster_five_20261102',stage).replace('P154_corner_cluster_research.zip','P159_coverage70_research.zip')
 text=text.replace('CORNER_CONTRACT_V2_FIRST.json','NUMERIC_CONTRACT_FIRST.json').replace('PASS_CORNER_NUMERIC_AND_OBJECTIVE_MESSAGE_CONTRACTS','PASS_COVERAGE70_FIXED_QUOTA_CHECKS')
 if name=='declare_native.py':
  text=text.replace('Explicit user requests coverage-guarded majority-corner placement and all original five maps; no control rerun or score pilot. Original SDK/BLUE/gates unchanged.','Explicit user requests all five original maps including BLUE scores for frozen P159 fixed6/coverage70; no pilot despite author concentration shortfall, no control rerun. Original SDK/BLUE/resources unchanged.')
 if name=='run_offline.py':
  text=text.replace('clusters=[];commits=[]','clusters=[];commits=[];plan_chain=[]')
  needle="   if '[CORNER_COMMIT] 'in line:commits.append(json.loads(line.split('[CORNER_COMMIT] ',1)[1]))"
  assert text.count(needle)==1;text=text.replace(needle,needle+"\n   if '[CORNER_PLAN_CHAIN] 'in line:plan_chain.append(json.loads(line.split('[CORNER_PLAN_CHAIN] ',1)[1]))")
  text=text.replace('cluster_model_audits=clusters,concentration=','cluster_model_audits=clusters,issued_plan_chain=plan_chain,concentration=')
 if name=='finalize_and_publish.py':
  text=text.replace("a['coverage_ratio']>=.9-1e-8","a['coverage_ratio']>=.7-1e-8")
  text=text.replace('>=90% same-call baseline','>=70% same-call baseline').replace('90%是每次','70%是每次').replace('墙体分90%','墙体分70%')
  text=text.replace("concentration=r['concentration'],model_audits=", "concentration=r['concentration'],issued_plan_chain=r['issued_plan_chain'],model_audits=")
  needle="images='\\n\\n## 公开布局与红队路线图"
  assert needle in text
  at=text.index(needle)
  extra="""details='\\n\\n## 蓝队分数与加权细则\\n\\n|地图|地图×.5|墙体×.2|时间×.1|布局难度贡献|蓝队得分|完整红分|\\n|---|---:|---:|---:|---:|---:|---:|\\n'
for r in rows:
    details+=f\"|{r['map']}|{.5*r['map_score']:.6f}|{.2*r['wall_score']:.6f}|{.1*r['time_score']:.6f}|{r['layout_contribution']:.6f}|{r['blue_score']:.6f}|{r['cluster_full']:.6f}|\\n\"
details+='\\nBLUE得分来自原team006原SDK同轮公开评分；布局难度贡献采用冻结评测器原值。双队墙钟超时与步数耗尽必须区分；有墙钟超时的图保留分数但不用于稳定性能比较。完整均分是本组自然随机观察，不是同seed配对因果。\\n'
inputs['RESULTS.md']+=details.encode()
"""
  text=text[:at]+extra+text[at:]
 (F/name).write_text(text,encoding='utf-8')
protocol=dict(status='FROZEN_HUMAN_REQUESTED_COVERAGE70_RED_BLUE_FIVE',version=V,maps=['Map01','Map02','Map03','Map04','Map05'],native_rounds=10,RED_per_map=1,BLUE_per_map=1,external_seed=None,human_request='在五张地图上进行测试，加上蓝队测试的分数',coverage_floor=.70,quota_initial_total=10,quota_fixed=6,cluster_radius_in_blast_radii=2.,controller_unchanged_from_P159=True,pilot_screening=False,baseline_repeated=False,automatic_B=False,automatic_iteration=False,official_upload=False,small_test_actual_cluster=3,small_test_concentration_qualified=False,direct_human_request_overrides_small_score_gate=True,baseline_mean=74.25588336546745,baseline_reference_sha256=sha(F/'BASELINE_REFERENCE.json'),candidate_manifest_sha256=sha(F/'CANDIDATE_MANIFEST.json'),numeric_contract_sha256=sha(F/'NUMERIC_CONTRACT_FIRST.json'),limit='One RED+same team006 BLUE per original map. First real native error stops, no retries/seeds/labels. Low scores retained through requested five. No controller fixes stacked.')
(F/'TEST_PROTOCOL.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
for p in F.glob('*.py'):ast.parse(p.read_text())
print(json.dumps(dict(status=protocol['status'],version=V,payload_files=len(payload),zip_sha256=sha(archive),max_native_rounds=10)))

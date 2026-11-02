from pathlib import Path
import ast,hashlib,json,shutil,datetime
F=Path(__file__).resolve().parent;P=F.parent/'P159_cluster_coverage70'
C=F/'candidate_project';assert not C.exists();shutil.copytree(P/'candidate_project',C,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
S=C/'src/swarm_rescue/solutions';text=(P/'candidate_project/src/swarm_rescue/solutions/corner_cluster.py').read_text()
node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=='_corners')
detector=ast.get_source_segment(text,node).replace('def _corners(','def _inner_corners(')
needle="    lock=getattr(memory,'corner_cluster_anchor',None)";assert detector.count(needle)==1;detector=detector.replace(needle,'    lock=None # multi-corner domains are not a single locked site')
new=(F/'multi_layout_core.py').read_text();assert new.count('# INSERT_INNER_DETECTOR')==1
(S/'corner_cluster.py').write_text(new.replace('# INSERT_INNER_DETECTOR',detector),encoding='utf-8')
(S/'corner_mission.py').write_bytes((F/'multi_mission.py').read_bytes())
for p in S.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
changes=[p.name for p in S.iterdir()if p.is_file()and p.read_bytes()!=(P/'candidate_project/src/swarm_rescue/solutions'/p.name).read_bytes()]
assert sorted(changes)==['corner_cluster.py','corner_mission.py']
manifest=dict(parent='P159_coverage70',changed=changes,candidate_files={str(p.relative_to(C)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()for p in C.rglob('*')if p.is_file()},Gurobi=False,SDK_changed=False,dependencies_changed=False,group_count_min=2,per_group_min=2,per_group_max=3,group_radius_ratio=1.,coverage_floor=.7)
(F/'CANDIDATE_MANIFEST_FIRST.json').write_text(json.dumps(manifest,indent=2)+'\n')
shutil.copyfile(P/'BASE_WORKSPACE.json',F/'BASE_WORKSPACE.json')
prep=(P/'prepare_sdk_workspace.py').read_text().replace('CANDIDATE_MANIFEST_V2.json','CANDIDATE_MANIFEST_FIRST.json').replace('workspace_P159','workspace_P161').replace("'P159':dict(","'P161':dict(")
(F/'prepare_sdk_workspace.py').write_text(prep,encoding='utf-8')
print(json.dumps(dict(changed=changes,payloads=len(manifest['candidate_files']),coverage_floor=.7,group_radius=1.,per_group=[2,3])))

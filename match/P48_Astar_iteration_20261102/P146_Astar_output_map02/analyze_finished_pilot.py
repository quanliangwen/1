from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess

F=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert load(F/'CAMPAIGN_CLIENT_REVIEW.json')['status']=='PASS'
assert load(F/'P145_A/CLIENT_FIRST_RAW_REVIEW.json')['status']=='PASS'
assert not(F/'POSTMORTEM_FIRST.json').exists()
g=F/'P145_A'
manifest=load(g/'RAW_SHA256.json')
remote=load(g/'LAUNCH.json')['result']
p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','junhao@10.112.162.60','cat',remote+'/Map02_red/console.log'],capture_output=True,check=True,timeout=45)
assert hashlib.sha256(p.stdout).hexdigest()==manifest['Map02_red/console.log']['sha256']
fresh=[]
drops=[]
releases=[]
farthest=[]
audits=[]
for line in p.stdout.decode('utf-8').splitlines():
    if line.startswith('[FRESH_OPPORTUNITY] '):fresh.append(json.loads(line.split('] ',1)[1]))
    elif line.startswith('[FREE_SUPPORT_OUTPUT] '):audits.append(json.loads(line.split('] ',1)[1]))
    elif line.startswith('[placement]'):
        m=re.search(r'drone=(\d+) step=(\d+) inventory=(\d+) position=\(([-\d.]+),([-\d.]+)\)',line)
        assert m,line
        drops.append(dict(owner=int(m[1]),step=int(m[2]),inventory=int(m[3]),position=[float(m[4]),float(m[5])]))
    elif line.startswith('[active-coverage] release_all_inventory '):
        m=re.match(r'\[active-coverage\] release_all_inventory (\d+) (\d+) (.*)',line)
        assert m,line
        releases.append(dict(owner=int(m[1]),step=int(m[2]),model=ast.literal_eval(m[3])))
    elif line.startswith('[farthest-wall] '):farthest.append(ast.literal_eval(line.split('] ',1)[1]))
mechanism=load(g/'MECHANISM_REVIEW.json')
b=mechanism['phase']['map_breakdown']
old=load(F.parent.parent/'P48_astar_five_20261102/CAMPAIGN_CLIENT_REVIEW.json')if False else load(Path('E:/codex/P48_astar_five_20261102/CAMPAIGN_CLIENT_REVIEW.json'))
old=next(x for x in old['result']['rows']if x['map']=='Map02')
row=load(F/'CAMPAIGN_CLIENT_REVIEW.json')['rows'][0]
result=dict(status='REVIEWED_FAILED_SINGLE_NO_FIVE',actual=row,
            exit_events=[x for x in fresh if x['kind']=='ACTUAL_SUBMISSION_DUE'],
            submit_events=[x for x in fresh if x['kind']=='SUBMIT_IMAGE'],releases=releases,placements=drops,
            all_local_refreshes=[x for x in fresh if x['kind']=='ACTUAL_LOCAL_MODEL_REFRESH'],
            farthest_events=farthest,actual_output_audits=audits,
            map_surface_credit_percent=100*b['credit'],map_false_penalty_percentage_points=100*b['penalty'],
            total_point_gaps=dict(missing_surface=50*(1-b['credit']),false_positive=50*b['penalty'],wall=.2*(100-row['wall_score']),time=.1*(100-row['time_score'])),
            observed_vs_prior_astar_map02=dict(full=row['score']-old['full'],map=row['map_score']-old['phase']['score_map'],wall=row['wall_score']-old['phase']['score_wall'],time=row['time_score']-old['phase']['score_time']),
            own_console_sha256=manifest['Map02_red/console.log']['sha256'],
            decision='Fail frozen score/completion gates. No five, retry, promotion or release.',
            limits=['Final-output rule does not alter policy before submission. Different natural episode/load cannot identify it as cause of short inventory or different raw map.',
                    'No same-episode original-map truth counterfactual for this native run. Actual erasure is not proof of native map gain.',
                    'Remaining_steps=0 branch, if logged, proves nominal budget exit, not measured complete-route feasibility or wallclock hard hit.',
                    'Known local release/model slots are not the full fleet truth.'])
(F/'POSTMORTEM_FIRST.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps({k:result[k]for k in ['status','exit_events','releases','placements','actual_output_audits','map_surface_credit_percent','map_false_penalty_percentage_points','total_point_gaps']},ensure_ascii=False))

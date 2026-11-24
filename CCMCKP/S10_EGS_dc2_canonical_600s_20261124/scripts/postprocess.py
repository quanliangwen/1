from pathlib import Path
import json
R=Path(__file__).resolve().parent;A=json.loads((R/'evidence/INDEPENDENT_AUDIT_STATISTICS.json').read_text());C=json.loads(Path('E:/codex/S10_EGS_costfront_600s_20261124/evidence/INDEPENDENT_AUDIT_STATISTICS.json').read_text())
rows=[dict(trial='CF',case=x['case_index'],raw_p=x['cost_p_raw']) for x in C['comparisons']]+[dict(trial='paused_DC_reserved',case=i,raw_p=None) for i in [19,35,39]]+[dict(trial='DC2',case=x['case_index'],raw_p=x['cost_p_raw']) for x in A['comparisons']]
order=sorted(range(9),key=lambda i:rows[i]['raw_p'] if rows[i]['raw_p'] is not None else 1);prev=0
for rank,i in enumerate(order):
 raw=rows[i]['raw_p'];adj=min(1,max(prev,(9-rank)*(raw if raw is not None else 1)));prev=adj;rows[i]['cumulative_holm9']=adj if raw is not None else None
(R/'CUMULATIVE_EXPLORATORY_TESTS.json').write_text(json.dumps({'scope':'exploratory adaptive revisions, not independent confirmatory validation','family_size':9,'incomplete_old_DC_tests_reserved_at_1':True,'tests':rows},indent=2))
print('POSTPROCESSED')

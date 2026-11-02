from pathlib import Path
import hashlib,json
F=Path(__file__).resolve().parent
dest=F/'POSTMORTEM_FIRST.json';assert not dest.exists()
r=json.loads((F/'RESULT_FIRST.json').read_text());b=json.loads((F/'ONEWAY_PHASE_FIRST.json').read_text());a=json.loads((F.parent/'P142_profile_and_task_chain/BASELINE_FIRST.json').read_text())
pre=json.loads((F/'PREDECLARATION_FIRST.json').read_text())
assert hashlib.sha256((F/'check_sdk_phase.py').read_bytes()).hexdigest()==pre['code_sha256']
manifest=json.loads((F/'CANDIDATE_MANIFEST_FIRST.json').read_text())
assert all(hashlib.sha256((F/'candidate_project'/n).read_bytes()).hexdigest()==h for n,h in manifest['candidate_files'].items())
assert all(r['checks'][n]for n in['all_five_phase_started','identical_prefix','actual_decisions_changed','all_final_routes_deploy_or_return','all_drops_after_actual_phase','all10'])
old=a['coverage_evaluation'];new=b['coverage_evaluation']
before=a['submission_records'][0]['breakdown'];after=b['submission_records'][0]['breakdown']
def drops(j):
    previous=[2]*5;out=[]
    for row in j['rows']:
        for i,q in enumerate(row['inventory']):
            if q<previous[i]:out.append(dict(owner=i,step=row['step']))
        previous=row['inventory']
    return out
out=dict(status='REAL_ONEWAY_PHASE_EXECUTED_BUT_FAILED_MAP_AND_TOTAL_GAIN',
         raw_result_sha256=hashlib.sha256((F/'ONEWAY_PHASE_FIRST.json').read_bytes()).hexdigest(),
         source_frozen_and_all_gates_preserved=True,checks=r['checks'],
         baseline={**old,'steps':a['physics_steps'],'mean5_map':sum(e['score']for e in a['map_results'])/5,'credit_percent':100*before['credit'],'false_penalty_pp':100*before['penalty']},
         candidate={**new,'steps':b['physics_steps'],'mean5_map':sum(e['score']for e in b['map_results'])/5,'credit_percent':100*after['credit'],'false_penalty_pp':100*after['penalty']},
         delta=dict(map=new['actual_submitted_map']-old['actual_submitted_map'],wall=new['score_wall']-old['score_wall'],
                    subtotal=new['controllable_subtotal']-old['controllable_subtotal'],steps=b['physics_steps']-a['physics_steps'],
                    credit_pp=100*(after['credit']-before['credit']),false_penalty_pp=100*(after['penalty']-before['penalty'])),
         phase_started=r['phase_started'],baseline_drops=drops(a),candidate_drops=drops(b),
         baseline_actual_deferrals=sum(e['defer']for e in a['deferrals']),baseline_deferral_calls=len(a['deferrals']),
         parent_health=r['parent_health_min'],candidate_health=r['candidate_health_min'],
         total_health_loss_parent=sum(50-x for x in r['parent_health_min']),total_health_loss_candidate=sum(50-x for x in r['candidate_health_min']),
         interpretation=['All five entered deployment at264..266, first drop307; one-way switch was actually executed, not just relabelled.',
                         'The parent actually deferred zero of69 observed commitment checks in this episode. Do not explain the score change as elimination of repeated parent deferrals.',
                         'Owner3 starts target12 steps earlier but first drop445->840 and task releases occur458/708. New contact health losses363/364 precede the releases; exact release cause was not observed.',
                         'Total health loss remains2, but owners change. Per-owner no-regression gate fails; do not say extra total damage occurred.',
                         'Map loss is mostly increased false-paint penalty, not simply reduced wall observation.'],
         decision='No native/five or promotion. Preserve this first result; do not change phase parameters, seed, label or renderer to rescue it.',
         limitations=['One authored same-input scenario, no BLUE/full red score or five-map mean.',
                      'A local single-phase rule does not prove all globally synchronized two-phase designs are worse. Entry timing/relay fallback/execution recovery are part of this exact engineering adaptation.'],native_rounds=0)
dest.write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
note='''
首次真实SDK已终态：STOP_FIRST_ONEWAY_PHASE_MECHANISM_GATE。五机264/265/265/266/265实际切换，首切换前所有行同父本，131个切换后最终路线均为投放目标或回联络/hold；10次实际库存下降全部在各自切换后。43payload及harness SHA复核不变，未重跑。
父本→新：10→10枚，地图95.47034292→93.80367625（−1.66666667），墙体覆盖74.65800920→76.72571393（+2.06770472），时间100→100，结束779→872步（+93），可控小计72.66677330→72.24698091（−.41979239）。没有BLUE，此小计不是完整红分。均未hit作者90秒loop界限。
地图credit99.95560%→99.90233%，误绘penalty4.48526→6.09865pp；主要是误绘增加，不能简单说“少探索漏了大片墙”。5raw均分也下降，不只是选择提交者从0变3。
父本69次commitment检查实际defer为0！因此本场不能把改善原因归为阻止大量拖延；新阶段同时影响接单时刻、补扫/空载任务和失败任务回退。3号接受首目标从278提前到266，但首次投放445变840；458/708目标被释放并返回联络，734重新接回首目标，840/871才两投，拖长尾部。363/364发生0/3号健康各掉1；父本344步1/4各掉1，总掉血仍2，不能说总损伤增加，但不满足逐机健康不退步。具体释放分支/谁与谁发生接触未采集，不能硬归因为纯拥堵、A*或投放禁区。
按事前门槛淘汰，不扩正式单图/五图、不调阶段时刻或混入P152地图层来救分。用户的二阶段思路不是被普遍否定；这个具体“一有有效计划便不可逆切换”的实现没有优于当前底本。原P48 A*保留。
附首错：只读汇总误用了mission_state的assignment键，真实task_snapshot字段为assignment_goal；ANALYSIS_FIRST_ERROR保留，V2只改诊断字段后读取同一数据，无SDK/候选/场景重跑。
'''
with(F/'分析依据与小测试结论.txt').open('a',encoding='utf-8')as f:f.write(note)
print(json.dumps(dict(status=out['status'],delta=out['delta'],parent_deferrals=out['baseline_actual_deferrals'],health_loss=[out['total_health_loss_parent'],out['total_health_loss_candidate']]),ensure_ascii=False))

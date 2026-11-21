"""Read existing JSON/NPZ and source text only. No controller or SDK imports."""
from pathlib import Path
from hashlib import sha256
import json
import numpy as np

root=Path(__file__).resolve().parent
base=root.parent/'team615_messenger_batch1_20261121'
sources=base/'baseline'
data=base/'received'/'Map08_baseline'
dest=root/'delivery'
dest.mkdir(exist_ok=True)
score=json.loads((data/'OFFICIAL_SCORE.json').read_text(encoding='utf-8'))
details={r['drone']:r for r in score['drone_details']}
recording=next((data/'official'/'recordings').glob('*.npz'))
z=np.load(recording)
states=z['drone_states']
xy=np.stack((states['x'],states['y']),axis=-1).astype(float)
events=[json.loads(s) for s in (data/'placement_events.jsonl').read_text().splitlines()]
traces=[e for e in events if e['event']=='trace']
assert len(traces)==572
for e in traces:
    assert np.linalg.norm(xy[e['step']-3,e['drone']]-e['physical_xy'])<.0002

contacts={}
for i in range(5):
    for j in range(i+1,5):
        distances=np.linalg.norm(xy[:,i]-xy[:,j],axis=1)
        ids=np.flatnonzero(distances<180)
        groups=np.split(ids,np.flatnonzero(np.diff(ids)>1)+1)
        contacts[f'{i}-{j}']=[dict(start=int(g[0]+3),end=int(g[-1]+3),min_distance=float(distances[g].min()))
                              for g in groups if len(g)]

p=xy[2387-3:3240-3+1,2]
motion2=dict(start=p[0].tolist(),end=p[-1].tolist(),min=p.min(0).tolist(),max=p.max(0).tolist(),
             distance_pixels=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()),
             warning='Position stability does not prove zero new lidar or bearing evidence.')

snippets={
    'red_hooks.py':[(161,203),(487,504),(613,644),(943,973),(976,991),(1039,1087)],
    'greedy_mapping.py':[(93,112)],
    'pre_submit_scan.py':[(4,44)],
    'final_map_relay.py':[(4,76)],
    'partial_map_submit.py':[(1,8)],
    'deadline_submission.py':[(9,50)],
    'submission_renderer.py':[(23,43)],
    'coverage_placement.py':[(108,123)]
}
excerpt=[]
for name,ranges in snippets.items():
    lines=(sources/name).read_text(encoding='utf-8').splitlines()
    for start,end in ranges:
        excerpt.append(f'=== {name}:{start}-{min(end,len(lines))} ===')
        excerpt.extend(f'{i}: {lines[i-1]}' for i in range(start,min(end,len(lines))+1))
(dest/'SOURCE_EXCERPTS.txt').write_text('\n'.join(excerpt)+'\n',encoding='utf-8')

baseline_zip=base/'original.zip'
assert sha256(baseline_zip.read_bytes()).hexdigest()=='c3021a3eb48031e82bfac9306654b48ca09f168d6f65b13349cf12f783104c7c'
source_hashes={name:sha256((sources/name).read_bytes()).hexdigest() for name in snippets}
result=dict(new_matches=0,simulation_steps=0,controller_functions_executed=0,seed=615,map='Map08',
    baseline_zip_sha256=sha256(baseline_zip.read_bytes()).hexdigest(),
    inputs={str(p):sha256(p.read_bytes()).hexdigest() for p in [recording,data/'OFFICIAL_SCORE.json',data/'placement_events.jsonl',base/'stage_run.py']},
    source_hashes=source_hashes,alignment_checks=len(traces),frame_offset=3,
    all_pair_geometric_radio_contacts=contacts,motion2_since_received_version=motion2,
    drone_details=details,observed_submissions=score['submissions'],
    recorded_drone4_packets=[e for e in events if e['event']=='messenger_map_refresh'],
    known_stock_cleared_at_drone0=2538,
    packet_lineage_findings={
        'direct_revision_is_sender_not_original_source':True,
        'original_packet_includes_merged_memory':True,
        'origin_pixel_payloads_saved':False,
        'archived_per_packet_wall_free_bearing_arrays':False,
        'raw_message_receipt_timeline_for_drone0':False,
        'drone2_version2387_was_already_received_by_drone0_before3240':'confirmed by final direct revision and last radio contact before2422',
        'drone4_direct2479_already_received_before3240':'confirmed by final direct revision and contact ending2981',
        'drone3_direct_at3240_estimate':3213,
        'drone1_via_drone3_at3240_supported_lower_bound':2971,
        'reconstructed_timestamps_warning':'3213 and2971 transport lineage are source/trajectory deductions, not an exported per-step packet-array snapshot.',
        'missing_updates_at3240':['drone1 updates after2971','drone4 local updates after messenger DONE3176, packet3199'],
        'effective_unique_correct_wall_pixels_missing':'UNKNOWN: not recoverable exactly from exported arrays.'},
    submission_gates=[
        dict(gate='minimum ordinary opening',function='RedHooks._submission_window_open',step=3240,actual=True),
        dict(gate='pre-submit scan continuation',function='PreSubmitScan.waiting',start=3240,end_exclusive=3420,actual=True),
        dict(gate='final snapshot collection',function='FinalMaps.waiting',start=3420,end_exclusive=3444,
             explanation='Source2 cannot freeze because it still believes drone4 has stock1; source3 freezes only after its last contact3361. Missing final snapshots are not proof of missing live map evidence.'),
        dict(gate='submission preference',function='RedHooks._prefer_own_submission',
             possible='fresh higher ready peer; historical preference may wait until3468; weaker ready opportunity can last48steps',
             actual_extra_delay='not demonstrated by archived fields; old branch first reachable at3444'),
        dict(gate='partial-map guard',function='provisional_map',actual=False,
             reason='Map estimate8949 at3240 and9025 at3420 exceed5000'),
        dict(gate='last30/dual deadline',function='DeadlineSubmission',step_window_start=5371,ordinary_submit3444_is_deadline_fallback=False)
    ],
    recommended_minimal_design=dict(algorithm_changes_applied=False,files_to_change=['red_hooks.py'],
        keep_original_flight_and_scan_through3420=True,mandatory_drone2_return=False,mandatory_rendezvous=False,
        exit='At existing scan end, drone0 may submit freshly rendered current memory directly if team inventory is confirmed empty, no pending drop, image usable and unchanged partial-map guard passes.',
        bypass_only_for_drone0=['FinalMaps.waiting','_prefer_own_submission'],
        preserve=['original scan window','placement review','navigation','map fitting','ordinary packet refresh','pre-control dual deadline fallback','other aircraft original path'],
        counterfactual_timing='Target3420 instead of3444 on the frozen baseline, conditional on current image and ordinary validity guards; no simulation performed.',
        maximum_observed_tail_removed=24,
        caveat='3420..3444 new live data and final snapshots would be foregone; equal score is not proven. Earlier3300-style targets cannot be promised with latest1/4 information and unchanged flight.'),
    old_early24_observation=dict(step=2753,map_score=68.00802892561715,original_map_score=score['map_score'],
        warning='Different candidate trajectory; demonstrates risk, not a controlled causal estimate for this design.'))
(dest/'EVIDENCE.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

report='''潜力1.1原版种子615 Map08：0号缺图、2号返航必要性和提前交图最小方案

结论
撤掉全员定点会合和2号提前返航。现有日志不能证明0号缺2号独有的有效墙面信息。实际薄弱处是1号后期地图，以及4号结束信使后才恢复刷新的地图；原轨迹已有3→0、4→1→0的传递机会。
要保证方案不再被旧窗口串行拖延，最小可审查改动是：保留原版飞行和3240～3420扫描，只给0号加一个3420收尾即提交的出口，跳过额外24步终局快照等待和旧选举等待。目标是3444→3420，只省24个比赛步，不应冒称大幅加速。算法未修改，新仿真=0。

一、证据能回答什么，不能回答什么
OFFICIAL_SCORE.final_source_versions来源是dict(d.map_revision)，不是“原始来源有效地图全账本”。RedHooks.receive按直接发送者更新map_revision，但MapMemory.packet打包整个已融合memory；接收后采用hits逐格max、free或并和visits max。方向证据也会经SubmissionBearings进行OR并再转发。
所以“0号的2号版本2387、1号版本很老”不等于“0号没收到2/1号地图”。收到3号当前融合包，可以携带此前1/2/4号证据。FinalMaps.mask更只计终局快照的owner数，也不是独有墙面数量。
归档没有逐包hits/free/bearings数组，没有3240时每机memory，也没有0号逐步收包快照，因此无法逐像素确定“缺谁多少正确墙、能带来多少分”。最终地图差分也不能归因给单架机。版本和距离只能确定传递机会、内容时间上限及等待逻辑，不能代替有效新增像素比较。

二、3240前0号的实际信息结构
2号：0号最终直收版本为2387，而0↔2最后连通2389～2421；所以这份地图早已收到，不是缺整张地图。3号也带着2号2387版本，可重复转入0号。2号自2387到3240位置范围仅x85.71～91.35、y-453.67～-451.45，累计移动27.76px；仍可能有细微新观测或新方向证据，不能称绝对零新增，但不足以支持专门跑1054px回来。2号不应成为必须到齐条件。
3号：2983～3254一直与0号处于180px内，3240附近已有直接传递机会。按周期45步且错开编号的正常发包规则，可还原3240附近0号可得到3号3213版本；这是源码/轨迹还原，不是保存的逐帧包数组。
1号：0↔1上次连通1317～1566，之后直到3418才重新连通。但1↔3在2771～3017连通，3号最终直收1号版本为2971，因此3号后续融合包支持将1号2971版本内容带给0号。0号真正可能缺的是1号2971以后新增内容，不是1号完整地图；哪些内容被0号或3号自己的观测补掉，无法从日志精确判定。
4号：0号最终直收4号版本2479，且0↔4最后连通2933～2981。4号2489进入信使ACTIVE，3176结束；ACTIVE从red_hooks.control提前return，正常MapMemory.observe与red_packet刷新被跳过，因而直到结束仍转发旧2479包。原版恢复后3199生成新包、3244继续刷新。这些包在3240前没有通往0号的通信链：4↔3最后3016，4↔1要到3272再连通，4↔0要到结束也未再直连。
所以4号3199及以后新包缺失是可确定的“尚未送达的新数据”，但其中多少是独有正确墙点仍不能确认。
0号库存方面：2538步已通过4号收到4号清零，其他库存此前已确认清零；这场原版没有“0号一直等不到末弹确认”的事实基础。

三、已有路径能补什么，为什么不必另建会合
0↔3：2983～3254、3335～3361，原版最终直收3号3357版本。
4↔1：3272～3388、3404到终局，4号新地图可先合入1号。
1↔0：3418到终局，0号最后收到1号3421版本；源码支持1号融合包携带4号新数据转入0号。归档没有保存这次具体像素贡献，不能声称已量化收益。
仅沿原轨迹，1号及4号较晚的新信息最快也要等这段晚接触。若要求3300或更早交图，还要拿齐这两者的后期资料，就不能同时要求飞行不变；必须改变接触时机，或接受放弃部分后期信息。

四、真正挡住提交的窗口
1. RedHooks._submission_window_open：5400步上限的3/5=3240步；或墙钟达到85%。原版提交墙钟约130.16秒，180秒的85%为153秒，本场是步数窗口起作用。2538全清并不直接打开交图。
2. PreSubmitScan.waiting：3240～3419继续搜索和收包，3420才结束。日志freeze_audit的begin实际是扫描等待开始，不能误读为3240已冻结最终图。0号内部质量估计3240为8949、3420为9025，证明数值变化，但不是官方地图分或变化来源的证明。
3. FinalMaps.freeze在全队已清零时，还要求step>=3420。此时才建立终局快照。
4. FinalMaps.waiting：不到五份快照就启动24步收集；3420开始，3444到期。2号仍把4号库存记为[2007,1]，所以其_all_inventory_empty为假，3420根本不能冻自己的快照。3号直到3420才冻结，但它与0号最后接触3361、与其他机更早就失联，所以3号的新终局快照也无法及时传出。缺终局快照并不证明0号缺它们的有效实时地图。最终0号3444提交，符合3420+24链条。
5. _prefer_own_submission：新鲜更高排名、历史更高排名都可能挡提前出口；历史偏好可拖到3420+48=3468，另有48步候选等待。不能只把前面某个return删掉就保证立即交图。现有归档未保存该逐步选举状态，不能宣称本场额外实等了48步；只能确认3444提交时通过。
6. provisional_map：估计低于5000且长期无同伴地图才继续等。0号8949/9025，本场并未因此被挡；不建议删这一检查。
7. DeadlineSubmission最后30步窗口在5371开始，步数/墙钟应急出口在control前段优先执行。本场3444为普通交图，walltime_submission=null；不能将其归因于双时限兜底失效。

五、压缩后的最小修改设计（只设计，未实施）
仅red_hooks.py：在普通提交分支中，已有_submission_window_open通过且PreSubmitScan扫描结束后、FinalMaps.waiting和_prefer_own_submission之前，增加0号单独提交出口。
进入条件保留：全队实际库存确认清零、本机没有pending_drop、未提交、当前地图可渲染且非空；沿用现有partial-map检查。渲染使用此刻memory及已接收证据，经原_submission_image路径生成，不拿早先预制图冒充当前图。
0号作为既定收图者，满足条件就提交；仅该出口不再因“终局快照不足五份”重等24步，也不再进入旧候选选举。其他飞机和异常回退仍按原版执行。pre-control的双时限应急出口优先级不变。
不改变0号的3420前行为，因此原版已有的3→0及4→1→0接触机会仍保留。2号不提前返航，不设置(780,-180)定点，不新增按缺口配送、末弹再配送或ACTIVE地图刷新，不改投放、导航与拟合参数。
基于这场冻结日志，目标交图步为3420而非3444，削掉24步尾部等待。仍需承认：3420～3444后续新增数据和1号3421版本最终包会被放弃，不能保证同分；旧历史选举是否会单独挡在3420，归档无法逐步恢复，所以方案需要明确绕过该旧选举，不能仅删除FinalMaps.waiting调用。

六、是否值得继续扩大修改
如果只愿意做非常小的加速，上述尾部出口是最小、可审查的方向，但仅24个比赛步，墙钟能省多少未验证，不应为此投入复杂协调开发。
不推荐直接恢复“全清后24步交图”：已有该候选Map08在2753交图、地图分68.01，原版80.23，说明过早结束可能损失地图；它还改变了飞行，不能当本方案的因果预测。
若要求显著提前到3300左右，现有证据不足以同时保证拿到1/4后期资料和保持地图效果。应先补逐包增量/渲染前后对照证据，再决定是否缩短扫描窗口或改接触，不能继续按“版本旧就缺图”驱动全队返航。
后续如授权实施，先做纯逻辑反例：收包但仍有pending/库存未清不得提交；无效/空图不得提交；0号3420可绕过五份快照与历史选举；非0保留原逻辑；步数/墙钟紧急出口仍优先；当前图而非旧缓存被提交。此轮未运行这些反例，也未运行整场仿真。
'''
(dest/'REPORT.txt').write_text(report,encoding='utf-8')
(dest/'AUDIT_SCRIPT.py').write_bytes(Path(__file__).read_bytes())
manifest={p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir()) if p.name!='CHECKSUMS_SHA256.json'}
(dest/'CHECKSUMS_SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'status':'read-only audit complete','files':list(manifest),'source0_final':details[0]['final_source_versions'],
 'motion2':motion2,'no_map_packet_arrays_available':True,'target_submit_step':3420},ensure_ascii=False))

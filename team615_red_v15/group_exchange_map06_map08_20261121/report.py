from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
import json,shutil

r=Path(__file__).resolve().parent;read=lambda p:json.loads(p.read_bytes())
results={name:read(r/name/'RESULTS.json') for name in ['Map06','Map08']}
prior=r.parent/'team615_group_exchange_map09_20261121'
build=read(prior/'BUILD.json');candidate_hash=build['candidate_zip_sha256']
assert candidate_hash=='641685d7bd460f6241abb4e2c0f02527d7324a37d78f6492401d66a4b6a63cda'
for name,result in results.items():
    assert result['candidate_zip_sha256']==candidate_hash
    assert sha256((r/name/'candidate_snapshot.zip').read_bytes()).hexdigest()==candidate_hash

def mechanism(result):
    groups=result['group_details'];score=read(r/result['map']/'received/OFFICIAL_SCORE.json')
    all_audits=[(int(i),v) for i,g in groups.items() for v in g['group_audit']]
    proposals=[(i,v) for i,v in all_audits if v[1]=='choice_proposed']
    submissions=[(i,v) for i,v in all_audits if v[1] in ('submitted','soft_cutoff_submit')]
    return dict(
        root_by_drone={i:g['group_root'] for i,g in groups.items()},
        root_ack_members_by_drone={i:g['group_root_acks'] for i,g in groups.items()},
        return_start_by_drone={i:g['group_started'] for i,g in groups.items()},
        route_abort_by_drone={i:g['abort_events'] for i,g in groups.items()},
        phase_by_drone={i:g['group_phase'] for i,g in groups.items()},
        branch_by_drone={i:g['group_branch'] for i,g in groups.items()},
        received_payloads=[dict(receiver=int(i),entry=v) for i,g in groups.items() for v in g['stored_payloads']],
        actually_full_personal_pool_holders=[int(i) for i,g in groups.items() if
            set(range(5)).issubset(g['snapshot_owners']) and set(range(5)).issubset(g['image_owners'])],
        choice_proposals=proposals,group_submission_events=submissions,
        final_inventory_records={str(v['drone']):v['final_inventory_records'] for v in score['drone_details']})

for result in results.values():
    result['mechanism']=mechanism(result)
    result['post_run_source_check']=read(r/result['map']/'received/POST_RUN_SOURCE_CHECK.json')
    assert result['post_run_source_check']['status']=='PASS'
config=dict(candidate_zip_sha256=candidate_hash,baseline_zip_sha256=build['baseline_zip_sha256'],
    identical_to_map09_candidate=True,algorithm_files_changed_in_this_task=[],maps=['Map06','Map08'],seed=615,
    new_red_rounds_per_map=1,new_red_rounds_total=2,blue_rounds=0,historical_original_rounds=2,
    serial=True,sdk_commit='6557940dc18549ffc7a945db887da5b05b7ed2f1',
    timestep_limit=5400,walltime_limit=180,drones=5,bombs_per_drone=2,zones=['NO_COM_ZONE','NO_GPS_ZONE'],
    validation='Reused 36 synthetic cases and static/environment receipt for byte-identical Map09 candidate; not rerun.',
    source_commit='aa8c14a7021a625378455ab985387dcaec1ec79d')
all_results=dict(status='COMPLETE',configuration=config,maps=results,
    limitations=['One new candidate round per map with historical same-seed originals; no statistical improvement claim.',
                 'Only red-side 80-point subtotal measured; blue-side 20-point bomb-difficulty term unmeasured.',
                 'Walltime comparisons are sensitive to runtime load and cannot alone establish computational acceleration.'])
all_results['conclusion']='Neither map completed the grouped best-map election. Map06 score fell and submitted later; Map08 score fell at the same submission step. Do not promote as an accelerated replacement.'
dest=r/'delivery';dest.mkdir(exist_ok=True)
(dest/'RESULTS.json').write_text(json.dumps(all_results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(dest/'RUN_CONFIGURATION.json').write_text(json.dumps(config,indent=2)+'\n')

lines=['# 同一分组返航候选：Map06、Map08，种子615','',
       '两张地图各新增1局候选红队测试，串行运行；原版使用已有同种子结果。本轮未修改算法、未重跑Map09、未运行蓝队。',
       '',f'候选ZIP SHA256：`{candidate_hash}`。与此前Map09实测候选逐字节一致，56个成员逐项绑定。',
       '', '候选源码、实现说明和已有36组合成反例见[Map09交付](https://github.com/quanliangwen/1/tree/aa8c14a7021a625378455ab985387dcaec1ec79d/team615_red_v15/group_exchange_map09_20261121)。',
       '', '## 分数与时间','',
       '| 指标 | Map06原版 | Map06候选 | Map08原版 | Map08候选 |',
       '|---|---:|---:|---:|---:|']
metrics=[('红队小计 / 80','partial_score_out_of_80',4),('地图分 / 100','map_score',4),
    ('墙覆盖分 / 100','wall_score',4),('交图步数','submission_step',0),('漏墙像素','missed_wall_pixels',0),
    ('扣分误画像素','charged_misdraw_pixels',0),('探索率 / %','exploration_percent',4),('实投数','placed',0),
    ('总掉血','total_health_lost',0),('整局墙钟 / 秒','elapsed_walltime_seconds',3)]
for label,key,precision in metrics:
    vals=[results[name][arm][key] for name in ['Map06','Map08'] for arm in ['original','candidate']]
    lines.append('| '+label+' | '+' | '.join(f'{v:.{precision}f}' for v in vals)+' |')
for name,result in results.items():
    o,c,d=result['original'],result['candidate'],result['candidate_minus_original'];m=result['mechanism']
    selected=c['selected_submission'];who=None if selected is None else selected.get('drone')
    lines.extend(['',f'## {name}机制核对','',
       f"得分变化 **{d['partial_score_out_of_80']:+.4f}**；交图步数变化 **{d['submission_step']:+d}**；墙钟变化 **{d['elapsed_walltime_seconds']:+.3f}秒**。候选选中交图机：{who}号。",
       '', '| 无人机 | 返航开始 | 返航退出事件 | 末态 | 实际持有快照owner | 实际持有图owner |',
       '|---|---:|---|---|---|---|'])
    for i,g in result['group_details'].items():
        start='未接管' if g['group_started'] is None else str(g['group_started'])
        aborted='；'.join(f'{v[0]}:{v[2]}' for v in g['abort_events']) or '—'
        lines.append(f"| {i}号 | {start} | {aborted} | {g['group_phase']} | {g['snapshot_owners']} | {g['image_owners']} |")
    lines.extend(['',f"真实保存的外来载荷次数：{len(m['received_payloads'])}；实际持齐5份个人快照及5张个人图的机器：{m['actually_full_personal_pool_holders']}；择图提案次数：{len(m['choice_proposals'])}；分组模块提交次数：{len(m['group_submission_events'])}。",
        '', '| 无人机 | 原版末弹确认 | 候选末弹确认 | 差值 |','|---|---:|---:|---:|'])
    for i in range(5):
        a,b=o['per_drone_last_confirmation'][str(i)],c['per_drone_last_confirmation'][str(i)]
        difference='—' if a is None or b is None else f'{b-a:+d}'
        lines.append(f'| {i}号 | {a} | {b} | {difference} |')
    lines.extend(['','候选最终各机交图/兜底事件：','', '```json',json.dumps(c['deadline_events'],ensure_ascii=False,indent=2),'```','',
        '共享父点、接受成员、局部分组与实际载荷明细：','', '```json',json.dumps(m,ensure_ascii=False,indent=2),'```','',
        '轨迹记录前缀对照：','', '```json',json.dumps(result['recorded_prefix'],indent=2),'```','',
        '得分变化分解：','', '```json',json.dumps(result['score_contribution_changes'],indent=2),'```'])
lines.extend(['','## 结论与边界','',
    '**两张地图均未实现完整分组择图，当前不建议作为加速版替换原版。**','',
    '- Map06：得分下降1.5850，交图晚525步。虽然3号末弹由3957提前到3297，但全队信息没有汇集到提交者，最终仍耗到墙钟兜底。5架返航均因当前安全连接检查失败而退出；仅3/4号在3895步互收快照、3897步互收位图。',
    '- Map08：得分下降1.5202，交图仍为3444步，提交者由原版0号改为1号。0/3号和1/4号完成局部载荷交换，2号因预算不足没有返航，各组没有打通完整交互。',
    '- Map08存在明确的提交协调缺口：1号3336步退出返航后，本机恢复旧普通提交资格；0号到3444步仍为RETURN_LOCAL，旧普通出口受协同门控。1号随后从旧普通出口交图，新的统一择图并未运行。这能确认提交者变化的路径，但不能据此断言新版本0号的图一定更高分。',
    '- Map08的10枚炸弹确认步数与原版一致，记录中的炸弹状态全程一致。地图分下降3.0404，漏墙增加3266像素、扣分误画减少5995像素；不是少投弹造成的退分。总掉血由14变16。',
    '- Map08墙钟短11.241秒，但提交步数没有提前且得分更低；历史对照存在负载差异，本次不足以证明稳定的计算加速。',
    '- 两图的实际载荷校验和收据路径都工作过，但没有任何一架实际持齐5份个人快照和5张个人图，没有择图提案，也没有分组模块交图事件。局部收包成功与整套会合成功必须分开评价。',
    '',
    '这里只能评价两个固定种子样本，不能宣称稳定提分。完整会合是否完成，以实际快照/图像保存、择图提案和提交事件为准；单纯分数上涨不构成机制成功。',
    '', '## 复现与交付','',
    '`CANDIDATE_SOURCE.zip`为此前已经测试的完整研究快照，未改字节，不是新正式参赛放行包。`BUILD.json`给出全部源码哈希。',
    '', '`Map06_RUN_EVIDENCE.zip`与`Map08_RUN_EVIDENCE.zip`包含候选原始评分、事件、轨迹、地图输出、SDK与源码绑定、执行脚本，以及历史原版关键证据。两局都使用同一官方SDK提交、5400步/180秒、5机各2弹和两类特殊区域。',
    '', 'Map08的观察器包含历史版本已有的局部轨迹记录；本轮观察器与此前Map09交付的脚本逐字节一致，没有在控制器中注入测试专用策略。',
    '', '红队小计满分80，未测蓝队对应20分。原版是历史运行，墙钟和采用墙钟预算的算法行为可能受负载影响。校验和绑定全部本次交付文件。'])
text='\n'.join(lines)+'\n'
(r/'README.draft.md').write_text(text,encoding='utf-8')
(dest/'README.md').write_text(text,encoding='utf-8')
for name,result in results.items():
    (dest/f'{name}_RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copyfile(r/name/'RUN_EVIDENCE.zip',dest/f'{name}_RUN_EVIDENCE.zip')
shutil.copyfile(prior/'candidate_snapshot.zip',dest/'CANDIDATE_SOURCE.zip')
shutil.copyfile(prior/'BUILD.json',dest/'BUILD.json')
shutil.copyfile(r/'report.py',dest/'report.py')
print(json.dumps({name:dict(delta=v['candidate_minus_original'],mechanism=dict(
    returns=v['mechanism']['return_start_by_drone'],full_pool=v['mechanism']['actually_full_personal_pool_holders'],
    proposals=len(v['mechanism']['choice_proposals']),submits=len(v['mechanism']['group_submission_events'])))
    for name,v in results.items()},indent=2))

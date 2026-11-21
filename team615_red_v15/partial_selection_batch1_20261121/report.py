from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
import json,shutil

r=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_bytes())
results={name:read(r/name/'RESULTS.json') for name in ['Map08','Map09']}
b=read(r/'BUILD.json');v=read(r/'VALIDATION.json');tests=read(r/'counterexamples.json')
assert b['candidate_zip_sha256']==v['candidate_zip_sha256']==tests['archive_sha256']
assert tests['scenario_groups']==53 and tests['status']==v['status']=='PASS'
for name,result in results.items():
    assert result['candidate_zip_sha256']==b['candidate_zip_sha256']
    assert result['post_run_source_check']['status']==result['personal_original_integrity']['status']=='PASS'
    assert result['offline_map_scores']['selected_submission_reproduced']
    for prior,d in result['candidate_minus'].items():
        contribution=.5*d['map_score']+.2*d['wall_score']+.1*d['time_score']
        assert abs(contribution-d['partial_score_out_of_80'])<1e-8

config=dict(seed=615,maps=['Map08','Map09'],new_red_rounds=4,final_candidate_red_rounds=2,initial_diagnostic_red_rounds=2,historical_current_rounds=2,historical_original_rounds=2,
    blue_rounds=0,sdk_commit='6557940dc18549ffc7a945db887da5b05b7ed2f1',drones=5,bombs_per_drone=2,
    timestep_limit=5400,walltime_limit=180,zones=['NO_COM_ZONE','NO_GPS_ZONE'],serial=True,
    baseline='current three-map candidate',baseline_zip_sha256=b['baseline_zip_sha256'],candidate_zip_sha256=b['candidate_zip_sha256'],
    changed_existing_files=b['changed_existing_files'],added_files=[],unchanged_files=b['unchanged_files'],
    source_frozen_during_both_matches=True,navigation_scanning_fitting_placement_deadline_unchanged=True,
    post_score_fixture_error_recovery='Initial Map08 post-score export name collision recovered read-only without rerun for that fixture error; subsequently both maps rerun for the separate algorithm cache-boundary fix.',
    offline_scoring='Official map scorer on saved candidate images only; no new simulation and no truth exposed to controller.')
dest=r/'delivery';dest.mkdir(exist_ok=True)
data=dict(status='COMPLETE',configuration=config,build=b,validation=v,counterexamples=tests,maps=results,
    limitations=['One new candidate round per map; both comparator arms are historical same-seed runs.',
                 'Red-side 80-point subtotal only. Blue-side bomb-difficulty 20 points not measured.',
                 'Wall-clock and wall-clock-budgeted decisions can vary with runtime load.',
                 'Online quality is estimated from observed evidence, not official truth. Offline truth scores do not imply in-flight global availability.'])
data['initial_diagnostic_trials']=dict(candidate_zip_sha256='954563b92accb120f3aa657aa410d2f2ce6050a990de02aa10c74a8faa880d23',
    new_red_rounds=2,maps={name:read(r/'initial_trial'/name/'RESULTS.json')['arms']['candidate'] for name in ['Map08','Map09']},
    reason_for_final_retest='Late already-rendered live maps were skipped after coordination cutoff; fixed without new fitting or navigation changes.')
(dest/'RESULTS.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# 第一批：统一提交资格与部分候选择图——Map08、Map09，种子615','',
    '以当前三图候选为基线，只修改提交/候选比较。本轮先诊断两图，再修复缓存边界后各复测1局，共4局红队仿真；下表只列最终版。原版与当前版采用已核验的历史同种子结果。没有修改导航、扫描或拟合参数。','',
    '## 实施范围','',
    f"基线SHA256：`{b['baseline_zip_sha256']}`；新候选SHA256：`{b['candidate_zip_sha256']}`。",'',
    '- 56个成员，仅修改`group_exchange.py`、`map_candidates.py`、`red_hooks.py`，其余53个文件字节一致。所有返航导航方法AST一致；red_hooks.control去除两个已有绘图结果缓存回调后可逐字节还原当前版。',
    '- 返航中、退出返航后和其他状态采用同一提交协调入口，不因ABORT状态提前恢复另一套普通交图资格。',
    '- 有已有个人候选就按共同证据比较、缓存，不等待5份快照和5张图；比较可以发生在队友尚未投完时，实际提交仍要求全队真实库存清零、本机无pending、现有窗口开放和部分图保护通过。',
    '- 个人冻结图不可覆盖。保留最新本机实时/融合候选，与个人图共同评价；已有缓存流程已生成的实时图尽量直接复用，遇到新快照才用原拟合器生成当前候选，拟合参数不变。',
    '- 输入版本真正变化才重比。重复广播不重启计时。新比较后留2步，再发提案并留2步提交确认；租约最多12步，不再锁到4590步。',
    '- 普通入口沿用当前候选的60%最早窗口，没有重新加入旧180步扫描/24步收图/48步竞价等待。因而部分候选可用且库存已确认时，可能比当前版更早交图；这也是本轮必须核对的信息损失风险。',
    '- 图像槽0～4是个人原图；槽5是本机当前/融合图，不是第六架无人机。槽5只本地使用，不以相同owner在不同机器之间互相覆盖。真正执行者为实际持有选中图且符合投放确认的评分者，可代交别人的个人图。',
    '- 步数/墙钟硬兜底的触发与优先级保持原样，选中图同步进入兜底缓存。任何早交都不能以“发过投弹指令”代替库存确认。','',
    '## 反例和范围验证','',
    '53组合成反例PASS，包含原有36组、本批15组和截止后复用已生成图的2组：两份候选可比较提交、所有返航状态同资格、库存未清只缓存、pending否决、个人原图不变、实时图更新、重复数据不重启、真正新候选重比、本地槽隔离、步数兜底、空图不污染、比较不改导航、窗口保留、已接触成员选举、断联提案过期退出。',
    '', '合成测试禁止pymunk.Space.step，物理步、地图实例、完整比赛均为0。官方静态内容检查和当前只读复用数值环境的实际运算通过。详细回执绑定本次实际候选ZIP，不冒称正式官网兼容验证。','',
    '## 三版对照','']
metrics=[('红队小计 / 80','partial_score_out_of_80',4),('地图分 / 100','map_score',4),('墙覆盖分 / 100','wall_score',4),
    ('交图步数','submission_step',0),('漏墙像素','missed_wall_pixels',0),('扣分误画像素','charged_misdraw_pixels',0),
    ('探索率 / %','exploration_percent',4),('实投数','placed',0),('总掉血','total_health_lost',0),('墙钟 / 秒','elapsed_walltime_seconds',3)]
for name,result in results.items():
    lines.extend(['',f'### {name}','', '| 指标 | 潜力1.1原版 | 当前三图版 | 本批候选 |','|---|---:|---:|---:|'])
    for label,key,prec in metrics:
        lines.append('| '+label+' | '+' | '.join(f"{result['arms'][arm][key]:.{prec}f}" for arm in ['original','current','candidate'])+' |')
    submitters=[result['arms'][a]['selected_submission']['drone'] for a in ['original','current','candidate']]
    lines+=['',f'三版实际选中交图机依次为：{submitters}。', '', '| 无人机 | 原版末弹 | 当前版末弹 | 本批末弹 |','|---|---:|---:|---:|']
    for i in range(5):lines.append(f'| {i}号 | '+' | '.join(str(result['arms'][a]['per_drone_last_confirmation'][str(i)]) for a in ['original','current','candidate'])+' |')
    lines+=['','本批提交、比较与个人图保留证据：','', '| 无人机 | 首次比较步 | 比较时快照数 | 比较次数 | 提案次数 | 分组提交步 |','|---|---:|---:|---:|---:|---|']
    for i,g in result['group_details'].items():
        first=g['comparisons'][0] if g['comparisons'] else None
        lines.append(f"| {i}号 | {first[0] if first else '—'} | {first[2] if first else '—'} | {len(g['comparisons'])} | {len(g['proposals'])} | {[x[0] for x in g['submission_events']]} |")
    lines+=['',f"个人原图完整性：{result['personal_original_integrity']['images_verified']}份持有记录校验PASS，图像摘要与首次构建/接收时一致。",'']
    offline=result['offline_map_scores'];rows=offline['candidates']
    lines+=['离线官方地图评分仅使用本局保存候选，不重跑控制器或仿真：','', '| 持有者 | 候选槽 | 版本步数 | 离线地图分 |','|---|---:|---:|---:|']
    for row in rows:lines.append(f"| {row['holder']}号 | {row['slot']} | {row['version']} | {row['map_score']:.4f} |")
    lines+=['',f"实际提交地图分已精确复现：{offline['actual_map_score']:.4f}。保存候选中的最高分为{offline['best_saved_candidate']['map_score']:.4f}，由{offline['best_saved_candidate']['holder']}号持有、槽{offline['best_saved_candidate']['slot']}。这不代表其他断联机器在比赛中能拿到该图。",'']
lines+=['## 结果判断','', '<!-- FINDINGS -->','',
    '## 首轮诊断与最终版的区别','',
    '首轮候选954563b：Map08为51.7505/80、3245步交图；Map09为42.4621/80、4797步交图。Map09选中缓存版本4231，尽管4590步已有新实时图。修复后候选706915e专门补上截止后复用已生成图，原始两局和错误回执完整保留，未混入最终版分数。','',
    '## 赛后夹具错误说明','',
    '首轮Map08在官方评分与数据导出后，赛后循环变量source覆盖输入目录Path，最后源码核验报错。原始错误保留，通过独立只读检查补齐回执；没有为了此夹具错误重跑控制器。最终复测使用已修正的赛后脚本。',
    '', '另一个独立问题发生在首轮Map09的算法：4590步的新实时图没有在软截止后参加比较，旧4231步图一直占用兜底缓存。已修复这一边界并新增两组反例，随后复测Map08、Map09。首轮两局完整保存在INITIAL_TRIAL_EVIDENCE.zip，不能当作最终候选成绩；总计4局，未跑其他地图。所有比赛中观察函数AST保持相同，最终两图算法ZIP完全一致。','',
    '## 文件与边界','',
    'CANDIDATE_SOURCE.zip为完整研究候选，partial_selection.patch用于当前三图版，不能套在潜力1.1原版。三个修改文件也单独提供。不是新正式参赛放行包，未上传官网。',
    '', '两份RUN_EVIDENCE包包含原始评分、轨迹、实际候选位图、原始快照/方向证据、个人图完整性验证、历史对照、源码/SDK绑定及运行/采集脚本。RESULTS.json记录全部数值和事件。',
    '', '红队仅测80分，蓝队20分未测。单种子、历史对照和墙钟负载差异不支持稳定提分或稳定计算加速的承诺。']
(r/'README.draft.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
for name,result in results.items():
    (dest/f'{name}_RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copyfile(r/name/'RUN_EVIDENCE.zip',dest/f'{name}_RUN_EVIDENCE.zip')
for n in ['BUILD.json','VALIDATION.json','counterexamples.json','partial_selection.patch']:shutil.copyfile(r/n,dest/n)
for n in b['changed_existing_files']:shutil.copyfile(r/'candidate'/n,dest/n)
shutil.copyfile(r/'candidate_snapshot.zip',dest/'CANDIDATE_SOURCE.zip')
shutil.copyfile(r/'report.py',dest/'report.py')
print(json.dumps({name:dict(arms={a:dict(score=v['partial_score_out_of_80'],map=v['map_score'],step=v['submission_step']) for a,v in result['arms'].items()},delta=result['candidate_minus']) for name,result in results.items()},indent=2))

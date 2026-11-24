from pathlib import Path
import json,hashlib,csv,shutil,zipfile,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parent;E=R/'evidence';D=R/'delivery';D.mkdir(exist_ok=True)
A=json.loads((E/'INDEPENDENT_AUDIT_STATISTICS.json').read_text());C=json.loads((R/'COLLECTION_RECEIPT.json').read_text());P=json.loads((R/'PROTOCOL.json').read_text())
assert A['terminal']==180 and not A['global_errors'] and A['new_probability_evaluations']==0
assert A['all_processes_under_600'] and all(r['process_wall_seconds']<=600 for r in A['runs'])
archive=R/'COMPACT_EVIDENCE_FULL.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==C['sha256']
checked=0
for p in (E/'outcomes').glob('*.json'):
 o=json.loads(p.read_text())
 for n,v in o['output_files'].items():
  f=E/'runs'/o['identity']/n;assert f.stat().st_size==v['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==v['sha256'];checked+=1
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
X=D/'S10与椭球DC2_三大算例30次_完整600秒_对比结果.xlsx'
with zipfile.ZipFile(X) as z:
 sheets=[ET.fromstring(z.read('xl/worksheets/sheet%d.xml'%i)) for i in [1,2]]
 assert not [c for sh in sheets for c in sh.findall('.//s:c',ns) if c.attrib.get('t')=='e']
 s={c.attrib['r']:c for c in sheets[0].findall('.//s:c',ns)};raw={c.attrib['r']:c for c in sheets[1].findall('.//s:c',ns)}
 def check(cell,expected):
  v=cell.find('s:v',ns) if cell is not None else None
  if expected is None:assert v is None or v.text in ['',None]
  else:assert v is not None and abs(float(v.text)-expected)<1e-9,(ET.tostring(cell),expected)
 for i,g in enumerate(A['case_summaries'],7):
  for col,k in [('E','valid'),('F','best'),('G','avg'),('H','std'),('I','runtime_mean_seconds'),('J','runtime_std_seconds'),('K','maximum_process_wall_seconds')]:check(s.get(f'{col}{i}'),g[k])
 for i,g in enumerate(A['case_summaries'],24):
  for col,k in [('I','final_solution_first_found_mean_seconds'),('J','best_hits'),('K','best_hit_first_found_mean_seconds')]:check(s.get(f'{col}{i}'),g[k])
 for i,g in enumerate(A['comparisons'],17):
  check(s.get(f'C{i}'),g['mean_difference']);check(s.get(f'D{i}'),g['relative_mean_difference'])
 for i,g in enumerate(A['runs'],5):
  check(raw.get(f'G{i}'),int(g['valid']))
  for col,k in [('H','cost'),('I','LSS_probability'),('J','process_wall_seconds'),('K','search_seconds'),('Z','final_solution_first_found_seconds')]:check(raw.get(f'{col}{i}'),g.get(k))
shutil.copyfile(archive,D/'180次_完整600秒_LSS验收_紧凑证据.tar.gz')
for n in ['INDEPENDENT_AUDIT_STATISTICS.json','PROTOCOL.json','COMPLETED.json','LAUNCH.json','VALIDATION.json']:
 shutil.copyfile(E/n,D/n)
for n in ['DESIGN_AND_DIAGNOSIS.txt','CUMULATIVE_EXPLORATORY_TESTS.json','PREVIOUS_PAUSED_AUDIT.json']:
 shutil.copyfile(R/n,D/n)
for n,rows in [('case_summaries.csv',A['case_summaries']),('paired_comparisons.csv',A['comparisons']),('runs.csv',A['runs'])]:
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with (D/n).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows)
(D/'scripts').mkdir(exist_ok=True)
for n in ['controller.py','audit_remote.py','prepare_trial.py','collect.py','collect_remote.py','build_report.mjs','finalize_delivery.py','validate_remote.py','postprocess.py']:
 shutil.copyfile(R/n,D/'scripts'/n)
with zipfile.ZipFile(D/'EGS_DC2_完整600秒_冻结源码.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in (R/'source').rglob('*'):
  if p.is_file():
   key='source/'+p.relative_to(R/'source').as_posix();assert hashlib.sha256(p.read_bytes()).hexdigest()==P['source_and_binary_pins'][key];z.writestr(key,p.read_bytes())
 for n in ['DESIGN_AND_DIAGNOSIS.txt','PROTOCOL.json','controller.py','VALIDATION.json']:z.writestr(n,(R/n).read_bytes())
 z.writestr('README_CURRENT.txt',('本包为实际执行180次的冻结DC2源码。当前协议和DESIGN_AND_DIAGNOSIS优先于保留旧流程的帮助文字。\n'
  '两臂统一最终仅LSS>=.99，全样本0—499，不计算真实概率，不读取历史解。\n'
  '完整600秒必须通过配套controller从Popen前到退出计时与595秒硬保护；单独调用C++的协作时限不能替代父级硬终止。\n'
  '候选参数：--search-flow ellipsoid_dominance --ellipsoid-gamma 2.4 --ellipsoid-slice 5 --seconds 600 --local-phases none。S10为frontier_mitm。\n'
  '所有已运行身份与失败原样保留；禁止在同目录覆盖重跑。\n').encode())
fmt=lambda x:'空（不足30有效）' if x is None else f'{x:.8f}'
lines=['椭球DC2：恢复迭代后三大算例独立30次结论','',f"180次已终末，独立有效{A['valid']}/180，输出变体核验{A['variants_checked']}个，最高并行{A['completed']['max_active_observed']}。",'唯一最终验收为最后一次完整LSS>=.99，未重算真实概率。完整进程包含全部加载、搜索、LSS、保存fsync及退出，未截断时间。','',
 '编号 | 版本 | 有效/30 | best | avg | 样本std | 平均总耗时(s) | 最大总耗时(s)']
for g in A['case_summaries']:lines.append(f"{g['case_index']} | {g['arm']} | {g['valid']}/30 | {fmt(g['best'])} | {fmt(g['avg'])} | {fmt(g['std'])} | {fmt(g['runtime_mean_seconds'])} | {fmt(g['maximum_process_wall_seconds'])}")
lines+=['','同seed配对成本（DC2-S10）：']
for c in A['comparisons']:
 lines.append(f"{c['case_index']}：方向{c['direction']}；未四舍五入均值差{fmt(c['mean_difference'])}；Holm3 p={fmt(c['cost_p_holm3'])}。")
 lines.append('不足30独立有效，不给官方均值胜负。' if not c['complete_pairs'] else ('本批平均成本相同，不能据此证明等效。' if c['direction']=='平' else ('均值显著'+('降低。' if c['direction']=='优' else '升高，未实现成本改善。') if c['cost_p_holm3']<.05 else '均值差未显著，不视作等效或无用。')))
lines+=['','本轮有边界的收获：APP_30两臂均19/30命中最低观察成本194.09620911316662；条件发现均时S10为168.578秒、DC2为19.997秒。但最终avg/std相同，完整均时344.397→492.140秒，不能把发现更早说成完整算法更快。',
 'LAB_50平均成本相同而完整均时386.706→547.398秒；APP_50候选avg高0.387603（约0.1203%），Holm3 p=0.00003，仍未取得整体改进，不扩展全40例。',
 'APP_50核验2592个候选、添加3072条完整CDF证明支持的割，主搜索改善数仍为0，最终停在本run初始化成本322.6330496141。割合法和处理数量多不能替代成本改善证据。风险代理排序与成本目标不一致是待检验解释，不归咎未经核实的外部进程。',
 '本轮合计9349个精确规范SOC见证通过；其中1个合法离散候选会被旧辅助检查拒绝。原旧失败日志缺少向量和分支，不能将这个新观测说成定位旧失败。']
lines+=['','发现时间口径：每次最终合格向量首次进入本run候选池的时刻；另列命中本组30次最低成本的次数与条件均时。这不是最后一次LSS确认时刻，明细两者分开保留。','',
 '算法解释和适配边界：','DC2沿用无硬风险上界的原生SOC风险主问题、逐组原十进制样本精确比较得到的CDF占优割。只从原完整整数CDF上界<.99的证明生成割，不从抽样LSS失败或未完成证明生成割。最终输出仍须原LSS接受。',
 '规范辅助见证修正：离散x先独立检查分组、成本、处理排除与全部割；再对模型中存储sd系数用精确二进制有理数重建u/t，t向外舍入到平方可行。没有风险上界时此举保持x投影可行集。原求解器t、规范t、精确平方和/松弛和旧检查是否拒绝全部留存。',
 '旧失败只有合并错误信息，无法恢复具体分支；不能声称已经证明旧失败由锥辅助变量造成。新版本遇到真实离散约束违反仍失败并记录具体分支。',
 '原生SOC、均值方差风险目标和CDF占优只是候选生成机制，不是总体概率覆盖定理或CCMCKP全局最优证明。solver optimal只有规范风险和ObjBound相符时才标记proxy optimal。',
 '旧暂停实验的60人为中止、53未启动和1普通失败全部封存，未补跑或覆盖。本批是独立新版本和新鲜S10对照，不与旧结果拼满30。',
 '成本均值先保持未四舍五入值，方向沿冻结协议采用1e-8数值持平容差。best命中按输出成本的精确记录值统计。',
 '这是一系列观察后设计的探索性迭代。除本轮Holm3，累计CF、旧DC预留三项和DC2九项校正在CUMULATIVE_EXPLORATORY_TESTS中披露，不作确认性泛化声明。耗时受60并行与调度影响，标准差小不单独代表更好avg。',
 f"逐文件核验{checked}个输出SHA和字节数，Excel统计公式缓存及180条记录与独立JSON一致。审计未调用求解器、概率评价器或新增MC。",
 '文献与证明：Forbes等2024单调性能逻辑Benders思想，https://pure.tue.nl/ws/portalfiles/portal/352893928/1-s2.0-S037722172300591X-main.pdf 。本题CDF割有单独分位数耦合证明，不照搬排班模型。',
 '数值背景：Gurobi官方容差说明 https://docs.gurobi.com/projects/optimizer/en/current/concepts/numericguide/tolerances_scaling.html 。规范见证的投影等价为本题独立证明，不将官方容差说明当作旧失败原因证明。',
 '协议SHA256：'+A['protocol_sha256'],'证据SHA256：'+C['sha256']]
(D/'DC2_完整600秒_正式结论.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(D/'README.txt').write_text('恢复迭代的DC2独立180次LSS-only对照。Excel、结论、冻结源码和紧凑证据均保留，旧暂停数据独立封存、不混算。结论不得从启动或单纯低波动推定改进成功。\n',encoding='utf-8')
manifest={p.relative_to(D).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in D.rglob('*') if p.is_file() and p.name!='CHECKSUMS_SHA256.json' and not p.name.endswith('.inspect.ndjson')}
(D/'CHECKSUMS_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
proof={'status':'PASS','all180_terminal':True,'independent_valid':A['valid'],'all_actual_wall_under600':True,'variants_checked':A['variants_checked'],'output_files_sha_verified':checked,'xlsx_numeric_and_formula_caches_verified':True,'files':manifest}
(R/'DELIVERY_LOCAL_VERIFIED.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in proof.items() if k!='files'}))

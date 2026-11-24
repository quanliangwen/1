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
X=D/'S10与椭球CP_三大算例30次_完整600秒_对比结果.xlsx'
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
for n in ['DESIGN_AND_DIAGNOSIS.txt','CUMULATIVE_EXPLORATORY_TESTS.json','MEAN_BOUND_DIAGNOSIS.json']:
 shutil.copyfile(R/n,D/n)
for n,rows in [('case_summaries.csv',A['case_summaries']),('paired_comparisons.csv',A['comparisons']),('runs.csv',A['runs'])]:
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with (D/n).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows)
(D/'scripts').mkdir(exist_ok=True)
for n in ['controller.py','audit_remote.py','prepare_trial.py','collect.py','collect_remote.py','build_report.mjs','finalize_delivery.py','validate_remote.py']:
 shutil.copyfile(R/n,D/'scripts'/n)
with zipfile.ZipFile(D/'EGS_CP_完整600秒_冻结源码.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in (R/'source').rglob('*'):
  if p.is_file():
   key='source/'+p.relative_to(R/'source').as_posix();assert hashlib.sha256(p.read_bytes()).hexdigest()==P['source_and_binary_pins'][key];z.writestr(key,p.read_bytes())
 for n in ['DESIGN_AND_DIAGNOSIS.txt','PROTOCOL.json','controller.py','VALIDATION.json']:z.writestr(n,(R/n).read_bytes())
 z.writestr('README_CURRENT.txt',('本包为实际执行180次的冻结CP源码。当前协议和DESIGN_AND_DIAGNOSIS优先于保留旧流程的帮助文字。\n'
  '两臂统一最终仅LSS>=.99，全样本0—499，不计算真实概率，不读取历史解。\n'
  '完整600秒必须通过配套controller从Popen前到退出计时与595秒硬保护；单独调用C++的协作时限不能替代父级硬终止。\n'
  '候选参数：--search-flow ellipsoid_costpriority --ellipsoid-gamma 2.4 --ellipsoid-slice 5 --seconds 600 --local-phases none。S10为frontier_mitm。\n'
  '所有已运行身份与失败原样保留；禁止在同目录覆盖重跑。\n').encode())
fmt=lambda x:'空（不足30有效）' if x is None else f'{x:.8f}'
lines=['成本优先、椭球次级CP：三大算例各30次正式结果','',f"180次已终末，独立有效{A['valid']}/180，540输出变体核验通过；最高并行{A['completed']['max_active_observed']}，0资源事件。",
 f"最长实际进程{max(r['process_wall_seconds'] for r in A['runs']):.9f}秒。包含启动、加载、初始化、全部搜索/CDF/LSS、保存fsync和退出，没有clip为600。",
 '2026-11-24北京时间17:00:50自然结束。仅最后完整原LSS>=.99验收，样本0..499，sum<T，原百万MC/精确分支不变；没有重新计算真实概率。','',
 '编号 | 版本 | 有效/30 | best | avg | 样本std | 平均完整耗时(s) | 最大完整耗时(s)']
for g in A['case_summaries']:lines.append(f"{g['case_index']} | {g['arm']} | {g['valid']}/30 | {fmt(g['best'])} | {fmt(g['avg'])} | {fmt(g['std'])} | {fmt(g['runtime_mean_seconds'])} | {fmt(g['maximum_process_wall_seconds'])}")
lines+=['','同seed配对成本（CP-S10）：']
for g in A['comparisons']:lines.append(f"{g['case_index']}：{g['direction']}，均值差{fmt(g['mean_difference'])}，相对差{100*g['relative_mean_difference']:.6f}%，Holm3 p={g['cost_p_holm3']:.12g}。")
lines+=['','结论：三个算例平均成本均显著变差。90次候选主搜索改善数全部为0，最终停在各run自身初始化候选附近。低std反映重复输出较贵候选，不代表优于S10。不扩展到40例，不补跑或挑seed。','',
 '完整平均耗时LAB50为493.658→555.908秒，APP30为420.569→505.178秒，APP50为555.756→547.240秒。末例时间略少而成本更高，不能称整体加速。不同批次负载不同，不能把旧DC2和本批S10时间混成同一对照。',
 '主问题诊断（每例r01，仅读取原始边际矩及已有提案，没有新增概率评价）：']
for d in json.loads((R/'MEAN_BOUND_DIAGNOSIS.json').read_text()):
 lines.append(f"{d['case_index']}：提案{d['queries']}个，均值区间[{d['queried_mean_min']:.6f},{d['queried_mean_max']:.6f}]；由Cantelli得到的必要均值上界约{d['diagnostic_necessary_mean_upper']:.6f}，全部{d['excluded_by_necessary_mean_bound']}个超过该界。这是每例r01的描述性诊断，不是全部30次分布总结。")
lines+=['','原因判断：成本首目标在缺少有效概率松弛的主问题中，不断选择成本极低、资源均值却远超容量的方案；现有全组CDF占优割不足以快速排除整个区域。这是已有提案支持的模型松弛薄弱解释，不归责未核实外部进程，也不推断增加并发能改善解质量。',
 '下一轮仅检验一个有证明的必要条件强化：对独立经验边际，若P(sum<T)>=.99，则mu<=T+sqrt(V/99)<=T+sqrt(Vmax/99)，Vmax=sum_g max_j Var(X_gj)。加入线性均值上界切除明显无效区域；原始十进制矩须精确计算并向外舍入。它不是mu+2.4sigma<=T的充分椭球硬约束，也不替代最终LSS。',
 '理论依据：Ryu/Park2021第4页给出Cantelli与矩型机会约束背景 https://arxiv.org/pdf/2105.11875 。上述对下尾的必要条件重排及一组一项全局方差界为本题独立推导，不能冒称是论文原算法或概率等价改写。Forbes等2024的主问题松弛强化原则 https://pure.tue.nl/ws/portalfiles/portal/352893928/1-s2.0-S037722172300591X-main.pdf 。',
 '最终验收只按LSS。原CDF仍为共同搜索内部筛选机制，因此新增必要条件只声称对独立经验CDF目标有效，不对随机LSS可能误接受的所有向量或总体真实分布作覆盖保证。',
 '每run仍从原始数据独立生成初始解，不读任何历史解或别的重复结果。原生SOC、CDF割和层次目标都只指导候选；多目标ObjBound不可用，记录为null，未伪报CCMCKP全局最优界。',
 '报告最终输出解首次进入候选池的均时，以及命中本组best次数/条件均时；它们与最后LSS确认时刻、完整运行时间不同。发现得早不代表算法已提前结束。',
 'avg/std要求30/30独立有效，std分母29。方向按未舍入均值及冻结1e-8数值容差；best是观察最低，不是全局最优证明。',
 '本轮3项符号翻转Holm3，有效率另做McNemar/Holm3；累计CF、旧暂停DC预留、DC2和CP十二项Holm见JSON。属于观察后设计的探索性迭代，不作确认性泛化或将不显著说成无用/等效。',
 f"1800个run输出SHA/字节数、Excel公式缓存及180条记录均已核对。独立审计global_errors=[]，未调用求解器或新增原生MC。",
 '协议SHA256：'+A['protocol_sha256'],'证据包SHA256：'+C['sha256']]
(D/'CP_三大算例_统计与下一轮依据.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(D/'README.txt').write_text('CP完整180次对照，全部独立有效但三个成本均值都显著差于S10。含Excel、冻结源码、全套紧凑证据及下一轮必要条件强化依据，不将低std或启动当作成功。\n',encoding='utf-8')
manifest={p.relative_to(D).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in D.rglob('*') if p.is_file() and p.name!='CHECKSUMS_SHA256.json' and not p.name.endswith('.inspect.ndjson')}
(D/'CHECKSUMS_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
proof={'status':'PASS','all180_terminal':True,'independent_valid':A['valid'],'all_actual_wall_under600':True,'variants_checked':A['variants_checked'],'output_files_sha_verified':checked,'xlsx_numeric_and_formula_caches_verified':True,'files':manifest}
(R/'DELIVERY_LOCAL_VERIFIED.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in proof.items() if k!='files'}))

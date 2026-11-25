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
X=D/'S10与椭球CORE_三大算例30次_完整600秒_对比结果.xlsx'
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
for n in ['DESIGN_AND_DIAGNOSIS.txt','CUMULATIVE_EXPLORATORY_TESTS.json','INDEPENDENT_READER_UNIT_CHECK.json','CORE_TERMINAL_DIAGNOSIS.json','RESULT_SUMMARY_COMPACT.json']:
 shutil.copyfile(R/n,D/n)
for n,rows in [('case_summaries.csv',A['case_summaries']),('paired_comparisons.csv',A['comparisons']),('runs.csv',A['runs'])]:
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with (D/n).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows)
(D/'scripts').mkdir(exist_ok=True)
for n in ['controller.py','audit_remote.py','prepare_protocol.py','collect.py','collect_remote.py','build_report.mjs','finalize_delivery.py','validate_remote.py','analyze_completed.py','test_independent_reader.py']:
 shutil.copyfile(R/n,D/'scripts'/n)
with zipfile.ZipFile(D/'EGS_CORE_完整600秒_冻结源码.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in (R/'source').rglob('*'):
  if p.is_file():
   key='source/'+p.relative_to(R/'source').as_posix();assert hashlib.sha256(p.read_bytes()).hexdigest()==P['source_and_binary_pins'][key];z.writestr(key,p.read_bytes())
 for n in ['DESIGN_AND_DIAGNOSIS.txt','PROTOCOL.json','controller.py','VALIDATION.json']:z.writestr(n,(R/n).read_bytes())
 z.writestr('README_CURRENT.txt',('本包为实际执行180次的冻结CORE源码。当前协议和DESIGN_AND_DIAGNOSIS优先于保留旧流程的帮助文字。\n'
  '两臂统一最终仅LSS>=.99，全样本0—499，不计算真实概率，不读取历史解。\n'
  '完整600秒必须通过配套controller从Popen前到退出计时与595秒硬保护；单独调用C++的协作时限不能替代父级硬终止。\n'
  '候选参数：--search-flow ellipsoid_corecuts --ellipsoid-gamma 2.4 --ellipsoid-slice 5 --seconds 600 --local-phases none。S10为frontier_mitm。\n'
  '所有已运行身份与失败原样保留；禁止在同目录覆盖重跑。\n').encode())
from datetime import datetime
fmt=lambda x:'空（不足30有效）' if x is None else f'{x:.8f}'
finish=datetime.fromisoformat(A['completed']['utc']).astimezone(__import__('datetime').timezone(__import__('datetime').timedelta(hours=8)))
lines=['不可行核心割CORE：三大算例各30次正式结果','',f"180次终末，独立有效{A['valid']}/180，输出变体核验{A['variants_checked']}，最高并行{A['completed']['max_active_observed']}。",
 f"北京时间{finish.isoformat()}自然结束，最长实际进程{max(r['process_wall_seconds'] for r in A['runs']):.9f}秒。",
 '统一最后完整原LSS>=.99验收，0..499、严格sum<T、原MC/精确分支未变；全过程600含加载/初始化/核心证明/全部求解/全部LSS/保存fsync/返回，不clip。',
 '编号 | 版本 | 有效/30 | best | avg | 样本std | 平均完整耗时(s) | 最大完整耗时(s)']
for g in A['case_summaries']:lines.append(f"{g['case_index']} | {g['arm']} | {g['valid']}/30 | {fmt(g['best'])} | {fmt(g['avg'])} | {fmt(g['std'])} | {fmt(g['runtime_mean_seconds'])} | {fmt(g['maximum_process_wall_seconds'])}")
lines+=['','同seed成本比较（CORE-S10）：']
for g in A['comparisons']:lines.append(f"{g['case_index']}：{g['direction']}，均值差{fmt(g['mean_difference'])}，相对差{fmt(g['relative_mean_difference'])}，Holm3 p={g['cost_p_holm3']}。")
lines+=['','机制诊断：']
for g in A['case_summaries']:
 if g['arm']=='S10_TOTAL600':continue
 sizes=g['core_sizes'];lines.append(f"{g['case_index']}：独立有效{g['valid']}/30，核心割{g['core_cuts']}，核心组数范围{min(sizes) if sizes else None}至{max(sizes) if sizes else None}，候选主搜索改善次数{g['ellipsoid_search_improvements']}。核心大小和次数不单独代表性能改善。")
complete=all(g['valid']==30 for g in A['case_summaries'])
if not complete:lines+=['有效覆盖不足，缺失组官方avg/std为空，不从valid-only均值宣称改进；不补跑失败。']
else:
 wins=sum(g['direction']=='优' for g in A['comparisons']);losses=sum(g['direction']=='劣' for g in A['comparisons'])
 lines += [f'三例观察均值：{wins}优、{3-wins-losses}平、{losses}劣。单例显著性见上述Holm3，不将不显著解释为等效。']
 if wins==0 and losses==3 and sum(g.get('ellipsoid_search_improvements') or 0 for g in A['case_summaries'])==0:
  lines+=['阶段判断：本轮不是有效改进。三个成本均值都显著差于本批新鲜S10；候选90次初始化后改善数为0。较小std伴随停留在自身初始化候选，不能解释为综合稳定性改善。不扩展全部40例，不启动下一轮，保留所有结果供重新评估方向。']
diag=json.loads((R/'CORE_TERMINAL_DIAGNOSIS.json').read_text())
lines+=['','全部90次候选运行的耗时诊断（只读旧日志，不重算概率）：']
for d in diag['diagnostics']:
 lines.append(f"{d['case_index']}：主模型平均{d['model_query_mean_seconds']:.3f}s、原候选检查平均{d['candidate_check_mean_seconds']:.3f}s、核心工作平均{d['core_work_mean_seconds']:.3f}s；共查询{d['query_count_total']}次，原CDF接受的新提案{d['raw_CDF_accepted_queries']}。核心割虽已独立证明有效，主模型仍未产生能改善起点的合格新候选。")
lines+=['','这是观察MB失败后设计的探索性试验。累计CF、暂停DC预留、DC2、CP、MB和CORE共18项Holm另见JSON；未完成旧测试按p1预留，不混旧成绩补本批。',
 'CORE唯一新增机制是原经验分布不可行核心割。MB成本/风险层次、必要均值外松弛以及初始化未变；每run自身起点，禁旧解和跨重复输入。椭球仍是候选引导，不是最终约束，也不是新DRO模型。',
 '核心证明针对原独立均匀经验边际CDF目标：非核心组采用逐秩最小包络，使和随机不大于任何真实选择；只有完整整数网格概率上界仍<.99才缩核心。不从MC负观测直接切除区域，不声称保留所有随机LSS误接受向量或总体概率保证。',
 '文献Forbes等2024 EJOR312:840—854第3节及算法2 https://pure.tue.nl/ws/portalfiles/portal/352893928/1-s2.0-S037722172300591X-main.pdf 。核心割是本题独立适配证明，非原文完整算法，不保证600秒原问题全局最优。',
 '最终输出解首次发现均时与最后LSS确认时刻、完整运行时间不同；命中本组best条件均时只含命中者。样本std分母29，best为本批最小观察成本。',
 '小型16向量/256原子和、12真实MIQCP排序、256独立Python计数核对和端到端时钟先通过；正式审计不调用求解器、不新增概率抽样，独立重建核心证书/来源/时钟/LSS及全部输出SHA。',
 '不自动扩40例；后续是否采用须结合avg、波动、完整运行效率及退化共同判断。',
 '协议SHA256：'+A['protocol_sha256'],'紧凑证据SHA256：'+C['sha256']]
(D/'CORE_三大算例_终末统计与结论.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(D/'README.txt').write_text('CORE不可行核心割完整180次对照。以独立审计和中文结论为准，包含Excel、冻结源码、紧凑证据与复现代码。不以低std、启动或生成核心割直接宣称性能改进。\n',encoding='utf-8')
manifest={p.relative_to(D).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in D.rglob('*') if p.is_file() and p.name!='CHECKSUMS_SHA256.json' and not p.name.endswith('.inspect.ndjson')}
(D/'CHECKSUMS_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
proof={'status':'PASS','all180_terminal':True,'independent_valid':A['valid'],'all_actual_wall_under600':True,'variants_checked':A['variants_checked'],'output_files_sha_verified':checked,'xlsx_numeric_and_formula_caches_verified':True,'files':manifest}
(R/'DELIVERY_LOCAL_VERIFIED.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in proof.items() if k!='files'}))

from pathlib import Path
import json,hashlib,csv,shutil,zipfile,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parent;E=R/'evidence';D=R/'delivery';D.mkdir(exist_ok=True)
A=json.loads((E/'INDEPENDENT_AUDIT_STATISTICS.json').read_text());C=json.loads((R/'COLLECTION_RECEIPT.json').read_text())
assert A['terminal']==180 and not A['global_errors'] and A['new_probability_evaluations']==0
assert A['completed']['max_active_observed']==60
assert A['all_processes_under_600'] and all(r['process_wall_seconds']<=600 for r in A['runs'])
archive=R/'COMPACT_EVIDENCE_FULL.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==C['sha256']
checked=0
for p in (E/'outcomes').glob('*.json'):
 o=json.loads(p.read_text())
 for n,v in o['output_files'].items():
  f=E/'runs'/o['identity']/n;assert f.stat().st_size==v['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==v['sha256'];checked+=1
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
X=D/'S10与改进椭球_三大算例30次_完整600秒_对比结果.xlsx'
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
 for i,g in enumerate(A['comparisons'],17):
  check(s.get(f'C{i}'),g['mean_difference']);check(s.get(f'D{i}'),g['relative_mean_difference'])
  k=i-17;check(s.get(f'I{i}'),A['case_summaries'][2*k+1]['runtime_mean_seconds']/A['case_summaries'][2*k]['runtime_mean_seconds'])
 for i,g in enumerate(A['runs'],5):
  check(raw.get(f'G{i}'),int(g['valid']))
  for col,k in [('H','cost'),('I','LSS_probability'),('J','process_wall_seconds'),('K','search_seconds')]:check(raw.get(f'{col}{i}'),g[k])
 formula_count=sum(c.find('s:f',ns) is not None for sh in sheets for c in sh.findall('.//s:c',ns))
shutil.copyfile(archive,D/'180次_完整600秒_LSS验收_紧凑证据.tar.gz')
for n in ['INDEPENDENT_AUDIT_STATISTICS.json','PROTOCOL.json','COMPLETED.json','LAUNCH.json','VALIDATION.json','EARLY_RECORD_CHECK.json','WATCHDOG_REGRESSION.json','PROXY_DOMAIN_DIAGNOSIS.json']:
 shutil.copyfile(E/n,D/n)
for n in ['DESIGN_AND_DIAGNOSIS.txt','PREVIOUS_RUN_DIAGNOSIS.json','PREVIOUS_LSS_SELECTION_GAP.json','PREPARATION_NOTES.txt']:
 shutil.copyfile(R/n,D/n)
for n,rows in [('case_summaries.csv',A['case_summaries']),('paired_comparisons.csv',A['comparisons']),('runs.csv',A['runs'])]:
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with (D/n).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows)
(D/'scripts').mkdir(exist_ok=True)
for n in ['controller.py','audit_remote.py','prepare_trial.py','collect.py','collect_remote.py','build_report.mjs','finalize_delivery.py','diagnose.py','diagnose_lss_gap.py','validate_remote.py','test_controller_guard.py']:
 shutil.copyfile(R/n,D/'scripts'/n)
# Frozen source bytes are delivered exactly as executed. Current policy is at zip root.
with zipfile.ZipFile(D/'EGS_CF_完整600秒_冻结源码.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in (R/'source').rglob('*'):
  if p.is_file():
   key='source/'+p.relative_to(R/'source').as_posix()
   P=json.loads((R/'PROTOCOL.json').read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==P['source_and_binary_pins'][key]
   z.writestr(key,p.read_bytes())
 for n in ['DESIGN_AND_DIAGNOSIS.txt','PROTOCOL.json','PREPARATION_NOTES.txt','controller.py']:z.writestr(n,(R/n).read_bytes())
 z.writestr('README_CURRENT.txt',('本包源码为实际180次测试的冻结版本。source内旧README/命令help保留原字节用于来源核对，包含上版流程说明；当前时限与流程以包根目录DESIGN_AND_DIAGNOSIS.txt和PROTOCOL.json为准。\n'
  '完整总时限600秒，最终只按LSS验收，不计算真实概率。严格进程终止保护由配套controller负责。单独调用C++时仍有协作阶段截止，但不能替代外部硬超时保护。\n'
  '新候选显式参数：--search-flow ellipsoid_costfront --ellipsoid-gamma 2.4 --ellipsoid-slice 5 --seconds 600 --local-phases none。新S10对照为--search-flow frontier_mitm。\n'
  'controller及PROTOCOL是本批冻结复现证据，已完成身份不得在原目录重跑或覆盖。新实验应新建独立根目录、注册身份与冻结协议。\n').encode())
fmt=lambda x:'空（不足30有效）' if x is None else f'{x:.8f}'
lines=['改进椭球 EGS-CF-600：三大算例30次正式结论','',
 f"本批180次全部终末，独立有效{A['valid']}/180，验收输出变体核对{A['variants_checked']}个。所有进程实测总耗时<=600秒，最高60并行。",
 '完整600秒包括进程启动、加载、初始化、搜索、原LSS全部评价、结果保存和fsync。父级等待线程记录实际退出，没有clip耗时。',
 '旧版643秒源于把600秒当搜索阶段预算，后面另做LSS复检与保存。这是旧计时实现不符合完整600秒要求，不能称为容许误差。旧记录保留。',
 '','六组正式统计：best为有效输出最小成本；avg/std只有30次全部有效时给出；std分母29。',
 '编号 | 版本 | 有效/30 | best | avg | std | 平均完整耗时(s) | 最大完整耗时(s)']
for g in A['case_summaries']:
 lines.append(f"{g['case_index']} | {g['arm']} | {g['valid']}/30 | {fmt(g['best'])} | {fmt(g['avg'])} | {fmt(g['std'])} | {fmt(g['runtime_mean_seconds'])} | {fmt(g['maximum_process_wall_seconds'])}")
lines+=['','同seed配对，候选椭球减去S10；负值为成本改善：']
for g in A['comparisons']:
 lines.append(f"{g['case_index']} | 均值方向{g['direction']} | 差值{fmt(g['mean_difference'])} | 相对差{fmt(g['relative_mean_difference'])} | Holm成本p={fmt(g['cost_p_holm3'])} | 有效率Holm p={fmt(g['validity_p_holm3'])}")
lines+=['','结果解释：']
for i,g in enumerate(A['comparisons']):
 b,c=A['case_summaries'][2*i:2*i+2]
 if not g['complete_pairs']:msg='有组不足30次有效，不能给出官方均值胜负结论，失败保持原样且不补跑。'
 elif g['direction']=='平':msg='本批平均成本相同，不据此宣称等效或全局最优。'
 elif g['cost_p_holm3']<.05:msg='候选平均成本'+('显著降低。' if g['direction']=='优' else '显著升高，不能认定改进成功。')
 else:msg='候选平均成本'+('较低' if g['direction']=='优' else '较高')+'，但配对差异未显著，不能认定等效。'
 msg+=f" 完整均时由{b['runtime_mean_seconds']:.3f}秒变为{c['runtime_mean_seconds']:.3f}秒。"
 lines.append(str(g['case_index'])+'：'+msg)
lines+=['','算法与限制：',
 '候选生成从原来的风险最小化外逼近，改为椭球风险候选域内直接最小化成本，并使用提升后的原生凸SOC和分解旋转锥预处理。初始向量只由本run原始数据和公共初始化生成。',
 '椭球风险上界只是候选生成限制，未替代最终LSS。LSS原精确/百万MC分支、阈值.99、事件sum<T和完整0—499索引不变。没有计算额外真实概率。',
 '两臂于430秒触发搜索协作截止，非抢占算子在检查点退出，因此阶段记录可有小量延迟；这不允许完整运行超过600秒。LSS截止590秒、595秒父级保护，留足保存余量。截止时未完成LSS不提供部分概率、不重试；最后完整观测仍为该向量验收依据。',
 '本次与旧版不混算。S10对照也在新完整600秒政策下重新冷启动。相同seed不意味着两条不同搜索路径对每个候选消耗完全相同的随机流位置。',
 '实际运行时间受60并行负载和操作系统调度影响，耗时比较作描述性统计。样本标准差降低不单独代表平均成本改进。',
 '成本3项同seed符号翻转/Holm3，失败有效率独立McNemar/Holm3。未显著不能解释为方法无用或等效。',
 '本方法不覆盖所有LSS可行解，不声称CCMCKP全局最优或任意经验分布下的椭球概率保证。本批不自动扩展40例。',
 f"已逐文件验证{checked}个run输出SHA和字节数，Excel六组统计、180条记录与{formula_count}个公式缓存核对通过。独立审计未重新抽样概率。",
 '旧APP_30两版所有30次原始搜索最好成本均为194.0962091132；最终LSS后S10有11次、椭球有15次选择更贵的合格解，因此其最终avg差全部来自这些选择差异，不能归咎为两版找到的最低候选不同。',
 '旧APP_50椭球原始搜索与最终输出均停在322.6330496141；旧S10原始最好候选在30次均为322.0997047676，其中13次最终LSS选择了更贵的合格解。这一例椭球确有主搜索退化，不能把std=0当优势。',
 '以上只读旧结果成本和评价trace，没有重算任何真实概率。LSS的随机复检结果按预注册规则保留，不通过重抽选优降低avg。',
 '文献、数学模型、旧版本诊断与适配局限详见DESIGN_AND_DIAGNOSIS.txt，补充的搜索/最终选择成本差见PREVIOUS_LSS_SELECTION_GAP.json。',
 '协议SHA256：'+A['protocol_sha256'],'证据包SHA256：'+C['sha256']]
(D/'本轮改进与完整600秒_正式结论.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(D/'README.txt').write_text('本目录含新完整600秒正式对比Excel、结论、冻结源码和180次紧凑证据。所有最终概率验收只用LSS。旧版超600秒的情况和原因保留在诊断文件中，不混入本批。源码zip根目录说明优先于其中保留的上版source/README历史说明。\n',encoding='utf-8')
manifest={p.relative_to(D).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in D.rglob('*') if p.is_file() and p.name!='CHECKSUMS_SHA256.json' and not p.name.endswith('.inspect.ndjson')}
(D/'CHECKSUMS_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
proof={'status':'PASS','all180_terminal':True,'independent_valid':A['valid'],'all_actual_wall_under600':True,
 'variants_checked':A['variants_checked'],'output_files_sha_verified':checked,'xlsx_numeric_and_formula_caches_verified':True,'files':manifest}
(R/'DELIVERY_LOCAL_VERIFIED.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in proof.items() if k!='files'},ensure_ascii=False))

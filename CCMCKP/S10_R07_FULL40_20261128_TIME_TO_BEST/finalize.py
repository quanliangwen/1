from pathlib import Path
import json,hashlib,statistics,zipfile,xml.etree.ElementTree as ET,shutil
R=Path(__file__).resolve().parent;D=R/'delivery';P=R.parent;O=P.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
S=read(R/'statistics.json');receipt=read(O/'COLLECTION_RECEIPT.json')
assert read(R/'TIMESTAMP_QA.json')['status']=='PASS'
verified=0
for r in S['rows']:
 for name in ['S10_search.json','RESULT.json','ORIGINAL_LSS_DECISION_TRACE.json']:
  rel='full40/runs/'+r['identity']+'/'+name
  assert sha(O/'evidence'/rel)==receipt[rel]['sha256'],rel
  verified+=1
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def cells(b):return {c.attrib['r']:c for c in ET.fromstring(b).findall('.//m:sheetData/m:row/m:c',ns)}
def val(c):return float(c.find('m:v',ns).text)
new=D/'R07_全40算例_结果汇总_含首次最优均时.xlsx'
with zipfile.ZipFile(new) as z,zipfile.ZipFile(P/'delivery/R07_全40算例_30次_结果汇总.xlsx') as old:
 assert z.testzip() is None
 summary=cells(z.read('xl/worksheets/sheet1.xml'));detail=cells(z.read('xl/worksheets/sheet2.xml'))
 for sheet,lastrow,lastcol in [('sheet1',47,'K'),('sheet2',1207,'I')]:
  oldc=cells(old.read('xl/worksheets/'+sheet+'.xml'));newc=cells(z.read('xl/worksheets/'+sheet+'.xml'))
  for key,c in oldc.items():
   row=int(''.join(x for x in key if x.isdigit()));col=''.join(x for x in key if x.isalpha())
   if 7<=row<=lastrow and len(col)==1 and col<=lastcol:
    assert ET.tostring(c.find('m:f',ns))==ET.tostring(newc[key].find('m:f',ns)) if c.find('m:f',ns) is not None else True
    if c.attrib.get('t','n')=='n' and c.find('m:v',ns) is not None:assert abs(val(c)-val(newc[key]))<1e-10
 for i,g in enumerate(S['groups'],8):
  assert val(summary[f'L{i}'])==g['best_hit_count']
  assert abs(val(summary[f'M{i}'])-g['best_hit_first_mean_seconds'])<1e-10
  assert summary[f'M{i}'].find('m:f',ns) is not None
 for i,r in enumerate(S['rows'],8):
  assert val(detail[f'J{i}'])==r['first_best_found_seconds'] and val(detail[f'K{i}'])==r['best_hit']
 for name in ['sheet1','sheet2']:
  cc=cells(z.read('xl/worksheets/'+name+'.xml'));assert all(c.attrib.get('t')!='e' for c in cc.values())
md=['# R07首次达到Best平均时间补充统计','','原Excel的“完整均时”统计每次进程从启动到结束的耗时，并未统计用户要求的首次达到Best平均时间。本版保留全部原统计，新增40例汇总L列“命中Best次数”和M列“首次达Best平均时间(s)”，以及1200次明细J列首次找到时间、K列命中标记。','','## 统计定义','','对每个算例，以本批30次最终通过原LSS验收的未四舍五入成本的最小值为Best。只取最终输出成本恰好等于该Best的运行，计算其首次找到该解时间的算术平均：','','$$H=\\{r:c_r=\\min_{1\\le j\\le30}c_j\\},\\qquad \\overline{t}_{\\mathrm{Best}}=\\frac{1}{|H|}\\sum_{r\\in H}t_r^{\\mathrm{first}}.$$','','未命中的运行不进入这个平均值，不记为0或600。若30次均命中Best，则平均全部30次的首次达到时间。Best指本批观测最好成本，未宣称已证明全局最优。','','时间使用冻结日志candidate_shortlist中输出解的found_seconds，从进程启动起计，包含此前加载、构造和认证时间。该时刻是首次通过内部CDF认证并进入候选池的时刻，最终输出另外通过原LSS验收。它不是最后一次LSS验收结束时间，也不是完整运行耗时。原生池对已接受选择直接返回，不重复覆盖首次时间；已检查1200次输出选择与日志一致，且无同成本不同选择造成时间歧义。','','所有40例Best、Avg、样本Std(ddof=1)和完整耗时保持原值。本次只重统计已有日志，未重新运行求解器或概率抽样。条件均时须结合命中次数阅读，不能单靠该均时推断整体速度优势。','','## 40例统计','','|编号|算例|T|Best|Avg|样本Std|命中Best次数|首次达Best均时(s)|完整均时(s)|','|---:|---|---:|---:|---:|---:|---:|---:|---:|']
for g in S['groups']:md.append(f'|{g["case_index"]}|{g["instance_label"]}|{g["capacity"]:g}|{g["best"]:.9f}|{g["avg"]:.9f}|{g["sample_std"]:.9f}|{g["best_hit_count"]}/30|{g["best_hit_first_mean_seconds"]:.6f}|{g["whole_mean_seconds"]:.6f}|')
base='https://github.com/quanliangwen/1/tree/bc85fd8000267cbd80eceef694e60c4345d33b6d/CCMCKP/S10_R07_FULL40_20261128_RESULTS'
md+=['','## 来源与留存','',f'[原全量实验及全部紧凑证据]({base})。原交付保持不变，本次另存补充统计。最终独立审计SHA256：`8161d76e05bd58064dbacfde7c27e9bd286e6a810835d09f9ef31c19f3bdc6da`。','',f'本次回核1200次的输出、CDF候选日志和LSS决策日志，共{verified}个文件，均与此前已核验的采集SHA256一致。']
(D/'R07_首次达到Best平均时间_说明与汇总.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
for n in ['prepare.py','update_excel.mjs','finalize.py']:shutil.copyfile(R/n,D/n)
qa={'status':'PASS','stage':'FORMAL_COMPLETE','all_files_sha_verified':True,'cases':40,'runs':1200,'raw_file_sha_matches_previous_collection':verified,'original_workbook_tables_and_formulas_preserved':True,'saved_xlsx_hit_flags_checked':1200,'saved_conditional_means_checked':40,'visual_review_changed_views_passed':True}
(D/'DELIVERY_QA.json').write_text(json.dumps(qa,indent=2),encoding='utf-8')
checks={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in D.iterdir() if p.is_file() and p.suffix!='.ndjson' and p.name!='CHECKSUMS_SHA256.json'}
(D/'CHECKSUMS_SHA256.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'DELIVERY_LOCAL_VERIFIED.json').write_text(json.dumps(qa,indent=2),encoding='utf-8')
pub=(P/'publish_results.py').read_text(encoding='utf-8').replace("FOLDER='S10_R07_FULL40_20261128_RESULTS'","FOLDER='S10_R07_FULL40_20261128_TIME_TO_BEST'").replace('Publish R07 full40 1200-run statistics, Excel workbook and final Markdown report','Add conditional first-time-to-Best averages and hit counts for R07 full40')
(R/'publish_results.py').write_text(pub,encoding='utf-8')
print(json.dumps(qa))

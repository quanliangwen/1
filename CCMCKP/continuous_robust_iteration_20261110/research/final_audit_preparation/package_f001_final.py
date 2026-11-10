"""Package the actual audited cohort only after workbook cache and visual QA."""
from pathlib import Path
import json,zipfile,hashlib,shutil
H=Path(__file__).parent;F=H/'formal/F001_I002_40x30';O=H/'outputs/F001_final';A=H/'artifact';T=A/'formal/F001_I002_40x30';stats=F/'FINAL_AUDIT_STATS.json'
if not stats.exists():raise RuntimeError('Complete real final audit required; no delivery archives created')
d=json.load(open(stats));qa=json.load(open(O/'FINAL_QA.json'));cached=json.load(open(O/'XLSX_CACHED_VALUE_CHECK.json'));xlsx=O/'F001_40cases_30runs.xlsx'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if not d['integrity_passed'] or len(d['details'])!=1200 or len(d['summary'])!=40 or not qa['visual_review_passed'] or not cached['passed'] or cached['xlsx_sha256']!=sha(xlsx) or qa['xlsx_sha256']!=sha(xlsx):raise RuntimeError('Actual complete data and verified final workbook required')
source=H/'iterations/I002_cdf_neighborhood/candidate'
if {p.name:sha(p) for p in source.glob('*.py')}!=d['source_sha256']:raise RuntimeError('Frozen source changed')
R=T/'full_records';R.mkdir(parents=True,exist_ok=True);archives=[]
def package(name,files,scope):
 files=sorted(set(files))
 missing=[str(p.relative_to(H)) for p in files if not p.is_file()]
 if missing:raise RuntimeError('Evidence files missing: '+json.dumps(missing))
 out=R/name
 if out.exists():raise RuntimeError('No archive overwrite; inspect existing evidence before retry '+name)
 with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,p.relative_to(H).as_posix())
 with zipfile.ZipFile(out) as z:
  if z.testzip() is not None:raise RuntimeError('ZIP CRC failure')
 if out.stat().st_size>=95*1024**2:raise RuntimeError('Archive requires further splitting before GitHub upload '+name)
 archives.append(dict(file=out.relative_to(T).as_posix(),bytes=out.stat().st_size,sha256=sha(out),scope=scope,zip_CRC_passed=True,files=[dict(path=p.relative_to(H).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files]))
guide=F/'SOURCE_README.md'
existing_guide=guide.read_text(encoding='utf8') if guide.exists() else None
guide_text='''# F001：实际执行的冻结I002源码与正式证据

正式优化器为iterations/I002_cdf_neighborhood/candidate中的16个Python文件；登记和最终审计包含逐项SHA256。reference下是21个原LSS源码，校验后仅用兼容别名加载。主搜索不读取真实分布、历史解或外部验收缓存。

实际搜索环境：Python3.13.9，numpy2.4.0，scipy1.17.1，python-flint0.8.0；原LSS环境：Python3.8.10，numpy1.24.4，scipy1.10.1。原benchmark数据不重复打包，按RAW_REFERENCE.json和LSS_DATA_REFERENCE.json逐项SHA恢复原始输入；不能用其他样本或新生成分布替代。

单次搜索入口：candidate/run.py --instance 原算例目录 --capacity T --seed 登记搜索种子 --seconds 600 --risk-method cdf_lns --phase-seconds 180 --out 新输出路径。40例参数见CASES.json，30个新种子见formal/F001_I002_40x30/REGISTRATION.json。程序拒绝覆盖证据；复现需新工作目录并恢复vendor313依赖。原始driver中的服务器路径需按实际原数据位置配置，路径调整不改变求解器算法。

主队列run_f001_stages.py严格先完成1200次搜索再调用validate_f001.py。全部原样本的sum<T整数下界≥0.99，再按冻结候选成本顺序运行原real_P_test：1000万次，seed832273，sum≤T，点估计≥0.985；首次通过即停。固定身份原调用可在优化器外复用，不能当1200次独立MC种子估计。不得只保留成功运行计算Avg；每例30次协议有效才给Avg和总体Std(ddof=0)。

40个case_XX.zip包含各例全部登记种子的搜索输出/日志/元数据/终止记录、外部原LSS验收记录及实际引用的调用凭证。NATIVE_ATTEMPT_LOGS.zip单独保存本正式阶段新增的调用尝试日志（含可能失败）。最终审计、Excel、校验文件和归档逐项SHA在本目录。工程/开发结果不替代本正式队列。
'''
if existing_guide is not None:
 if existing_guide!=guide_text:raise RuntimeError('Existing guide differs; no overwrite')
else:guide.write_text(guide_text,encoding='utf8')
files=list(source.glob('*.py'))+[H/'reference'/r['path'] for r in json.load(open(H/'REFERENCE_SHA256.json'))['files']]
files+=[H/n for n in ['run_f001_search.py','run_f001_stages.py','validate_f001.py','native_lss_eval.py','reference_loader.py','audit_f001_progress.py','audit_f001_final.py','independent_raw_recount.py','check_independent_raw_recount.py','INDEPENDENT_RAW_RECOUNT_MATH_CHECK.json','CASES.json','BASELINE_S10.json','RAW_REFERENCE.json','REFERENCE_SHA256.json','LSS_DATA_REFERENCE.json']]
files+=[H/n for n in ['build_f001_workbook.mjs','create_f001_excel.ps1','check_f001_xlsx.py']]+[O/n for n in ['AUTHORING_CHECK.json','XLSX_CACHED_VALUE_CHECK.json','FINAL_QA.json']]
files+=[F/n for n in ['REGISTRATION.json','LAUNCH.json','CACHE_BEFORE_VALIDATION.json','CACHE_LOGS_BEFORE_VALIDATION.json','FINAL_AUDIT_STATS.json','SOURCE_README.md']]
P=H/'research/final_audit_preflight';proof=json.load(open(P/'FIRST3_APP_EXHAUSTIVE_JOINT_AUDIT.json'));check=json.load(open(P/'FIRST3_APP_INTEGER_RECHECK.json'))
if not check['passed'] or check['proof_sha256']!=sha(P/'FIRST3_APP_EXHAUSTIVE_JOINT_AUDIT.json'):raise RuntimeError('First3 cost-line proof identity differs')
files+=[P/n for n in ['FIRST3_APP_EXHAUSTIVE_JOINT_AUDIT.json','FIRST3_APP_INTEGER_RECHECK.json','SMALL_FORMAL_COMPATIBILITY.json','README.md']]
files+=[H/n for n in ['audit_first3_small_global.py','check_first3_small_integer.py','diagnose_small_formal_compatibility.py']]
keys={c['witness_LSS_key'] for c in proof['cases']}
keys.update(r['LSS_key'] for c in proof['cases'] for r in c['cheaper_choice_records'] if 'LSS_key' in r)
files+=[H/'lss_cache'/(k+'.json') for k in sorted(keys)]
P16=H/'research/small16_joint_global';p16=json.load(open(P16/'RESULT.json'));c16=json.load(open(P16/'INDEPENDENT_CPP_RECHECK.json'))
if not c16['passed'] or not c16['all16_global_fixed_joint_optimal'] or c16['result_sha256']!=sha(P16/'RESULT.json'):raise RuntimeError('Complete small16 proof identity differs')
files+=[P16/n for n in ['RESULT.json','INDEPENDENT_CPP_RECHECK.json','REGISTRATION.json','CPP_MATH_CHECK.json','cpp_full.log','cpp_full.in','cpp_math.in','choices.jsonl.gz','README.md']]
files+=[H/n for n in ['small_exact_integer_core.py','SMALL_EXACT_INTEGER_CORE_MATH_CHECK.json','audit_small16_global.py','small_exact_checker.cpp','cpp_audit_codec.py','recheck_small16_cpp.py']]
files+=[H/'lss_cache'/(k+'.json') for k in sorted(p16['native_receipt_sha256'])]
package('F001_SOURCE_AND_AUDIT.zip',files,'actual frozen formal source16+original LSS21, registered protocol, independent verifier and actual final audit')
for i in range(1,41):
 rows=[r for r in d['details'] if r['index']==i]
 if len(rows)!=30:raise RuntimeError('Expected all30 registered attempts')
 files=[];keys=set()
 for r in rows:
  base=F/'search'/f'cdf_lns_{i:02d}_seed{r["seed"]}.json.gz';terminal=Path(str(base)+'.terminal.json');post=F/'validation'/(base.name+'.post.json')
  if not terminal.exists() or not post.exists():raise RuntimeError('Registered outcome missing')
  files+=[terminal,post]+[p for p in [base,Path(str(base)+'.run.json'),Path(str(base)+'.log')] if p.exists()]
  keys.update(x['key'] for x in json.load(open(post)).get('tested',[]))
 files+=[H/'lss_cache'/(key+'.json') for key in sorted(keys)]
 package(f'case_{i:02d}_30runs.zip',files,'all30 registered search and native postselection records for case'+str(i)+'; failures retained')
before={r['name'] for r in json.load(open(F/'CACHE_LOGS_BEFORE_VALIDATION.json'))['files']};logs=[p for p in (H/'lss_cache').glob('*.log') if p.name not in before and p.stat().st_mtime<=d['native_finish_time']]
package('NATIVE_ATTEMPT_LOGS.zip',logs,'physical new invocation logs in F001 window, includes unsuccessful attempts')
for p in [stats,xlsx,O/'FINAL_QA.json',O/'XLSX_CACHED_VALUE_CHECK.json',guide]:shutil.copy2(p,T/p.name)
manifest=dict(scope='actual complete registered40x30 cohort; qualification outcomes preserved without success-only averages',registered_attempts=1200,protocol_valid=d['protocol_valid'],joint_accepted=d['joint_accepted'],xlsx_sha256=sha(xlsx),archives=archives,storage='ordinary GitHub Git files; each archive verified below95MiB; final upload and independent remote byte/SHA verification still required')
with (T/'FINAL_RECORD_MANIFEST.json').open('x') as f:json.dump(manifest,f,indent=2)
print(json.dumps(dict(packaged=True,archives=len(archives),bytes=sum(r['bytes'] for r in archives),remote_upload_and_verification_pending=True)))

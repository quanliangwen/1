"""Freeze whole6/8 audited development evidence; preserve all original attempts."""
from pathlib import Path
import argparse,json,zipfile,shutil
from isolated_original_lss import sha
from register_completed_pool_prefix import PROFILES
H=Path(__file__).resolve().parent
def pack(profile):
 cfg=PROFILES[profile];D=H/cfg['study'];S=H/cfg['cohort'];number='005' if profile=='P016' else '006';out=D/('D'+number+'_COMPLETE_COHORT_EVIDENCE.zip');manifest=D/'EVIDENCE_MANIFEST.json'
 if out.exists() or manifest.exists():raise RuntimeError('No complete cohort evidence overwrite')
 reg=json.load(open(D/'REGISTRATION.json'));a=json.load(open(D/'INDEPENDENT_FINAL_AUDIT.json'));post=json.load(open(D/'POSTPROCESS_TERMINAL.json'));summary=json.load(open(D/'DEVELOPMENT_COMPARISON.json'));r=json.load(open(D/'RESULT.json'));cat=json.load(open(D/'CATALOGUE.json'));cc=json.load(open(D/'CATALOGUE_CHECK.json'))
 if not a['passed'] or not post['passed'] or a['result_sha256']!=sha(D/'RESULT.json') or a['registration_sha256']!=sha(D/'REGISTRATION.json') or len(a['pools'])!=cfg['required'] or summary['all_original_attempts_qualified']!=cfg['required']:raise RuntimeError('Whole actual independent cohort audit/comparison must pass')
 note=D/'RESULTS_NOTES.md';text='# D'+number+'：完整开发对照与费用\n\n'+cfg['scope']+'。全部预登记成员、原样本复核、原LSS完整成本前缀均已独立审计，保持严格原样本整数下界≥0.99与原完整LSS1000万次/832273/sum≤T点估计≥0.985，无新尾部硬筛。\n\n'
 if profile=='P016':
  text+='|版本|开发种子数|Best|Avg|Std.P|Avg−自身Best|\n|---|---:|---:|---:|---:|---:|\n'
  for label,v in summary['summaries'].items():text+=f"|{label}|{v['runs']}|{v['Best']:.9f}|{v['Avg']:.9f}|{v['Std_population']:.9f}|{v['Avg_minus_own_Best']:.9f}|\n"
 else:text+='每个算例每个方法仅一个新种子，只列独立配对成本，不给每例Avg/Std或跨算例平均成本。\n\n'
 text+='\n|算例|种子|父版成本|新版成本|父版−新版|\n|---:|---:|---:|---:|---:|\n'
 for v in summary['paired_rows']:text+=f"|{v['index']}|{v['seed']}|{v['parent_cost']:.9f}|{v['new_cost']:.9f}|{v['parent_minus_new']:.9f}|\n"
 text+=f"\n本组新增物理原LSS尝试{a['physical_new_MC_attempts']}次，原生秒合计{a['physical_new_original_MC_seconds']:.9f}；其中批内超出最终必需前缀的推测额外秒{a['speculative_extra_MC_seconds']:.9f}全部计费。逻辑复用秒按各池完整前缀分别报告，重复执行的旧队列调用不抵扣。固定LSS种子复用同身份凭证，不是独立概率重复试验。\n\n仅证明各冻结池的最低联合合格成员，不是全局最优、30次Avg或历史Best已追平。正式F001的40×30及其Excel保持原样；下一版正式1200必须单独冻结登记。持续目标active。\n"
 files=[p for p in D.rglob('*') if p.is_file() and p.suffix!='.zip' and p not in [manifest,note]]+[H/n for n in reg['source_sha256']]+[H/n for n in reg['input_sha256']]+[H/v['path'] for v in cat.values()]+[H/v['alias']['path'] for v in cc['aliases']]
 files.extend(p for p in S.rglob('*') if p.is_file() and p.suffix!='.zip')
 for info in json.load(open(S/'REGISTRATION.json'))['sources'].values():files.extend((H/info['candidate']).parent.joinpath('vendor313').rglob('*.py'))
 files.extend(H/'reference'/v['path'] for v in json.load(open(H/'REFERENCE_SHA256.json'))['files'])
 files.extend(H/n for n in ['pack_completed_prefix_final.py','register_completed_pool_prefix.py','launch_completed_pool_prefix.py','make_completed_prefix_remote_receipt.py','postprocess_completed_pool_prefix.py','launch_completed_prefix_postprocess.py','summarize_completed_prefix.py','audit_d'+number+'_prefix.py','snapshot_d'+number+'_isolation.py','independent_raw_recount.py','INDEPENDENT_RAW_RECOUNT_MATH_CHECK.json'])
 files=sorted(set(files))
 for p in files:
  if not p.is_file():raise RuntimeError('Missing actual evidence before ZIP creation '+str(p))
 for n,d in {**reg['source_sha256'],**reg['input_sha256']}.items():
  if sha(H/n)!=d:raise RuntimeError('Frozen source/input changed')
 for v in list(cat.values())+[x['alias'] for x in cc['aliases']]:
  if sha(H/v['path'])!=v['sha256']:raise RuntimeError('Actual completed receipt changed')
 with note.open('x',encoding='utf8') as f:f.write(text)
 files.append(note)
 with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,p.relative_to(H).as_posix())
 with zipfile.ZipFile(out) as z:
  if z.testzip() is not None:raise RuntimeError('Complete cohort ZIP CRC failed')
 m=dict(file=out.name,bytes=out.stat().st_size,sha256=sha(out),zip_CRC_passed=True,scope=cfg['scope']+'; actual whole-cohort independently audited original native/raw/source/lineage/ledger/isolation evidence; no30/globaloptimality claim',files=[dict(path=p.relative_to(H).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files])
 with manifest.open('x') as f:json.dump(m,f,indent=2)
 T=H/'artifact'/cfg['study'];T.mkdir(parents=True,exist_ok=True)
 for p in [out,manifest,note]+list(D.glob('*.json')):shutil.copy2(p,T/p.name)
 print(json.dumps({k:v for k,v in m.items() if k!='files'}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cohort',choices=sorted(PROFILES),required=True);pack(p.parse_args().cohort)

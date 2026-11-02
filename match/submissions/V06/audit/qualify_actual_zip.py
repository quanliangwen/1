"""Qualify actual immutable V06 ZIP; imports and installation dry-runs only."""
from pathlib import Path
import base64,json,subprocess,sys
root=Path(__file__).resolve().parent.parent
manifest=json.loads((root/'audit/PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
archive=root/'team615_red_v06.zip'
remote=r'''
from pathlib import Path
import base64,datetime,hashlib,json,os,shutil,subprocess,zipfile
R=Path('/home/junhao/quan/parallel_test_solver/match');H=R/'solver_study/framework_screen_20261016/best87_independent_20261025'
C=H/'PJ01_submission_team615_v06_20261029';assert not C.exists(),'Do not overwrite prior qualification'
C.mkdir();audit=C/'audit';audit.mkdir()
manifest=__MANIFEST__
archive=C/'team615_red_v06.zip';archive.write_bytes(base64.b64decode(__ARCHIVE_B64__))
assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['submission_zip_sha256']
repo=H/'F32_official_sdk_20261028/source_repo';W=C/'runtime_workspace'
shutil.copytree(repo/'src',W/'src',ignore=shutil.ignore_patterns('__pycache__','solutions'))
solutions=W/'src/swarm_rescue/solutions';solutions.mkdir(parents=True)
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None and set(z.namelist())==set(manifest['payload_files_sha256'])
 for n in z.namelist():
  assert '/' not in n and '\\' not in n and n not in ['.','..']
  data=z.read(n);assert hashlib.sha256(data).hexdigest()==manifest['payload_files_sha256'][n]
  p=W/'req.txt' if n=='req.txt' else solutions/n;p.write_bytes(data)
(C/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
revision=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
probe=r"""
from pathlib import Path
import sys,json,hashlib,traceback,importlib.metadata as md
W=Path(sys.argv[1]);site=Path(sys.argv[2]);base=Path(sys.argv[3]);receipt=Path(sys.argv[4]);C=W.parent
manifest=json.loads((C/'PACKAGE_MANIFEST.json').read_text());archive=C/'team615_red_v06.zip'
sys.path.insert(0,str(site));sys.path.insert(0,str(W/'src'))
if str(base) not in sys.path:sys.path.append(str(base))
out={'scope':'Actual ZIP extracted into fresh source workspace. Numeric operations, SDK and controller factory imports only; no drone instantiation, simulation or scoring. Some dependencies reused from existing isolated environments.','official_container_verified':False,'python':sys.version,'executable':sys.executable,'submission_zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'payload_files_sha256':manifest['payload_files_sha256']}
try:
 for n,sha in manifest['payload_files_sha256'].items():
  p=W/'req.txt' if n=='req.txt' else W/'src/swarm_rescue/solutions'/n
  assert hashlib.sha256(p.read_bytes()).hexdigest()==sha,n
 out['all_payload_hashes_match']=True
 import numpy as np,pandas as pd,cv2,numpy.random.mtrand as mt
 out['distribution_versions']={n:md.version(n) for n in ['numpy','pandas','opencv-contrib-python']}
 out['critical_module_paths']={n:m.__file__ for n,m in [('numpy',np),('pandas',pd),('cv2',cv2),('numpy.random.mtrand',mt)]}
 assert Path(np.__file__).resolve().is_relative_to(site.resolve())
 assert Path(mt.__file__).resolve().is_relative_to(site.resolve())
 assert np.isfinite(np.random.RandomState(615).normal(size=64)).all()
 assert pd.DataFrame({'a':[1.,2.,3.]})['a'].sum()==6.
 assert cv2.filter2D(np.ones((8,8),np.float32),-1,np.ones((3,3),np.float32)).shape==(8,8)
 out['numeric_random_pandas_cv_operations']='PASS'
 from swarm_rescue.launcher import Launcher
 from swarm_rescue.simulation.reporting.stats_computation import StatsComputation
 import swarm_rescue
 assert Path(swarm_rescue.__file__).resolve().is_relative_to((W/'src').resolve())
 out['sdk_module_path']=swarm_rescue.__file__;out['sdk_launcher_and_stats_import']='PASS'
 from swarm_rescue.simulation.reporting.team_info import TeamInfo
 info=TeamInfo();assert type(info.team_number) is int and info.team_number==615
 out['team_number']=info.team_number
 from swarm_rescue.solutions.my_drone_eval import MyDroneEval,drone_class_for_mode
 assert drone_class_for_mode('place') is MyDroneEval
 own=[]
 for name,module in list(sys.modules.items()):
  if name.startswith('swarm_rescue.solutions') and getattr(module,'__file__',None):
   p=Path(module.__file__);assert p.resolve().is_relative_to((W/'src/swarm_rescue/solutions').resolve()),name
   assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['payload_files_sha256'][p.name]
   own.append({'module':name,'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 out.update(status='PASS',controller_factory_import='PASS',own_payload_imports=own)
except BaseException:out.update(status='FAIL',traceback=traceback.format_exc())
receipt.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'status':out['status'],'versions':out.get('distribution_versions'),'error':out.get('traceback')}))
sys.exit(0 if out['status']=='PASS' else 1)
"""
(C/'probe_actual_zip.py').write_text(probe)
env=os.environ.copy();env.pop('PYTHONPATH',None);env.update(PATH=str(R/'system/usr/bin')+':'+env.get('PATH',''),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',MPLBACKEND='Agg',LIBGL_ALWAYS_SOFTWARE='1',ALSOFT_DRIVERS='null',LP_NUM_THREADS='1')
oldenv=H/'submission_alns_v9_20261025T1532Z/dependency_venv';newenv=H/'COMPATIBILITY_V05_BLUE_20261029/numpy2_probe_venv'
profiles=[('numpy1',R/'.venv/bin/python',oldenv/'lib/python3.11/site-packages',oldenv/'bin/python'),('numpy2',newenv/'bin/python',newenv/'lib/python3.11/site-packages',newenv/'bin/python')]
runs={}
for tag,python,site,pip_python in profiles:
 receipt=audit/(tag+'_ABI_RECEIPT.json')
 with (audit/(tag+'_imports.log')).open('w') as log:
  p=subprocess.run([str(R/'system/usr/bin/xvfb-run'),'-a','-s','-screen 0 640x480x24',str(python),str(C/'probe_actual_zip.py'),str(W),str(site),str(R/'.venv/lib/python3.11/site-packages'),str(receipt)],cwd=W,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
 run=json.loads(receipt.read_text()) if receipt.exists() else {'status':'FAIL','error':'No ABI receipt','returncode':p.returncode}
 plan=audit/(tag+'_install_plan.json')
 with (audit/(tag+'_install_plan.log')).open('w') as log:
  planned=subprocess.run([str(pip_python),'-m','pip','install','--dry-run','--no-index','--disable-pip-version-check','--report',str(plan),'-r',str(W/'req.txt')],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60)
 planned_packages=[{'name':x['metadata']['name'],'version':x['metadata']['version']} for x in json.loads(plan.read_text()).get('install',[])] if plan.exists() else None
 run['installation_dry_run']={'status':'PASS' if planned.returncode==0 and planned_packages==[] else 'FAIL','returncode':planned.returncode,'planned_installations':planned_packages,'command_scope':'Read-only --dry-run --no-index using extracted ZIP req.txt; not an official installer execution.'}
 if p.returncode!=0 or run['installation_dry_run']['status']!='PASS':run['status']='FAIL'
 run['sdk_source_revision']=revision;runs[tag]=run
 receipt.write_text(json.dumps(run,indent=2)+'\n')
# Old SDK checker validates archive contents under its legacy filename convention.
alias=audit/'team615_preliminary.zip';shutil.copyfile(archive,alias);assert hashlib.sha256(alias.read_bytes()).hexdigest()==manifest['submission_zip_sha256']
with (audit/'OFFICIAL_STATIC_CHECK.log').open('w') as log:
 static=subprocess.run([str(R/'.venv/bin/python'),str(repo/'scripts/check_submission.py'),str(alias)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60)
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if all(r.get('status')=='PASS' for r in runs.values()) and static.returncode==0 else 'FAIL','dependency_profile':'sdk-inherit-v06','submission_zip_sha256':manifest['submission_zip_sha256'],'payload_files_sha256':manifest['payload_files_sha256'],'team_number':615,'sdk_source_revision':revision,'official_container_verified':False,'algorithm_simulation_run':False,'abi_runs':runs,'official_static_check':{'status':'PASS' if static.returncode==0 else 'FAIL','returncode':static.returncode,'legacy_filename_alias':str(alias),'alias_sha256':hashlib.sha256(alias.read_bytes()).hexdigest(),'final_filename_policy':'Final team615_red_v06.zip follows user contest convention; SDK static checker receives byte-identical team615_preliminary.zip solely for its old filename rule.'},'environment_scope':'Existing isolated numeric dependencies reused; NumPy2 environment was independently installed for dependency diagnosis. Other SDK dependencies reused read-only from fixed base environment. No original environment installations/uninstallations, no official container execution.'}
(audit/'RELEASE_ABI_RECEIPT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
'''
remote=remote.replace('__MANIFEST__',repr(manifest)).replace('__ARCHIVE_B64__',repr(base64.b64encode(archive.read_bytes()).decode('ascii')))
p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','junhao@10.112.162.60','/home/junhao/quan/parallel_test_solver/match/.venv/bin/python','-'],input=remote.encode('utf-8'),capture_output=True,timeout=300)
(root/'audit/qualification_ssh.log').write_bytes(p.stderr)
if p.returncode:
 (root/'audit/qualification_failed_stdout.log').write_bytes(p.stdout);print(p.stderr.decode('utf-8',errors='replace'));sys.exit(p.returncode)
r=json.loads(p.stdout)
(root/'audit/RELEASE_ABI_RECEIPT.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':r['status'],'zip_sha256':r['submission_zip_sha256'],'official_static_check':r['official_static_check'],'runs':{k:{'status':v['status'],'versions':v.get('distribution_versions'),'dry_run':v['installation_dry_run'],'error':v.get('traceback')} for k,v in r['abi_runs'].items()}},ensure_ascii=False))
sys.exit(0 if r['status']=='PASS' else 1)

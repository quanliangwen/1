from pathlib import Path
import subprocess,sys,json
R=Path(__file__).resolve().parent
for name in ['structure','tail_model_diagnostic']:
 p=subprocess.run([sys.executable,'-X','utf8','E:/codex/S10_EGS_OA_20261123/remote.py',str(R/(name+'_remote.py'))],capture_output=True,text=True,encoding='utf-8',check=True)
 data=json.loads(p.stdout);(R/(name.upper()+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('READ_ONLY_DIAGNOSTICS_SAVED')

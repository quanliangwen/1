import pathlib,time,subprocess,json
H=pathlib.Path(__file__).resolve().parent
while not (H/'FINAL_SUMMARY_FINISHED').exists():time.sleep(5)
steps=[('/home/junhao/miniconda3/bin/python','summarize_returned_outputs.py'),('python3','summarize_user_validation.py'),('python3','make_user_plot.py'),('python3','write_user_report.py'),('python3','pack_final.py')]
results=[]
for python,script in steps:
 started=time.time()
 with open(H/(script+'.final.log'),'x') as log:p=subprocess.run([python,'-u',str(H/script)],stdout=log,stderr=subprocess.STDOUT)
 r=dict(script=script,exit=p.returncode,wall=time.time()-started);results.append(r);(H/'USER_EXPORTS_STATUS.json').write_text(json.dumps(results,indent=2));print(json.dumps(r),flush=True)
 if p.returncode:raise RuntimeError('User probability/export stage failed: '+script)
(H/'USER_EXPORTS_FINISHED').write_text('All 1200-output probability summaries, explicitly separate timing deviations, plots, report and raw archives generated. Verify before uploading.')

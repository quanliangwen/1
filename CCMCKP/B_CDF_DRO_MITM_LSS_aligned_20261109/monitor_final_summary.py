import pathlib,time,subprocess,json
H=pathlib.Path(__file__).resolve().parent
while not (H/'formal30_lss/DISPATCH_RESULTS.json').exists() or not (H/'formal30_lss_validation/FINISHED').exists():
 if (H/'FORMAL_LAUNCH_BLOCKED.json').exists():raise RuntimeError('Frozen development gate rejected launch')
 time.sleep(5)
for script,python in [('summarize_empirical.py','/home/junhao/miniconda3/bin/python'),('summarize_lss.py','python3')]:
 with open(H/(script+'.log'),'x') as log:p=subprocess.run([python,'-u',str(H/script)],stdout=log,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError('Final summary failed: '+script)
(H/'FINAL_SUMMARY_FINISHED').write_text('Formal records and LSS records summarized; inspect FINAL_SUMMARY.json before declaring success.')

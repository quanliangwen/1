"""Replay only to recover score recording; controller and fixture unchanged.
The original recording failure is retained. This cannot rescue qualification.
"""
from pathlib import Path
import json,runpy,sys
import numpy as np
F=Path(__file__).resolve().parent;script=F/'check_sdk_inner.py'
try:runpy.run_path(str(script),run_name='__main__')
except TypeError as error:
 if 'not JSON serializable'not in str(error):raise
 tb=error.__traceback__;payload=None
 while tb is not None:
  if Path(tb.tb_frame.f_code.co_filename)==script:
   item=tb.tb_frame.f_locals.get('out')
   if isinstance(item,dict)and item.get('status')=='AUTHOR_SDK_COMPLETED':payload=item
  tb=tb.tb_next
 if payload is None:raise
 def convert(item):
  if isinstance(item,np.generic):return item.item()
  if isinstance(item,np.ndarray):return item.tolist()
  raise TypeError(type(item).__name__)
 destination=F/(sys.argv[1]+'_SDK_FIRST.json');assert not destination.exists()
 payload['replayed_for_recording_only']=True;payload['original_recording_error']=str(error);payload['qualification_rescued']=False
 destination.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=convert)+'\n')
 print(json.dumps(dict(status='RECOVERED_POST_CONTROL_RECORDING_ONLY',steps=payload['physics_steps'],placed=payload['placed'],scores=payload['scores']),default=convert))

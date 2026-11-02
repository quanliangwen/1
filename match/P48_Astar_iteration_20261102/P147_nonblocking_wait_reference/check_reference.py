from pathlib import Path
import hashlib
import json
import time
import numpy as np
from wait_connectivity import certify_waiting_sites

F=Path(__file__).resolve().parent
assert not(F/'RESULT_FIRST.json').exists()
cases=[]
began=time.perf_counter()
def check(name,grid,protected,parking,radius,status,budget=100000):
    before=hashlib.sha256(grid.tobytes()).hexdigest()
    result=certify_waiting_sites(grid,protected,parking,radius,budget)
    assert result['status']==status,(name,result)
    assert hashlib.sha256(grid.tobytes()).hexdigest()==before
    cases.append(dict(name=name,result=result,input_unchanged=True))

room=np.ones((15,15),bool)
endpoints=[(7,1),(7,13)]
check('open_room_off_route_wait',room,endpoints,[(3,7)],1.1,'CERTIFIED_TERMINAL_GRAPH_ONLY')
narrow=np.zeros((15,15),bool)
narrow[7,1:14]=True
narrow[3:8,4:7]=True
check('do_not_park_on_narrow_through_lane',narrow,endpoints,[(7,9)],1.1,'REJECT_PARK_SEVERS_PROTECTED_CONNECTION')
check('side_bay_keeps_task_route',narrow,endpoints,[(4,5)],1.1,'CERTIFIED_TERMINAL_GRAPH_ONLY')
loop=np.zeros((13,15),bool)
loop[3,1:14]=True
loop[9,1:14]=True
loop[3:10,1]=True
loop[3:10,13]=True
ports=[(6,1),(6,13)]
check('upper_park_alone_passes',loop,ports,[(3,7)],1.1,'CERTIFIED_TERMINAL_GRAPH_ONLY')
check('lower_park_alone_passes',loop,ports,[(9,7)],1.1,'CERTIFIED_TERMINAL_GRAPH_ONLY')
check('independent_safe_parks_jointly_cut_both_routes',loop,ports,[(3,7),(9,7)],1.1,'REJECT_PARK_SEVERS_PROTECTED_CONNECTION')
check('do_not_invent_free_parking',narrow,endpoints,[(1,1)],1.1,'REJECT_PARK_NOT_KNOWN_FREE')
check('task_endpoint_is_not_a_parking_site',room,endpoints,[(7,2)],1.1,'REJECT_PARK_COVERS_TASK_ENDPOINT')
separate=narrow.copy()
separate[1,1]=True
check('unreachable_park_rejected',separate,endpoints,[(1,1)],1.1,'REJECT_PARK_NOT_REACHABLE_FROM_TASK_COMPONENT')
corner=np.zeros((4,4),bool)
corner[1,1]=corner[2,2]=True
check('no_corner_cut_to_fake_task_connection',corner,[(1,1),(2,2)],[],0.,'ABSTAIN_BASE_TASK_COMPONENT_DISCONNECTED')
check('finite_budget_does_not_fake_a_certificate',room,endpoints,[(3,7)],1.1,'ABSTAIN_EXPANSION_BUDGET',3)
check('too_close_waiting_sites_rejected',room,endpoints,[(3,7),(3,8)],1.1,'REJECT_PARK_SEPARATION')
out=dict(status='PASS_12_GEOMETRY_REFERENCE_CHECKS',cases=cases,seconds=time.perf_counter()-began,
         source_sha256=hashlib.sha256((F/'wait_connectivity.py').read_bytes()).hexdigest(),
         sdk_frames=0,native_rounds=0,controller_modified=False,
         decisive_result='Two independently acceptable parks can jointly block both routes. Do not integrate independent per-agent fixed ring slots.',
         limits=['Authored dimensionless graphs, not actual SDK clearances or maps.',
                 'No proof that terminal parking caused P146 inventory loss.',
                 'No distributed assignment or physical travel protocol tested.'])
(F/'RESULT_FIRST.json').write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(status=out['status'],seconds=out['seconds'],checks=len(cases),decisive_result=out['decisive_result'])))

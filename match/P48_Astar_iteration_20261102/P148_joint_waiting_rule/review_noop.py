"""Read the completed authored run once; no new simulator execution."""
from pathlib import Path
import hashlib,json
F=Path(__file__).resolve().parent
out=F/'NOOP_DIAGNOSIS_FIRST.json'
assert not out.exists()
p=F/'JOINT_WAITING_V2_FIRST.json'
j=json.loads(p.read_text())
ready={e['owner']:e['step']for e in j['waiting_events']if e['kind']=='MAP_EXCHANGE_COMPLETED'}
records=[]
for e in j['gate_events']:
    b=e['after']or e['before'];owner=b['owner'];step=b['step']
    if owner not in ready or step<ready[owner]or b['inventory']!=0:continue
    fleet={int(i):v for i,v in b['fleet'].items()if v['position']is not None and 0<=v['age']<=120}
    fleet[owner]={'inventory':0,'age':0}
    empty=sorted(i for i,v in fleet.items()if v['inventory']==0)
    records.append(dict(owner=owner,step=step,all_five_received_states=set(fleet)==set(range(5)),
                        empty_ids=empty,selected_min_empty=min(empty),
                        owner_passes_election=owner==min(empty),rally_distance=b['rally_distance']))
assert records and all(not r['owner_passes_election']for r in records)
assert not any(e['kind']in['BUILD','ROUTE_ACCEPTED','ARRIVED']for e in j['waiting_events'])
r=json.loads((F/'RESULT_V2_FIRST.json').read_text())
result=dict(status='CONFIRMED_ELIGIBILITY_ELECTION_MISMATCH_NO_OP',source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            actual_exchange_ready_steps=ready,received_state_evidence=records,
            actual_score=r['candidate'],rows_identical_to_parent=r['raw_rows_identical'],
            conclusion='All observed post-readiness empty planning calls fail the min-empty election. Missing states and ring geometry were not reached; do not blame them.',
            limits=['Readiness is an earlier actual event, not proof every later call is outside SORTIE/survey.',
                    'No actual waiting action occurred, so parking benefit, congestion repair and transit safety remain untested.'],
            next='Independent eligibility-aware waiting leader candidate; preserve failed run and all original gates. No native/five for P148.')
out.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(status=result['status'],witnesses=len(records),actual_ready=ready)))

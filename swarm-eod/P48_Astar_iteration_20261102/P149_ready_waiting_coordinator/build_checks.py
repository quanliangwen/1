from pathlib import Path
import ast
F=Path(__file__).resolve().parent
P=F.parent/'P148_joint_waiting_rule'
text=(P/'check_contracts_v2.py').read_text()
text=text[:text.index('# Counterexample is explicitly pre-SDK')]
text=text.replace("F/'waiting_core_v2.py'","F/'waiting_core.py'").replace("F/'joint_waiting_v2.py'","F/'joint_waiting.py'")
text=text.replace("self.last_peer_step={0:90};", "self.last_peer_step={0:90};")
text=text.replace("x.last_peer_step={0:90};x._sortie_docked_step=50;", "x.last_peer_step={0:90};x._waiting_ready_reports={0:(100,True)};x._sortie_docked_step=50;")
text=text.replace("assert not(F/'CONTRACT_V2_FIRST.json').exists()","assert not(F/'CONTRACT_FIRST.json').exists()")
text+='''
# Specific observed P148 dead coordinator counterexample; no physics or truth.
waiting_states={0:(100,np.array([0.,0.]),0),1:(100,np.array([16.,0.]),0),2:(100,np.array([32.,0.]),0),3:(100,np.array([180.,180.]),1)}
check('old_min_empty_is_not_automatically_eligible',core.waiting_leader(waiting_states,{2})==2)
check('lowest_actually_ready_empty_is_elected',core.waiting_leader(waiting_states,{1,2})==1)
check('carrying_peer_cannot_be_elected_even_if_bad_readiness',core.waiting_leader(waiting_states,{3})is None)
check('empty_readiness_set_abstains',core.waiting_leader(waiting_states,set())is None)
new_plan,new_audit=core.propose_waiting_plan(m,100,2,4,waiting_states,anchor,protected,time.perf_counter()+2.,eligible_idle={2})
check('ready_peer_can_build_when_lower_empty_unready',new_plan is not None and set(new_plan['goals'])=={2},audit=new_audit)
check('same_readiness_domain_accepts_plan',core.validate_plan(new_plan,100,2,4,waiting_states,anchor,2,100,eligible_idle={2})is not None)
check('new_lower_ready_leader_invalidates_old_proposal',core.validate_plan(new_plan,100,2,4,waiting_states,anchor,2,100,eligible_idle={1,2})is None)
check('expired_readiness_does_not_validate_leader',core.validate_plan(new_plan,100,2,4,waiting_states,anchor,2,100,eligible_idle=set())is None)
x=ready_fixture();x._waiting_ready_reports={0:(51,True),2:(100,True)}
check('stale_report_and_loaded_report_not_eligible',x._waiting_eligible(100,states)=={1})
x._waiting_ready_reports={0:(101,True)}
check('future_readiness_not_eligible',x._waiting_eligible(100,states)=={1})
x._waiting_ready_reports={0:(100,False)}
check('explicit_not_ready_excludes_lower_empty',x._waiting_eligible(100,states)=={1})
x._waiting_ready_reports={0:(100,True)}
check('fresh_ready_report_and_self_both_eligible',x._waiting_eligible(100,states)=={0,1})
x.survey_plan=(100,0,1,np.array([80.,0.]),180)
check('live_survey_self_excluded_from_new_election',x._waiting_eligible(100,states)=={0})
out=dict(status='PASS_READY_ELECTION_AND_ORIGINAL_WAITING_SCOPE',checks=checks,
         source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in[F/'waiting_core.py',F/'joint_waiting.py']},
         scope='Explicit helper/protocol fixtures only, no SDK or physics qualification.',sdk_frames=0,native_rounds=0)
(F/'CONTRACT_FIRST.json').write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\\n').encode())
print(json.dumps(dict(status=out['status'],checks=len(checks))))
'''
ast.parse(text)
(F/'check_contracts.py').write_bytes(text.encode())

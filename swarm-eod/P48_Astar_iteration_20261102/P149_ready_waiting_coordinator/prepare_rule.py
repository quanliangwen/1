"""One new functional change after P148 failed: readiness-aware election."""
from pathlib import Path
import ast,hashlib,json
F=Path(__file__).resolve().parent
P=F.parent/'P148_joint_waiting_rule'
assert not(F/'waiting_core.py').exists()
core=(P/'waiting_core_v2.py').read_text()
core=core.replace('def waiting_leader(states):\n    return min((k for k,v in states.items()if v[2]==0),default=None)',
'''def waiting_leader(states,eligible_idle=None):
    return min((k for k,v in states.items()if v[2]==0 and(eligible_idle is None or k in eligible_idle)),default=None)''')
core=core.replace('sender=None,sent=None):','sender=None,sent=None,eligible_idle=None):')
core=core.replace('leader!=waiting_leader(states)','leader!=waiting_leader(states,eligible_idle)')
assert core.count('waiting_leader(states,eligible_idle)')==2
mix=(P/'joint_waiting_v2.py').read_text()
anchor='    def define_message_for_all(self):'
assert mix.count(anchor)==1
mix=mix.replace(anchor,'''    def _waiting_eligible(self,step,states):
        ready={peer for peer,(stamp,flag)in self._waiting_ready_reports.items()
               if flag and type(stamp)is int and 0<=step-stamp<=48
               and peer in states and states[peer][2]==0}
        own=int(self.identifier or 0)
        ready.discard(own)
        if self._waiting_can_wait(step):ready.add(own)
        return ready

'''+anchor)
a=mix.index('        for _,msg in self.communicator.received_messages:')
b=mix.index('    def _plan_route(',a)
mix=mix[:a]+'''        incoming=[]
        for _,msg in self.communicator.received_messages:
            if not isinstance(msg,dict)or msg.get('kind')!='greedy-map-v1'or'map'not in msg:continue
            sender,sent=msg.get('id'),msg.get('step')
            if type(sender)is not int or self.last_peer_step.get(sender)!=sent:continue
            readiness=msg.get('waiting_ready_v1')
            if(isinstance(readiness,(tuple,list))and len(readiness)==2 and type(readiness[0])is int
                    and type(readiness[1])is bool and readiness[0]==sent and 0<=step-sent<=48):
                old_ready=self._waiting_ready_reports.get(sender,(-1,False))
                if sent>old_ready[0]:self._waiting_ready_reports[sender]=(sent,readiness[1])
            incoming.append((sender,sent,msg.get('waiting_plan_v1')))
        eligible=self._waiting_eligible(step,states)
        # Process readiness before proposals; list order cannot choose leader.
        for sender,sent,plan in incoming:
            target=validate_plan(plan,step,int(self.identifier or 0),self.team_size,states,self.rally,sender,sent,eligible_idle=eligible)
            if target is None:continue
            old=self._waiting_plan
            if old is None or(plan['epoch'], -plan['leader'])>(old['epoch'],-old['leader']):
                self._waiting_plan=plan
                self._waiting_emit('RECEIVED',step,leader=sender,epoch=plan['epoch'])

'''+mix[b:]
mix=mix.replace('        if own==waiting_leader(states)and','        eligible=self._waiting_eligible(step,states)\n        if own==waiting_leader(states,eligible)and')
mix=mix.replace("            ready={peer for peer,(sent,flag)in self._waiting_ready_reports.items()if flag and 0<=step-sent<=48}\n            ready.add(own)","            ready=eligible")
mix=mix.replace("self._waiting_emit('BUILD',step,audit=audit)","self._waiting_emit('BUILD',step,audit=audit,eligible=sorted(eligible),min_empty=waiting_leader(states))")
mix=mix.replace('self.team_size,states,self.rally)\n        if target', 'self.team_size,states,self.rally,eligible_idle=eligible)\n        if target')
mix=mix.replace('        goal=validate_plan(self._waiting_plan,step,int(self.identifier or 0),self.team_size,self._waiting_states(step),self.rally)',
'''        states=self._waiting_states(step)
        goal=validate_plan(self._waiting_plan,step,int(self.identifier or 0),self.team_size,states,self.rally,eligible_idle=self._waiting_eligible(step,states))''')
assert mix.count('eligible_idle=')==4
for name,text in [('waiting_core.py',core),('joint_waiting.py',mix)]:
    ast.parse(text);(F/name).write_bytes(text.encode())
(F/'wait_connectivity.py').write_bytes((P.parent/'P147_nonblocking_wait_reference/wait_connectivity.py').read_bytes())
manifest=dict(status='SOURCE_READY_BEFORE_NEW_FIXTURE_OR_SDK',functional_change='Elect among fresh actually-ready empty peers; same domain used for build/message/route validation.',
              predecessor='P148 V2 failed actual activation gate; preserved without native or rescue.',
              unchanged=['Original P48 A* mapping/layout/motion','P148 scope/proposal geometry/budgets/lease/state ages','Original benchmark seed/case/gates'],
              limits=['Readiness views can differ; no leader consensus or simultaneous collision safety guarantee. Uncertain proposals abstain.',
                      'A later coordinator change can invalidate an old proposal; original route fallback remains.'],
              sources={n:hashlib.sha256((F/n).read_bytes()).hexdigest()for n in['waiting_core.py','joint_waiting.py','wait_connectivity.py']},native_rounds=0)
(F/'DESIGN_FIRST.json').write_bytes((json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(status=manifest['status'],files=len(manifest['sources']))))

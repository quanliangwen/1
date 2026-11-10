"""AST identity of numerical scheduling/error decisions versus completed D005."""
from pathlib import Path
import ast,json,hashlib,time
H=Path(__file__).resolve().parent;D=H/'research/F002_native_audit_preflight';D.mkdir(exist_ok=True);out=D/'CONTROL_FLOW_IDENTITY.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if out.exists():raise RuntimeError('No control-flow identity preflight overwrite')
old=H/'run_d005_pair_prefix.py';new=H/'run_f002_native.py';reg=json.load(open(H/'research/D005_I016_pair_prefix/REGISTRATION.json'))
if sha(old)!=reg['source_sha256'][old.name]:raise RuntimeError('Completed predecessor source changed')
trees=[ast.parse(p.read_text()) for p in [old,new]]
class RemovePrint(ast.NodeTransformer):
 def visit_Expr(self,node):
  if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='print':return None
  return self.generic_visit(node)
checks=[]
for name,predicate in [('hash_guards',lambda n:isinstance(n,ast.FunctionDef) and n.name=='identities'),('whole_batch_error_control',lambda n:isinstance(n,ast.Try)),('complete_pool_loading',lambda n:isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and [v.id for v in n.target.elts]==['name','info'])]:
 nodes=[next(n for n in t.body if predicate(n)) for t in trees];normalized=[ast.dump(RemovePrint().visit(n),include_attributes=False) for n in nodes]
 if normalized[0]!=normalized[1]:raise RuntimeError('Formal controller changed completed decision flow '+name)
 checks.append(name)
script=new.read_text()
if "reg['search_attempts'] != 1200" not in script or 'excluded_search_attempts=len' not in script:raise RuntimeError('Formal trial accounting guard missing')
r=dict(passed=True,time=time.time(),scope=__doc__+'; static comparison after removal of log print only, not a new formal runtime/MC experiment',checked_blocks=checks,source_sha256=sha(new),predecessor_sha256=sha(old),same_batch_engine=True,full1200_native_runtime_exercised=False,new_MC_calls=0)
with out.open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))

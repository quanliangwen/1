from pathlib import Path
import ast,base64
R=Path(__file__).resolve().parent
c=(R/'controller.py').read_text()
code='''from pathlib import Path
import ast,subprocess,time,sys,threading,os,signal,json
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/egs_costfront_600s_20261124';assert Path.cwd()==B
tree=ast.parse(SOURCE)
node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='watch_exit')
module=ast.Module(body=[node],type_ignores=[])
scope={'P':{'process_wall_watchdog_seconds':.15},'time':time,'os':os,'signal':signal,'threading':threading,'subprocess':subprocess}
exec(compile(module,'frozen_controller_guard','exec'),scope)
start=time.monotonic();p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(5)'],cwd=str(H),start_new_session=True,
 stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
item={'process':p,'started':start};scope['watch_exit'](item)
elapsed=item['exited_monotonic']-start
assert p.returncode<0 and elapsed<1 and item['termination_reason']=='guarded_total_wall_timeout'
data={'status':'PASS','guard_seconds':.15,'observed_exit_seconds':elapsed,'rc':p.returncode,
 'tested_exact_controller_watch_exit_AST':True,'not_a_registered_algorithm_run':True}
(H/'WATCHDOG_REGRESSION.json').write_text(json.dumps(data,indent=2));print(json.dumps(data))
'''.replace('SOURCE',repr(c))
(R/'test_controller_guard_remote.py').write_text(code,encoding='utf-8')

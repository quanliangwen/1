import pathlib,sys,importlib,hashlib,json
H=pathlib.Path(__file__).resolve().parent
R=H/'reference';manifest=json.load(open(H/'REFERENCE_SHA256.json'))
for r in manifest['files']:
 if hashlib.sha256((R/r['path']).read_bytes()).hexdigest()!=r['sha256']:raise RuntimeError('Original LSS source changed')
sys.path[:0]=[str(R),str(R/'src')]
# The uploaded files use these old import names; only module aliases are restored.
sys.modules['src.benchmark.benchmark_lab']=importlib.import_module('src.benchmark.benchmark_LAB')
sys.modules['src.benchmark.benchmark_huawei']=importlib.import_module('src.benchmark.benchmark_APP')
real_module=importlib.import_module('src.functions.func_realP_statistical')
estimator=importlib.import_module('src.functions.func_cl_estimator')
Factor=importlib.import_module('src.utils.factor').Factor

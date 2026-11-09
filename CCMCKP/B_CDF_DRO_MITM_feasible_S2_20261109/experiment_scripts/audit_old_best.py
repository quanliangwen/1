import os,sys,pathlib,json,gzip
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
H=pathlib.Path(__file__).parent;sys.path[:0]=[str(H/'vendor313'),str(H/'source_v2')]
from instance import load_instance
from exact_oracle import ExactOracle
B=pathlib.Path('/home/junhao/quan/parallel_test_solver/CCMKCP/work/codex_v50_dro_ablation_20261016/results');cases=json.load(open('/home/quanliangwen/work/cdf_stability_20261109/frozen/original_experiment/cases.json'));rows=[]
for c in cases:
 i=c['index'];records=[json.load(gzip.open(p,'rt')) for p in sorted(B.glob(f'B_CDF_DRO_MITM_{i:02d}_r*.json.gz'))];best=min(records,key=lambda d:d['selected']['cost'])['selected'];o=ExactOracle(load_instance('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/'+c['instance']),c['tmax'])
 for bins in [4096,16384,65536,262144,1048576]:
  cert=o.certify(best['selection'],bins,True)
  if cert['accepted'] or cert['infeasible']:break
 rows.append(dict(**c,old_best=best['cost'],old_observation=best['probability'],full_sample_certificate=cert));print(i,cert['accepted'],cert['infeasible'],flush=True)
(H/'OLD_BEST_FULL_SAMPLE_AUDIT.json').write_text(json.dumps(rows,indent=2))

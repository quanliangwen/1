from pathlib import Path
import json,hashlib,subprocess,os,time,pickle
B=Path('/home/junhao/quan/parallel_test_solver/CCMKCP');H=B/'work/d02_transport_cert_20261126';assert Path.cwd()==B and not (H/'formal').exists()
previous=json.loads((H/'VALIDATION_FAILURE_0.json').read_text());checks=previous['checks'];assert len(checks)==4 and all(q['rc']==0 for q in checks)
F=H/'fixtures/LAB_3_4_500_';assert not F.exists();F.mkdir();(F/'node_to_factor.pkl').write_bytes(pickle.dumps({g:list(range(4*g,4*g+4)) for g in range(3)},protocol=4))
(F/'cost.txt').write_text('\n'.join(str(c+g*.01) for g in range(3) for c in [4,3,2,1])+'\n')
for g in range(3):
 for k,(a,b) in enumerate([('.03','.1'),('.05','.2'),('.1','.4'),('.2','.6')]):(F/('%d_sample.txt'%(4*g+k))).write_text('\n'.join([a]*250+[b]*250)+'\n')
out=H/'integration60/mechanism_exercised';assert not out.exists();start=time.monotonic();env=dict(os.environ,CCMCKP_LAUNCH_MONOTONIC=str(start),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',BLIS_NUM_THREADS='1')
p=subprocess.run([str(H/'build/ccmckp_s10'),'--instance',str(F),'--capacity','.75','--seed','1000002','--seconds','60','--out',str(out),'--search-flow','block_winf_transport'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,timeout=60)
(H/'transport_mechanism_integration.log').write_bytes(p.stdout);row={'name':'transport_mechanism_active_integration','rc':p.returncode,'whole_seconds':time.monotonic()-start,'tail':p.stdout.decode(errors='replace')[-1000:]};assert p.returncode==0,row
raw=json.loads((out/'S10_search.json').read_text());x=json.loads((out/'RESULT.json').read_text());st=raw['DRO_transport_statistics']
assert x['original_LSS_confidence']>=.99 and x['lss_sample_index_max']==499 and not x['real_probability_reporting']
assert row['whole_seconds']<60 and st['queries']>0 and st['native_witnesses_added']>0 and st['excluded']>0 and st['excluded']==len(raw['DRO_transport_prunes'])
assert st['maximum_bank_size']<=128 and not st['feasible_certificate_reuse'] and st['model_unchanged_from_D01']
row.update(cost=x['cost'],LSS=x['original_LSS_confidence'],transport=st);checks.append(row)
unchanged=['evaluation.cpp','evaluation.hpp','rng.cpp','rng.hpp','report.cpp','report.hpp','model.cpp','model.hpp','mip.cpp','mip.hpp','fft.hpp','partition.hpp','block_mitm.hpp','block_bounds.hpp','block_schedule.hpp','convolution_tree.hpp','winf_product.hpp']
for name in unchanged:assert (H/'source'/name).read_bytes()==(B/'work/d01_winf_product_20261126/source'/name).read_bytes(),name
v={'status':'PASS','checks':checks,'unchanged_bytes':unchanged,'preparation_note':'First common tiny fixture produced no native infeasible witnesses; all math and three pipeline runs passed. Added separate heterogeneous small fixture to exercise actual inferred exclusions; did not repeat passed math or controls.','reused_D01_math_checks_by_identical_source':632,'no_extra_native_probability_diagnostic':True,'binary_sha256':hashlib.sha256((H/'build/ccmckp_s10').read_bytes()).hexdigest(),'source_sha256':{p.relative_to(H/'source').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (H/'source').rglob('*') if p.is_file()}}
(H/'VALIDATION.json').write_text(json.dumps(v,indent=2));print(json.dumps({'status':'PASS','mechanism':row,'source_unchanged':unchanged,'binary_sha256':v['binary_sha256']}))

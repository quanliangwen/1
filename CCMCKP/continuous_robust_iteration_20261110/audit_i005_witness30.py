"""External audit of an already independently generated/validated witness.
The witness does not enter branch search and no new true-MC call is made.
"""
from pathlib import Path
from fractions import Fraction
import sys,json,hashlib
H=Path(__file__).parent;I=H/'iterations/I005_exact_cdf_bound';sys.path[:0]=[str(I/'candidate'),str(I/'vendor313')]
from instance import load_instance
from exact_oracle import ExactOracle
proof=json.load(open(I/'case30/probe_s10_minus_1e6.json'));audit=json.load(open(I/'case30/probe_s10_minus_1e6.json.audit.json'))
if not audit['passed'] or not audit['raw_cost_line_excluded']:raise RuntimeError('First audit full lower cost exclusion')
post=json.load(open(H/'iterations/I002_cdf_neighborhood/pilot_validation/cdf_lns_30_seed970201.json.gz.post.json'));s=post['selected'];bench=Path('/home/junhao/quan/parallel_test_solver/CCMKCP/benchmark/APP_10_10_500_');inst=load_instance(bench);selection=inst.validate_selection(s['selection']);cert=s['certificate']
if cert['method']!='exact_integer_upward_grid_count':raise RuntimeError('Unexpected certificate method')
n,d=ExactOracle(inst,37,'.99').count(selection,cert['bins'],True)
if n!=int(cert['lower_numerator']) or d!=int(cert['denominator']) or 100*n<99*d:raise RuntimeError('Witness raw99 recount failed')
cost=[Fraction(x) for x in (bench/'cost.txt').read_text().split()];actual=sum((cost[j] for j in selection),Fraction(0));lower=Fraction(proof['cost_limit'])
key=s['LSS_key'];native=json.load(open(H/'lss_cache'/(key+'.json')));identity=dict(instance=inst.name,capacity=37.,selection=list(selection),seed=832273,draws=10000000,event='sum<=T')
if hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()!=key or any(native[k]!=v for k,v in identity.items()) or native['real_probability']<.985:raise RuntimeError('Wrong fixed original LSS witness call')
reference=json.load(open(H/'REFERENCE_SHA256.json'))
if native['source_sha256']!=reference['files']:raise RuntimeError('Native LSS source identity mismatch')
for r in reference['files']:
 if hashlib.sha256((H/'reference'/r['path']).read_bytes()).hexdigest()!=r['sha256']:raise RuntimeError('Original LSS source altered')
for name,sha in native['distribution_sha256'].items():
 if hashlib.sha256((bench/name).read_bytes()).hexdigest()!=sha:raise RuntimeError('True-data identity altered')
gap=actual-lower
result=dict(passed=True,instance=inst.name,capacity=37,selection=list(selection),witness_cost_exact=str(actual),witness_cost_float=float(actual),excluded_cost_line_exact=str(lower),joint_optimum_interval='(excluded cost line, witness exact cost]',interval_width_exact=str(gap),interval_width=float(gap),raw_certificate_recounted=True,raw_lower=float(Fraction(n,d)),native_original_LSS_point=native['real_probability'],native_key=key,native_record_sha256=hashlib.sha256((H/'lss_cache'/(key+'.json')).read_bytes()).hexdigest(),native_reused_by_identical_identity=True,new_MC_calls=0,source_of_witness='existing independent I002 development run; used in this external audit only, never passed to branch search or F001 optimizer',exclusion_audit_sha256=hashlib.sha256((I/'case30/probe_s10_minus_1e6.json.audit.json').read_bytes()).hexdigest(),cost_note='proof and witness use exact source decimal costs; printed floating cost agrees up to machine rounding')
(I/'case30/WITNESS_AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

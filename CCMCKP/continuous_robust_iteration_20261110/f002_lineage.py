"""Reuse the independently exercised I016 pool/stage audit without MC or search."""
from pathlib import Path
from fractions import Fraction as F
import ast,hashlib
H=Path(__file__).resolve().parent;file=H/'audit_i016_priority_breadth.py'
EXPECTED='db94795439327338024a3bc1ddfbe00457c8be4b07a884ebb89344484211e703'
if hashlib.sha256(file.read_bytes()).hexdigest()!=EXPECTED:raise RuntimeError('Previously audited lineage source differs')
tree=ast.parse(file.read_text());pool=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='pool_check');loop=next(n for n in tree.body if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and [t.id for t in n.target.elts]==['label','index','seed']);start=next(i for i,n in enumerate(loop.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ext' for t in n.targets));assert loop.body[-1].value.func.attr=='append'
poolcode=compile(ast.Module(body=[pool],type_ignores=[]),str(file),'exec');stagecode=compile(ast.Module(body=loop.body[start:-1],type_ignores=[]),str(file),'exec')

def check(data,prices,groups):
 env=dict(F=F,prices=prices,groups=groups,unique={},current_instance=data['instance'],current_capacity=data['capacity'],data=data,label='I016_pair_cover')
 exec(poolcode,env);ext=data['extension']
 if ext['phase_status']!='completed' or ext['method']!='cdf_pair_cover' or ext['phase_budget']!=180 or ext['extension_seconds']>180 or ext['final_pool']!=len(data['candidate_shortlist']) or not ext['all_certified_points_retained']:raise RuntimeError('Frozen I016 shared phase identity differs')
 if len(groups)<=5:
  rows=data['candidate_shortlist']
  if rows!=sorted(rows,key=lambda r:(r['cost'],r['selection'])) or len({tuple(r['selection']) for r in rows})!=len(rows):raise RuntimeError('Small pool not unique canonical cost order')
  for r in rows:
   q=r['selection'];c=r['certificate']
   if len(q)!=len(groups) or len(set(q))!=len(q) or any(j not in groups[g] for g,j in enumerate(q)) or c['selection']!=q or c['method'] not in ['outward_interval_integer_pair_count','exact_integer_upward_grid_count'] or c['strict_event']!='sum<T' or not c['all_original_samples'] or 100*int(c['lower_numerator'])<99*int(c['denominator']) or abs(r['cost']-float(sum((prices[j] for j in q),F(0))))>1e-9:raise RuntimeError('Small original interval/grid99 canonical cost differs')
   env['unique'][(data['instance'],data['capacity'],tuple(q),c.get('bins'),c['lower_numerator'],c['denominator'])]=c
  if ext['base_pool']!=len(data['candidate_shortlist']) or 'pair_cover' in ext or 'precision_closure' in ext:raise RuntimeError('Skipped small-case extension changed members')
  return env['unique'],dict(branch='unchanged small-case base solver',raw_members=len(data['candidate_shortlist']))
 env['pool_check'](data['candidate_shortlist'])
 if not data['candidate_shortlist']:
  if ext['base_pool']!=0:raise RuntimeError('Empty final pool removed base members')
  return env['unique'],dict(branch='empty own pool, qualification pending/failed',raw_members=0)
 exec(stagecode,env)
 return env['unique'],dict(branch='previously exercised complete ownCDF/pair/block/precision branch',raw_members=len(data['candidate_shortlist']))

from pathlib import Path
import hashlib,json,shutil
F=Path(__file__).resolve().parent;F.mkdir(exist_ok=True)
P=F.parent/'P154_corner_cluster_five';S=P/'versions/P154_CORNER_ASTAR/source'
D=F/'candidate_project/src/swarm_rescue/solutions';assert not D.exists();D.mkdir(parents=True)
for p in S.iterdir():
 if p.is_file():shutil.copyfile(p,D/p.name)
shutil.copyfile(S/'req.txt',F/'candidate_project/req.txt')
c=(S/'corner_cluster.py').read_text()
start=c.index('def _corners(');end=c.index('\ndef corner_cluster_layout',start)
c=c[:start]+(F/'inner_corners.py').read_text()+c[end:]
c=c.replace('    corners=_corners(memory,allowed,xx,yy,radius)', '''    state=getattr(memory,'corner_policy_state',{})
    initial_total=state.get('initial_total')
    if not isinstance(initial_total,int)or initial_total<=0:return finish('no_initial_inventory_certificate')
    target_total=int(math.ceil(MAJORITY_RATIO*initial_total))
    confirmed=[np.asarray(p,float)for p in state.get('confirmed',[])]
    reserved=[np.asarray(p,float)for p in state.get('reserved',{}).values()]
    committed=confirmed+reserved
    audit.update(initial_total=initial_total,target_total=target_total,confirmed_count=len(confirmed),reserved_count=len(reserved))
    corners=_corners(memory,allowed,xx,yy,radius)''')
c=c.replace("    wanted=max(2,int(math.ceil(MAJORITY_RATIO*total)))", "    wanted=target_total # fixed initial-total quota; candidate-specific confirmed credit below")
c=c.replace("            base_cluster=sum(", "            committed_cluster=sum(np.linalg.norm(p-anchor)<=CORNER_RADIUS_RATIO*radius+1e-8 for p in committed)\n            wanted=max(0,target_total-int(committed_cluster))\n            audit['required_suffix']=wanted\n            if wanted>total:continue\n            base_cluster=sum(")
c=c.replace("            if base_cluster>=wanted:continue", "            # Even a previously accepted layout must survive the same current coverage/route checks.\n            if wanted==0:continue")
c=c.replace('            if wanted==0:continue','            # Zero suffix deficit still retains the reserved clustered objective.')
# Evaluate confirmed+reserved+future union, not residual-only ratio.
c=c.replace('            ratio=score/baseline', '''            full_reference=float(np.asarray(values)[_mask(xx,yy,committed+baseline_points,radius)].sum())
            full_value=float(np.asarray(values)[_mask(xx,yy,committed+points,radius)].sum())
            ratio=full_value/max(1e-12,full_reference)''')
c=c.replace('            if score+1e-5<COVERAGE_RATIO*baseline or clustered<wanted or clustered<=base_cluster:continue', '            if ratio+1e-8<COVERAGE_RATIO or clustered<wanted:continue')
c=c.replace("    memory.corner_cluster_anchor=(sx,sy,float(anchor[0]),float(anchor[1]))", "    memory.corner_cluster_anchor=(sx,sy,float(anchor[0]),float(anchor[1]))")
c=c.replace("coverage_ratio=ratio,clustered=clustered,baseline_clustered=int(before),step=", "coverage_ratio=ratio,clustered=clustered,fixed_target=target_total,baseline_clustered=int(before),step=")
# A legal previous complete suffix is examined before constructing a new one.
mark="            order=sorted(counts,key="
at=c.index(mark)
carry='''            old=state.get('previous_suffix',{})
            if old and all(k in old and len(old[k])==len(original[k])for k in original):
                carried={k:[np.asarray(p,float).copy()for p in old[k]]for k in original}
                carried_points=[p for ps in carried.values()for p in ps]
                carried_cluster=sum(np.linalg.norm(p-anchor)<=CORNER_RADIUS_RATIO*radius+1e-8 for p in carried_points)
                full_reference=float(np.asarray(values)[_mask(xx,yy,committed+baseline_points,radius)].sum())
                full_value=float(np.asarray(values)[_mask(xx,yy,committed+carried_points,radius)].sum())
                carried_ratio=full_value/max(1e-12,full_reference)
                good=carried_cluster>=wanted and carried_ratio+1e-8>=COVERAGE_RATIO
                good=good and all(allowed[pm.world_to_cell(p)]for p in carried_points)
                good=good and all(np.linalg.norm(p-q)>=separation-1e-8 for i,p in enumerate(carried_points)for q in carried_points[i+1:])
                if good:
                    lengths={k:route_length(k,carried[k])for k in counts}
                    good=all(math.isfinite(lengths[k])and lengths[k]<=owner_travel_budget(travel_budget,k)+1e-6 for k in counts)
                if good:
                    best=(carried,sx,sy,anchor,carried_ratio,int(carried_cluster),base_cluster)
                    best_rank=(int(carried_cluster),full_value,-sum(lengths.values()),sx,sy)
                    audit['carry_previous_suffix']=True
                    break
'''
c=c[:at]+carry+c[at:]
(D/'corner_cluster.py').write_text(c,encoding='utf-8')
shutil.copyfile(F/'fixed_corner_mission.py',D/'corner_mission.py')
candidate={str(p.relative_to(F/'candidate_project')).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()for p in (F/'candidate_project').rglob('*')if p.is_file()}
diff=[p.name for p in D.iterdir()if p.is_file()and p.read_bytes()!=(S/p.name).read_bytes()]
assert sorted(diff)==['corner_cluster.py','corner_mission.py']
(F/'CANDIDATE_MANIFEST_FIRST.json').write_text(json.dumps(dict(parent='P154_CORNER_ASTAR',changed=diff,candidate_files=candidate,SDK_changed=False,dependencies_changed=False,Gurobi=False),indent=2)+'\n')
print(json.dumps(dict(changed=diff,files=len(candidate))))

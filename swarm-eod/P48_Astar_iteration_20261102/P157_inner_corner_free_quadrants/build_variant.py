from pathlib import Path
import hashlib,json,shutil
F=Path(__file__).resolve().parent;P=F.parent/'P156_fixed_quota_inner_corner';F.mkdir(exist_ok=True)
S=P/'candidate_project';D=F/'candidate_project';assert not D.exists();shutil.copytree(S,D,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
p=D/'src/swarm_rescue/solutions/corner_cluster.py';s=p.read_text();start=s.index('        ids=np.flatnonzero(');end=s.index('    return out',start)
s=s[:start]+'''        # The wall pivot is not itself a standable corner site. Keep each
        # locally free quadrant, instead of committing to the nearest side.
        near=allowed & ((xx-pivot[0])**2+(yy-pivot[1])**2<=(4*memory.CELL)**2)
        anchors=[]
        if lock is not None:
            anchors=[np.asarray(lock[2:4],float)]
        else:
            for sx,sy in[(-1,-1),(-1,1),(1,-1),(1,1)]:
                ids=np.flatnonzero(near &(sx*(xx-pivot[0])>=memory.CELL)&(sy*(yy-pivot[1])>=memory.CELL))
                if not len(ids):continue
                flat=min(ids,key=lambda n:(float((xx.ravel()[n]-pivot[0])**2+(yy.ravel()[n]-pivot[1])**2),int(n)))
                anchors.append(np.array([xx.ravel()[flat],yy.ravel()[flat]]))
        for anchor in anchors:
            region=allowed & ((xx-anchor[0])**2+(yy-anchor[1])**2<=(CORNER_RADIUS_RATIO*radius)**2)
            count,labels=cv2.connectedComponents(region.astype(np.uint8),connectivity=8)
            cell=memory.world_to_cell(anchor);component=int(labels[cell])
            if component==0:continue
            region &= labels==component
            if any(np.linalg.norm(anchor-old[2])<memory.CELL for old in out):continue
            out.append((float(pivot[0]),float(pivot[1]),anchor,region))
''' +s[end:]
# Up to four locally distinct standable quadrants, same cooperative .40s cap.
s=s.replace('for _,sx,sy,anchor,region in ranked[:2]:','for _,sx,sy,anchor,region in ranked[:4]:')
p.write_text(s,encoding='utf-8')
manifest=json.loads((P/'CANDIDATE_MANIFEST_V2.json').read_text());manifest.update(parent='P156_V2',changed_from_parent=['corner_cluster.py'])
manifest['candidate_files']={str(p.relative_to(D)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()for p in D.rglob('*')if p.is_file()}
(F/'CANDIDATE_MANIFEST_V2.json').write_text(json.dumps(manifest,indent=2)+'\n')
for n in ['BASE_WORKSPACE.json','check_sdk_inner.py']:shutil.copyfile(P/n,F/n)
prep=(P/'prepare_sdk_workspace.py').read_text().replace('workspace_P156','workspace_P157').replace("'P156':dict(","'P157':dict(")
(F/'prepare_sdk_workspace.py').write_text(prep,encoding='utf-8')
test=(P/'check_numeric_v3.py').read_text().replace('NUMERIC_V3_FIXTURE_FIXED_FIRST.json','NUMERIC_FIRST.json')
(F/'check_numeric.py').write_text(test,encoding='utf-8')
runner=(P/'run_small.py').read_text().replace('P156_fixed_quota_inner_corner_20261102','P157_inner_corner_free_quadrants_20261102')
runner=runner.replace("for arm in ['P48_ASTAR','P156']:","for arm in ['P157']:")
runner=runner.replace("a=read(F/'P48_ASTAR_SDK_FIRST.json');b=read(F/'P156_SDK_FIRST.json');", "a=read(F.parent/'P156_fixed_quota_inner_corner/P48_ASTAR_SDK_FIRST.json');b=read(F/'P157_SDK_FIRST.json');")
(F/'run_small.py').write_text(runner,encoding='utf-8')
pre=json.loads((P/'PREDECLARATION_FIRST.json').read_text());pre.update(SDK_arms=['P157'],baseline_not_repeated=True,baseline_path=str(P/'P48_ASTAR_SDK_FIRST.json'),baseline_sha256=hashlib.sha256((P/'P48_ASTAR_SDK_FIRST.json').read_bytes()).hexdigest(),SDK_script_sha256=hashlib.sha256((F/'check_sdk_inner.py').read_bytes()).hexdigest(),candidate_manifest_sha256=hashlib.sha256((F/'CANDIDATE_MANIFEST_V2.json').read_bytes()).hexdigest(),scope='Only measured inner-corner free-quadrant anchors changed; fixed6/90%/radii/physical rules identical to failed P156')
(F/'PREDECLARATION_FIRST.json').write_text(json.dumps(pre,indent=2)+'\n')
print(json.dumps(dict(changed=['corner_cluster.py'],SDK_script_identical=(F/'check_sdk_inner.py').read_bytes()==(P/'check_sdk_inner.py').read_bytes(),new_native_rounds=0)))

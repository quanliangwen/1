from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
import ast,difflib,json,shutil

ROOT=Path(__file__).resolve().parent
BASE=Path(r'E:\codex\team615_red_v16_first30_release_20261121\delivery\team615_red_v16.zip')
assert sha256(BASE.read_bytes()).hexdigest()=='e98990cfd9269ab521621bc97d7c9e81e21fa83bb83dafbfefb3943480dd6791'
shutil.copyfile(BASE,ROOT/'baseline_snapshot.zip')
with ZipFile(BASE) as z:
    original={n:z.read(n) for n in z.namelist()};infos=z.infolist();z.extractall(ROOT/'candidate')
assert len(original)==56
raw=original['line_regularization.py'];ending='\r\n' if b'\r\n' in raw else '\n'
text=raw.decode().replace('\r\n','\n')
needle='    points = np.column_stack((cols, rows)).astype(float)\n'
assert text.count(needle)==1
text=text.replace(needle,needle+'''    # nonzero() is row-major: each image row occupies a contiguous point range.
    row_offsets = np.empty(hits.shape[0] + 1, dtype=np.intp)
    row_offsets[0] = 0
    np.cumsum(np.bincount(rows, minlength=hits.shape[0]), out=row_offsets[1:])
''')
before='''        subset=np.flatnonzero((points[:,0]>=min(x1,x2)-margin) &
            (points[:,0]<=max(x1,x2)+margin) &
            (points[:,1]>=min(y1,y2)-margin) &
            (points[:,1]<=max(y1,y2)+margin))'''
after='''        lower_y, upper_y = min(y1,y2)-margin, max(y1,y2)+margin
        if math.isfinite(lower_y) and math.isfinite(upper_y):
            first_row = min(hits.shape[0], max(0, math.floor(lower_y)))
            last_row = min(hits.shape[0], max(0, math.ceil(upper_y) + 1))
            row_start, row_stop = row_offsets[first_row], row_offsets[last_row]
        else:
            # Preserve the original comparison semantics for nonfinite options.
            row_start, row_stop = 0, len(points)
        local_points = points[row_start:row_stop]
        subset=row_start+np.flatnonzero((local_points[:,0]>=min(x1,x2)-margin) &
            (local_points[:,0]<=max(x1,x2)+margin) &
            (local_points[:,1]>=min(y1,y2)-margin) &
            (local_points[:,1]<=max(y1,y2)+margin))'''
assert text.count(before)==1
text=text.replace(before,after)
new=text.replace('\n',ending).encode();(ROOT/'candidate/line_regularization.py').write_bytes(new)
with ZipFile(ROOT/'candidate_snapshot.zip','w') as z:
    hashes={}
    for info in infos:
        data=(ROOT/'candidate'/info.filename).read_bytes();z.writestr(info,data);hashes[info.filename]=sha256(data).hexdigest()
        if info.filename.endswith('.py'):compile(data,info.filename,'exec')
assert [n for n in original if original[n]!=(ROOT/'candidate'/n).read_bytes()]==['line_regularization.py']
before_ast=ast.parse(raw);after_ast=ast.parse(new)
def funcs(tree):return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a,b=funcs(before_ast),funcs(after_ast)
assert [name for name in a if a[name]!=b[name]]==['regularized_walls']
assert b'MIN_WALL_MARGIN = 1.5' in original['deadline_submission.py']
patch=''.join(difflib.unified_diff(raw.decode().replace('\r\n','\n').splitlines(keepends=True),text.splitlines(keepends=True),fromfile='V16/line_regularization.py',tofile='candidate/line_regularization.py'))
(ROOT/'CHANGES.patch').write_text(patch,encoding='utf8',newline='\n')
build=dict(status='PASS',baseline='formal V16',baseline_zip_sha256=sha256(BASE.read_bytes()).hexdigest(),
    candidate_zip_sha256=sha256((ROOT/'candidate_snapshot.zip').read_bytes()).hexdigest(),
    baseline_files={n:sha256(data).hexdigest() for n,data in original.items()},candidate_files=hashes,
    changed_files=['line_regularization.py'],changed_functions=['regularized_walls'],unchanged_files=55,
    wall_margin_seconds=1.5,previous_optimizations_included=False,full_matches=0,release_status='RESEARCH_ONLY')
(ROOT/'BUILD.json').write_text(json.dumps(build,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in build.items() if k not in ['baseline_files','candidate_files']},indent=2))

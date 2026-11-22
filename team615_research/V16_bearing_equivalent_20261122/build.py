from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
import ast
import difflib
import json
import shutil

ROOT=Path(__file__).resolve().parent
SOURCE=Path(r'E:\codex\team615_red_v16_first30_release_20261121\delivery\team615_red_v16.zip')
BASE_SHA='e98990cfd9269ab521621bc97d7c9e81e21fa83bb83dafbfefb3943480dd6791'
assert sha256(SOURCE.read_bytes()).hexdigest()==BASE_SHA
shutil.copyfile(SOURCE,ROOT/'baseline_snapshot.zip')
with ZipFile(SOURCE) as archive:
    assert len(archive.namelist())==56 and archive.testzip() is None
    assert all('/' not in n and '\\' not in n for n in archive.namelist())
    archive.extractall(ROOT/'candidate')
    original=archive.read('bearing_core.py').decode('utf8')
    info=archive.infolist()
old='''    result = np.zeros(h * w, np.uint8)
    np.bitwise_or.at(result, ids, bits)
    nonzero = np.flatnonzero(result)
    return nonzero.astype(np.int32), result[nonzero]'''
new='''    # Only touched cells are needed; unique() preserves the original ascending IDs.
    nonzero, inverse = np.unique(ids, return_inverse=True)
    result = np.zeros(nonzero.size, np.uint8)
    np.bitwise_or.at(result, inverse, bits)
    keep_nonzero = result != 0
    return nonzero[keep_nonzero].astype(np.int32), result[keep_nonzero]'''
assert original.count(old)==1
candidate=original.replace(old,new)
old2='''def independent_incidence(bits):
    """Two populated 45 degree bins separated by at least one empty bin."""
    b = np.asarray(bits, np.uint8)
    result = np.zeros(b.shape, bool)
    for first in range(8):
        for second in range(first + 1, 8):
            if min(second - first, 8 - (second - first)) >= 2:
                result |= ((b & (1 << first)) != 0) & ((b & (1 << second)) != 0)
    return result'''
new2='''# The unchanged sector-pair rule has only 256 possible uint8 inputs.
_INDEPENDENT_INCIDENCE = np.array([
    any((value & (1 << first)) and (value & (1 << second))
        for first in range(8) for second in range(first + 1, 8)
        if min(second - first, 8 - (second - first)) >= 2)
    for value in range(256)
], dtype=bool)
_INDEPENDENT_INCIDENCE.flags.writeable = False


def independent_incidence(bits):
    """Two populated 45 degree bins separated by at least one empty bin."""
    b = np.asarray(bits, np.uint8)
    # asarray keeps the original zero-dimensional ndarray return for scalar input.
    return np.asarray(_INDEPENDENT_INCIDENCE[b], dtype=bool)'''
assert candidate.count(old2)==1
candidate=candidate.replace(old2,new2)
(ROOT/'candidate/bearing_core.py').write_bytes(candidate.encode('utf8'))
before=ast.parse(original);after=ast.parse(candidate)
old_functions={n.name:ast.dump(n,include_attributes=False) for n in before.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
new_functions={n.name:ast.dump(n,include_attributes=False) for n in after.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
changed=[n for n in old_functions if old_functions[n]!=new_functions[n]]
assert changed==['hit_direction_bits','independent_incidence']
old_files={};new_files={}
with ZipFile(SOURCE) as archive,ZipFile(ROOT/'candidate_snapshot.zip','w') as output:
    for item in info:
        a=archive.read(item.filename);b=(ROOT/'candidate'/item.filename).read_bytes()
        old_files[item.filename]=sha256(a).hexdigest();new_files[item.filename]=sha256(b).hexdigest()
        if item.filename.endswith('.py'):compile(b,item.filename,'exec')
        output.writestr(item,b)
assert [n for n in old_files if old_files[n]!=new_files[n]]==['bearing_core.py']
deadline=ast.parse((ROOT/'candidate/deadline_submission.py').read_text(encoding='utf8'))
klass=next(n for n in deadline.body if isinstance(n,ast.ClassDef) and n.name=='DeadlineSubmission')
margin=next(n.value.value for n in klass.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MIN_WALL_MARGIN' for t in n.targets))
assert margin==1.5
patch=''.join(difflib.unified_diff(original.splitlines(keepends=True),candidate.splitlines(keepends=True),fromfile='V16/bearing_core.py',tofile='candidate/bearing_core.py'))
(ROOT/'CHANGES.patch').write_text(patch,encoding='utf8',newline='\n')
build=dict(status='PASS',baseline='V16',baseline_zip_sha256=BASE_SHA,
    candidate_zip_sha256=sha256((ROOT/'candidate_snapshot.zip').read_bytes()).hexdigest(),
    baseline_files=old_files,candidate_files=new_files,changed_files=['bearing_core.py'],unchanged_files=55,
    changed_functions=changed,added_constant='_INDEPENDENT_INCIDENCE: immutable 256-entry bool lookup table',
    min_wall_margin_seconds=margin,full_matches=0,release_status='RESEARCH_CANDIDATE_NOT_COMPETITION_RELEASE')
(ROOT/'BUILD.json').write_text(json.dumps(build,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in build.items() if k not in ['baseline_files','candidate_files']},indent=2))

from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
import ast,difflib,json,shutil

ROOT=Path(__file__).resolve().parent
BASE=Path(r'E:\codex\team615_red_v16_first30_release_20261121\delivery\team615_red_v16.zip')
assert sha256(BASE.read_bytes()).hexdigest()=='e98990cfd9269ab521621bc97d7c9e81e21fa83bb83dafbfefb3943480dd6791'
shutil.copyfile(BASE,ROOT/'baseline_snapshot.zip')
with ZipFile(BASE) as z:
    z.extractall(ROOT/'candidate');original={n:z.read(n) for n in z.namelist()};infos=z.infolist()
assert len(original)==56
ending='\r\n' if b'\r\n' in original['map_candidates.py'] else '\n'
code=original['map_candidates.py'].decode().replace('\r\n','\n')
code=code.replace('        self.fusion_signature = None\n','        self.fusion_signature = None\n        self._scored_image = None\n',1)
code=code.replace("return np.unpackbits(self.images[owner]['packed'])[:self.width*self.height].reshape(self.height,self.width).astype(np.uint8)","return np.unpackbits(self.images[owner]['packed'], count=self.width*self.height).reshape(self.height,self.width)")
code=code.replace('        if not self.images:return None\n        memory=MapMemory', '        self._scored_image = None\n        if not self.images:return None\n        memory=MapMemory',1)
code=code.replace('        table=[]\n        for owner,data in sorted(self.images.items()):\n            bitmap=self.image(owner).astype(bool)',
'''        table=[]
        decoded={}
        context={} if getattr(score_fn, '_accepts_score_context', False) else None
        for owner,data in sorted(self.images.items()):
            bitmap=self.image(owner)''',1)
code=code.replace('            reduced=bitmap[::2,::2][:hits.shape[0],:hits.shape[1]]\n            score=score_fn(reduced,hits)',
'''            reduced=bitmap[::2,::2][:hits.shape[0],:hits.shape[1]].astype(bool)
            decoded[owner]=bitmap
            score=(score_fn(reduced,hits,context=context) if context is not None
                   else score_fn(reduced,hits))''',1)
code=code.replace('        self.score_table=table;self.best=best\n',
'''        self.score_table=table;self.best=best
        data=self.images[best['owner']]
        self._scored_image=(best['owner'],data['version'],data['digest'],
                            data['packed'],decoded[best['owner']])
''',1)
code=code.replace('        image=self.image(owner);data=self.images[owner]\n',
'''        data=self.images[owner]
        staged=self._scored_image
        self._scored_image=None
        if (staged is not None and staged[:3]==(owner,data['version'],data['digest'])
                and staged[3] is data['packed']):
            image=staged[4]
        else:
            image=self.image(owner)
''',1)
(ROOT/'candidate/map_candidates.py').write_bytes(code.replace('\n',ending).encode())
ending='\r\n' if b'\r\n' in original['red_hooks.py'] else '\n'
code=original['red_hooks.py'].decode().replace('\r\n','\n')
old='''def local_score(bitmap, hits):
    # Assess predicted walls only against stable lidar evidence in the same frame.
    # A one-cell (two-pixel) tolerance allows raster quantization.
    k=np.ones((3,3), np.uint8)
    hit_band=cv2.dilate(hits.astype(np.uint8),k)>0
    map_band=cv2.dilate(bitmap.astype(np.uint8),k)>0
    precision=np.count_nonzero(bitmap & hit_band)/max(1,np.count_nonzero(bitmap))
    recall=np.count_nonzero(hits & map_band)/max(1,np.count_nonzero(hits))
    dice=2*precision*recall/max(1e-12,precision+recall)
    return dict(precision=precision,recall=recall,score=dice)'''
new='''def local_score(bitmap, hits, *, context=None):
    # Context belongs to one choose() call; reference evidence is never cached across rounds.
    k=np.ones((3,3), np.uint8)
    if context is None:
        context={}
    if context.get('hits') is not hits:
        context.clear()
        context.update(hits=hits,hit_band=cv2.dilate(hits.astype(np.uint8),k)>0,
                       hit_count=np.count_nonzero(hits))
    map_band=cv2.dilate(bitmap.astype(np.uint8),k)>0
    precision=np.count_nonzero(bitmap & context['hit_band'])/max(1,np.count_nonzero(bitmap))
    recall=np.count_nonzero(hits & map_band)/max(1,context['hit_count'])
    dice=2*precision*recall/max(1e-12,precision+recall)
    return dict(precision=precision,recall=recall,score=dice)


# Other two-argument scoring callbacks retain their original calling convention.
local_score._accepts_score_context = True'''
assert code.count(old)==1
code=code.replace(old,new)
(ROOT/'candidate/red_hooks.py').write_bytes(code.replace('\n',ending).encode())
changed={};hashes={}
with ZipFile(ROOT/'candidate_snapshot.zip','w') as z:
    for info in infos:
        data=(ROOT/'candidate'/info.filename).read_bytes();z.writestr(info,data)
        hashes[info.filename]=sha256(data).hexdigest()
        if data!=original[info.filename]:changed[info.filename]=data
        if info.filename.endswith('.py'):compile(data,info.filename,'exec')
assert list(changed)==['map_candidates.py','red_hooks.py']
assert (ROOT/'candidate/bearing_core.py').read_bytes()==original['bearing_core.py']
assert (ROOT/'candidate/deadline_submission.py').read_bytes()==original['deadline_submission.py']
assert b'MIN_WALL_MARGIN = 1.5' in original['deadline_submission.py']
def functions(data):
    tree=ast.parse(data);result={}
    for n in tree.body:
        if isinstance(n,ast.FunctionDef):result[n.name]=ast.dump(n,include_attributes=False)
        if isinstance(n,ast.ClassDef):
            for child in n.body:
                if isinstance(child,ast.FunctionDef):result[n.name+'.'+child.name]=ast.dump(child,include_attributes=False)
    return result
changes={}
for name,data in changed.items():
    before,after=functions(original[name]),functions(data)
    changes[name]=[key for key in before if before[key]!=after[key]]
assert changes=={'map_candidates.py':['MapCandidates.__init__','MapCandidates.image','MapCandidates.choose','MapCandidates.install'],
                'red_hooks.py':['local_score']}
patch=''.join(''.join(difflib.unified_diff(original[n].decode().replace('\r\n','\n').splitlines(keepends=True),changed[n].decode().replace('\r\n','\n').splitlines(keepends=True),fromfile='V16/'+n,tofile='candidate/'+n)) for n in changed)
(ROOT/'CHANGES.patch').write_text(patch,encoding='utf8',newline='\n')
build=dict(status='PASS',baseline='released V16',baseline_zip_sha256=sha256(BASE.read_bytes()).hexdigest(),
    candidate_zip_sha256=sha256((ROOT/'candidate_snapshot.zip').read_bytes()).hexdigest(),
    baseline_files={n:sha256(b).hexdigest() for n,b in original.items()},candidate_files=hashes,
    changed_functions=changes,unchanged_files=54,wall_margin_seconds=1.5,
    previous_bearing_optimization_included=False,full_matches=0,release_status='RESEARCH_ONLY')
(ROOT/'BUILD.json').write_text(json.dumps(build,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in build.items() if not k.endswith('_files')},indent=2))

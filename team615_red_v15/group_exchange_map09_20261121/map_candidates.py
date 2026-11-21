"""Immutable epoch snapshots, actual payload receipts and common-reference ranking."""
import hashlib
import numpy as np
from swarm_rescue.solutions.greedy_mapping import MapMemory
from swarm_rescue.solutions.submission_renderer import SubmissionBearings


def digest(value):
    h = hashlib.sha256()
    def add(v):
        if isinstance(v,np.ndarray):
            h.update(str((v.dtype.str,v.shape)).encode());h.update(v.tobytes(order='C'))
        elif isinstance(v,dict):
            for k in sorted(v,key=repr): add(k);add(v[k])
        elif isinstance(v,(tuple,list)):
            h.update(b'[')
            for x in v: add(x)
            h.update(b']')
        else:
            h.update(repr(v).encode());h.update(b';')
    add(value)
    return h.hexdigest()


def frozen(value):
    if isinstance(value,np.ndarray):
        a=value.copy();a.flags.writeable=False;return a
    if isinstance(value,dict):return {k:frozen(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return tuple(frozen(x) for x in value)
    return value


class MapCandidates:
    def __init__(self, owner, epoch, width, height):
        self.owner,self.epoch,self.width,self.height = int(owner),epoch,int(width),int(height)
        self.snapshots = {}
        self.images = {}
        self.receipts = {}
        self.audit = []
        self.local_version = None
        self.best = None
        self.score_table = None
        self.reference_digest = None
        self.fusion_built = False
        self.last_payload = -10
        self.cursor = 0

    def freeze_local(self, drone, step):
        if self.owner in self.snapshots:
            return
        self.local_version = int(step)
        data = dict(epoch=self.epoch,owner=self.owner,version=int(step),
                    memory=frozen(drone.memory.packet()),bearings=frozen(drone.submission_bearings.bits),
                    inventory=frozen(drone.inventory_records))
        data['digest']=digest(data)
        self.snapshots[self.owner]=data
        self.audit.append((step,'snapshot_frozen',self.owner,data['digest']))

    def context(self, snapshot):
        memory=MapMemory(self.width,self.height);memory.merge(snapshot['memory'])
        bearing=SubmissionBearings(self.width,self.height);bearing.bits=np.array(snapshot['bearings'],copy=True)
        return memory,bearing

    def build_local_image(self, drone, step):
        if self.owner in self.images or self.owner not in self.snapshots:
            return
        if step % drone.team_size != self.owner or drone.walltime_limit-drone.elapsed_walltime <= 8:
            return
        memory,bearing=self.context(self.snapshots[self.owner])
        self.add_image(self.owner,self.local_version,bearing.render(memory),
                       {self.owner:self.snapshots[self.owner]['digest']},step)

    def add_image(self, owner, version, bitmap, sources, step):
        data=dict(epoch=self.epoch,owner=int(owner),version=int(version),
                  packed=frozen(np.packbits(np.asarray(bitmap,dtype=bool).ravel())),
                  sources=dict(sources))
        data['digest']=digest(data)
        self.images[int(owner)]=data
        self.audit.append((step,'image_built',owner,data['digest']))

    def image(self, owner):
        return np.unpackbits(self.images[owner]['packed'])[:self.width*self.height].reshape(self.height,self.width).astype(np.uint8)

    def manifest(self):
        return tuple((kind,owner,data['version'],data['digest'])
                     for kind,store in (('snapshot',self.snapshots),('image',self.images))
                     for owner,data in sorted(store.items()))

    def receive(self, drone, peer, payload, step):
        if not isinstance(payload,tuple) or len(payload) != 2:
            return False
        kind,data=payload
        if kind not in ('snapshot','image') or not isinstance(data,dict):return False
        owner,version=data.get('owner'),data.get('version')
        if (type(owner) is not int or not 0 <= owner <= drone.team_size or
                type(version) is not int or not 0 <= version <= step or
                tuple(data.get('epoch',())) != self.epoch):return False
        if kind=='snapshot' and owner==drone.team_size:return False
        store=self.snapshots if kind=='snapshot' else self.images
        old=store.get(owner)
        if old is not None:
            return old['version']==version and old['digest']==data.get('digest')
        if data.get('digest') != digest({k:v for k,v in data.items() if k!='digest'}):
            self.audit.append((step,'payload_rejected',peer,kind,owner,'digest'));return False
        if kind=='snapshot':
            packet,bits=data.get('memory'),data.get('bearings')
            if not isinstance(packet,tuple) or len(packet)!=4:return False
            ids,values,free,visits=packet
            if (not isinstance(ids,np.ndarray) or ids.ndim!=1 or ids.dtype.kind not in 'iu'
                    or not isinstance(values,np.ndarray) or values.dtype!=np.uint8 or values.shape!=ids.shape
                    or (ids.size and (ids.min()<0 or ids.max()>=drone.memory.hits.size))
                    or not isinstance(free,np.ndarray) or free.dtype!=np.uint8 or free.ndim!=1
                    or free.size!=(drone.memory.free.size+7)//8
                    or not isinstance(visits,np.ndarray) or visits.dtype!=np.uint8 or visits.shape!=drone.memory.shape
                    or not isinstance(bits,np.ndarray) or bits.dtype!=np.uint8
                    or bits.shape!=drone.submission_bearings.bits.shape):return False
            # Validated actual payload, not a peer's claim that a source exists.
            saved=frozen(data)
            drone.memory.merge(saved['memory'])
            drone.submission_bearings.bits |= saved['bearings']
            drone._receive_team_coordination({'id':peer,'red_inventory':saved['inventory']},step)
        else:
            packed=data.get('packed')
            if (not isinstance(packed,np.ndarray) or packed.dtype!=np.uint8 or packed.ndim!=1
                    or packed.size!=(self.width*self.height+7)//8 or not isinstance(data.get('sources'),dict)):
                return False
            saved=frozen(data)
        store[owner]=saved
        self.audit.append((step,'payload_stored',peer,kind,owner,version,data['digest']))
        return True

    def payload(self, step, peer_manifests):
        if step-self.last_payload < 2 or not peer_manifests:return None
        missing=[]
        for item in self.manifest():
            if any(item not in have for have in peer_manifests):missing.append(item)
        if not missing:return None
        self.cursor %= len(missing)
        kind,owner,_,_=missing[self.cursor];self.cursor+=1;self.last_payload=step
        data=(self.snapshots if kind=='snapshot' else self.images)[owner]
        return kind,data

    def choose(self, drone, step, score_fn, fusion=True):
        if not self.images:return None
        memory=MapMemory(self.width,self.height);memory.merge(drone.memory.packet())
        bearing=SubmissionBearings(self.width,self.height);bearing.bits=drone.submission_bearings.bits.copy()
        for data in self.snapshots.values():
            memory.merge(data['memory']);bearing.bits |= data['bearings']
        if fusion and not self.fusion_built and drone.walltime_limit-drone.elapsed_walltime > 8:
            self.fusion_built=True
            self.add_image(drone.team_size,step,bearing.render(memory),
                           {i:d['digest'] for i,d in self.snapshots.items()},step)
        hits=memory.hits>=3
        self.reference_digest=digest(hits)
        table=[]
        for owner,data in sorted(self.images.items()):
            bitmap=self.image(owner).astype(bool)
            # Same downsample and stable-hit reference for every candidate.
            reduced=bitmap[::2,::2][:hits.shape[0],:hits.shape[1]]
            score=score_fn(reduced,hits)
            table.append(dict(owner=owner,version=data['version'],digest=data['digest'],**score))
        best=max(table,key=lambda x:(x['score'],x['version'],-x['owner'],x['digest']))
        self.score_table=table;self.best=best
        self.audit.append((step,'map_selected',self.reference_digest,table,best['digest']))
        return best

    def install(self, drone, owner, step):
        image=self.image(owner);data=self.images[owner]
        versions={i:d['version'] for i,d in self.snapshots.items()}
        cache=('group-return-v1',owner,data['version'],data['digest'])
        drone.group_best_image=(image,cache,versions)
        deadline=drone.deadline_submission
        deadline.image=image;deadline.cache=cache;deadline.remember(step,image)
        drone.deadline_versions=versions.copy()
        return image,cache,versions

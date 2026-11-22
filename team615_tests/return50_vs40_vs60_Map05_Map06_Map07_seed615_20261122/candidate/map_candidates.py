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
    ORDINARY_NEAR_TIE = 0.003

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
        self.live_image = None
        self.live_version = -1
        self.fusion_signature = None

    def input_signature(self):
        team_size=int(self.epoch[2])
        return (tuple((o,d['version'],d['digest']) for o,d in sorted(self.snapshots.items())),
                tuple((o,d['version'],d['digest']) for o,d in sorted(self.images.items()) if o<team_size),
                self.live_version)

    def remember_live(self, step, bitmap, force=False):
        # Reuse images already rendered by the existing backup/cache cadence.
        # This is independent from install(), so installing a choice cannot
        # continually invalidate the comparison or generate more renders.
        if step<self.live_version or step==self.live_version and not force:return
        self.live_version=int(step)
        self.live_image=frozen(np.asarray(bitmap,dtype=np.uint8))
        if force:self.fusion_signature=None
        self.audit.append((step,'live_candidate_cached',self.owner))

    def retain_best(self, step):
        if self.best is None:return
        owner=self.best['owner'];team_size=int(self.epoch[2])
        if owner<team_size or owner==team_size+1:return
        data=self.images[owner]
        preserved=dict(epoch=self.epoch,owner=team_size+1,version=data['version'],
                       packed=frozen(data['packed']),sources=dict(data['sources']))
        preserved['digest']=digest(preserved)
        self.images[team_size+1]=preserved
        self.audit.append((step,'previous_best_retained',data['digest'],preserved['digest']))

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
        old=self.images.get(int(owner))
        if owner<int(self.epoch[2]) and old is not None:
            # Individual original images are immutable for this epoch.
            return old['digest']==data['digest']
        self.images[int(owner)]=data
        self.audit.append((step,'image_built',owner,data['digest']))
        return True

    def image(self, owner):
        return np.unpackbits(self.images[owner]['packed'])[:self.width*self.height].reshape(self.height,self.width).astype(np.uint8)

    def manifest(self):
        return tuple((kind,owner,data['version'],data['digest'])
                     for kind,store in (('snapshot',self.snapshots),('image',self.images))
                     for owner,data in sorted(store.items()) if owner<int(self.epoch[2]))

    def receive(self, drone, peer, payload, step):
        if not isinstance(payload,tuple) or len(payload) != 2:
            return False
        kind,data=payload
        if kind not in ('snapshot','image') or not isinstance(data,dict):return False
        owner,version=data.get('owner'),data.get('version')
        if (type(owner) is not int or not 0 <= owner <= drone.team_size or
                type(version) is not int or not 0 <= version <= step or
                tuple(data.get('epoch',())) != self.epoch):return False
        # The local current/fusion slot is not a shared immutable source ID.
        if owner==drone.team_size:return False
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

    @classmethod
    def select_candidate(cls, table, ordinary=False):
        if not table:return None
        if ordinary:
            highest=max(x['score'] for x in table)
            near=[x for x in table if x['score']>=highest-cls.ORDINARY_NEAR_TIE]
            return max(near,key=lambda x:(x['version'],x['score'],-x['owner'],x['digest']))
        return max(table,key=lambda x:(x['score'],x['version'],-x['owner'],x['digest']))

    def choose(self, drone, step, score_fn, fusion=True, ordinary=False):
        if not self.images:return None
        memory=MapMemory(self.width,self.height);memory.merge(drone.memory.packet())
        bearing=SubmissionBearings(self.width,self.height);bearing.bits=drone.submission_bearings.bits.copy()
        for data in self.snapshots.values():
            memory.merge(data['memory']);bearing.bits |= data['bearings']
        signature=(tuple((i,d['digest']) for i,d in sorted(self.snapshots.items())),self.live_version)
        # A soft coordination deadline prohibits new fitting, not reuse of an
        # image which the unchanged backup cadence has already rendered.
        # Otherwise the emergency image can remain pinned to an older epoch.
        if (not fusion and self.live_image is not None
                and self.live_version>self.images.get(drone.team_size,{}).get('version',-1)):
            self.add_image(drone.team_size,self.live_version,self.live_image,
                           {i:d['digest'] for i,d in self.snapshots.items()},step)
            self.fusion_built=True;self.fusion_signature=signature
        if (fusion and (not self.fusion_built or signature!=self.fusion_signature)
                and drone.walltime_limit-drone.elapsed_walltime>8):
            last_snapshot=max((v[0] for v in self.audit if v[1] in ('snapshot_frozen','payload_stored')
                               and (v[1]=='snapshot_frozen' or v[3]=='snapshot')),default=-1)
            # If an existing live render already includes the received payloads,
            # compare it directly. Otherwise make one render with unchanged fit.
            current=(self.live_image if self.live_image is not None and self.live_version>=last_snapshot
                     else bearing.render(memory))
            self.fusion_built=True;self.fusion_signature=signature
            self.add_image(drone.team_size,step,current,
                           {i:d['digest'] for i,d in self.snapshots.items()},step)
        hits=memory.hits>=3
        self.reference_digest=digest(hits)
        table=[]
        for owner,data in sorted(self.images.items()):
            bitmap=self.image(owner).astype(bool)
            if not bitmap.any():continue
            # Same downsample and stable-hit reference for every candidate.
            reduced=bitmap[::2,::2][:hits.shape[0],:hits.shape[1]]
            score=score_fn(reduced,hits)
            table.append(dict(owner=owner,version=data['version'],digest=data['digest'],**score))
        if not table:return None
        best=self.select_candidate(table,ordinary=ordinary)
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

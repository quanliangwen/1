"""End-of-search snapshots relayed by origin; used only for submission."""
from copy import copy


class FinalMaps:
    CONTACT_TTL = 12
    SEND_INTERVAL = 3
    COLLECTION_STEPS = 24

    def __init__(self, owner, team_size):
        self.owner = owner
        self.team_size = team_size
        self.snapshots = {}
        self.peers = {}
        self.last_sent = {}
        self.received = []
        self.collection_start = None

    @property
    def mask(self):
        return sum(1 << owner for owner in self.snapshots)

    def freeze(self, step, memory):
        if self.owner not in self.snapshots:
            self.snapshots[self.owner] = (self.owner, step, True, memory.packet())

    def receive(self, sender, step, mask, snapshot):
        if type(sender) is not int or not 0 <= sender < self.team_size or sender == self.owner:
            return
        if type(mask) is not int or not 0 <= mask < 1 << self.team_size:
            return
        self.peers[sender] = step, mask
        if not isinstance(snapshot, tuple) or len(snapshot) != 4:
            return
        owner, version, final, evidence = snapshot
        if (type(owner) is not int or not 0 <= owner < self.team_size or owner == self.owner
                or type(version) is not int or not 0 <= version <= step or final is not True
                or not isinstance(evidence, tuple) or len(evidence) != 4
                or owner in self.snapshots or not mask & (1 << owner)):
            return
        self.snapshots[owner] = snapshot
        self.received.append((step, sender, owner, version))

    def outgoing(self, step):
        if step % self.SEND_INTERVAL != self.owner % self.SEND_INTERVAL:
            return None
        near = [mask for stamp, mask in self.peers.values() if step - stamp <= self.CONTACT_TTL]
        missing = [owner for owner in self.snapshots if any(not mask & (1 << owner) for mask in near)]
        if not missing:
            return None
        owner = min(missing, key=lambda peer: (self.last_sent.get(peer, -1), peer != self.owner, peer))
        self.last_sent[owner] = step
        return self.snapshots[owner]

    def waiting(self, step, deadline_start, wall_left):
        if len(self.snapshots) == self.team_size or step >= deadline_start or wall_left <= 12:
            return False
        if self.collection_start is None:
            self.collection_start = step
        return step - self.collection_start < self.COLLECTION_STEPS

    def rank(self, estimate):
        # Compare final-source counts before the ordinary map estimate.
        return len(self.snapshots) * 1600 + estimate * 1500 // 10000

    def fuse(self, memory):
        merged = copy(memory)
        merged.hits = memory.hits.copy()
        merged.free = memory.free.copy()
        merged.visits = memory.visits.copy()
        versions = {}
        for owner, (_, version, _, evidence) in sorted(self.snapshots.items()):
            merged.merge(evidence)
            versions[owner] = version
        return merged, versions

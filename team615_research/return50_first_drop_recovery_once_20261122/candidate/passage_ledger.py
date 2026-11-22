"""Record an actual transit only after consecutive narrow scans and downstream motion."""
import math


class PassageLedger:
    BUFFER = 180.

    def __init__(self):
        self.pending = None
        self.local = ()
        self.reports = {}
        self.last_narrow = None

    def observe(self, owner, step, pose, course, narrow):
        point = tuple(map(float, pose))
        course = tuple(map(float, course))
        pending = self.pending
        if narrow:
            self.last_narrow = step, point
            same = pending is not None and step - pending[0] <= 32 and math.dist(point,pending[1]) <= 48.
            count = min(2, pending[3]+1) if same else 1
            self.pending = step, point, course, count
            return
        if pending is None:
            return
        tick, anchor, direction, count = pending
        offset = point[0]-anchor[0], point[1]-anchor[1]
        ahead = sum(a*b for a,b in zip(offset,direction))
        if step - tick > 100 or math.hypot(*offset) > 128.:
            self.pending = None
        elif count >= 2 and ahead >= 48.:
            self.pending = None
            vote = (step,*anchor,*course,*point)
            if any(self.same(vote, old) for old in self.local) or len(self.local) >= 12:
                return
            self.local += (vote,)
            self.reports[owner] = self.local

    @staticmethod
    def same(a,b):
        return (math.dist(a[1:3], b[1:3]) <= 90. and math.dist(a[5:7], b[5:7]) <= 108.
                and sum(x*y for x,y in zip(a[3:5], b[3:5])) >= .35)

    def receive(self, drone, owner, message):
        payload = message.get("red_passages")
        if not isinstance(payload, dict) or len(payload) > drone.team_size or type(owner) is not int:
            return
        for source, entries in payload.items():
            if type(source) is not int or not 0 <= source < drone.team_size or source == drone.identifier:
                continue
            old = self.reports.get(source, ())
            if not isinstance(entries, tuple) or not len(old) < len(entries) <= 12 or entries[:len(old)] != old:
                continue
            if all(isinstance(r, tuple) and len(r)==7 and type(r[0]) is int
                   and 0 < r[0] < drone.elapsed_timestep and drone._inside_team_point(r[1:3])
                   and drone._inside_team_point(r[5:7]) and .9 <= math.hypot(*r[3:5]) <= 1.1 for r in entries):
                self.reports[source] = entries

    LOCAL_RADIUS = 38.

    @staticmethod
    def _segment_distance(point, start, end):
        dx,dy = end[0]-start[0], end[1]-start[1]
        px,py = point[0]-start[0], point[1]-start[1]
        norm = dx*dx+dy*dy
        if not norm:
            return math.dist(point, start)
        along = max(0.,min(1.,(px*dx+py*dy)/norm))
        return math.hypot(px-along*dx,py-along*dy)

    def _protects(self, pose, row, opening_limit):
        if row[0] <= opening_limit:
            return min(math.dist(pose,row[1:3]),math.dist(pose,row[5:7])) <= self.BUFFER
        return self._segment_distance(pose,row[1:3],row[5:7]) <= self.LOCAL_RADIUS

    def nearby(self, pose, opening_limit):
        return [row for entries in self.reports.values() for row in entries
                if self._protects(pose,row,opening_limit)]

    def near_recent_narrow(self, pose, opening_limit):
        if self.last_narrow is None:
            return False
        step, point = self.last_narrow
        radius = self.BUFFER if step <= opening_limit else self.LOCAL_RADIUS
        return math.dist(pose, point) <= radius

    def opening_halo_only(self, point, references, opening_limit, buffer):
        if not references or any(row[0] > opening_limit for row in references):
            return False
        if self.last_narrow is not None and math.dist(point,self.last_narrow[1]) <= buffer:
            return False
        return all(self._segment_distance(point,row[1:3],row[5:7]) > buffer for row in references)

    def last_for(self, references, team_size):
        last = None
        for reference in references:
            matches = {}
            for owner, entries in self.reports.items():
                match = next((row for row in entries if self.same(row, reference)), None)
                if match is not None:
                    matches[owner] = match[0]
            if set(matches) != set(range(team_size)):
                continue
            # Require uniqueness. Two equally stamped passes give no authorization.
            end = max(matches.values())
            winners = [owner for owner,tick in matches.items() if tick==end]
            if len(winners) != 1 or (last is not None and last != winners[0]):
                return None
            last = winners[0]
        return last

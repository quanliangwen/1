"""作业1：Edmonds-Karp最大流，并穷举全部割独立校验。仅需Python标准库。"""
from collections import deque
from itertools import combinations
import json
from pathlib import Path

ARCS = [('ST','RO',50), ('ST','BO',70), ('ST','LI',40),
        ('RO','NY',60), ('BO','NY',40), ('BO','NO',50),
        ('LI','NO',30), ('NY','LA',80), ('NO','LA',70)]

def solve():
    adj, residual = {}, {}
    for u, v, c in ARCS:
        adj.setdefault(u, []).append(v)
        adj.setdefault(v, []).append(u)
        residual[u, v], residual[v, u] = c, 0
    value, trace = 0, []
    while True:
        parent, queue = {'ST': None}, deque(['ST'])
        while queue and 'LA' not in parent:
            u = queue.popleft()
            for v in adj[u]:
                if v not in parent and residual[u, v] > 0:
                    parent[v] = u
                    queue.append(v)
        if 'LA' not in parent:
            break
        path, v = [], 'LA'
        while parent[v] is not None:
            u = parent[v]
            path.append((u, v))
            v = u
        delta = min(residual[e] for e in path)
        for u, v in path:
            residual[u, v] -= delta
            residual[v, u] += delta
        value += delta
        trace.append({'path': ['ST'] +
                      [v for u, v in reversed(path)],
                      'delta': delta, 'total': value})
    flows = [(u, v, c, c-residual[u,v]) for u,v,c in ARCS]
    for u,v,c,f in flows:
        assert 0 <= f <= c
    for n in adj:
        net = sum(f for u,v,c,f in flows if u == n)
        net -= sum(f for u,v,c,f in flows if v == n)
        assert net == (value if n == 'ST' else
                       -value if n == 'LA' else 0)
    middle = sorted(set(adj) - {'ST', 'LA'})
    cuts = []
    for k in range(len(middle)+1):
        for subset in combinations(middle, k):
            side = {'ST', *subset}
            capacity = sum(c for u,v,c in ARCS
                           if u in side and v not in side)
            cuts.append((capacity, sorted(side)))
    minimum = min(c for c,s in cuts)
    assert value == minimum
    return {'maximum_flow': value, 'arcs': flows,
            'augmentations': trace, 'cuts_checked': len(cuts),
            'minimum_cuts': [s for c,s in cuts if c == minimum]}

if __name__ == '__main__':
    result = solve()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    Path(__file__).with_name('result1.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

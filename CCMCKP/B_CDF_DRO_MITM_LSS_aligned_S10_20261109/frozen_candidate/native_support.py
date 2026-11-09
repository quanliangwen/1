import math
import numpy as np

def checks(L, m, seed):
    target = L**m // 100
    if not target:
        return []
    rng = np.random.default_rng(seed)
    result = []
    for repeat in range(10):
        products = [1] * m
        factors = ([5] * (3*m-2) + [2] * (2*m-2)) if L == 500 else ([3]*m + [5]*(m-2) + [2]*(m-2))
        if repeat:
            rng.shuffle(factors)
        for f in factors:
            valid = [i for i,p in enumerate(products) if p*f <= L]
            if not valid:
                break
            floor = min(products[i] for i in valid)
            opts = [i for i in valid if products[i] == floor]
            products[int(rng.choice(opts))] *= f
        else:
            assert math.prod(products) == target
            for _ in range(50):
                result.append(rng.permutation(np.asarray(products)-1).tolist())
    return result

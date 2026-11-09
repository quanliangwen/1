import time,warnings,os
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import csr_matrix

def binary_model(groups,n,objective,rows=(),lo=(),hi=(),seconds=1.,pool=1):
    matrix=[];lower=[];upper=[]
    for g in groups:
        row=np.zeros(n);row[g]=1;matrix.append(row);lower.append(1.);upper.append(1.)
    matrix.extend(rows);lower.extend(lo);upper.extend(hi)
    out=[];end=time.monotonic()+seconds
    for _ in range(pool):
        remaining=end-time.monotonic()
        if remaining<=.005:break
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',message='Unrecognized options detected.*')
            result=milp(objective,integrality=np.ones(n),bounds=Bounds(0,1),constraints=LinearConstraint(csr_matrix(np.array(matrix)),lower,upper),options={'time_limit':remaining,'mip_rel_gap':0.,'threads':1,'random_seed':int(os.environ.get('S2_SEARCH_SEED','0'))})
        if result.x is None:break
        s=tuple(int(g[np.argmax(result.x[g])]) for g in groups);out.append(s)
        row=np.zeros(n);row[list(s)]=1.;matrix.append(row);lower.append(-np.inf);upper.append(len(groups)-1.)
    return out


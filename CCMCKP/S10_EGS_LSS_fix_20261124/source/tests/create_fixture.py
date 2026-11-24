"""Generate the no-distribution-metadata regression fixture in a new directory."""
from pathlib import Path
import pickle,sys
p=Path(sys.argv[1]);p.mkdir(parents=True,exist_ok=False)
(p/'node_to_factor.pkl').write_bytes(pickle.dumps({0:[0,1],1:[2,3],2:[4,5]},protocol=4))
(p/'cost.txt').write_text('1\n2\n1\n2\n1\n2\n')
for j in range(6):(p/(str(j)+'_sample.txt')).write_text('\n'.join(['0']*499+(['100'] if j==0 else ['0']))+'\n')
print(p)

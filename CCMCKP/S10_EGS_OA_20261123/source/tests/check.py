"""Portable tiny checks. No benchmark campaign, historical solutions or extra MC."""
from pathlib import Path
from fractions import Fraction
import argparse
import itertools
import json
import pickle
import subprocess

def fixture(root,size):
    root.mkdir()
    groups={g:list(range(g*size,(g+1)*size)) for g in range(3)}
    (root/'node_to_factor.pkl').write_bytes(pickle.dumps(groups,protocol=4))
    costs=[]
    for g in range(3):
        for k in range(size):
            j=g*size+k
            costs.append(10-k+.031*g+.007*k*k)
            mu=.15+.14*k+.013*g
            spread=.015+.004*((k+g)%3)
            (root/(str(j)+'_sample.txt')).write_text('\n'.join(
                f'{mu+spread*((i%5)-2):.6f}' for i in range(30))+'\n',encoding='utf-8')
    (root/'cost.txt').write_text('\n'.join(map(str,costs))+'\n',encoding='utf-8')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',required=True,type=Path)
    parser.add_argument('--math-binary',required=True,type=Path)
    parser.add_argument('--workdir',required=True,type=Path,help='Must not already exist')
    args=parser.parse_args()
    args.workdir.mkdir(parents=True,exist_ok=False)
    fixture(args.workdir/'math',2)
    fixture(args.workdir/'probability',8)
    def run(command):
        result=subprocess.run([str(s) for s in command],capture_output=True,text=True,timeout=90)
        if result.returncode:
            raise RuntimeError(result.stdout+'\n'+result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])
    report={'math':run([args.math_binary,args.workdir/'math']),'fraction_checks':[]}
    data=args.workdir/'probability'
    for name,selection in [('safe',[0,8,16]),('unsafe',[7,15,23]),('boundary',[2,11,20])]:
        record=run([args.binary,'--instance',data,'--capacity','1.7','--seed','960001',
            '--evaluate',','.join(map(str,selection))])
        samples=[[Fraction(s) for s in (data/(str(j)+'_sample.txt')).read_text().split()] for j in selection]
        successes=sum(sum(row)<Fraction('1.7') for row in itertools.product(*samples))
        cert=record['grid']
        assert int(cert['denominator'])==27000
        assert int(cert['lower_numerator'])<=successes<=int(cert['upper_numerator'])
        report['fraction_checks'].append({'case':name,'successes':successes,'denominator':27000})
    report['status']='PASS'
    (args.workdir/'RESULT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__':
    main()

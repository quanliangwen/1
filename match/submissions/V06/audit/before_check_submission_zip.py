"""Fail-closed contest ZIP identity/dependency/ABI-receipt release check."""
import argparse,ast,datetime,hashlib,json,re,sys,zipfile
from pathlib import Path

PINNED={'numpy':'1.26.4','opencv-contrib-python':'4.11.0.86','pandas':'2.2.3'}

def inspect_package(path,receipt=None,static_only=False):
    checks=[]
    def require(condition,name):
        if not condition:raise ValueError(name)
        checks.append(name)
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    require(re.fullmatch(r'team615_(red|blue)_v[0-9]{2,}\.zip',path.name) is not None,'numeric_team615_and_version_filename')
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        require(z.testzip() is None,'zip_crc')
        require(len(names)==len(set(names)),'no_duplicate_entries')
        require(all('/' not in n and '\\' not in n and n not in ['.','..'] for n in names),'flat_zip_no_traversal')
        require({'team_info.yml','my_drone_eval.py','req.txt'}<=set(names),'required_root_files')
        require(all(n.endswith(('.py','.txt','.yml','.yaml')) for n in names),'no_engine_state_or_binary_payload')
        team=z.read('team_info.yml').decode('utf-8-sig')
        require(len(re.findall(r'(?m)^\s*team_number\s*:',team))==1,'one_team_number_key')
        require(re.search(r'(?m)^team_number:\s*615\s*(?:#.*)?$',team) is not None,'team_number_yaml_integer_615')
        require('wLoPV5EE' not in team,'historical_string_identifier_absent')
        for field in ['team_name','team_members']:
            require(re.search(r'(?m)^'+field+r':\s*[^\s#].*$',team) is not None,field+'_present')
        deps={}
        for line in z.read('req.txt').decode('utf-8-sig').splitlines():
            line=line.split('#',1)[0].strip()
            if not line:continue
            match=re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)',line)
            require(match is not None,'all_dependencies_exact_pins')
            name,version=match.groups();name=name.lower().replace('_','-')
            require(name not in deps,'no_duplicate_dependency_'+name);deps[name]=version
        require(all(deps.get(n)==v for n,v in PINNED.items()),'validated_numpy_opencv_pandas_pins')
        require(not any(n in deps for n in ['opencv-python','opencv-python-headless','opencv-contrib-python-headless']),'no_conflicting_opencv_distributions')
        files={n:hashlib.sha256(z.read(n)).hexdigest() for n in names}
        for n in names:
            if n.endswith('.py'):ast.parse(z.read(n).decode('utf-8-sig'),filename=n)
        require(True,'all_python_syntax')
        require('image_ref.txt' not in names or not z.read('image_ref.txt').strip(),'code_submission_empty_image_ref')
    if not static_only:
        require(receipt is not None,'abi_receipt_required')
        proof=json.loads(receipt.read_text(encoding='utf-8'))
        require(proof.get('status')=='PASS','abi_checks_pass')
        require(proof.get('submission_zip_sha256')==digest,'abi_receipt_bound_to_actual_zip')
        require(proof.get('payload_files_sha256')==files,'abi_receipt_exact_payload')
        require(proof.get('team_number')==615,'sdk_reads_team615')
        require(proof.get('distribution_versions')==PINNED,'runtime_critical_distributions_match_pins')
        require(proof.get('numeric_random_pandas_cv_operations')=='PASS','mtrand_random_pandas_cv_operations_pass')
        require(proof.get('sdk_launcher_and_stats_import')=='PASS','sdk_import_chain_pass')
        require(all(proof.get('critical_module_paths',{}).get(n) for n in ['numpy','numpy.random.mtrand','pandas','cv2']),'recorded_critical_binary_paths')
    return {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'STATIC_ONLY_PASS_NOT_RELEASED' if static_only else 'PASS','zip':str(path),'sha256':digest,'checks':checks,'official_container_verified':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('zip',type=Path);p.add_argument('--abi-receipt',type=Path);p.add_argument('--static-only',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    try:r=inspect_package(a.zip,a.abi_receipt,a.static_only);code=0
    except Exception as e:r={'status':'FAIL','zip':str(a.zip),'error':str(e)};code=1
    if a.output:a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False));sys.exit(code)

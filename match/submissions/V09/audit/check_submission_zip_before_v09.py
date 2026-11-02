"""Fail-closed contest ZIP identity/dependency/ABI-receipt release check."""
import argparse,ast,datetime,hashlib,json,re,sys,zipfile
from pathlib import Path

PINNED={'numpy':'1.26.4','opencv-contrib-python':'4.11.0.86','pandas':'2.2.3'}
SDK_INHERIT={'numpy':'>=1.24.4','opencv-contrib-python':'>=4.10.0.84'}
J17_PORTABLE={'numpy':'>=1.24.4','opencv-contrib-python':'>=4.10.0.84','scipy':'==1.17.1'}
J17_GUROBI={'numpy':'>=1.24.4','opencv-contrib-python':'>=4.10.0.84','gurobipy':'==13.0.1'}
J17_REFERENCE=Path('E:/codex/J17_team615_red_v07_20261030/J17_original_research_payload.zip')
J17_REFERENCE_SHA256='652b59edbfba68aa5b163b2cbdc904ebecdbe75927073e3a59168013e725a839'
REFERENCE_V05=Path('E:/codex/PJ01_team615_red_v05_20261026/team615_red_v05.zip')
REFERENCE_V05_SHA256='1413661721353548f9dcb9badf6aed4c8763dbde56de0c6d170b7429dc0c9406'
SDK_INHERIT_RUNS={
    'numpy1':{'numpy':'1.26.4','opencv-contrib-python':'4.11.0.86','pandas':'2.2.3'},
    'numpy2':{'numpy':'2.2.6','opencv-contrib-python':'4.11.0.86','pandas':'2.2.3'},
}

def inspect_package(path,receipt=None,static_only=False,dependency_profile='pinned'):
    checks=[]
    def require(condition,name):
        if not condition:raise ValueError(name)
        checks.append(name)
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    require(dependency_profile in ['pinned','sdk-inherit-v06','j17-portable-v07','j17-gurobi-v08'],'known_explicit_dependency_profile')
    if dependency_profile=='sdk-inherit-v06':
        require(path.name=='team615_red_v06.zip','sdk_inherit_profile_scoped_to_v06')
    if dependency_profile=='j17-portable-v07':
        require(path.name=='team615_red_v07.zip','j17_portable_profile_scoped_to_v07')
    if dependency_profile=='j17-gurobi-v08':
        require(path.name=='team615_red_v08.zip','j17_gurobi_profile_scoped_to_v08')
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
            pattern=r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)' if dependency_profile=='pinned' else r'([A-Za-z0-9_.-]+)((?:>=|==)[A-Za-z0-9_.+-]+)'
            match=re.fullmatch(pattern,line)
            require(match is not None,'all_dependencies_exact_pins' if dependency_profile=='pinned' else 'sdk_dependency_lower_bounds_only')
            name,version=match.groups();name=name.lower().replace('_','-')
            require(name not in deps,'no_duplicate_dependency_'+name);deps[name]=version
        if dependency_profile=='pinned':
            require(all(deps.get(n)==v for n,v in PINNED.items()),'validated_numpy_opencv_pandas_pins')
        elif dependency_profile=='sdk-inherit-v06':
            require(deps==SDK_INHERIT,'exact_sdk_inherit_v06_dependency_declarations')
        elif dependency_profile=='j17-portable-v07':
            require(deps==J17_PORTABLE,'exact_j17_portable_dependency_declarations')
        else:
            require(deps==J17_GUROBI,'exact_j17_gurobi_dependency_declarations')
        require(not any(n in deps for n in ['opencv-python','opencv-python-headless','opencv-contrib-python-headless']),'no_conflicting_opencv_distributions')
        files={n:hashlib.sha256(z.read(n)).hexdigest() for n in names}
        for n in names:
            if n.endswith('.py'):
                tree=ast.parse(z.read(n).decode('utf-8-sig'),filename=n)
                if dependency_profile=='j17-portable-v07':
                    for node in ast.walk(tree):
                        imports=([x.name for x in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else [])
                        require(not any(x=='gurobipy' or x.startswith('gurobipy.') for x in imports),'no_commercial_solver_import_'+n)
        require(True,'all_python_syntax')
        require('image_ref.txt' not in names or not z.read('image_ref.txt').strip(),'code_submission_empty_image_ref')
        if dependency_profile=='sdk-inherit-v06':
            require(REFERENCE_V05.exists(),'preserved_v05_reference_available')
            require(hashlib.sha256(REFERENCE_V05.read_bytes()).hexdigest()==REFERENCE_V05_SHA256,'preserved_v05_reference_hash')
            with zipfile.ZipFile(REFERENCE_V05) as reference:
                require(set(reference.namelist())==set(names),'v06_payload_names_unchanged_from_v05')
                require(all(z.read(n)==reference.read(n) for n in names if n!='req.txt'),'v06_changes_req_only_all_other_payload_bytes_unchanged')
        if dependency_profile=='j17-gurobi-v08':
            require(J17_REFERENCE.exists() and hashlib.sha256(J17_REFERENCE.read_bytes()).hexdigest()==J17_REFERENCE_SHA256,'j17_original_tested_archive_available_and_bound')
            with zipfile.ZipFile(J17_REFERENCE) as reference:
                require(set(reference.namelist())==set(names),'v08_same_payload_names_as_original_j17')
                require(all(z.read(n)==reference.read(n) for n in names if n!='req.txt'),'v08_changes_req_only_original_j17_algorithm_bytes_preserved')
    if not static_only:
        require(receipt is not None,'abi_receipt_required')
        proof=json.loads(receipt.read_text(encoding='utf-8'))
        require(proof.get('status')=='PASS','abi_checks_pass')
        require(proof.get('submission_zip_sha256')==digest,'abi_receipt_bound_to_actual_zip')
        require(proof.get('payload_files_sha256')==files,'abi_receipt_exact_payload')
        require(proof.get('team_number')==615,'sdk_reads_team615')
        if dependency_profile=='pinned':
            require(proof.get('distribution_versions')==PINNED,'runtime_critical_distributions_match_pins')
            require(proof.get('numeric_random_pandas_cv_operations')=='PASS','mtrand_random_pandas_cv_operations_pass')
            require(proof.get('sdk_launcher_and_stats_import')=='PASS','sdk_import_chain_pass')
            require(all(proof.get('critical_module_paths',{}).get(n) for n in ['numpy','numpy.random.mtrand','pandas','cv2']),'recorded_critical_binary_paths')
        elif dependency_profile=='sdk-inherit-v06':
            require(proof.get('dependency_profile')==dependency_profile,'abi_receipt_dependency_profile_matches')
            runs=proof.get('abi_runs',{})
            require(set(runs)==set(SDK_INHERIT_RUNS),'two_numpy_branches_required')
            for key,versions in SDK_INHERIT_RUNS.items():
                run=runs[key]
                require(run.get('status')=='PASS',key+'_abi_pass')
                require(run.get('submission_zip_sha256')==digest and run.get('payload_files_sha256')==files,key+'_receipt_exact_zip_and_payload')
                require(run.get('distribution_versions')==versions,key+'_runtime_full_numeric_combination')
                require(run.get('team_number')==615,key+'_sdk_reads_team615')
                require(run.get('numeric_random_pandas_cv_operations')=='PASS',key+'_real_numeric_operations')
                require(run.get('sdk_launcher_and_stats_import')=='PASS',key+'_sdk_import_chain')
                require(run.get('controller_factory_import')=='PASS' and run.get('all_payload_hashes_match') is True,key+'_actual_extracted_controller_import_and_hashes')
                require(all(run.get('critical_module_paths',{}).get(n) for n in ['numpy','numpy.random.mtrand','pandas','cv2']),key+'_critical_module_paths_recorded')
                plan=run.get('installation_dry_run',{})
                require(plan.get('status')=='PASS' and plan.get('planned_installations')==[],key+'_sdk_inheritance_requests_no_dependency_replacement')
        elif dependency_profile=='j17-portable-v07':
            require(proof.get('dependency_profile')==dependency_profile,'j17_receipt_profile_matches')
            require(proof.get('source_parent_zip_sha256')=='652b59edbfba68aa5b163b2cbdc904ebecdbe75927073e3a59168013e725a839','j17_tested_parent_bound')
            runs=proof.get('abi_runs',{})
            require({'numpy1','numpy2','clean_sdk'}<=set(runs),'j17_two_numpy_branches_and_full_sdk_stack')
            for key in ['numpy1','numpy2','clean_sdk']:
                run=runs[key]
                require(run.get('status')=='PASS',key+'_j17_abi_pass')
                require(run.get('submission_zip_sha256')==digest and run.get('payload_files_sha256')==files,key+'_j17_exact_zip_and_payload')
                versions=run.get('distribution_versions',{})
                expected=dict(SDK_INHERIT_RUNS[key],scipy='1.17.1') if key in SDK_INHERIT_RUNS else {'numpy':'2.4.6','pandas':'3.1.0','opencv-contrib-python':'5.0.0.93','scipy':'1.17.1'}
                require(versions==expected,key+'_j17_full_numeric_combination')
                require(run.get('team_number')==615,key+'_j17_sdk_integer615')
                require(run.get('numeric_random_pandas_cv_operations')=='PASS' and run.get('sdk_launcher_and_stats_import')=='PASS',key+'_j17_numeric_and_sdk_pass')
                require(run.get('controller_factory_import')=='PASS' and run.get('all_payload_hashes_match') is True,key+'_j17_actual_controller_and_hashes')
                require(run.get('solver_real_solve')=='PASS' and run.get('solver_no_license_and_import_block_test')=='PASS' and run.get('solver_test_variables',0)>2000,key+'_j17_real_license_free_solver')
                require(all(run.get('critical_module_paths',{}).get(n) for n in ['numpy','numpy.random.mtrand','pandas','cv2','scipy']),key+'_j17_binary_paths_recorded')
                plan=run.get('installation_dry_run',{})
                require(plan.get('status')=='PASS' and plan.get('planned_installations')==[],key+'_j17_install_requests_no_replacement')
            model=proof.get('model_equivalence',{})
            require(model.get('status')=='PASS' and model.get('submission_zip_sha256')==digest and model.get('payload_files_sha256')==files,'j17_model_proof_bound_to_actual_payload')
            require(model.get('independent_brute_cases',0)>=40 and model.get('gurobi_comparison_cases',0)>=40,'j17_independent_brute_and_parent_model_equivalence')
            native=proof.get('native_validation',{})
            require(native.get('status')=='PASS' and native.get('submission_zip_sha256')==digest and native.get('payload_files_sha256')==files,'j17_actual_native_validation_bound')
            require(native.get('pilot_gate')=='PASS' and native.get('five_maps_complete') is True and native.get('first_windows_raw_review')=='PASS' and native.get('native_failure') is False,'j17_pilot_and_five_maps_really_completed')
            if native.get('evaluation_resource_scope')=='EXPLICIT_USER_CPU_AND_LOAD_GATE_OVERRIDE':
                auth=native.get('direct_start_authorization',{})
                require(auth.get('human_request')=='直接启动测试' and auth.get('max_remaining_native_rounds')==10,'j17_high_load_run_explicit_human_scope')
                require(native.get('resource_matched_to_original_J17') is False,'j17_high_load_not_mislabelled_as_resource_matched')
                observed=native.get('direct_start_resource_receipt',{})
                require(observed.get('human_request')=='直接启动测试' and observed.get('applies_to')=='J17P_FIVE only; no later cohorts','j17_high_load_actual_resource_receipt')
        else:
            require(proof.get('dependency_profile')==dependency_profile,'v08_receipt_profile_matches')
            require(proof.get('source_parent_zip_sha256')==J17_REFERENCE_SHA256,'v08_original_j17_parent_bound')
            require(proof.get('all_other_payload_bytes_unchanged') is True,'v08_only_dependency_declaration_changed')
            runs=proof.get('abi_runs',{})
            require({'numpy1','numpy2','clean_sdk'}<=set(runs),'v08_three_complete_numeric_stacks')
            for key in ['numpy1','numpy2','clean_sdk']:
                run=runs[key]
                expected=dict(SDK_INHERIT_RUNS[key],gurobipy='13.0.1') if key in SDK_INHERIT_RUNS else {'numpy':'2.4.6','pandas':'3.1.0','opencv-contrib-python':'5.0.0.93','gurobipy':'13.0.1'}
                require(run.get('status')=='PASS' and run.get('distribution_versions')==expected,key+'_v08_numeric_and_gurobi_versions')
                require(run.get('submission_zip_sha256')==digest and run.get('payload_files_sha256')==files,key+'_v08_exact_zip_and_payload')
                require(run.get('team_number')==615 and run.get('all_payload_hashes_match') is True,key+'_v08_integer615_and_actual_source')
                require(run.get('numeric_random_pandas_cv_operations')=='PASS' and run.get('sdk_launcher_and_stats_import')=='PASS' and run.get('controller_factory_import')=='PASS',key+'_v08_real_numeric_and_sdk_entry')
                require(run.get('solver_real_solve')=='PASS' and run.get('solver_full_license_large_model')=='PASS' and run.get('solver_test_variables',0)>2000,key+'_v08_full_license_actual_large_solve')
                require(all(run.get('critical_module_paths',{}).get(n) for n in ['numpy','numpy.random.mtrand','pandas','cv2','gurobipy']),key+'_v08_critical_paths_recorded')
                plan=run.get('installation_dry_run',{})
                require(plan.get('status')=='PASS' and plan.get('planned_installations')==[],key+'_v08_no_dependency_replacement_in_reused_stacks')
            history=proof.get('native_history',{})
            require(history.get('status')=='PASS' and history.get('tested_source_parent_zip_sha256')==J17_REFERENCE_SHA256,'v08_original_five_map_history_bound')
            require(history.get('original_python_payload_sha256')=={n:h for n,h in files.items() if n.endswith('.py')},'v08_all_executed_python_sources_match_original_five_maps')
            require(history.get('first_windows_raw_review')=='PASS' and history.get('native_failure') is False,'v08_original_native_evidence_reviewed')
            license_scope=proof.get('license_deployment',{})
            require(license_scope.get('user_requested_licensed_variant') is True and license_scope.get('requires_external_full_license') is True,'v08_explicit_full_license_deployment_condition')
            require(license_scope.get('bundled_license_material') is False and license_scope.get('official_container_license_verified') is False,'v08_no_license_credentials_packaged_or_platform_claim')
            official=proof.get('official_static_check',{})
            require(official.get('status')=='PASS' and official.get('submission_zip_sha256')==digest==official.get('alias_sha256'),'v08_official_static_actual_zip_pass')
    result_status='STATIC_ONLY_PASS_NOT_RELEASED' if static_only else 'PASS_REQUIRES_EXTERNAL_GUROBI_LICENSE' if dependency_profile=='j17-gurobi-v08' else 'PASS'
    return {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':result_status,'zip':str(path),'sha256':digest,'dependency_profile':dependency_profile,'checks':checks,'official_container_verified':False,'external_full_gurobi_license_required':dependency_profile=='j17-gurobi-v08'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('zip',type=Path);p.add_argument('--abi-receipt',type=Path);p.add_argument('--static-only',action='store_true');p.add_argument('--dependency-profile',choices=['pinned','sdk-inherit-v06','j17-portable-v07','j17-gurobi-v08'],default='pinned');p.add_argument('--output',type=Path);a=p.parse_args()
    try:r=inspect_package(a.zip,a.abi_receipt,a.static_only,a.dependency_profile);code=0
    except Exception as e:r={'status':'FAIL','zip':str(a.zip),'error':str(e)};code=1
    if a.output:a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False));sys.exit(code)

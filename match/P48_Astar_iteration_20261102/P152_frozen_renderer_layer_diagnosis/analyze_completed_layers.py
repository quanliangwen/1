from pathlib import Path
import hashlib,json
F=Path(__file__).resolve().parent
dest=F/'LAYER_DIAGNOSIS_FIRST.json';assert not dest.exists()
r=json.loads((F/'RESULT_FIRST.json').read_text());raw=F/'RENDERER_LAYERS_FIRST.json';d=json.loads(raw.read_text())
pre=json.loads((F/'PREDECLARATION_FIRST.json').read_text());assert hashlib.sha256((F/'check_sdk_renderer_layers.py').read_bytes()).hexdigest()==pre['code_sha256']
assert r['status']=='PASS_FROZEN_RENDERER_LAYER_IDENTITY'and all(r['checks'].values())
base=json.loads((F.parent/'P142_profile_and_task_chain/BASELINE_FIRST.json').read_text())
assert d['rows']==base['rows']and d['map_results']==base['map_results']and len(d['renderer_layer_review'])==25
assert all(e['all_memory_arrays_identical']and e['full_matches_original_frozen_image']for e in d['layer_integrity'])
rows=[]
for owner in range(5):
    layers={e['layer']:e for e in d['renderer_layer_review']if e['owner']==owner}
    frame=layers['inferred_frame_actual'];full=layers['full_bearing_actual']
    assert abs(full['score']-100*(full['breakdown']['credit']-full['breakdown']['penalty']))<1e-8
    rows.append(dict(owner=owner,frame_map=frame['score'],full_map=full['score'],map_change=full['score']-frame['score'],
                     correct_credit_change_pp=100*(full['breakdown']['credit']-frame['breakdown']['credit']),
                     false_penalty_change_pp=100*(full['breakdown']['penalty']-frame['breakdown']['penalty']),
                     added_pixels=full['added_pixels_vs_previous'],removed_pixels=full['removed_pixels_vs_previous']))
out=dict(status='CONFIRMED_BEARING_ADDITION_DOMINATES_THIS_FROZEN_AUTHORED_MAP_LOSS',
         source_result_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),rows=rows,
         mean_map_change=sum(e['map_change']for e in rows)/5,
         actual_selected_owner=d['submission_records'][0]['owner'],actual_selected_map=d['coverage_evaluation']['actual_submitted_map'],
         original_controller_and_health_failure_unchanged=True,sdk_frames=779,native_rounds=0,
         conclusion='In this exact final own-memory state, most precision loss is caused by the final multi-bearing additions, not lack of wall observations or short-wall/frame additions.',
         limits=['Authored CROSS lacks the varied small-object geometry of all five official maps; do not remove the entire layer and assume a game gain.',
                 'A post-freeze rendering counterfactual does not measure the closed-loop effects of changing the layer also used for coverage values.',
                 'Do not stack this map hypothesis into user-requested P153 phase test.'])
dest.write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
note='''P152已结束并核验：779帧与原P142动作、位置、库存、地图、提交、任务/gate链全部一致；5机全部memory ndarray不变、full图等于原冻结图，八项身份检查通过。旧健康49失败保留，未获得新的性能或发布资格。
选中0号：实际frame层99.34904982，最终bearing层95.47034292，下降3.87870690地图pp；仅多命中2个墙面像素，却增加误绘penalty3.88758631pp。其他4机也同方向下降，见LAYER_DIAGNOSIS_FIRST。
这次实际冻结状态中，主要误绘增量来自多方向补图；不能据单一无小物体CROSS场景关掉整个层、宣称五图提分。P153新用户请求只测试单向投放阶段，不叠此地图规则。P152旧114360已经结束，不恢复或重启。
'''
(F/'完成分层诊断结论.txt').write_bytes(note.encode())
print(json.dumps(dict(status=out['status'],selected_owner=out['actual_selected_owner'],mean_map_change=out['mean_map_change'],owner0=rows[0]),ensure_ascii=False))

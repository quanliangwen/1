"""Exact score bounds from a binary erasure audit and public aggregate scoring.

No official truth grid, original image reconstruction, private state or rerun.
"""
from pathlib import Path
import hashlib
import json

F=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert not(F/'OUTPUT_EFFECT_BOUND_FIRST.json').exists()
review=read(F/'P145_A/MECHANISM_REVIEW.json')
assert read(F/'CAMPAIGN_CLIENT_REVIEW.json')['status']=='PASS'
selected=[e for e in review['all_audit_events']if e['sha256']==review['image_sha256']]
assert len(selected)==1
audit=selected[0]['audit']
assert audit['status']=='COMPLETE_FREE_DIRECTION_REFERENCE'and audit['parent_preserved']and audit['raw_positive_preserved']
parts=review['phase']['map_breakdown']
N=parts['surface_pixels']
missing=N-parts['wall_hits']
removed=audit['erased_pixels']
score=review['phase']['score_map']
assert abs(score-100*(parts['credit']-parts['penalty']))<1e-8
# Original credit can only decrease under erasure. Each removed false pixel
# had an independent charge in [0,1], weighted .2 / true surface size.
max_gain=20.*removed/N
max_loss=100.*min(removed,missing)/N
original_low=max(0.,score-max_gain)
original_high=min(100.,score+max_loss,100*(1-parts['penalty']))
full=review['score']
full_bounds=[full+.5*(original_low-score),full+.5*(original_high-score)]
out=dict(status='VERIFIED_FIXED_ITEM_SCORE_BOUNDS',selected_owner=selected[0]['owner'],
         surface_pixels=N,current_surface_hits=parts['wall_hits'],current_missing_surface=missing,erased_pixels=removed,
         filtered_map_score=score,max_map_gain_from_this_erasure=max_gain,max_map_loss_from_this_erasure=max_loss,
         possible_unfiltered_map_interval=[original_low,original_high],
         possible_unfiltered_full_interval_holding_other_public_items_fixed=full_bounds,
         unfiltered_cannot_reach_map96=original_high<96.,unfiltered_cannot_reach_full75=full_bounds[1]<75.,
         formulas=['S=100*(C-P), P=.2*sum(charge)/N, charge in [0,1].',
                   'For m erased pixels, delta=S_after-S_before in [-100*min(m,missing_after)/N,20*m/N].',
                   'P_before>=P_after and C_before<=1 imply S_before<=100*(1-P_after).'],
         source_map_scoring_sha256='68e44a3edcc04f7632584a7e9f726a003228aa50271eea2b90d73d669fd3ba56',
         mechanism_receipt_sha256=hashlib.sha256((F/'P145_A/MECHANISM_REVIEW.json').read_bytes()).hexdigest(),
         source_constraint='Frozen helper only zeros selected pixels; no new occupied pixels. Numeric bound assumes unchanged map dimensions and the frozen SDK score.',
         limitations=['Bounds do not determine whether this native filter helped or hurt the map.',
                     'Fixed-item full bounds are score arithmetic, not a simulated matched-seed counterfactual.',
                     'Not comparison with the earlier naturally randomized A-star episode.'],
         sdk_frames=0,native_rounds=0,original_map_or_truth_grid_loaded=False)
(F/'OUTPUT_EFFECT_BOUND_FIRST.json').write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps({k:out[k]for k in ['status','max_map_gain_from_this_erasure','max_map_loss_from_this_erasure','possible_unfiltered_map_interval','possible_unfiltered_full_interval_holding_other_public_items_fixed','unfiltered_cannot_reach_map96','unfiltered_cannot_reach_full75']}))

"""After the single complete five: compare and publish; never start/retry games."""
from pathlib import Path
import hashlib,importlib.util,json,urllib.parse,urllib.request
F=Path(__file__).resolve().parent
# Publication only: wait for the initial input commit to finish before using its worktree.
import time
publication_deadline=time.monotonic()+300
while not(F/"INPUTS_PUBLICATION_FIRST.json").exists():
    if time.monotonic()>=publication_deadline:raise TimeoutError("Initial GitHub input publication not verified")
    time.sleep(1)
spec=importlib.util.spec_from_file_location('publisher_common',F.parent/'publish_progress.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert not(F/'RESULT_PUBLICATION.json').exists()
review=read(F/'CAMPAIGN_CLIENT_REVIEW.json');assert review['status']=='PASS'and not review['native_failure']
G=F/'P159_C70_ASTAR_A';raw=read(G/'CLIENT_FIRST_RAW_REVIEW.json');matrix=read(G/'RESULT.json');binding=read(F/'INTERNAL_ZIP_BINDING.json')
assert raw['status']=='PASS'and matrix['complete']and matrix['payload_unchanged']and matrix['source_hashes']['red']==binding['payload_files']
result=review['result'];assert len(result['rows'])==5
old={r['map']:r for r in read(F/'BASELINE_REFERENCE.json')['rows']}
blue_old=read(F/'BASELINE_BLUE_REFERENCE.json')
rows=[]
for r in result['rows']:
    b=old[r['map']];p=r['phase'];blue=r['blue_public']
    assert abs(r['full']-(.5*p['score_map']+.2*p['score_wall']+.1*p['score_time']+r['layout_contribution']))<1e-6
    accepted=[a for a in r['cluster_model_audits']if a.get('accepted')]
    assert all(a['coverage_ratio']>=.7-1e-8 for a in accepted)
    rows.append(dict(map=r['map'],baseline_full=b['astar_full'],cluster_full=r['full'],delta=r['full']-b['astar_full'],
                     baseline_map=b['astar_map'],map_score=p['score_map'],baseline_wall=b['astar_wall'],wall_score=p['score_wall'],
                     baseline_time=b['astar_time'],time_score=p['score_time'],placed=r['placed'],expected=r['expected'],
                     red_steps=r['red_steps'],red_walltime=r['red_walltime'],red_wallhit=r['red_wallhit'],blue_wallhit=r['blue_wallhit'],
                     baseline_layout_contribution=b['astar_blue_difficulty_points'],layout_contribution=r['layout_contribution'],
                     baseline_blue_disposed=blue_old[r['map']]['disposed'],blue_disposed=blue['disposed'],blue_expected=blue['expected'],
                     baseline_blue_steps=blue_old[r['map']]['timestep'],baseline_blue_score=blue_old[r['map']]['blue_score'],blue_steps=blue['timestep'],blue_score=blue['blue_score'],
                     accepted_proposals=r['cluster_accepted'],objective_commit_checks=r['cluster_commits'],
                     actual_cluster_strict=r['max_actual_cluster']if accepted else None,
                     actual_cluster_with12=r['max_actual_cluster_with12']if accepted else None,
                     majority_executed=bool(accepted)and r['max_actual_cluster']>=6,
                     concentration=r['concentration'],issued_plan_chain=r['issued_plan_chain'],model_audits=r['cluster_model_audits'],
                     note='No accepted proposal means no tested cluster anchor; null is not zero physical bombs in all possible corners.'if not accepted else'Physical exported RED bombs compared to proposed corner disks.'))
mean=lambda key:sum(r[key]for r in rows)/5
summary=dict(status='COMPLETE_REVIEWED_CORNER_FIVE_MAP_OBSERVATION',baseline_mean=mean('baseline_full'),cluster_mean=mean('cluster_full'),mean_delta=mean('delta'),
             placed=sum(r['placed']for r in rows),expected=50,blue_mean=mean('blue_score'),baseline_blue_mean=mean('baseline_blue_score'),evaluation_valid=result['evaluation_valid'],audit_integrity=result['audit_integrity'],
             red_wall_hits=sum(r['red_wallhit']for r in rows),blue_wall_hits=sum(r['blue_wallhit']for r in rows),
             maps_with_accepted_proposals=sum(r['accepted_proposals']>0 for r in rows),maps_with_actual_majority=sum(r['majority_executed']for r in rows),
             weighted_mean_changes=dict(map_points=.5*(mean('map_score')-mean('baseline_map')),wall_points=.2*(mean('wall_score')-mean('baseline_wall')),
                                        time_points=.1*(mean('time_score')-mean('baseline_time')),blue_difficulty_points=mean('layout_contribution')-mean('baseline_layout_contribution')),
             rows=rows,comparison_scope='One explicit Map01-05 RED+original team006 BLUE group versus retained P48 A-star; same SDK/resources/limits, naturally different episodes, not paired causal proof.',
             goal_scope='Fixed initial10 quota6; current observed joint confirmed+reserved+suffix coverage >=70% same-call reference. Not a guarantee on actual official coverage or across replans.',
             official_submission_ready=False,automatic_B=False,ranking_promoted=False,game_rounds_added=10)
assert abs(sum(summary['weighted_mean_changes'].values())-summary['mean_delta'])<1e-6
(F/'FIVE_COMPARISON.json').write_bytes((json.dumps(summary,ensure_ascii=False,indent=2)+'\n').encode())
text=f'''# 角落集中布点：完整五图结果

原P48 A*留存均分 **{summary['baseline_mean']:.6f}**，角落集中方案 **{summary['cluster_mean']:.6f}**，观察差 **{summary['mean_delta']:+.6f}**；投放{summary['placed']}/50。RED/BLUE墙钟超时{summary['red_wall_hits']}/{summary['blue_wall_hits']}图。{summary['maps_with_accepted_proposals']}图实际生成被接受的集中方案，{summary['maps_with_actual_majority']}图最终至少6枚落入同一已选角落（严格半径）。

|地图|原总分|新总分|变化|地图分|覆盖分|时间分|投放|实际角落枚数|蓝队清除|蓝队步数|RED/BLUE超时|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
'''
for r in rows:
    n='未接受方案'if r['actual_cluster_strict']is None else str(r['actual_cluster_strict'])
    text+=f"|{r['map']}|{r['baseline_full']:.4f}|{r['cluster_full']:.4f}|{r['delta']:+.4f}|{r['map_score']:.4f}|{r['wall_score']:.4f}|{r['time_score']:.4f}|{r['placed']}/10|{n}|{r['blue_disposed']}/{r['blue_expected']}|{r['blue_steps']}|{r['red_wallhit']}/{r['blue_wallhit']}|\n"
text+='''
各组原始文件首次Windows不透明字节SHA及campaign检查完成，未反序列化NPZ/pickle、不读BLUE私有console；真实投放位置来自公开RED弹药JSON。实际半径=2倍爆炸半径，另在JSON报告+12px原到达容差的数量，不能混用来夸大集中。

70%是每次当前观测模型对条件剩余墙面价值的保护线；真实物理墙体覆盖可能跌得更多，也可能没有大簇可行。无接受方案不能称成功测试了集中布局。此时分数变化包含自然随机差异和计算开销，不能归因集中有效。不存在重复种子/标签救分或追加B组，未自动晋级或发布参赛包。

完整分项、蓝队变化、每次保护线拒绝/接受、实际坐标对应角落与权重分解见FIVE_COMPARISON.json。任何BLUE墙钟超时均明确标记，不拿资源超时宣称稳定增益。
'''
inputs={'FIVE_COMPARISON.json':(F/'FIVE_COMPARISON.json').read_bytes(),'RESULTS.md':text.encode(),
        'test_receipts.json':(json.dumps(dict(zip_sha256=binding['sha256'],first_raw_review=raw,entry=read(F/'ENTRY_ACTUAL_ZIP_FIRST.json'),payload_unchanged=matrix['payload_unchanged']),ensure_ascii=False,indent=2)+'\n').encode()}
from draw_layouts import draw_layouts
plot_inputs=draw_layouts(F,rows)
inputs.update(plot_inputs)
details='\n\n## 蓝队分数与加权细则\n\n|地图|地图×.5|墙体×.2|时间×.1|布局难度贡献|原蓝队得分|本轮蓝队得分|完整红分|\n|---|---:|---:|---:|---:|---:|---:|---:|\n'
for r in rows:
    details+=f"|{r['map']}|{.5*r['map_score']:.6f}|{.2*r['wall_score']:.6f}|{.1*r['time_score']:.6f}|{r['layout_contribution']:.6f}|{r['baseline_blue_score']:.6f}|{r['blue_score']:.6f}|{r['cluster_full']:.6f}|\n"
details+='\nBLUE得分来自原team006原SDK同轮公开评分；布局难度贡献采用冻结评测器原值。双队墙钟超时与步数耗尽必须区分；有墙钟超时的图保留分数但不用于稳定性能比较。完整均分是本组自然随机观察，不是同seed配对因果。\n'
inputs['RESULTS.md']+=details.encode()
images='\n\n## 公开布局与红队路线图\n\n底图均为红队预测，不是真图；编号只标记初始投放弹药，不表示蓝队最终未清除编号。\n\n'
for n in plot_inputs:images+='!['+n+']('+n+')\n\n'
inputs['RESULTS.md']+=images.encode()
root=c.WORK/c.TASK/F.name
assert c.git('status','--porcelain')==''
for n,data in inputs.items():(root/n).write_bytes(data)
checks={n:hashlib.sha256(data).hexdigest()for n,data in inputs.items()};name='RESULT_SHA256SUMS.json';data=(json.dumps(checks,indent=2)+'\n').encode();inputs[name]=data;(root/name).write_bytes(data)
c.git('add','--',c.TASK+'/'+F.name);c.git('commit','-m','Report full five-map corner-concentration experiment')
c.git('fetch','origin','main');c.git('rebase','origin/main');c.git('push','origin','HEAD:main')
commit=c.git('rev-parse','HEAD');opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));verified={}
for n,data in inputs.items():
    got=opener.open('https://raw.githubusercontent.com/quanliangwen/1/'+commit+'/'+urllib.parse.quote(c.TASK+'/'+F.name+'/'+n),timeout=45).read()
    assert hashlib.sha256(got).hexdigest()==hashlib.sha256(data).hexdigest(),n
    verified[n]=hashlib.sha256(got).hexdigest()
out=dict(status='PASS_REMOTE_RESULTS_AND_ALL_SHA256_VERIFIED',commit=commit,url='https://github.com/quanliangwen/1/blob/'+commit+'/'+c.TASK+'/'+F.name+'/RESULTS.md',summary=summary,sha256=verified)
(F/'RESULT_PUBLICATION.json').write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps(dict(status=out['status'],commit=commit,url=out['url'],mean=summary['cluster_mean'],delta=summary['mean_delta'])))

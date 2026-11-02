from pathlib import Path
import json,hashlib,zipfile,subprocess,sys,datetime
F=Path(__file__).resolve().parent;A=F/'audit';read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not(F/'DELIVERY_MANIFEST.json').exists();build=read(F/'BUILD.json');z=F/'team615_red_v09.zip';digest=sha(z);assert digest==build['submission_zip_sha256']
with zipfile.ZipFile(z)as a:files={n:hashlib.sha256(a.read(n)).hexdigest()for n in a.namelist()}
assert files==build['payload_files_sha256']
P=Path('E:/codex/PJ01_rule_refinement_20261101/P55_P48_five_score_validation_20261101');matrix=read(P/'P48_A/RESULT.json');raw=read(P/'P48_A/CLIENT_FIRST_RAW_REVIEW.json');client=read(P/'CAMPAIGN_CLIENT_REVIEW.json')
assert matrix['complete']and matrix['payload_unchanged']and matrix['source_hashes']['red']==files
assert raw['status']=='PASS'and client['status']=='PASS'and client['native_failure']is False
rows=client['result']['rows'];assert len(rows)==5 and all(not r['red_wallhit']and not r['blue_wallhit']for r in rows)and sum(r['placed']for r in rows)==50
runs={name:read(A/('ABI_'+name+'.json'))for name in ['numpy1','numpy2','native_main']}
assert all(r['status']=='PASS'and r['submission_zip_sha256']==digest and r['payload_files_sha256']==files for r in runs.values())
official=read(A/'OFFICIAL_STATIC_CHECK.json');assert official['status']=='PASS'and official['submission_zip_sha256']==digest==official['alias_sha256']
regression=read(A/'GUARD_REGRESSION_V3_AVAILABLE_REFERENCES.json');assert regression['status']=='PASS'and regression['old_profile_bodies_unchanged']
history=dict(status='PASS',tested_zip_sha256=digest,payload_files_sha256=files,maps=5,mean=client['result']['mean'],placed=50,expected=50,first_windows_raw_review='PASS',native_failure=False,red_wall_hits=0,blue_wall_hits=0,source_result_sha256=sha(P/'P48_A/RESULT.json'),source_first_review_sha256=sha(P/'P48_A/CLIENT_FIRST_RAW_REVIEW.json'),raw_archive_sha256=raw['archive_sha256'],no_raw_archive_reaudit=True,new_game_rounds=0,rows=[dict(map=r['map'],full=r['full'],map_score=r['phase']['score_map'],wall_score=r['phase']['score_wall'],time_score=r['phase']['score_exploration_trajectory'],placed=r['placed'])for r in rows])
receipt=dict(status='PASS',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),dependency_profile='p48-sdk-v09',submission_zip_sha256=digest,payload_files_sha256=files,team_number=615,abi_runs=runs,native_history=history,official_static_check=official,requires_Gurobi=False,official_container_verified=False,official_online_submission_performed=False,scope='Same tested complete P48 archive under new official filename; actual payload/algorithm bytes unchanged. Newly created isolated NumPy1/2 numerical stacks plus current restored SDK stack; auxiliary SDK dependencies shared read-only. Packaging/startup validation only; algorithm iteration and automation remain paused.')
(A/'RELEASE_ABI_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
cmd=[sys.executable,str(F.parent/'swarm-submission-guard/check_submission_zip.py'),str(z),'--abi-receipt',str(A/'RELEASE_ABI_RECEIPT.json'),'--dependency-profile','p48-sdk-v09','--output',str(A/'RELEASE_CHECK.json')]
p=subprocess.run(cmd,capture_output=True);(A/'FINAL_GUARD.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stdout+p.stderr
assert read(A/'RELEASE_CHECK.json')['status']=='PASS'
text='''P48比赛提交版本V09

上传文件：team615_red_v09.zip。P48_v09_source.zip仅供查阅源码，不上传源码包。
队号team_number为YAML整数615，队名AAA排雷大队及队员信息保持原样。
最终提交ZIP根目录直接含my_drone_eval.py、辅助源码、team_info.yml、req.txt和空image_ref.txt。无SDK、地图、评测数据、虚拟环境、二进制包或许可证；不使用Gurobi。

算法：保持完成五图测试的P48全部源码字节不变。P48以PJ01为底本，保留多机独立观测与消息建图、临时协调机分配墙面覆盖布点及各机路径执行；加入普通探索规划错峰和投放前过期机会模型刷新，继续用收益、时间损失与执行风险决定补扫或执行投放。它包含原有近似规划模块，不是整数规划或全局最优算法。未叠加之后未通过筛选的规则。

依赖准确为numpy>=1.24.4、opencv-contrib-python>=4.10.0.84，与本次实际测试包一致，不额外覆盖Pandas。不捆绑或在运行时安装数值库。本次实际ZIP已在新建NumPy1.26.4/Pandas2.2.3/OpenCV4.11.0.86、新建NumPy2.2.6/Pandas2.2.3/OpenCV4.11.0.86，以及现有SDK的NumPy1.26.4/Pandas3.0.6/OpenCV4.11.0.86三组合中验证真实mtrand、随机数、DataFrame和cv2运算、SDK Launcher/Stats、控制器入口、真实整数615及五机独立构造。Gurobi导入被主动阻断仍通过，安装预演均无替换项。SDK其他依赖为现有恢复环境只读共享，完整路径详audit/RELEASE_ABI_RECEIPT.json；不将其伪称官方镜像或完全独立重装的SDK。
官方静态检查器使用旧preliminary命名规则，因此用与最终ZIP逐字节相同的team615_preliminary.zip审计内容；正式推荐文件仍按用户规范命名team615_red_v09.zip。实际ZIP另外通过新版发布检查器p48-sdk-v09的数字队号、平铺、依赖、源码、ABI与成绩绑定检查。

完整五图历史均分72.6026760546，投放50/50，双方无墙钟超时；与本包全41项payload及整个ZIP字节绑定。本次只完成打包与兼容/启动验证，没有重跑比赛，没有恢复算法迭代或自动调度。自然随机成绩不保证下一局相同。
官网基础镜像和官网在线评测尚未验证，不能承诺官网损坏或后续覆盖依赖时绝不发生NumPy ABI错误；此次检查不沿用旧版本回执。

逐图完整红分：
'''
for r in history['rows']:text+=f"{r['map']}: {r['full']:.8f}；投放{r['placed']}/10\n"
text+='\n提交ZIP SHA256：'+digest+'\n'
(F/'提交说明与验证结果.txt').write_text(text,encoding='utf8')
out=dict(status='PASS_READY_FOR_USER_UPLOAD_NOT_OFFICIAL_PLATFORM_VERIFIED',submission_zip=str(z),source_zip=str(F/'P48_v09_source.zip'),sha256=digest,profile='p48-sdk-v09',payload_files=files,history=history,requires_Gurobi=False,new_game_rounds=0,algorithm_iteration_remains_paused=True,official_online_submission_performed=False)
(F/'DELIVERY_MANIFEST.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');(A/'STATUS.json').write_text(json.dumps(dict(status=out['status']),indent=2)+'\n')
print(json.dumps(dict(status=out['status'],sha256=digest,mean=history['mean'],placed=history['placed'])))

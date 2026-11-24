from pathlib import Path
import csv,hashlib,json,shutil,xml.etree.ElementTree as ET,zipfile
R=Path(__file__).resolve().parent;E=R/'evidence';D=R/'delivery'
A=json.loads((E/'INDEPENDENT_AUDIT_STATISTICS.json').read_text());receipt=json.loads((R/'COLLECTION_RECEIPT.json').read_text())
assert A['terminal']==A['valid']==180 and A['variants_checked']==540 and not A['global_errors']
assert A['completed']['max_active_observed']==60 and A['new_probability_evaluations']==0
archive=R/'COMPACT_EVIDENCE_FULL.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['sha256']
verified=0
for p in (E/'outcomes').glob('*.json'):
    o=json.loads(p.read_text())
    for name,item in o['output_files'].items():
        f=E/'runs'/o['identity']/name
        assert f.stat().st_size==item['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256']
        verified+=1
assert verified==1620
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
X=D/'修正后S10与椭球_三大算例30次_60并行_对比结果.xlsx'
with zipfile.ZipFile(X) as z:
    sheets=[ET.fromstring(z.read('xl/worksheets/sheet%d.xml'%i)) for i in [1,2]]
    assert not [c for sheet in sheets for c in sheet.findall('.//s:c',ns) if c.attrib.get('t')=='e']
    summary={c.attrib['r']:c for c in sheets[0].findall('.//s:c',ns)};raw={c.attrib['r']:c for c in sheets[1].findall('.//s:c',ns)}
    def check(cell,expected):
        value=cell.find('s:v',ns) if cell is not None else None
        if expected is None:assert value is None or value.text in ['',None]
        else:assert value is not None and abs(float(value.text)-expected)<1e-10
    for i,s in enumerate(A['case_summaries'],9):
        for col,key in [('E','valid'),('F','best'),('G','avg'),('H','std'),('I','runtime_mean_seconds'),('J','runtime_std_seconds')]:check(summary.get(f'{col}{i}'),s[key])
    for i,c in enumerate(A['comparisons']):
        row=27+i;check(summary.get('C'+str(row)),c['mean_difference']);check(summary.get('D'+str(row)),c['relative_mean_difference'])
        check(summary.get('I'+str(row)),A['case_summaries'][2*i+1]['runtime_mean_seconds']/A['case_summaries'][2*i]['runtime_mean_seconds'])
    for i,r in enumerate(A['runs'],2):
        check(raw.get(f'G{i}'),int(r['valid']))
        for col,key in [('H','cost'),('I','LSS_probability'),('J','process_wall_seconds'),('K','search_seconds')]:check(raw.get(f'{col}{i}'),r[key])
shutil.copyfile(archive,D/'180次_LSS验收_完整紧凑证据.tar.gz')
for name in ['INDEPENDENT_AUDIT_STATISTICS.json','PROTOCOL.json','LAUNCH.json','COMPLETED.json']:
    shutil.copyfile(E/name,D/name)
for name,rows in [('case_summaries.csv',A['case_summaries']),('paired_comparisons.csv',A['comparisons']),('runs.csv',A['runs'])]:
    with (D/name).open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader()
        writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()} for row in rows)
(D/'scripts').mkdir(exist_ok=True)
for name in ['controller.py','audit_remote.py','prepare.py','collect.py','collect_remote.py','build_report.mjs','finalize_delivery.py']:
    shutil.copyfile(R/name,D/'scripts'/name)
lines=['修正后S10与椭球γ=2.4：三大算例各30次，60并行，对比统计','',
'结论：180次全部自然结束，180/180通过本批独立LSS验收，540个输出变体逐项匹配同一方案最后一次LSS概率且均>=.99。',
'LAB50：best/avg/std完全相同；椭球完整运行均时646.412秒，S10为347.910秒。',
'APP30：best相同；椭球avg高0.038975（约0.0201%），std也略高；均值差未显著，Holm p=.6875。',
'APP50：椭球best和avg均更高，avg高0.424996（约0.1319%），Holm p=.00003；两版完整运行均时接近。椭球std=0，但其主搜索没有改善自身初始化，不能把固定于较高成本解当作综合改进。',
'本批没有观察到椭球降低平均成本；不据此声称所有算例或所有椭球方法无用。未自动扩展全40例。',
'','成本与完整运行时间（样本std分母29）',
'编号 | 算例 | 容量 | 版本 | 有效/30 | best | avg | std | 完整运行均时(s) | 完整运行std(s) | 搜索均时(s)']
for s in A['case_summaries']:
    lines.append(f"{s['case_index']} | {s['instance']} | {s['capacity']} | {s['arm']} | {s['valid']}/30 | {s['best']:.10f} | {s['avg']:.10f} | {s['std']:.10f} | {s['runtime_mean_seconds']:.6f} | {s['runtime_std_seconds']:.6f} | {s['search_mean_seconds']:.6f}")
lines+=['','同seed配对比较：候选椭球减去原S10，负数为成本改善','编号 | 均值差 | 相对均值差 | 方向 | 成本原始p | 成本Holm3 p | 有效率Holm3 p']
for c in A['comparisons']:lines.append(f"{c['case_index']} | {c['mean_difference']:.10f} | {c['relative_mean_difference']:.10f} | {c['direction']} | {c['cost_p_raw']:.8f} | {c['cost_p_holm3']:.8f} | {c['validity_p_holm3']:.8f}")
lines+=['','执行及验收口径',
'北京时间2026-11-24 10:36:19启动，11:08:32全部自然结束；控制器总历时1933.018秒（32分13秒），最高60并行，0次资源保护终止，无失败身份、无补跑。',
'固定编号19 LAB50 T63、35 APP30 T58、39 APP50 T91；每版每例30次；配对seed960001—960030。各次独立自生成起点，不读旧解或其他重复结果。',
'两版同一个修正后二进制，Gurobi11.0.3，每求解器1线程；S10为frontier_mitm，椭球为ellipsoid_oa，γ=2.4、每查询5秒。没有混入修正前旧批数据。',
'最终仅以LSS>=.99验收，抽样索引0—499。原始经验样本证书仅保留为算法内部搜索机制，未额外作为统计验收门槛。没有计算、读取或补算生成分布真实概率。',
'独立核验只读既有记录：身份/种子、输入和源码SHA、搜索预算、结构与成本、完整LSS调用及最终过滤trace、全部变体与主CSV。没有再次调用求解器或概率评价器。',
f'完整trace中共保留最终过滤未通过的候选记录{sum(s["final_LSS_rejected_candidates"] for s in A["case_summaries"])}个。这是候选级负观测，不代表失败运行；最终输出均通过LSS。',
'正式avg/std要求30次均有效；本批六组全部满足。best为本组有效输出的观测最低成本，未宣称全局最优。',
'完整运行时间为控制器观测的进程墙钟，包含启动、加载、搜索、LSS与保存，不含排队；轮询及收集存在小量退出发现延迟。',
'搜索时间使用worker记录的原搜索时钟，600秒为搜索上限、45秒共同预留；LSS后处理另计。因此总运行时间可大于600秒，不截断。',
'时间对比仅作描述性统计。不同负载/CPU版本、旧时间定义的结果不能直接混算；本批60并行同批比较，未对时间差另加显著性门槛。',
'成本配对均值符号翻转检验：非零差<=20精确枚举，否则99999次随机符号+观测项，固定seed20261124+算例编号，3项Holm校正；有效率另做精确McNemar/Holm3。未显著不等于等效。',
'完整成本用于统计，仅展示值四舍五入。运行时间与成本std均为样本标准差ddof1。',
'','证据与源码',
f'下载证据包的{verified}个原始输出已逐文件SHA256与字节数验证；含全部CSV及LSS trace，无原始大数据数组或求解器许可证。',
'Excel的6组统计、180条明细、9个差值/比例公式及缓存值均核对通过；所有540个输出变体匹配其最后一次LSS观测。',
'修正源码：https://github.com/quanliangwen/1/tree/'+A['source_commit']+'/CCMCKP/S10_EGS_LSS_fix_20261124/source',
'协议SHA256：'+A['protocol_sha256'],'证据包SHA256：'+receipt['sha256']]
(D/'三大算例_LSS统一验收_对比结论.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
files=[p for p in D.rglob('*') if p.is_file() and p.name!='CHECKSUMS_SHA256.json' and not p.name.endswith('.inspect.ndjson')]
manifest={p.relative_to(D).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files}
(D/'CHECKSUMS_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'DELIVERY_LOCAL_VERIFIED.json').write_text(json.dumps({'status':'PASS','all180_LSS_valid':True,'all540_variants_valid':True,'output_files_sha_verified':verified,'xlsx_6groups_180rows_9formulas_verified':True,'files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','outputs_verified':verified,'all180_LSS_valid':True,'payload_files':len(manifest)+1,'xlsx_sha256':manifest[X.name]['sha256']},ensure_ascii=False))

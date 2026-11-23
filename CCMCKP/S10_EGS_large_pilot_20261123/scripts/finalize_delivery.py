from pathlib import Path
import csv,hashlib,json,shutil,tarfile,xml.etree.ElementTree as ET,zipfile
R=Path(__file__).resolve().parent;E=R/'evidence';D=R/'delivery'
A=json.loads((E/'INDEPENDENT_AUDIT_STATISTICS.json').read_text())
B=json.loads((E/'OBSERVED_OUTPUT_DIAGNOSTICS.json').read_text())
assert B['independent_audit_sha256']==hashlib.sha256((E/'INDEPENDENT_AUDIT_STATISTICS.json').read_bytes()).hexdigest()
observed={r['identity']:r for r in B['runs']}
assert A['terminal']==270
receipt=json.loads((R/'COLLECTION_RECEIPT.json').read_text())
archive=R/'COMPACT_EVIDENCE_FULL.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['sha256']
verified=0
for p in (E/'outcomes').glob('*.json'):
    record=json.loads(p.read_text())
    for name,expected in record['output_files'].items():
        f=E/'runs'/record['identity']/name
        assert f.stat().st_size==expected['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==expected['sha256']
        verified+=1
X=D/'EGS_三大算例_三版本30次_统计结果.xlsx'
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(X) as z:
    sheets=[ET.fromstring(z.read('xl/worksheets/sheet%d.xml'%n)) for n in (1,2)]
    assert not [c for sheet in sheets for c in sheet.findall('.//s:c',ns) if c.attrib.get('t')=='e']
    summary={c.attrib['r']:c for c in sheets[0].findall('.//s:c',ns)}
    raw={c.attrib['r']:c for c in sheets[1].findall('.//s:c',ns)}
    def close(c,expected):
        value=c.find('s:v',ns) if c is not None else None
        if expected is None:assert value is None or value.text in ['',None]
        else:assert value is not None and abs(float(value.text)-expected)<1e-10
    for i,s in enumerate(A['case_summaries'],9):
        for col,key in [('E','valid'),('F','best'),('G','avg'),('H','sample_std'),('I','cv')]:close(summary.get(f'{col}{i}'),s[key])
    for i,r in enumerate(A['runs'],2):
        close(raw.get(f'G{i}'),int(r['valid']))
        for col,key in [('H','cost'),('L','process_wall_seconds')]:close(raw.get(f'{col}{i}'),r[key])
        o=observed[r['identity']]
        for col,key in [('I','reported_final_lss_probability'),('J','reported_real_probability'),('K','observed_search_seconds'),('M','observed_final_selection_first_raw_accept_seconds'),('Z','reported_output_cost')]:close(raw.get(f'{col}{i}'),o[key])
shutil.copyfile(archive,D/'EGS_大算例270次_完整紧凑证据.tar.gz')
for name in ['INDEPENDENT_AUDIT_STATISTICS.json','OBSERVED_OUTPUT_DIAGNOSTICS.json','PROTOCOL.json','COMPLETED.json','LAUNCH.json','AUDIT_READER_CHECKS.json','AUDIT_TOOLCHAIN.json']:
    shutil.copyfile(E/name,D/name)
for filename,rows in [('case_summaries.csv',A['case_summaries']),('paired_comparisons.csv',A['comparisons']),('runs.csv',A['runs']),('reported_output_diagnostics.csv',B['runs'])]:
    with (D/filename).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader()
        writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows)
(D/'scripts').mkdir(exist_ok=True)
for name in ['controller.py','audit_remote.py','audit_count_helper.cpp','observed_diagnostics_remote.py','monitor_remote.py','collect_remote.py','test_independent_reader.py','prepare_reader_helper.py','build_report.mjs','finalize_delivery.py']:
    shutil.copyfile(R/name,D/'scripts'/name)
fmt=lambda x:'null（不足30次有效）' if x is None else f'{x:.10f}'
lines=['EGS椭球引导搜索：三个大算例独立试点','',
'核心结论：本批未形成椭球方案同时改善成本、波动与速度的证据，未扩展全40例。',
'LAB50：三版30/30有效，best=avg=197.9864543988，std=0；原S10搜索231.576秒，EGS_2p4为552.693秒。成本无改善且搜索耗时增加。',
'APP30：原S10/EGS_2p4/EGS_0有效18/21/18次，全部不足30；官方avg/std为空，不判成本胜负。',
'APP50：原S10有效15/30，两个EGS均30/30；有效率配对Holm p=0.0005493164。两个EGS的avg=322.6330496141、std=0，彼此没有成本差异。',
'APP50两个EGS主搜索均未改善自身初始化，不能把该例有效率改善全部归功于椭球风险项；gamma0同样达成。',
'全部270次主输出的原程序真实概率报告均低于.99；因此不得称为满足真实分布约束的改进版本。',
'统计口径：222/270通过冻结原经验样本证书与最终LSS检查；其余48次进程虽rc0，最终LSS值仍<.99，无资源失败、不补跑。',
'',
f"一、完成与有效性：270次终末，原协议独立有效{A['independent_valid']}/270，global_errors={A['global_errors']}",
'三版本：原S10_MITM；EGS_2p4（椭球代理评分gamma=2.4引导OA）；EGS_0（相同搜索gamma=0）。',
'编号19 LAB_50_10_500_ T63；35 APP_30_10_500_ T58；39 APP_50_10_500_ T91。预先固定，不按结果挑案例。',
'每例每版本30次，共270；登记seed960001—960030。每次只从原始数据自生成起点，不读历史解或其他重复结果。',
'算法、评价、输入、约束均为此前交付冻结源码；本轮仅扩大测试规模，不调参，不补跑普通失败。',
'最终输出固定取RESULT主输出/原LSS第1变体；椭球不作为最终约束。',
'','二、成本结果（未四舍五入值用于统计；展示保留10位）',
'编号 | 版本 | 有效/30 | best | avg | sample_std | CV']
for s in A['case_summaries']:lines.append(f"{s['case_index']} | {s['arm']} | {s['valid']}/30 | {fmt(s['best'])} | {fmt(s['avg'])} | {fmt(s['sample_std'])} | {fmt(s['cv'])}")
lines += ['','三、配对比较','编号 | 候选 | 参照 | 完整配对 | 均值差 | 相对均值差 | 方向 | 成本Holm p | 有效率Holm p']
for c in A['comparisons']:lines.append(f"{c['case_index']} | {c['candidate']} | {c['reference']} | {c['complete_pairs']} | {fmt(c['mean_difference'])} | {fmt(c['relative_mean_difference'])} | {c['direction']} | {fmt(c['p_mean_holm'])} | {fmt(c['p_validity_holm'])}")
lines += ['','四、时间与主搜索贡献','编号 | 版本 | 最终解首次原始接受均时 | best命中数 | best条件平均时间 | 搜索均时 | 进程总均时 | EGS新增接受总数 | EGS改善总数']
for s in A['case_summaries']:
    new=sum(r['egs_new_acceptances'] for r in A['runs'] if r['case_index']==s['case_index'] and r['arm']==s['arm'])
    lines.append(f"{s['case_index']} | {s['arm']} | {fmt(s['mean_final_selection_first_raw_accept_seconds'])} | {s['best_hits']} | {fmt(s['mean_raw_accept_seconds_conditional_on_best'])} | {fmt(s['mean_search_seconds'])} | {fmt(s['mean_process_wall_seconds'])} | {new} | {s['total_egs_improvements']}")
lines += ['','五、真实概率报告与失败限制',
'原口径独立有效不是“真分布保证”：仅表示身份、来源/全部输出SHA、时钟、原始经验样本计数证书、选择成本及原LSS通过。',
'原程序真实概率报告仍为报告项，未追加成新验收标准。低于0.99的运行单列，不按该报告挑变体或重新运行。']
for s in A['case_summaries']:lines.append(f"{s['case_index']} {s['arm']}：真实P报告均值={fmt(s['mean_reported_realP'])}，>=.99的有效运行{s['reported_realP_ge99_count']}/{s['valid']}。")
lines += ['以下为全部30次原输出的真实概率报告，包含原验收未通过者，仅为观测诊断：']
for g in B['groups']:lines.append(f"{g['case_index']} {g['arm']}：全30次真实P均报告={g['all_mean_reported_realP']:.10f}，>=.99的报告{g['all_reported_realP_ge99_count']}/30，最终LSS<.99者{g['reported_lss_below99_count']}/30。")
failures=[dict({k:r.get(k) for k in ['identity','rc','termination_reason','errors','failure_detail']},diagnosis=observed[r['identity']]['diagnosis'],reported_lss_p=observed[r['identity']]['reported_final_lss_probability'],reported_output_cost_diagnostic_only=observed[r['identity']]['reported_output_cost']) for r in A['runs'] if not r['valid']]
lines += ['失败/无效记录：'+json.dumps(failures,ensure_ascii=False),
'不足30次独立有效的组，官方avg/std留空；valid-only均值仅诊断，不据缺失组宣称成本胜负；失败不赋假成本。',
'','六、计时与统计口径',
'每次搜索预算600秒，原程序共同45秒余量；加载与搜索时钟沿用现有代码，LSS/真实概率报告在搜索时钟后执行。',
'整进程保护3600秒，仅给大算例原报告阶段留足时间，不扩展600秒搜索；首重复按原程序报告top10，耗时可能更长。',
'最多12并行，单任务6GiB预留、5GiB可用内存余量、极低2GiB保护；同批Gurobi11.0.3，不混用历史Gurobi13成绩。',
'搜索均时与整进程均时分开；后者包含后续报告及进程调度。不能将不同计时定义的旧Time直接横比。',
'工作簿物理搜索/进程耗时与日志贡献取全部30次原观测，含最终LSS未通过者；质量不完整时不据此判同等有效输出下的加速。正式成本统计仍仅按原独立有效性判定。',
'最终选择首次原始接受：最终LSS输出同一选择首次获得原始证书的时刻，非首次LSS准入（本代码未记录）。',
'best条件均时仅统计成本与本组30次best相差<=1e-8的有效运行；best不等于已证明全局最优。',
'各算法自己的best成本可能不同，不能把best条件时间当作达到同一目标成本的速度比较。',
'原LSS源码在入队接受后又复检并覆盖概率字段，主输出仍取成本队首，没有按新的最终复检概率再次过滤。本轮保留原源码行为，故rc0不等于最终LSS>=.99。48次在独立统计时判无效；这与真实概率报告270次均<.99是两个不同现象。',
'官方样本std分母n-1=29；成本优平劣采用冻结容差1e-8；统计检验用完整成本，同seed配对。',
'三对比×三例共9项均值符号翻转检验，Holm校正；<=20非零差精确枚举，否则99999次随机符号+观测项，固定统计seed。',
'失败有效率另做配对精确McNemar及独立9项Holm校正。未显著不代表等效或无用。',
'EGS主搜索新增接受/改善与共同初始化区分；仅三例，不宣称全40例提升；没有自动扩展全40例。',
'工作簿另列全30次初始化与原始搜索最终成本日志诊断，不冒充最终LSS正式avg。逐次记录保留全部原输出成本与概率，包括48个无效输出。',
'','七、复核与来源',
f'已对下载证据的{verified}个不可变输出逐文件SHA256与字节数复核；证据包不含原始大数组/SDK/许可证。',
'独立Python读者不导入搜索/证书写者；用Fraction量化及单独GMP算术读者重建整数计数。读者自身50项有限枚举核对通过，无额外原生MC。',
'冻结源码：https://github.com/quanliangwen/1/tree/4fadf036407a938aeab96412962f53199428ed47/CCMCKP/S10_EGS_OA_20261123/source',
'协议SHA256：'+A['protocol_sha256'],'证据包SHA256：'+receipt['sha256']]
(D/'三个大算例测试结论.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
files=[p for p in D.rglob('*') if p.is_file() and not p.name.endswith('.inspect.ndjson') and p.name!='CHECKSUMS_SHA256.json']
manifest={p.relative_to(D).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files}
(D/'CHECKSUMS_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'DELIVERY_LOCAL_VERIFIED.json').write_text(json.dumps({'status':'PASS','terminal':A['terminal'],'independent_valid':A['independent_valid'],'output_files_sha_verified':verified,'xlsx_270_rows_and_9_groups_verified':True,'files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','terminal':A['terminal'],'valid':A['independent_valid'],'output_files_verified':verified,'delivery_files':len(manifest)+1}))

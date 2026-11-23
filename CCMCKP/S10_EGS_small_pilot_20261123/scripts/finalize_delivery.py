from pathlib import Path
import csv,hashlib,json,shutil,tarfile,zipfile,xml.etree.ElementTree as ET

R=Path(__file__).resolve().parent
D=R/'delivery'
archive=R/'COMPACT_EVIDENCE_FULL.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='dcd9925dedcad3619fb026c3bc648dfce72a1ab86de487f3739681f602d479cd'
with tarfile.open(archive) as tar:
    assert all(not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in tar.getmembers())
    tar.extractall(R/'evidence_full',filter='data')
E=R/'evidence_full'
verified_files=0
for p in (E/'outcomes').glob('*.json'):
    record=json.loads(p.read_text())
    for name,v in record['output_files'].items():
        f=E/'runs'/record['identity']/name
        assert f.stat().st_size==v['bytes']
        assert hashlib.sha256(f.read_bytes()).hexdigest()==v['sha256']
        verified_files+=1
assert verified_files==2430
A=json.loads((E/'INDEPENDENT_AUDIT_STATISTICS.json').read_text())
assert A['terminal']==A['independent_valid']==270 and not A['global_errors']
assert all(s['sample_std']==0 and s['total_egs_improvements']==0 for s in A['case_summaries'])
assert all(c['p_mean_holm']==1 for c in A['comparisons'])
X=D/'EGS_三小算例_三版本30次_统计结果.xlsx'
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(X) as z:
    roots=[ET.fromstring(z.read('xl/worksheets/sheet%d.xml'%n)) for n in (1,2)]
    assert not [c for root in roots for c in root.findall('.//s:c',ns) if c.attrib.get('t')=='e']
    def cells(root):return {c.attrib['r']:c for c in root.findall('.//s:c',ns)}
    s,raw=map(cells,roots)
    def number(c):return float(c.find('s:v',ns).text)
    for i,g in enumerate(A['case_summaries'],9):
        assert abs(number(s[f'E{i}'])-g['best'])<1e-12
        assert abs(number(s[f'F{i}'])-g['avg'])<1e-12
        assert number(s[f'G{i}'])==g['sample_std']
    for i,r in enumerate(A['runs'],2):
        assert number(raw[f'G{i}'])==1
        for col,key in [('H','cost'),('I','lss_probability'),('J','reported_real_probability'),('K','search_seconds'),('L','process_wall_seconds'),('M','final_selection_first_raw_accept_seconds')]:
            assert abs(number(raw[f'{col}{i}'])-r[key])<1e-11
shutil.copyfile(archive,D/'EGS_270次_完整紧凑证据.tar.gz')
shutil.copyfile(E/'INDEPENDENT_AUDIT_STATISTICS.json',D/'INDEPENDENT_AUDIT_STATISTICS.json')
shutil.copyfile(E/'PROTOCOL.json',D/'PROTOCOL.json')
for filename,rows in [('case_summaries.csv',A['case_summaries']),('paired_comparisons.csv',A['comparisons']),('runs.csv',A['runs'])]:
    with (D/filename).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows)
(D/'scripts').mkdir(exist_ok=True)
for name in ['controller.py','audit_remote.py','monitor_remote.py','collect_remote.py','build_report.mjs','finalize_delivery.py']:
    shutil.copyfile(R/name,D/'scripts'/name)
lines=['EGS椭球引导搜索：三小算例试点结果（2026-11-23）','',
'一、结论','270次全部自然终末，原协议独立核验270/270；source/input/binary/controller pins不变，无资源终止。',
'三版本在三个算例的30次输出成本完全相同，样本std全部为0，9项配对成本检验Holm p全部为1。',
'EGS_2p4及EGS_0主搜索阶段均未新增原始证书接受解，也未改善初始最好成本。原S10搜索更快。',
'这批小算例未显示椭球引导的成本、稳定性或速度收益；未扩展全部40例。不能据此断言大算例一定无用或三算法等效。',
'','二、三版本与运行设置',
'S10_MITM：上传S10原源码重新编译，保持原搜索与所有评价不变。',
'EGS_2p4：新椭球代理评分mu*x+2.4*sqrt(sum(v_j*x_j))引导OA搜索；椭球不作为最终可行性约束。',
'EGS_0：相同EGS搜索，gamma=0，用于区分搜索框架与风险惩罚的作用。',
'预先固定编号1、3、21，两个LAB及一个APP，3—4组、每组5项；每算例每版30次，seed960001—960030。',
'全部自生成起点，未读取历史解或其他重复结果。每次搜索上限600秒；原S10保留45秒余量。',
'原LSS及真实概率报告在搜索时钟后执行，未将原程序改为端到端600秒。进程总时间另列。',
'同批原生Gurobi11.0.3，最多12并行、按6GiB/worker预留并保留5GiB可用内存余量；未混用历史Gurobi13数据。',
'北京时间2026-11-23 23:22:11启动，23:26:22全270次结束，控制器自然退出、无残留worker。',
'','三、各版本结果（best和avg相同；std为样本标准差）',
'编号 | 算例 | 版本 | 有效/30 | best | avg | std | 最终解首次原始接受均时(s) | 搜索均时(s) | 进程总均时(s)']
for s in A['case_summaries']:
    lines.append(f"{s['case_index']} | {s['instance']} | {s['arm']} | {s['valid']}/30 | {s['best']:.10f} | {s['avg']:.10f} | {s['sample_std']:.10f} | {s['mean_final_selection_first_raw_accept_seconds']:.6f} | {s['mean_search_seconds']:.6f} | {s['mean_process_wall_seconds']:.6f}")
lines += ['', '四、必须披露的概率差异',
'LAB_3_5_30_：三臂主输出原LSS概率0.9994814815，真实概率报告0.9997518。',
'LAB_4_5_30_：三臂主输出原LSS概率0.9999975309，真实概率报告0.9999844。',
'APP_3_5_30_：三臂主输出原LSS概率0.9924814815，但真实概率报告0.9651546，90/90次该报告低于0.99。',
'独立核验通过仅指原协议：身份、时钟、成本、选择、原始经验样本整数计数证书及原LSS接受规则通过。',
'真实概率报告仍按原程序报告，未在本次试验追加成新门槛，不能将270/270称为真实概率约束全部达到0.99。',
'经验样本验收与真实概率报告存在差距，本试点不能声称真分布可行性保证，也不能声称严格DRO覆盖保证。',
'','五、统计与时间定义',
'最终结果固定取RESULT主输出/原LSS第1变体；未按事后真实概率或变体选择最好结果。',
'官方avg及样本std仅30/30全部独立有效时填列；ddof=1；失败没有假成本、没有补跑。',
'达到最好解时间：最终输出同一选择首次获得原始证书的时间，不是首次LSS入选时间（当前代码未记录后者）。',
'best命中时间是命中该组30次最低成本的条件均值，容差1e-8。本试点各组30/30命中，故与上述时间相同。',
'搜索时间包含初始化和主搜索；进程时间还含LSS和原真实概率报告，两个时间不得混用。',
'每例三对比：EGS_2p4-S10、EGS_0-S10、EGS_2p4-EGS_0；共9项同seed均值符号翻转检验，Holm校正。',
'全部成本差为0，所以原始p和Holm p均为1。有效率配对精确McNemar另做9项Holm，全部p=1。',
'没有全局最优性证明；三个小算例缺少成本差异，无法验证原先大算例avg差、波动大的问题。',
'计时在共同并发环境下获得，包含操作系统调度影响；本报告不将初始化计时微差认定为算法收益。',
'','六、可复核文件与源码',
'工作簿含9组best/avg/std/时间、9配对比较、270条逐次明细及口径说明。',
'完整紧凑证据包包含全部270个outcomes与2430个原始输出文件（含原CSV）、终末/启动记录、协议与控制器日志。',
'已对下载证据的2430个输出逐文件SHA256及字节数核验；没有复制原始大数组、求解器SDK或许可证。',
'独立读者audit_remote.py不导入搜索/证书写者；Fraction/整数卷积重算全部接受候选的概率计数。',
'对应冻结源码：https://github.com/quanliangwen/1/tree/4fadf036407a938aeab96412962f53199428ed47/CCMCKP/S10_EGS_OA_20261123/source',
'协议SHA256：627224b5c1293b92ccb902bcd94d815c2db9126b5d808e2e83bb9556039b365e',
'完整紧凑证据SHA256：dcd9925dedcad3619fb026c3bc648dfce72a1ab86de487f3739681f602d479cd']
# Read exact LSS mean from audited records rather than transcribing rounded values.
for i,line in enumerate(lines):
    if line.startswith('LAB_4_5_30_：'):
        value=next(r['lss_probability'] for r in A['runs'] if r['case_index']==3)
        lines[i]=f'LAB_4_5_30_：三臂主输出原LSS概率{value:.10f}，真实概率报告0.9999844。'
(D/'小算例测试结论.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
files=[p for p in D.rglob('*') if p.is_file() and not p.name.endswith('.inspect.ndjson') and p.name!='CHECKSUMS_SHA256.json']
manifest={p.relative_to(D).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files}
(D/'CHECKSUMS_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'DELIVERY_LOCAL_VERIFIED.json').write_text(json.dumps({'status':'PASS','output_files_sha_verified':verified_files,'xlsx_270_rows_and_9_groups_verified':True,'files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','verified_output_files':verified_files,'delivery_files':len(manifest)+1,'xlsx_sha256':manifest[X.name]['sha256']},ensure_ascii=False))

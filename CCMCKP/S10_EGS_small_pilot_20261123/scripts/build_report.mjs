import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/,'$1');
const audit=JSON.parse(await fs.readFile(path.join(root,'evidence/INDEPENDENT_AUDIT_STATISTICS.json'),'utf8'));
const out=path.join(root,'delivery'); await fs.mkdir(out,{recursive:true});
const wb=Workbook.create();
const summary=wb.worksheets.add('结果汇总'), raw=wb.worksheets.add('逐次记录');
for(const s of [summary,raw]) {s.showGridLines=false; s.getRange('A1:U310').format.font.name='Microsoft YaHei';s.getRange('A1:U310').format.font.size=10;s.getRange('A1:U310').format.rowHeightPx=24;}
const navy='#173650', teal='#007F86', pale='#E9F3F5', warn='#FFF0D9';
function header(s,range){s.getRange(range).format.fill=navy;s.getRange(range).format.font.color='#FFFFFF';s.getRange(range).format.font.bold=true;s.getRange(range).format.rowHeightPx=34;s.getRange(range).format.wrapText=true;}
function section(s,cell,text){s.getRange(cell).values=[[text]];s.getRange(cell).format.font.bold=true;s.getRange(cell).format.font.color=teal;s.getRange(cell).format.font.size=12;}
function band(s,start,end,cols){for(let i=start;i<=end;i++) if((i-start)%2===0)s.getRange(`A${i}:${cols}${i}`).format.fill=pale;}
function col(s,c,w){s.getRange(`${c}:${c}`).format.columnWidthPx=w;}
summary.getRange('A1:K2').merge();summary.getRange('A1').values=[['EGS椭球引导搜索｜三例独立小试点']];summary.getRange('A1:K2').format.fill=navy;summary.getRange('A1:K2').format.font.color='#FFFFFF';summary.getRange('A1:K2').format.font.size=19;summary.getRange('A1:K2').format.font.bold=true;
summary.getRange('A3:K3').merge();summary.getRange('A3').values=[['3算例 × 3版本 × 30次 = 270次；全部完成；原口径独立核验270/270；无资源终止。']];
summary.getRange('A4:K4').merge();summary.getRange('A4').values=[['结论：成本全部相同；椭球阶段新增接受/改善均为0，搜索耗时增加。本试点不能证明大算例性能。']];
summary.getRange('A5:K5').merge();summary.getRange('A5').values=[['注意：APP的原程序真实概率报告为0.9651546，90/90低于0.99；该项未改作新验收门槛。']];summary.getRange('A5:K5').format.fill=warn;summary.getRange('A3:K5').format.wrapText=true;summary.getRange('A3:K5').format.rowHeightPx=31;
section(summary,'A7','成本与稳定性｜成本越低越好，std为样本标准差');
const sh=['编号','算例','版本','有效数/30','best','avg','std','CV','best命中数','LSS均概率','真实P均报告'];
summary.getRange('A8:K8').values=[sh];header(summary,'A8:K8');
summary.getRange('A9:K17').values=audit.case_summaries.map(s=>[s.case_index,s.instance,s.arm,s.valid,s.best,s.avg,s.sample_std,s.cv,s.best_hits, audit.runs.filter(r=>r.case_index===s.case_index&&r.arm===s.arm).reduce((a,r)=>a+r.lss_probability,0)/30,s.mean_reported_realP]);band(summary,9,17,'K');
summary.getRange('E9:G17').setNumberFormat('0.000000');summary.getRange('H9:H17').setNumberFormat('0.00%');summary.getRange('J9:K17').setNumberFormat('0.0000000');summary.getRange('K15:K17').format.fill=warn;
section(summary,'A19','时间与搜索贡献｜单位：秒');
summary.getRange('A20:K20').values=[['编号','版本','最终解首次原始接受均时','命中best条件均时','搜索均时','进程总均时','搜索相对S10倍数','EGS查询均数','EGS新增接受总数','EGS改善总数','真实P≥.99次数']];header(summary,'A20:K20');summary.getRange('A20:K20').format.rowHeightPx=48;
summary.getRange('A21:K29').values=audit.case_summaries.map(s=>[s.case_index,s.arm,s.mean_final_selection_first_raw_accept_seconds,s.mean_raw_accept_seconds_conditional_on_best,s.mean_search_seconds,s.mean_process_wall_seconds,null,s.mean_egs_queries,audit.runs.filter(r=>r.case_index===s.case_index&&r.arm===s.arm).reduce((a,r)=>a+r.egs_new_acceptances,0),s.total_egs_improvements,s.reported_realP_ge99_count]);band(summary,21,29,'K');summary.getRange('C21:G29').setNumberFormat('0.0000');
for(let i=0;i<9;i++){const row=21+i,base=21+3*Math.floor(i/3);summary.getRange(`G${row}`).formulas=[[`=E${row}/E${base}`]];}
section(summary,'A31','同seed配对比较｜9项均值符号翻转检验，Holm校正');
summary.getRange('A32:I32').values=[['编号','候选','参照','完整配对','均值差','相对均值差','方向','成本Holm p','有效率Holm p']];header(summary,'A32:I32');
summary.getRange('A33:I41').values=audit.comparisons.map(c=>[c.case_index,c.candidate,c.reference,c.complete_pairs?30:0,c.mean_difference,c.relative_mean_difference,c.direction,c.p_mean_holm,c.p_validity_holm]);band(summary,33,41,'I');summary.getRange('E33:E41').setNumberFormat('0.000000');summary.getRange('F33:F41').setNumberFormat('0.00%');summary.getRange('H33:I41').setNumberFormat('0.00000');
section(summary,'A43','口径、限制与溯源');
const notes=[
'S10_MITM：原S10搜索；EGS_2p4：椭球代理评分引导OA搜索，γ=2.4；EGS_0：同搜索的γ=0消融。',
'三臂自生成起点；统一seed 960001—960030、600秒搜索上限；未读历史解。椭球不是最终约束。',
'最终结果固定取RESULT主输出（原LSS第1变体）；原始证书与原LSS验收保持不变。',
'“独立有效”指按原协议记录、身份、成本、选择、原始整数计数证书与LSS验收通过，不代表真实P报告≥.99。',
'APP主输出LSS概率0.99248148，但真实概率报告0.9651546。经验样本验收与原程序真实概率报告存在差距。',
'最终解首次原始接受均时：最终LSS输出的同一选择首次获得原始证书的时间；并非首次LSS入选时间。',
'命中best条件均时仅统计达到本组30次最低成本的运行；本试点每组均30次命中。未证明全局最优。',
'搜索时间含初始化及主搜索；进程总时间还含原LSS与真实概率报告。后续报告不在原600秒搜索时钟内。',
'均值/std仅全30次有效时填列；std分母29。统计来自独立审计JSON；时间倍数使用表内公式。',
'所有组成本波动为0；相同成本不证明算法等效。共同初始化已得到最终输出，EGS阶段未新增接受解。',
'仅3—4组、每组5项的小算例；不能据此判断大规模avg、波动或速度。未自动扩展全40例。',
'同批新鲜Gurobi11.0.3，最多12并行；不与历史Gurobi13成绩混用；并发负载影响实际计时。',
'来源：INDEPENDENT_AUDIT_STATISTICS.json；270条逐次记录和不可变输出SHA见随附证据包。',
'协议SHA256：627224b5c1293b92ccb902bcd94d815c2db9126b5d808e2e83bb9556039b365e',
'运行：北京时间2026-11-23 23:22:11—23:26:22；全部270次自然完成；source/input pins不变。'];
for(let i=0;i<notes.length;i++){const n=44+i;summary.getRange(`A${n}:K${n}`).merge();summary.getRange(`A${n}`).values=[[notes[i]]];summary.getRange(`A${n}:K${n}`).format.wrapText=true;summary.getRange(`A${n}:K${n}`).format.rowHeightPx=31;}
summary.freezePanes.freezeRows(8);col(summary,'A',58);col(summary,'B',178);col(summary,'C',178);for(const c of ['D','E','F','G','H','I','J','K'])col(summary,c,112);
const rh=['算例编号','算例','容量','版本','重复号','seed','独立有效(1/0)','成本','LSS概率','真实概率报告','搜索时间(s)','进程总时间(s)','最终选择首次原始接受(s)','EGS查询数','EGS新增接受','EGS改善数','峰值RSS(GiB)','退出码','选择向量','错误','身份'];
raw.getRange('A1:U1').values=[rh];header(raw,'A1:U1');raw.getRange('A1:U1').format.rowHeightPx=50;
raw.getRange('A2:U271').values=audit.runs.map(r=>[r.case_index,r.instance,r.capacity,r.arm,r.rep,r.seed,r.valid?1:0,r.cost,r.lss_probability,r.reported_real_probability,r.search_seconds,r.process_wall_seconds,r.final_selection_first_raw_accept_seconds,r.egs_queries,r.egs_new_acceptances,r.egs_improvements,r.peak_rss_bytes/2**30,r.rc,JSON.stringify(r.selection),r.errors.join(';'),r.identity]);
band(raw,2,271,'U');raw.getRange('H2:H271').setNumberFormat('0.000000');raw.getRange('I2:J271').setNumberFormat('0.0000000');raw.getRange('K2:M271').setNumberFormat('0.000000');raw.getRange('Q2:Q271').setNumberFormat('0.0000');for(const c of 'ABCDEFGHIJKLMNOPQRSTU')col(raw,c,105);col(raw,'B',160);col(raw,'D',145);col(raw,'S',135);col(raw,'T',160);col(raw,'U',200);raw.freezePanes.freezeRows(1);raw.freezePanes.freezeColumns(2);raw.tables.add('A1:U271',true,'RunRecords');
await wb.recalculate();
const validation=await wb.inspect({kind:'region',sheetId:'结果汇总',range:'E21:G29',maxChars:2200,tableMaxRows:9,tableMaxCols:3});console.log(validation.ndjson??JSON.stringify(validation));
for(const [s,range,file]of [['结果汇总','A1:K17','summary_preview.png'],['逐次记录','A1:M12','details_preview.png']]){const blob=await wb.render({sheetName:s,range,scale:1,format:'png'});await fs.writeFile(path.join(root,file),new Uint8Array(await blob.arrayBuffer()));}
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(path.join(out,'EGS_三小算例_三版本30次_统计结果.xlsx'));
console.log('EXPORTED',audit.runs.length,audit.case_summaries.length);

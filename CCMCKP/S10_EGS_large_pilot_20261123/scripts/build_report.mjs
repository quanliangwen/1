import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/,'$1');
const auditBytes=await fs.readFile(path.join(root,'evidence/INDEPENDENT_AUDIT_STATISTICS.json'));
const a=JSON.parse(auditBytes.toString('utf8'));
const observed=JSON.parse(await fs.readFile(path.join(root,'evidence/OBSERVED_OUTPUT_DIAGNOSTICS.json'),'utf8'));
if(crypto.createHash('sha256').update(auditBytes).digest('hex')!==observed.independent_audit_sha256)throw Error('Diagnostic/audit provenance mismatch');
const obsRow=new Map(observed.runs.map(x=>[x.identity,x]));
const obsGroup=g=>observed.groups.find(x=>x.case_index===g.case_index&&x.arm===g.arm);
const p=JSON.parse(await fs.readFile(path.join(root,'evidence/PROTOCOL.json'),'utf8'));
const out=path.join(root,'delivery');await fs.mkdir(out,{recursive:true});
const wb=Workbook.create(),s=wb.worksheets.add('结果汇总'),r=wb.worksheets.add('逐次记录');
const navy='#173650',teal='#007F86',pale='#E9F3F5',warn='#FFF0D9';
for(const sheet of [s,r]){sheet.showGridLines=false;sheet.getRange('A1:Z300').format.font.name='Microsoft YaHei';sheet.getRange('A1:Z300').format.font.size=10;sheet.getRange('A1:Z300').format.rowHeightPx=25;}
function header(sheet,range){const q=sheet.getRange(range);q.format.fill=navy;q.format.font.color='#FFFFFF';q.format.font.bold=true;q.format.wrapText=true;q.format.rowHeightPx=48;}
function section(cell,text){s.getRange(cell).values=[[text]];s.getRange(cell).format.font.bold=true;s.getRange(cell).format.font.color=teal;s.getRange(cell).format.font.size=12;}
function note(row,text,bg){s.getRange(`A${row}:L${row}`).merge();s.getRange(`A${row}`).values=[[text]];s.getRange(`A${row}:L${row}`).format.wrapText=true;s.getRange(`A${row}:L${row}`).format.rowHeightPx=33;if(bg)s.getRange(`A${row}:L${row}`).format.fill=bg;}
function bands(sheet,start,end,last){for(let row=start;row<=end;row++)if((row-start)%2===0)sheet.getRange(`A${row}:${last}${row}`).format.fill=pale;}
function width(sheet,col,pixels){sheet.getRange(`${col}:${col}`).format.columnWidthPx=pixels;}
s.getRange('A1:L2').merge();s.getRange('A1').values=[['EGS椭球引导搜索｜三大算例独立试点']];s.getRange('A1:L2').format.fill=navy;s.getRange('A1:L2').format.font.color='#FFFFFF';s.getRange('A1:L2').format.font.size=19;s.getRange('A1:L2').format.font.bold=true;
note(3,`3算例 × 3版本 × 30次 = 270次；终末${a.terminal}次，原口径独立有效${a.independent_valid}次。`);
const against=a.comparisons.filter(x=>x.candidate==='EGS_2p4'&&x.reference==='S10_MITM');
note(4,`EGS_2p4对原S10：完整可评${against.filter(x=>x.complete_pairs).length}/3例，成本优/平/劣=${['优','平','劣'].map(d=>against.filter(x=>x.direction===d).length).join('/')}；单例Holm p见配对表。`);
const failReal=observed.runs.filter(x=>x.reported_real_probability<.99).length;
note(5,`真实概率报告低于0.99：${failReal}次。该报告不是本次追加门槛；“原口径有效”不等于真实概率保证。`,failReal?warn:undefined);
section('A7','成本与稳定性｜成本越低越好；每组30次全有效才列官方avg/std');
s.getRange('A8:L8').values=[['编号','算例','容量T','版本','有效数/30','best','avg','样本std','CV','valid-only avg诊断','真实P≥.99次数','真实P均报告']];header(s,'A8:L8');
s.getRange('A9:L17').values=a.case_summaries.map(g=>[g.case_index,g.instance,g.capacity,g.arm,g.valid,g.best,g.avg,g.sample_std,g.cv,g.valid_only_avg_diagnostic,g.reported_realP_ge99_count,g.mean_reported_realP]);bands(s,9,17,'L');s.getRange('F9:H17').setNumberFormat('0.000000');s.getRange('I9:I17').setNumberFormat('0.00%');s.getRange('J9:J17').setNumberFormat('0.000000');s.getRange('L9:L17').setNumberFormat('0.0000000');
section('A19','时间与日志贡献｜秒；物理耗时含全部30次，质量不完整时不据此判加速');
s.getRange('A20:L20').values=[['编号','版本','最终选择首次原始接受均时','best命中数','best条件平均时间','搜索均时（全30）','进程总均时（全30）','搜索相对S10倍数','EGS查询均数（日志）','EGS原始接受总数（日志）','EGS改善总数（日志）','30次全有效']];header(s,'A20:L20');
s.getRange('A21:L29').values=a.case_summaries.map(g=>{const o=obsGroup(g);return[g.case_index,g.arm,g.mean_final_selection_first_raw_accept_seconds,g.best_hits,g.mean_raw_accept_seconds_conditional_on_best,o.all_observed_mean_search_seconds,g.mean_process_wall_seconds,null,observed.runs.filter(x=>x.case_index===g.case_index&&x.arm===g.arm).reduce((n,x)=>n+x.observed_egs_queries,0)/30,o.all_observed_egs_new_acceptances,o.all_observed_egs_improvements,g.valid===30?'是':'否'];});bands(s,21,29,'L');
for(let i=0;i<9;i++){const row=i+21,base=21+3*Math.floor(i/3);s.getRange(`H${row}`).formulas=[[`=F${row}/F${base}`]];}
s.getRange('C21:C29').setNumberFormat('0.0000');s.getRange('E21:H29').setNumberFormat('0.0000');
section('A31','同seed配对比较｜9项均值符号翻转检验及Holm校正，有效率另检');
s.getRange('A32:K32').values=[['编号','候选','参照','完整配对数','均值差','相对均值差','方向','成本原始p','成本Holm p','有效率原始p','有效率Holm p']];header(s,'A32:K32');
s.getRange('A33:K41').values=a.comparisons.map(c=>[c.case_index,c.candidate,c.reference,c.complete_pairs?30:null,c.mean_difference,c.relative_mean_difference,c.direction,c.p_mean_raw,c.p_mean_holm,c.p_validity_raw,c.p_validity_holm]);bands(s,33,41,'K');s.getRange('E33:E41').setNumberFormat('0.000000');s.getRange('F33:F41').setNumberFormat('0.00%');s.getRange('H33:K41').setNumberFormat('0.00000');
section('A43','初始化与主搜索诊断｜原始成本均值取全30日志，非官方最终成本avg');
s.getRange('A44:F44').values=[['编号','版本','初始化最好成本均值','原始搜索最终成本均值','主输出LSS成本均值','初始化平均耗时(s)']];header(s,'A44:F44');
s.getRange('A45:F53').values=a.case_summaries.map(g=>{const o=obsGroup(g);return[g.case_index,g.arm,o.all_observed_mean_initialization_cost,o.all_observed_mean_raw_final_cost,g.avg,o.all_observed_mean_initialization_seconds];});bands(s,45,53,'F');s.getRange('C45:E53').setNumberFormat('0.000000');s.getRange('F45:F53').setNumberFormat('0.0000');
section('A55','最终概率观测｜全部30次原输出；真实概率报告未追加为新门槛');
s.getRange('A56:H56').values=[['编号','版本','最终LSS<.99次数','原验收有效数','真实P≥.99次数','真实P均报告','真实P最低报告','真实P最高报告']];header(s,'A56:H56');
s.getRange('A57:H65').values=a.case_summaries.map(g=>{const o=obsGroup(g),x=observed.runs.filter(r=>r.case_index===g.case_index&&r.arm===g.arm);return[g.case_index,g.arm,o.reported_lss_below99_count,g.valid,o.all_reported_realP_ge99_count,o.all_mean_reported_realP,Math.min(...x.map(r=>r.reported_real_probability)),Math.max(...x.map(r=>r.reported_real_probability))];});bands(s,57,65,'H');s.getRange('F57:H65').setNumberFormat('0.0000000');s.getRange('E57:H65').format.fill=warn;
section('A67','方法、限制与来源');
const notes=[
'S10_MITM：原S10；EGS_2p4：椭球代理评分引导OA搜索，γ=2.4；EGS_0：相同EGS搜索的γ=0消融。椭球不作为最终约束。',
'编号19：LAB50组T63；35：APP30组T58；39：APP50组T91。均每组10项、每项500样本；三例在启动前固定。',
'seed960001—960030，各次独立生成起点；同批Gurobi11.0.3、最多12并行，未混历史成绩或借用旧解。',
'统一搜索预算600秒、原程序45秒搜索余量；原LSS和真实概率报告在搜索时钟外；报告耗时不伪装为搜索耗时。',
'最终成本固定取RESULT主输出/原LSS第1变体，原始经验样本证书与LSS准入不变；不按真实概率挑输出变体。',
'原口径独立有效检查身份、全部输出SHA、冻结源/输入、时钟、原始证书、LSS、选择与成本。rc0不能代替独立有效。',
'真实概率报告仍沿用原程序；其低于.99单列披露。不将经验样本验收冒充真分布或严格DRO置信覆盖保证。',
'avg/std仅30/30有效时列值；样本std分母29。valid-only avg仅诊断，缺失组不据此判胜负，失败不补跑、不赋假成本。',
'最终选择首次原始接受时间：最终输出同一选择首次通过原始证书的时间；不是首次LSS接受（本源码未记录后者）。',
'best条件平均时间仅取命中本组最低成本的有效运行，容差1e-8；未证明该best为全局最优。',
'各版本自己的best成本可能不同；best条件时间不能当成到达同一个目标成本的速度比较。',
'每例三对比，共9项同seed配对均值符号翻转检验；≤20非零差精确枚举，否则99999次符号抽样+观测项。Holm家族9项。',
'有效率采用配对精确McNemar并另做9项Holm校正。全精度成本计算；四舍五入仅用于显示。',
'EGS新增接受与改善来自主搜索逐次日志，不把共同初始化所得好解算成椭球阶段贡献。',
'计时受到共同并发负载影响；仅三个大算例，不能据此宣布全40例都更好或总体等效；本试点未自动扩展。',
'数值来源INDEPENDENT_AUDIT_STATISTICS.json；原始270次输出及逐文件SHA在完整紧凑证据包中。',
'48次最终LSS低于.99均保留原输出成本、概率、时间及选择，标为诊断；不会因进程rc0便计为有效。',
'OBSERVED_OUTPUT_DIAGNOSTICS为原输出观测补充，不改变独立有效性与正式成本统计。日志贡献/物理时间取全部30次。',
`协议SHA256：${a.protocol_sha256}`];
for(let i=0;i<notes.length;i++)note(68+i,notes[i]);
width(s,'A',58);width(s,'B',180);width(s,'C',118);width(s,'D',148);for(const c of ['E','F','G','H','I','J','K','L'])width(s,c,114);s.freezePanes.freezeRows(8);
const headers=['编号','算例','容量T','版本','重复号','seed','独立有效(1/0)','有效解成本','原输出LSS概率','原输出真实概率报告','搜索时间(s)','进程总时间(s)','最终选择首次原始接受(s)','EGS查询数（日志）','EGS新增接受（日志）','EGS改善数（日志）','峰值RSS(GiB)','退出码','终止原因','原输出选择向量','独立核验诊断','身份','初始化最好成本（日志）','原始搜索最终成本（日志）','初始化耗时(s)','原输出成本（诊断）'];
r.getRange('A1:Z1').values=[headers];header(r,'A1:Z1');
r.getRange('A2:Z271').values=a.runs.map(x=>{const o=obsRow.get(x.identity);return[x.case_index,x.instance,x.capacity,x.arm,x.rep,x.seed,x.valid?1:0,x.cost,o.reported_final_lss_probability,o.reported_real_probability,o.observed_search_seconds,x.process_wall_seconds,o.observed_final_selection_first_raw_accept_seconds,o.observed_egs_queries,o.observed_egs_new_acceptances,o.observed_egs_improvements,x.peak_rss_bytes/2**30,x.rc,x.termination_reason??'',JSON.stringify(o.observed_selection),o.diagnosis||x.errors.join(';'),x.identity,o.observed_initialization_best_cost,o.observed_raw_final_best_cost,o.observed_initialization_seconds,o.reported_output_cost];});bands(r,2,271,'Z');r.getRange('H2:H271').setNumberFormat('0.000000');r.getRange('I2:J271').setNumberFormat('0.0000000');r.getRange('K2:M271').setNumberFormat('0.0000');r.getRange('Q2:Q271').setNumberFormat('0.0000');r.getRange('W2:X271').setNumberFormat('0.000000');r.getRange('Y2:Y271').setNumberFormat('0.0000');r.getRange('Z2:Z271').setNumberFormat('0.000000');
for(const c of 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')width(r,c,107);width(r,'B',180);width(r,'D',148);width(r,'S',180);width(r,'T',300);width(r,'U',280);width(r,'V',200);width(r,'Z',170);r.freezePanes.freezeRows(1);r.freezePanes.freezeColumns(2);r.tables.add('A1:Z271',true,'RunRecords');
await wb.recalculate();console.log((await wb.inspect({kind:'region',sheetId:'结果汇总',range:'A9:L17',maxChars:2200,tableMaxRows:9,tableMaxCols:12})).ndjson);
for(const [sheetName,range,name]of [['结果汇总','A1:L17','summary_preview.png'],['逐次记录','A1:M12','details_preview.png']]){const image=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(root,name),new Uint8Array(await image.arrayBuffer()));}
await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(out,'EGS_三大算例_三版本30次_统计结果.xlsx'));
console.log('EXPORTED',a.terminal,a.independent_valid);

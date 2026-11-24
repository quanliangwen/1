import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/,'$1');
const a=JSON.parse(await fs.readFile(path.join(root,'evidence/INDEPENDENT_AUDIT_STATISTICS.json'),'utf8'));
const out=path.join(root,'delivery');await fs.mkdir(out,{recursive:true});
const wb=Workbook.create(),s=wb.worksheets.add('统计对比'),r=wb.worksheets.add('180次明细');
const navy='#173650',teal='#007F86',pale='#E9F3F5',amber='#FFF0D9';
const label=arm=>arm==='S10_LSS_FIXED'?'S10（修正）':'椭球γ=2.4（修正）';
for(const sheet of [s,r]){sheet.showGridLines=false;sheet.getRange('A1:V200').format.font.name='Microsoft YaHei';sheet.getRange('A1:V200').format.font.size=10;sheet.getRange('A1:V200').format.rowHeightPx=25;}
function header(sheet,range){const q=sheet.getRange(range);q.format.fill=navy;q.format.font.color='#FFFFFF';q.format.font.bold=true;q.format.wrapText=true;q.format.rowHeightPx=46;}
function section(row,text){s.getRange(`A${row}:J${row}`).merge();s.getRange(`A${row}`).values=[[text]];s.getRange(`A${row}:J${row}`).format.font.bold=true;s.getRange(`A${row}:J${row}`).format.font.color=teal;s.getRange(`A${row}:J${row}`).format.font.size=12;}
function note(row,text,fill){s.getRange(`A${row}:J${row}`).merge();s.getRange(`A${row}`).values=[[text]];s.getRange(`A${row}:J${row}`).format.wrapText=true;s.getRange(`A${row}:J${row}`).format.rowHeightPx=32;if(fill)s.getRange(`A${row}:J${row}`).format.fill=fill;}
function bands(sheet,start,end,last){for(let row=start;row<=end;row++)if((row-start)%2===0)sheet.getRange(`A${row}:${last}${row}`).format.fill=pale;}
function width(sheet,column,pixels){sheet.getRange(`${column}:${column}`).format.columnWidthPx=pixels;}
s.getRange('A1:J2').merge();s.getRange('A1').values=[['修正后S10与椭球版本｜三大算例对比']];s.getRange('A1:J2').format.fill=navy;s.getRange('A1:J2').format.font.color='#FFFFFF';s.getRange('A1:J2').format.font.bold=true;s.getRange('A1:J2').format.font.size=19;
note(3,`3算例 × 2版本 × 30次 = 180次；独立有效${a.valid}/180；540个输出变体通过最后LSS检查。`);
note(4,`最终只按LSS≥0.99验收；抽样索引0—499；不计算额外真实概率。实测并行峰值${a.completed.max_active_observed}。`);
note(5,'均值比较：LAB50持平；APP30椭球略高、未显著；APP50椭球更高、Holm p=0.00003。',amber);
section(7,'best / avg / 样本std与完整运行时间｜成本越低越好；时间单位：秒');
s.getRange('A8:J8').values=[['编号','算例','容量T','版本','有效数/30','best','avg','样本std','平均运行时间(s)','运行时间std(s)']];header(s,'A8:J8');
s.getRange('A9:J14').values=a.case_summaries.map(x=>[x.case_index,x.instance,x.capacity,label(x.arm),x.valid,x.best,x.avg,x.std,x.runtime_mean_seconds,x.runtime_std_seconds]);bands(s,9,14,'J');s.getRange('F9:H14').setNumberFormat('0.000000');s.getRange('I9:J14').setNumberFormat('0.000');
section(16,'搜索耗时及LSS检查｜搜索时间与完整进程时间分别统计');
s.getRange('A17:H17').values=[['编号','版本','平均搜索时间(s)','搜索时间std(s)','最低LSS值','平均LSS值','最终剔除候选记录数','椭球阶段改善次数']];header(s,'A17:H17');
s.getRange('A18:H23').values=a.case_summaries.map(x=>[x.case_index,label(x.arm),x.search_mean_seconds,x.search_std_seconds,x.LSS_min,x.LSS_mean,x.final_LSS_rejected_candidates,x.ellipsoid_search_improvements]);bands(s,18,23,'H');s.getRange('C18:D23').setNumberFormat('0.000');s.getRange('E18:F23').setNumberFormat('0.000000');
section(25,'同种子配对比较｜椭球−S10，负差表示降低成本；Holm校正家族为3项');
s.getRange('A26:J26').values=[['编号','算例','avg成本差','avg相对差','均值方向','成本原始p','成本Holm p','有效率Holm p','运行时间比（椭球/S10）','成本结论']];header(s,'A26:J26');
s.getRange('A27:J29').values=a.comparisons.map((x,i)=>[x.case_index,a.case_summaries[2*i].instance,null,null,x.direction,x.cost_p_raw,x.cost_p_holm3,x.validity_p_holm3,null,x.direction==='平'?'均值相同':x.cost_p_holm3<.05?'均值显著更高':'均值略高，未显著']);bands(s,27,29,'J');
for(let i=0;i<3;i++){const row=27+i,base=9+2*i,eg=base+1;s.getRange(`C${row}`).formulas=[[`=G${eg}-G${base}`]];s.getRange(`D${row}`).formulas=[[`=C${row}/G${base}`]];s.getRange(`I${row}`).formulas=[[`=I${eg}/I${base}`]];}
s.getRange('C27:C29').setNumberFormat('0.000000');s.getRange('D27:D29').setNumberFormat('0.0000%');s.getRange('F27:H29').setNumberFormat('0.00000');s.getRange('I27:I29').setNumberFormat('0.000');
section(31,'口径与复核证据');
const notes=[
'本批为2026-11-24北京时间10:36:19—11:08:32，历时约32分13秒；最高60并行，0个失败运行，0次资源保护终止。',
'180次主输出与540个输出变体逐项对齐LSS最后一次评价记录，全部≥0.99。只读取既有记录，未额外概率抽样或重跑。',
'正式运行时间取控制器观测的完整进程墙钟，含启动、加载、搜索、LSS和保存；不含排队，存在轮询发现退出的延迟。',
'600秒是搜索上限，沿用45秒共同余量；LSS后处理另计。因此完整运行时间可以超过600秒，未截断或隐藏时间。',
'搜索时间取worker元数据的原搜索时钟定义。运行时间std与成本std均用样本标准差，分母n−1=29。',
'best是30次有效输出的最低观测成本，不是已证明的全局最优；正式avg/std要求30/30有效，失败不赋假成本、不补跑。',
'每版每例使用同样960001—960030种子；每次自身生成起点，不读取历史解、其他版本解或其他重复结果。',
'两版使用同一个修正后二进制、Gurobi11.0.3、每求解器1线程。原S10以frontier_mitm运行，椭球以ellipsoid_oa、γ=2.4运行。',
'最终只按LSS验收。搜索内部经验样本评分/证书机制保留；额外按分布参数计算真实概率的流程已移除。',
'剔除候选记录数表示各run最终LSS过滤未通过的候选，不表示运行失败；负观测仍在完整trace中。',
'椭球阶段改善次数只适用于椭球主搜索，S10留空；APP50椭球阶段没有改善初始化，std为0不能单独当作成本优势。',
'成本配对检验：非零差≤20时精确枚举符号，否则固定seed做99999次符号翻转+观测项；3例Holm校正。有效率另做McNemar/Holm3。',
'成本差使用完整精度计算，展示值才四舍五入。运行时间仅作描述性对比；并行负载和调度影响计时。未显著不代表等效。',
'不混入修正前旧成绩，不自动扩展全40例。本表按既定LSS验收标准比较算法输出。',
'来源：INDEPENDENT_AUDIT_STATISTICS.json；原始输出、CSV、完整LSS trace和逐文件SHA在证据包中。',
`源码提交：${a.source_commit}`,
`协议SHA256：${a.protocol_sha256}`];
for(let i=0;i<notes.length;i++)note(32+i,notes[i]);
width(s,'A',58);width(s,'B',183);width(s,'C',100);width(s,'D',173);width(s,'E',104);width(s,'F',125);width(s,'G',130);width(s,'H',124);width(s,'I',145);width(s,'J',165);s.freezePanes.freezeRows(8);
const headers=['编号','算例','容量T','版本','重复号','seed','LSS独立有效(1/0)','最终成本','最终LSS概率','完整运行时间(s)','搜索时间(s)','程序内墙钟(s)','峰值RSS(GiB)','LSS评价次数','最终剔除候选数','初始化成本（诊断）','原始搜索成本（诊断）','椭球阶段改善数','退出码','终止原因','最终选择向量','核验错误'];
r.getRange('A1:V1').values=[headers];header(r,'A1:V1');r.getRange('A1:V1').format.rowHeightPx=50;
r.getRange('A2:V181').values=a.runs.map(x=>[x.case_index,x.instance,x.capacity,label(x.arm),x.rep,x.seed,x.valid?1:0,x.cost,x.LSS_probability,x.process_wall_seconds,x.search_seconds,x.worker_wall_seconds,x.peak_rss_bytes/2**30,x.LSS_evaluations,x.final_LSS_rejected_candidates,x.initialization_cost,x.raw_final_cost,x.ellipsoid_search_improvements,x.rc,x.termination_reason??'',x.selection?JSON.stringify(x.selection):'',x.errors.join(';')]);bands(r,2,181,'V');
r.getRange('H2:H181').setNumberFormat('0.000000');r.getRange('I2:I181').setNumberFormat('0.000000');r.getRange('J2:M181').setNumberFormat('0.000');r.getRange('P2:Q181').setNumberFormat('0.000000');
for(const c of 'ABCDEFGHIJKLMNOPQRSTUV')width(r,c,115);width(r,'B',183);width(r,'D',180);width(r,'U',330);width(r,'V',200);r.freezePanes.freezeRows(1);r.freezePanes.freezeColumns(2);r.tables.add('A1:V181',true,'RunRecords180');
await wb.recalculate();console.log((await wb.inspect({kind:'region',sheetId:'统计对比',range:'F9:J14',maxChars:2200,tableMaxRows:6,tableMaxCols:5})).ndjson);
for(const [sheetName,range,file]of [['统计对比','A1:J14','summary_preview.png'],['统计对比','A16:J29','comparison_preview.png'],['180次明细','A1:L10','details_preview.png']]){const im=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(root,file),new Uint8Array(await im.arrayBuffer()));}
await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(out,'修正后S10与椭球_三大算例30次_60并行_对比结果.xlsx'));
console.log('EXPORTED',a.terminal,a.valid);

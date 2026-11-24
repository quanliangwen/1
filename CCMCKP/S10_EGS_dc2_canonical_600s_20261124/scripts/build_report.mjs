import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/,'$1');
const a=JSON.parse(await fs.readFile(path.join(root,'evidence/INDEPENDENT_AUDIT_STATISTICS.json'),'utf8'));
const out=path.join(root,'delivery');await fs.mkdir(out,{recursive:true});
const wb=Workbook.create(),s=wb.worksheets.add('统计对比'),r=wb.worksheets.add('180次记录');
const navy='#243B53',pale='#F0F4F8';
const label=arm=>arm==='S10_TOTAL600'?'S10（完整600s）':'EGS-DC2（完整600s）';
for(const [sheet,range] of [[s,'A1:K42'],[r,'A1:AD184']]){
 sheet.showGridLines=false;sheet.getRange(range).format.font.name='Arial';sheet.getRange(range).format.font.size=10;
 sheet.getRange(range).format.rowHeightPx=27;sheet.getRange(range).format.verticalAlignment='center';
}
s.tabColor=navy;
function header(sheet,range){const q=sheet.getRange(range);q.format.fill=navy;q.format.font.color='#FFFFFF';q.format.font.bold=true;q.format.wrapText=true;q.format.rowHeightPx=44;q.format.horizontalAlignment='center';}
function stripe(sheet,start,end,last){for(let row=start;row<=end;row++)if((row-start)%2===0)sheet.getRange(`A${row}:${last}${row}`).format.fill=pale;}
function width(sheet,column,pixels){sheet.getRange(`${column}:${column}`).format.columnWidthPx=pixels;}
function line(row,text){s.getRange(`A${row}`).values=[[text]];s.getRange(`A${row}`).format.font.size=12;s.getRange(`A${row}`).format.font.bold=true;}
s.getRange('A2').values=[['S10与椭球DC2对比（完整600秒）']];s.getRange('A2').format.font.size=16;s.getRange('A2').format.font.bold=true;
s.getRange('A3').values=[[`3例 × 2版 × 30次，共180次。有效${a.valid}/180。LSS≥0.99为唯一最终验收。实测并行峰值${a.completed.max_active_observed}。`]];
s.getRange('A4:K4').format.borders={bottom:{style:'thin',color:navy}};
s.getRange('A6:K6').values=[['编号','算例','容量T','版本','有效数/30','best','avg','样本std','平均总耗时(s)','总耗时std(s)','最大总耗时(s)']];header(s,'A6:K6');
s.getRange('A7:K12').values=a.case_summaries.map(x=>[x.case_index,x.instance,x.capacity,label(x.arm),null,null,null,null,null,null,null]);stripe(s,7,12,'K');
const idx=new Map();
a.runs.forEach((x,i)=>{const k=x.case_index+'|'+x.arm;if(!idx.has(k))idx.set(k,[]);idx.get(k).push(i+5);});
for(let i=0;i<a.case_summaries.length;i++){
 const x=a.case_summaries[i],rows=idx.get(x.case_index+'|'+x.arm),row=i+7;
 if(rows.length!==30 || rows.at(-1)-rows[0]!==29)throw Error('Noncontiguous source group');
 const rng=c=>`'180次记录'!${c}${rows[0]}:${c}${rows.at(-1)}`;
 s.getRange(`E${row}:K${row}`).formulas=[[
  `=SUM(${rng('G')})`,`=IF(COUNT(${rng('H')})>0,MIN(${rng('H')}),"")`,
  `=IF(AND(E${row}=30,COUNT(${rng('H')})=30),AVERAGE(${rng('H')}),"")`,
  `=IF(AND(E${row}=30,COUNT(${rng('H')})=30),STDEV(${rng('H')}),"")`,
  `=AVERAGE(${rng('J')})`,`=STDEV(${rng('J')})`,`=MAX(${rng('J')})`]];
}
s.getRange('F7:H12').setNumberFormat('0.000000');s.getRange('I7:K12').setNumberFormat('0.000');
s.getRange('K7:K12').conditionalFormats.add('cellIs',{operator:'greaterThan',formula:600,format:{fill:'#FDE8E8',font:{bold:true,color:'#B91C1C'}}});
line(15,'同seed成本比较（改进椭球−S10）');
s.getRange('A16:J16').values=[['编号','算例','avg成本差','avg相对差','均值方向','成本原始p','成本Holm p','有效率Holm p','平均耗时比','成本结论']];header(s,'A16:J16');
s.getRange('A17:J19').values=a.comparisons.map((x,i)=>[x.case_index,a.case_summaries[2*i].instance,null,null,x.direction,x.cost_p_raw,x.cost_p_holm3,x.validity_p_holm3,null,
 !x.complete_pairs?'有效覆盖不足':x.direction==='平'?'观察均值相同':x.cost_p_holm3<.05?(x.direction==='优'?'均值显著降低':'均值显著升高'):'均值差未显著']);stripe(s,17,19,'J');
for(let i=0;i<3;i++){
 const row=i+17,b=7+2*i,e=b+1;
 s.getRange(`C${row}`).formulas=[[`=IF(AND(ISNUMBER(G${e}),ISNUMBER(G${b})),G${e}-G${b},"")`]];
 s.getRange(`D${row}`).formulas=[[`=IF(ISNUMBER(C${row}),C${row}/G${b},"")`]];
 s.getRange(`I${row}`).formulas=[[`=I${e}/I${b}`]];
}
s.getRange('C17:C19').setNumberFormat('0.000000');s.getRange('D17:D19').setNumberFormat('0.0000%');s.getRange('F17:H19').setNumberFormat('0.000000');s.getRange('I17:I19').setNumberFormat('0.000');
line(22,'阶段耗时与LSS记录');
s.getRange('A23:K23').values=[['编号','版本','平均搜索结束时刻(s)','LSS后处理均时(s)','最低最终LSS','截止中断LSS调用数','最终LSS剔除候选数','椭球主搜索改善数','最终解发现均时(s)','命中本组best次数','命中best条件均时(s)']];header(s,'A23:K23');
s.getRange('A24:H29').values=a.case_summaries.map(x=>[x.case_index,label(x.arm),x.search_mean_seconds,x.LSS_finalization_mean_seconds,x.LSS_min,x.LSS_incomplete_evaluations,x.final_LSS_rejected_candidates,x.ellipsoid_search_improvements]);stripe(s,24,29,'K');
for(let i=0;i<a.case_summaries.length;i++){const g=a.case_summaries[i],rows=idx.get(g.case_index+'|'+g.arm),row=i+24;const rr=c=>`'180次记录'!${c}${rows[0]}:${c}${rows.at(-1)}`;s.getRange(`I${row}:K${row}`).formulas=[[`=IF(SUM(${rr('G')})=30,AVERAGE(${rr('Z')}),"")`,`=SUM(${rr('AD')})`,`=IF(J${row}>0,AVERAGEIFS(${rr('Z')},${rr('AD')},1),"")`]];}
s.getRange('I24:I29').setNumberFormat('0.000');s.getRange('K24:K29').setNumberFormat('0.000');
s.getRange('C24:D29').setNumberFormat('0.000');s.getRange('E24:E29').setNumberFormat('0.000000');
const notes=[
 '总耗时从进程启动前到退出，包含加载、初始化、搜索、全部LSS、保存及fsync。未截断为600秒，排队时间不计。',
 '搜索于430秒触发协作截止，非抢占操作在检查点退出。LSS截止590秒，595秒父级硬保护。全进程不得超过600秒。',
 '两版从本run原始样本独立生成起点。抽样使用0—499。禁止旧解、其他重复结果和额外真实概率评价。',
 '截止中断的LSS不返回部分概率、不重试。最终输出采用该向量最后一次完整LSS结果，必须≥0.99。',
 'avg与样本std只在30/30独立有效时给出，否则空。best为有效输出的最小观察成本，不是全局最优证明。',
 '成本按未四舍五入值比较，同seed符号翻转/Holm3；累计三轮Holm9另见JSON。属于探索性迭代，未显著不等于等效。',
 'DC2用无硬风险上界的SOC风险主问题与精确CDF占优割，最终仍须统一LSS。不自动扩展40例。',
 '首次发现时间指最终LSS合格向量在本run首次进入候选池的时刻，不等于最终LSS确认时间。条件均时只含命中本组best者。' 
];
notes.forEach((t,i)=>{s.getRange(`A${32+i}`).values=[[t]];s.getRange(`A${32+i}`).format.font.size=10;});
['A','B','C','D','E','F','G','H','I','J','K'].forEach((c,i)=>width(s,c,[55,182,75,172,100,126,126,126,140,140,140][i]));
r.getRange('A1').values=[['来源：本批不可变run输出、完整LSS trace及独立记录审计。未新增概率抽样。']];
r.getRange('A2').values=[['协议SHA256：'+a.protocol_sha256]];
const head=['编号','算例','容量T','版本','重复号','seed','独立有效(1/0)','最终成本','最终LSS概率','完整进程耗时(s)','搜索结束时刻(s)','程序内墙钟(s)','峰值RSS(GiB)','LSS完成调用数','最终剔除候选数','初始化成本（诊断）','搜索最好成本（诊断）','椭球主搜索改善数','退出码','终止原因','最终选择向量','核验错误','LSS后处理(s)','中断LSS调用数','输出fsync完成(s)','最终输出解首次发现(s)','规范SOC候选核验数','旧辅助检查可能拒绝数','最终解最后LSS结束(s)','命中本组best(1/0)'];
r.getRange('A4:AD4').values=[head];header(r,'A4:AD4');
r.getRange('A5:AD184').values=a.runs.map(x=>[x.case_index,x.instance,x.capacity,label(x.arm),x.rep,x.seed,x.valid?1:0,x.cost,x.LSS_probability,x.process_wall_seconds,x.search_seconds,x.worker_wall_seconds,x.peak_rss_bytes/2**30,x.LSS_evaluations,x.final_LSS_rejected_candidates,x.initialization_cost,x.raw_final_cost,x.ellipsoid_search_improvements,x.rc,x.termination_reason??'',x.selection?JSON.stringify(x.selection):'',x.errors.join(';'),x.LSS_finalization_seconds??null,x.LSS_incomplete_evaluations??null,x.completion_saved_seconds??null,x.final_solution_first_found_seconds??null,x.canonical_candidates_checked??null,x.legacy_epigraph_guard_would_reject_count??null,x.final_solution_last_LSS_evaluation_end_seconds??null,(x.valid&&x.cost===a.case_summaries.find(g=>g.case_index===x.case_index&&g.arm===x.arm).best)?1:0]);
stripe(r,5,184,'AD');for(const c of ['AA','AB','AC','AD'])width(r,c,150);for(const c of 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')width(r,c,120);width(r,'B',182);width(r,'D',172);width(r,'U',340);width(r,'V',240);
r.getRange('H5:I184').setNumberFormat('0.000000');r.getRange('J5:M184').setNumberFormat('0.000');r.getRange('P5:Q184').setNumberFormat('0.000000');r.getRange('W5:Z184').setNumberFormat('0.000');r.getRange('X5:X184').setNumberFormat('0');r.getRange('AA5:AB184').setNumberFormat('0');r.getRange('AD5:AD184').setNumberFormat('0');r.getRange('AC5:AC184').setNumberFormat('0.000');
width(r,'U',520);r.getRange('U5:V184').format.wrapText=true;r.getRange('A5:AD184').format.rowHeightPx=52;
r.freezePanes.freezeRows(4);r.freezePanes.freezeColumns(2);r.tables.add('A4:AD184',true,'ExperimentRecords180');
await wb.recalculate();
console.log((await wb.inspect({kind:'region',sheetId:'统计对比',range:'E7:K12',maxChars:2500,tableMaxRows:6,tableMaxCols:7})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'formula error scan'})).ndjson);
for(const [sheetName,range,file] of [['统计对比','A22:K39','notes_preview.png'],['180次记录','T4:AD12','witness_preview.png']]){
 const png=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(root,file),new Uint8Array(await png.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(out,'S10与椭球DC2_三大算例30次_完整600秒_对比结果.xlsx'));
console.log('EXPORTED',a.terminal,a.valid);

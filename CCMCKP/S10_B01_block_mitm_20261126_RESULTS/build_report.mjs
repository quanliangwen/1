import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/,'$1');
const e=JSON.parse(await fs.readFile(path.join(root,'evidence/engineering/ENGINEERING_INDEPENDENT_AUDIT.json'),'utf8'));
let a;try{a=JSON.parse(await fs.readFile(path.join(root,'evidence/formal/FINAL_INDEPENDENT_AUDIT.json'),'utf8'));}catch(err){if(err.code!=='ENOENT')throw err;a=null;}
const protocol=JSON.parse(await fs.readFile(path.join(root,a?'evidence/formal/PROTOCOL.json':'evidence/engineering/PROTOCOL.json'),'utf8'));
const wb=Workbook.create(),s=wb.worksheets.add('对比统计'),r=wb.worksheets.add('运行明细');
const header=(sh,rg)=>{sh.getRange(rg).format.fill='#183449';sh.getRange(rg).format.font.color='#FFFFFF';sh.getRange(rg).format.font.bold=true;sh.getRange(rg).format.rowHeightPx=38;sh.getRange(rg).format.wrapText=true;};
const width=(sh,c,w)=>{sh.getRange(`${c}:${c}`).format.columnWidthPx=w;};
const title=(row,text)=>{s.getRange(`A${row}:M${row}`).merge();s.getRange(`A${row}`).values=[[text]];s.getRange(`A${row}:M${row}`).format.fill='#E9F0F4';s.getRange(`A${row}`).format.font.bold=true;s.getRange(`A${row}:M${row}`).format.rowHeightPx=30;};
for(const sh of [s,r]){sh.showGridLines=false;sh.getRange('A1:T330').format.font.name='Arial';sh.getRange('A1:T330').format.font.size=10;}
s.getRange('A1:M2').merge();s.getRange('A1').values=[['B01 小块 MITM：统一 LSS 验收对照测试']];s.getRange('A1').format.font.size=16;s.getRange('A1').format.font.bold=true;
s.getRange('A3:M3').merge();s.getRange('A3').values=[[a?`正式 ${a.terminal} 次：独立有效 ${a.independent_valid}；工程 ${e.terminal} 次另列。完整进程上限 600 秒。`:`工程 ${e.terminal} 次：独立有效 ${e.independent_valid}；扩展门槛${e.gate_pass?'通过':'未通过'}，没有正式30次均值结论。`]];
s.getRange('A4:M4').merge();s.getRange('A4').values=[['A 原 S10 半径组合；B 原 S10 零半径；C B01 零半径。B→C 检验搜索机制，A→B 区分半径影响。']];
s.getRange('A5:M5').merge();s.getRange('A5').values=[[protocol.cases.map(c=>`${c.index} ${c.instance} (T=${c.tmax})`).join('；')]];
const formalRows=a?.rows??[],combined=[...formalRows.map(x=>({...x,stage:'正式'})),...e.rows.map(x=>({...x,stage:'工程'}))];
r.getRange('A1:T1').merge();r.getRange('A1').values=[['来源：本批不可变run输出、完整LSS决策记录及独立记录审计；没有新增真实概率抽样。']];
r.getRange('A2:T2').merge();r.getRange('A2').values=[['官方 avg/std 要求每组30/30有效；两次工程记录只用于实现诊断，未混入正式统计。']];
r.getRange('A3:T3').merge();r.getRange('A3').formulas=[["='对比统计'!A5"]];
const rh=['阶段','算例编号','版本','重复','seed','独立有效(1/0)','最终成本','最终LSS','完整进程秒','搜索完成秒','LSS阶段秒','最终解首次发现秒','初始化成本','搜索最好成本','初始化后改善(1/0)','小块改善次数','峰值RSS GiB','退出码','核验错误','最终选择'];
r.getRange('A4:T4').values=[rh];header(r,'A4:T4');
if(combined.length)r.getRange(`A5:T${combined.length+4}`).values=combined.map(x=>[x.stage,x.case_index,x.arm,x.rep,x.seed,x.valid?1:0,x.cost,x.LSS??null,x.process_wall_seconds,x.search_seconds??null,x.LSS_seconds??null,x.first_found_seconds??null,x.initialization_cost??null,x.raw_final_cost??null,x.post_init_improved?1:0,x.block_incumbent_improvements??0,x.peak_rss_bytes/2**30,x.rc,x.errors.join(';'),JSON.stringify(x.selection??null)]);
for(const col of 'ABCDEFGHIJKLMNOPQRST')width(r,col,115);width(r,'C',195);width(r,'S',330);width(r,'T',520);r.getRange(`G5:H${combined.length+4}`).setNumberFormat('0.000000');r.getRange(`I5:N${combined.length+4}`).setNumberFormat('0.000');r.getRange(`Q5:Q${combined.length+4}`).setNumberFormat('0.000');r.getRange(`S5:T${combined.length+4}`).format.wrapText=true;r.getRange(`A5:T${combined.length+4}`).format.rowHeightPx=64;r.freezePanes.freezeRows(4);r.freezePanes.freezeColumns(3);r.tables.add(`A4:T${combined.length+4}`,true,'RunRecords');
title(6,a?'正式结果：各版本每例30次':e.gate_pass?'正式结果：正在运行，暂不统计':'正式结果：未启动（工程门槛未通过）');
s.getRange('A7:M7').values=[['编号','版本','有效数/30','best','avg','样本std','平均总耗时(s)','总耗时std(s)','最大总耗时(s)','最终解首次发现均时(s)','命中本组best次数','命中best条件均时(s)','小块改善总次数']];header(s,'A7:M7');
const groups=a?.groups??[];
const rowsByGroup=new Map();formalRows.forEach((x,i)=>{const key=x.case_index+'|'+x.arm;if(!rowsByGroup.has(key))rowsByGroup.set(key,[]);rowsByGroup.get(key).push(i+5);});
for(let i=0;i<groups.length;i++){
 const g=groups[i],row=i+8,rr=rowsByGroup.get(g.case_index+'|'+g.arm);if(rr.length!==30||rr.at(-1)-rr[0]!==29)throw Error('Unaligned formal group');
 const range=c=>`'运行明细'!${c}${rr[0]}:${c}${rr.at(-1)}`;
 s.getRange(`A${row}:B${row}`).values=[[g.case_index,g.arm]];
 s.getRange(`C${row}:M${row}`).formulas=[[
  `=SUM(${range('F')})`,`=IF(COUNT(${range('G')})>0,MIN(${range('G')}),"")`,
  `=IF(C${row}=30,AVERAGE(${range('G')}),"")`,`=IF(C${row}=30,STDEV(${range('G')}),"")`,
  `=AVERAGE(${range('I')})`,`=STDEV(${range('I')})`,`=MAX(${range('I')})`,
  `=IF(C${row}=30,AVERAGE(${range('L')}),"")`,`=IF(COUNT(${range('G')})>0,COUNTIFS(${range('G')},D${row}),0)`,
  `=IF(K${row}>0,AVERAGEIFS(${range('L')},${range('G')},D${row}),"")`,`=SUM(${range('P')})`]];
}
s.getRange('D8:F16').setNumberFormat('0.000000');s.getRange('G8:J16').setNumberFormat('0.000');s.getRange('L8:L16').setNumberFormat('0.000');
if(a){s.getRange('A17:M17').merge();s.getRange('A17').values=[['本批观察：B01加速，但avg未改善；APP50样本std增大。本轮不扩展40例。']];}
title(19,'成本对比（候选−参照；同seed，三对比×三算例，Holm9）');
s.getRange('A20:H20').values=[['编号','候选','参照','完整30对','未舍入avg差','成本原始p','成本Holm9 p','有效率Holm9 p']];header(s,'A20:H20');
const shortArm=x=>x.startsWith('A_')?'A 原S10':x.startsWith('B_')?'B 零半径':'C B01';
if(a)s.getRange('A21:H29').values=a.comparisons.map(c=>[c.case_index,shortArm(c.candidate),shortArm(c.reference),c.complete30?'是':'否',c.avg_diff,c.cost_p_raw,c.cost_p_holm9,c.validity_p_holm9]);
s.getRange('E21:H29').setNumberFormat('0.000000');
title(32,'工程试验：每版本每例2次，仅诊断，不作正式均值/显著性结论');
s.getRange('A33:G33').values=[['编号','版本','有效数/2','观察best','初始化后改善run数','小块改善次数','平均总耗时(s)']];header(s,'A33:G33');
s.getRange('A34:G42').values=e.groups.map(g=>[g.case_index,g.arm,g.valid,g.best_diagnostic,g.post_init_improvements,g.block_improvements,g.whole_mean]);s.getRange('D34:D42').setNumberFormat('0.000000');s.getRange('G34:G42').setNumberFormat('0.000');
title(45,'口径与限制');
const notes=['LSS是唯一最终验收，阈值0.99，抽样索引0—499；所有版本沿用相同评价实现与最终复核政策。',
 '每run从原始样本自行初始化。禁止历史解/其他重复结果输入。整数CDF证明是内部搜索机制，不替代最终LSS。',
 '600秒包含进程启动、加载、初始化、搜索、全部LSS、保存/fsync及退出。595秒外部保护；没有把超时截断为600。',
 'best是本批有效输出观察到的最低成本，不是全局最优证明。最终解首次发现时刻不等于LSS确认结束时刻。',
 'C版本首先验证零半径搜索工程机制，不属于新DRO模型，不能把成本降低归为DRO理论优势或总体概率覆盖。',
 '浮点FFT/DGEMM只排序；整块剪枝依靠已完成的整数上界证书，证明超时为未知。未扫描全部k-opt邻域。',
 '正式成本检验要求双方30/30有效；缺覆盖不填假成本，有效率单独检验；本轮属于探索性机制评估。'];
notes.forEach((n,i)=>{s.getRange(`A${46+i}:M${46+i}`).merge();s.getRange(`A${46+i}`).values=[[n]];s.getRange(`A${46+i}:M${46+i}`).format.rowHeightPx=27;});
['A','B','C','D','E','F','G','H','I','J','K','L','M'].forEach((c,i)=>width(s,c,[55,190,90,125,125,125,135,135,135,150,135,150,130][i]));
for(const [first,last] of [[8,16],[21,29],[34,42]])for(let row=first;row<=last;row++){s.getRange(`A${row}:M${row}`).format.rowHeightPx=28;if(row%2===0)s.getRange(`A${row}:M${row}`).format.fill='#F3F7FA';}
s.freezePanes.freezeRows(7);
await wb.recalculate();
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:20},summary:'formula error scan'})).ndjson);
for(const [sheetName,range,file] of [['对比统计','A1:M16','summary_preview.png'],['对比统计','J7:M16','times_preview.png'],['对比统计','A19:M42','diagnostic_preview.png'],['运行明细','A1:L12','records_preview.png'],['运行明细','M4:T10','selection_preview.png'],['对比统计','A45:M52','notes_preview.png']]){const blob=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(root,file),new Uint8Array(await blob.arrayBuffer()));}
await fs.mkdir(path.join(root,'delivery'),{recursive:true});await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(root,'delivery/B01小块MITM_三大算例_统一LSS_对照结果.xlsx'));
console.log('EXPORTED',combined.length);

import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/,'$1');
const a=JSON.parse(await fs.readFile(path.join(root,'evidence/formal/FINAL_INDEPENDENT_AUDIT.json'),'utf8'));
const p=JSON.parse(await fs.readFile(path.join(root,'evidence/formal/PROTOCOL.json'),'utf8'));
const d=JSON.parse(await fs.readFile(path.join(root,'FINAL_COMPARISON_AND_DIAGNOSIS.json'),'utf8'));
if(a.terminal!==270||a.global_errors.length)throw Error('Incomplete or globally invalid audit');
const wb=Workbook.create(),s=wb.worksheets.add('对比统计'),r=wb.worksheets.add('运行明细');
const names={A_B01_ORIGINAL:'A 原B01',B_D02_TRANSPORT:'B D02·DRO',C_R01_BUDGET_RO:'C R01·预算RO'};
const write=(sh,cell,values)=>sh.getRange(cell).values=values;
const head=(sh,range)=>{const z=sh.getRange(range);z.format.fill='#203D51';z.format.font.color='#FFFFFF';z.format.font.bold=true;z.format.wrapText=true;z.format.rowHeightPx=44;z.format.horizontalAlignment='center';};
const section=(row,text)=>{write(s,`A${row}`,[[text]]);s.getRange(`A${row}:K${row}`).format.fill='#E8EEF2';s.getRange(`A${row}`).format.font.bold=true;s.getRange(`A${row}:K${row}`).format.rowHeightPx=28;};
const width=(sh,col,w)=>sh.getRange(`${col}:${col}`).format.columnWidthPx=w;
for(const [sh,range] of [[s,'A1:K87'],[r,'A1:AG274']]){sh.showGridLines=false;sh.getRange(range).format.font.name='Arial';sh.getRange(range).format.font.size=10;sh.getRange(range).format.verticalAlignment='center';}
write(s,'A2',[['预算鲁棒优化与B01、D02：三大算例统一LSS测试']]);s.getRange('A2').format.font.size=16;s.getRange('A2').format.font.bold=true;
write(s,'A4',[[`270次全部终末；独立有效${a.independent_valid}/270。每版本每算例30次，原LSS≥0.99最终验收。`]]);
write(s,'A5',[[p.cases.map(c=>`${c.index} ${c.instance} (T=${c.tmax})`).join('；')]]);
section(7,'成本与完整耗时（std为样本标准差；无解成本留空，不能将快速失败视为加速）');
write(s,'A8:K8',[['算例','版本','有效/30','best','avg','样本std','CV','有效run均时(s)','全部尝试均时(s)','完整最大(s)','失败次数']]);head(s,'A8:K8');
const rows=d.rows;const ranges=new Map();
write(r,'A1',[['来源：不可变运行记录、原LSS决策轨迹、独立Fraction/GMP审核；未新增真实概率抽样。']]);
write(r,'A2',[['失败成本为空；预算证书是内部候选生成证据，不能替代最终LSS验收或冒称0.99覆盖。']]);
const cols=['算例','版本','重复','seed','独立有效(1/0)','最终成本','最终LSS','完整进程秒','搜索完成秒','LSS阶段秒','最终解首次发现秒','首次可行候选成本','搜索最好成本','峰值RSS GiB','退出码','失败分类','核验错误','最终选择','预算证明数','预算合格候选数','预算子问题数','活跃CDF调用数','活跃CDF证书秒','D02运输排除数','原候选池数','短名单数','最终回退成本增量','最终解预算Gamma','最终解预算theta','最终解预算最坏消耗','预算准备秒','预算排序秒','预算拒绝数'];
write(r,'A4:AG4',[cols]);head(r,'A4:AG4');
write(r,'A5:AG274',rows.map(x=>[x.case_index,x.arm,x.rep,x.seed,x.valid?1:0,x.cost??null,x.LSS??null,x.process_wall_seconds,x.search_seconds??null,x.LSS_seconds??null,x.first_found_seconds??null,x.self_first_accepted_cost??null,x.raw_final_cost??null,x.peak_rss_bytes/2**30,x.rc,x.failure_class??'',x.errors.join(';'),x.selection?JSON.stringify(x.selection):'',x.budget_proofs_verified?.proofs??null,x.budget_proofs_verified?.qualified??null,x.budget_proofs_verified?.subproblems??null,x.active_certificate_calls??null,x.active_certificate_seconds??null,x.transport_exclusions_verified??(x.arm==='C_R01_BUDGET_RO'?0:null),x.raw_pool_count??null,x.shortlist_count??null,x.final_cost_minus_raw_best??null,x.final_budget_gamma??null,x.final_budget_theta??null,x.final_budget_worst_load??null,x.budget_statistics?.preparation_seconds??(x.arm==='C_R01_BUDGET_RO'?null:0),x.budget_statistics?.ranking_seconds??(x.arm==='C_R01_BUDGET_RO'?null:0),x.budget_proofs_verified?.rejected??null]));
rows.forEach((x,i)=>{const key=x.case_index+'|'+x.arm;if(!ranges.has(key))ranges.set(key,[]);ranges.get(key).push(i+5);});
for(let i=0;i<a.groups.length;i++){
 const g=a.groups[i],n=i+9,rr=ranges.get(g.case_index+'|'+g.arm);if(rr.length!==30||rr.at(-1)-rr[0]!==29)throw Error('Noncontiguous group');
 const rg=c=>`'运行明细'!${c}${rr[0]}:${c}${rr.at(-1)}`;
 write(s,`A${n}:B${n}`,[[g.case_index,names[g.arm]]]);
 s.getRange(`C${n}:K${n}`).formulas=[[
  `=SUM(${rg('E')})`,`=IF(COUNT(${rg('F')})>0,MIN(${rg('F')}),"")`,`=IF(C${n}=30,AVERAGE(${rg('F')}),"")`,`=IF(C${n}=30,IF(MAX(${rg('F')})=MIN(${rg('F')}),0,STDEV(${rg('F')})),"")`,`=IF(C${n}=30,F${n}/E${n},"")`,
  `=IF(C${n}>0,AVERAGEIFS(${rg('H')},${rg('E')},1),"")`,`=AVERAGE(${rg('H')})`,`=MAX(${rg('H')})`,`=30-C${n}`]];
 const n2=i+22;write(s,`A${n2}:B${n2}`,[[g.case_index,names[g.arm]]]);
 s.getRange(`C${n2}:I${n2}`).formulas=[[
  `=IF(C${n}=30,AVERAGE(${rg('K')}),"")`,`=IF(COUNT(${rg('F')})>0,COUNTIFS(${rg('F')},D${n}),0)`,`=IF(D${n2}>0,AVERAGEIFS(${rg('K')},${rg('F')},D${n}),"")`,`=IF(C${n}>0,AVERAGEIFS(${rg('I')},${rg('E')},1),"")`,`=IF(C${n}>0,AVERAGEIFS(${rg('J')},${rg('E')},1),"")`,`=COUNT(${rg('I')})`,`=IF(C${n}=30,"完整30次",IF(C${n}=0,"无有效结果","成本均值未报告"))`]];
 const n3=i+48;write(s,`A${n3}:B${n3}`,[[g.case_index,names[g.arm]]]);
 s.getRange(`C${n3}:I${n3}`).formulas=[[
  `=AVERAGE(${rg('V')})`,`=AVERAGE(${rg('W')})`,`=AVERAGE(${rg('X')})`,`=AVERAGE(${rg('S')})`,`=AVERAGE(${rg('T')})`,`=AVERAGE(${rg('U')})`,`=AVERAGE(${rg('AG')})`]];
}
section(20,'解的发现时间与阶段耗时（阶段均时仅统计有效run；搜索记录数包括失败尝试）');
write(s,'A21:I21',[['算例','版本','最终解首次发现\n均时(s)','命中best次数','命中best条件\n均时(s)','有效搜索均时(s)','有效LSS\n均时(s)','搜索记录数','成本统计状态']]);head(s,'A21:I21');
section(33,'同seed配对比较：三对比×三算例，成本与有效率分别Holm9');
write(s,'A34:I34',[['算例','候选','参照','完整30对','未舍入avg差','成本原始p','成本Holm9 p','有效率Holm9 p','限制']]);head(s,'A34:I34');
write(s,'A35:I43',a.comparisons.map(c=>[c.case_index,names[c.candidate],names[c.reference],c.complete30?'是':'否',c.avg_diff,c.cost_p_raw,c.complete30?c.cost_p_holm9:null,c.validity_p_holm9,c.complete30?'':'成本不足30对']));
section(46,'求解机制诊断（全部尝试的平均计数；失败的快速退出不能当作有效提速）');
write(s,'A47:I47',[['算例','版本','活跃CDF调用均数','CDF证书均时(s)','D02排除均数','预算证明均数','预算合格候选均数','预算子问题均数','预算拒绝均数']]);head(s,'A47:I47');
section(59,'模型差异与失败限制');
const notes=[d.headline,
 'A为原B01，B为正半径D02，C为预算RO阈值分解。C的集合与D02不同，不能宣称相同鲁棒保证。',
 'C从本run原500样本精确均值、最大值构建偏差；8个正预算前瞻冻结，不按本批结果调参。',
 '每个预算候选均精确核算前Gamma项保护和固定theta见证，再沿原CDF内部gate及原LSS最终验收。',
 'Gamma不是概率水平；经验最大值不是未知总体上界。预算可行不等于LSS .99可行。',
 '无历史解、旧证书、外部MIP start或跨重复输入；没有LSS驱动预算调节及新增真实概率抽样。',
 '完整600含加载、模型与排序、初始化、搜索、CDF/LSS和保存fsync。430搜索、590 LSS、595独立硬保护。',
 'avg/std只有30个独立有效结果才报告；空白不等于0。best是观察最优，不是全局最优证明。',
 '耗时为启动前至退出。全部尝试均时包含失败；仅当有效率一致时才比较成功求解速度。',
 '未显著不表示等效。本轮未扩展40例，未修改预算或补跑失败。'];
notes.forEach((n,i)=>{write(s,`A${60+i}`,[[n]]);s.getRange(`A${60+i}:K${60+i}`).format.rowHeightPx=27;});
section(73,'文献与独立适配证明');
write(s,'A74',[['Bertsimas & Sim (2004), The Price of Robustness, Proposition 1 / Theorem 1, DOI 10.1287/opre.1030.0065。']]);
write(s,'A75',[['https://www.mit.edu/~dbertsim/papers/melvyn/The-Price-Of-Robustness-OR52.pdf']]);
write(s,'A76',[['固定theta后的一组一项背包分解为本题适配，经过421项检查及32个真实tinyMILP核对。']]);
write(s,'A77',[['Büsing et al. (2025), Recycling valid inequalities…, DOI 10.1007/s10107-024-02135-7；本版未实现该文割。']]);
write(s,'A78',[['https://link.springer.com/article/10.1007/s10107-024-02135-7']]);
const widths=[55,205,115,125,125,125,95,145,155,140,105];'ABCDEFGHIJK'.split('').forEach((c,i)=>width(s,c,widths[i]));
for(const [first,last] of [[9,17],[22,30],[35,43],[48,56]])for(let n=first;n<=last;n++){s.getRange(`A${n}:K${n}`).format.rowHeightPx=28;if(n%2)s.getRange(`A${n}:K${n}`).format.fill='#F4F7FA';}
s.getRange('D9:F17').setNumberFormat('0.000000');s.getRange('G9:G17').setNumberFormat('0.000%');s.getRange('H9:J17').setNumberFormat('0.000');s.getRange('C22:C30').setNumberFormat('0.000');s.getRange('E22:G30').setNumberFormat('0.000');s.getRange('E35:E43').setNumberFormat('0.000000');s.getRange('F35:H43').setNumberFormat('0.000E+00');s.getRange('C48:I56').setNumberFormat('0.0');s.getRange('D48:D56').setNumberFormat('0.000');
s.getRange('C9:C17').conditionalFormats.add('cellIs',{operator:'lessThan',formula:30,format:{fill:'#FFF0DD',font:{color:'#9A3412'}}});
const letters='A B C D E F G H I J K L M N O P Q R S T U V W X Y Z AA AB AC AD AE AF AG'.split(' ');letters.forEach(c=>width(r,c,120));width(r,'B',235);width(r,'P',300);width(r,'Q',300);width(r,'R',500);width(r,'AB',160);width(r,'AC',180);
r.getRange('F5:G274').setNumberFormat('0.000000');r.getRange('H5:K274').setNumberFormat('0.000');r.getRange('L5:M274').setNumberFormat('0.000000');r.getRange('N5:N274').setNumberFormat('0.000');r.getRange('W5:W274').setNumberFormat('0.000');r.getRange('AA5:AA274').setNumberFormat('0.000000');r.getRange('AD5:AF274').setNumberFormat('0.000');r.getRange('P5:R274').format.wrapText=true;r.getRange('A5:AG274').format.rowHeightPx=55;r.freezePanes.freezeRows(4);r.freezePanes.freezeColumns(2);r.tables.add('A4:AG274',true,'RunRecords');
r.getRange('AC5:AC274').format.wrapText=true;
await wb.recalculate();
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'formula error scan'})).ndjson);
console.log((await wb.inspect({kind:'table',range:'对比统计!A8:K17',include:'values,formulas',tableMaxRows:10,tableMaxCols:11,maxChars:3500})).ndjson);
const previews=[['对比统计','A2:G17','cost_preview.png'],['对比统计','H8:K17','time_preview.png'],['对比统计','A20:I30','discovery_preview.png'],['对比统计','A33:I43','comparison_preview.png'],['对比统计','A46:I56','mechanism_preview.png'],['对比统计','A59:K78','notes_preview.png'],['运行明细','A1:K10','records_preview.png'],['运行明细','L4:V10','record_details_preview.png'],['运行明细','W4:AG10','record_mechanism_preview.png'],['运行明细',`A${d.first_failed_excel_row}:Q${d.first_failed_excel_row+3}`,'failed_records_preview.png'],['运行明细','AB65:AG68','budget_values_preview.png']];
for(const [sheetName,range,file] of previews){if(process.argv.includes('--changed-only')&&!['discovery_preview.png','comparison_preview.png','budget_values_preview.png'].includes(file))continue;if(process.argv.includes('--summary-only')&&sheetName!=='对比统计')continue;const blob=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(root,file),new Uint8Array(await blob.arrayBuffer()));}
await fs.mkdir(path.join(root,'delivery'),{recursive:true});await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(root,'delivery/R01预算鲁棒_B01_D02_三大算例30次_对比统计.xlsx'));
console.log('EXPORTED',rows.length);

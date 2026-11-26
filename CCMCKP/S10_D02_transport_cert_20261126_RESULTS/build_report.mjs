import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/,'$1');
const a=JSON.parse(await fs.readFile(path.join(root,'evidence/formal/FINAL_INDEPENDENT_AUDIT.json'),'utf8'));
const p=JSON.parse(await fs.readFile(path.join(root,'evidence/formal/PROTOCOL.json'),'utf8'));
const diagnosis=JSON.parse(await fs.readFile(path.join(root,'FINAL_COMPARISON_AND_DIAGNOSIS.json'),'utf8'));
if(a.terminal!==270||a.global_errors.length)throw Error('Incomplete or globally invalid audit');
const wb=Workbook.create(),s=wb.worksheets.add('对比统计'),r=wb.worksheets.add('运行明细');
const names={A_B01_ORIGINAL:'A 原B01',B_D01_WINF:'B D01·原DRO',C_D02_TRANSPORT:'C D02·运输剪枝'};
const write=(sh,cell,values)=>sh.getRange(cell).values=values;
const header=(sh,range)=>{let z=sh.getRange(range);z.format.fill='#203D51';z.format.font.color='#FFFFFF';z.format.font.bold=true;z.format.wrapText=true;z.format.rowHeightPx=42;z.format.horizontalAlignment='center';};
const section=(row,text)=>{write(s,`A${row}`,[[text]]);s.getRange(`A${row}:L${row}`).format.fill='#E8EEF2';s.getRange(`A${row}`).format.font.bold=true;s.getRange(`A${row}:L${row}`).format.rowHeightPx=28;};
const width=(sh,col,w)=>sh.getRange(`${col}:${col}`).format.columnWidthPx=w;
for(const [sh,range] of [[s,'A1:L84'],[r,'A1:AE274']]){sh.showGridLines=false;sh.getRange(range).format.font.name='Arial';sh.getRange(range).format.font.size=10;sh.getRange(range).format.verticalAlignment='center';}
write(s,'A2',[['D02：同一 Wasserstein DRO 模型的运输占优剪枝测试']]);s.getRange('A2').format.font.size=16;s.getRange('A2').format.font.bold=true;
write(s,'A4',[[`正式270次；独立有效${a.independent_valid}/270；原始LSS≥0.99最终验收；每组30次。`]]);
write(s,'A5',[[p.cases.map(c=>`${c.index} ${c.instance} (T=${c.tmax})`).join('；')]]);
section(7,'成本与最终解首次发现时间（成本越低越好；std为样本标准差）');
header(s,'A8:L8');write(s,'A8',[['算例','版本','独立有效/30','best','avg','样本std','CV','最终解首次发现均时(s)','命中本组best次数','命中best条件均时(s)','模型最好被回退次数','本run自身初始成本均值']]);
const rows=a.rows.map(x=>({...x,block_incumbent_improvements:diagnosis.block_events_by_identity[x.identity]}));const groupRanges=new Map();
write(r,'A1',[['来源：formal不可变输出、原始LSS决策记录、FINAL_INDEPENDENT_AUDIT.json；未新增真实概率抽样。']]);
write(r,'A2',[['初始解均在本run生成。缺30个独立有效结果时官方avg/std空白；失败不填假成本。']]);
const cols=['算例','版本','重复','seed','独立有效(1/0)','最终成本','最终LSS','完整进程秒','搜索完成秒','LSS阶段秒','最终解首次发现秒','自身初始化成本','搜索模型最好成本','初始化后改善(1/0)','块改善次数','峰值RSS GiB','退出码','核验错误','最终选择','DRO选中总位移(精确数)','原始候选池数','短名单数','最终成本回退增量','模型输出整数证书核验数','活跃CDF证书调用数','活跃CDF证书秒','运输排除数','运输查询数','运输准备秒','运输查询秒','运输维护秒'];
write(r,'A4',[cols]);header(r,'A4:AE4');
write(r,`A5:AE${rows.length+4}`,rows.map(x=>[x.case_index,x.arm,x.rep,x.seed,x.valid?1:0,x.cost,x.LSS??null,x.process_wall_seconds,x.search_seconds??null,x.LSS_seconds??null,x.first_found_seconds??null,x.initialization_cost??null,x.raw_final_cost??null,x.post_init_improved?1:0,x.block_incumbent_improvements??0,x.peak_rss_bytes/2**30,x.rc,x.errors.join(';'),JSON.stringify(x.selection??null),x.selected_transport_shift??null,x.raw_pool_count??null,x.shortlist_count??null,x.final_cost_minus_raw_best??null,x.independent_DRO_output_checks??0,x.active_certificate_calls??null,x.active_certificate_seconds??null,x.transport_exclusions_verified??null,x.transport_statistics?.queries??(x.valid?0:null),x.transport_statistics?.preparation_seconds??(x.valid?0:null),x.transport_statistics?.probe_seconds??(x.valid?0:null),x.transport_statistics?.add_seconds??(x.valid?0:null)]));
for(let i=0;i<rows.length;i++){let key=rows[i].case_index+'|'+rows[i].arm;if(!groupRanges.has(key))groupRanges.set(key,[]);groupRanges.get(key).push(i+5);}
for(let i=0;i<a.groups.length;i++){
 const g=a.groups[i],n=i+9,rr=groupRanges.get(g.case_index+'|'+g.arm);if(rr.length!==30||rr.at(-1)-rr[0]!==29)throw Error('Group must be contiguous');
 const rg=c=>`'运行明细'!${c}${rr[0]}:${c}${rr.at(-1)}`;
 write(s,`A${n}:B${n}`,[[g.case_index,names[g.arm]]]);
 s.getRange(`C${n}:L${n}`).formulas=[[
 `=SUM(${rg('E')})`,`=IF(COUNT(${rg('F')})>0,MIN(${rg('F')}),"")`,`=IF(C${n}=30,AVERAGE(${rg('F')}),"")`,`=IF(C${n}=30,IF(MAX(${rg('F')})=MIN(${rg('F')}),0,STDEV(${rg('F')})),"")`,
 `=IF(C${n}=30,F${n}/E${n},"")`,`=IF(C${n}=30,AVERAGE(${rg('K')}),"")`,`=IF(COUNT(${rg('F')})>0,COUNTIFS(${rg('F')},D${n}),0)`,`=IF(I${n}>0,AVERAGEIFS(${rg('K')},${rg('F')},D${n}),"")`,`=COUNTIFS(${rg('W')},">0.00000001")`,`=IF(C${n}=30,AVERAGE(${rg('L')}),"")`]];
 const t=i+22;write(s,`A${t}:B${t}`,[[g.case_index,names[g.arm]]]);
 s.getRange(`C${t}:H${t}`).formulas=[[
 `=AVERAGE(${rg('H')})`,`=STDEV(${rg('H')})`,`=MAX(${rg('H')})`,`=IF(C${n}=30,AVERAGE(${rg('I')}),"")`,`=IF(C${n}=30,AVERAGE(${rg('J')}),"")`,`=SUM(${rg('N')})`]];
}
section(20,'完整运行时间（启动前计时至退出；包含加载、全部评价及保存/fsync）');
write(s,'A21:H21',[['算例','版本','完整均时(s)','完整时间std(s)','完整最大(s)','搜索均时(s)','LSS均时(s)','初始化后改善run数']]);header(s,'A21:H21');
section(33,'配对成本比较：候选−参照，三对比×三算例，Holm9');
write(s,'A34:I34',[['算例','候选','参照','完整30对','未舍入avg差','成本原始p','成本Holm9 p','有效率Holm9 p','主要机制对比']]);header(s,'A34:I34');
write(s,'A35:I43',a.comparisons.map(c=>[c.case_index,names[c.candidate],names[c.reference],c.complete30?'是':'否',c.avg_diff,c.cost_p_raw,c.complete30?c.cost_p_holm9:null,c.validity_p_holm9,c.candidate==='C_D02_TRANSPORT'&&c.reference==='B_D01_WINF'?'C−B':'']));
section(46,'机制诊断：同一DRO模型，测量实际省下的证书计算与新增开销');
write(s,'A47:G47',[['算例','版本','活跃CDF调用均数','活跃CDF证书\n均时(s)','推断排除均数','运输准备均时(s)','查询及维护\n均时(s)']]);header(s,'A47:G47');
for(let i=0;i<a.groups.length;i++){
 const g=a.groups[i],rr=groupRanges.get(g.case_index+'|'+g.arm),row=i+48;
 const rg=c=>`'运行明细'!${c}${rr[0]}:${c}${rr.at(-1)}`;const complete=`C${i+9}=30`;
 write(s,`A${row}:B${row}`,[[g.case_index,names[g.arm]]]);
 s.getRange(`C${row}:G${row}`).formulas=[[
 `=IF(${complete},AVERAGE(${rg('Y')}),"")`,`=IF(${complete},AVERAGE(${rg('Z')}),"")`,`=IF(${complete},AVERAGE(${rg('AA')}),"")`,`=IF(${complete},AVERAGE(${rg('AC')}),"")`,`=IF(${complete},AVERAGE(${rg('AD')})+AVERAGE(${rg('AE')}),"")`]];
}
s.getRange('C48:C56').setNumberFormat('0.0');s.getRange('D48:D56').setNumberFormat('0.000');s.getRange('E48:E56').setNumberFormat('0.0');s.getRange('F48:G56').setNumberFormat('0.000');
section(59,'模型、证书与验收边界');
const notes=[diagnosis.headline,
 'A原B01；B原D01正半径；C同一DRO模型加运输占优有效剪枝。主要机制对比C−B；没有缩半径。',
 '负witness只从当前run原生整数上界<.99的证书产生。独立组内共同rank耦合给出目标总消耗的逐点下界。',
 '每组min(Q目标−Q证人)向下取整到1e-12后求和，只有非负才剪。越界为未知。每条排除都保存独立可重建证据。',
 '仅复用不可行证书，不复用可行证书。原始LSS≥.99最终验收、索引0—499、strict sum<T及复核顺序不变。',
 '每run从原数据自己生成初始解；不加载历史解、旧证书或其他重复结果。DRO半径仍是工程预算，非95%总体覆盖。',
 '完整600含加载、新矩阵、初始化、全部搜索/LSS、保存fsync和退出。430搜索、590LSS截止、595独立硬保护。',
 'best是观察最小成本而非全局最优证明；未显著不等于等效。缺30个独立有效结果时官方avg/std空白。',
 '九项同seed均值符号翻转+Holm9；有效率独立配对检验。未自动扩展40例，失败不补跑择seed。'];
notes.forEach((n,i)=>{write(s,`A${60+i}`,[[n]]);s.getRange(`A${60+i}:L${60+i}`).format.rowHeightPx=27;});
section(72,'文献与本题适配（不冒称实现原论文完整算法）');
write(s,'A73',[['Jiang & Xie (2022), ALSO-X and ALSO-X+, Proposition 8, DOI 10.1287/opre.2021.2225：沿用D01点态DRO重写。']]);
write(s,'A74',[['https://optimization-online.org/wp-content/uploads/2020/12/8148.pdf']]);
write(s,'A75',[['Gerhold & Gülüm (2019), Peacocks nearby, Definition 2.6 / (2.1), DOI 10.1016/j.spa.2018.07.007：耦合与CDF平移。']]);
write(s,'A76',[['https://fam.tuwien.ac.at/~sgerhold/pub_files/papers/peacocks_nearby.pdf']]);
write(s,'A77',[['Ho-Nguyen et al. (2022), DOI 10.1287/ijoo.2022.0083：利用packing结构强化DRO；本题加性秩下界另有独立证明。']]);
write(s,'A78',[['https://arxiv.org/abs/2007.06750']]);
const sw=[55,200,200,125,125,125,95,155,130,160,145,160];'ABCDEFGHIJKL'.split('').forEach((c,i)=>width(s,c,sw[i]));
for(const [first,last] of [[9,17],[22,30],[35,43],[48,56]])for(let n=first;n<=last;n++){s.getRange(`A${n}:L${n}`).format.rowHeightPx=28;if(n%2)s.getRange(`A${n}:L${n}`).format.fill='#F4F7FA';}
s.getRange('D9:F17').setNumberFormat('0.000000');s.getRange('G9:G17').setNumberFormat('0.000%');s.getRange('H9:H17').setNumberFormat('0.000');s.getRange('J9:J17').setNumberFormat('0.000');s.getRange('L9:L17').setNumberFormat('0.000000');s.getRange('C22:G30').setNumberFormat('0.000');s.getRange('E35:H43').setNumberFormat('0.000000');
for(const c of ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','AA','AB','AC','AD','AE'])width(r,c,115);width(r,'B',230);width(r,'R',260);width(r,'S',500);width(r,'T',260);
r.getRange('F5:G274').setNumberFormat('0.000000');r.getRange('H5:K274').setNumberFormat('0.000');r.getRange('L5:M274').setNumberFormat('0.000000');r.getRange('P5:P274').setNumberFormat('0.000');r.getRange('W5:W274').setNumberFormat('0.000000');r.getRange('Z5:Z274').setNumberFormat('0.000');r.getRange('AC5:AE274').setNumberFormat('0.000');r.getRange('R5:T274').format.wrapText=true;r.getRange('A5:AE274').format.rowHeightPx=55;r.freezePanes.freezeRows(4);r.freezePanes.freezeColumns(2);r.tables.add('A4:AE274',true,'RunRecords');
await wb.recalculate();
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'formula error scan'})).ndjson);
console.log((await wb.inspect({kind:'table',range:'对比统计!A8:G17',include:'values,formulas',tableMaxRows:10,tableMaxCols:7,maxChars:3000})).ndjson);
for(const [sheetName,range,file] of [['对比统计','A2:G17','cost_preview.png'],['对比统计','H8:L17','discovery_preview.png'],['对比统计','A20:H30','runtime_preview.png'],['对比统计','A33:I43','comparison_preview.png'],['对比统计','A46:G56','mechanism_preview.png'],['对比统计','A59:L78','notes_preview.png'],['运行明细','A1:K10','records_preview.png'],['运行明细','L4:X10','record_details_preview.png'],['运行明细','Y4:AE10','record_mechanism_preview.png']]){if(process.argv.includes('--mechanism-only')&&file!=='mechanism_preview.png')continue;if(process.argv.includes('--summary-only')&&(sheetName!=='对比统计'||file==='discovery_preview.png'))continue;const blob=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(root,file),new Uint8Array(await blob.arrayBuffer()));}
await fs.mkdir(path.join(root,'delivery'),{recursive:true});await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(root,'delivery/D02运输占优_DRO三大算例_统一LSS_对比结果.xlsx'));
console.log('EXPORTED',rows.length);

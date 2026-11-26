import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/,'$1');
const a=JSON.parse(await fs.readFile(path.join(root,'evidence/formal/FINAL_INDEPENDENT_AUDIT.json'),'utf8'));
const p=JSON.parse(await fs.readFile(path.join(root,'evidence/formal/PROTOCOL.json'),'utf8'));
const diagnosis=JSON.parse(await fs.readFile(path.join(root,'FINAL_COMPARISON_AND_DIAGNOSIS.json'),'utf8'));
if(a.terminal!==270||a.global_errors.length)throw Error('Incomplete or globally invalid audit');
const wb=Workbook.create(),s=wb.worksheets.add('对比统计'),r=wb.worksheets.add('运行明细');
const names={A_B01_ORIGINAL:'A 原B01',B_COVERAGE_NOMINAL:'B 覆盖框架·零半径',C_D01_WINF_PRODUCT:'C D01·正半径DRO'};
const write=(sh,cell,values)=>sh.getRange(cell).values=values;
const header=(sh,range)=>{let z=sh.getRange(range);z.format.fill='#203D51';z.format.font.color='#FFFFFF';z.format.font.bold=true;z.format.wrapText=true;z.format.rowHeightPx=42;z.format.horizontalAlignment='center';};
const section=(row,text)=>{write(s,`A${row}`,[[text]]);s.getRange(`A${row}:L${row}`).format.fill='#E8EEF2';s.getRange(`A${row}`).format.font.bold=true;s.getRange(`A${row}:L${row}`).format.rowHeightPx=28;};
const width=(sh,col,w)=>sh.getRange(`${col}:${col}`).format.columnWidthPx=w;
for(const [sh,range] of [[s,'A1:L70'],[r,'A1:X274']]){sh.showGridLines=false;sh.getRange(range).format.font.name='Arial';sh.getRange(range).format.font.size=10;sh.getRange(range).format.verticalAlignment='center';}
write(s,'A2',[['D01：B01框架上的 Wasserstein DRO 三大算例测试']]);s.getRange('A2').format.font.size=16;s.getRange('A2').format.font.bold=true;
write(s,'A4',[[`正式270次；独立有效${a.independent_valid}/270；原始LSS≥0.99最终验收；每组30次。`]]);
write(s,'A5',[[p.cases.map(c=>`${c.index} ${c.instance} (T=${c.tmax})`).join('；')]]);
section(7,'成本与最终解首次发现时间（成本越低越好；std为样本标准差）');
header(s,'A8:L8');write(s,'A8',[['算例','版本','独立有效/30','best','avg','样本std','CV','最终解首次发现均时(s)','命中本组best次数','命中best条件均时(s)','模型最好被回退次数','本run自身初始成本均值']]);
const rows=a.rows.map(x=>({...x,block_incumbent_improvements:diagnosis.block_events_by_identity[x.identity]}));const groupRanges=new Map();
write(r,'A1',[['来源：formal不可变输出、原始LSS决策记录、FINAL_INDEPENDENT_AUDIT.json；未新增真实概率抽样。']]);
write(r,'A2',[['初始解均在本run生成。缺30个独立有效结果时官方avg/std空白；失败不填假成本。']]);
const cols=['算例','版本','重复','seed','独立有效(1/0)','最终成本','最终LSS','完整进程秒','搜索完成秒','LSS阶段秒','最终解首次发现秒','自身初始化成本','搜索模型最好成本','初始化后改善(1/0)','块改善次数','峰值RSS GiB','退出码','核验错误','最终选择','DRO选中总位移(精确数)','原始候选池数','短名单数','最终成本回退增量','模型输出整数证书核验数'];
write(r,'A4',[cols]);header(r,'A4:X4');
write(r,`A5:X${rows.length+4}`,rows.map(x=>[x.case_index,x.arm,x.rep,x.seed,x.valid?1:0,x.cost,x.LSS??null,x.process_wall_seconds,x.search_seconds??null,x.LSS_seconds??null,x.first_found_seconds??null,x.initialization_cost??null,x.raw_final_cost??null,x.post_init_improved?1:0,x.block_incumbent_improvements??0,x.peak_rss_bytes/2**30,x.rc,x.errors.join(';'),JSON.stringify(x.selection??null),x.selected_transport_shift??null,x.raw_pool_count??null,x.shortlist_count??null,x.final_cost_minus_raw_best??null,x.independent_DRO_output_checks??0]));
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
write(s,'A34:I34',[['算例','候选','参照','完整30对','未舍入avg差','成本原始p','成本Holm9 p','有效率Holm9 p','主要DRO对比']]);header(s,'A34:I34');
write(s,'A35:I43',a.comparisons.map(c=>[c.case_index,names[c.candidate],names[c.reference],c.complete30?'是':'否',c.avg_diff,c.cost_p_raw,c.complete30?c.cost_p_holm9:null,c.validity_p_holm9,c.candidate==='C_D01_WINF_PRODUCT'&&c.reference==='B_COVERAGE_NOMINAL'?'C−B':'']));
section(46,'本轮结论与模型边界');
const notes=[diagnosis.headline,
 'A=原B01；B=相同候选覆盖框架的名义中心；C=B框架加正半径DRO。主要贡献比较C−B，避免把覆盖修补归功于DRO。',
 '中心是每项全部500原始样本的经验乘积分布；type-infinity Wasserstein，地面距离为逐项半径加权l∞。',
 '最坏分布由每项消耗向上平移r_j得到；r_j=ceil(10^12×sqrt(v_j/(10000N)))/10^12，v_j为经验总体方差。',
 '半径是预注册工程预算；没有95%总体覆盖或全局最优声明。连续不确定支持允许样本外值，未变更原始LSS数据。',
 '所有内部DRO候选均须通过平移后分布的整数CDF下界证书；无名义候选fallback；最终统计验收仍仅原LSS。',
 '完整600秒包括所有阶段，430秒搜索、590秒LSS截止、595秒外部保护；没有将超时截为600。',
 'best指本批有效输出最低成本；首次发现时间不等于LSS验收结束时间。不显著不等于等效或无用。',
 '成本检验为同seed均值符号翻转；小差值族精确枚举，否则固定99999次符号翻转（不是额外概率评价）。',
 '资源上限60并行；未自动扩展40例。完整负观测、失败、时钟及来源证据保留。'];
notes.forEach((n,i)=>{write(s,`A${47+i}`,[[n]]);s.getRange(`A${47+i}:L${47+i}`).format.rowHeightPx=27;});
section(59,'文献依据（点态鲁棒重写；未声称实现文献完整算法）');
write(s,'A60',[['Jiang & Xie (2022), ALSO-X and ALSO-X+, Proposition 8, DOI 10.1287/opre.2021.2225']]);
write(s,'A61',[['https://optimization-online.org/wp-content/uploads/2020/12/8148.pdf']]);
write(s,'A62',[['Jiang & Xie (2025), The Terminator, Section 3, equations (5)–(6), DOI 10.1287/ijoc.2023.0299']]);
write(s,'A63',[['https://optimization-online.org/wp-content/uploads/2023/08/Variable_Fixing_Final_Online.pdf']]);
const sw=[55,200,200,125,125,125,95,155,130,160,145,160];'ABCDEFGHIJKL'.split('').forEach((c,i)=>width(s,c,sw[i]));
for(const [first,last] of [[9,17],[22,30],[35,43]])for(let n=first;n<=last;n++){s.getRange(`A${n}:L${n}`).format.rowHeightPx=28;if(n%2)s.getRange(`A${n}:L${n}`).format.fill='#F4F7FA';}
s.getRange('D9:F17').setNumberFormat('0.000000');s.getRange('G9:G17').setNumberFormat('0.000%');s.getRange('H9:H17').setNumberFormat('0.000');s.getRange('J9:J17').setNumberFormat('0.000');s.getRange('L9:L17').setNumberFormat('0.000000');s.getRange('C22:G30').setNumberFormat('0.000');s.getRange('E35:H43').setNumberFormat('0.000000');
for(const c of 'ABCDEFGHIJKLMNOPQRSTUVWX')width(r,c,115);width(r,'B',230);width(r,'R',260);width(r,'S',500);width(r,'T',260);
r.getRange('F5:G274').setNumberFormat('0.000000');r.getRange('H5:K274').setNumberFormat('0.000');r.getRange('L5:M274').setNumberFormat('0.000000');r.getRange('P5:P274').setNumberFormat('0.000');r.getRange('W5:W274').setNumberFormat('0.000000');r.getRange('R5:T274').format.wrapText=true;r.getRange('A5:X274').format.rowHeightPx=55;r.freezePanes.freezeRows(4);r.freezePanes.freezeColumns(2);r.tables.add('A4:X274',true,'RunRecords');
await wb.recalculate();
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'formula error scan'})).ndjson);
console.log((await wb.inspect({kind:'table',range:'对比统计!A8:G17',include:'values,formulas',tableMaxRows:10,tableMaxCols:7,maxChars:3000})).ndjson);
for(const [sheetName,range,file] of [['对比统计','A2:G17','cost_preview.png'],['对比统计','H8:L17','discovery_preview.png'],['对比统计','A20:H30','runtime_preview.png'],['对比统计','A33:I43','comparison_preview.png'],['对比统计','A46:L63','notes_preview.png'],['运行明细','A1:K10','records_preview.png'],['运行明细','L4:X10','record_details_preview.png']]){if(process.argv.includes('--summary-only')&&(sheetName!=='对比统计'||file==='discovery_preview.png'))continue;const blob=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(root,file),new Uint8Array(await blob.arrayBuffer()));}
await fs.mkdir(path.join(root,'delivery'),{recursive:true});await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(root,'delivery/D01_WassersteinDRO_三大算例_统一LSS_对比结果.xlsx'));
console.log('EXPORTED',rows.length);

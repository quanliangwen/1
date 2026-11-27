import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/,'$1');
const read=async n=>JSON.parse(await fs.readFile(path.join(root,n),'utf8'));
const d=await read('FINAL_COMPARISON_AND_DIAGNOSIS.json'),a=await read('evidence/formal/FINAL_INDEPENDENT_AUDIT.json'),gate=await read('evidence/formal/FULL40_ELIGIBILITY_DECISION.json');
if(a.terminal!==360||a.global_errors.length)throw Error('Not fully audited');
const wb=Workbook.create(),s=wb.worksheets.add('对比统计'),r=wb.worksheets.add('运行明细');
const names={A_B01_ORIGINAL:'A 原B01',B_D02_TRANSPORT:'B D02·DRO',C_R02_CVAR_BUDGET:'C R02·预算RO',D_R04_BUDGET_FFT:'D R04·RO引导精炼'};
const write=(sh,where,data)=>sh.getRange(where).values=data;
const rat=v=>v==null?null:typeof v==='string'&&v.includes('/')?Number(v.split('/')[0])/Number(v.split('/')[1]):Number(v);
const header=(sh,range)=>{const z=sh.getRange(range);z.format.fill='#203D51';z.format.font.color='#FFFFFF';z.format.font.bold=true;z.format.wrapText=true;z.format.rowHeightPx=48;z.format.horizontalAlignment='center';};
const section=(row,text)=>{write(s,`A${row}`,[[text]]);s.getRange(`A${row}:K${row}`).format.fill='#E8EEF2';s.getRange(`A${row}`).format.font.bold=true;s.getRange(`A${row}:K${row}`).format.rowHeightPx=28;};
const width=(sh,col,n)=>sh.getRange(`${col}:${col}`).format.columnWidthPx=n;
for(const [sh,range] of [[s,'A1:K134'],[r,'A1:AX364']]){sh.showGridLines=false;sh.getRange(range).format.font.name='Arial';sh.getRange(range).format.font.size=10;sh.getRange(range).format.verticalAlignment='center';}
write(s,'A2',[['R04预算RO引导的边界精炼：四版本、三大算例统一LSS测试']]);s.getRange('A2').format.font.size=16;s.getRange('A2').format.font.bold=true;
write(s,'A4',[[`360次终末，独立有效${a.independent_valid}/360；每组30次，同seed新鲜对照，最终只原LSS≥0.99。`]]);
write(s,'A5',[['19 LAB50·T63；35 APP30·T58；39 APP50·T91。完整600秒含加载、RO、FFT提议、整数CDF、LSS、保存和退出。']]);
section(7,'成本、波动与完整运行时间（官方avg/std要求30次全有效；std为样本标准差）');
write(s,'A8:K8',[['算例','版本','有效/30','best','avg','样本std','CV','有效完整均时(s)','全部尝试均时(s)','完整最大(s)','失败次数']]);header(s,'A8:K8');
const columns=['算例','版本','重复','seed','独立有效1/0','最终成本','最终LSS','完整进程秒','搜索完成秒','LSS阶段秒','最终解首次发现秒','首次CDF接受成本','内部最好成本','峰值RSS GiB','退出码','失败分类','核验错误','最终选择','模型类型','母体模型证明数','母体合格候选数','母体MIP数','搜索CDF调用数','CDF证书秒','D02运输排除数','原候选池数','短名单数','终审回退成本','最终RO Gamma','最终RO theta','最终预算最坏和','最终输出来源','R04母体完成秒','R04精炼全阶段秒','母体准备秒','母体MIP秒','母体成本剪枝数','母体查询数','精炼路径记录数','原LSS接受数','精炼提议数','精炼新认证数','精炼MIP数','私人FFT秒','私人提议阶段秒','新native请求数','本run种子数','精炼发生截尾1/0','R04母体认证池数','R04母体最好成本'];
write(r,'A1',[['来源：formal_FINAL_INDEPENDENT_AUDIT.json、不可变结果与原LSS轨迹；预算见证、私人FFT重建及整数CDF输出证书独立核验。']]);
write(r,'A2',[['失败成本为空，非对应模型参数为空。参数数值近似展示，精确有理数见证保留JSON。R04精炼解不冒称母体预算鲁棒可行。']]);
write(r,'A4:AX4',[columns]);header(r,'A4:AX4');
const N=d.rows.length,last=N+4;
write(r,`A5:AX${last}`,d.rows.map(x=>{const m=x.R04_model;return [x.case_index,x.arm,x.rep,x.seed,x.valid?1:0,x.cost??null,x.LSS??null,x.process_wall_seconds,x.search_seconds??null,x.LSS_seconds??null,x.first_found_seconds??null,x.self_first_accepted_cost??null,x.raw_final_cost??null,x.peak_rss_bytes/2**30,x.rc,x.failure_class??'',x.errors.join(';'),x.selection?JSON.stringify(x.selection):'',x.model_type,x.budget_proofs_verified?.proofs??0,x.budget_proofs_verified?.qualified??0,x.budget_proofs_verified?.subproblems??0,x.active_certificate_calls??null,x.active_certificate_seconds??null,x.transport_exclusions_verified??0,x.raw_pool_count??null,x.shortlist_count??null,x.final_cost_minus_raw_best??null,rat(x.final_budget_gamma),rat(x.final_budget_theta),x.final_budget_worst_load??null,x.final_output_source??'',m?.parent_snapshot_seconds??null,m?.polish_whole_seconds??null,x.model_statistics?.preparation_seconds??null,x.model_statistics?.MIP_seconds??null,x.budget_proofs_verified?.exact_cost_cuts??0,x.query_count??0,m?x.polish_history_count:null,x.LSS_accepted_count??null,m?x.polish_proposal_count:null,x.polish_accepted_novel??null,m?x.polish_MIP_count:null,m?.private_FFT_seconds??null,m?.proposal_seconds??null,m?.new_native_queries??null,m?m.seeds.length:null,m?(m.private_proposal_slice_expired||m.native_adjudication_slice_expired?1:0):null,x.parent_pool_count??null,m?.parent_best_cost??null];}));
const ranges=new Map();d.rows.forEach((x,i)=>{const key=x.case_index+'|'+x.arm;if(!ranges.has(key))ranges.set(key,[]);ranges.get(key).push(i+5);});
for(let i=0;i<d.groups.length;i++){
 const g=d.groups[i],cr=9+i,dr=25+i,mr=63+i,fr=102+i,rr=ranges.get(g.case_index+'|'+g.arm);
 if(rr.length!==30||rr.at(-1)-rr[0]!==29)throw Error('Group ordering');
 const rg=c=>`'运行明细'!${c}${rr[0]}:${c}${rr.at(-1)}`;
 for(const row of [cr,dr,mr,fr])write(s,`A${row}:B${row}`,[[g.case_index,names[g.arm]]]);
 s.getRange(`C${cr}:K${cr}`).formulas=[[
 `=SUM(${rg('E')})`,`=IF(COUNT(${rg('F')})>0,MIN(${rg('F')}),"")`,`=IF(C${cr}=30,AVERAGE(${rg('F')}),"")`,`=IF(C${cr}=30,IF(MAX(${rg('F')})=MIN(${rg('F')}),0,STDEV(${rg('F')})),"")`,`=IF(C${cr}=30,F${cr}/E${cr},"")`,`=IF(C${cr}>0,AVERAGEIFS(${rg('H')},${rg('E')},1),"")`,`=AVERAGE(${rg('H')})`,`=MAX(${rg('H')})`,`=30-C${cr}`]];
 s.getRange(`C${dr}:I${dr}`).formulas=[[
 `=IF(C${cr}=30,AVERAGE(${rg('K')}),"")`,`=COUNTIFS(${rg('F')},D${cr},${rg('E')},1)`,`=IF(D${dr}>0,AVERAGEIFS(${rg('K')},${rg('F')},D${cr},${rg('E')},1),"")`,`=IF(C${cr}>0,AVERAGEIFS(${rg('I')},${rg('E')},1),"")`,`=IF(C${cr}>0,AVERAGEIFS(${rg('J')},${rg('E')},1),"")`,`=COUNT(${rg('I')})`,`=IF(C${cr}=30,"完整30次","avg/std不可用")`]];
 const mean=c=>`=IF(COUNT(${rg(c)})>0,AVERAGE(${rg(c)}),"")`;
 s.getRange(`C${mr}:K${mr}`).formulas=[[mean('U'),g.arm==='D_R04_BUDGET_FFT'?mean('AW'):g.arm==='C_R02_CVAR_BUDGET'?mean('Z'):'=""',mean('AO'),mean('AP'),mean('AR'),mean('AQ'),mean('X'),mean('AI'),mean('AH')]];
 s.getRange(`C${fr}:H${fr}`).formulas=[[
 `=IF(C${cr}=30,AVERAGE(${rg('M')}),"")`,`=E${cr}`,`=COUNTIFS(${rg('AB')},">0.00000001",${rg('E')},1)`,`=IF(C${cr}=30,ROUND(AVERAGE(${rg('AB')}),9),"")`,`=AVERAGE(${rg('Z')})`,`=AVERAGE(${rg('AA')})`]];
}
section(23,'发现时间与阶段耗时（发现时间对应本run最终LSS返回解，不是全局最优证明）');
write(s,'A24:I24',[['算例','版本','最终解发现均时(s)','命中best次数','命中best均时(s)','有效搜索均时(s)','有效LSS均时(s)','搜索记录数','成本统计状态']]);header(s,'A24:I24');
section(39,'同seed配对：六对比×三例；成本、完整时间、有效率分别使用独立Holm18族');
write(s,'A40:K40',[['算例','候选','参照','完整30对','未舍入avg差','成本Holm18 p','完整均时差(s)','时间Holm18 p','有效率Holm18 p','成本原始p','时间原始p']]);header(s,'A40:K40');
write(s,'A41:K58',a.comparisons.map(c=>[c.case_index,names[c.candidate],names[c.reference],c.complete30?'是':'否',c.avg_diff,c.complete30?c.cost_p_holm18:null,c.whole_time_diff,c.complete30?c.time_p_holm18:null,c.validity_p_holm18,c.cost_p_raw,c.time_p_raw]));
section(61,'候选漏斗与开销（私人FFT只作提议；CDF秒是整数证书阶段，不涵盖所有浮点预筛）');
write(s,'A62:K62',[['算例','版本','母体合格候选均数','母体认证池均数','精炼提议均数','精炼新认证均数','私人FFT均时(s)','精炼MIP均数','CDF证书均时(s)','母体准备均时(s)','精炼全阶段均时(s)']]);header(s,'A62:K62');
section(77,'模型、时钟和统计限制');
const notes=[d.headline,
'R04是R02预算RO引导的经验机会约束精炼混合算法，精炼输出可能离开预算集合，不冒称相同鲁棒保护。',
'母体阶段固定前120秒，私人提议最多60秒并为原整数CDF留出搜索时钟44%；共同搜索430/LSS590/外guard595秒。',
'母体时间分配也是本版改动；不能将与R02的全部性能差异单独归因于FFT。全程包含加载、构造、保存fsync和退出。',
'8192格最近格点FFT使用指数阻尼12、周期2B及前缀/后缀共享；仍有格点与浮点误差，仅为提议评分。',
'通过原整数CDF才入原候选池；原shortlist、公共guide_cache、原LSS、私有随机流及抽样索引政策不变。',
'本run原数据生成RO种子，最多6个；固定3轮，信任域最多改5组，即翻转10个one-hot变量。没有旧解或LSS反馈。',
'avg/std要求30次全部独立有效；失败成本留空，best是本批观察值。成本、时间、有效率分别校正，未显著不等于等效。',
'阶段计时按已记录字段报告，不将整数CDF证书时间等同全部概率预筛开销，不用阶段之和伪造完整时钟。',
'探索版本和母体选择基于开发样本。全40仅在下述冻结门槛通过并核验fresh容量后另行登记，失败不补跑。',
'发现时间按首次通过原整数CDF认证入池的found_seconds记录，包含认证计算；不是第一次MIP提出或全局最优证明时间。'];
notes.forEach((x,i)=>{write(s,`A${78+i}`,[[x]]);s.getRange(`A${78+i}:K${78+i}`).format.rowHeightPx=28;});
section(99,'内部候选至原LSS终审：avg差异与低成本回退覆盖');
write(s,'A101:H101',[['算例','版本','内部最好成本均值','LSS最终avg','终审回退次数','平均回退成本','原候选池均数','短名单均数']]);header(s,'A101:H101');
section(117,'全40例前瞻门槛（均值不高于是本批门槛，不是统计等效证明）');
const descriptions=['R04/D02三例各30全有效且来源与时钟清洁','三例R04未舍入avg均不高于D02','至少一例R04成本Holm18显著更低','三例R04完整均时更低且时间Holm18均显著'];
Object.entries(gate.tests).forEach(([key,value],i)=>{write(s,`A${119+i}`,[[descriptions[i]]]);write(s,`H${119+i}`,[[value?'通过':'未通过']]);});
write(s,'A124',[[gate.L4_eligible?'L3门槛通过；仍需fresh容量核验与新的全40协议。':'未达到完整L3门槛，本批不扩展全40例。']]);
section(127,'原始文献与适配边界');
write(s,'A128',[['Fischetti & Lodi (2003), Local Branching：MIP距离邻域；本版不是完整全局分支算法。']]);
write(s,'A129',[['https://www.dei.unipd.it/~fisch/papers/local_branching.pdf']]);
write(s,'A130',[['Serang (2014), PLOS ONE e91507：独立和的卷积与共享计算；不据此把浮点量化评分称为精确概率。']]);
write(s,'A131',[['https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0091507']]);
write(s,'A132',[['母体：Bertsimas & Sim (2004), The Price of Robustness；具体ES95集合与D02保护范围不同。']]);
'ABCDEFGHIJK'.split('').forEach((c,i)=>width(s,c,[55,215,180,125,135,135,155,155,170,155,165][i]));
for(const [lo,hi] of [[9,20],[25,36],[41,58],[63,74],[102,113]])for(let n=lo;n<=hi;n++){s.getRange(`A${n}:K${n}`).format.rowHeightPx=28;if(n%2)s.getRange(`A${n}:K${n}`).format.fill='#F4F7FA';}
s.getRange('D9:F20').setNumberFormat('0.000000');s.getRange('G9:G20').setNumberFormat('0.000%');s.getRange('H9:J20').setNumberFormat('0.000');s.getRange('C25:C36').setNumberFormat('0.000');s.getRange('E25:G36').setNumberFormat('0.000');s.getRange('E41:E58').setNumberFormat('0.000000');s.getRange('G41:G58').setNumberFormat('0.000');for(const c of ['F','H','I','J','K'])s.getRange(`${c}41:${c}58`).setNumberFormat('0.000E+00');s.getRange('C63:F74').setNumberFormat('0.0');s.getRange('G63:K74').setNumberFormat('0.000');s.getRange('H63:H74').setNumberFormat('0.0');s.getRange('C102:D113').setNumberFormat('0.000000');s.getRange('F102:F113').setNumberFormat('0.000000');s.getRange('G102:H113').setNumberFormat('0.0');
s.getRange('C9:C20').conditionalFormats.add('cellIs',{operator:'lessThan',formula:30,format:{fill:'#FFF0DD',font:{color:'#9A3412'}}});
const letters=Array.from({length:50},(_,i)=>{let n=i+1,t='';while(n){n--;t=String.fromCharCode(65+n%26)+t;n=Math.floor(n/26);}return t;});
letters.forEach(c=>width(r,c,140));width(r,'B',225);width(r,'P',280);width(r,'Q',280);width(r,'R',520);width(r,'S',315);width(r,'AF',340);
r.getRange(`A5:AX${last}`).format.rowHeightPx=75;r.getRange(`P5:S${last}`).format.wrapText=true;r.getRange(`AF5:AF${last}`).format.wrapText=true;
for(const c of ['F','G','L','M','AB','AC','AD','AE','AX'])r.getRange(`${c}5:${c}${last}`).setNumberFormat('0.000000');for(const c of ['H','I','J','K','N','X','AG','AH','AI','AJ','AR','AS'])r.getRange(`${c}5:${c}${last}`).setNumberFormat('0.000');
r.freezePanes.freezeRows(4);r.freezePanes.freezeColumns(2);r.tables.add(`A4:AX${last}`,true,'RunRecords');
await wb.recalculate();console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'formula errors'})).ndjson);
const previews=[['对比统计','A2:G20','cost_preview.png'],['对比统计','H8:K20','time_preview.png'],['对比统计','A23:I36','discovery_preview.png'],['对比统计','A39:F58','comparison_cost_preview.png'],['对比统计','G40:K58','comparison_time_preview.png'],['对比统计','A61:F74','mechanism_count_preview.png'],['对比统计','G62:K74','mechanism_time_preview.png'],['对比统计','A77:K88','notes_preview.png'],['对比统计','A99:H113','fallback_preview.png'],['对比统计','A117:K132','gate_preview.png'],['运行明细','A1:K9','records_preview.png'],['运行明细','L4:V9','record_details_preview.png'],['运行明细','W4:AH9','model_headers_preview.png'],['运行明细','AI4:AX9','polish_headers_preview.png'],['运行明细','AC95:AX98','polish_values_preview.png']];
for(const [sheetName,range,file] of previews){const blob=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(root,file),new Uint8Array(await blob.arrayBuffer()));}
await fs.mkdir(path.join(root,'delivery'),{recursive:true});await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(root,'delivery/R04预算RO边界精炼_四版本_三大算例30次_对比统计.xlsx'));
console.log('EXPORTED',N);

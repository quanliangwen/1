import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/,'$1');
const read=async name=>JSON.parse(await fs.readFile(path.join(root,name),'utf8'));
const d=await read('FINAL_COMPARISON_AND_DIAGNOSIS.json'),a=await read('evidence/formal/FINAL_INDEPENDENT_AUDIT.json');
if(a.terminal!==360||a.global_errors.length)throw Error('Not fully audited');
const wb=Workbook.create(),s=wb.worksheets.add('对比统计'),r=wb.worksheets.add('运行明细');
const names={A_B01_ORIGINAL:'A 原B01',B_D02_TRANSPORT:'B D02·DRO',C_R02_CVAR_BUDGET:'C R02·预算RO',D_R03B_ENTROPIC:'D R03b·熵代理'};
const write=(sh,where,data)=>sh.getRange(where).values=data;
const rat=v=>v==null?null:typeof v==='string'&&v.includes('/')?Number(v.split('/')[0])/Number(v.split('/')[1]):Number(v);
const header=(sh,range)=>{let z=sh.getRange(range);z.format.fill='#203D51';z.format.font.color='#FFFFFF';z.format.font.bold=true;z.format.wrapText=true;z.format.rowHeightPx=46;z.format.horizontalAlignment='center';};
const section=(row,text)=>{write(s,`A${row}`,[[text]]);s.getRange(`A${row}:K${row}`).format.fill='#E8EEF2';s.getRange(`A${row}`).format.font.bold=true;s.getRange(`A${row}:K${row}`).format.rowHeightPx=28;};
const width=(sh,col,n)=>sh.getRange(`${col}:${col}`).format.columnWidthPx=n;
for(const [sh,range] of [[s,'A1:K116'],[r,'A1:AQ364']]){sh.showGridLines=false;sh.getRange(range).format.font.name='Arial';sh.getRange(range).format.font.size=10;sh.getRange(range).format.verticalAlignment='center';}
write(s,'A2',[['R03b熵风险代理：四版本、三大算例统一LSS测试']]);s.getRange('A2').format.font.size=16;s.getRange('A2').format.font.bold=true;
write(s,'A4',[[`360次终末，独立有效${a.independent_valid}/360；每组30次，同seed新鲜对照，最终只原LSS≥0.99。`]]);
write(s,'A5',[['19 LAB50·T63；35 APP30·T58；39 APP50·T91。完整600秒包括系数构造、模型、原CDF、LSS及保存退出。']]);
section(7,'成本、波动与完整运行时间（官方avg/std要求30次全有效；std为样本标准差）');
write(s,'A8:K8',[['算例','版本','有效/30','best','avg','样本std','CV','有效完整均时(s)','全部尝试均时(s)','完整最大(s)','失败次数']]);header(s,'A8:K8');
const columns=['算例','版本','重复','seed','独立有效1/0','最终成本','最终LSS','完整进程秒','搜索完成秒','LSS阶段秒','最终解首次发现秒','首次CDF接受成本','内部最好成本','峰值RSS GiB','退出码','失败分类','核验错误','最终选择','模型类型','新增模型证明数','新增模型合格候选数','新增模型MIP数','搜索CDF调用数','CDF证书秒','D02运输排除数','原候选池数','短名单数','终审回退成本','R02 Gamma','R02 theta','R02预算最坏和','R03b t','R03b eta','R03b权重上包络和','新增模型准备秒','新增模型MIP秒','精确成本剪枝数','模型查询数','已准备t表数','原LSS接受数','所选见证etaMax','R02 GammaMax','新增模型原始返回数'];
const N=d.rows.length,last=N+4;
write(r,'A1',[['来源：formal_FINAL_INDEPENDENT_AUDIT.json、不可变结果与原LSS轨迹；逐项数值包络和模型见证由独立读者核验。']]);
write(r,'A2',[['零与空白分开：失败成本为空；无对应模型参数为空。未新增真实概率抽样，熵惩罚不称为固定KL球；参数展示数值近似，精确有理数见证保留在JSON。']]);
write(r,'A4:AQ4',[columns]);header(r,'A4:AQ4');
write(r,`A5:AQ${last}`,d.rows.map(x=>[x.case_index,x.arm,x.rep,x.seed,x.valid?1:0,x.cost??null,x.LSS??null,x.process_wall_seconds,x.search_seconds??null,x.LSS_seconds??null,x.first_found_seconds??null,x.self_first_accepted_cost??null,x.raw_final_cost??null,x.peak_rss_bytes/2**30,x.rc,x.failure_class??'',x.errors.join(';'),x.selection?JSON.stringify(x.selection):'',x.model_type,x.budget_proofs_verified?.proofs??0,x.budget_proofs_verified?.qualified??0,x.budget_proofs_verified?.subproblems??0,x.active_certificate_calls??null,x.active_certificate_seconds??null,x.transport_exclusions_verified??0,x.raw_pool_count??null,x.shortlist_count??null,x.final_cost_minus_raw_best??null,rat(x.final_budget_gamma),rat(x.final_budget_theta),x.final_budget_worst_load??null,rat(x.final_entropic_t),rat(x.final_entropic_eta),x.final_entropic_sum_upper??null,x.model_statistics?.preparation_seconds??null,x.model_statistics?.MIP_seconds??null,x.budget_proofs_verified?.exact_cost_cuts??0,x.query_count??0,x.tables_prepared??null,x.LSS_accepted_count??null,rat(x.final_entropic_eta_max),rat(x.gamma_max),x.model_statistics?.raw_solver_candidates??null]));
const ranges=new Map();d.rows.forEach((x,i)=>{const key=x.case_index+'|'+x.arm;if(!ranges.has(key))ranges.set(key,[]);ranges.get(key).push(i+5);});
for(let i=0;i<d.groups.length;i++){
 const g=d.groups[i],cr=9+i,dr=25+i,mr=63+i,fr=102+i,rr=ranges.get(g.case_index+'|'+g.arm);
 if(rr.length!==30||rr.at(-1)-rr[0]!==29)throw Error('Group ordering');
 const rg=col=>`'运行明细'!${col}${rr[0]}:${col}${rr.at(-1)}`;
 for(const row of [cr,dr,mr,fr])write(s,`A${row}:B${row}`,[[g.case_index,names[g.arm]]]);
 s.getRange(`C${cr}:K${cr}`).formulas=[[
  `=SUM(${rg('E')})`,`=IF(COUNT(${rg('F')})>0,MIN(${rg('F')}),"")`,`=IF(C${cr}=30,AVERAGE(${rg('F')}),"")`,`=IF(C${cr}=30,IF(MAX(${rg('F')})=MIN(${rg('F')}),0,STDEV(${rg('F')})),"")`,`=IF(C${cr}=30,F${cr}/E${cr},"")`,
  `=IF(C${cr}>0,AVERAGEIFS(${rg('H')},${rg('E')},1),"")`,`=AVERAGE(${rg('H')})`,`=MAX(${rg('H')})`,`=30-C${cr}`]];
 s.getRange(`C${dr}:I${dr}`).formulas=[[
  `=IF(C${cr}=30,AVERAGE(${rg('K')}),"")`,`=COUNTIFS(${rg('F')},D${cr},${rg('E')},1)`,`=IF(D${dr}>0,AVERAGEIFS(${rg('K')},${rg('F')},D${cr},${rg('E')},1),"")`,`=IF(C${cr}>0,AVERAGEIFS(${rg('I')},${rg('E')},1),"")`,`=IF(C${cr}>0,AVERAGEIFS(${rg('J')},${rg('E')},1),"")`,`=COUNT(${rg('I')})`,`=IF(C${cr}=30,"完整30次","avg/std不可用")`]];
 s.getRange(`C${mr}:J${mr}`).formulas=[[
  `=AVERAGE(${rg('W')})`,`=AVERAGE(${rg('X')})`,`=AVERAGE(${rg('Y')})`,`=AVERAGE(${rg('T')})`,`=AVERAGE(${rg('U')})`,`=AVERAGE(${rg('V')})`,`=AVERAGE(${rg('AK')})`,`=IF(COUNT(${rg('AI')})>0,AVERAGE(${rg('AI')}),"")`]];
 s.getRange(`C${fr}:H${fr}`).formulas=[[
  `=IF(C${cr}=30,AVERAGE(${rg('M')}),"")`,`=E${cr}`,`=COUNTIFS(${rg('AB')},">0.00000001",${rg('E')},1)`,`=IF(C${cr}=30,ROUND(AVERAGE(${rg('AB')}),9),"")`,`=AVERAGE(${rg('Z')})`,`=AVERAGE(${rg('AA')})`]];
}
section(23,'发现时间与阶段耗时（发现时间对应本run最终LSS返回解，不是全局最优证明）');
write(s,'A24:I24',[['算例','版本','最终解发现均时(s)','命中best次数','命中best均时(s)','有效搜索均时(s)','有效LSS均时(s)','搜索记录数','成本统计状态']]);header(s,'A24:I24');
section(39,'同seed配对比较：四臂六对比×三例，成本与有效率分别Holm18');
write(s,'A40:I40',[['算例','候选','参照','完整30对','未舍入avg差','成本原始p','成本Holm18 p','有效率Holm18 p','限制']]);header(s,'A40:I40');
write(s,'A41:I58',a.comparisons.map(c=>[c.case_index,names[c.candidate],names[c.reference],c.complete30?'是':'否',c.avg_diff,c.cost_p_raw,c.complete30?c.cost_p_holm18:null,c.validity_p_holm18,c.complete30?'':'不足完整30对']));
section(61,'搜索机制诊断（新增模型指R02或熵代理；B01/D02的对应扩展未启用）');
write(s,'A62:J62',[['算例','版本','搜索CDF调用均数','CDF证书均时(s)','D02排除均数','新增模型证明均数','新增合格候选均数','新增MIP均数','成本剪枝均数','新增准备均时(s)']]);header(s,'A62:J62');
section(77,'模型和统计限制');
const notes=[d.headline,
 'R03b是经验熵风险/Chernoff代理，具有KL惩罚表示；不是指定半径KL球DRO，也不声称总体覆盖。',
 't固定为0.10/0.16/0.25/0.40/0.60/0.85，eta最低0.8。eta低于ln100时，代理单独不再给出.99充分保证。',
 'GMP 192-bit有向包络构造权重；独立208-bit重建，另300-bit标量核验。数值包络不是统计置信区间。',
 '每run从当前原始500样本自生成系数与起点；没有旧解、外部MIP start、跨重复算法缓存或LSS反馈调参。',
 '原LSS、原短名单、私有随机流和0..499索引不变；完整时间从Popen前到退出，含全部系数/模型/保存。',
 'avg/std要求30次全部独立有效；失败成本留空；best是本批观察最好值。未显著不等于等效。',
 '内部成本剪枝不保证保留所有更贵的LSS回退候选；必须同时查看终审回退与最终avg/std。',
 't使用原单位，固定网格不保证对单位缩放不变。小例确认代理可能排除CDF可行低成本向量，不能普遍宣称优于R02。',
 '尚未扩全40例；R03b完整统计后才开始R04。耗时为本硬件本批60并发的描述性结果。'];
notes.forEach((x,i)=>{write(s,`A${78+i}`,[[x]]);s.getRange(`A${78+i}:K${78+i}`).format.rowHeightPx=28;});
section(91,'文献');
write(s,'A92',[['Nemirovski & Shapiro (2006), Convex Approximations of Chance Constrained Programs, DOI 10.1137/050622328。']]);
write(s,'A93',[['https://www2.isye.gatech.edu/~nemirovs/SIOPT_Bern_2006.pdf']]);
write(s,'A94',[['Föllmer & Knispel, Convex Risk Measures…, §4.6.1：熵风险的相对熵惩罚变分表示。']]);
write(s,'A95',[['https://www2.mathematik.hu-berlin.de/~foellmer/papers/RiskMeasures_FoellmerKnispel.pdf']]);
section(99,'内部候选至LSS最终输出：avg差异与回退覆盖');
write(s,'A101:H101',[['算例','版本','内部最好成本均值','LSS最终avg','终审回退次数','平均回退成本','原候选池均数','短名单均数']]);header(s,'A101:H101');
'ABCDEFGHIJK'.split('').forEach((c,i)=>width(s,c,[55,205,125,125,125,125,100,150,165,150,100][i]));
for(const [lo,hi] of [[9,20],[25,36],[41,58],[63,74],[102,113]])for(let n=lo;n<=hi;n++){s.getRange(`A${n}:K${n}`).format.rowHeightPx=28;if(n%2)s.getRange(`A${n}:K${n}`).format.fill='#F4F7FA';}
s.getRange('D9:F20').setNumberFormat('0.000000');s.getRange('G9:G20').setNumberFormat('0.000%');s.getRange('H9:J20').setNumberFormat('0.000');s.getRange('C25:C36').setNumberFormat('0.000');s.getRange('E25:G36').setNumberFormat('0.000');s.getRange('E41:E58').setNumberFormat('0.000000');s.getRange('F41:H58').setNumberFormat('0.000E+00');s.getRange('C63:J74').setNumberFormat('0.0');s.getRange('D63:D74').setNumberFormat('0.000');s.getRange('J63:J74').setNumberFormat('0.000');s.getRange('C102:D113').setNumberFormat('0.000000');s.getRange('F102:F113').setNumberFormat('0.000000');s.getRange('G102:H113').setNumberFormat('0.0');
s.getRange('C9:C20').conditionalFormats.add('cellIs',{operator:'lessThan',formula:30,format:{fill:'#FFF0DD',font:{color:'#9A3412'}}});
const letters=Array.from({length:43},(_,i)=>{let n=i+1,t='';while(n){n--;t=String.fromCharCode(65+n%26)+t;n=Math.floor(n/26);}return t;});
letters.forEach(c=>width(r,c,130));width(r,'B',225);width(r,'P',280);width(r,'Q',280);width(r,'R',520);width(r,'S',255);for(const c of ['AC','AD','AF','AG','AO','AP']){width(r,c,220);r.getRange(`${c}5:${c}${last}`).format.wrapText=true;}
r.getRange(`A5:AQ${last}`).format.rowHeightPx=75;r.getRange(`P5:S${last}`).format.wrapText=true;r.getRange(`F5:G${last}`).setNumberFormat('0.000000');for(const rg of [`H5:K${last}`,`N5:N${last}`,`X5:X${last}`,`AI5:AJ${last}`])r.getRange(rg).setNumberFormat('0.000');r.getRange(`L5:M${last}`).setNumberFormat('0.000000');r.getRange(`AB5:AB${last}`).setNumberFormat('0.000000');r.getRange(`AE5:AE${last}`).setNumberFormat('0.000000');r.getRange(`AH5:AH${last}`).setNumberFormat('0.000000');for(const col of ['AC','AD','AF','AG','AO','AP'])r.getRange(col+'5:'+col+last).setNumberFormat('0.000000');r.freezePanes.freezeRows(4);r.freezePanes.freezeColumns(2);r.tables.add(`A4:AQ${last}`,true,'RunRecords');
await wb.recalculate();console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},summary:'formula errors'})).ndjson);
const previews=[['对比统计','A2:G20','cost_preview.png'],['对比统计','H8:K20','time_preview.png'],['对比统计','A23:I36','discovery_preview.png'],['对比统计','A39:I58','comparison_preview.png'],['对比统计','A61:J74','mechanism_preview.png'],['对比统计','A77:K95','notes_preview.png'],['对比统计','A99:H113','fallback_preview.png'],['运行明细','A1:K10','records_preview.png'],['运行明细','L4:V10','record_details_preview.png'],['运行明细','W4:AH10','risk_headers_preview.png'],['运行明细','AI4:AQ10','funnel_headers_preview.png'],['运行明细','AC95:AQ99','entropy_values_preview.png']];
for(const [sheetName,range,file] of previews){const blob=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(root,file),new Uint8Array(await blob.arrayBuffer()));}
await fs.mkdir(path.join(root,'delivery'),{recursive:true});await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(root,'delivery/R03b熵代理_四版本_三大算例30次_对比统计.xlsx'));
console.log('EXPORTED',N);

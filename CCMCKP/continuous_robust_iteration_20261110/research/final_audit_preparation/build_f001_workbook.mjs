// Author only after the real, independently audited 1200-run cohort is complete.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
const H=path.dirname(fileURLToPath(import.meta.url));
const input=path.join(H,'formal/F001_I002_40x30/FINAL_AUDIT_STATS.json');
const bytes=await fs.readFile(input), data=JSON.parse(bytes);
if(!data.integrity_passed || data.registered_attempts!==1200 || data.details.length!==1200 || data.summary.length!==40) throw Error('Real complete audited cohort required');
const ordered=[...data.details].sort((a,b)=>a.index-b.index||a.seed-b.seed);
const ids=new Set(ordered.map(r=>`${r.index}/${r.seed}`));
if(ids.size!==1200) throw Error('Duplicate registered attempt');
for(const s of data.summary){
  const rows=ordered.filter(r=>r.index===s.index);
  if(rows.length!==30 || rows.filter(r=>r.protocol_valid).length!==s.protocol_valid) throw Error('Run coverage inconsistent');
}
const O=path.join(H,'outputs/F001_final');await fs.mkdir(O,{recursive:true});
const wb=Workbook.create();
const names=['汇总40','运行明细1200','LSS调用','证书独立复核','验收与来源'];
const sheets=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
function col(k){let s='';for(k++;k;k=Math.floor((k-1)/26))s=String.fromCharCode(65+(k-1)%26)+s;return s;}
function table(name,title,headers,rows,widths){
 const sh=sheets[name],end=col(headers.length-1),last=4+rows.length;
 sh.showGridLines=false;
 sh.getRange(`A2:${end}${last}`).format.font={name:'Microsoft YaHei',size:10,color:'#263445'};
 sh.getRange(`A2:${end}${last}`).format.rowHeightPx=24;
 sh.getRange('A2').values=[[title]];sh.getRange('A2').format.font={size:14,bold:true};
 sh.getRange(`A4:${end}4`).values=[headers];
 sh.getRange(`A4:${end}4`).format.fill='#23415D';
 sh.getRange(`A4:${end}4`).format.font={color:'#FFFFFF',bold:true};
 sh.getRange(`A4:${end}4`).format.horizontalAlignment='center';
 sh.getRange(`A4:${end}4`).format.rowHeightPx=32;
 if(rows.length)sh.getRange(`A5:${end}${last}`).values=rows;
 widths.forEach((w,i)=>sh.getRange(`${col(i)}2:${col(i)}${last}`).format.columnWidthPx=w);
 if(rows.length>40)sh.freezePanes.freezeRows(4);
 if(headers.length>12)sh.freezePanes.freezeColumns(4);
 if(rows.length)sh.tables.add(`A4:${end}${last}`,true,`Data${names.indexOf(name)+1}`).showFilterButton=true;
 return sh;
}
const drows=ordered.map(r=>[r.index,r.instance,r.tmax,r.seed,Number(r.joint_accepted),Number(r.protocol_valid),r.protocol_valid?r.cost:null,r.search_seconds,r.search_wall_seconds,r.logical_MC_seconds,r.LSS_tested,r.LSS_rejected,r.new_calls_charged_to_run,r.real_probability??null,r.original_raw_lower??null,r.independent_raw_lower??null,r.LSS_key??'',r.raw_recount_key??'',r.selection?.join(',')??'',r.post_error?String(r.post_error):r.search_exit!==0?String(r.search_exit):r.within_budget?'':'search budget overrun',r.cost??null]);
const detail=table(names[1],'F001 · 全部登记运行（失败保留）',['ID','算例','T','搜索种子','双门槛通过','协议有效','有效成本','搜索秒','搜索墙钟秒','逻辑LSS秒','LSS测试数','LSS拒绝数','本次新调用','LSS真实概率','原证书下界','独立重算下界','LSS身份SHA256','重算身份SHA256','选择向量','错误或超时','选择成本原值'],drows,[45,185,65,95,100,85,108,95,108,115,95,95,100,115,115,120,540,540,540,330,110]);
detail.getRange('G5:J1204').setNumberFormat('0.000000');
detail.getRange('N5:P1204').setNumberFormat('0.00000000');detail.getRange('U5:U1204').setNumberFormat('0.000000');
const sums=[...data.summary].sort((a,b)=>(a.instance.startsWith('APP')?0:1)-(b.instance.startsWith('APP')?0:1)||a.index-b.index);
const summary=table(names[0],'F001 · 40 算例 × 30 次',['ID','算例','T','历史Best','本轮Best','本轮Avg','Std(P)','Avg−Best','Avg−原Best','搜索Time(s)','有效/30','原样本下界最小','LSS概率最小'],sums.map(s=>[s.index,s.instance,s.tmax,s.old_best,null,null,null,null,null,null,null,s.minimum_independent_raw_lower,s.minimum_real_probability]),[44,180,60,110,110,110,105,110,120,120,85,135,130]);
summary.tabColor='#23415D';
for(let j=0;j<sums.length;j++){
 const s=sums[j],r=j+5,start=ordered.findIndex(x=>x.index===s.index)+5,end=start+29;
 const g=`'运行明细1200'!G${start}:G${end}`,h=`'运行明细1200'!H${start}:H${end}`,f=`'运行明细1200'!F${start}:F${end}`;
 summary.getRange(`E${r}:K${r}`).formulas=[[
  `=IF(COUNT(${g})>0,MIN(${g}),"")`,`=IF(K${r}=30,AVERAGE(${g}),"")`,
  `=IF(K${r}=30,STDEV.P(${g}),"")`,`=IF(K${r}=30,ROUND(F${r}-E${r},9),"")`,
  `=IF(K${r}=30,ROUND(F${r}-D${r},9),"")`,`=AVERAGE(${h})`,`=SUM(${f})`]];
}
summary.getRange('D5:J44').setNumberFormat('0.000000');summary.getRange('L5:M44').setNumberFormat('0.00000000');
summary.getRange('K5:K44').conditionalFormats.add('cellIs',{operator:'lessThan',formula:'30',format:{fill:'#FDE8E7',font:{color:'#A12622',bold:true}}});
const mc=data.all_used_native_receipts;
const m=table(names[2],'原 LSS · 唯一调用身份（包括拒绝）',['算例','T','点估计概率','达到0.985','正式前已存在','原调用秒','种子','抽样数','身份SHA256','原记录SHA256','选择向量'],mc.map(r=>[r.instance,r.capacity,r.probability,Number(r.passed),Number(r.was_preexisting),r.seconds,data.MC_seed,data.MC_draws_per_identity,r.key,r.sha256,r.selection.join(',')]),[185,65,120,110,130,110,100,110,540,540,540]);
m.getRange(`C5:C${mc.length+4}`).setNumberFormat('0.0000000');m.getRange(`F5:F${mc.length+4}`).setNumberFormat('0.000');
const raw=data.independent_raw_recounts;
const p=table(names[3],'原样本 · 选中证书独立重算',['算例','T','下界','原方法','独立方法','原格数','精确计数分子','精确计数分母','重算身份SHA256','选择向量'],raw.map(r=>[r.instance,r.capacity,r.lower,r.original_method,r.method,r.original_bins??'',r.numerator,r.denominator,r.key,r.selection.join(',')]),[185,65,120,330,390,95,540,540,540,540]);
p.getRange(`C5:C${raw.length+4}`).setNumberFormat('0.00000000');p.getRange(`G5:H${raw.length+4}`).setNumberFormat('@');
const notes=[
 ['原样本门槛','全部原始样本；严格事件 sum<T；整数证书下界≥0.99。'],
 ['原LSS门槛','原 real_P_test 完整源码；1000万次，seed=832273，事件 sum≤T；点估计≥0.985。'],
 ['验收流程','冻结搜索后按成本排序调用原LSS，选首个通过成员；真实参数只用于外部验收。'],
 ['Avg与Std','仅全部30次协议有效才给Avg/Std；Std为总体标准差(ddof=0)；所有失败保留。'],
 ['搜索Time','30次搜索秒平均；真实仿真时间另列，逻辑复用时间不等于本次实际新调用时间。'],
 ['历史Best','来自用户原统计表；缺少相应可行向量时，单凭旧成本不能证明联合可行或不可能。'],
 ['重复调用','完整身份一致的LSS记录在外部复用；固定MC种子，不能称1200次独立MC估计。'],
 ['完整性审计',data.integrity_passed?'通过':'失败'],['1200次全合格',data.all1200_qualified?'是':'否'],
 ['登记次数',data.registered_attempts],['协议有效次数',data.protocol_valid],['双门槛通过次数',data.joint_accepted],
 ['实际使用唯一MC身份',data.unique_used_MC_keys],['逻辑MC调用次数',data.total_logical_MC_calls],
 ['正式新增成功MC调用',data.physical_new_successful_MC_calls],['正式新增调用尝试',data.physical_new_invocation_attempts],
 ['新增MC调用墙钟秒合计',data.physical_new_native_call_wall_seconds],['逻辑MC秒合计（含复用）',data.total_logical_MC_seconds],
 ['正式前已有MC记录',data.native_inventory_before],['数据文件SHA256',createHash('sha256').update(bytes).digest('hex')],
 ['独立复核程序SHA256',data.raw_recount_verifier_sha256],
 ['GitHub任务目录','https://github.com/quanliangwen/1/tree/main/CCMCKP/continuous_robust_iteration_20261110'],
 ...Object.entries(data.source_sha256).map(([k,v])=>[`冻结源码 ${k}`,v]),
 ...data.protocol_errors.map(r=>[`异常 ${r.index}/${r.seed}/${r.stage}`,String(r.error)])];
table(names[4],'F001 · 验收定义、计时与源码身份',['项目','定义或审计值'],notes,[300,1080]);
wb.recalculate();
// Compare calculated results against independently computed Python statistics.
const actual=summary.getRange('D5:M44').values;
for(let j=0;j<sums.length;j++){
 const s=sums[j],expected=[s.old_best,s.best,s.avg,s.std,s.avg_minus_own_best,s.avg_minus_old_best,s.mean_search_seconds,s.protocol_valid,s.minimum_independent_raw_lower,s.minimum_real_probability];
 for(let k=0;k<expected.length;k++){
  const a=actual[j][k],b=expected[k];
  if(b===null){if(a!==null && a!=='')throw Error(`Expected missing ${j}/${k}: ${a}`);}
  else if(typeof a!=='number'||Math.abs(a-b)>1e-7)throw Error(`Formula/statistics mismatch ${j}/${k}: ${a} vs ${b}`);
 }
}
for(const n of names){
 const sh=sheets[n];for(const row of sh.getUsedRange().values)for(const v of row)if(typeof v==='string'&&/^#(REF!|DIV\/0!|VALUE!|NAME\?|NUM!|N\/A|SPILL!)/.test(v))throw Error(`Formula error ${n}: ${v}`);
}
const inspection=await wb.inspect({kind:'region',sheetId:names[0],range:'A4:M12',maxChars:5000});
await fs.writeFile(path.join(O,'inspection.json'),JSON.stringify(inspection,null,2));
const ranges=[['summary_all',names[0],'A1:M44'],['detail_first',names[1],'A1:P16'],['detail_last',names[1],'A1199:P1204'],['native',names[2],`A1:H${Math.min(mc.length+4,16)}`],['raw',names[3],`A1:F${Math.min(raw.length+4,16)}`],['method',names[4],'A1:B24']];
for(const [file,sheetName,range]of ranges){const img=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(O,file+'.png'),new Uint8Array(await img.arrayBuffer()));}
const output=await SpreadsheetFile.exportXlsx(wb);await output.save(path.join(O,'F001_40cases_30runs.xlsx'));
await fs.writeFile(path.join(O,'AUTHORING_CHECK.json'),JSON.stringify({real_complete_cohort:true,all_formula_statistics_matched:true,formula_errors:0,all_sheets_rendered:true,model_visual_review_pending:true,source_sha256:createHash('sha256').update(bytes).digest('hex'),sheet_names:names},null,2));
console.log(JSON.stringify({exported:path.join(O,'F001_40cases_30runs.xlsx'),visual_review_pending:true}));

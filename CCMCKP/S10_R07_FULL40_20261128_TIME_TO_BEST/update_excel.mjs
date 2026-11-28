import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const R=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(R,'statistics.json'),'utf8'));
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(R,'../delivery/R07_全40算例_30次_结果汇总.xlsx')));
const s=wb.worksheets.getItem('40例汇总'),d=wb.worksheets.getItem('1200次明细');
const before=[s.getRange('A7:K47').values,d.getRange('A7:I1207').values];
s.getRange('L7:M47').copyFrom(s.getRange('J7:K47'),'all');
d.getRange('J7:K1207').copyFrom(d.getRange('H7:I1207'),'all');
s.getRange('L7:M7').values=[['命中Best\n次数','首次达Best\n平均时间(s)']];
d.getRange('J7:K7').values=[['输出解首次\n找到时间(s)','命中本例Best\n(1=是)']];
s.getRange('L:L').format.columnWidth=14;s.getRange('M:M').format.columnWidth=21;
d.getRange('J:J').format.columnWidth=22;d.getRange('K:K').format.columnWidth=19;
d.getRange('J8:J1207').values=data.rows.map(r=>[r.first_best_found_seconds]);
// Hit flags compare final unrounded LSS-accepted costs with the group minimum.
for(let i=0;i<40;i++){
 const r=i+8,lo=8+30*i,hi=lo+29;
 d.getRange(`K${lo}:K${hi}`).formulas=Array.from({length:30},(_,j)=>[`=IF(F${lo+j}=MIN($F$${lo}:$F$${hi}),1,0)`]);
 s.getRange(`L${r}:M${r}`).formulas=[[
  `=COUNTIFS('1200次明细'!$K$${lo}:$K$${hi},1)`,
  `=AVERAGEIFS('1200次明细'!$J$${lo}:$J$${hi},'1200次明细'!$K$${lo}:$K$${hi},1)`]];
}
s.getRange('A5').values=[['M列：仅平均命中本例30次Best的运行，取输出解首次找到时间；L列为命中次数，单位秒。']];
d.getRange('A5').values=[['J列从进程启动计时，取解首次通过内部CDF认证的时间；该解已通过最终原LSS验收。']];
s.getRange('L8:L47').setNumberFormat('0');s.getRange('M8:M47').setNumberFormat('0.000');
d.getRange('J8:J1207').setNumberFormat('0.000');d.getRange('K8:K1207').setNumberFormat('0');
wb.recalculate();
let maxDelta=0;
for(let i=0;i<40;i++){
 const a=s.getRange(`L${i+8}:M${i+8}`).values[0],g=data.groups[i];
 if(a[0]!==g.best_hit_count||Math.abs(a[1]-g.best_hit_first_mean_seconds)>1e-8)throw Error('timing mismatch '+i);
 maxDelta=Math.max(maxDelta,Math.abs(a[1]-g.best_hit_first_mean_seconds));
}
const after=[s.getRange('A7:K47').values,d.getRange('A7:I1207').values];
if(JSON.stringify(before)!==JSON.stringify(after))throw Error('Original table values changed');
await fs.writeFile(path.join(R,'INSPECT.ndjson'),(await wb.inspect({kind:'table',range:"'40例汇总'!J7:M18",include:'values,formulas',tableMaxRows:12,tableMaxCols:4,maxChars:4500})).ndjson);
await fs.writeFile(path.join(R,'ERROR_SCAN.ndjson'),(await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10},maxChars:2000})).ndjson);
for(const [sheetName,range,name] of [['40例汇总','J7:M20','timing_preview.png'],['1200次明细','F7:K18','detail_time_preview.png']]){
 const p=await wb.render({sheetName,range,scale:1.5,format:'png'});await fs.writeFile(path.join(R,name),new Uint8Array(await p.arrayBuffer()));
}
const x=await SpreadsheetFile.exportXlsx(wb);await x.save(path.join(R,'delivery/R07_全40算例_结果汇总_含首次最优均时.xlsx'));
await fs.writeFile(path.join(R,'WORKBOOK_QA.json'),JSON.stringify({status:'PASS',original_tables_preserved:true,all_40_conditional_time_means_checked:true,max_delta:maxDelta,hit_flags:1200,creator:'@oai/artifact-tool'},null,2));
console.log(JSON.stringify({status:'PASS',max_delta:maxDelta}));

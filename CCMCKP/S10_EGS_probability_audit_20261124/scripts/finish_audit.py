from pathlib import Path
from fractions import Fraction
from collections import Counter
import hashlib,json,shutil,subprocess,sys
R=Path(__file__).resolve().parent;D=R/'delivery'
OLD=Path('E:/codex/S10_EGS_large_pilot_20261123/evidence')
SRC=Path('E:/codex/S10_EGS_OA_20261123/source')
sha=lambda b:hashlib.sha256(b).hexdigest()
p=subprocess.run([sys.executable,'-X','utf8','E:/codex/S10_EGS_OA_20261123/remote.py',str(R/'check_server_remote.py')],capture_output=True,check=True)
remote=json.loads(p.stdout.decode('utf-8'))
assert remote['status']=='PASS'
(D/'SERVER_SOURCE_AND_BINARY_VERIFICATION.json').write_text(json.dumps(remote,ensure_ascii=False,indent=2),encoding='utf-8')
A=json.loads((OLD/'INDEPENDENT_AUDIT_STATISTICS.json').read_text())
examples=[];low=[];hist=Counter()
for row in A['runs']:
    folder=OLD/'runs'/row['identity'];outcome=json.loads((OLD/'outcomes'/(row['identity']+'.json')).read_text())
    names=['RESULT.json','ORIGINAL_LSS_DECISION_TRACE.json','S10_search.json','S10_search.run.json']
    for name in names:
        f=folder/name;assert sha(f.read_bytes())==outcome['output_files'][name]['sha256']
    result=json.loads((folder/'RESULT.json').read_text());raw=json.loads((folder/'S10_search.json').read_text())
    trace=json.loads((folder/'ORIGINAL_LSS_DECISION_TRACE.json').read_text())
    selected=result['selection'];source=next(c for c in raw['candidate_shortlist'] if c['selection']==selected)
    cert=source['certificate'];assert int(cert['lower_numerator'])*100>=int(cert['denominator'])*99
    accepted=[{'stage':x['stage'],'probability':x['probability']} for x in trace if x['selection']==selected and x['probability']>=.99]
    assert accepted,'Final output was never admitted by LSS?'
    item={'identity':row['identity'],'case_index':row['case_index'],'arm':row['arm'],'rep':row['rep'],
        'full_empirical_certificate_lower':float(Fraction(int(cert['lower_numerator']),int(cert['denominator']))),
        'full_empirical_certificate_upper':float(Fraction(int(cert['upper_numerator']),int(cert['denominator']))),
        'original_LSS_admissions_for_final_selection':accepted,'final_LSS_probability':result['original_LSS_confidence'],
        'parametric_MC_probability_report':result['recorded_real_probability'],'realP_draws':10000000,
        'result_sha256':outcome['output_files']['RESULT.json']['sha256'],
        'trace_sha256':outcome['output_files']['ORIGINAL_LSS_DECISION_TRACE.json']['sha256']}
    if result['original_LSS_confidence']<.99:low.append(item);hist[(row['case_index'],row['arm'])]+=1
    if row['rep']==1:examples.append(item)
assert len(low)==48 and sum(r['valid'] for r in A['runs'])==222
observations={'scope':'existing 270-run batch; read-only, no new probability sampling',
    'all270_final_selections_had_prior_LSS_admission_ge99':True,'all270_final_selections_had_full_sample_integer_certificate_ge99':True,
    'final_LSS_below99_count':len(low),'realP_report_below99_count':270,
    'source_audit_sha256':sha((D/'SERVER_SOURCE_AND_BINARY_VERIFICATION.json').read_bytes()),
    'below99_by_case_arm':[{'case_index':i,'arm':a,'count':n} for (i,a),n in sorted(hist.items())],
    'representative_first_repetitions':examples,'all_final_LSS_below99_records':low}
(D/'EXISTING_RUN_TRACE_EVIDENCE.json').write_text(json.dumps(observations,ensure_ascii=False,indent=2),encoding='utf-8')
def line(file,text):return next(i for i,l in enumerate((SRC/file).read_text().splitlines(),1) if text in l)
anchors={
 'lss_mode':{'file':'evaluation.cpp','line':line('evaluation.cpp','exact(std::pow')},
 'lss_MC_last_sample_excluded':{'file':'evaluation.cpp','line':line('evaluation.cpp','numpy.below(L - 1)')},
 'LSS_strict_boundary':{'file':'evaluation.cpp','line':line('evaluation.cpp','return double(std::count_if(sums.begin()')},
 'realP_generator':{'file':'report.cpp','line':line('report.cpp','double real_probability(')},
 'realP_closed_boundary':{'file':'report.cpp','line':line('report.cpp','x <= capacity')},
 'LSS_admission':{'file':'report.cpp','line':line('report.cpp','row.probability >= .99')},
 'LSS_recheck_without_filter':{'file':'report.cpp','line':line('report.cpp','for (auto& row : cost)')},
 'legacy_Mlist_wrong_target':{'file':'report.cpp','line':line('report.cpp','mc.at(cost.size() - 1).probability')},
 'main_output_cost_front':{'file':'report.cpp','line':line('report.cpp','const Row outputs[]')},
 'binomial_draw_default':{'file':'report.hpp','line':line('report.hpp','10000000')},
 'mutable_LSS_RNG':{'file':'evaluation.hpp','line':line('evaluation.hpp','LegacyRandom numpy')},
 'integer_raw_threshold':{'file':'evaluation.hpp','line':line('evaluation.hpp','lower * 100 >= denominator * 99')},
}
(D/'CODE_LINE_ANCHORS.json').write_text(json.dumps(anchors,ensure_ascii=False,indent=2),encoding='utf-8')
base='https://github.com/quanliangwen/1/blob/4fadf036407a938aeab96412962f53199428ed47/CCMCKP/S10_EGS_OA_20261123/source/'
links={name:base+v['file']+'#L'+str(v['line']) for name,v in anchors.items()}
(D/'SOURCE_LINKS.json').write_text(json.dumps(links,ensure_ascii=False,indent=2),encoding='utf-8')
text='''S10与EGS概率评价及最终验收代码核查（2026-11-24）

结论
以用户上传的S10_Cpp_Gurobi_Unified_Source.zip为基准，评价/报告/输入加载/随机数等10个关键文件逐字节相同，原始证书接受及最终复核等4个搜索函数正文相同。实际服务器的原S10构建源码、EGS构建源码和试点源码均匹配；实际运行二进制也匹配本批冻结SHA。椭球改动没有另换概率评价器，没有把椭球约束变成最终验收，也没有按真实概率报告筛选输出。
本次仅检查源码与既有270次记录，没有修改源码、输入、旧结果，没有重跑算法或额外蒙特卡洛。

一、代码中有三层不同的概率口径
1. 搜索原始证书：使用每项全部原始_sample样本，在独立边际经验乘积分布上做精确整数网格计数，要求下界>=99/100。它约束经验分布，不等于对生成分布的保证。
2. 原LSS：仍使用_sample文件。样本数L、组数m满足L^m<10^7走原精确分支，否则先做原快速检查，再用100万次经验重采样估计P(sum<T)。本轮三个大算例全走蒙特卡洛分支。LSS对象内的随机流随每次调用推进，同一解反复评价可有不同数值。
3. 原real_probability报告：读取_dist参数，按原分布生成器另外生成1000万次；固定seed832273，事件为sum<=T。APP仍按原代码包含尾部偏移逻辑。这个值是生成分布下的蒙特卡洛报告值，并非已知精确真实概率；它只用于报告，没有反馈给搜索，也没有作为输出门槛。
因此，将500条经验样本重采样100万次，并不等于取得100万条新的生成分布观测。优化和LSS重采样用相同经验样本，也不是独立的分布外验证。有限样本的分布近似与优化后的选解效应都可能造成经验概率与生成分布报告不同；当前检查不能把差距精确归因给单一机制。

二、确认存在的原代码遗留问题
A. LSS蒙特卡洛漏掉最后一个样本。
evaluation.cpp的instance.samples[j][numpy.below(L-1)]，而rng.hpp的below(n)只生成0..n-1。因此L=500时实际抽0..498，共499个样本；索引499永不抽到。原始整数证书使用全部500个样本，LSS的蒙特卡洛中心与它并不严格相同。原S10压缩包已存在这行，EGS未引入。漏掉的最后一项对概率影响方向取决于具体样本，不能笼统认定一定偏乐观。
B. 入队检查后复检覆盖概率，输出前没有重新过滤。
report.cpp只有候选入队时按p>=.99筛选。之后对cost队列每个解再评价两次，并把后一次概率覆盖row.probability；没有删除最终值<.99的项。最终主输出直接取cost.front()，返回status=completed。real_probability随后只报告，不拦截。因此“曾经通过LSS入队”“最终LSS值>=.99”“进程rc0”是不同条件。
既有270次记录中，270个最终选择都能找到先前LSS>=.99的入队记录，也都有全部样本的整数证书；其中48次最终LSS值又低于.99，程序仍正常输出。这48次在本轮独立统计中判无效，未补跑。
C. 其他保留的旧行为。
概率队列mc的复检把值写入mc.at(cost.size()-1)，而不是当前mc[j]。这影响概率队列及其他输出变体的语义；主输出是cost.front()，不能把它直接认定为主输出真实概率偏低的原因。
精确分支与MC分支在阈值边界处的处理也不完全统一：原LSS MC用<T，生成分布报告用<=T。后一个事件包含前一个；若在同一分布上，它不会解释“真实概率更低”的方向。本轮保留了原行为。

三、原口径一致性的范围
确认的是“与这次上传的C++源码包一致”。没有据此宣布更早Python实现、分布生成器与论文的全部细节都已重新证明正确。相同评价代码和参数，也不意味着不同候选列表会消耗相同位置的随机流，因此不同搜索流程的LSS数值不必逐项相同。
之前把“LSS通过”概括得过于笼统，需要澄清：旧程序只在入队时检查.99，没有对主输出最终复检值做强制拦截；222/270是本轮后处理按冻结口径的独立有效数，不是旧程序自身返回的通过数。
全部270次生成分布报告均低于.99，不能全部解释为“阈值附近MC复检抖动”。例如APP50的EGS报告约.9817656；需要另行核对经验样本与分布生成器的适配，不能通过更改统计标签使其达标。

四、后续修正边界（本次未执行）
如果修正，应让S10与EGS共用同一修正版评价器及最终输出规则；至少纠正MC采样端点、最终输出过滤及概率队列写回位置，明确统一<或<=的业务事件，并冻结后重新对照。统一修正属于新的实验版本，旧270次记录应保持不变，不能补跑挑种子或覆盖旧成绩。若要求生成分布下>=.99，还需单独定义共同的外部验证/校准规则，不能把事后real_probability报告悄悄加入旧门槛。

证据文件
LOCAL_SOURCE_COMPARISON.json：原压缩包与EGS源码的逐字节/函数级比较。
SERVER_SOURCE_AND_BINARY_VERIFICATION.json：实际服务器源码、运行二进制及冻结SHA核对。
MAIN_CPP_DIFF.txt：原main与EGS入口完整差异，显示搜索分支与输出元数据的增量。
EXISTING_RUN_TRACE_EVIDENCE.json：9个首重复示例与全部48个“入队过、最终复检低于.99”记录。
SOURCE_LINKS.json：代码行直达链接。
'''
text+='\n代表性原始记录（同一最终选择）：\n'
for x in examples:
    if x['arm'] in ['S10_MITM','EGS_2p4']:
        text+=f"{x['identity']}：全样本证书=[{x['full_empirical_certificate_lower']:.10f},{x['full_empirical_certificate_upper']:.10f}]；LSS入队={x['original_LSS_admissions_for_final_selection']}；最终LSS={x['final_LSS_probability']:.7f}；生成分布报告={x['parametric_MC_probability_report']:.7f}。\n"
text+='\n代码链接：\n'+'\n'.join(k+' '+v for k,v in links.items())+'\n'
(D/'概率评价与最终验收核查结论.txt').write_text(text,encoding='utf-8')
(D/'scripts').mkdir(exist_ok=True)
for name in ['check_sources.py','check_server_remote.py','finish_audit.py']:shutil.copyfile(R/name,D/'scripts'/name)
files=[p for p in D.rglob('*') if p.is_file() and p.name!='CHECKSUMS_SHA256.json']
manifest={p.relative_to(D).as_posix():{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in files}
(D/'CHECKSUMS_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'DELIVERY_LOCAL_VERIFIED.json').write_text(json.dumps({'status':'PASS','probability_source_unchanged':True,'actual_binaries_pinned':True,'existing_run_files_sha_verified':270*4,'files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','source_files_byte_identical':10,'search_acceptance_functions_identical':4,'final_LSS_recheck_below99':len(low),'prior_admission_observed_all270':True,'examples':examples[:2]},ensure_ascii=False))

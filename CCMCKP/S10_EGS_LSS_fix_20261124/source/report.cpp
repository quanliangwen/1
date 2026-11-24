#include "report.hpp"
#include <algorithm>
#include <cmath>
#include <cctype>
#include <fstream>
#include <functional>
#include <iomanip>
#include <map>
#include <set>
#include <sstream>
#include <tuple>

namespace s10 {
namespace {
struct Row { Selection selection; double cost, probability; std::size_t evaluation; };
bool by_cost_queue(const Row& a, const Row& b) {
    if (a.cost != b.cost) return a.cost < b.cost;
    return a.selection > b.selection;
}
bool by_probability_queue(const Row& a, const Row& b) {
    return std::tie(a.probability,a.cost,a.selection)>std::tie(b.probability,b.cost,b.selection);
}
bool accepted(double p) { return std::isfinite(p) && p >= .99 && p <= 1.; }
Json as_json(const Row& row) {
    return {{"selection",row.selection},{"cost",row.cost},{"probability",row.probability}};
}
std::string csv_selection(const Selection& s) { return "\""+Json(s).dump()+"\""; }

Json report_impl(const Instance& instance, double capacity, std::uint32_t seed, int repetition,
                 const Json& shortlist,
                 const std::function<double(const Selection&)>& evaluate_probability,
                 const fs::path& directory, double search_started) {
    Json trace=Json::array();std::size_t evaluations=0;
    std::map<Selection,Row> latest;
    const auto evaluate=[&](const Selection& s,const char* stage) {
        instance.validate(s);
        Row row{s,instance.lss_cost(s),evaluate_probability(s),++evaluations};
        latest.insert_or_assign(s,row);
        trace.push_back({{"evaluation",evaluations},{"stage",stage},{"selection",s},
                         {"cost",row.cost},{"probability",row.probability}});
        return row;
    };
    const auto fail=[&](const char* reason) {
        trace.push_back({{"stage","LSS_final_failure"},{"reason",reason}});
        write_json(directory/"ORIGINAL_LSS_DECISION_TRACE.json",trace);
        throw std::runtime_error(reason);
    };
    std::vector<Row> cost,mc,records;
    const auto push=[&](const Row& row) {
        const auto duplicate=[&](const Row& other){return other.selection==row.selection;};
        if(std::none_of(mc.begin(),mc.end(),duplicate)) {
            mc.push_back(row);
            if(mc.size()>30) {
                std::stable_sort(mc.begin(),mc.end(),[](const Row& a,const Row& b) {
                    if(a.probability!=b.probability)return a.probability>b.probability;
                    return a.cost<b.cost;
                });mc.pop_back();
            }
        }
        if(std::none_of(cost.begin(),cost.end(),duplicate)) {
            cost.push_back(row);std::sort(cost.begin(),cost.end(),by_cost_queue);
            if(cost.size()>30)cost.pop_back();
        }
    };
    for(const auto& candidate:shortlist) {
        const auto row=evaluate(candidate.at("selection").get<Selection>(),"S10_result_to_LSS_initial");
        if(accepted(row.probability)){push(row);records.push_back(row);break;}
    }
    if(records.empty())fail("No S10-generated candidate passes original LSS decision");
    for(const auto& candidate:shortlist) {
        const auto row=evaluate(candidate.at("selection").get<Selection>(),"S10_pool_original_LSS_decision");
        if(accepted(row.probability)){push(row);records.push_back(row);}
    }
    // Preserve both original recheck calls per queue entry, without resampling
    // until a pass. Every call is logged, including negative observations.
    for(auto& row:cost) {
        evaluate(row.selection,"LSS_cost_recheck_warmup");
        row=evaluate(row.selection,"LSS_cost_recheck_final");
    }
    std::sort(mc.begin(),mc.end(),by_probability_queue);
    for(std::size_t j=0;j<mc.size();++j) {
        evaluate(mc[j].selection,"LSS_probability_recheck_warmup");
        mc[j]=evaluate(mc[j].selection,"LSS_probability_recheck_final");
    }
    // One authoritative last LSS result per solution, shared by all outputs.
    std::set<Selection> audited;
    const auto filter=[&](std::vector<Row>& rows) {
        for(auto& row:rows) {
            row=latest.at(row.selection);
            if(audited.insert(row.selection).second)
                trace.push_back({{"stage","LSS_final_acceptance"},{"selection",row.selection},
                    {"probability",row.probability},{"accepted",accepted(row.probability)},
                    {"source_evaluation",row.evaluation}});
        }
        rows.erase(std::remove_if(rows.begin(),rows.end(),[](const Row& row){return !accepted(row.probability);}),rows.end());
    };
    filter(cost);filter(mc);
    if(cost.empty()&&!mc.empty())cost=mc; // Same-run already validated fallback.
    if(cost.empty())fail("No candidate passes final LSS acceptance (P >= 0.99)");
    std::sort(cost.begin(),cost.end(),by_cost_queue);
    std::sort(mc.begin(),mc.end(),by_probability_queue);
    Row second=cost.front();
    for(const auto& row:cost) {
        if(row.probability>=second.probability)second=row;
        if(row.probability>=.995)break;
    }
    std::map<Selection,std::pair<double,Row>> ranking;
    for(std::size_t i=0;i<cost.size();++i)ranking[cost[i].selection]={.7*(30-i),cost[i]};
    for(std::size_t i=0;i<mc.size();++i) {
        auto& [score,row]=ranking[mc[i].selection];score+=(1-.7)*(30-i);row=mc[i];
    }
    const auto rank=[](const auto& a) {
        const auto& [score,row]=a.second;return std::make_tuple(score,row.cost,row.probability,row.selection);
    };
    const auto weighted=std::max_element(ranking.begin(),ranking.end(),[&](const auto& a,const auto& b){return rank(a)<rank(b);})->second.second;
    const double elapsed=now()-search_started;
    const auto output=directory/"result"/"Localsearch";fs::create_directories(output);
    std::string name=instance.name;for(char& ch:name)ch=static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    std::ostringstream threshold;threshold<<std::setprecision(15)<<capacity;
    const std::string stem="LocalSearch_"+name+threshold.str();
    const auto csv=[&](const std::string& suffix,const char* header) {
        std::ofstream file(output/(stem+suffix+".csv"),std::ios::binary);
        if(!file)throw std::runtime_error("Cannot create LSS CSV");
        file<<std::setprecision(17)<<header<<"\r\n";return file;
    };
    Json variants=Json::array();const Row outputs[]={cost.front(),second,weighted};
    for(int i=0;i<3;++i) {
        const auto& row=outputs[i];
        if(!accepted(row.probability))throw std::logic_error("Final LSS invariant violated");
        auto file=csv("_"+std::to_string(i),"Times,Cost,Confidence Level,Evaluation Times,Solution,Running Time");
        file<<repetition-1<<','<<row.cost<<','<<row.probability<<','<<evaluations<<','<<csv_selection(row.selection)<<','<<elapsed<<"\r\n";
        variants.push_back(as_json(row));
    }
    auto top=csv("_3","Cost,Confidence Level,Solution,Running Time");
    auto record=csv("_record","Times,Cost,Confidence Level,Solution");
    if(repetition==1) {
        for(std::size_t i=0;i<std::min<std::size_t>(10,cost.size());++i) {
            const auto& row=cost[i];top<<row.cost<<','<<row.probability<<','<<csv_selection(row.selection)<<','<<elapsed<<"\r\n";
        }
        for(const auto& row:records)record<<row.evaluation<<','<<row.cost<<','<<row.probability<<','<<csv_selection(row.selection)<<"\r\n";
    }
    write_json(directory/"ORIGINAL_LSS_DECISION_TRACE.json",trace);
    const auto& main=variants[0];
    return {{"schema","S10_LSS_full_sample_v2"},{"status","completed"},{"instance",instance.name},
        {"capacity",capacity},{"search_seed",seed},{"rep",repetition},{"cost",main["cost"]},
        {"selection",main["selection"]},{"original_LSS_confidence",main["probability"]},
        {"acceptance_evaluator","LSS"},{"acceptance_threshold",.99},{"final_lss_enforced",true},
        {"lss_sample_index_min",0},{"lss_sample_index_max",instance.sample_count-1},
        {"real_probability_reporting",false},{"original_mainflow_search_seconds",elapsed},
        {"original_output_variants",variants},{"evaluation_times",evaluations}};
}
} // namespace

Json report(const Instance& instance,double capacity,std::uint32_t seed,int repetition,
            const Json& shortlist,LssEvaluator& evaluator,const fs::path& directory,double search_started) {
    return report_impl(instance,capacity,seed,repetition,shortlist,
        [&](const Selection& s){return evaluator.evaluate(s);},directory,search_started);
}
#ifdef S10_LSS_TESTING
Json test_report(const Instance& instance,double capacity,std::uint32_t seed,int repetition,
                 const Json& shortlist,const std::function<double(const Selection&)>& evaluator,
                 const fs::path& directory,double search_started) {
    return report_impl(instance,capacity,seed,repetition,shortlist,evaluator,directory,search_started);
}
#endif
} // namespace s10

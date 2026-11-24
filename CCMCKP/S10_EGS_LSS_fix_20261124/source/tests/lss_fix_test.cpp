#include "report.hpp"
#include <algorithm>
#include <iostream>
#include <map>
#include <stdexcept>
using namespace s10;
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
int main(int argc,char** argv) {
    try {
        require(argc==3,"fixture and fresh test output root required");
        Instance instance(argv[1]);fs::path output(argv[2]);
        require(!fs::exists(output),"Refuse to overwrite test output");fs::create_directories(output);
        ccmckp::Pcg64 pcg(7);const auto indices=pcg.integers16(500,100000);
        require(*std::max_element(indices.begin(),indices.end())==499,"PCG did not include last index");
        ccmckp::LegacyRandom legacy(7);bool saw499=false;
        for(int i=0;i<100000;++i){const auto k=legacy.below(500);require(k<500,"Index outside range");saw499|=k==499;}
        require(saw499,"Legacy sampler did not include last index");
        const Selection a{0,2,4},b{1,3,5};
        // Only item0's last sample exceeds capacity. Correct MC is near .998;
        // excluding sample499 would incorrectly return exactly 1.
        LssEvaluator lss(instance,.5,7,100000);
        const double p=lss.evaluate(a);
        require(p>.997&&p<.999,"LSS Monte Carlo did not use the last sample");
        Json shortlist=Json::array({{{"selection",a}},{{"selection",b}}});
        fs::create_directory(output/"drop");std::map<Selection,int> calls;
        auto evaluator=[&](const Selection& s){const int n=++calls[s];return s==a?(n<=4?.999:.98):(n==1?.999:.997);};
        const auto result=test_report(instance,.5,7,1,shortlist,evaluator,output/"drop",now());
        require(result["selection"].get<Selection>()==b,"Kept stale earlier pass instead of final LSS result");
        require(result["evaluation_times"]==11,"Unexpected resampling/retry");
        require(!result.contains("recorded_real_probability")&&!result["real_probability_reporting"].get<bool>(),"External real-P report survived");
        for(const auto& v:result["original_output_variants"]){require(v["selection"].get<Selection>()==b,"Invalid output variant");require(v["probability"]==.997,"Variants disagree with last LSS result");require(!v.contains("real_probability"),"Real-P variant field survived");}
        const auto trace=read_json(output/"drop/ORIGINAL_LSS_DECISION_TRACE.json");bool rejected_a=false;
        for(const auto& e:trace)if(e["stage"]=="LSS_final_acceptance"&&e["selection"].get<Selection>()==a)rejected_a=!e["accepted"].get<bool>();
        require(rejected_a,"Missing negative final-acceptance trace");
        fs::create_directory(output/"none");calls.clear();bool threw=false;
        try{test_report(instance,.5,7,1,shortlist,[&](const Selection& s){int n=++calls[s];return n<=(s==a?2:1)?.999:.98;},output/"none",now());}
        catch(const std::runtime_error& e){threw=std::string(e.what()).find("No candidate passes final LSS")!=std::string::npos;}
        require(threw,"Did not reject an all-failed final LSS pool");
        require(fs::exists(output/"none/ORIGINAL_LSS_DECISION_TRACE.json"),"Missing failed trace");
        require(!fs::exists(output/"none/result"),"Emitted final CSV despite no accepted solution");
        const Json receipt={{"status","PASS"},{"last_index_499_reachable",true},{"LSS_last_atom_fixture_probability",p},
            {"late_recheck_invalidates_earlier_pass",true},{"all_variants_share_last_LSS_value",true},
            {"no_retry_until_pass",true},{"all_final_failures_rejected",true},{"no_distribution_metadata_present",true}};
        write_json(output/"UNIT_RECEIPT.json",receipt);std::cout<<receipt.dump()<<'\n';return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}

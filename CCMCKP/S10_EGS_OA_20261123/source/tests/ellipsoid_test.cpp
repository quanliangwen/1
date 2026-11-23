#include "ellipsoid.hpp"
#include <cmath>
#include <iostream>
#include <set>
#include <stdexcept>

using namespace s10;
void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("Need a tiny fixture directory");
        Instance instance(argv[1]);
        require(instance.m() == 3 && instance.n() == 6, "Unexpected fixture");
        instance.mean = {.8,1.3,.6,1.8,.5,1.0};
        instance.variance = {.09,.001,.16,.002,.25,.003};
        instance.costs = {7,2,6,1,5,3};
        Groups all;
        for (int a : instance.groups[0]) for (int b : instance.groups[1]) for (int c : instance.groups[2])
            all.push_back({a,b,c});
        const auto brute_norm = [&](const Selection& s) {
            double variance = 0;
            for (int j : s) variance += instance.variance[j];
            return std::sqrt(variance);
        };
        const auto brute_risk = [&](const Selection& s, double gamma) {
            double mu = 0;
            for (int j : s) mu += instance.mean[j];
            return mu + gamma * brute_norm(s);
        };
        int support_checks = 0, enumeration_checks = 0;
        for (const auto& anchor : all) for (const auto& x : all) {
            double cut = 0;
            for (int j : anchor)
                if (std::find(x.begin(), x.end(), j) != x.end()) cut += instance.variance[j] / brute_norm(anchor);
            require(cut <= brute_norm(x) + 1e-12, "Invalid support plane");
            ++support_checks;
        }
        for (double gamma : {0.,2.4,8.}) {
            EllipsoidMaster master(instance, 960001, gamma);
            master.set_cost_bound(100);
            master.add_support_cut(all.front());
            std::set<Selection> used;
            for (std::size_t k = 0; k < all.size(); ++k) {
                double best = 1e100;
                for (const auto& s : all) if (!used.count(s)) best = std::min(best, brute_risk(s, gamma));
                const auto q = master.next_candidate(10);
                require(q.has_candidate && q.proxy_optimal, "Tiny OA query did not reach proxy optimum");
                require(!used.count(q.selection), "Repeated excluded vector");
                require(std::abs(q.risk - brute_risk(q.selection, gamma)) < 1e-9, "Reported risk mismatch");
                require(std::abs(q.risk - best) < 1e-6, "OA differs from exhaustive enumeration");
                used.insert(q.selection);
                require(master.exclude_processed(q.selection), "Missing first exclusion");
                require(!master.exclude_processed(q.selection), "Duplicate exclusion was added");
                ++enumeration_checks;
            }
            const auto final = master.next_candidate(10);
            require(final.exhausted && !final.has_candidate, "Finite domain did not exhaust");
            require(master.excluded_count() == 8, "Wrong exclusion count");
        }
        {
            EllipsoidMaster master(instance, 960001, 2.4);
            master.set_cost_bound(8);
            auto q = master.next_candidate(10);
            double best = 1e100;
            for (const auto& s : all) if (instance.cost_of(s) <= 8) best = std::min(best, brute_risk(s,2.4));
            require(q.has_candidate && std::abs(q.risk-best)<1e-6 && q.cost<=8, "Cost bound mismatch");
            bool rejected = false;
            try { master.set_cost_bound(9); } catch (const std::invalid_argument&) { rejected = true; }
            require(rejected, "Cost bound was allowed to loosen");
            master.set_cost_bound(5);
            q = master.next_candidate(10);
            require(q.exhausted && !q.has_candidate, "Infeasible cost domain not detected");
        }
        instance.variance.assign(6,0);
        {
            EllipsoidMaster master(instance,960001,2.4);
            master.set_cost_bound(100);
            require(!master.add_support_cut(all.front()), "Zero norm support cut was added");
            const auto q = master.next_candidate(10);
            require(q.has_candidate && q.norm==0 && q.proxy_optimal, "Zero variance path failed");
        }
        bool rejected = false;
        try { EllipsoidMaster bad(instance,960001,-1); } catch (const std::invalid_argument&) { rejected=true; }
        require(rejected, "Negative gamma accepted");
        std::cout << Json({{"status","PASS"},{"support_plane_checks",support_checks},
            {"exhaustive_rank_queries",enumeration_checks},{"zero_gamma",true},
            {"zero_variance",true},{"cost_bound_tightening",true},
            {"full_vector_exclusion_only",true}}).dump() << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}

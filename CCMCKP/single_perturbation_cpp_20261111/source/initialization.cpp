#include "initialization.hpp"

#include <cmath>
#include <limits>
#include <set>
#include <tuple>

namespace ccmckp {
namespace {

Selection ordered_seed(const Groups& groups, bool last) {
    Selection selection;
    for (const auto& group : groups) selection.push_back(last ? group.back() : group.front());
    return selection;
}

Selection cost_risk_proposal(const Instance& instance, const Settings& settings) {
    const int classes = instance.classes;
    const auto& items = instance.items;
    const auto& ids = instance.utility;
    const double z = normal_quantile(settings.p0);
    const auto assignment = [&](double multiplier, const std::vector<double>& weights) {
        Selection result(classes);
        for (int cid = 0; cid < classes; ++cid) {
            const auto& group = ids[cid];
            const auto score = [&](int fid) { return items[fid].cost + multiplier * weights[fid]; };
            for (int i = 1; i < static_cast<int>(group.size()); ++i) {
                if (score(group[i]) < score(group[result[cid]])) result[cid] = i;
            }
        }
        return result;
    };
    const auto totals = [&](const Selection& choice) {
        std::array<double, 3> total{};
        for (int cid = 0; cid < classes; ++cid) {
            const auto& item = items[ids[cid][choice[cid]]];
            total[0] += item.cost;
            total[1] += item.mean;
            total[2] += item.variance;
        }
        return total;
    };
    std::vector<double> weights(items.size());
    Selection current = assignment(0.0, weights);
    std::set<Selection> visited, considered;
    std::size_t retained = 0;
    for (const auto& group : ids) retained += group.size();
    for (std::size_t iteration = 0; iteration < retained && visited.insert(current).second; ++iteration) {
        const double sigma = std::sqrt(std::max(totals(current)[2], std::numeric_limits<double>::min()));
        const double beta = z / (2.0 * sigma);
        for (std::size_t fid = 0; fid < items.size(); ++fid) {
            weights[fid] = items[fid].mean + beta * items[fid].variance;
        }
        const double budget = settings.tmax - 0.5 * z * sigma;
        const auto weight = [&](const Selection& choice) {
            double total = 0.0;
            for (int cid = 0; cid < classes; ++cid) total += weights[ids[cid][choice[cid]]];
            return total;
        };
        double lo = 0, hi = 1;
        auto low = assignment(lo, weights), high = assignment(hi, weights);
        while (weight(high) > budget) {
            auto previous = high;
            hi *= 2;
            high = assignment(hi, weights);
            if (high == previous && hi > 1e12) break;
        }
        for (int i = 0; i < 64; ++i) {
            const double mid = (lo + hi) / 2;
            auto choice = assignment(mid, weights);
            considered.insert(choice);
            if (weight(choice) > budget) {
                lo = mid;
                low = std::move(choice);
            } else {
                hi = mid;
                high = std::move(choice);
            }
        }
        considered.insert(low);
        considered.insert(high);
        current = std::move(high);
    }
    const auto key = [&](const Selection& choice) {
        const auto [cost, mean, variance] = totals(choice);
        const double violation = mean + z * std::sqrt(variance) - settings.tmax;
        return std::make_tuple(violation > 0, std::max(0.0, violation), cost, choice);
    };
    auto best = *std::min_element(considered.begin(), considered.end(),
                                  [&](const auto& a, const auto& b) { return key(a) < key(b); });
    for (int cid = 0; cid < classes; ++cid) best[cid] = ids[cid][best[cid]];
    return best;
}

} // namespace

Initial initialize(const Instance& instance, const Settings& settings,
                   const std::function<double(const Selection&)>& evaluate, const Stop& stopped) {
    if (stopped()) throw std::runtime_error("initialization_deadline_reached_before_start");
    Initial initial{};
    initial.selection = instance.exact() ? ordered_seed(instance.utility, false)
                                         : cost_risk_proposal(instance, settings);
    initial.cost = instance.cost(initial.selection);
    Pilot pilot(instance, settings, initial.selection, std::uint64_t(settings.seed) + 0x12000, stopped);
    if (!pilot.ready()) throw std::runtime_error("pilot_construction_timeout");
    const int allowed = allowed_pilot_failures(settings);
    int violations = pilot.failures();
    const auto accept = [&](const char* source) {
        if (violations > allowed || stopped()) return false;
        initial.probability = evaluate(initial.selection);
        if (initial.probability + 1e-15 < settings.p0) return false;
        initial.source = source;
        return true;
    };
    if (accept(instance.exact() ? "utility_seed" : "cost_risk_seed")) return initial;

    while (!stopped()) {
        using Rank = std::tuple<int, double, double, double, double, int, int>;
        Rank best_key;
        int best_class = -1, best_factor = -1, best_failures = 0;
        double best_cost = 0;
        for (int cid = 0; cid < instance.classes && !stopped(); ++cid) {
            const int old = initial.selection[cid];
            for (int fid : instance.weight[cid]) {
                if (stopped()) break;
                if (fid == old) continue;
                const int failures = pilot.candidate_failures(cid, old, fid);
                const int reduction = violations - failures;
                if (reduction <= 0) continue;
                const double delta = instance.items[fid].cost - instance.items[old].cost;
                const double candidate_cost = initial.cost + delta;
                const Rank rank = delta <= tolerance
                    ? Rank(0, -reduction, 0, 0, candidate_cost, cid, fid)
                    : Rank(1, -reduction / delta, -reduction, delta, candidate_cost, cid, fid);
                if (best_class < 0 || rank < best_key) {
                    best_key = rank;
                    best_class = cid;
                    best_factor = fid;
                    best_cost = candidate_cost;
                    best_failures = failures;
                }
            }
        }
        if (best_class < 0) break;
        pilot.apply(best_class, initial.selection[best_class], best_factor);
        initial.selection[best_class] = best_factor;
        initial.cost = best_cost;
        violations = best_failures;
        ++initial.repairs;
        if (accept("violation_driven_repair")) return initial;
    }

    initial.selection = ordered_seed(instance.weight, true);
    initial.cost = instance.cost(initial.selection);
    if (!pilot.reset(initial.selection, stopped) || stopped()) {
        throw std::runtime_error("initialization_timeout_before_safe_anchor_confirmation");
    }
    violations = pilot.failures();
    if (accept("safe_anchor")) return initial;
    throw std::runtime_error(violations > allowed ? "safe_anchor_failed_pilot_feasibility"
                                                 : "safe_anchor_failed_high_precision_validation");
}

} // namespace ccmckp

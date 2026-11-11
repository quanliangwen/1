#include "search.hpp"
#include "initialization.hpp"

#include <cmath>
#include <iomanip>
#include <map>
#include <numeric>
#include <optional>
#include <tuple>

namespace ccmckp {

void write_selection(std::ostream& out, const Selection& selection) {
    out << '[';
    for (std::size_t i = 0; i < selection.size(); ++i) {
        if (i) out << ',';
        out << selection[i];
    }
    out << ']';
}

namespace {

using Change = std::pair<int, int>;

struct Proposal {
    double delta;
    int failures;
    std::vector<Change> changes;
    bool operator<(const Proposal& other) const {
        return std::tie(delta, failures, changes) < std::tie(other.delta, other.failures, other.changes);
    }
};

std::vector<Proposal> rank_pairs(const Instance& instance, const Settings& settings,
                                const Selection& current, std::uint64_t seed, const Stop& stop) {
    struct Move {
        int cid, fid;
        double delta;
        std::vector<double> changes;
    };
    const auto size = settings.pilot_samples;
    std::vector<double> sums(size);
    std::vector<Move> moves;
    for (int cid = 0; cid < instance.classes; ++cid) {
        if (stop()) return {};
        const auto& old = instance.items[current[cid]];
        const auto indices = pilot_indices(seed, cid, 0x2a17, instance.sample_count, size);
        for (int i = 0; i < size; ++i) sums[i] += old.samples[indices[i]];
        for (int fid : instance.value[cid]) {
            if (fid == current[cid]) continue;
            const auto& item = instance.items[fid];
            Move move{cid, fid, item.cost - old.cost, std::vector<double>(size)};
            for (int i = 0; i < size; ++i) move.changes[i] = item.samples[indices[i]] - old.samples[indices[i]];
            moves.push_back(std::move(move));
        }
    }
    const int allowed = allowed_pilot_failures(settings);
    std::vector<Proposal> proposals;
    for (std::size_t i = 0; i < moves.size() && !stop(); ++i) {
        const auto& a = moves[i];
        for (std::size_t j = i + 1; j < moves.size(); ++j) {
            const auto& b = moves[j];
            if (a.cid == b.cid || a.delta + b.delta >= -tolerance) continue;
            int failures = 0;
            for (int k = 0; k < size; ++k) {
                failures += sums[k] + a.changes[k] + b.changes[k] >= settings.tmax;
            }
            if (failures <= allowed) {
                proposals.push_back({a.delta + b.delta, failures, {{a.cid, a.fid}, {b.cid, b.fid}}});
            }
        }
    }
    std::sort(proposals.begin(), proposals.end());
    return proposals;
}

class Search {
public:
    Search(const Instance& instance, const Settings& settings, const Groups& checks,
           std::ostream* trace, std::uint64_t evaluation_budget)
        : instance_(instance), settings_(settings), evaluator_(instance, settings, checks),
          trace_(trace), evaluation_budget_(evaluation_budget), started_(Clock::now()),
          deadline_(started_ + std::chrono::seconds(600)),
          tabu_(instance.items.size()), tenure_(settings.tabu_tenure) {}

    Result run() {
        if (trace_) {
            *trace_ << std::setprecision(17)
                << "phase,event,cycle,evaluation_count,solution,cost,probability,samples_used,tenure\n";
        }
        const auto initial = initialize(instance_, settings_,
            [&](const Selection& candidate) { return evaluate(candidate, "init"); },
            [&] { return expired(); });
        if (std::abs(instance_.cost(initial.selection) - initial.cost) > 1e-9) {
            throw std::runtime_error("initial objective validation failed");
        }
        current_ = result_.solution = result_.initial_solution = initial.selection;
        result_.initial_cost = initial.cost;
        cost_ = result_.cost = instance_.exact() ? initial.cost : instance_.cost(initial.selection);
        probability_ = result_.probability = result_.initial_probability = initial.probability;
        result_.initialization = initial.source;
        result_.init_repairs = initial.repairs;
        result_.best_found_seconds = elapsed();
        result_.maximum_tenure = tenure_;
        configurations_[current_] = 0;
        record("search", "cp_initial", current_, cost_, probability_, 0);
        evaluator_.reseed(settings_.seed);
        if (instance_.exact()) exact_search();
        else monte_carlo_search();
        if (std::abs(instance_.cost(result_.solution) - result_.cost) > 1e-9 ||
            result_.probability + tolerance < settings_.p0) {
            throw std::runtime_error("final solution validation failed");
        }
        result_.seconds = elapsed();
        result_.stop_reason = evaluation_budget_ && result_.evaluations >= evaluation_budget_ &&
            (!instance_.exact() || !expired()) ? "evaluation_budget" : "time_limit";
        return result_;
    }

private:
    bool expired() const { return Clock::now() >= deadline_; }
    bool stopped() const {
        return expired() || (evaluation_budget_ && result_.evaluations >= evaluation_budget_);
    }
    double elapsed() const { return std::chrono::duration<double>(Clock::now() - started_).count(); }

    void record(const char* phase, const char* event, const Selection& selection,
                double cost, double probability, int samples_used) {
        if (!trace_) return;
        *trace_ << phase << ',' << event << ',' << cycle_ << ',' << result_.evaluations << ",\"";
        write_selection(*trace_, selection);
        *trace_ << "\"," << cost << ',' << probability << ',' << samples_used << ',' << tenure_ << '\n';
    }

    double evaluate(const Selection& selection, const char* phase) {
        const double p = evaluator_(selection);
        ++result_.evaluations;
        if (trace_) record(phase, "evaluate", selection, instance_.cost(selection), p, evaluator_.last_samples_used());
        return p;
    }

    void commit(Selection selection, const std::vector<Change>& changes, double cost,
                double probability, const char* event) {
        for (const auto& [cid, fid] : changes) {
            if (pilot_) pilot_->apply(cid, current_[cid], fid);
            tabu_[current_[cid]] = cycle_ + tenure_;
        }
        current_ = std::move(selection);
        cost_ = cost;
        probability_ = probability;
        if (cost < result_.cost - tolerance) {
            result_.solution = current_;
            result_.cost = cost;
            result_.probability = probability;
            result_.best_found_seconds = elapsed();
        }
        record("search", event, current_, cost_, probability_, 0);
    }

    Selection class_order() {
        Selection order(instance_.classes);
        std::iota(order.begin(), order.end(), 0);
        evaluator_.random().shuffle(order);
        return order;
    }

    double exact_candidate_cost(int old, int fid) const {
        return cost_ - instance_.items[old].cost + instance_.items[fid].cost;
    }

    void complete_cycle(bool strong, double previous_best) {
        const auto previous = configurations_.find(current_);
        const auto before = tenure_;
        if (previous != configurations_.end()) {
            ++result_.repeats;
            if (instance_.exact()) {
                tenure_ = std::max(tenure_, std::max<std::uint64_t>(1, cycle_ - previous->second) + 1);
                cycle_free_ = 0;
            }
        } else if (instance_.exact() && ++cycle_free_ >= tenure_) {
            tenure_ = std::max<std::uint64_t>(settings_.tabu_tenure, tenure_ - (tenure_ > 0));
            cycle_free_ = 0;
        }
        configurations_[current_] = cycle_;
        result_.maximum_tenure = std::max(result_.maximum_tenure, tenure_);
        result_.tenure_updates += before != tenure_;
        result_.cycles = cycle_;
        record("search", "iteration_end", current_, cost_, probability_, 0);
        if (strong || result_.cost < previous_best - tolerance) idle_cycles_ = 0;
        else ++idle_cycles_;
    }

    Selection perturbation_order(int cid, int old, bool nearby) {
        Selection alternatives;
        for (int fid : instance_.value[cid])
            if (fid != old) alternatives.push_back(fid);
        evaluator_.random().shuffle(alternatives);
        if (nearby) {
            const auto gap = [&](int fid) {
                return std::abs(instance_.items[fid].cost - instance_.items[old].cost);
            };
            std::stable_sort(alternatives.begin(), alternatives.end(),
                             [&](int a, int b) { return gap(a) < gap(b); });
        }
        return alternatives;
    }

    bool light_perturbation() {
        for (int cid : class_order()) {
            const int old = current_[cid];
            for (int fid : perturbation_order(cid, old, true)) {
                if (stopped()) return false;
                auto candidate = current_;
                candidate[cid] = fid;
                const double p = evaluate(candidate, "search");
                if (p + tolerance < settings_.p0) continue;
                const double cost = instance_.exact() ? exact_candidate_cost(old, fid) : instance_.cost(candidate);
                ++result_.perturbations;
                commit(std::move(candidate), {{cid, fid}}, cost, p, "random_perturbation");
                return true;
            }
            if (!instance_.exact() && stopped()) return false;
        }
        if (instance_.exact()) record("search", "random_perturbation_noop", current_, cost_, probability_, 0);
        return true;
    }

    int strong_target() const {
        return static_cast<int>(std::ceil(instance_.classes * strong_class_ratio));
    }

    bool exact_strong_perturbation() {
        // The exact branch samples a fixed set of classes. Its intermediate
        // feasible solutions remain provisional until the whole move returns.
        auto order = class_order();
        order.resize(strong_target());
        auto solution = current_;
        double cost = cost_, probability = probability_;
        std::vector<Change> changes;
        for (int cid : order) {
            if (stopped()) break;
            const int old = solution[cid];
            for (int fid : perturbation_order(cid, old, false)) {
                if (stopped()) return false;
                auto candidate = solution;
                candidate[cid] = fid;
                const double p = evaluate(candidate, "search");
                if (p + tolerance < settings_.p0) continue;
                changes.emplace_back(cid, fid);
                cost = cost - instance_.items[old].cost + instance_.items[fid].cost;
                probability = p;
                solution = std::move(candidate);
                break;
            }
        }
        if (changes.empty()) {
            record("search", "random_perturbation_noop", current_, cost_, probability_, 0);
        } else {
            ++result_.strong_perturbations;
            result_.perturbations += changes.size();
            result_.strong_destroyed_classes += changes.size();
            commit(std::move(solution), changes, cost, probability, "strong_perturbation");
        }
        return true;
    }

    void monte_carlo_strong_perturbation() {
        // The reference-MC branch continues past infeasible classes until
        // enough moves succeed, committing every successful class immediately.
        int destroyed = 0;
        const int target = strong_target();
        for (int cid : class_order()) {
            if (stopped() || destroyed >= target) break;
            for (int fid : perturbation_order(cid, current_[cid], false)) {
                if (stopped()) break;
                auto candidate = current_;
                candidate[cid] = fid;
                const double p = evaluate(candidate, "search");
                if (p + tolerance < settings_.p0) continue;
                const double cost = instance_.cost(candidate);
                ++result_.perturbations;
                ++destroyed;
                commit(std::move(candidate), {{cid, fid}}, cost, p, "strong_perturbation");
                break;
            }
        }
        ++result_.strong_perturbations;
        result_.strong_destroyed_classes += destroyed;
    }

    void exact_search() {
        while (!stopped()) {
            ++cycle_;
            const double previous_best = result_.cost;
            for (int cid : class_order()) {
                if (stopped()) return;
                ++result_.class_scans;
                std::vector<std::pair<double, int>> candidates;
                const int old = current_[cid];
                for (int fid : instance_.value[cid]) {
                    if (fid == old) continue;
                    const double cost = exact_candidate_cost(old, fid);
                    if (cost >= cost_ - tolerance) continue;
                    if (cycle_ <= tabu_[fid] && cost >= result_.cost - tolerance) continue;
                    candidates.emplace_back(cost, fid);
                }
                std::sort(candidates.begin(), candidates.end());
                bool accepted = false;
                for (const auto& [cost, fid] : candidates) {
                    if (stopped()) return;
                    auto candidate = current_;
                    candidate[cid] = fid;
                    const double p = evaluate(candidate, "search");
                    if (p + tolerance < settings_.p0) continue;
                    ++result_.tabu_moves;
                    commit(std::move(candidate), {{cid, fid}}, cost, p, "class_scan_move");
                    accepted = true;
                    break;
                }
                if (!accepted) record("search", "class_scan_no_improvement", current_, cost_, probability_, 0);
            }
            const bool strong = idle_cycles_ >= strong_no_improve;
            if (!(strong ? exact_strong_perturbation() : light_perturbation())) return;
            complete_cycle(strong, previous_best);
        }
    }

    bool try_mc_proposals(const std::vector<Proposal>& proposals, bool pairs) {
        for (const auto& proposal : proposals) {
            if (pairs) {
                bool tabu = false;
                for (const auto& [cid, fid] : proposal.changes) {
                    (void)cid;
                    tabu |= cycle_ <= tabu_[fid];
                }
                if (tabu && cost_ + proposal.delta >= result_.cost - tolerance) continue;
            }
            if (stopped()) return false;
            auto candidate = current_;
            for (const auto& [cid, fid] : proposal.changes) candidate[cid] = fid;
            const double p = evaluate(candidate, "search");
            if (pairs) ++result_.pair_evaluations;
            if (p + tolerance < settings_.p0) continue;
            if (pairs) ++result_.pair_exchanges;
            else ++result_.tabu_moves;
            const double cost = instance_.cost(candidate);
            commit(std::move(candidate), proposal.changes, cost, p,
                   pairs ? "two_class_exchange" : "tail_priority_single");
            return true;
        }
        return false;
    }

    std::vector<Proposal> rank_singles() {
        const int allowed = allowed_pilot_failures(settings_);
        std::vector<Proposal> proposals;
        for (int cid = 0; cid < instance_.classes; ++cid) {
            const int old = current_[cid];
            for (int fid : instance_.value[cid]) {
                if (stopped()) return proposals;
                const double delta = instance_.items[fid].cost - instance_.items[old].cost;
                if (fid == old || delta >= -tolerance) continue;
                if (cycle_ <= tabu_[fid] && cost_ + delta >= result_.cost - tolerance) continue;
                const int failures = pilot_->candidate_failures(cid, old, fid);
                if (failures <= allowed) proposals.push_back({delta, failures, {{cid, fid}}});
            }
        }
        std::sort(proposals.begin(), proposals.end());
        return proposals;
    }

    void monte_carlo_search() {
        const Stop stop = [&] { return stopped(); };
        pilot_.emplace(instance_, settings_, current_, std::uint64_t(settings_.seed) + 0x50700, stop);
        if (!pilot_->ready()) return;
        while (!stopped()) {
            ++cycle_;
            const double previous_best = result_.cost;
            while (!stopped()) {
                auto singles = rank_singles();
                result_.class_scans += instance_.classes;
                const bool moved = try_mc_proposals(singles, false);
                if (stopped()) return;
                if (moved) continue;

                const auto pairs = rank_pairs(instance_, settings_, current_,
                    std::uint64_t(settings_.seed) + cycle_, stop);
                result_.pair_proposals += pairs.size();
                const bool exchanged = try_mc_proposals(pairs, true);
                if (stopped()) return;
                if (!exchanged) break;
            }
            if (stopped()) return;
            const bool strong = idle_cycles_ >= strong_no_improve;
            if (strong) monte_carlo_strong_perturbation();
            else light_perturbation();
            if (stopped()) return;
            complete_cycle(strong, previous_best);
        }
    }

    const Instance& instance_;
    const Settings& settings_;
    Evaluator evaluator_;
    std::ostream* trace_;
    std::uint64_t evaluation_budget_;
    Deadline started_, deadline_;
    Result result_;
    Selection current_;
    double cost_ = 0, probability_ = 0;
    std::vector<std::uint64_t> tabu_;
    std::map<Selection, std::uint64_t> configurations_;
    std::uint64_t cycle_ = 0, tenure_, cycle_free_ = 0;
    int idle_cycles_ = 0;
    std::optional<Pilot> pilot_;
};

} // namespace

Result solve(const Instance& instance, const Settings& settings, const Groups& quick_checks,
             std::ostream* trace, std::uint64_t evaluation_budget) {
    return Search(instance, settings, quick_checks, trace, evaluation_budget).run();
}

} // namespace ccmckp


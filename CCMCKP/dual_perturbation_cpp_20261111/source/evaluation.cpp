#include "evaluation.hpp"

#include <cmath>
#include <iomanip>
#include <locale>
#include <queue>
#include <set>
#include <sstream>
#include <utility>

namespace ccmckp {

Evaluator::Evaluator(const Instance& instance, const Settings& settings, const Groups& quick_checks)
    : instance_(instance), settings_(settings), quick_checks_(quick_checks),
      random_(settings.seed), scratch_(instance.classes) {
    const double tail = 1.0 - settings.p0;
    double scaled;
    if (instance.exact()) {
        // The reference rounds the binary double by formatting it to three
        // decimal places before converting that decimal back to a double.
        std::stringstream rounded;
        rounded.imbue(std::locale::classic());
        rounded << std::fixed << std::setprecision(3) << tail;
        double exact_tail = 0.0;
        rounded >> exact_tail;
        scaled = instance.combinations * exact_tail;
        exact_max_pops_ = static_cast<std::uint64_t>(std::ceil(scaled));
    } else {
        scaled = std::nearbyint(instance.combinations * tail);
    }
    rank_ = static_cast<int>(std::ceil(std::pow(scaled, 1.0 / instance.classes)));
    if (rank_ >= instance.sample_count) throw std::runtime_error("reference QuickCheck rank exceeds sample count");
}

double Evaluator::indexed_sum(const Selection& solution, const Selection& ranks) {
    for (int cid = 0; cid < instance_.classes; ++cid) {
        scratch_[cid] = instance_.items[solution[cid]].descending[ranks[cid]];
    }
    return numpy_sum(scratch_.data(), scratch_.size());
}

double Evaluator::operator()(const Selection& solution) {
    last_samples_used_ = 0;
    double sum = indexed_sum(solution, Selection(instance_.classes, rank_));
    bool rejected = sum >= settings_.tmax;
    for (const auto& ranks : quick_checks_) {
        sum = indexed_sum(solution, ranks);
        rejected |= sum >= settings_.tmax;
    }
    if (rejected) return 0.0;
    if (instance_.exact()) return exact_probability(solution, rank_, sum);

    sums_.assign(settings_.mc_samples, 0.0);
    for (int fid : solution) {
        const auto& samples = instance_.items[fid].samples;
        for (double& total : sums_) total += samples[random_.below(samples.size() - 1)];
    }
    last_samples_used_ = settings_.mc_samples;
    const auto passes = std::count_if(sums_.begin(), sums_.end(),
                                      [&](double total) { return total < settings_.tmax; });
    return static_cast<double>(passes) / settings_.mc_samples;
}

double Evaluator::exact_probability(const Selection& solution, int rank, double last_sum) {
    // This starts with the sum left by the last QuickCheck row, as the author
    // evaluator does. Its heap includes the first popped point at/below T.
    while (last_sum < settings_.tmax && rank > 0) {
        --rank;
        last_sum = indexed_sum(solution, Selection(instance_.classes, rank));
    }
    using Point = std::pair<double, Selection>;
    std::priority_queue<Point, std::vector<Point>, std::greater<Point>> queue;
    std::set<Selection> pending;
    const auto push = [&](const Selection& ranks) {
        if (pending.insert(ranks).second) queue.emplace(-indexed_sum(solution, ranks), ranks);
    };

    const int boundary = rank + 1;
    if (boundary < instance_.sample_count) {
        Selection ranks(instance_.classes);
        const auto push_boundary = [&](const auto& self, int cid, bool contains_boundary) -> void {
            if (cid == instance_.classes) {
                push(ranks);
                return;
            }
            const int start = cid + 1 == instance_.classes && !contains_boundary ? boundary : 0;
            for (int r = start; r <= boundary; ++r) {
                ranks[cid] = r;
                self(self, cid + 1, contains_boundary || r == boundary);
            }
        };
        push_boundary(push_boundary, 0, false);
    }

    double popped_sum = settings_.tmax + 1;
    std::uint64_t pops = 0;
    while (!queue.empty() && popped_sum > settings_.tmax) {
        auto point = queue.top();
        queue.pop();
        pending.erase(point.second);
        popped_sum = -point.first;
        ++pops;
        for (int& r : point.second) {
            if (r + 1 < instance_.sample_count) {
                ++r;
                push(point.second);
                --r;
            }
        }
        if (pops > exact_max_pops_) return 0.0;
    }
    std::uint64_t count = 1;
    for (int cid = 0; cid < instance_.classes; ++cid) count *= rank + 1;
    count += pops;
    return 1.0 - count / instance_.combinations;
}

Selection pilot_indices(std::uint64_t seed, int cid, int salt, int sample_count, int pilot_count) {
    PilotRandom random(seed, cid, salt);
    Selection indices(pilot_count);
    for (int& index : indices) index = random.below(sample_count - 1);
    return indices;
}

int allowed_pilot_failures(const Settings& settings) {
    return settings.pilot_samples - static_cast<int>(std::ceil(settings.p0 * settings.pilot_samples - tolerance));
}

Pilot::Pilot(const Instance& instance, const Settings& settings, const Selection& selection,
             std::uint64_t seed, const Stop& stop)
    : instance_(instance), tmax_(settings.tmax), sums_(settings.pilot_samples) {
    for (int cid = 0; cid < instance_.classes; ++cid) {
        if (stop()) return;
        indices_.push_back(pilot_indices(seed, cid, 0x1a17, instance_.sample_count, settings.pilot_samples));
        const auto& samples = instance_.items[selection[cid]].samples;
        for (std::size_t i = 0; i < sums_.size(); ++i) sums_[i] += samples[indices_[cid][i]];
    }
    ready_ = true;
}

bool Pilot::reset(const Selection& selection, const Stop& stop) {
    std::fill(sums_.begin(), sums_.end(), 0.0);
    for (int cid = 0; cid < instance_.classes; ++cid) {
        if (stop()) return false;
        const auto& samples = instance_.items[selection[cid]].samples;
        for (std::size_t i = 0; i < sums_.size(); ++i) sums_[i] += samples[indices_[cid][i]];
    }
    return true;
}

int Pilot::failures() const {
    return std::count_if(sums_.begin(), sums_.end(), [&](double sum) { return sum >= tmax_; });
}

int Pilot::candidate_failures(int cid, int old_factor, int new_factor) const {
    const auto& old_values = instance_.items[old_factor].samples;
    const auto& new_values = instance_.items[new_factor].samples;
    int result = 0;
    for (std::size_t i = 0; i < sums_.size(); ++i) {
        const int k = indices_[cid][i];
        result += sums_[i] - old_values[k] + new_values[k] >= tmax_;
    }
    return result;
}

void Pilot::apply(int cid, int old_factor, int new_factor) {
    const auto& old_values = instance_.items[old_factor].samples;
    const auto& new_values = instance_.items[new_factor].samples;
    for (std::size_t i = 0; i < sums_.size(); ++i) {
        const int k = indices_[cid][i];
        sums_[i] += new_values[k] - old_values[k];
    }
}

} // namespace ccmckp

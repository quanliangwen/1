#pragma once

#include "model.hpp"

namespace ccmckp {

class Evaluator {
public:
    Evaluator(const Instance& instance, const Settings& settings, const Groups& quick_checks);
    double operator()(const Selection& solution);
    void reseed(std::uint32_t seed) { random_ = LegacyRandom(seed); }
    LegacyRandom& random() { return random_; }
    int last_samples_used() const { return last_samples_used_; }

private:
    double indexed_sum(const Selection& solution, const Selection& ranks);
    double exact_probability(const Selection& solution, int rank, double last_sum);
    const Instance& instance_;
    const Settings& settings_;
    const Groups& quick_checks_;
    LegacyRandom random_;
    std::vector<double> sums_, scratch_;
    std::uint64_t exact_max_pops_ = 0;
    int rank_, last_samples_used_ = 0;
};

class Pilot {
public:
    Pilot(const Instance& instance, const Settings& settings, const Selection& selection,
          std::uint64_t seed, const Stop& stop);
    bool reset(const Selection& selection, const Stop& stop);
    bool ready() const { return ready_; }
    int failures() const;
    int candidate_failures(int cid, int old_factor, int new_factor) const;
    void apply(int cid, int old_factor, int new_factor);

private:
    const Instance& instance_;
    double tmax_;
    std::vector<Selection> indices_;
    std::vector<double> sums_;
    bool ready_ = false;
};

Selection pilot_indices(std::uint64_t seed, int cid, int salt, int sample_count, int pilot_count);
int allowed_pilot_failures(const Settings& settings);

} // namespace ccmckp

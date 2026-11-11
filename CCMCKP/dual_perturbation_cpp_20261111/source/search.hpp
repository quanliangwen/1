#pragma once

#include "evaluation.hpp"

#include <ostream>

namespace ccmckp {

inline constexpr int strong_no_improve = 5;
inline constexpr double strong_class_ratio = 0.5;

struct Result {
    Selection solution, initial_solution;
    std::string initialization, stop_reason;
    double cost = 0, probability = 0, initial_cost = 0, initial_probability = 0;
    double seconds = 0, best_found_seconds = 0;
    std::uint64_t evaluations = 0, cycles = 0, class_scans = 0, tabu_moves = 0;
    std::uint64_t perturbations = 0, pair_exchanges = 0, pair_evaluations = 0, pair_proposals = 0;
    std::uint64_t strong_perturbations = 0, strong_destroyed_classes = 0;
    std::uint64_t repeats = 0, maximum_tenure = 0, tenure_updates = 0, init_repairs = 0;
};

Result solve(const Instance& instance, const Settings& settings, const Groups& quick_checks,
             std::ostream* trace = nullptr, std::uint64_t evaluation_budget = 0);
void write_selection(std::ostream& out, const Selection& selection);

} // namespace ccmckp

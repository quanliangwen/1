#pragma once
#include "evaluation.hpp"

namespace s10 {
double real_probability(const Instance& instance, const Selection& selection, double capacity,
                        std::size_t draws = 10000000);
Json report(const Instance& instance, double capacity, std::uint32_t seed, int repetition,
            const Json& shortlist, LssEvaluator& evaluator, const fs::path& directory,
            double search_started);
} // namespace s10

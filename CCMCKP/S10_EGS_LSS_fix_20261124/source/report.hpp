#pragma once
#include "evaluation.hpp"
#ifdef S10_LSS_TESTING
#include <functional>
#endif
namespace s10 {
Json report(const Instance& instance, double capacity, std::uint32_t seed, int repetition,
            const Json& shortlist, LssEvaluator& evaluator, const fs::path& directory,
            double search_started);
#ifdef S10_LSS_TESTING
Json test_report(const Instance&, double, std::uint32_t, int, const Json&,
                 const std::function<double(const Selection&)>&, const fs::path&, double);
#endif
} // namespace s10

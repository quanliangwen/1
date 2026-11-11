#pragma once

#include "rng.hpp"

#include <chrono>
#include <filesystem>
#include <functional>
#include <string>

namespace ccmckp {

using Clock = std::chrono::steady_clock;
using Deadline = Clock::time_point;
using Selection = std::vector<int>;
using Groups = std::vector<Selection>;
using Stop = std::function<bool()>;
constexpr double tolerance = 1e-12;

struct Item {
    double cost, mean, variance, weight, utility;
    std::vector<double> samples, descending;
};

struct Instance {
    std::string name;
    int classes, items_per_class, sample_count;
    double combinations;
    Groups weight, utility, value;
    std::vector<Item> items;
    bool exact() const { return combinations < 1e7; }
    double cost(const Selection& selection) const;
};

struct Settings {
    double tmax = 0;
    double p0 = 0.99;
    int mc_samples = 1000000;
    int pilot_samples = 10000;
    int validation_samples = 100000;
    int tabu_tenure = 1;
    std::uint32_t seed = 832273;
};

double numpy_sum(const double* values, std::size_t count);
double integer_power_as_double(int base, int exponent);
Instance read_instance(const std::filesystem::path& directory, double lambda);
Groups quick_check(const Instance& instance, double p0, double seconds,
                   const std::filesystem::path& cache_file, bool& timed_out);
std::uint32_t sha256_prefix(const std::string& input);
double normal_quantile(double p);

} // namespace ccmckp
